from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class ProjectBase(BaseModel):
    title: Optional[str] = None

class ProjectCreate(ProjectBase):
    title: str

class ProjectUpdate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True
