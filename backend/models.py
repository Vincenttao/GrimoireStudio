from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ==========================================
# §1.11 VoiceSignature — V1.1 Web Novel Author Edition
# ==========================================


class VoiceSignature(BaseModel):
    """
    Grep-level OOC drift detector for characters in web novels.
    Catchphrases / honorifics / forbidden words — rule-based, no LLM cost.
    """

    catchphrases: List[str] = Field(default_factory=list, description="口头禅。每 N 章至少出现一次")
    catchphrase_min_freq_chapters: int = Field(default=10, description="口头禅频次下限窗口（章）")
    honorifics: Dict[str, str] = Field(
        default_factory=dict,
        description='{对象类型/实体ID: 使用的称谓} 如 {"长辈": "您", "平辈": "你"}',
    )
    forbidden_words: List[str] = Field(
        default_factory=list, description="角色绝不说的词（硬约束，命中阻断 Commit）"
    )
    sample_utterances: List[str] = Field(
        default_factory=list, description="3-5 条作者手动标定的范本台词"
    )
    tone_keywords: List[str] = Field(
        default_factory=list, description='常用语气副词（"便""倒是""罢了"等）'
    )


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
    voice_signature: Optional[VoiceSignature] = Field(
        default=None,
        description="V1.1: 角色声音签名，用于 Scribe 规则级 OOC 检测。非 CHARACTER 类型可为 None",
    )
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
# §1.10 BeatType — V1.1 Web Novel Author Edition
# ==========================================


class BeatType(str, Enum):
    """
    Maestro 按 beat_type 专项判完成，替代 V1.0 通用张力评分。
    术语直取网文生态，对齐作者语言。
    """

    SHOW_OFF_FACE_SLAP = "SHOW_OFF_FACE_SLAP"  # 装逼打脸
    PAYOFF = "PAYOFF"  # 爽点兑现
    SUSPENSE_SETUP = "SUSPENSE_SETUP"  # 悬念铺垫
    EMOTIONAL_CLIMAX = "EMOTIONAL_CLIMAX"  # 情感升华
    POWER_REVEAL = "POWER_REVEAL"  # 金手指展示
    REVERSAL = "REVERSAL"  # 反转
    WORLDBUILDING = "WORLDBUILDING"  # 世界观补完
    DAILY_SLICE = "DAILY_SLICE"  # 日常流


BEAT_TYPE_CRITERIA: Dict[BeatType, str] = {
    BeatType.SHOW_OFF_FACE_SLAP: (
        "判据：(1) 主角是否展示了具体能力/态度/资源（必需）；"
        "(2) 反派/对立方是否明确被挫，需有外显文字——表情/动作/台词（必需）；"
        "(3) 双方地位反差是否可感知（必需）。"
    ),
    BeatType.PAYOFF: ("判据：前期铺垫的冲突/承诺是否在本 Beat 明确兑现，读者期待是否有回报事件。"),
    BeatType.SUSPENSE_SETUP: (
        "判据：是否已埋下可追溯的未解冲突/未揭示信息，章末读者应有明确的'后续想看'诉求。"
    ),
    BeatType.EMOTIONAL_CLIMAX: (
        "判据：是否出现角色情感外化的关键对白/动作，情绪冲突是否推到临界点。"
    ),
    BeatType.POWER_REVEAL: (
        "判据：主角金手指/新能力是否展示并被场上其他角色见证，效果是否具备碾压性。"
    ),
    BeatType.REVERSAL: ("判据：是否出现明确的形势翻转——强弱易位/信息反转/立场转向，需有文字锚点。"),
    BeatType.WORLDBUILDING: (
        "判据：是否有新的世界观信息曝光，至少 2 条可抽取为 Grimoire 条目的事实。"
    ),
    BeatType.DAILY_SLICE: ("判据：达到目标字数即可收束，无硬性戏剧要素要求。"),
}


