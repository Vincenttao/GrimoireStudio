from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.models import (
    BaseAttributes,
    CurrentStatus,
    Entity,
    EntityType,
    MaestroDecision,
    MaestroEvaluation,
    POVType,
    RenderRequest,
    ScribeExtractionResult,
)


def test_entity_validation_success():
    """Ensure a valid Entity object passes validation."""
    entity = Entity(
        entity_id="uuid-1234",
        type=EntityType.CHARACTER,
        name="John Doe",
        base_attributes=BaseAttributes(
            aliases=["Johnny"], personality="Brave", core_motive="Justice", background="A knight"
        ),
        current_status=CurrentStatus(
            health="Healthy",
            inventory=["Sword"],
            recent_memory_summary=["Fought a dragon"],
            relationships={"uuid-5678": "Friend"},
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    assert entity.name == "John Doe"


def test_maestro_decision_extra_fields_forbidden():
    """Ensure MaestroDecision rejects hallucinated extra fields (SPEC §7.1)."""
    with pytest.raises(ValidationError) as exc_info:
        MaestroDecision.model_validate(
            {
                "next_actor_id": "uuid-9999",
                "is_beat_complete": False,
                "reasoning": "Deciding who speaks next",
                "hallucinated_field": "This should not exist",
            }
        )
    assert "Extra inputs are not permitted" in str(exc_info.value)


def test_maestro_evaluation_tension_score_bounds():
    """Ensure MaestroEvaluation tension_score remains within 0-100 bounds."""
    # Test lower bound failure
    with pytest.raises(ValidationError):
        MaestroEvaluation(is_valid=True, tension_score=-1)

    # Test upper bound failure
    with pytest.raises(ValidationError):
        MaestroEvaluation(is_valid=True, tension_score=101)


def test_render_request_subtext_ratio_bounds():
    """Ensure RenderRequest subtext_ratio remains within 0.0-1.0 bounds."""
    with pytest.raises(ValidationError):
        RenderRequest(
            ir_block_id="block-1",
            pov_type=POVType.OMNISCIENT,
            style_template="Dark fantasy",
            subtext_ratio=1.5,
        )


def test_scribe_extraction_missing_required():
    """Ensure ScribeExtractionResult requires the correct structure."""
    with pytest.raises(ValidationError):
        # Missing 'delta' inside 'updates' item
        ScribeExtractionResult.model_validate({"updates": [{"entity_id": "uuid-1234"}]})
