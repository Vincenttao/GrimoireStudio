from typing import List, Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, JSON
from enum import Enum

if TYPE_CHECKING:
    from .project import Project

class EntityType(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    ITEM = "item"
    LORE = "lore"

class Entity(SQLModel, table=True):
    __tablename__: str = "entities"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    name: str
    type: EntityType
    description: str
    
    is_active: bool = Field(default=True)
    appearance_rank: str = Field(default="0|000000:", index=True)
    disappearance_rank: Optional[str] = Field(default=None, index=True)
    disappearance_status: Optional[str] = Field(default=None)

    project: "Project" = Relationship(back_populates="entities")
    alias_entries: List["EntityAlias"] = Relationship(back_populates="entity")

class EntityAlias(SQLModel, table=True):
    __tablename__: str = "entity_aliases"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_id: int = Field(foreign_key="entities.id", index=True)
    alias: str = Field(index=True)
    normalized_alias: str = Field(index=True)

    entity: Entity = Relationship(back_populates="alias_entries")

class EntityRelationship(SQLModel, table=True):
    __tablename__: str = "entity_relationships"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    source_entity_id: int = Field(foreign_key="entities.id")
    target_entity_id: int = Field(foreign_key="entities.id")
    
    relation_type: str
    description: str
    category: str = Field(default="general", index=True)
    
    start_rank: str = Field(index=True)
    end_rank: Optional[str] = Field(default=None, index=True)