# ==========================================
# §1.3 The Spark (V1.1 扩展 beat_type + target_char_count)
# ==========================================


class TheSpark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spark_id: str
    chapter_id: str
    user_prompt: str
    overrides: Dict[str, str] = Field(default_factory=dict)
    # V1.1 新增
    beat_type: BeatType = Field(
        default=BeatType.DAILY_SLICE,
        description="V1.1: 声明本 Spark 属于哪类戏剧 Beat，供 Maestro 专项判完成",
    )
    target_char_count: int = Field(
        default=3000,
        ge=500,
        le=20000,
        description="V1.1: 章节/场景目标字数，Camera 渲染时作为硬约束",
    )


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
    # V1.1 新增
    target_char_count: Optional[int] = Field(
        default=None,
        ge=500,
        le=20000,
        description="V1.1: 目标字数硬约束。Camera 输出后按 ±tolerance_ratio 判定是否需要 expand/shrink",
    )
    max_sent_len: Optional[int] = Field(
        default=None,
        ge=10,
        le=100,
        description="V1.1: 最大句长（平台预设注入，番茄/七猫类短句平台需要）",
    )
    tolerance_ratio: float = Field(
        default=0.10, ge=0.0, le=0.5, description="字数容差比例（默认 ±10%）"
    )
    adjust_mode: Optional[str] = Field(
        default=None,
        description="字数调整模式：'expand' | 'shrink'。首轮渲染为 None；重试时由内部填充",
    )


# ==========================================
# §1.7 Maestro Output Definitions
# ==========================================


class MaestroDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    next_actor_id: Optional[str] = None
    is_beat_complete: bool
    reasoning: str
    # V1.1: 缺失要素反馈，帮助调试和 UI 提示作者
    missing_requirements: List[str] = Field(
        default_factory=list, description="V1.1: beat_type 判据下尚未满足的要素"
    )


class MaestroEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    reject_reason: Optional[str] = None
    tension_score: int = Field(ge=0, le=100)


class HookGuardResult(BaseModel):
    """V1.1: Ending Hook Guard 检测输出。"""

    model_config = ConfigDict(extra="forbid")

    has_hook: bool
    hook_type: Optional[str] = Field(
        default=None,
        description="'未解冲突' | '新入场' | '反转' | '悬念对白' | None",
    )
    reason: str = Field(description="判定理由，用于 UI 提示作者")


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


# ==========================================
# §1.15 PlatformProfile — V1.1 网文平台预设
# ==========================================


class PlatformProfile(str, Enum):
    """目标平台 — 决定 Render Mixer 默认值。"""

    QIDIAN = "QIDIAN"  # 起点中文网 — 爽文 / 打脸 / 热血
    FANQIE = "FANQIE"  # 番茄小说 — 短句 / 节奏快 / 爽点密集
    JINJIANG = "JINJIANG"  # 晋江文学城 — 情感 / 细腻 / 心理描写
    ZONGHENG = "ZONGHENG"  # 纵横中文网 — 权谋 / 军事 / 历史
    QIMAO = "QIMAO"  # 七猫 / 飞卢 — 短平快 / 流水账爽文
    CUSTOM = "CUSTOM"  # 自定义


