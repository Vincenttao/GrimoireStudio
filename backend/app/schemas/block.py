from typing import List, Optional, Dict, Any
from pydantic import BaseModel, model_validator

class BlockUpdate(BaseModel):
    selected_variant_index: Optional[int] = None
    content_snapshot: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def check_snapshot_consistency(self):
        # SPEC 2.6: 'content_snapshot' is required when updating 'selected_variant_index'
        if self.selected_variant_index is not None and self.content_snapshot is None:
            raise ValueError("Data Integrity Error: 'content_snapshot' is required when updating 'selected_variant_index'.")
        return self

class BlockRead(BaseModel):
    id: int
    chapter_id: int
    rank: str
    type: str
    variants: List[Dict[str, Any]]
    selected_variant_index: int
    content_snapshot: str
    meta_info: Dict[str, Any]

    class Config:
        from_attributes = True
