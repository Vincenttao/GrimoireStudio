from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime

# ==========================================
# §1.1 Entity - The Grimoire
# ==========================================


class EntityType(str, Enum):
    CHARACTER = "CHARACTER"
    FACTION = "FACTION"
    LOCATION = "LOCATION"
    ITEM = "ITEM"


class BaseAttributes(BaseModel):
    aliases: List[str] = Field(default_factory=list)
    personality: str
    core_motive: str
    background: str


class CurrentStatus(BaseModel):
    health: str
    inventory: List[str] = Field(default_factory=list)
    recent_memory_summary: List[str] = Field(
        default_factory=list,
        description="滑动窗口：后端仅保留最近 N 条，超限自动淘汰最旧条目",
    )
    relationships: Dict[str, str] = Field(default_factory=dict)


class Entity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    type: EntityType
    name: str
    base_attributes: BaseAttributes
    current_status: CurrentStatus
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime


# ==========================================
# §1.2 Story IR Block
# ==========================================


class SceneContext(BaseModel):
    location_id: str
    time_of_day: str


class ActionItem(BaseModel):
    actor_id: str = Field(description="UUID 或 'SYSTEM'")
    intent: str
    action: str
    dialogue: str


class StoryIRBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    chapter_id: str
    lexorank: str
    summary: str
    involved_entities: List[str]
    scene_context: SceneContext
    action_sequence: List[ActionItem]
    content_html: Optional[str] = None
    created_at: datetime


# ==========================================
# §1.3 The Spark
# ==========================================


class TheSpark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spark_id: str
    chapter_id: str
    user_prompt: str
    overrides: Dict[str, str] = Field(default_factory=dict)


# ==========================================
# §1.4 Snapshot & Branch
# ==========================================


class GrimoireStateJSON(BaseModel):
    entities: List[Entity] = Field(default_factory=list)


class GrimoireSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    branch_id: str
    parent_snapshot_id: Optional[str]
    triggering_block_id: str
    grimoire_state_json: GrimoireStateJSON
    created_at: datetime


class Branch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: str
    name: str
    origin_snapshot_id: Optional[str]
    parent_branch_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime


# ==========================================
# §1.5 StoryNode
# ==========================================


class StoryNodeType(str, Enum):
    VOLUME = "VOLUME"
    CHAPTER = "CHAPTER"


class StoryNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    branch_id: str
    type: StoryNodeType
    title: str
    summary: Optional[str] = None
    lexorank: str
    parent_node_id: Optional[str] = None


# ==========================================
# §1.6 RenderRequest
# ==========================================


class POVType(str, Enum):
    OMNISCIENT = "OMNISCIENT"
    FIRST_PERSON = "FIRST_PERSON"
    CHARACTER_LIMITED = "CHARACTER_LIMITED"


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ir_block_id: str
    pov_type: POVType
    pov_character_id: Optional[str] = None
    style_template: str
    subtext_ratio: float = Field(ge=0.0, le=1.0)


# ==========================================
# §1.7 Maestro Output Definitions
# ==========================================


class MaestroDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_actor_id: Optional[str] = None
    is_beat_complete: bool
    reasoning: str


class MaestroEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    reject_reason: Optional[str] = None
    tension_score: int = Field(ge=0, le=100)


# ==========================================
# §1.8 Character Output Definition
# ==========================================


class CharacterAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str
    action: str
    dialogue: str


# ==========================================
# §1.9 Scribe Output Definitions
# ==========================================


class InventoryChanges(BaseModel):
    added: List[str] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list)


class ScribeMemoryDelta(BaseModel):
    inventory_changes: InventoryChanges
    health_delta: Optional[str] = None
    memory_to_append: Optional[str] = None
    relationship_changes: Dict[str, str] = Field(default_factory=dict)


class DeltaUpdate(BaseModel):
    entity_id: str
    delta: ScribeMemoryDelta


class ScribeExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updates: List[DeltaUpdate] = Field(default_factory=list)


# ==========================================
# §1.10 ProjectSettings
# ==========================================


class LLMApiKeys(BaseModel):
    openai: Optional[str] = None
    anthropic: Optional[str] = None
    deepseek: Optional[str] = None


class ModelRouting(BaseModel):
    """
    High/Low 模型路由配置。
    推演层使用低成本快速模型，渲染层使用高质量创意模型。
    """

    maestro_model: str = Field(default="gpt-4", description="Maestro 决策模型 - 需要强推理能力")
    character_model: str = Field(
        default="gpt-3.5-turbo", description="Character 对话模型 - 追求低成本快速响应"
    )
    camera_model: str = Field(
        default="gpt-4", description="Camera 渲染模型 - 需要高质量文学创作能力"
    )


class DefaultRenderMixer(BaseModel):
    pov_type: str
    style_template: str
    subtext_ratio: float = Field(default=0.5, ge=0.0, le=1.0)


class ProjectSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = "single_row_lock"
    llm_model: str = "gpt-4"  # 保留作为默认值，优先使用 model_routing
    model_routing: Optional[ModelRouting] = Field(
        default=None, description="高/低模型路由配置。若设置，将覆盖 llm_model"
    )
    llm_api_keys: LLMApiKeys
    llm_api_base: Optional[str] = Field(
        default=None,
        description="自定义 API 端点 URL，如阿里云 DashScope 的 OpenAI 兼容地址。留空则使用模型供应商默认端点",
    )
    max_turns: int = 12
    tension_threshold: float = 0.8
    default_render_mixer: DefaultRenderMixer


# ==========================================
# §2.1 Sandbox State Enum
# ==========================================


class SandboxState(str, Enum):
    IDLE = "IDLE"
    SPARK_RECEIVED = "SPARK_RECEIVED"
    REASONING = "REASONING"
    CALLING_CHARACTER = "CALLING_CHARACTER"
    EVALUATING = "EVALUATING"
    EMITTING_IR = "EMITTING_IR"
    RENDERING = "RENDERING"
    COMMITTED = "COMMITTED"
    INTERRUPTED = "INTERRUPTED"


# ==========================================
# §4.3 Error Response Schema
# ==========================================


class ErrorCode(str, Enum):
    ERR_CUT = "ERR_CUT"
    ERR_SYS = "ERR_SYS"
    ERR_NET_TIMEOUT = "ERR_NET_TIMEOUT"
    ERR_WORLD_REJECT = "ERR_WORLD_REJECT"
    ERR_SAFETY_BLOCK = "ERR_SAFETY_BLOCK"
    ERR_VALIDATION = "ERR_VALIDATION"


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    details: Optional[Dict[str, str]] = None
    recoverable: bool = Field(
        default=True, description="是否可恢复。True=用户可重试，False=需要人工干预"
    )
    retry_count: int = Field(default=0, ge=0)
