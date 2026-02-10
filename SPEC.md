# Project Specification: Grimoire Studio (v1.5) - Project Alchemist
**文档状态:** Final (Feature Complete)
**架构模式:** Control-First (FastAPI + Raw SDK + SQLModel + JWT Auth)
 
---
## 0. 技术栈与环境规范 (Tech Stack & Environment)
- **Backend:** Python 3.11+, FastAPI (Async), PostgreSQL 15+ (`pgvector`), SQLModel.
- **Security:** `python-jose` (JWT), `passlib[bcrypt]`.
- **AI Service:** OpenAI Python SDK (Compatible with OpenRouter/DeepSeek).
- **Prompt Engine:** **Jinja2** (逻辑与模板分离，严格禁止代码硬编码 Prompt).
- **Ordering Algorithm:** **LexoRank** (Custom implementation or library). 用于实现 O(1) 复杂度的列表重排与插入，替代浮点数排序。
- **Retry Policy:** `tenacity` (用于 AI 服务熔断与重试).
- **Frontend:** React 18+, TypeScript, Vite, 
	- **Editor Engine:** **Tiptap** (Headless, ProseMirror core). **Single Source of Truth for Content.**
	- **Global State:** **Zustand** (仅负责 Auth, UI Flags, Project Metadata, Debug Info，**不存储文档内容**).
- - **UI Components:** TailwindCSS + Shadcn/ui.
- **i18n:** `i18next` (Namespace 结构).
---
## 1. 数据模型 (Data Models)
> **指令:** 以下模型支持多租户隔离、叙事风格锚点及“老虎机”变体存储。后端模型保持不变，前端通过 JSON 序列化与后端交互。
### 1.1 Identity & Project (SaaS Layer)
``` python
from typing import List, Optional, Dict
from sqlmodel import Field, SQLModel, Relationship, JSON
from datetime import datetime
from enum import Enum

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    projects: List["Project"] = Relationship(back_populates="owner")

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True) 
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Negative Constraints (Style Guardrails)
    # e.g. ["No passive voice", "No modern slang", "No breaking 4th wall"]
    style_constraints: List[str] = Field(default_factory=list, sa_type=JSON)
    style_profiles: List[StyleProfile] = Relationship(back_populates="project")

    owner: User = Relationship(back_populates="projects")
    chapters: List["Chapter"] = Relationship(back_populates="project")
    entities: List["Entity"] = Relationship(back_populates="project")
    
class StyleProfile(SQLModel, table=True): 
	id: Optional[int] = Field(default=None, primary_key=True) 
	project_id: int = Field(foreign_key="project.id", index=True) 
	name: str description: Optional[str] 
	is_active: bool = Field(default=False) 
	# 当前激活的风格 
	project: "Project" = Relationship(back_populates="style_profiles") 
	examples: List["StyleExample"] = Relationship(back_populates="profile") 
# [新增] 具体的风格片段 (RAG Unit) 

class StyleExample(SQLModel, table=True): 
	id: Optional[int] = Field(default=None, primary_key=True) 
	profile_id: int = Field(foreign_key="styleprofile.id", index=True) 
	text: str 	# The actual few-shot example 
	# [Critical] 用于 RAG 的向量嵌入 (需开启 pgvector) 
	# embedding: List[float] = Field(sa_column=Column(Vector(1536))) 
	# 元数据: ["dialogue", "action", "introspection"] 
	tags: List[str] = Field(default_factory=list, sa_type=JSON)
	profile: StyleProfile = Relationship(back_populates="examples")
```
### 1.2 Narrative Structure (The Slot Machine)

```python
class NarrativeMode(str, Enum): 
	STANDARD = "standard" # Mode A 
	CONFLICT = "conflict_injector" # Mode B 
	SENSORY = "sensory_lens" # Mode C 
	FOCUS = "focus_beam" # Mode D 


class Chapter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    title: str
    

    # 格式示例: "0|h00000:" (Bucket | Rank)
    # 优势: 支持无限细分插入，避免浮点数精度耗尽，支持 O(1) 重排
    rank: str = Field(default="0|h00000:", index=True)
    
    content_blocks: List["Block"] = Relationship(back_populates="chapter")
    project: Project = Relationship(back_populates="chapters")

class BlockType(str, Enum):
    TEXT = "text"
    SCENE_BREAK = "scene_break"
    
class VariantType(str, Enum): 
	AI_GENERATED = "ai" 
	USER_CUSTOM = "user"
    
class Variant(BaseModel): """ JSON Payload Schema for Slot Machine Variants. """ 
	id: str = PydanticField(default_factory=lambda: str(uuid4())) 
	type: VariantType = Field(default=VariantType.AI_GENERATED)
	label: str 
	text: str 
	is_edited: bool = Field(default=False) # [新增] 用于UI显示 "Edited" 标记
	style_tag: str 
	model_id: str 
	prompt_version: str 
	token_usage: int 
	created_at: datetime = PydanticField(default_factory=datetime.utcnow)

class Block(SQLModel, table=True):
    """
    Slot Machine Core Unit.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    chapter_id: int = Field(foreign_key="chapter.id")
    
    # Ranking for O(1) reordering
    rank: str = Field(default="0|h00000:", index=True)
	type: str = Field(default="text") # 简化 Enum 为 str 或保持 Enum
    
    # 【Critical Change】: 存储结构化变体 
    # Schema: List[Dict] 
	variants: List[Variant] = Field(default_factory=list, sa_type=JSON)
	
	# 用于识别历史数据结构，支持未来的平滑逻辑转换
	schema_version: int = Field(default=1)
    selected_variant_index: int = Field(default=0)
    
    # 冗余快照 (Snapshot): RAG 与上下文检索的核心优化
    # 作用: 存储当前选中的变体文本 (或用户手动编辑后的最终文本)。
    # 目的: 允许后端通过简单 SQL 直接组装 Lookback Window，避免遍历 JSON 数组带来的性能开销。
    # 约束: 每次更新 selected_variant_index 或编辑内容时，必须同步更新此字段。
	content_snapshot: str = Field(default="")
    
    # 用于存储额外元数据 (Scrying Glass 数据, 调试信息等)
    # 结构规范: { "scrying_glass": { "rag_hits": [...], ... } }
    # 前端 Tiptap attributes: { meta_info: { scrying_glass: { ... } } }
	meta_info: Dict[str, Any] = Field( 
		default_factory=dict, 
		sa_type=JSON, 
		sa_column_kwargs={"server_default": text("'{}'::jsonb"), "nullable": False} 
	)
    chapter: Chapter = Relationship(back_populates="content_blocks")
    
    class Variant(BaseModel): 
	    """ 
	    [新增] 变体原子单位：支持溯源、计费统计与埋点追踪。 
	    """ 
	    id: str = Field(default_factory=lambda: str(uuid4())) 
	    label: str # UI 显示标签 (例如: "Action Focus") 
	    text: str # 变体正文内容 
	    style_tag: str # 内部策略标签 (例如: "Fast Paced") 
	    # --- 溯源与审计元数据 (Glass Box 愿景支撑) --- 
	    model_id: str # 生成该变体的模型 ID (例如: "deepseek-reasoner", "claude-3-5-sonnet") 
	    prompt_version: str # 关联的 Jinja2 模板版本号或哈希 (例如: "v1.5-sensory-lens") 
	    token_usage: int # 本次生成消耗的 Total Tokens (用于成本核算) 
	    created_at: datetime = Field(default_factory=datetime.utcnow)
```
### 1.3 The Grimoire (Dynamic Entities)
``` python
class EntityType(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    ITEM = "item"
    LORE = "lore"

class Entity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    name: str
    type: EntityType
    description: str
    project: Project = Relationship(back_populates="entities")
    alias_entries: List["EntityAlias"] = Relationship()
    
    # 实体状态定义
    is_active: bool = Field(default=True) # 基础开关
    # 生命周期区间 (基于 Chapter Rank) 
    # appearance_rank: 首次登场（用于过滤掉尚未出场的角色） 
    # disappearance_rank: 离场/去世（用于过滤掉已退场的角色） 
    appearance_rank: str = Field(default="0|000000:", index=True) 
    disappearance_rank: Optional[str] = Field(default=None, index=True) 
    # 退场状态描述 (例如: "Deceased", "Missing", "Exiled") 
    disappearance_status: Optional[str] = Field(default=None)

class EntityRelationship(SQLModel, table=True):
    """Supports Multi-identity & Temporal Scope"""
    id: Optional[int] = Field(default=None, primary_key=True)
    source_entity_id: int = Field(foreign_key="entity.id")
    target_entity_id: int = Field(foreign_key="entity.id")
    
	relation_type: str # 例如: "Enemy", "Temporary Ally" 
	description: str
    # 关系类别：用于逻辑去重
    # 例如：'Social' (社交), 'Professional' (职业), 'Romantic' (情感)
    category: str = Field(default="general", index=True)
	# 作用区间 (基于 Chapter Rank - LexoRank Format)
    # 数据类型严格强制为 str，禁止使用 float
	start_rank: str = Field(index=True, description="LexoRank string (e.g. '0|h00000:')")
    end_rank: Optional[str] = Field(default=None, index=True, description="LexoRank string")

class EntityAlias(SQLModel, table=True): 
	id: Optional[int] = Field(default=None, primary_key=True) 
	entity_id: int = Field(foreign_key="entity.id", index=True) 
	# 核心字段：存储 "Batman", "The Dark Knight", "Bruce" 
	# 必须加索引，用于快速查找 
	alias: str = Field(index=True) 
	# 归一化字段 (Optional): 存储 "batman" (lowercase/trimmed)，用于忽略大小写匹配 
	normalized_alias: str = Field(index=True)

# schemas.py

class EntityRead(SQLModel):
    id: int
    name: str
    type: EntityType
    description: str
    # 明确定义为字符串列表，不含任何隐藏逻辑
    aliases: List[str] 



class EntityUpdate(SQLModel): 
	name: Optional[str] = None 
	type: Optional[EntityType] = None 
	description: Optional[str] = None 
	# 传入全量别名列表。后端将执行：Current DB - New List = Delete; New List - Current DB = Insert. 
	aliases: Optional[List[str]] = None
```

