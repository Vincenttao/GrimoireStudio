from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlmodel import select
from uuid import uuid4
from datetime import datetime

from app.api import deps
from app.models.chapter import Chapter, Block, NarrativeMode
from app.models.project import Project
from app.models.user import User
from app.schemas.generation import GenerationBeatRequest, GenerationBeatResponse
from app.schemas.smoothing import SmoothingRequest, SmoothingResponse
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.core.prompts.loader import render_prompt
from app.core.lexorank import lexorank

router = APIRouter()

# Mock idempotency cache
smoothing_cache = {}

@router.post("/smooth", response_model=SmoothingResponse)
async def smooth_transition(
    *,
    db: Session = Depends(deps.get_db),
    request: SmoothingRequest,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Smart Context Smoothing (SPEC 2.2)
    """
    # 1. Tenancy Check
    project = db.exec(select(Project).where(
        Project.id == request.project_id,
        Project.owner_id == current_user.id
    )).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Idempotency Check
    if request.idempotency_key in smoothing_cache:
        return smoothing_cache[request.idempotency_key]

    # 3. Edge Case: Empty next block
    if not request.next_block_text.strip():
        return {"needs_smoothing": False}

    # 4. Action: Call Smoothing Logic
    smoothed_text = await llm_service.smooth_transition(
        request.prev_block_text, 
        request.next_block_text
    )

    response = {
        "needs_smoothing": True,
        "smoothed_text": smoothed_text
    }

    # Cache result
    smoothing_cache[request.idempotency_key] = response
    
    return response

@router.post("/beat", response_model=GenerationBeatResponse)
async def generate_beat(
    *,
    db: Session = Depends(deps.get_db),
    request: GenerationBeatRequest,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    The Ritual (Generation Engine)
    """
    # 1. Anti-IDOR Validation (SPEC 2.1)
    statement = select(Chapter, Project).join(Project).where(
        Chapter.id == request.chapter_id,
        Project.owner_id == current_user.id
    )
    result = db.exec(statement).first()
    if not result:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    chapter, project = result

    # 2. RAG Assembly (SPEC 3.4)
    active_entities = rag_service.get_active_entities(db, project.id, request.anchor_block_rank)
    # Filter manual entities
    if request.manual_entity_ids:
        # TODO: Force fetch manual entities if not in active_entities
        pass
    
    relationships = rag_service.get_temporal_relationships(db, project.id, request.anchor_block_rank)
    
    # Prepare data for prompt (mapping to template expected structure)
    entities_data = [{"name": e.name, "description": e.description} for e in active_entities]
    # Simple mapping for relationships
    rel_data = []
    # In a real scenario, we'd fetch names for IDs
    
    # 3. Prompt Rendering
    template_map = {
        NarrativeMode.STANDARD: "standard.j2",
        NarrativeMode.CONFLICT: "conflict.j2",
        NarrativeMode.SENSORY: "sensory.j2",
        NarrativeMode.FOCUS: "focus.j2"
    }
    template_name = template_map.get(request.narrative_mode, "standard.j2")
    
    prompt = render_prompt(
        template_name,
        style_constraints=[], # TODO: Fetch from project settings
        style_anchors=[],     # TODO: Fetch from project settings
        preceding_context=request.preceding_context,
        active_entities=entities_data,
        relationships=rel_data
    )

    # 4. LLM Call
    llm_output = await llm_service.generate_beat(prompt)
    
    # 5. Post-processing (Inject IDs and Metadata)
    variants = []
    for v in llm_output["variants"]:
        variants.append({
            "id": str(uuid4()),
            "type": "ai",
            "label": v["label"],
            "text": v["text"],
            "style_tag": v["style_tag"],
            "model_id": "mock-v1",
            "prompt_version": f"v1.5-{request.narrative_mode}",
            "token_usage": 0,
            "created_at": datetime.utcnow().isoformat()
        })

    # 6. LexoRank Generation
    # Find the next rank after anchor
    generated_rank = lexorank.gen_next(request.anchor_block_rank)

    # 7. Metadata / Scrying Glass
    meta_info = {
        "scrying_glass": {
            "lookback_window_size": 2000, # Mock
            "rag_hits": [e.name for e in active_entities],
            "strategy_explanation": llm_output["strategy_summary"]
        }
    }

    return {
        "generated_rank": generated_rank,
        "schema_version": 1,
        "variants": variants,
        "meta_info": meta_info
    }
