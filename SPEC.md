# 🏗️ 技术架构规范 (SPEC.md): Genesis Engine

**文档描述:** 本文档基于 `docs/PRD_Genesis.md` 和 `docs/Genesis_User_Journey_Example.md` 制定，定义拉起本系统的纯粹技术契约。开发者必须严格遵守本规范，不容讨价还价。

---

## 1. 技术栈选型 (Technology Stack)

为了实现复杂的高频并发推演、状态持久化和前端极速渲染，核心栈锁定为：

* **Backend (后端):** [FastAPI](https://fastapi.tiangolo.com/) + Python 3.12+ (全异步支持)
* **Database (数据库):** [SQLModel](https://sqlmodel.tiangolo.com/) (Pydantic 兼容的 ORM) + SQLite (MVP 阶段) / PostgreSQL (生产阶段)
* **Real-time (实时通信):**  FastAPI WebSockets 或 Server-Sent Events (SSE) (用于 The Monitor 状态流式更新)
* **Frontend (前端):** React 19 + Vite + TypeScript
* **Editor & UI (编辑器):** Tiptap (无头富文本) + Tailwind CSS 4
* **Dependency Management:** `poetry` (后端) / `npm` (前端)
* **LLM Orchestration:** `langchain-core` / 纯净的生 API 调用（优先基于 Jinja2 组装 Prompt，拒绝过度封装的 LangChain 黑盒）

---

## 2. 核心数据模型 (The Three-Tier Schema)

系统摒弃了传统的“富文本长字符串”保存模式。所有数据必须严密落盘于以下三个层次。

### 2.1 The Grimoire (世界管理器)

用于全局状态记录与 Lazy Instantiation（边演边建）。实体数据是高度解耦的 Key-Value JSON。

```python
class GrimoireEntity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int
    entity_type: str = Field(index=True)  # "CHARACTER", "FACTION", "ITEM", "LOCATION", "LORE"
    name: str = Field(index=True)         # 例: "宁毅", "乌家"

    # 核心字段：存储模型随时读写的结构化状态
    attributes_json: str                  # JSON string: {"隐藏动机": "怕老婆", "武力值": 99}
    relations_json: str                   # JSON string: {"苏檀儿": "极其信任"}

    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2.2 The Storyboard (大纲管理器)

组织小说结构的骨架。注意：`Chapter` 仅仅是文件夹，业务数据在 `Block` 里。

```python
class StoryNode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int
    parent_id: Optional[int] = Field(default=None, foreign_key="storynode.id")

    node_type: str        # "VOLUME" (卷), "CHAPTER" (章)
    title: str            # 例: "第三章：诗会风波"
    summary: str          # 大纲简述，用于 Context 注入

    rank: str = Field(index=True) # LexoRank 值，决定卷/章本身的排序
```

### 2.3 The Story IR Block (推演原子块)

最底层的发生器。由 Director Agent 取自论坛并脱水出的结果。

```python
class StoryBlock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int
    node_id: int = Field(foreign_key="storynode.id") # 归属于哪一章

    # LexoRank: 绝对顺序键 (例如 "0|i00000:")。由于它，我们可以随意插入/回档
    lexo_rank: str = Field(index=True, unique=True)

    # The Spark 触发词
    user_spark: str       # "苏檀儿急疯了向宁毅求助..."

    # 脱水后的剧本中间件 (Story IR)
    ir_json: str          # JSON array of actions: [{"agent": "苏檀儿", "action": "哭诉"}, ...]

    # Camera Agent 渲染后的缓存
    rendered_text: Optional[str] = None 
    render_pov: Optional[str] = None
    render_style: Optional[str] = None

    is_committed: bool = False # 锁定后，Scribe 才能读取此 Block 的 IR
```

---

## 3. 六大 Agent 通信与管线契约

系统从 UI 输入到输出包含清晰的单向数据流。

### 3.1 Phase 0 & 1: 🧚‍♀️ The Muse Agent (Human-in-the-loop)

* **输入:** 用户的口语聊天 (WebSocket/HTTP)。
* **处理:** Muse 分析语境，决定是要创建/修改 `GrimoireEntity` 还是要构建 `StoryNode`。
* **输出/防患:** Muse 构造出一个 **Diff 草案** (例如 `{"action": "update", "entity": "宁毅", "patch": {"弱点": "怕老婆"}}`) 并发回前端。用户在 UI 点击 `Approve` 后，前端发送正式的 HTTP POST 写入数据库。

### 3.2 Phase 2 & 3: 异步回合制沙盒 (Forum Debate)

* **触发:** 前端下发 `POST /api/orchestration/spark`，带上 `Grimoire` 约束和 `Spark` 冲突设定。
* **通信栈:** 必须使用 **Server-Sent Events (SSE)**，下发如下结构的流日志到前端：
  
  ```json
  // Server 端推送事件 (Event Stream)
  {"event": "turn_start", "data": {"speaker": "苏檀儿", "intent": "求助"}}
  {"event": "world_validation", "data": {"status": "valid", "msg": "所在位置合法"}}
  {"event": "turn_end", "data": {"content": "焦急地在院子里走来走去..."}}
  ```
* **微操冻结机制:** 
  * 前端接收每一回合后，客户端强制 `await delay(2000)`，展示倒计时进度条。
  * 用户若点击覆写，前端通过 `POST /api/orchestration/override` 中断当前 Agent，注入用户的最高指令。

### 3.3 Phase 4: ✂️ Director Agent (IR 脱水)

* **触发:** 论坛推演达到张力阈值 (Tension Threshold) 或达到回合上限，触发脱水。
* **输出契约:** 必须输出符合以下 JSON Schema 的不可变 `Story IR`：
  
  ```json
  {
    "block_summary": "宁毅给出做空乌家的狠毒计策",
    "dialogues_and_actions": [
      {"character": "苏檀儿", "type": "action", "detail": "来回踱步，咬牙请教"},
      {"character": "宁毅", "type": "dialogue", "detail": "让他们截，坑死他们。"}
    ],
    "tension_shift": "+10"
  }
  ```
  
  此结果被写入 `StoryBlock.ir_json` 进行持久化，并分配 `lexo_rank`。

### 3.4 Phase 5: 🎥 Camera Agent (解耦渲染)

* **边界:** 绝不允许 Camera 接触原始推演日志。它只能读取 `StoryBlock.ir_json`。
* **接口:** `POST /api/render/block/{block_id}`。携带 `pov` 和 `style_template` 参数。利用高级模型 (如 Claude 3.5 Sonnet 等) 把冰冷的 JSON 写成出版级网文，存入 `StoryBlock.rendered_text` 并推至前端 Tiptap 画布。由于基底是 IR，用户可无限次低成本 `Retry` 本接口。

### 3.5 Phase 6: 📜 Scribe Agent (仅读 IR)

* **触发:** 当用户在 Tiptap 内点击 `[Commit]`，调用 `POST /api/blocks/{block_id}/commit`。
* **边界:** 史官 **绝对不读取** `StoryBlock.rendered_text`。它只能分析刚才那个脱水的 JSON（`ir_json`），如果有必要，产生新的 `GrimoireEntity` Diff 给数据库（Lazy Instantiation）。

---

## 4. 全局核心铁律 (Gold Rules)

1. **Never OOC Rule:** 在 The Monitor 推演环节，所有 Character Agent 的 Prompt 必须从 `The Grimoire` 实时拉取最新上下文，不允许任何未记录的私设。
2. **Immutable IR Rule:** 一旦 Director 输出了 `ir_json` 并持久化，无论上层渲染文风如何变幻，推演产生的事实逻辑永不可被篡改（除非用户时光倒流废弃这个 Block）。
3. **No Direct World Edits Rule:** 涉及实体变更、记忆变更，必须交由 World Agent 判断或者 Muse 提供 Diff 视图让真人在前端点击 Approve 授权。