PLATFORM_PRESETS: Dict[PlatformProfile, Dict[str, Any]] = {
    PlatformProfile.QIDIAN: {
        "subtext_ratio": 0.2,
        "style_template": "热血爽文",
        "max_sent_len": 30,
        "default_char_count": 3000,
        "scene_pacing_hint": "高能章每 3 章 1 次",
    },
    PlatformProfile.FANQIE: {
        "subtext_ratio": 0.15,
        "style_template": "快节奏爽文",
        "max_sent_len": 20,
        "default_char_count": 2500,
        "scene_pacing_hint": "每章至少 1 个爽点",
    },
    PlatformProfile.JINJIANG: {
        "subtext_ratio": 0.6,
        "style_template": "江南烟雨",
        "max_sent_len": 40,
        "default_char_count": 4000,
        "scene_pacing_hint": "情感线优先",
    },
    PlatformProfile.ZONGHENG: {
        "subtext_ratio": 0.3,
        "style_template": "肃杀权谋",
        "max_sent_len": 35,
        "default_char_count": 3500,
        "scene_pacing_hint": "伏笔为主",
    },
    PlatformProfile.QIMAO: {
        "subtext_ratio": 0.1,
        "style_template": "白开水爽文",
        "max_sent_len": 18,
        "default_char_count": 2000,
        "scene_pacing_hint": "每段一个小爽点",
    },
    PlatformProfile.CUSTOM: {
        "subtext_ratio": 0.5,
        "style_template": "Standard",
        "max_sent_len": 30,
        "default_char_count": 3000,
        "scene_pacing_hint": "自定义",
    },
}


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
    # V1.1 新增
    target_platform: PlatformProfile = Field(
        default=PlatformProfile.QIDIAN, description="V1.1: 目标平台预设"
    )
    default_target_char_count: int = Field(default=3000, description="V1.1: 默认章节字数")
    default_max_sent_len: int = Field(default=30, description="V1.1: 默认最大句长")
    ending_hook_guard_enabled: bool = Field(default=True, description="V1.1: 钩子守卫开关")
    padding_detector_enabled: bool = Field(default=True, description="V1.1: 水字数检测开关")
    daily_streak_count: int = Field(default=0, description="V1.1: 连续日更天数")
    last_commit_at: Optional[datetime] = Field(
        default=None, description="V1.1: 上次 Commit 时间（超过 24h 重置 streak）"
    )


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
    # V1.1 新增
    CHAR_COUNT_ADJUST = "CHAR_COUNT_ADJUST"
    HOOK_GUARDING = "HOOK_GUARDING"
    HOOK_REFINING = "HOOK_REFINING"
    VOICE_CHECKING = "VOICE_CHECKING"

    COMMITTED = "COMMITTED"
    INTERRUPTED = "INTERRUPTED"


# ==========================================
# §1.13 SoftPatch — V1.1 软层 Delta（作者事实修订）
# ==========================================


class SoftPatchStatus(str, Enum):
    PENDING = "PENDING"
    MERGED = "MERGED"
    DISCARDED = "DISCARDED"


class SoftPatch(BaseModel):
    """
    作者手动修订事实的软层补丁。不改历史快照，只在当前快照上 overlay。
    下次 Commit 时合并进新快照。
    """

    model_config = ConfigDict(extra="forbid")

    patch_id: str
    target_entity_id: str
    target_path: str = Field(
        description='JSONPath，如 "current_status.inventory" 或 "base_attributes.personality"'
    )
    old_value: Any
    new_value: Any
    author_note: str = Field(description='作者改动原因，如"原文 3000 两错了，应该 300 两"')
    status: SoftPatchStatus = SoftPatchStatus.PENDING
    created_at: datetime
    merged_into_snapshot_id: Optional[str] = None


# ==========================================
# §1.14 Scene — V1.1 Chapter→Scene→IRBlock 三级层次
# ==========================================


class SceneState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    EMITTED = "EMITTED"
    COMMITTED = "COMMITTED"


class Scene(BaseModel):
    """Chapter 下的独立 Beat 闭环。一章可挂 1-N 个 Scene。"""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    chapter_id: str
    lexorank: str
    beat_type: BeatType
    spark_id: Optional[str] = None
    ir_block_id: Optional[str] = None
    state: SceneState = SceneState.PENDING
    created_at: datetime


# ==========================================
# §1.16 ChapterBeatLog — V1.1 爽点节奏表（V2.0 使用）
# ==========================================


class ChapterBeatLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_id: str
    lexorank: str
    beat_types: List[BeatType] = Field(default_factory=list)
    committed_at: datetime


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