---

## 2. API 接口定义 (API Interface)

> **Security Rule (Strict Ownership Chain):** 所有业务接口必须依赖 `get_current_active_user`。 对于任何子资源（Entity, Chapter, Block, StyleProfile）的访问（GET/PUT/DELETE），**严禁**仅校验 ID 存在性。 **必须**执行链式校验（Chain Verification）：在 SQL 查询中显式 JOIN `Project` 表，并强制校验 `Project.owner_id == current_user.id`。

### Shared Enums & Schemas

为了确保前后端类型统一，定义以下核心枚举：

```Python
class NarrativeMode(str, Enum):
    STANDARD = "standard"             # Mode A: Fractal/Pacing (Default)
    CONFLICT = "conflict_injector"    # Mode B: Yes And / No But
    SENSORY = "sensory_lens"          # Mode C: Show Don't Tell
    FOCUS = "focus_beam"              # Mode D: Micro-details
```
---
### 2.1 The Ritual (Generation Engine)
**Endpoint:** `POST /api/v1/generation/beat`
- **Description:** 核心生成接口。后端负责编排 RAG 检索、Prompt 组装和 JSON 格式强制。
- **Request Body:**
```JSON
{
  "project_id": 1,
  "chapter_id": 5,
  // 使用 LexoRank 锚定当前插入位置 ("在此 Rank 之后生成")
  "anchor_block_rank": "0|h00005:",
  
  // (Frontend-Heavy): 前端直接传 context 文本 (减少 DB 读压力)
  "preceding_context": "The hero stood at the cliff...",
  
  // The Narrative Compass (必须匹配 NarrativeMode Enum)
  "narrative_mode": "conflict_injector",
  "mode_params": { 
      "sub_type": "no_but",
      "intensity": "high"
  },


  // Scrying Glass: Manual Intervention
  "manual_entity_ids": [12],   // Force include (@Mention)
  "muted_entity_ids": [5]      // Force exclude (Mute)
}
```
**Input Validation (Anti-IDOR):** 接口接收 `chapter_id` 后，必须执行以下校验逻辑，不得直接信任前端传入的 `project_id`：
```SQL
SELECT Chapter.id, Project.id 
FROM chapter 
JOIN project ON chapter.project_id = project.id 
WHERE chapter.id = :input_chapter_id 
AND project.owner_id = :current_user_id
```
若无结果，直接返回 404 Not Found。后续逻辑必须使用数据库查询出的 `project_id`，而非请求体中的参数。

- **Backend Context Assembly Strategy (Snapshot-First):**
> **Optimization:** 为了避免从复杂的 JSON `variants` 中提取文本导致性能瓶颈，后端必须优先使用 `content_snapshot` 字段。
1. **Lookback Query:** 使用 LexoRank 索引进行快速反向扫描：
    ```SQL
    -- 获取前 2000 tokens 大致对应的 Blocks (例如取前 20 段)
    SELECT content_snapshot FROM block 
    WHERE chapter_id = :cid AND rank < :anchor_rank 
    ORDER BY rank DESC LIMIT 20;
    ```
2. **Assembly:** 直接拼接查询结果列表 (`List[str]`)，无需任何 JSON 解析操作。
3. **Fallback:** 仅当 `content_snapshot` 为空（旧数据兼容）时，才回退到解析 `variants[selected_variant_index].text` 的逻辑，并触发后台修复任务。
- **Response Body:**
> **Schema Fix:** `scrying_glass` 数据必须包裹在 `meta_info` 中，以匹配数据库 `Block.meta_info` 结构。
```JSON
{
  "generated_rank": "0|h00006:",
  "schema_version": 1,
  "variants": [
    {
	  "id": "550e8400-e29b-41d4-a716-446655440000",
      "label": "External Block",     // UI Display Tag
      "text": "He tried to jump, BUT the rocks crumbled beneath him.", 
      "style_tag": "Physical Obstacle", // Internal Strategy Tag
      "model_id": "deepseek-v3", 
      "prompt_version": "v1.5-conflict-injector", 
      "token_usage": 842, 
      "created_at": "2026-02-09T21:30:00Z"
    },
    {
      "label": "Escalation",
      "text": "He drew his sword, AND lightning struck the blade.",
      "style_tag": "High Stakes"
    },
    {
      "label": "Internal Doubt",
      "text": "He looked down. The abyss stared back.",
      "style_tag": "Psychological"
    }
  ],
  "meta_info": { 
      "scrying_glass": { 
          "lookback_window_size": 2000, 
          "rag_hits": [ 
              {"entity_name": "Excalibur", "reason": "Manual Injection (@)"} 
          ], 
          "strategy_explanation": "Mode B Active: Generating 3 branching conflicts..." 
      } 
  }
}
```
---
### 2.2 Smart Context Smoothing (智能平滑)
**Endpoint:** `POST /api/v1/generation/smooth`
- **Trigger:** 当用户在前端 Slot Machine 选定变体 B，且 B 与下文 C 连接不畅时触发。
- **Logic:** 
	- **Input (Block B):** `context_block_text` (用户刚刚选定或修改的当前段落)。 
	- **Target (Block C):** `next_block_text` (紧随其后的下一段落)。 
	- **Action:** 重写 `next_block_text` 的**首句 (Leading Sentence)**，使其与 Block B 自然衔接。严禁重写 Block B。 
	- **Edge Case:** 如果 `next_block_text` 为空 (End of Chapter)，后端直接返回 `needs_smoothing: false`。
