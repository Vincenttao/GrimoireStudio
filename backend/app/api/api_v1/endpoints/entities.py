from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlmodel import select, delete

from app.api import deps
from app.models.entity import Entity, EntityAlias, EntityRelationship
from app.models.project import Project
from app.models.user import User
from app.schemas.entity import EntityCreate, EntityRead, EntityUpdate

router = APIRouter()

def get_owned_entity(db: Session, entity_id: int, user_id: int) -> Entity:
    """
    Helper to fetch an entity only if it belongs to the user.
    """
    statement = select(Entity).join(Project).where(
        Entity.id == entity_id,
        Project.owner_id == user_id
    )
    entity = db.exec(statement).first()
    if not entity:
        # Return 404 to mask existence (SPEC 4.1)
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity

@router.post("/", response_model=EntityRead)
def create_entity(
    *,
    db: Session = Depends(deps.get_db),
    entity_in: EntityCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # Verify project ownership
    project = db.exec(select(Project).where(
        Project.id == entity_in.project_id, 
        Project.owner_id == current_user.id
    )).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_obj = Entity(
        project_id=entity_in.project_id,
        name=entity_in.name,
        type=entity_in.type,
        description=entity_in.description,
        is_active=entity_in.is_active,
        appearance_rank=entity_in.appearance_rank,
        disappearance_rank=entity_in.disappearance_rank,
        disappearance_status=entity_in.disappearance_status,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Add aliases
    for alias_str in entity_in.aliases:
        alias_obj = EntityAlias(
            entity_id=db_obj.id,
            alias=alias_str,
            normalized_alias=alias_str.lower().strip()
        )
        db.add(alias_obj)
    db.commit()
    db.refresh(db_obj)

    return EntityRead(
        **db_obj.dict(),
        aliases=[a.alias for a in db_obj.alias_entries]
    )

@router.get("/{entity_id}", response_model=EntityRead)
def read_entity(
    *,
    db: Session = Depends(deps.get_db),
    entity_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    entity = get_owned_entity(db, entity_id, current_user.id)
    return EntityRead(
        **entity.dict(),
        aliases=[a.alias for a in entity.alias_entries]
    )

@router.put("/{entity_id}", response_model=EntityRead)
def update_entity(
    *,
    db: Session = Depends(deps.get_db),
    entity_id: int,
    entity_in: EntityUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    entity = get_owned_entity(db, entity_id, current_user.id)
    
    update_data = entity_in.dict(exclude_unset=True)
    
    # Handle Aliases via Set Arithmetic (SPEC 2.3.C)
    if "aliases" in update_data:
        new_aliases = set(update_data.pop("aliases"))
        current_alias_objs = db.exec(select(EntityAlias).where(EntityAlias.entity_id == entity_id)).all()
        current_aliases = {a.alias for a in current_alias_objs}

        to_add = new_aliases - current_aliases
        to_remove = current_aliases - new_aliases

        # Safe Deletion: Must limit scope to this entity_id
        if to_remove:
            stmt = delete(EntityAlias).where(
                EntityAlias.entity_id == entity_id,
                EntityAlias.alias.in_(list(to_remove))
            )
            db.exec(stmt)

        # Insertion
        for a in to_add:
            db.add(EntityAlias(
                entity_id=entity_id,
                alias=a,
                normalized_alias=a.lower().strip()
            ))

    # Update other fields
    for field in update_data:
        setattr(entity, field, update_data[field])

    db.add(entity)
    db.commit()
    db.refresh(entity)

    return EntityRead(
        **entity.dict(),
        aliases=[a.alias for a in entity.alias_entries]
    )

@router.delete("/{entity_id}")
def delete_entity(
    *,
    db: Session = Depends(deps.get_db),
    entity_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    entity = get_owned_entity(db, entity_id, current_user.id)
    # Cascading delete usually handled by relationship or manual
    # For now manual cleanup of aliases
    db.exec(delete(EntityAlias).where(EntityAlias.entity_id == entity_id))
    db.delete(entity)
    db.commit()
    return {"status": "success"}
