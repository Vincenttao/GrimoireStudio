from unittest.mock import AsyncMock, patch

import pytest

from backend.models import CharacterAction, StoryIRBlock


class TestIRExtraction:
    """TDD tests for Story IR Block extraction (SPEC §3.1)."""

    @pytest.fixture
    def sample_turn_logs(self) -> list[CharacterAction]:
        return [
            CharacterAction(
                intent="掩饰紧张，假装镇定",
                action="拆开信件，扫视内容后冷笑一声",
                dialogue="呵，有意思。三天？那就三天吧。",
            ),
            CharacterAction(intent="观察对方反应", action="从阴影中注视，不做声响", dialogue=""),
            CharacterAction(
                intent="试探对方底线",
                action="向前迈一步，语气加重",
                dialogue="你确定你能承受这个代价？",
            ),
        ]

    @pytest.mark.asyncio
    async def test_extract_ir_from_turn_logs_returns_valid_block(self, sample_turn_logs):
        """Test: IR extraction returns a valid StoryIRBlock."""
        from backend.services.llm_client import llm_client

        with patch.object(llm_client, "_generate_structured", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "block_id": "block_001",
                "chapter_id": "chap_001",
                "lexorank": "a0",
                "summary": "李道长收到威胁信，决定将计就计",
                "involved_entities": ["hero_001"],
                "scene_context": {"location_id": "loc_001", "time_of_day": "夜"},
                "action_sequence": [
                    {
                        "actor_id": "hero_001",
                        "intent": "掩饰紧张",
                        "action": "拆开信件",
                        "dialogue": "呵，有意思。",
                    }
                ],
            }

            result = await llm_client.extract_story_ir(
                history=sample_turn_logs, previous_block_id=None, chapter_id="chap_001"
            )

            assert result is not None
            assert isinstance(result, StoryIRBlock)
            assert result.chapter_id == "chap_001"

    @pytest.mark.asyncio
    async def test_extract_ir_includes_all_actors(self, sample_turn_logs):
        """Test: IR extraction includes all actors from turn logs."""
        from backend.services.llm_client import llm_client

        result = await llm_client.extract_story_ir(
            history=sample_turn_logs, previous_block_id=None, chapter_id="chap_001"
        )

        assert len(result.involved_entities) == 3
        assert len(result.action_sequence) == 3

    @pytest.mark.asyncio
    async def test_extract_ir_generates_summary(self, sample_turn_logs):
        """Test: IR extraction generates a meaningful summary."""
        from backend.services.llm_client import llm_client

        result = await llm_client.extract_story_ir(
            history=sample_turn_logs, previous_block_id=None, chapter_id="chap_001"
        )

        assert result.summary is not None
        assert len(result.summary) > 0

    @pytest.mark.asyncio
    async def test_extract_ir_assigns_lexorank(self, sample_turn_logs):
        """Test: IR extraction assigns proper lexorank based on previous block."""
        from backend.services.llm_client import llm_client

        result = await llm_client.extract_story_ir(
            history=sample_turn_logs,
            previous_block_id="block_003",
            chapter_id="chap_001",
        )

        assert result.lexorank is not None
        assert len(result.lexorank) > 0

    @pytest.mark.asyncio
    async def test_extract_ir_with_empty_logs_raises_error(self):
        """Test: Empty turn logs raises validation error."""
        from backend.services.llm_client import LLMError, llm_client

        with pytest.raises(LLMError):
            await llm_client.extract_story_ir(
                history=[], previous_block_id=None, chapter_id="chap_001"
            )

    @pytest.mark.asyncio
    async def test_extract_ir_preserves_dialogue_verbatim(self, sample_turn_logs):
        """Test: IR extraction preserves dialogue text exactly as spoken."""
        from backend.services.llm_client import llm_client

        result = await llm_client.extract_story_ir(
            history=sample_turn_logs, previous_block_id=None, chapter_id="chap_001"
        )

        dialogue = result.action_sequence[0].dialogue
        assert dialogue == "呵，有意思。三天？那就三天吧。"