- **Request:**
```JSON
{ 
	"prev_block_text": "Alice slapped Bob.", 
	"next_block_text": "Bob smiled warmly and offered tea.", 
	// [新增] 幂等键：由前后文文本哈希生成的唯一标识 
	// 逻辑：Hash(prev_text + target_text + selected_variant_index)
	 "idempotency_key": "sha256:7a8b9c...", 
	 "project_id": 1 }
```
**Backend Logic:** * 后端使用 Redis 或数据库缓存该 `idempotency_key`，有效期建议为 5-10 分钟。

- 若 Key 已存在且已有结果，直接返回缓存值；若正在生成中，返回 `202 Accepted` 或挂起等待。
- **Response:**

```JSON
{
  "needs_smoothing": true,
  "smoothed_text": "Bob, hiding his shock, forced a smile and offered tea."
}
```
---
### 2.3 The Grimoire (Entity Management)
#### A. Read Entity
**Endpoint:** `GET /api/v1/entities/{entity_id}`
- **Logic:** 
- 安全校验：执行 `get_owned_entity` 依赖注入。
- **显式转换 (Explicit Mapping):** 严禁依赖 Pydantic Validator 自动拍平。必须在 Endpoint 中显式构造返回对象：
```python
return EntityRead(
    id=entity.id,
    name=entity.name,
    type=entity.type,
    description=entity.description,
    # 显式提取关联表中的 alias 字段
    aliases=[entry.alias for entry in entity.alias_entries]
)
```
- **Required:** > ```python stmt = select(Entity).join(Project).where( Entity.id == entity_id, Project.owner_id == current_user.id )
    
- 若查询为空，必须抛出 `404 Not Found`（而非 403，以防止枚举攻击）。
- 自动将关联表 `alias_entries` 拍平为简单的字符串列表。
- **Response:**

```JSON
{
  "id": 1,
  "name": "Bruce Wayne",
  "aliases": ["Batman", "The Dark Knight", "Bruce"] // Flattened List
}
```

#### B. Create Entity

**Endpoint:** `POST /api/v1/entities/`
- **Logic:** 事务性地创建 Entity 及其 Alias 记录。后端负责自动生成 `normalized_alias` (lowercase)。
#### C. Update Entity (Full Sync)
**Endpoint:** `PUT /api/v1/entities/{entity_id}`
- **Description:** 更新实体基础信息及别名。采用“全量替换”策略同步别名列表。
- **Request Schema:**
```Python
class EntityUpdate(SQLModel):
    name: Optional[str] = None
    type: Optional[EntityType] = None
    description: Optional[str] = None
    # Optional List: 
    # - None: 不更新别名 
    # - []: 清空所有别名
    # - ["A", "B"]: 全量替换为 A, B
    aliases: Optional[List[str]] = None 
```

	- **Response Construction:**
	
	- 更新完成后，同样执行显式转换逻辑返回 `EntityRead`，确保返回给前端的结构与数据库模型解耦。
- **Backend Logic (Set Arithmetic Strategy):**
    为避免暴力删除重建 (Nuke and Rebuild) 导致的 ID 膨胀，后端必须使用 **集合运算** 并配合 **严格的作用域限制**：
	- **Scope Definition:** 首先查询当前实体 **现有** 的别名列表： `current_aliases = SELECT alias FROM entityalias WHERE entity_id = :entity_id`
	- **Set Calculation:**
	    - **To Add:** `Input Set - Current DB Set` -> `INSERT INTO entityalias (entity_id, alias, ...) VALUES ...`
	    - **To Delete:** `Current DB Set - Input Set`
	- **Safe Deletion (Critical):**
	    - 执行删除操作时，**必须** 显式限定 `entity_id`，严禁仅根据别名字符串删除。
	    - **Correct SQL:** ```sql DELETE FROM entityalias WHERE entity_id = :entity_id AND alias IN (:to_delete_list)
	    - **Prohibition:** 严禁生成 `DELETE FROM entityalias WHERE alias IN (...)` (缺少 ID 约束)，这会导致删错其他角色的同名别名（例如不同项目中的 "Boss" 或 "Captain"）。
---
### 2.4 Style Anchors (RAG-Enabled)
> **Refactor:** 替代旧版的 `style_anchors: List[str]`，支持向量检索。
#### A. Create Style Profile
**Endpoint:** `POST /api/v1/projects/{project_id}/styles`
- **Request:** `{ "name": "Noir Detective POV", "description": "Short sentences, cynical tone." }`
#### B. Add Style Example (The Anchor)
**Endpoint:** `POST /api/v1/styles/{profile_id}/examples`
**Security Check:** 上传 Example 前，必须校验 `profile_id` 的归属权： `StyleProfile -> Project -> Owner (Current User)`。 严禁向不属于当前用户的 StyleProfile 插入数据。
- **Description:** 上传具体的风格片段，后端将自动计算 Embedding 并存入 `pgvector`。
- **Request:**
```JSON
{
  "text": "The sky above the port was the color of television, tuned to a dead channel.",
  "tags": ["atmospheric", "opening"]
}
```
---
### 2.5 Foreshadowing Scanner (Mode E)
**Endpoint:** `POST /api/v1/analysis/foreshadowing`
- **Description:** 这是一个独立的**分析模式**，不参与常规的文本生成流 (The Ritual)。
- **Logic:** 它不生成新段落，而是反向扫描前文 (Reverse RAG) 并返回建议列表 (Suggestions JSON)。
- **Response:**
```JSON
{
  "is_abrupt": true,
  "suggestions": [
    {
       "chapter_index": 3, 
       "original_snippet": "He checked his pockets...", 
       "suggestion": "Insert: 'his fingers brushed against cold metal.'"
    }
  ]
}
```
### 2.6 Block Consistency & Update Protocol (Critical)
**Endpoint:** `PATCH /api/v1/blocks/{block_id}`

> **Consistency Rule (Snapshot Integrity):** > 为了保证 RAG 检索的准确性，后端必须强制维护 `selected_variant_index` 与 `content_snapshot` 的强一致性。禁止“宽松更新”。

- **Request Validation Logic (Backend Guardrail):**
  后端必须在 Pydantic 层或 Service 层执行以下校验：
  1. **Co-occurrence Check (共现检查):** 如果 Payload 包含 `selected_variant_index`，则 **必须** 同时包含 `content_snapshot`。
     - *Invalid:* `{ "selected_variant_index": 2 }` -> **422 Unprocessable Entity**
     - *Valid:* `{ "selected_variant_index": 2, "content_snapshot": "Actual text..." }`
  
  2. **Equality Check (内容一致性检查 - Recommended):**
     除非标记为手动编辑模式，否则 `content_snapshot` 的文本内容必须等于 `variants[index].text`。
     *(注意：此检查可能需要数据库读取，可视性能要求决定是否仅在前端做，但共现检查必须在后端做。)*

