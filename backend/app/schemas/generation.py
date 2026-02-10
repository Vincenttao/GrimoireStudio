from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.models.chapter import NarrativeMode

class GenerationBeatRequest(BaseModel):
    project_id: int
    chapter_id: int
    anchor_block_rank: Optional[str] = "0|000000:"
    preceding_context: Optional[str] = ""
    narrative_mode: NarrativeMode = NarrativeMode.STANDARD
    mode_params: Optional[Dict[str, Any]] = {}
    manual_entity_ids: Optional[List[int]] = []
    muted_entity_ids: Optional[List[int]] = []

class GenerationBeatResponse(BaseModel):
    generated_rank: str
    schema_version: int = 1
    variants: List[Dict[str, Any]]
    meta_info: Dict[str, Any]
