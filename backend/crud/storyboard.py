from typing import List, Optional
from backend.models import StoryNode, StoryNodeType, StoryIRBlock, SceneContext, ActionItem
from backend.database import get_db_connection
import json
from datetime import datetime

# ==========================================
# StoryNode CRUD
# ==========================================

async def create_story_node(node: StoryNode) -> StoryNode:
    async with get_db_connection() as conn:
        await conn.execute(
            '''
            INSERT INTO story_nodes (node_id, branch_id, type, title, summary, lexorank, parent_node_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                node.node_id, 
                node.branch_id, 
                node.type.value, 
                node.title, 
                node.summary, 
                node.lexorank, 
                node.parent_node_id
            )
        )
        await conn.commit()
    return node

async def list_story_nodes(branch_id: str) -> List[StoryNode]:
    nodes = []
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM story_nodes WHERE branch_id = ? ORDER BY lexorank ASC", 
            (branch_id,)
        )
        rows = await cursor.fetchall()
        for row in rows:
            nodes.append(StoryNode(
                node_id=row['node_id'],
                branch_id=row['branch_id'],
                type=StoryNodeType(row['type']),
                title=row['title'],
                summary=row['summary'],
                lexorank=row['lexorank'],
                parent_node_id=row['parent_node_id']
            ))
    return nodes

# ==========================================
# StoryIRBlock CRUD
# ==========================================

async def create_story_ir_block(block: StoryIRBlock) -> StoryIRBlock:
    async with get_db_connection() as conn:
        await conn.execute(
            '''
            INSERT INTO story_ir_blocks (
                block_id, chapter_id, lexorank, summary, 
                involved_entities_json, scene_context_json, 
                action_sequence_json, content_html, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                block.block_id,
                block.chapter_id,
                block.lexorank,
                block.summary,
                json.dumps(block.involved_entities),
                block.scene_context.model_dump_json(),
                json.dumps([a.model_dump() for a in block.action_sequence]),
                block.content_html,
                block.created_at.isoformat()
            )
        )
        await conn.commit()
    return block

async def update_ir_block_html(block_id: str, content_html: str) -> bool:
    """Updates the final prose of an IR Block (used by Render Pipeline or User Edit)."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE story_ir_blocks SET content_html = ? WHERE block_id = ?",
            (content_html, block_id)
        )
        await conn.commit()
        return cursor.rowcount > 0

async def list_story_ir_blocks(chapter_id: str) -> List[StoryIRBlock]:
    blocks = []
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM story_ir_blocks WHERE chapter_id = ? ORDER BY lexorank ASC", 
            (chapter_id,)
        )
        rows = await cursor.fetchall()
        for row in rows:
            # Reconstruct nested lists
            action_dicts = json.loads(row['action_sequence_json'])
            action_sequence = [ActionItem(**a) for a in action_dicts]
            
            blocks.append(StoryIRBlock(
                block_id=row['block_id'],
                chapter_id=row['chapter_id'],
                lexorank=row['lexorank'],
                summary=row['summary'],
                involved_entities=json.loads(row['involved_entities_json']),
                scene_context=SceneContext.model_validate_json(row['scene_context_json']),
                action_sequence=action_sequence,
                content_html=row['content_html'],
                created_at=datetime.fromisoformat(row['created_at'])
            ))
    return blocks
