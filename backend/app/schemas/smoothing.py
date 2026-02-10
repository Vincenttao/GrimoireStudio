from typing import Optional
from pydantic import BaseModel

class SmoothingRequest(BaseModel):
    prev_block_text: str
    next_block_text: str
    idempotency_key: str
    project_id: int

class SmoothingResponse(BaseModel):
    needs_smoothing: bool
    smoothed_text: Optional[str] = None
