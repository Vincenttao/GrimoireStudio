from typing import List, Optional
from pydantic import BaseModel
from app.models.entity import EntityType

class EntityBase(BaseModel):
    name: str
    type: EntityType
    description: str
    is_active: bool = True
    appearance_rank: str = "0|000000:"
    disappearance_rank: Optional[str] = None
    disappearance_status: Optional[str] = None

class EntityCreate(EntityBase):
    project_id: int
    aliases: List[str] = []

class EntityUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[EntityType] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    appearance_rank: Optional[str] = None
    disappearance_rank: Optional[str] = None
    disappearance_status: Optional[str] = None
    aliases: Optional[List[str]] = None

class EntityRead(BaseModel):
    id: int
    project_id: int
    name: str
    type: EntityType
    description: str
    is_active: bool
    appearance_rank: str
    disappearance_rank: Optional[str]
    disappearance_status: Optional[str]
    aliases: List[str]

    class Config:
        from_attributes = True
