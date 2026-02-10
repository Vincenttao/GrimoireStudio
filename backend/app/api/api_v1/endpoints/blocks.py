from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlmodel import select
from uuid import uuid4
from datetime import datetime

from app.api import deps
from app.models.chapter import Block, Chapter, VariantType
from app.models.project import Project
from app.models.user import User
from app.schemas.block import BlockUpdate, BlockRead

router = APIRouter()

@router.patch("/{block_id}", response_model=BlockRead)
def update_block(
    *,
    db: Session = Depends(deps.get_db),
    block_id: int,
    block_in: BlockUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # 1. Ownership Verification (Chain JOIN Project)
    statement = select(Block).join(Chapter).join(Project).where(
        Block.id == block_id,
        Project.owner_id == current_user.id
    )
    block = db.exec(statement).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    # 2. Apply updates
    if block_in.meta_info is not None:
        block.meta_info = block_in.meta_info

    if block_in.selected_variant_index is not None:
        # Consistency Check
        current_variants = [dict(v) for v in block.variants] # Deep-ish copy
        selected_idx = block_in.selected_variant_index
        
        if selected_idx >= len(current_variants):
             raise HTTPException(status_code=400, detail="Invalid variant index")

        # Update block values
        block.selected_variant_index = selected_idx
        block.content_snapshot = block_in.content_snapshot

        # Fork Strategy
        target_variant = current_variants[selected_idx]
        if block_in.content_snapshot != target_variant.get("text"):
            if target_variant.get("type") == VariantType.AI_GENERATED:
                # Scenario B: Create new USER_CUSTOM variant
                new_variant = {
                    "id": str(uuid4()),
                    "type": VariantType.USER_CUSTOM,
                    "label": "Custom Edit",
                    "text": block_in.content_snapshot,
                    "is_edited": True,
                    "style_tag": target_variant.get("style_tag", "custom"),
                    "model_id": "user",
                    "prompt_version": "manual",
                    "token_usage": 0,
                    "created_at": datetime.utcnow().isoformat()
                }
                current_variants.append(new_variant)
                block.selected_variant_index = len(current_variants) - 1
            else:
                # Scenario C: In-Place Update for existing USER_CUSTOM variant
                target_variant["text"] = block_in.content_snapshot
                target_variant["is_edited"] = True
        
        # FINAL ASSIGNMENT triggers database update for JSONB field
        block.variants = current_variants

    db.add(block)
    db.commit()
    db.refresh(block)
    return block
