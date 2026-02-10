import pytest
from app.core.prompts.loader import render_prompt

def test_prompt_inheritance():
    # Test rendering sensory mode
    prompt = render_prompt(
        "sensory.j2",
        style_constraints=["No passive voice"],
        style_anchors=["He looked at the sky."],
        preceding_context="The portal opened.",
        active_entities=[{"name": "Alice", "description": "A mage"}],
        relationships=[]
    )
    
    # Assert XML tags from base
    assert "<system_role>" in prompt
    assert "<style_guardrails>" in prompt
    assert "<style_anchors>" in prompt
    assert "<context>" in prompt
    assert "<narrative_mode_instruction>" in prompt
    assert "<output_format>" in prompt
    
    # Assert sensory specific content
    assert "CURRENT MODE: SENSORY" in prompt
    assert "Visual" in prompt
    assert "Auditory" in prompt
    assert "Tactile" in prompt
    
    # Assert data injection
    assert "No passive voice" in prompt
    assert "The portal opened." in prompt
    assert "Alice" in prompt

def test_json_requirement_in_prompt():
    prompt = render_prompt("standard.j2", 
        style_constraints=[], style_anchors=[], preceding_context="", 
        active_entities=[], relationships=[]
    )
    assert "Return a valid JSON object" in prompt
    assert '"variants":' in prompt
