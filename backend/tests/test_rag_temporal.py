import pytest
from sqlalchemy.orm import Session
from sqlmodel import Session as SQLModelSession
from app.db.session import engine
from app.models.entity import Entity, EntityRelationship, EntityType
from app.models.project import Project
from app.models.user import User
from app.services.rag_service import rag_service
from app.core import security

@pytest.fixture
def db():
    with SQLModelSession(engine) as session:
        yield session

def test_entity_lifecycle_visibility(db: Session):
    # Setup: User and Project
    user = User(email="ragtest@example.com", hashed_password="pw")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    project = Project(title="RAG Project", owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    # 1. Entity A appearance_rank: "0|c00000:"
    entity_a = Entity(
        project_id=project.id,
        name="Entity A",
        type=EntityType.CHARACTER,
        description="Test desc",
        appearance_rank="0|c00000:"
    )
    db.add(entity_a)
    db.commit()

    # Action: Query at current_rank = "0|b00000:" (Before)
    active = rag_service.get_active_entities(db, project.id, "0|b00000:")
    assert len(active) == 0

    # Action: Query at current_rank = "0|d00000:" (After)
    active = rag_service.get_active_entities(db, project.id, "0|d00000:")
    assert len(active) == 1
    assert active[0].name == "Entity A"

def test_temporal_relationship_regression(db: Session):
    # Find the project from previous test or create new
    user = db.query(User).filter(User.email == "ragtest@example.com").first()
    project = db.query(Project).filter(Project.owner_id == user.id).first()

    entity_a = db.query(Entity).filter(Entity.name == "Entity A").first()
    entity_b = Entity(
        project_id=project.id,
        name="Entity B",
        type=EntityType.CHARACTER,
        description="Test desc B"
    )
    db.add(entity_b)
    db.commit()
    db.refresh(entity_b)

    # 1. Global relationship: Enemy (permanent), category="social", start="0|000000:"
    rel_enemy = EntityRelationship(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="Enemy",
        description="Always enemies",
        category="social",
        start_rank="0|000000:"
    )
    db.add(rel_enemy)
    
    # 2. Temporary relationship: Ally (interval), category="social", start="0|m00000:", end="0|z00000:"
    rel_ally = EntityRelationship(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="Ally",
        description="Temporary alliance",
        category="social",
        start_rank="0|m00000:",
        end_rank="0|z00000:"
    )
    db.add(rel_ally)
    db.commit()

    # Assert (Rank "0|a00000:"): Only "Enemy" ("a" < "m")
    rels = rag_service.get_temporal_relationships(db, project.id, "0|a00000:")
    assert len(rels) == 1
    assert rels[0].relation_type == "Enemy"

    # Assert (Rank "0|r00000:"): Should be "Ally" (Winner because "m" > "0" in the same category)
    rels = rag_service.get_temporal_relationships(db, project.id, "0|r00000:")
    assert len(rels) == 1
    assert rels[0].relation_type == "Ally"

    # Assert (Rank "0|{"): "0|z..." < "0|{" (Assuming "{" is after "z"). 
    # Actually, z00000: end_rank means after that it's gone.
    # The query for Ally has: start_rank <= current and (end_rank == None or end_rank >= current)
    # At rank "0|zzzzzz", end_rank "0|z00000:" is NOT >= "0|zzzzzz".
    rels = rag_service.get_temporal_relationships(db, project.id, "0|zzzzzz")
    # Should regress back to Enemy? 
    # Wait, my query doesn't automatically fall back to Enemy if Ally expires, 
    # UNLESS Enemy also matches.
    # Enemy matches because start_rank "0|000000:" <= "0|zzzzzz" and end_rank is None.
    # But groupby(category) picks the one with MAX start_rank.
    # Ally's start_rank is "0|m00000:". Enemy's is "0|000000:".
    # So Ally STILL wins the Max(start_rank) if it matches.
    # If Ally DOES NOT match (because it's past end_rank), then ONLY Enemy matches.
    # So it naturally regresses.
    assert len(rels) == 1
    assert rels[0].relation_type == "Enemy"