- **Code Snippet (Pydantic Validator):**
```python
# schema/block.py
from pydantic import model_validator

class BlockUpdate(SQLModel):
    selected_variant_index: Optional[int] = None
    content_snapshot: Optional[str] = None
    # ... other fields

    @model_validator(mode='after')
    def check_snapshot_consistency(self):
        # 强制要求：改索引必须带快照
        if self.selected_variant_index is not None and self.content_snapshot is None:
            raise ValueError("Data Integrity Error: 'content_snapshot' is required when updating 'selected_variant_index'.")
        return self
```
当前端检测到用户在 `SlotMachineNode` 中进行了手动编辑 (Input Event)，并触发保存 (Auto-save/Manual Save) 时，后端 `PATCH /api/v1/blocks/{id}` 处理逻辑如下：
1. **Check Consistency:** 获取当前 Block 的 `variants` 列表和 `selected_variant_index`。
2. **Comparison:** 对比 Payload 中的 `content_snapshot` 与 `variants[selected_index].text`。
3. **Fork Strategy:**
    - **Scenario A (无变更):** 内容一致 -> 仅更新 `content_snapshot` (幂等操作)。
    - **Scenario B (首次编辑 AI 变体):**
        - 如果当前 Variant 是 `AI_GENERATED` 类型：
        - **Action:创建一个新 Variant** (Type: `USER_CUSTOM`, Label: "Custom Edit")。
        - 将新 Variant 追加到列表末尾。
        - 更新 `selected_variant_index` 指向这个新 Variant。
        - 保留原 AI Variant 不变 (用于用户后悔回退)。
    - **Scenario C (继续编辑自定义变体):**
        - 如果当前 Variant 已经是 `USER_CUSTOM` 类型：
        - **Action:** **In-Place Update** (直接覆写该 Variant 的 `text`，不再创建新副本，防止列表无限膨胀)。
---
## 3. 核心逻辑与状态机 (Core Logic)
### 3.1 Narrative Mode Strategy (Jinja2 Routing)
**Constraints:**
- The Backend MUST NOT create a Jinja2 template for "Mode E" or "Foreshadowing" in the generation pipeline.
- If the frontend requests `generation/beat` with an invalid mode, return 400 Error.
为了降低 Token 成本并提升 UI 响应速度，Scrying Glass 中的 "Decision Explanation" **不通过 LLM 生成**。 后端在组装 `StoryBeatOutput` 时，基于 `NarrativeMode` 和 `Variant Label` 执行查表操作。
```python
EXPLANATION_MAP = {
    "sensory_lens": { # Mode C
        "Visual": "Focuses on lighting, geometry, and spatial relationships.",
        "Auditory": "Highlights soundscapes and atmospheric noise.",
        "Tactile": "Emphasizes temperature, texture, and physical sensation."
    },
    "conflict_injector": { # Mode B
        "External Block": "Introduces a physical obstacle to impede the protagonist.",
        "Internal Doubt": "Shifts focus to the protagonist's hesitation and fear."
    }
}
```
**Backend Logic:** 在返回 `StoryBeatOutput` 之前，后端根据生成的 `style_tag` 或 `label` 填充 `strategy_summary` 字段： `variant.strategy_summary = EXPLANATION_MAP[mode][variant.label] || "Standard narrative flow."`
后端根据 `narrative_mode` 选择不同的 Jinja2 模板和 Context 策略：
**Pydantic Model for LLM Response:** 在 `llm_service.py` 中定义结构，用于 OpenRouter/OpenAI 的 `response_format` 参数。

``` Python
from pydantic import BaseModel

class Variant(BaseModel):
    label: str  # UI Display Name (e.g. "Action Focus")
    text: str   # Content
    style_tag: str # Consolidated Internal Strategy Tag (e.g. "Fast Paced")

class StoryBeatOutput(BaseModel):
    variants: List[Variant]
    strategy_summary: str # For Scrying Glass
```

为了防止风格锚点 (Style Anchors) 与 叙事模式 (Narrative Modes) 发生指令冲突，后端 **必须** 采用分层组装策略 (Layered Assembly Strategy)，利用 XML 标签对不同维度的指令进行物理隔离。

**Prompt 结构规范 (Jinja2 Template Structure):**

后端不应将所有文本混为一谈，而是构建如下结构的 Prompt：
``` Code snippet
<system_role>
You are "The Grimoire", an expert creative writing assistant.
Your goal is to write a story beat based on the provided context and specific narrative constraints.
</system_role>

<style_guardrails>
{# 1. 负向约束：这是最高优先级的“红线”，模型不得越过 #}
Critical Constraints:
{% for constraint in style_constraints %}
- {{ constraint }}
{% endfor %}
</style_guardrails>

<style_anchors>
{# 2. 风格参考：提供 Few-Shot，但明确标注这只是参考 #}
Reference the following writing style regarding tone and sentence structure, BUT prioritize the Narrative Mode instructions below for content focus:
{% for anchor in style_anchors %}
Example: {{ anchor }}
{% endfor %}
</style_anchors>

<context>
{# 3. 剧情上下文 #}
Previous Context: {{ preceding_context }}
Active Entities: {{ active_entities_list }}
</context>

<narrative_mode_instruction>
{# 4. 核心指令：这里是 Mode A/B/C/D 的具体 Jinja2 逻辑 #}
CURRENT MODE: {{ mode_name }} ({{ mode_theory }})

You MUST generate 3 variants following these specific strategies:
1. Slot 1 ({{ slot_1_label }}): {{ slot_1_instruction }}
2. Slot 2 ({{ slot_2_label }}): {{ slot_2_instruction }}
3. Slot 3 ({{ slot_3_label }}): {{ slot_3_instruction }}

**CRITICAL OVERRIDE:** If the Narrative Mode asks for "Detailed Description" (e.g., Mode C) but Style Constraints ask for "Minimalism", you must apply the Minimalism to the *sentence structure*, but keep the *focus* on the sensory details.
</narrative_mode_instruction>

<output_format>
You must return a valid JSON object.
</output_format>
```

**LLM Service 封装逻辑:**

1. **注入 ID**: 后端在接收到 LLM 返回的 JSON 原始数据后，必须为每个变体注入 `uuid4()`。    
2. **环境快照**: 必须记录当前请求真实的 `model_id` (来自环境变量或用户配置) 和 `prompt_version` (根据 `narrative_mode` 映射的模板名)。    
3. **原子写入**: `variants` 必须作为一个整体写入数据库，禁止对 JSON 内部字段进行部分更新，以维护数据一致性。
### 3.2 Scrying Glass (可观测性逻辑)
- **前端行为 (UI/UX):**
    - 用户输入 `@` 触发自动补全。
    - 前端调用 `GET /api/v1/entities/search?query=Bat`。
    - 后端查询 `EntityAlias` 表，返回 `{ id: 101, name: "Bruce Wayne", matched_alias: "Batman" }`。
    - 前端将 Token 转换为不可见的 `manual_entity_ids: [101]` 存入 Payload。
- **后端兜底 (Backend Fallback):**
    - 如果前端直接传了纯文本（例如用户复制粘贴了 `@Batman`），后端在 `POST /generation/beat` 的预处理阶段：
    - 执行 SQL: `SELECT entity_id FROM entityalias WHERE normalized_alias = :token`。
    - 将命中结果直接注入 Context。
### 3.3 Slot Machine Workflow (Frontend State)
 采用 **Tiptap-First** 策略。Zustand 不存储 Block 列表。Tiptap 的 Document Model 是文档内容的唯一事实来源。
- **State Location:**
	- **Content:** Tiptap Custom Node (`attrs: { variants: [], selectedIndex: 0, meta_info: {} }`).
    - **Selection/Focus:** Tiptap internal state (`editor.state.selection`).
    - **Global UI:** Zustand (`isSidebarOpen`, `isGenerating`).
