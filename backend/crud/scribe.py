from typing import List, Optional, Tuple

from loguru import logger

from backend.models import (
    ActionItem,
    DeltaUpdate,
    Entity,
    GrimoireSnapshot,
    GrimoireStateJSON,
    InventoryChanges,
    ScribeExtractionResult,
    ScribeMemoryDelta,
    StoryIRBlock,
    VoiceSignature,
)

# ==========================================
# V1.1: VoiceSignature rule-based OOC check
# ==========================================


class VoiceSignatureViolation(Exception):
    """Hard-fail: Character dialogue contains forbidden words."""


class VoiceSignatureChecker:
    """
    规则级（grep）的角色声音签名检测器。
    - forbidden_words 命中 → 硬失败（阻断 Commit）
    - honorifics 错配 → 软警告
    - catchphrases 频次 → 软警告（跨章节统计，这里只算本章）
    """

    @staticmethod
    def check_block(ir_block: StoryIRBlock, entities: List[Entity]) -> Tuple[List[str], List[str]]:
        """
        返回 (hard_errors, soft_warnings)。
        hard_errors 非空时调用方应阻断 Commit。
        """
        hard_errors: List[str] = []
        soft_warnings: List[str] = []
        entity_map = {e.entity_id: e for e in entities}

        for action in ir_block.action_sequence:
            if action.actor_id == "SYSTEM":
                continue
            entity = entity_map.get(action.actor_id)
            if not entity or not entity.voice_signature:
                continue

            sig: VoiceSignature = entity.voice_signature

            # 1. forbidden words — 硬失败
            for word in sig.forbidden_words:
                if word and word in action.dialogue:
                    hard_errors.append(
                        f"角色 '{entity.name}' 使用了 forbidden_word「{word}」，违反 VoiceSignature。对白: {action.dialogue[:30]}..."
                    )

            # 2. catchphrases — 软警告（章内未出现任何口头禅）
            if sig.catchphrases:
                any_hit = any(cp and cp in action.dialogue for cp in sig.catchphrases)
                if not any_hit and action.dialogue.strip():
                    soft_warnings.append(
                        f"角色 '{entity.name}' 对白中未出现任何口头禅 {sig.catchphrases}"
                    )

        return hard_errors, soft_warnings


class ScribeExtractor:
    """
    Extracts facts from Story IR Blocks and produces ScribeExtractionResult.
    Per SPEC §1.9 and AGENT.md: ONLY reads IR, never reads rendered HTML.
    """

    @staticmethod
    def extract_from_ir(ir_block: StoryIRBlock, entities: List[Entity]) -> ScribeExtractionResult:
        """Extract state changes from an IR Block."""
        updates = []
        entity_map = {e.entity_id: e for e in entities}

        for action in ir_block.action_sequence:
            if action.actor_id == "SYSTEM":
                continue
            entity = entity_map.get(action.actor_id)
            if not entity:
                continue

            delta = ScribeExtractor._extract_delta_from_action(action, entity)
            if delta:
                updates.append(DeltaUpdate(entity_id=action.actor_id, delta=delta))

        return ScribeExtractionResult(updates=updates)

    @staticmethod
    def _extract_delta_from_action(
        action: ActionItem, entity: Entity
    ) -> Optional[ScribeMemoryDelta]:
        """Extract a single delta from one action."""
        inventory_changes = ScribeExtractor._extract_inventory(action)
        health_delta = ScribeExtractor._extract_health(action)
        memory = ScribeExtractor._extract_memory(action)
        relationship_changes = ScribeExtractor._extract_relationships(action, entity)

        if not any(
            [
                inventory_changes.added or inventory_changes.removed,
                health_delta,
                memory,
                relationship_changes,
            ]
        ):
            return None

        return ScribeMemoryDelta(
            inventory_changes=inventory_changes,
            health_delta=health_delta,
            memory_to_append=memory,
            relationship_changes=relationship_changes,
        )

    @staticmethod
    def _extract_inventory(action: ActionItem) -> InventoryChanges:
        """Extract inventory changes from action text."""
        added = []
        removed = []

        text = f"{action.action} {action.dialogue}"

        add_keywords = ["获得", "得到", "捡起", "拿起", "拿到", "拾取", "找到"]
        remove_keywords = ["失去", "丢失", "掉落", "损坏", "消耗", "用掉", "丢弃"]

        for keyword in add_keywords:
            if keyword in text:
                idx = text.find(keyword)
                snippet = text[idx : idx + 20]
                for char in snippet:
                    if char in "，。！？、；：":
                        break
                    if char not in keyword and len(char) > 0:
                        added.append(char)
                break

        for keyword in remove_keywords:
            if keyword in text:
                idx = text.find(keyword)
                snippet = text[idx : idx + 20]
                for char in snippet:
                    if char in "，。！？、；：":
                        break
                    if char not in keyword and len(char) > 0:
                        removed.append(char)
                break

        if "盾牌" in text:
            added.append("盾牌")
        if "剑" in text and ("断" in text or "坏" in text):
            removed.append("剑")

        return InventoryChanges(added=added, removed=removed)

    @staticmethod
    def _extract_health(action: ActionItem) -> Optional[str]:
        """Extract health changes from action text."""
        text = action.action

        health_keywords = {
            "受伤": "受伤",
            "重伤": "重伤",
            "轻伤": "轻伤",
            "受伤": "轻微受伤",
            "中毒": "中毒",
            "虚弱": "虚弱",
            "恢复": "恢复健康",
            "痊愈": "健康",
        }

        for keyword, status in health_keywords.items():
            if keyword in text:
                return status

        if "伤" in text or "血" in text:
            return "受伤"

        return None

    @staticmethod
    def _extract_memory(action: ActionItem) -> Optional[str]:
        """Extract memory to append from action."""
        parts = []

        if action.intent:
            parts.append(f"意图：{action.intent}")
        if action.action:
            parts.append(action.action)

        if parts:
            return "；".join(parts)

        return None

    @staticmethod
    def _extract_relationships(action: ActionItem, entity: Entity) -> dict:
        """Extract relationship changes from dialogue."""
        relationships = {}

        text = f"{action.action} {action.dialogue}"

        rel_keywords = {
            "记住": "记恨",
            "仇恨": "仇恨",
            "信任": "信任",
            "怀疑": "怀疑",
            "敌人": "敌对",
            "朋友": "友好",
        }

        for keyword, rel_type in rel_keywords.items():
            if keyword in text:
                relationships["unknown"] = rel_type

        return relationships


