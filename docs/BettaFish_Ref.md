# 🐟 BettaFish 架构解析与“创世引擎”映射指南

本文档总结了从开源项目 [BettaFish (微舆)](https://github.com/666ghj/BettaFish) 中提取的核心多智能体架构思想，并映射说明其如何支撑我们在 `PRD_Genesis.md` 中定义的“Story Gods (创世引擎)”范式。

## 1. 核心架构：多 Agent 圆桌会议 (The Forum Debate)

### 1.1 BettaFish 的做法
BettaFish 并不依赖单个万能的 LLM 来一次性输出长篇报告。相反，它构建了一个“论坛 (Forum)”，让三个职能极其细分的 Agent 在其中交互：
*   **Insight Agent:** 专攻私有数据库挖掘。
*   **Media Agent:** 专攻多模态。
*   **Query Agent:** 专攻公网情报搜索。

**协作机制 (`monitor.py` & `llm_host.py`)：**
*   Agent 们在各自的日志中“发言”（输出带有自己视角的分析 JSON）。
*   `monitor.py` 实时监听这些日志，当某个节点产出有效的内容（例如 `SummaryNode`），它提取脱水后的结论，贴到共享黑板 (`forum.log`) 上。
*   当黑板上积攒了 N 条发言后，触发 **Host (论坛主持人)**。
*   主持人审视全局发言，主动“**拉偏架**”（指出各个数据源的矛盾、提出尖锐问题、引导后续深入挖掘的方向），再将新任务下发给各个 Agent 开启下一轮辩论。

### 1.2 Genesis Engine 的映射：The Autonomous Stage
*   **演员 (Character Agents):** 相当于 BettaFish 的三个分析 Agent。每个角色只基于自己的性格（Persona）、目标（Motive）和已知情报在舞台上丢出 `[意图] 与 [动作]`。
*   **导演 (The Showrunner):** 相当于 BettaFish 的 Host。它监控全场的戏剧张力。当发现两个角色互相推诿、节奏拖沓（“水字数”）时，导演立刻抛出环境突变（`Plot Twist`，如：突然停电、警察破门而入），强制推进剧情。

---

## 2. 核心范式：数据清洗组装与文学渲染的隔离

### 2.1 BettaFish 的做法 (Script IR & Stitching)
在 BettaFish 中，无论前端 Agent 怎么吵架、生成了多少文字，最终真正落盘成报告的，是 `ReportEngine` 中极为严密的一套管线：
1.  **JSON 契约 (`schema.py`):** 定义了 `HeadingBlock`, `ParagraphBlock`, `TableBlock` 等极度结构化的格式。LLM 的最终输出必须严格符合这个 Schema，不带任何 Markdown 修饰。这被称为 **中间表示 (Document IR)**。
2.  **原子装订 (`stitcher.py`):** 这是一个**纯 Python 代码，不调用任何大模型**的装订器。它将各个章节的 IR 按顺序组装，为每个段落注入唯一的防冲突锚点 (Anchor)，加上版本号和时间戳。
3.  **最终渲染 (`html_renderer.py` / `pdf_renderer.py`):** 将干瘪的 JSON 灌入指定的 CSS 模板，生成可供阅读的漂亮报告。

### 2.2 Genesis Engine 的映射：Render Mixer
这个“业务逻辑与展示层彻底分离”的思想是解决 AI 小说“一修改就全乱”、“文风不稳定”的终极解药：
1.  **脱水剧本 (Story IR):** 我们的 Director Agent 的唯一职责，就是把黑盒辩论环节（Forum Debate）的长篇大论，压缩打包成一份类似 `schema.py` 的 JSON（谁、在什么情境、有什么潜台词、说了什么话）。这个阶段，剧情逻辑被“锁死”。
2.  **幂等渲染 (Camera Agent):** Camera Agent 就是 `html_renderer` 的升级版。用户通过调整混音台（Render Mixer）的参数（换视点、改文风），系统只是把那份“干瘪且不变”的 `Story IR` 重新发给最聪明的模型进行文学加工。因为逻辑锚定在 IR 上，所以**无论怎么重绘（Retries），剧情都不会发生蝴蝶效应般的变异（免除了 OOC 灾难）**。

---

## 3. 技术工程实践启示

### 3.1 鲁棒性重试机制 (Resilience)
*   **BettaFish:** 在 `ReportEngine/agent.py` 中，当发现 LLM 生成的章节 JSON 损坏（解析失败）或内容字数过低（Content Sparse），它不会立刻崩溃，而是最多重试 N 次，并在实在不行时使用保留的“最佳残缺版”兜底，同时通过 SSE 给前端发送 `retrying` 事件。
*   **启示:** 我们的 Genesis 渲染管线同样极其依赖 JSON（Story IR 提取和渲染）。必须引入这种多级重试和自动修复机制，防止一次生成失败导致整个剧本卡死。

### 3.2 纯事件驱动流 (SSE/WebSockets)
*   **BettaFish:** 它的主调代码里充斥着 `emit('stage', ...)` 或 `emit('chapter_chunk', ...)`，把 LLM 的思考过程、报错、重试等所有的黑盒状态实时推送给前端。
*   **启示:** 我们在推演态 (The Monitor) 的体验核心就在于“看 AI 演戏”。因此，后端到前端的数据链路禁止使用传统的厚重 HTTP API 轮询，必须完全依赖 WebSockets 发射精确的 UI State Reducer 事件。

### 3.3 本地 LexoRank 生态融合
*   BettaFish 的 `stitcher.py` 是基于简单的 `idx` 排序的。但在 Grimoire (Genesis) 中，我们要在此基础上全面融入现有的 `LexoRank` 体系。
*   所有的 `Story IR` 区块在入库时，必须挂载字符串形式的 LexoRank。这样在 Tiptap 中用户拖拽打乱段落，或者导演插入新剧情时，能保证完全的 O(1) 性能和全局一致性。
