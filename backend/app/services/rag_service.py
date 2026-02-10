from typing import List, Optional
from sqlalchemy.orm import Session
from sqlmodel import select, and_, or_
from app.models.entity import Entity, EntityRelationship, EntityAlias
from itertools import groupby

class RAGService:
    @staticmethod
    def get_active_entities(db: Session, project_id: int, current_rank: str) -> List[Entity]:
        """
        Existence Logic (SPEC 3.4.1):
        Active if appearance_rank <= current_rank <= disappearance_rank (if exists)
        """
        statement = select(Entity).where(
            Entity.project_id == project_id,
            Entity.is_active == True,
            Entity.appearance_rank <= current_rank,
            or_(
                Entity.disappearance_rank == None,
                Entity.disappearance_rank >= current_rank
            )
        )
        return db.exec(statement).all()

    @staticmethod
    def get_temporal_relationships(db: Session, project_id: int, current_rank: str) -> List[EntityRelationship]:
        """
        Temporal Relationship Logic (SPEC 3.4):
        1. Range: start_rank <= current_rank
        2. Deduplication: groupby(category)
        3. Best Selection: max(start_rank) in each category
        """
        # Join with Entity to ensure we only get relationships for the current project
        statement = select(EntityRelationship).join(
            Entity, EntityRelationship.source_entity_id == Entity.id
        ).where(
            Entity.project_id == project_id,
            EntityRelationship.start_rank <= current_rank,
            or_(
                EntityRelationship.end_rank == None,
                EntityRelationship.end_rank >= current_rank
            )
        ).order_by(EntityRelationship.category, EntityRelationship.start_rank.desc())

        results = db.exec(statement).all()
        
        # Deduplication logic (擇优选取: String Max of start_rank per category)
        final_relationships = []
        for category, items in groupby(results, key=lambda x: x.category):
            # Since we ordered by category and start_rank DESC, the first item in each group is the winner
            final_relationships.append(list(items)[0])
            
        return final_relationships

rag_service = RAGService()
