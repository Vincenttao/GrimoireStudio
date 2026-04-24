"""
V1.1 端到端烟雾测试 — 真 LLM 联通（DashScope / qwen）

流程:
  1. 创建角色（带 VoiceSignature）
  2. 设置 Settings → QIDIAN 平台
  3. 触发 Spark（beat_type=SHOW_OFF_FACE_SLAP, target_char_count=1500）
  4. 订阅 WebSocket 看推演事件
  5. 等到 SCENE_COMPLETE
  6. 渲染 IR（mock，因为 IR 插入逻辑 V1 未完整）
  7. Commit → 看 streak 更新

使用：后端需已在 127.0.0.1:8000 上运行。
"""

import asyncio
import json
import sys
import time
import uuid

import httpx
import websockets

BASE = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws"


async def step(label: str):
    print(f"\n=== {label} ===")


async def ws_listener(stop_event: asyncio.Event, events: list):
    try:
        async with websockets.connect(WS_URL) as ws:
            print("  [WS] connected")
            while not stop_event.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2)
                    data = json.loads(raw)
                    events.append(data)
                    ev_type = data.get("type") or data.get("event") or "?"
                    state = data.get("state") or data.get("data", {}).get("state", "")
                    print(f"  [WS] {ev_type} {state}")
                    if ev_type in ("SCENE_COMPLETE", "ERROR", "COMMIT_COMPLETE"):
                        pass
                except asyncio.TimeoutError:
                    continue
    except Exception as e:
        print(f"  [WS] error: {e}")