- **Interaction Flow:**
	- **User Action:** User clicks `Next Variant` button.
		- **Immediate UI Update:**
		    - Tiptap updates the node content immediately (0ms latency).
		    - **Flag:** Set internal flag `isDirty = true`.
		    - **Backend Sync (Critical):**
				- 当触发保存（Auto-save 或 Explicit Save）时，前端发送的数据包必须遵守 **Atomic Variant Switch** 协议：
				    
				    - `selected_variant_index`: 新的索引。
				        
				    - `content_snapshot`: **必须**被覆写为当前变体的文本内容（Frontend Source of Truth）。
				        
				- **后端原子操作 (Strict):**
```python
# Pseudo-code for Block Update Endpoint 
if payload.selected_variant_index is not None: 
	if payload.content_snapshot is None: 
		raise HTTPException(400, "Snapshot missing for variant switch") 
		# 应用更新 
	block.selected_variant_index = payload.selected_variant_index
	block.content_snapshot = payload.content_snapshot
```

		- **Smoothing Trigger (The Gatekeeper):**
		    - **Condition A (Explicit Exit):** Trigger when the **Cursor leaves the Block** (`onBlur` / `onSelectionUpdate` detects node change).
		    - **Condition B (Idle Timeout):** Trigger only after a **Long Debounce (e.g., 2000ms)** if the cursor remains inside.
		- **API Execution:**
			- **Pre-condition:** Check if a Next Block (Block C) exists in the document.
				- **Condition 1 (End of Chapter):** If Next Block is `null`, set `isDirty = false` and **ABORT**. Do NOT call API. 
				- **Condition 2 (Standard):** If Next Block exists AND `isDirty === true` AND trigger fired:
					- Call `POST /generation/smooth`. 
					- On success: Update **ONLY the Next Block (Block C)** content. NEVER modify the current block.
				- set `isDirty = false`
- **Manual Editing Handling:**
	如果用户在选定某个变体后，手动修改了 Tiptap 中的文本：
	    - **Action:** 前端保持 `selected_variant_index` 不变。
	    - **Sync:** 将修改后的文本直接写入数据库的 `content_snapshot`。
	    - **Note:** 此时 `content_snapshot` 可能与 `variants[index].text` 不一致，这是允许的（User Override）。RAG 将始终读取 `content_snapshot` 以获取最新版本。
- **Idempotency Strategy:**
	1. 当 `isDirty` 为 `true` 准备触发 Smoothing 时。
	2. 计算 `prev_block` 与 `current_block` 的内容哈希。
	3. 检查本地 `last_smooth_key` 缓存。如果哈希未变，则 **跳过请求**。
	4. 这不仅解决了幂等问题，还在前端实现了初步的“请求节流”。
### 3.4 动态关系解析算法 (Dynamic Relationship Resolution)
为了在有限的 Context Window (通常 8k-128k) 内保持高相关性，后端必须执行严格的分层检索策略：
1. **Tier 1: Mandatory Injection (最高优先级)**
    - **Source:** 用户在 Scrying Glass 中手动 `@` 提及的实体 ID (`manual_entity_ids`)。
    - **Action:** 无条件注入。若超出 Token 限制，报错或截断 Tier 3 内容。
2. **Tier 2: Contextual Presence (当前文本相关性)**
    - **Source:** 后端对 `preceding_context` (Lookback Window, 例如前 2000 tokens) 执行 **Aho-Corasick 算法** 或高效的关键词匹配。
    - **Logic:**
        - 加载当前 Project 下所有活跃实体的 `alias_list`。
        - 若文本中检测到 "Batman" 或 "Bruce"，则自动命中对应实体 ID。
    - **Action:** 注入实体详情卡片。这解决了“角色在场但未被手动提及”的问题。
3. **Tier 3: Temporal Relevance (时空/剧情相关性)**
    - **Source:** 基于 `3.4.1 动态关系解析` (原逻辑) 的时间线计算。
    - **Constraint:** 仅当 Tier 1 + Tier 2 的 Token 占用量 < 70% Max Context 时，才填充此层级。
    - **Priority:** 优先注入 `rank` 距离当前章节最近有过互动的角色（Recency Bias）。
为了处理“宿敌 -> 结盟 -> 宿敌”的循环，后端在执行 RAG 时遵循以下逻辑：
- **取值范围 (Lexicographical Comparison)：** - 使用字符串比较逻辑：`start_rank <= current_rank` (String Comparison, NOT Numeric). - 由于 LexoRank 的特性，字符串字典序直接对应时间先后顺序。
- **分类去重**：在 Python 业务层对结果进行 `groupby(category)`。
- **择优选取**：在每个分类中，优先选择 `start_rank` 字典序最大（String Max）的记录。
- **最终组装**：将所有分类的最优记录合并，作为当前 Context。
- **存在性判定：** * 仅当 `current_chapter.rank >= entity.appearance_rank` 且 (`entity.disappearance_rank IS NULL` 或 `current_chapter.rank <= entity.disappearance_rank`) 时，该实体被视为 **“活跃 (Active)”**。
    
- **处理“已去世”实体：**
    - 如果 `current_chapter.rank > entity.disappearance_rank`：
        - **禁止：** 将其作为“当前在场角色”注入生成上下文。
        - **允许：** 仅作为“历史背景/记忆”在 RAG 的长程记忆中被引用（需标记其状态为 `disappearance_status`）。
### 3.5 LexoRank Strategy (New)
 - Helper Utility (`app/core/lexorank.py`):
	- `gen_next(rank: str) -> str`: 在末尾追加。
	- `gen_prev(rank: str) -> str`: 在开头插入。
	- `gen_between(rank_a: str, rank_b: str) -> str`: 计算中间值。如果字符串空间耗尽，自动增加字符长度（如 'a' 与 'b' 之间生成 'an'）。
-  **String Comparison:**
    - 由于 LexoRank 保证字典序与逻辑序一致，所有的 SQL 查询（如 `WHERE rank > :current_rank`）无需修改，直接利用数据库的字符串索引。
- **Auto-Rebalancing (Maintenance):**
    - **Trigger:** 当单条 Rank 字符串长度超过 **128 字符** 时。
    - **Action:** 触发后台异步任务 (`BackgroundTasks`)，锁定该章节，重新生成等间距的短 Rank (e.g., reset to "0|aaaaaa", "0|baaaaa"...)，并批量更新数据库。
- LexoRank Scope & Bucket Protocol (New Section)

> **Rule:** LexoRank 用于实现 O(1) 的列表重排。为了降低 v1 复杂度并防止查询越界，必须严格遵守以下作用域和 Bucket 规则。
1. **Scope Isolation (作用域隔离):**
    - **Chapter.rank:** 仅在 `project_id` 作用域内唯一且有序。
        - _Query:_ `SELECT * FROM chapter WHERE project_id = :pid ORDER BY rank ASC`
    - **Block.rank:** 仅在 `chapter_id` 作用域内唯一且有序。**严禁**跨章节排序。
        - _Query:_ `SELECT * FROM block WHERE chapter_id = :cid ORDER BY rank ASC`
2. **Bucket Strategy (Bucket 策略):**
    - **Format:** `bucket|rank_string` (e.g., `0|h00000:`)
    - **v1 Constant:** 在 v1 版本中，**Bucket 必须硬编码为 `"0"`**。
    - **No Logic:** 后端逻辑**不应**解析或依赖 Bucket 值来做业务判断（如卷、幕）。它目前仅作为 LexoRank 算法的格式占位符。
    - **Rebalancing (重平衡):** 只有当单条 Rank 长度溢出（>128 chars）需要全局重平衡时，后台任务才会将该作用域下的所有条目迁移至 `"1|..."`，除此之外，严禁动态修改 Bucket。
