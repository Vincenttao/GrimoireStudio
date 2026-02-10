from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, JSON, text
from datetime import datetime
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field as PydanticField

if TYPE_CHECKING:
    from .project import Project

class NarrativeMode(str, Enum): 
    STANDARD = "standard"
    CONFLICT = "conflict_injector"
    SENSORY = "sensory_lens"
    FOCUS = "focus_beam"

class Chapter(SQLModel, table=True):
    __tablename__: str = "chapters"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id")
    title: str
    rank: str = Field(default="0|h00000:", index=True)
    
    content_blocks: List["Block"] = Relationship(back_populates="chapter")
    project: "Project" = Relationship(back_populates="chapters")

class BlockType(str, Enum):
    TEXT = "text"
    SCENE_BREAK = "scene_break"

class VariantType(str, Enum): 
    AI_GENERATED = "ai" 
    USER_CUSTOM = "user"

class Variant(BaseModel):
    id: str = PydanticField(default_factory=lambda: str(uuid4())) 
    type: VariantType = VariantType.AI_GENERATED
    label: str 
    text: str 
    is_edited: bool = False
    style_tag: str 
    model_id: str 
    prompt_version: str 
    token_usage: int 
    created_at: datetime = PydanticField(default_factory=datetime.utcnow)

class Block(SQLModel, table=True):
    __tablename__: str = "blocks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    chapter_id: int = Field(foreign_key="chapters.id")
    rank: str = Field(default="0|h00000:", index=True)
    type: str = Field(default="text")
    
    variants: List[Dict[str, Any]] = Field(default_factory=list, sa_type=JSON)
    schema_version: int = Field(default=1)
    selected_variant_index: int = Field(default=0)
    content_snapshot: str = Field(default="")
    
    meta_info: Dict[str, Any] = Field( 
        default_factory=dict, 
        sa_type=JSON, 
        sa_column_kwargs={"server_default": text("'{}'::jsonb"), "nullable": False} 
    )
    
    chapter: Chapter = Relationship(back_populates="content_blocks")