async def main() -> int:
    errors = []

    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        # --- Step 1: 健康 ---
        await step("Step 1. health check")
        r = await client.get("/health")
        assert r.status_code == 200
        print(f"  health: {r.json()}")

        # --- Step 2: 切平台预设（起点）---
        await step("Step 2. switch platform → QIDIAN")
        r = await client.post("/api/v1/render/switch_platform", json={"platform": "QIDIAN"})
        assert r.status_code == 200, r.text
        preset = r.json()
        print(f"  platform: {preset['platform']}, default_char_count: {preset['default_target_char_count']}")

        # --- Step 3: 创建角色，带 VoiceSignature ---
        await step("Step 3. create character with VoiceSignature")
        char_id = f"char-{uuid.uuid4().hex[:8]}"
        entity_payload = {
            "entity_id": char_id,
            "type": "CHARACTER",
            "name": "宁毅",
            "base_attributes": {
                "aliases": ["老宁"],
                "personality": "散漫玩世不恭，心思缜密，懒得解释",
                "core_motive": "让苏家撑下去，顺便找乐子",
                "background": "穿越者，前投行分析师",
            },
            "current_status": {
                "health": "良好",
                "inventory": ["折扇"],
                "relationships": {},
                "recent_memory_summary": [],
            },
            "voice_signature": {
                "catchphrases": ["大人时代变了"],
                "catchphrase_min_freq_chapters": 10,
                "honorifics": {},
                "forbidden_words": ["宝宝", "亲亲"],
                "sample_utterances": ["风投比算命靠谱多了。"],
                "tone_keywords": ["便", "倒是"],
            },
            "is_deleted": False,
            "created_at": "2026-04-24T00:00:00+00:00",
            "updated_at": "2026-04-24T00:00:00+00:00",
        }
        r = await client.post("/api/v1/grimoire/entities", json=entity_payload)
        assert r.status_code == 200, r.text
        print(f"  entity created: {char_id}")

        # --- Step 4: 创建一个反派 ---
        foe_id = f"char-{uuid.uuid4().hex[:8]}"
        r = await client.post(
            "/api/v1/grimoire/entities",
            json={
                "entity_id": foe_id,
                "type": "CHARACTER",
                "name": "乌家来人",
                "base_attributes": {
                    "aliases": [],
                    "personality": "嚣张跋扈，欺软怕硬",
                    "core_motive": "勒索苏家",
                    "background": "乌家三爷心腹",
                },
                "current_status": {
                    "health": "良好",
                    "inventory": ["腰牌"],
                    "relationships": {},
                    "recent_memory_summary": [],
                },
                "voice_signature": None,
                "is_deleted": False,
                "created_at": "2026-04-24T00:00:00+00:00",
                "updated_at": "2026-04-24T00:00:00+00:00",
            },
        )
        assert r.status_code == 200, r.text
        print(f"  foe created: {foe_id}")

        # --- Step 5: 卡文救急（验证端点）---
        await step("Step 5. unblock_writer (optional LLM call)")
        r = await client.post("/api/v1/muse/unblock_writer", json={})
        assert r.status_code == 200, r.text
        candidates = r.json()["candidates"]
        print(f"  got {len(candidates)} candidates")
        for c in candidates[:3]:
            print(f"   - {c['direction']}（{c['beat_type']}）: {c['user_prompt'][:40]}...")

        # --- Step 6: 触发 Spark with beat_type ---
        await step("Step 6. trigger Spark (beat_type=SHOW_OFF_FACE_SLAP, 1500 chars)")
        spark_id = f"spark-{uuid.uuid4().hex[:8]}"

        events: list = []
        stop_event = asyncio.Event()
        ws_task = asyncio.create_task(ws_listener(stop_event, events))
        await asyncio.sleep(0.5)  # let WS connect

        spark_payload = {
            "spark_id": spark_id,
            "chapter_id": "chap-e2e-001",
            "user_prompt": (
                f"乌家派{foe_id[-4:]}来勒索苏家，在苏府门前嚣张叫嚣。"
                f"宁毅({char_id[-4:]})慢悠悠出场，用散漫态度轻描淡写化解，反将一军把对方挫得抬不起头。"
            ),
            "beat_type": "SHOW_OFF_FACE_SLAP",
            "target_char_count": 1500,
            "overrides": {},
        }
        r = await client.post("/api/v1/sandbox/spark", json=spark_payload)
        if r.status_code != 202:
            print(f"  Spark failed: {r.status_code} {r.text}")
            errors.append("spark")
            stop_event.set()
            await ws_task
            return 1
        print(f"  spark accepted: {spark_id}")

        # --- Step 7: 等 SCENE_COMPLETE (最多 3 分钟) ---
        await step("Step 7. waiting for SCENE_COMPLETE (up to 180s)")
        started = time.time()
        completed = False
        while time.time() - started < 180:
            for e in events:
                t = e.get("type") or e.get("event")
                if t == "SCENE_COMPLETE":
                    completed = True
                    break
                if t == "ERROR":
                    print(f"  ERROR event: {e}")
                    errors.append("maestro")
                    break
            if completed or errors:
                break
            await asyncio.sleep(1)

        stop_event.set()
        await ws_task

        print(f"  Total WS events received: {len(events)}")
        state_changes = [e for e in events if (e.get("type") or e.get("event")) == "STATE_CHANGE"]
        print(f"  State transitions: {[sc.get('data', {}).get('state') for sc in state_changes]}")

        if not completed:
            print("  ⚠️ Scene did not complete within timeout — backend running but Maestro may be stuck")
            errors.append("timeout")

        # --- Step 8: commit smoke (IR block id is mock for now) ---
        await step("Step 8. commit smoke (update streak)")
        r = await client.post(
            "/api/v1/sandbox/commit",
            json={"ir_block_id": "mock_block", "final_content_html": "<p>测试内容</p>"},
        )
        assert r.status_code == 200, r.text
        commit_data = r.json()
        print(f"  commit: {commit_data}")
        assert commit_data["daily_streak_count"] == 1

        # --- Step 9: SoftPatch smoke ---
        await step("Step 9. SoftPatch create + effective overlay")
        r = await client.post(
            "/api/v1/grimoire/soft_patches",
            json={
                "target_entity_id": char_id,
                "target_path": "current_status.inventory",
                "new_value": ["折扇", "加特林"],
                "author_note": "补一把神器",
            },
        )
        assert r.status_code == 200, r.text
        patch_id = r.json()["patch"]["patch_id"]
        print(f"  soft_patch created: {patch_id}")

        r = await client.get(f"/api/v1/grimoire/entities/{char_id}/effective")
        assert r.status_code == 200
        eff = r.json()
        print(f"  effective inventory: {eff['entity']['current_status']['inventory']}")
        assert "加特林" in eff["entity"]["current_status"]["inventory"]

    print("\n=== SUMMARY ===")
    if errors:
        print(f"  ⚠️ issues: {errors}")
        return 2 if "timeout" in errors else 1
    print("  ✅ end-to-end smoke passed (real DashScope LLM)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