3. **Future Proofing (未来扩展):**
    - 在 v2+ 中，Bucket 可被重构为 "Volume ID" (卷 ID) 或 "Act ID" (幕 ID)，但在 v1 中，所有数据必须扁平化存储在 Bucket `0` 中。
---
## 4. 边界情况与非功能需求 (Edge Cases)
### 4.1 Tenancy Isolation (Critical)
- **Logic (Deep Validation):** > 任何通过 ID 访问子资源（`Chapter`, `Entity`, `Block`, `StyleProfile`）的接口，禁止使用 `session.get(Model, id)`。 **必须**在 SQL 构建阶段显式 JOIN `Project` 表，并添加 `.where(Project.owner_id == current_user.id)` 过滤条件。
- **Error Handling:** > 当校验失败（即资源存在但属于其他用户）时，**必须返回 404 Not Found**，严禁返回 403 Forbidden 或具体的错误信息，以防止攻击者通过错误码探测资源 ID 是否存在。
- **Vector Store:** RAG 查询必须带上 `metadata={"project_id": ...}` 过滤器，防止跨项目泄露知识。
### 4.2 Performance
- **Single-Shot JSON Enforcement:**
    
    - **Constraint:** The backend MUST use `response_format={"type": "json_object"}` (or provider equivalent) to retrieve all 3 variants in a single HTTP request.
        
    - **Prohibition:** Do NOT issue 3 concurrent HTTP requests to the LLM provider. This quadruples the Input Token cost (Context Window is sent 3 times)
- **Latency Target:**
    - Since JSON Mode can be slightly slower than stream text, the frontend MUST show a "Writing..." skeleton state during generation.
    - **Streaming (Optional/Advanced):** If supported by the provider, stream the JSON structure. If too complex, await full response (Block-level granularity accepts 2-4s latency).
### 4.3 Privacy (BYOK)
- **API Keys:** 用户 API Key 仅在请求期间解密并驻留内存，严禁明文存储。

### 4.4 Data Consistency & RAG Integrity
- **Single Source of Truth:** - 对于 **RAG Lookback** (Context Assembly)，`Block.content_snapshot` 是唯一的真值来源。
    - 对于 **User UI**，`Block.variants[index]` 是真值来源。
- **Synchronization Contract:**
    - 前端负责在任何 `Variant Switch` 事件发生时，构建包含 `index` + `snapshot` 的完整 Payload。
    - 后端负责在写入数据库前拦截任何试图破坏这两者同步的请求（拒绝 Partial Updates）。
---
## 5. 验证与测试策略 (Verification Plan)
### 5.1 Backend Acceptance
- **JSON Structure Test:**
	- `pytest tests/test_llm_structure.py`:
		- **Scenario (Valid JSON):** Mock LLM 输出符合 Schema 的 JSON 对象。
		- **Assert:** 服务能够正确解析并序列化为 `List[BlockVariant]`。
		- **Scenario (Broken JSON):** Mock LLM 输出截断或格式错误的 JSON。
		- **Assert:** `tenacity` 重试机制触发；若超过重试次数，则返回受控的错误提示（Graceful Error）。
- **LexoRank & Ordering (Replaces Float Rank Test)**
	- `pytest tests/test_lexorank.py`:
	    - **Scenario (Dense Insertion):** 在 Rank A ("0|h00000:") 和 Rank B ("0|h00001:") 之间连续插入 50 次。
	    - **Assert:** 每次生成的 Rank 必须唯一且符合字典序排列 (`prev < new < next`)。
	    - **Assert:** 字符串长度随插入次数增加，但不应报错。
	- **Scenario (SQL Ordering):**
	    - **Action:** 插入 3 个乱序 Block，Rank 分别为 "0|z", "0|a", "0|m"。
	    - **Assert:** `session.exec(select(Block).order_by(Block.rank)).all()` 返回顺序为 a -> m -> z。
-  **Entity Lifecycle & Visibility (Existence Logic)**
	- `pytest tests/test_entity_lifecycle.py`:
		- **Scenario:** 实体 A `appearance_rank: "0|c00000:"`。
		- **Action:** 查询 `current_chapter.rank = "0|b00000:"` (Before)。
		- **Assert:** `"0|b..." < "0|c..."`，实体不应出现。
		- **Action:** 查询 `current_chapter.rank = "0|d00000:"` (After)。
		- **Assert:** 实体应出现在 RAG 结果中。
- **Temporal Relationship & Regression (Interval Logic)**
	- `pytest tests/test_rag_advanced.py`:
	    - **Scenario (Status Regression - 宿敌回归):**
             使用 LexoRank 字符串替代浮点数
	        1. **全局关系:** 创建 A->B "Enemy" (永久), `start_rank: "0|000000:"`, `end_rank: NULL`。
	        2. **临时关系:** 创建 A->B "Ally" (区间), `start_rank: "0|m00000:"`, `end_rank: "0|z00000:"`。
	    - **Assert (Rank "0|a00000:"):** 仅返回 "Enemy" ("a" < "m"，临时区间未开始)。
	    - **Assert (Rank "0|r00000:"):** 同时返回 "Enemy" 与 "Ally" ("m" < "r" < "z"，落入区间)。
	    - **Assert (Rank 6000.0):** 仅返回 "Enemy"（临时区间已结束，状态自动回归）。
	    - **Scenario (Base Fallback):** 删除所有 `EntityRelationship` 记录。
	    - **Assert:** RAG 应成功回退并提取 `Entity.description` 中的基础描述。
- **Mode & Scope Control**
	- `pytest tests/test_narrative_modes.py`:
	    - **Scenario:** 使用 `mode="focus_beam"` (沉浸光束)。
	    - **Assert:** `scrying_glass.rag_hits` 必须为空（强制禁用全局 RAG 以维持微观聚焦）。
	    - **Scenario (Manual Injection):** 在请求中包含 `manual_entity_ids: [12]` (@Mention)。
	    - **Assert:** 即使实体 Rank 不匹配，该实体也必须被强制注入 Prompt。
- **Data Schema Integrity Test:**
	- `pytest tests/test_block_schema.py`:
	    - **Scenario (Schema Validation):** 尝试向 `Block` 插入不含 `id` 或 `model_id` 的 `Variant` 字典。
	    - **Assert:** Pydantic 验证器应抛出 `ValidationError`，防止脏数据入库。
	    - **Scenario (Backward Compatibility):** 模拟读取 `schema_version` 缺失的旧数据。
	    - **Assert:** Service 层能够自动填充默认版本号，确保系统不崩溃。
- **Data Consistency Guardrails:**
	- `pytest tests/test_block_integrity.py`:
	    - **Scenario (Lazy Update):** 发送仅包含 `{"selected_variant_index": 1}` 的 PATCH 请求。
	    - **Assert:** API 返回 **422/400 Error**。数据库状态未改变。
	    - **Scenario (Atomic Update):** 发送 `{"selected_variant_index": 1, "content_snapshot": "..."}`。
	    - **Assert:** API 返回 **200 OK**。数据库正确更新。
