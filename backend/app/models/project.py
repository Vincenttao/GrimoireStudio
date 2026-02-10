from typing import List, Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

if TYPE_CHECKING:
    from .user import User
    from .entity import Entity
    from .chapter import Chapter

class Project(SQLModel, table=True):
    __tablename__: str = "projects"
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    owner: "User" = Relationship(back_populates="projects")
    entities: List["Entity"] = Relationship(back_populates="project")
    chapters: List["Chapter"] = Relationship(back_populates="project")
