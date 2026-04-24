from datetime import datetime

import pytest

from backend.crud.scribe import ScribeApplier
from backend.models import (
    ActionItem,
    BaseAttributes,
    CurrentStatus,
    DeltaUpdate,
    Entity,
    EntityType,
    GrimoireSnapshot,
    GrimoireStateJSON,
    InventoryChanges,
    SceneContext,
    ScribeExtractionResult,
    ScribeMemoryDelta,
    StoryIRBlock,
)


class TestScribeExtraction:
    """TDD tests for Scribe extraction from Story IR (SPEC §1.9)."""

    @pytest.fixture
    def sample_entity(self) -> Entity:
        return Entity(
            entity_id="hero_001",
            type=EntityType.CHARACTER,
            name="李道长",
            base_attributes=BaseAttributes(
                aliases=["老李"],
                personality="幽默散漫",
                core_motive="证明修仙已过时",
                background="前宗门弟子",
            ),
            current_status=CurrentStatus(
                health="良好",
                inventory=["符纸"],
                recent_memory_summary=[],
                relationships={},
            ),
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_ir_block(self) -> StoryIRBlock:
        return StoryIRBlock(
            block_id="block_001",
            chapter_id="chap_001",
            lexorank="a0",
            summary="李道长获得盾牌，受伤",
            involved_entities=["hero_001"],
            scene_context=SceneContext(location_id="loc_001", time_of_day="夜"),
            action_sequence=[
                ActionItem(
                    actor_id="hero_001",
                    intent="战斗中保护自己",
                    action="拿起盾牌格挡攻击，手臂受伤",
                    dialogue="咳，这盾牌还挺结实！",
                )
            ],
            created_at=datetime.utcnow(),
        )

    def test_extract_inventory_change_from_action(self, sample_ir_block, sample_entity):
        """Test: Scribe extracts inventory changes from IR action."""
        from backend.crud.scribe import ScribeExtractor

        result = ScribeExtractor.extract_from_ir(ir_block=sample_ir_block, entities=[sample_entity])

        assert result is not None
        assert len(result.updates) > 0

        delta = result.updates[0].delta
        assert "盾牌" in delta.inventory_changes.added or any(
            "盾牌" in item for item in delta.inventory_changes.added
        )

    def test_extract_health_delta_from_action(self, sample_ir_block, sample_entity):
        """Test: Scribe extracts health changes from action description."""
        from backend.crud.scribe import ScribeExtractor

        result = ScribeExtractor.extract_from_ir(ir_block=sample_ir_block, entities=[sample_entity])

        delta = result.updates[0].delta
        assert delta.health_delta is not None
        assert "伤" in delta.health_delta or "受伤" in delta.health_delta

    def test_extract_relationship_change_from_dialogue(self, sample_entity):
        """Test: Scribe extracts relationship changes from dialogue mentions."""
        from backend.crud.scribe import ScribeExtractor

        ir_block = StoryIRBlock(
            block_id="block_002",
            chapter_id="chap_001",
            lexorank="a1",
            summary="李道长与暗影对峙",
            involved_entities=["hero_001", "shadow_001"],
            scene_context=SceneContext(location_id="loc_001", time_of_day="夜"),
            action_sequence=[
                ActionItem(
                    actor_id="hero_001",
                    intent="探查对方身份",
                    action="盯着暗影中的身影",
                    dialogue="你到底是什么人？我记住你了。",
                )
            ],
            created_at=datetime.utcnow(),
        )

        shadow_entity = Entity(
            entity_id="shadow_001",
            type=EntityType.CHARACTER,
            name="暗影",
            base_attributes=BaseAttributes(
                aliases=[], personality="神秘", core_motive="监视", background="未知"
            ),
            current_status=CurrentStatus(
                health="良好", inventory=[], recent_memory_summary=[], relationships={}
            ),
            is_deleted=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        result = ScribeExtractor.extract_from_ir(
            ir_block=ir_block, entities=[sample_entity, shadow_entity]
        )

        assert len(result.updates) > 0

    def test_apply_delta_to_entity_updates_status(self, sample_entity):
        """Test: Applying delta updates entity status correctly."""
        snapshot = GrimoireSnapshot(
            snapshot_id="snap_001",
            branch_id="main",
            parent_snapshot_id=None,
            triggering_block_id="block_000",
            grimoire_state_json=GrimoireStateJSON(entities=[sample_entity]),
            created_at=datetime.utcnow(),
        )

        delta = ScribeExtractionResult(
            updates=[
                DeltaUpdate(
                    entity_id="hero_001",
                    delta=ScribeMemoryDelta(
                        inventory_changes=InventoryChanges(added=["金丹"], removed=[]),
                        health_delta="轻微受伤",
                        memory_to_append="获得金丹，与暗影对峙",
                        relationship_changes={"shadow_001": "怀疑"},
                    ),
                )
            ]
        )

        new_snapshot = ScribeApplier.apply_delta(snapshot, delta)
        updated = new_snapshot.grimoire_state_json.entities[0]

        assert updated.current_status.health == "轻微受伤"
        assert "金丹" in updated.current_status.inventory
        assert updated.current_status.relationships.get("shadow_001") == "怀疑"
        assert "金丹" in updated.current_status.recent_memory_summary[0]

    def test_scribe_ignores_rendered_html_content(self, sample_ir_block, sample_entity):
        """Test: Scribe only reads IR, never rendered HTML."""
        from backend.crud.scribe import ScribeExtractor

        sample_ir_block.content_html = "<p>一些渲染后的文字...</p>"

        result = ScribeExtractor.extract_from_ir(ir_block=sample_ir_block, entities=[sample_entity])

        assert result is not None
        for update in result.updates:
            for mem in [update.delta.memory_to_append] if update.delta.memory_to_append else []:
                assert "<p>" not in mem

    def test_multiple_deltas_applied_sequentially(self, sample_entity):
        """Test: Multiple deltas are applied in order."""
        snapshot = GrimoireSnapshot(
            snapshot_id="snap_001",
            branch_id="main",
            parent_snapshot_id=None,
            triggering_block_id="block_000",
            grimoire_state_json=GrimoireStateJSON(entities=[sample_entity]),
            created_at=datetime.utcnow(),
        )

        delta1 = ScribeExtractionResult(
            updates=[
                DeltaUpdate(
                    entity_id="hero_001",
                    delta=ScribeMemoryDelta(
                        inventory_changes=InventoryChanges(added=["剑"], removed=[]),
                        health_delta=None,
                        memory_to_append="找到一把剑",
                        relationship_changes={},
                    ),
                )
            ]
        )

        delta2 = ScribeExtractionResult(
            updates=[
                DeltaUpdate(
                    entity_id="hero_001",
                    delta=ScribeMemoryDelta(
                        inventory_changes=InventoryChanges(added=[], removed=["剑"]),
                        health_delta="重伤",
                        memory_to_append="剑断了，受了重伤",
                        relationship_changes={},
                    ),
                )
            ]
        )

        snapshot = ScribeApplier.apply_delta(snapshot, delta1)
        snapshot = ScribeApplier.apply_delta(snapshot, delta2)

        updated = snapshot.grimoire_state_json.entities[0]
        assert updated.current_status.health == "重伤"
        assert "剑" not in updated.current_status.inventory
        assert len(updated.current_status.recent_memory_summary) == 2

    def test_sliding_window_memory_cap(self, sample_entity):
        """Test: Memory window caps at max_memory_items."""
        snapshot = GrimoireSnapshot(
            snapshot_id="snap_001",
            branch_id="main",
            parent_snapshot_id=None,
            triggering_block_id="block_000",
            grimoire_state_json=GrimoireStateJSON(entities=[sample_entity]),
            created_at=datetime.utcnow(),
        )

        for i in range(10):
            delta = ScribeExtractionResult(
                updates=[
                    DeltaUpdate(
                        entity_id="hero_001",
                        delta=ScribeMemoryDelta(
                            inventory_changes=InventoryChanges(added=[], removed=[]),
                            health_delta=None,
                            memory_to_append=f"记忆{i}",
                            relationship_changes={},
                        ),
                    )
                ]
            )
            snapshot = ScribeApplier.apply_delta(snapshot, delta, max_memory_items=5)

        updated = snapshot.grimoire_state_json.entities[0]
        assert len(updated.current_status.recent_memory_summary) == 5
        assert "记忆5" in updated.current_status.recent_memory_summary[0]
        assert "记忆9" in updated.current_status.recent_memory_summary[-1]