- **Security & IDOR Tests:**
	- `pytest tests/test_security_idor.py`:
	    - **Scenario (Cross-Tenant Entity Update):**
	        - **Setup:** 用户 A 登录。已知用户 B 的 `entity_id` (例如 999)。
	        - **Action:** 用户 A 发送 `PUT /api/v1/entities/999`。
	        - **Assert:** 返回 **404 Not Found**。数据库中用户 B 的数据未被修改。
	    - **Scenario (Cross-Tenant Generation):**
	        - **Setup:** 用户 A 登录。构造请求 `{"chapter_id": user_b_chapter_id
	        - **Action:** 发送 `POST /api/v1/generation/beat`。
	        - **Assert:** 返回 **404 Not Found**。严禁在用户 B 的章节中生成内容。
### 5.2 Frontend Acceptance 
- **Slot Machine (Node Isolation):**
    - `npm run test`:
    - **Scenario:** Render `SlotMachineNode` within a Tiptap test environment.
    - **Action:** Simulate `updateAttributes` call.
    - **Assert:** Verify the rendered text matches `variants[newIndex]`. Verify **Zustand store is NOT accessed** for content updates.
- **Slot Machine Labels:**
	- **Scenario:** Render `SlotMachineBlock`.
    - **Assert:** Verify that the UI displays the `variant.label` (e.g., "Action Focus") next to the content or in the tooltip.
- **Scrying Glass (Context Awareness):**
    - **Scenario:** Move cursor into a specific block.
    - **Assert:** Right sidebar updates to show entities relevant to _that specific block_ (via `editor.state.selection`).
- **Data Flow:** 当光标移动时，读取 `editor.state.selection.$from.node().attrs.meta_info.scrying_glass`。如果该路径下的数据存在，渲染 RAG 命中列表和调试信息；否则显示 Empty State。
- **Scenario D: End of Chapter (Edge Case)**
	- **Action:** Create a document with only **one** block (Block A).
	- **Action:** Click "Next Variant" on Block A.
	- **Action:** Blur/Unfocus Block A.
	- **Assert:** Mock API (`POST /generation/smooth`) MUST NOT be called. (Reason: No subsequent text exists to smooth).
## 6. 文件结构规划 (File Structure)
```Plaintext
/
├── .gitignore
├── README.md
├── AGENT.md                       # [Critical] AI 行为准则 (The Guardrails)
├── SPEC.md                        # [Critical] 项目说明书 (The Bible)
├── docker-compose.yml             # 编排 DB, Backend, Frontend
├── .env.example                   # 环境变量模板
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml             # Python 依赖管理 (Poetry)
│   ├── alembic.ini                # DB Migration Config
│   ├── alembic/                   # [必需] 数据库变更记录
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── main.py                # [必需] App Entry Point (FastAPI app)
│   │   ├── __init__.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── api_v1/            # API Router V1
│   │   │   │   ├── api.py         # 路由汇总
│   │   │   │   └── endpoints/
│   │   │   │       ├── auth.py          # Login/Register (JWT)
│   │   │   │       ├── projects.py      # Project CRUD & Settings
│   │   │   │       ├── generation.py    # The Ritual (Modes A-D)
│   │   │   │       ├── analysis.py      # Mode E (Foreshadowing)
│   │   │   │       ├── entities.py      # Entity Management
│   │   │   │       └── blocks.py        # Block Consistency (Snapshot Sync)
│   │   │   │
│   │   │   └── deps.py            # [必需] Dependencies (get_current_user, get_db)
│   │   │
│   │   ├── core/
│   │   │   ├── config.py          # [必需] Settings (Env vars, Secrets)
│   │   │   ├── security.py        # JWT Encoding/Decoding, Password Hashing
│   │   │   ├── lexorank.py        # [核心] O(1) Ordering Logic
│   │   │   └── prompts/
│   │   │       ├── loader.py      # Jinja2 Environment Loader
│   │   │       └── templates/     # [核心] Logic-Free Templates
│   │   │           ├── base.j2          # XML Structure Skeleton
│   │   │           ├── standard.j2      # Mode A (Fractal)
│   │   │           ├── conflict.j2      # Mode B (Conflict)
│   │   │           ├── sensory.j2       # Mode C (Sensory)
│   │   │           └── focus.j2         # Mode D (Focus Beam)
│   │   │
│   │   ├── db/
│   │   │   ├── session.py         # Engine & SessionLocal
│   │   │   ├── base.py            # SQLModel Registry for Alembic
│   │   │   └── init_db.py         # Initial Data Seeding
│   │   │
│   │   ├── models/                # [核心] Database Tables (SQLModel)
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   ├── chapter.py         # Contains Chapter & Block models
│   │   │   └── entity.py          # Entity & EntityAlias
│   │   │
│   │   ├── schemas/               # [核心] Pydantic DTOs (Request/Response)
│   │   │   ├── common.py          # Generic Responses
│   │   │   ├── generation.py      # StoryBeatOutput, Variant Schema
│   │   │   └── entity.py          # EntityRead, EntityUpdate
│   │   │
│   │   └── services/
│   │       ├── llm_service.py     # OpenAI/DeepSeek Wrapper (Retry Logic)
│   │       └── rag_service.py     # Scrying Glass Logic (Vector Search)
│   │
│   └── tests/                     # 测试套件
│       ├── conftest.py            # Pytest Fixtures
│       ├── api/                   # Integration Tests
│       └── unit/                  # Unit Tests (LexoRank, Prompts)

