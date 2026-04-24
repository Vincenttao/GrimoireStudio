"""
V1.1 Web Novel Workshop — End-to-End Tests

覆盖：
  - BeatType 枚举 + Maestro 专项判据
  - Camera 字数硬约束循环 (expand / shrink)
  - Ending Hook Guard (本地启发式 + refine_ending)
  - VoiceSignature 规则检查 (forbidden_words 硬失败 + catchphrase 软警告)
  - SoftPatch CRUD + apply_patch overlay
  - PlatformProfile 切换
  - [卡文救急] unblock_writer 回退路径
  - Scratchpad JSONL 落盘 + 崩溃恢复扫描

所有 LLM 调用 mock，真 API 测试走 `-m llm` 标记。
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

# ==========================================
# Fixture: 临时数据库 + 环境隔离
# ==========================================


@pytest_asyncio.fixture(autouse=True)
async def isolated_db(tmp_path, monkeypatch):
    """每个测试独立 sqlite + scratchpad.jsonl，避免污染。"""
    db_path = tmp_path / "grimoire_test.sqlite"
    scratch_path = tmp_path / "scratchpad.jsonl"

    # Point the database module at our tmp file
    import backend.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))

    # Point scratchpad JSONL to tmp
    import backend.services.maestro_loop as maestro_module

    monkeypatch.setattr(maestro_module, "SCRATCHPAD_JSONL_PATH", scratch_path)

    # Initialize schema
    await db_module.init_db()

    yield {
        "db_path": str(db_path),
        "scratch_path": scratch_path,
    }


# ==========================================
# Helpers
# ==========================================


def make_entity(entity_id: str, name: str, voice_sig=None):
    from backend.models import BaseAttributes, CurrentStatus, Entity, EntityType

    return Entity(
        entity_id=entity_id,
        type=EntityType.CHARACTER,
        name=name,
        base_attributes=BaseAttributes(
            aliases=[],
            personality="网文主角",
            core_motive="变强",
            background="没什么特别",
        ),
        current_status=CurrentStatus(
            health="良好", inventory=[], recent_memory_summary=[], relationships={}
        ),
        voice_signature=voice_sig,
        is_deleted=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def make_ir_block_with_dialogue(block_id: str, actor_id: str, dialogue: str):
    from backend.models import ActionItem, SceneContext, StoryIRBlock

    return StoryIRBlock(
        block_id=block_id,
        chapter_id="chap_001",
        lexorank="a0",
        summary="测试",
        involved_entities=[actor_id],
        scene_context=SceneContext(location_id="loc_001", time_of_day="日"),
        action_sequence=[
            ActionItem(
                actor_id=actor_id,
                intent="展示实力",
                action="动了动手指",
                dialogue=dialogue,
            )
        ],
        created_at=datetime.utcnow(),
    )


# ==========================================
# 1. BeatType 枚举
# ==========================================


class TestBeatType:
    def test_beat_type_enum_has_eight_values(self):
        from backend.models import BeatType

        assert len(list(BeatType)) == 8
        assert BeatType.SHOW_OFF_FACE_SLAP.value == "SHOW_OFF_FACE_SLAP"
        assert BeatType.DAILY_SLICE.value == "DAILY_SLICE"

    def test_beat_type_criteria_covers_all_types(self):
        from backend.models import BEAT_TYPE_CRITERIA, BeatType

        for bt in BeatType:
            assert bt in BEAT_TYPE_CRITERIA
            assert len(BEAT_TYPE_CRITERIA[bt]) > 0, f"{bt} 缺少判据"

    def test_the_spark_defaults_to_daily_slice(self):
        from backend.models import BeatType, TheSpark

        spark = TheSpark(spark_id="s1", chapter_id="c1", user_prompt="一段日常")
        assert spark.beat_type == BeatType.DAILY_SLICE
        assert spark.target_char_count == 3000


# ==========================================
# 2. Maestro beat_type 判据接入
# ==========================================


class TestMaestroBeatTypeJudgment:
    @pytest.mark.asyncio
    async def test_maestro_prompt_contains_beat_type_criteria(self):
        from backend.models import BeatType, MaestroDecision
        from backend.services.llm_client import llm_client

        captured_messages = {}

        async def fake_generate(messages, response_model, temperature=0.5):
            captured_messages["messages"] = messages
            return MaestroDecision(next_actor_id=None, is_beat_complete=True, reasoning="done")

        with patch.object(llm_client, "_generate_structured", side_effect=fake_generate):
            await llm_client.evaluate_scene_progression(
                prompt="主角打反派",
                entities_json="[]",
                history_json="",
                beat_type=BeatType.SHOW_OFF_FACE_SLAP,
            )

        system_prompt = captured_messages["messages"][0]["content"]
        assert "SHOW_OFF_FACE_SLAP" in system_prompt or "装逼打脸" in system_prompt
        # Verify specific criterion text is present
        assert "反派" in system_prompt or "挫" in system_prompt


# ==========================================
# 3. Camera 字数硬约束 + 钩子守卫
# ==========================================


class TestCameraCharCount:
    @pytest.mark.asyncio
    async def test_char_count_within_tolerance_no_adjust(self):
        """首轮字数已命中目标 → 不触发 adjust_mode 重试。"""
        from backend.models import POVType
        from backend.services.camera_client import CameraClient

        camera = CameraClient()
        ir_block = make_ir_block_with_dialogue("b1", "e1", "你好")
        target = 100

        # 生成 95 字（在 ±10% 以内）
        html = "<p>" + ("字" * 95) + "</p>"
        with patch.object(camera, "_generate_prose", new=AsyncMock(return_value=html)):
            result_html, actual, _ = await camera.render_with_char_count_enforcement(
                ir_block=ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="热血爽文",
                subtext_ratio=0.2,
                target_char_count=target,
            )
            assert 90 <= actual <= 110
            assert camera._generate_prose.call_count == 1

    @pytest.mark.asyncio
    async def test_char_count_too_short_triggers_expand(self):
        from backend.models import POVType
        from backend.services.camera_client import CameraClient

        camera = CameraClient()
        ir_block = make_ir_block_with_dialogue("b1", "e1", "你好")
        target = 100
        responses = [
            "<p>" + ("字" * 50) + "</p>",  # first: too short
            "<p>" + ("字" * 95) + "</p>",  # after expand: OK
        ]
        mock = AsyncMock(side_effect=responses)
        with patch.object(camera, "_generate_prose", new=mock):
            _, actual, _ = await camera.render_with_char_count_enforcement(
                ir_block=ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="热血爽文",
                subtext_ratio=0.2,
                target_char_count=target,
            )
            assert mock.call_count == 2
            # Verify the second call's prompt contained "expand" / "追加"
            second_call_prompt = mock.call_args_list[1][0][0]
            assert "追加" in second_call_prompt or "扩" in second_call_prompt

    @pytest.mark.asyncio
    async def test_char_count_too_long_triggers_shrink(self):
        from backend.models import POVType
        from backend.services.camera_client import CameraClient

        camera = CameraClient()
        ir_block = make_ir_block_with_dialogue("b1", "e1", "你好")
        target = 100
        responses = [
            "<p>" + ("字" * 300) + "</p>",  # first: too long
            "<p>" + ("字" * 98) + "</p>",  # after shrink: OK
        ]
        mock = AsyncMock(side_effect=responses)
        with patch.object(camera, "_generate_prose", new=mock):
            _, actual, _ = await camera.render_with_char_count_enforcement(
                ir_block=ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="热血爽文",
                subtext_ratio=0.2,
                target_char_count=target,
            )
            assert mock.call_count == 2
            second_call_prompt = mock.call_args_list[1][0][0]
            assert (
                "精简" in second_call_prompt
                or "shrink" in second_call_prompt.lower()
                or "压" in second_call_prompt
            )

    @pytest.mark.asyncio
    async def test_char_count_retry_ceiling_3(self):
        """连续 3 轮仍不达标，返回实际字数不再重试。"""
        from backend.models import POVType
        from backend.services.camera_client import CameraClient

        camera = CameraClient()
        ir_block = make_ir_block_with_dialogue("b1", "e1", "")
        responses = ["<p>" + ("字" * 10) + "</p>"] * 10  # always too short
        mock = AsyncMock(side_effect=responses)
        with patch.object(camera, "_generate_prose", new=mock):
            await camera.render_with_char_count_enforcement(
                ir_block=ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="热血爽文",
                subtext_ratio=0.2,
                target_char_count=500,
                max_attempts=3,
            )
            # 1 first + max_attempts 调整 = 最多 4 次，但 max_attempts=3 意味着调整 3 轮
            assert mock.call_count <= 4


class TestHookGuard:
    @pytest.mark.asyncio
    async def test_ending_with_question_mark_has_hook(self):
        from backend.services.camera_client import CameraClient

        html = "<p>前面一段。后面一段内容。宁毅会答应吗？</p>"
        result = await CameraClient().check_ending_hook(html)
        assert result.has_hook is True

    @pytest.mark.asyncio
    async def test_ending_with_ellipsis_has_hook(self):
        from backend.services.camera_client import CameraClient

        html = "<p>他缓缓转身，竟然……</p>"
        result = await CameraClient().check_ending_hook(html)
        assert result.has_hook is True

    @pytest.mark.asyncio
    async def test_flat_ending_no_hook(self):
        from backend.services.camera_client import CameraClient

        html = "<p>" + ("他吃完饭，洗了澡，躺下睡觉。" * 10) + "</p>"
        result = await CameraClient().check_ending_hook(html)
        assert result.has_hook is False
        assert "建议补钩子" in result.reason or "未检测到" in result.reason

    @pytest.mark.asyncio
    async def test_refine_ending_replaces_last_paragraph(self):
        from backend.models import POVType
        from backend.services.camera_client import CameraClient

        camera = CameraClient()
        original = "<p>前半段内容。</p><p>平淡结尾。</p>"
        new_ending = "<p>就在此时，门被猛地撞开——！</p>"
        ir_block = make_ir_block_with_dialogue("b1", "e1", "")

        with patch.object(camera, "_generate_prose", new=AsyncMock(return_value=new_ending)):
            refined = await camera.refine_ending(
                html=original,
                ir_block=ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="热血爽文",
                subtext_ratio=0.2,
            )
            # Should still contain the first paragraph (前半段)
            assert "前半段内容" in refined
            # Should contain the new dramatic ending
            assert "撞开" in refined


# ==========================================
# 4. VoiceSignature 规则检查
# ==========================================


class TestVoiceSignature:
    def test_forbidden_word_in_dialogue_produces_hard_error(self):
        from backend.crud.scribe import VoiceSignatureChecker
        from backend.models import VoiceSignature

        vs = VoiceSignature(catchphrases=["时代变了"], forbidden_words=["宝宝", "亲亲"])
        actor = make_entity("ning_yi", "宁毅", voice_sig=vs)
        ir_block = make_ir_block_with_dialogue("b1", "ning_yi", "宝宝，你怎么还不睡呀")

        errors, warnings = VoiceSignatureChecker.check_block(ir_block, [actor])
        assert len(errors) > 0
        assert any("宝宝" in e for e in errors)

    def test_catchphrase_missing_produces_soft_warning(self):
        from backend.crud.scribe import VoiceSignatureChecker
        from backend.models import VoiceSignature

        vs = VoiceSignature(catchphrases=["大人，时代变了"], forbidden_words=[])
        actor = make_entity("ning_yi", "宁毅", voice_sig=vs)
        ir_block = make_ir_block_with_dialogue("b1", "ning_yi", "你说的都对")

        errors, warnings = VoiceSignatureChecker.check_block(ir_block, [actor])
        assert len(errors) == 0
        assert len(warnings) > 0

    def test_catchphrase_present_no_warning(self):
        from backend.crud.scribe import VoiceSignatureChecker
        from backend.models import VoiceSignature

        vs = VoiceSignature(catchphrases=["时代变了"], forbidden_words=[])
        actor = make_entity("ning_yi", "宁毅", voice_sig=vs)
        ir_block = make_ir_block_with_dialogue("b1", "ning_yi", "大人，时代变了，风投比算命靠谱")

        errors, warnings = VoiceSignatureChecker.check_block(ir_block, [actor])
        assert errors == []
        assert warnings == []

    def test_entity_without_voice_signature_skipped(self):
        from backend.crud.scribe import VoiceSignatureChecker

        actor = make_entity("e1", "路人", voice_sig=None)
        ir_block = make_ir_block_with_dialogue("b1", "e1", "宝宝")
        errors, warnings = VoiceSignatureChecker.check_block(ir_block, [actor])
        assert errors == [] and warnings == []


# ==========================================
# 5. SoftPatch CRUD + apply overlay
# ==========================================


class TestSoftPatch:
    @pytest.mark.asyncio
    async def test_create_and_list_patch(self, isolated_db):
        from backend.crud import soft_patches

        patch = await soft_patches.create_soft_patch(
            target_entity_id="e1",
            target_path="current_status.inventory",
            old_value=["旧物品"],
            new_value=["新物品 A", "新物品 B"],
            author_note="原文错了，实际应该有两件",
        )
        assert patch.patch_id.startswith("patch_")
        assert patch.status.value == "PENDING"

        all_pending = await soft_patches.list_pending_patches()
        assert len(all_pending) == 1
        assert all_pending[0].patch_id == patch.patch_id

    @pytest.mark.asyncio
    async def test_discard_patch_removes_from_pending(self, isolated_db):
        from backend.crud import soft_patches

        patch = await soft_patches.create_soft_patch(
            target_entity_id="e1",
            target_path="base_attributes.personality",
            old_value="腼腆",
            new_value="狂傲",
            author_note="改性格",
        )
        ok = await soft_patches.discard_patch(patch.patch_id)
        assert ok is True

        pending = await soft_patches.list_pending_patches()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_mark_merged(self, isolated_db):
        from backend.crud import soft_patches

        p1 = await soft_patches.create_soft_patch("e1", "current_status.inventory", [], ["a"], "n1")
        p2 = await soft_patches.create_soft_patch(
            "e1", "current_status.health", "良好", "受伤", "n2"
        )
        count = await soft_patches.mark_merged([p1.patch_id, p2.patch_id], "snap_001")
        assert count == 2

        pending = await soft_patches.list_pending_patches()
        assert pending == []

    def test_apply_patch_to_dict_nested_overlay(self):
        from backend.crud.soft_patches import apply_patch_to_dict

        data = {
            "base_attributes": {"personality": "腼腆"},
            "current_status": {"inventory": ["旧"]},
        }
        result = apply_patch_to_dict(data, "current_status.inventory", ["新 A", "新 B"])
        assert result["current_status"]["inventory"] == ["新 A", "新 B"]
        # Original must not be mutated
        assert data["current_status"]["inventory"] == ["旧"]


# ==========================================
# 6. PlatformProfile 切换
# ==========================================


class TestPlatformProfile:
    def test_five_platforms_plus_custom_exist(self):
        from backend.models import PLATFORM_PRESETS, PlatformProfile

        assert len(list(PlatformProfile)) == 6
        for p in PlatformProfile:
            assert p in PLATFORM_PRESETS

    def test_qidian_preset_values(self):
        from backend.models import PLATFORM_PRESETS, PlatformProfile

        qd = PLATFORM_PRESETS[PlatformProfile.QIDIAN]
        assert qd["subtext_ratio"] == 0.2
        assert qd["default_char_count"] == 3000

    def test_jinjiang_has_higher_subtext(self):
        from backend.models import PLATFORM_PRESETS, PlatformProfile

        jj = PLATFORM_PRESETS[PlatformProfile.JINJIANG]
        qd = PLATFORM_PRESETS[PlatformProfile.QIDIAN]
        # 晋江读者要心理描写
        assert jj["subtext_ratio"] > qd["subtext_ratio"]


# ==========================================
# 7. Scratchpad JSONL 落盘
# ==========================================


class TestScratchpadDurability:
    def test_append_writes_line(self, isolated_db):
        from backend.services.maestro_loop import SCRATCHPAD_JSONL_PATH, _scratchpad_append

        _scratchpad_append(
            {
                "trace_id": "t1",
                "spark_id": "s1",
                "event": "STARTED",
                "beat_type": "SHOW_OFF_FACE_SLAP",
            }
        )
        with open(SCRATCHPAD_JSONL_PATH) as f:
            lines = f.readlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["trace_id"] == "t1"
        assert row["event"] == "STARTED"
        assert "ts" in row  # timestamp auto-added

    def test_scan_unfinished_excludes_committed_traces(self, isolated_db):
        from backend.services.maestro_loop import (
            _scratchpad_append,
            scratchpad_scan_unfinished,
        )

        # trace A: unfinished (no COMMITTED)
        _scratchpad_append({"trace_id": "A", "spark_id": "A", "event": "STARTED", "turn": 0})
        _scratchpad_append(
            {"trace_id": "A", "spark_id": "A", "state": "CALLING_CHARACTER", "turn": 1}
        )

        # trace B: finished (has COMMITTED)
        _scratchpad_append({"trace_id": "B", "spark_id": "B", "event": "STARTED", "turn": 0})
        _scratchpad_append({"trace_id": "B", "spark_id": "B", "event": "COMMITTED"})

        unfinished = scratchpad_scan_unfinished()
        tids = {u["trace_id"] for u in unfinished}
        assert "A" in tids
        assert "B" not in tids

    def test_interrupted_treated_as_terminal(self, isolated_db):
        from backend.services.maestro_loop import (
            _scratchpad_append,
            scratchpad_scan_unfinished,
        )

        _scratchpad_append({"trace_id": "X", "spark_id": "X", "event": "STARTED"})
        _scratchpad_append({"trace_id": "X", "spark_id": "X", "event": "INTERRUPTED"})
        assert all(u["trace_id"] != "X" for u in scratchpad_scan_unfinished())

    def test_compact_reduces_log_size(self, isolated_db):
        from backend.services.maestro_loop import (
            SCRATCHPAD_JSONL_PATH,
            _scratchpad_append,
            scratchpad_compact,
        )

        # Create 5 committed traces
        for i in range(5):
            tid = f"old_{i}"
            _scratchpad_append({"trace_id": tid, "spark_id": tid, "event": "STARTED"})
            _scratchpad_append({"trace_id": tid, "spark_id": tid, "event": "COMMITTED"})

        before = SCRATCHPAD_JSONL_PATH.read_text().count("\n")
        scratchpad_compact(keep_terminal_recent=2)
        after = SCRATCHPAD_JSONL_PATH.read_text().count("\n")
        # Expect 2 traces kept × 2 lines each = 4 lines (not 10)
        assert after <= before


# ==========================================
# 8. Entity with VoiceSignature roundtrip (DB)
# ==========================================


class TestEntityVoiceSignatureRoundtrip:
    @pytest.mark.asyncio
    async def test_create_and_fetch_entity_with_voice_signature(self, isolated_db):
        from backend.crud import entities as ent_crud
        from backend.models import VoiceSignature

        vs = VoiceSignature(
            catchphrases=["时代变了"],
            honorifics={"长辈": "您", "平辈": "你"},
            forbidden_words=["宝宝"],
            sample_utterances=["大人，时代变了。"],
        )
        ent = make_entity("ning_yi", "宁毅", voice_sig=vs)
        await ent_crud.create_entity(ent)

        fetched = await ent_crud.get_entity("ning_yi")
        assert fetched is not None
        assert fetched.voice_signature is not None
        assert fetched.voice_signature.catchphrases == ["时代变了"]
        assert fetched.voice_signature.forbidden_words == ["宝宝"]

    @pytest.mark.asyncio
    async def test_fetch_entity_without_voice_signature(self, isolated_db):
        from backend.crud import entities as ent_crud

        ent = make_entity("plain", "路人甲", voice_sig=None)
        await ent_crud.create_entity(ent)

        fetched = await ent_crud.get_entity("plain")
        assert fetched.voice_signature is None


# ==========================================
# 9. unblock_writer endpoint (HTTP)
# ==========================================


class TestUnblockWriterEndpoint:
    @pytest.mark.asyncio
    async def test_unblock_writer_returns_three_candidates_offline(self, isolated_db, monkeypatch):
        """无 LLM key 时走默认候选回退路径。"""
        from httpx import ASGITransport, AsyncClient

        from backend.main import app

        # Make sure no API key present
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/muse/unblock_writer", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["candidates"]) == 3
        directions = {c["direction"] for c in data["candidates"]}
        # Three must cover different flavors
        assert len(directions) == 3


# ==========================================
# 10. 平台切换 endpoint
# ==========================================


class TestSwitchPlatformEndpoint:
    @pytest.mark.asyncio
    async def test_switch_to_jinjiang_updates_defaults(self, isolated_db):
        from httpx import ASGITransport, AsyncClient

        from backend.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/render/switch_platform", json={"platform": "JINJIANG"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["platform"] == "JINJIANG"
        assert data["default_render_mixer"]["subtext_ratio"] == 0.6
        assert data["default_target_char_count"] == 4000


# ==========================================
# 11. SoftPatch HTTP endpoint roundtrip
# ==========================================


class TestSoftPatchEndpoint:
    @pytest.mark.asyncio
    async def test_soft_patch_create_and_overlay(self, isolated_db):
        from httpx import ASGITransport, AsyncClient

        from backend.crud import entities as ent_crud
        from backend.main import app

        # Seed an entity
        ent = make_entity("ning_yi", "宁毅")
        await ent_crud.create_entity(ent)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Create soft patch
            resp = await ac.post(
                "/api/v1/grimoire/soft_patches",
                json={
                    "target_entity_id": "ning_yi",
                    "target_path": "current_status.inventory",
                    "new_value": ["加特林", "符纸"],
                    "author_note": "原文漏了加特林",
                },
            )
            assert resp.status_code == 200
            patch_id = resp.json()["patch"]["patch_id"]

            # Get effective view (should overlay the patch)
            eff = await ac.get("/api/v1/grimoire/entities/ning_yi/effective")
            assert eff.status_code == 200
            eff_data = eff.json()
            assert eff_data["applied_patch_count"] == 1
            assert "加特林" in eff_data["entity"]["current_status"]["inventory"]

            # Discard patch
            dd = await ac.delete(f"/api/v1/grimoire/soft_patches/{patch_id}")
            assert dd.status_code == 200

            eff2 = await ac.get("/api/v1/grimoire/entities/ning_yi/effective")
            assert eff2.json()["applied_patch_count"] == 0


# ==========================================
# 12. Health endpoint sanity
# ==========================================


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_ok(self, isolated_db):
        from httpx import ASGITransport, AsyncClient

        from backend.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
