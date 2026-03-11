from fastapi import APIRouter
from backend.crud import storyboard
from backend.models import StoryNode, StoryIRBlock

router = APIRouter()

@router.get("/nodes")
async def get_story_nodes(branch_id: str):
    nodes = await storyboard.list_story_nodes(branch_id)
    return {"nodes": nodes}

@router.post("/nodes")
async def create_story_node(node: StoryNode):
    created = await storyboard.create_story_node(node)
    return {"status": "created", "node": created}

@router.get("/chapters/{chapter_id}/blocks")
async def get_chapter_blocks(chapter_id: str):
    blocks = await storyboard.list_story_ir_blocks(chapter_id)
    return {"blocks": blocks}

@router.patch("/blocks/{block_id}")
async def patch_story_block(block_id: str, payload: dict):
    content_html = payload.get("content_html", "")
    success = await storyboard.update_ir_block_html(block_id, content_html)
    return {"status": "patched" if success else "not_found"}