├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── components.json            # Shadcn UI config
│   │
│   ├── public/
│   │   └── locales/               # i18n JSON files
│   │
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   │
│   │   ├── api/                   # [新增] API Client Layer
│   │   │   ├── client.ts          # Axios Instance (Auth Header Interceptor)
│   │   │   ├── auth.ts
│   │   │   ├── generation.ts
│   │   │   └── entities.ts
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                # Shadcn UI Components (Button, Input...)
│   │   │   ├── layout/            # Sidebar, Header
│   │   │   ├── scrying-glass/     # [核心] Right Sidebar Components
│   │   │   │   ├── InsightCard.tsx
│   │   │   │   └── EntityList.tsx
│   │   │   └── editor/            # [核心] Tiptap Editor
│   │   │       ├── GrimoireEditor.tsx # Main Wrapper
│   │   │       ├── BubbleMenu.tsx
│   │   │       └── extensions/
│   │   │           ├── SlotMachine/
│   │   │           │   ├── SlotMachineNode.ts  # Node Logic & Schema
│   │   │           │   └── SlotMachineView.tsx # React Render & Interaction
│   │   │           └── commands.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useAutosave.ts     # Debounced Save Logic
│   │   │   └── useProject.ts
│   │   │
│   │   ├── lib/
│   │   │   ├── utils.ts           # Shadcn utils
│   │   │   └── lexorank.ts        # Frontend helper (if needed)
│   │   │
│   │   ├── store/
│   │   │   └── appStore.ts        # [限制] Only Global UI & Auth State
│   │   │
│   │   └── types/                 # TypeScript Interfaces (Sync with Backend)
│   │       ├── api.ts
│   │       └── editor.ts
│   │
│   └── tests/
│       └── components/            # Component Testing
```

---
## 7. 分步实施计划 (Implementation Steps)
> **Agent 指令:** 请严格按照以下顺序执行。每完成一步，必须运行对应的验证命令并确认为 **PASS**，方可进入下一步。
### Phase 1: Foundation & Security (SaaS 基石)

**Step 1: Infrastructure & Database**
- **目标:** 配置 Docker 环境 (Postgres + pgvector)。初始化 FastAPI 项目结构。配置 `alembic` 迁移环境。
- **关键文件:** `docker-compose.yml`, `backend/app/core/config.py`, `backend/app/db/session.py`
- **验证:** `docker-compose up -d` 成功启动数据库；能够连接并执行简单的 SQL 查询。

**Step 2: Authentication & User Model (The Gatekeeper)**
- **目标:** 实现 `User` 模型。集成 `passlib` (Hash) 和 `python-jose` (JWT)。实现 `/auth/register` 和 `/auth/token` 接口。
- **关键文件:** `backend/app/models/user.py`, `backend/app/api/deps.py` (实现 `get_current_user`).
- **验证:**
    - 命令: `pytest tests/test_auth.py`
    - 标准: 注册用户 -> 登录获取 Token -> 使用 Token 访问受以此保护的 Mock 接口 -> 成功 (200)。不带 Token -> 失败 (401)。

**Step 3: Project Management & Tenancy Isolation**
- **目标:** 实现 `Project` CRUD。**关键:** 在所有查询中强制添加 `owner_id == current_user.id` 检查。
- **关键文件:** `backend/app/api/endpoints/projects.py`
- **验证:**
    - 命令: `pytest tests/test_tenancy.py`
    - 标准: 用户 A 尝试获取用户 B 的 Project ID -> 必须返回 **404 Not Found** (而非 403，防止 ID 遍历)。

### Phase 2: The Brain (Core Logic)
**Step 4: The Grimoire & Temporal RAG**
- **目标**：实现“时空查询逻辑”。
- **SQL 实现**：使用 `WHERE start_rank <= :current_rank` 配合 `ORDER BY category, start_rank DESC`。
- **验证逻辑**：更新 `test_rag_advanced.py`，确保在 Rank 4000.0 时，若 Enemy 和 Ally 属于同一 Category，则 Ally 覆盖 Enemy；若属于不同 Category，则两者并存。

**Step 5: Prompt Engine (Jinja2 Setup)**
- **目标:** - 搭建 Jinja2 环境。
    - **创建基类模板 `base_prompt.j2`:** 包含 3.1 节定义的 XML 骨架 (`<system_role>`, `<style_guardrails>`, `<style_anchors>`, `<output_format>`)，并预留 `{% block narrative_mode_instruction %}` 插槽。
    - **创建模式子模板:** 创建 `mode_standard.j2`, `mode_conflict.j2`, `mode_sensory.j2` 等。它们通过 `{% extends "base_prompt.j2" %}` 继承基类，并仅填充具体的叙事模式指令。
- **关键文件:** `backend/app/core/prompts/loader.py`, `templates/base_prompt.j2`, `templates/mode_*.j2`.
- **逻辑变更 (Critical):**
    1. **JSON 关键词强制:** OpenAI/DeepSeek 的 JSON Mode 要求 System Prompt 中必须明确包含单词 **"JSON"**。
    2. **Schema 注入:** 基类模板必须显式描述输出的 JSON 结构（即要求包含 `variants`, `label`, `text`, `style_tag` 字段），不能仅依赖 API 参数。
- **验证:**
    - 命令: `pytest tests/test_prompts.py`
    - 标准:
        - **继承测试:** 渲染 `mode_sensory.j2`，断言结果中同时包含基类的 XML 标签（如 `<style_guardrails>`）和子类的指令（如 "Focus on visual and olfactory details"）。
        - **格式测试:** 断言渲染后的字符串包含 **"Return a valid JSON object"**。
        - **Schema 测试:** 断言包含目标 Schema 的字段定义 (e.g., `"variants": [...]`)。

**Step 6: The Ritual API (Integration)**
- **目标:** 实现 `/generation/beat` 接口。串联 Auth -> RAG -> Jinja2 -> OpenAI SDK。
- **重点:** 
	- 引入 `pydantic` 定义 `StoryBeatOutput` 结构。
	- 在调用 OpenAI/DeepSeek API 时，配置 `response_format`。
	- 确保 Jinja2 模板显式要求输出 JSON 格式。
	- 获取当前光标所在 Block 的 `attrs.rank`。
	- 如果是新章节首段生成：传递 `anchor_block_rank = min_rank` (or "0|000000:")。
- **验证:**
    - 命令: `pytest tests/test_api_generation.py`


### Phase 3: Frontend Foundation & Global State
**架构核心变更:** 文档内容 (Blocks) 的唯一事实来源是 Tiptap Editor 实例。Zustand 仅负责全局 UI 状态和元数据。
**Step 7: Frontend Foundation & i18n**
- **目标:** 初始化 React + Vite + Tailwind。配置 `i18next`。搭建 **"瘦身版"** 全局状态管理 (`appStore.ts`)。
- **关键文件:** 
	- `src/store/appStore.ts`: **仅包含** `user` (Auth), `projectMeta` (ID, Title, Style Anchors), `uiFlags` (Sidebar Open/Close, IsGenerating). **严禁在此定义 `blocks` 或 `content` 数组。**
	- `src/locales/en/common.json`.
- **验证:** 
	- 浏览器访问: 登录后跳转至 Dashboard。
	- **State Check:** 打开 React Developer Tools 或 Console，确认 Zustand Store 中**不包含**任何文档文本数据。

**Step 8: Tiptap Engine & Slot Machine Node (The Core)**

- **目标:** 集成 Tiptap。开发自定义 Extension 和 React NodeView (`SlotMachineBlock.tsx`)。
    
- **状态逻辑 (Critical):**

``` TypeScript
// 在 SlotMachineNode 组件内
useEffect(() => {
  if (!isFocused && isDirty) {
    // 只有当用户“离开”当前段落时，才认为他选定了这个变体
    triggerSmoothing(currentVariant);
    setIsDirty(false);
  }
}, [isFocused, currentVariant]); // 依赖项：焦点状态、当前变体
```

- **验证:**
	- **命令:** `npm run test` (针对 `SlotMachineNode` 的单元/组件测试)
	- **Scenario A: 快速浏览 (Browsing State - Suppression Test)**
	    - **Action:** 在测试环境中渲染组件，模拟用户在 2 秒内连续点击 5 次 "Next Variant" 按钮。
	    - **Assert (UI):** DOM 中的文本内容必须实时更新 5 次（确保无 UI 延迟）。
	    - **Assert (Network):** 监控 Mock API (`POST /generation/smooth`)，断言其调用次数严格为 **0**。_(验证：浏览过程不消耗 Token)_
	- **Scenario B: 意图确认 (Commitment - Blur Trigger)**
	    - **Action:** 点击 "Next Variant" 切换到变体 B（触发 `isDirty = true`），然后程序化地将编辑器光标移动到文档的其他位置（模拟 `onBlur`）。
	    - **Assert:** Mock API (`POST /generation/smooth`) 被调用 **1 次**。
	    - **Assert:** API 请求体中的 `target_block_text` 必须匹配变体 B 的内容。_(验证：失焦即确认)_
	- **Scenario C: 无效交互 (Passive Interaction)**
	    - **Action:** 光标进入 SlotMachine 节点，**不点击**任何切换按钮，然后光标移出。
	    - **Assert:** Mock API **未被调用**。_(验证：无变更不请求，isDirty 逻辑正确)_

**Step 9: Scrying Glass & Context Awareness (The Observer)**

- **目标:** 开发右侧边栏 `ScryingGlass.tsx`。实现与编辑器光标的**单向联动**。
- **逻辑 (Decoupled):**
    - 组件内使用 `useCurrentEditor()` (来自 `@tiptap/react`)。
    - 监听 `selectionUpdate` 事件。
    - **Data Flow:** 当光标移动时，读取 `editor.state.selection.$from.node().attrs.scrying_glass`。如果该属性存在，渲染 RAG 命中列表和调试信息；否则显示 Empty State。

- **验证:**
    - 手动测试: 在编辑器中输入两段不同的文本（假设它们包含不同的 hidden attributes）。
    - 动作: 将光标从第一段移动到第二段。
    - 标准: 右侧边栏的内容瞬间改变，显示当前段落对应的 Entity Info。