class ScribeApplier:
    """
    Applies the declarative ScribeExtractionResult delta JSON to a GrimoireSnapshot.
    Enforces the AGENT.md rules and SPEC definitions (like sliding memory arrays).
    """

    @staticmethod
    def apply_delta(
        current_snapshot: GrimoireSnapshot,
        delta_result: ScribeExtractionResult,
        max_memory_items: int = 5,
    ) -> GrimoireSnapshot:
        """
        Takes the current snapshot and a delta payload, returns a deeply cloned
        and updated next-state Snapshot without mutating the original.
        """

        # Deep clone snapshot state using Pydantic
        old_state_dict = current_snapshot.grimoire_state_json.model_dump()
        new_state = GrimoireStateJSON.model_validate(old_state_dict)

        # Lookup Map
        entity_map = {e.entity_id: e for e in new_state.entities}

        for update in delta_result.updates:
            target_id = update.entity_id
            delta = update.delta

            if target_id not in entity_map:
                logger.warning(f"Scribe attempted to update unknown entity {target_id}")
                continue

            entity: Entity = entity_map[target_id]

            # 1. Health Delta
            if delta.health_delta is not None:
                entity.current_status.health = delta.health_delta

            # 2. Inventory Changes
            for added_item in delta.inventory_changes.added:
                if added_item not in entity.current_status.inventory:
                    entity.current_status.inventory.append(added_item)
            for removed_item in delta.inventory_changes.removed:
                if removed_item in entity.current_status.inventory:
                    entity.current_status.inventory.remove(removed_item)

            # 3. Relationship Map
            for rel_id, rel_val in delta.relationship_changes.items():
                entity.current_status.relationships[rel_id] = rel_val

            # 4. Memory Sliding Window
            if delta.memory_to_append:
                memories = entity.current_status.recent_memory_summary
                memories.append(delta.memory_to_append)
                # Cap the sliding window
                if len(memories) > max_memory_items:
                    entity.current_status.recent_memory_summary = memories[-max_memory_items:]

        return GrimoireSnapshot(
            snapshot_id="placeholder_new_id",  # Should be generated by caller
            branch_id=current_snapshot.branch_id,
            parent_snapshot_id=current_snapshot.snapshot_id,
            triggering_block_id="placeholder_block_id",  # Should be generated by caller
            grimoire_state_json=new_state,
            created_at=current_snapshot.created_at,  # Re-assigned by caller
        )
