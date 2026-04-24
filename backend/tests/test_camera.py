from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from backend.models import (
    ActionItem,
    BaseAttributes,
    CurrentStatus,
    Entity,
    EntityType,
    POVType,
    SceneContext,
    StoryIRBlock,
)


class TestCameraAgent:
    """TDD tests for Camera Agent rendering pipeline (SPEC §5.3)."""

    @pytest.fixture
    def sample_ir_block(self) -> StoryIRBlock:
        return StoryIRBlock(
            block_id="block_001",
            chapter_id="chap_001",
            lexorank="a0",
            summary="李道长收到神秘威胁信，决定将计就计",
            involved_entities=["entity_001", "entity_002"],
            scene_context=SceneContext(location_id="loc_001", time_of_day="夜"),
            action_sequence=[
                ActionItem(
                    actor_id="entity_001",
                    intent="掩饰内心紧张，假装镇定",
                    action="拆开信件，扫视内容后冷笑一声",
                    dialogue="呵，有意思。三天？那就三天吧。",
                ),
                ActionItem(
                    actor_id="entity_002",
                    intent="观察李道长的反应",
                    action="从阴影中注视，不做声响",
                    dialogue="",
                ),
            ],
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_character(self) -> Entity:
        return Entity(
            entity_id="entity_001",
            type=EntityType.CHARACTER,
            name="李道长",
            base_attributes=BaseAttributes(
                aliases=["老李"],
                personality="幽默散漫，实则深藏不露",
                core_motive="用科技证明传统修仙已经过时",
                background="前修仙宗门弟子，因理念不合出走",
            ),
            current_status=CurrentStatus(
                health="良好",
                inventory=["赛博金丹(假)", "符纸"],
                recent_memory_summary=["收到神秘信件"],
                relationships={"entity_002": "怀疑"},
            ),
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_render_ir_block_omniscient_pov_returns_html(self, sample_ir_block):
        """Test: Camera renders IR block with omniscient POV and returns valid HTML."""
        from backend.services.camera_client import camera_client

        with patch.object(camera_client, "_generate_prose", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "<p>夜幕低垂，李道长拆开信件...</p>"

            result = await camera_client.render(
                ir_block=sample_ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="Standard",
                subtext_ratio=0.5,
            )

            assert result is not None
            assert "<p>" in result
            mock_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_ir_block_first_person_pov_uses_character_voice(
        self, sample_ir_block, sample_character
    ):
        """Test: First-person POV renders from character's perspective."""
        from backend.services.camera_client import camera_client

        with patch.object(camera_client, "_generate_prose", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "<p>我拆开信件，冷笑一声...</p>"

            result = await camera_client.render(
                ir_block=sample_ir_block,
                pov_type=POVType.FIRST_PERSON,
                pov_character=sample_character,
                style_template="Standard",
                subtext_ratio=0.5,
            )

            assert "我" in result
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            assert "FIRST_PERSON" in str(call_args) or "第一人称" in str(call_args)

    @pytest.mark.asyncio
    async def test_render_ir_block_with_subtext_ratio_adjusts_style(self, sample_ir_block):
        """Test: Higher subtext_ratio produces more internal monologue."""
        from backend.services.camera_client import camera_client

        with patch.object(camera_client, "_generate_prose", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "<p>信纸在指间微微颤抖...</p>"

            await camera_client.render(
                ir_block=sample_ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="Standard",
                subtext_ratio=0.9,
            )

            call_args = mock_gen.call_args
            assert "90.0%" in str(call_args) or "潜台词密度" in str(call_args)

    @pytest.mark.asyncio
    async def test_render_retry_keeps_ir_unchanged(self, sample_ir_block):
        """Test: Retry with same IR produces different prose but IR remains unchanged."""
        from backend.services.camera_client import camera_client

        with patch.object(camera_client, "_generate_prose", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = ["<p>版本一</p>", "<p>版本二</p>"]

            result1 = await camera_client.render(
                ir_block=sample_ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="Standard",
                subtext_ratio=0.5,
            )
            result2 = await camera_client.render(
                ir_block=sample_ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="Standard",
                subtext_ratio=0.5,
            )

            assert result1 != result2
            assert sample_ir_block.summary == "李道长收到神秘威胁信，决定将计就计"

    @pytest.mark.asyncio
    async def test_render_empty_ir_block_raises_error(self):
        """Test: Empty action_sequence raises validation error."""
        from backend.services.camera_client import CameraError, camera_client

        empty_block = StoryIRBlock(
            block_id="block_empty",
            chapter_id="chap_001",
            lexorank="a0",
            summary="空场景",
            involved_entities=[],
            scene_context=SceneContext(location_id="loc_001", time_of_day="日"),
            action_sequence=[],
            created_at=datetime.utcnow(),
        )

        with pytest.raises(CameraError):
            await camera_client.render(
                ir_block=empty_block,
                pov_type=POVType.OMNISCIENT,
                style_template="Standard",
                subtext_ratio=0.5,
            )

    @pytest.mark.asyncio
    async def test_render_character_limited_pov_requires_character(self, sample_ir_block):
        """Test: CHARACTER_LIMITED POV requires pov_character to be set."""
        from backend.services.camera_client import CameraError, camera_client

        with pytest.raises(CameraError):
            await camera_client.render(
                ir_block=sample_ir_block,
                pov_type=POVType.CHARACTER_LIMITED,
                pov_character=None,
                style_template="Standard",
                subtext_ratio=0.5,
            )

    @pytest.mark.asyncio
    async def test_render_includes_style_template(self, sample_ir_block):
        """Test: Style template is passed to prompt."""
        from backend.services.camera_client import camera_client

        with patch.object(camera_client, "_generate_prose", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "<p>肃杀的文字...</p>"

            await camera_client.render(
                ir_block=sample_ir_block,
                pov_type=POVType.OMNISCIENT,
                style_template="商战肃杀风",
                subtext_ratio=0.5,
            )

            call_args = str(mock_gen.call_args)
            assert "商战肃杀风" in call_args or "style" in call_args.lower()
