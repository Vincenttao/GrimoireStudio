# 🤖 Project Genesis: AI 编程与架构纪律 (RULES.md)

**用途:** 规范 AI 编程助手（Agent）在撰写、修改底层代码与系统架构时的行为边界。
**状态:** 强制执行 (Strict Enforcement)

---

## 1. 核心架构纪律 (Architectural Strictness)

### 1.1 防患于未然 (No Silo Coding)
*   **动作准则:** 在撰写或修改任何后端接口或前端组件前，**必须**查阅并严格遵循 `docs/SPEC.md` 中定义的 JSON Schema 与架构策略。
*   **禁止操作:** 严禁 AI 编造不存在于该文档中的字段，或擅自改变（如将串行改并行）核心状态机运转逻辑。如果在代码实现中发现 SPEC 不合理，必须先在规划阶段（PLANNING）向用户指出，并优先修改 `SPEC.md`。

### 1.2 物理隔离架构 (Strict Separation of Concerns)
*   **动作准则:** 必须坚决捍卫“渲染”（Camera/Tiptap）与“逻辑”（Maestro/Story IR）的物理隔离。
*   **禁止操作:** 绝对不允许把最终生成的散文体内容传回给 The Maestro 或 Scribe 用于历史追溯；历史追溯只能使用 `Story IR Block`。

---

## 2. Agent IO 与 LLM 交互守则 (LLM Integration Standards)

### 2.1 强制 JSON 与容错 (Strict JSON & Fallbacks)
*   **动作准则:** 所有非 Camera Agent 的系统级调用，Prompt 必须明确要求输出 JSON 格式。代码侧必须实现健壮的解析器（例如 Pydantic 或 Zod），并捕获 `JSONDecodeError`。
*   **禁止操作:** 严禁信任大模型的直接输出内容。不能使用正则匹配进行核心业务字段提取（除非处于极其极端的容灾降级模式）。

### 2.2 零硬编码系统指令 (Zero Hardcoded Prompts)
*   **动作准则:** 系统指令（System Prompts）必须独立存放在单独的文件模块（如 `agents/prompts/maestro_v1.txt`），或作为一个常量配置注入。
*   **禁止操作:** 严禁将大段的 LLM 提示词硬编码在核心业务逻辑函数（如 `fetch_character_reply()`）的底层方法体内。

---

## 3. 并发、锁定与数据纪律 (Concurrency, Locking & Data)

### 3.1 状态机的强一致性 (State Machine Enforcing)
*   **动作准则:** 推演沙盒是“严格的串行回合制”。代码中必须使用显式状态机（或加锁机制）保证同一时间只有一个角色或主控节点在发言（除非后期 SPEC 明确演进为并发模型）。

### 3.2 绝对不可变性约定 (Immutability by Default)
*   **动作准则:** 为了不堵死向未来 V3.0（平行宇宙和回档）的演进，所有业务数据的流转默认使用追加日志（Append-only Logs）而非原地修改（In-place Updates）。不要随意使用 SQL 的 `UPDATE` 去覆写过去剧情的状态。

---

## 4. 异步通信守则 (Async Communication)

### 4.1 全局流式优先 (Streaming Preferred)
*   **动作准则:** 后端 FastApi 或任何 API 层，在调度 Character、Camera 等大模型输出时，应优先采用 SSE (Server-Sent Events) 或 WebSockets 向前端推送状态增量（Delta），确保 Monitor UI 的即时律动感。
*   **禁止操作:** 不要使用长轮询（Long Polling）来检查推演状态。

---

## 5. 前端界面的极简呈现准则 (Minimalist UI Guidelines)

### 5.1 永远的“唯一稿纸” (The One Manuscript)
*   **禁止操作:** 绝不允许在前端代码中编写任何**遮挡正文编辑区**的模态弹窗（Modals）或系统提示框（Alerts）。系统通知或确认逻辑必须全部下放给 `The Muse` 进行对话交互式确认，或采用原地的浮窗 (Inline Popovers/Toasts)。
