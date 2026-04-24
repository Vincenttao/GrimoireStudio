# Genesis Engine（创世引擎）

**AI-Native 网文日更作坊 — 你当导演，AI 角色演戏**

> 不是 AI 代笔，是你抛出冲突、AI 角色在沙盒里博弈、Camera 按你要的平台和字数渲染成正文。
> 60-90 分钟一章 3000 字，单章 LLM 成本 ¥1 以内，角色永不 OOC。

**当前版本：V1.1 网文作坊版**｜**北极星用户：中文网文连载作者**

---

## 谁该用这个

**服务：** 连载中的中文网文作者（起点 / 番茄 / 晋江 / 纵横 / 七猫）

**不服务：** 英文小说、剧本杀、学术写作、多人协作团队、严肃文学（架构为日更连载特化，其他场景请找别的工具）

## 核心痛点与答卷

| 传统 AI 写作的坑 | Genesis 怎么解 |
|---|---|
| 角色崩坏（OOC） | **VoiceSignature** 规则检测：口头禅 / 禁用词 / 范本台词，grep 级拦截 + Grimoire 快照链 |
| 节奏拖沓 / 流水账 | **Maestro 按 beat_type 专项判完成**：装逼打脸 / 爽点兑现 / 悬念铺垫 / 反转 等 8 种网文 Beat |
| 文风平庸 / 字数不准 | **Camera 字数硬约束**（±10% 自动 expand/shrink） + **章末钩子守卫** + **平台预设**（起点/番茄/晋江） |
| 改一句话要重推整段 | **SoftPatch 软层 delta**：作者手动改事实不改历史快照，Commit 时合并 |
| 卡文断更 | **[卡文救急]** 一键：基于最近章节生成 3 个不同方向的 Spark 候选 |
| Token 成本失控 | High/Low 模型路由 + 平台预设默认 qwen-turbo，单章 ¥0.3-1 |

---

## 核心架构（四大 Agent + 状态机）

```
       用户意图
          │
          ▼
   ┌─────────────┐      ┌──────────────────┐
   │  🧚‍♀️ Muse  │──►│ 双模：写稿 / 设定 │
   └──────┬──────┘      └──────────────────┘
          │ Spark（含 beat_type + target_char_count）
          ▼
   ┌─────────────┐
   │ 🎛️ Maestro │ ◄── 按 beat_type 判据循环
   └──────┬──────┘
          │ Dispatch
          ▼
   ┌─────────────┐      ┌──────────────────┐
   │ 🎭 Character│──►│ 3-Layer Prompt   │
   └──────┬──────┘      └──────────────────┘
          │ Turn Logs
          ▼
   ┌─────────────┐      IR Block（不可变）
   │ IR 提取     │──┐
   └─────────────┘  │
                    ▼
   ┌─────────────┐      ┌──────────────────┐
   │ 🎥 Camera   │──►│ 字数约束 + 钩子守卫│
   └──────┬──────┘      └──────────────────┘
          │ content_html
          ▼
   ┌─────────────┐
   │ 📜 Scribe   │──►  VoiceSignature 校验 → Grimoire Snapshot
   └─────────────┘
```

**三层数据架构：**
- **Grimoire（世界观）** — 角色、势力、地点、关系；快照链记录所有变更
- **Storyboard（大纲树）** — 卷 → 章 → Block；LexoRank 任意插入
- **Story IR Block** — 单次推演的结构化输出，**推演逻辑不可变**，仅 `content_html` 可重渲染

## V1.1 关键能力

| 能力 | 一句话 |
|---|---|
| 🎯 **beat_type** | 8 种网文 Beat，Maestro 按声明的类型专项判完成 |
| 🔒 **VoiceSignature** | 角色的口头禅 / 禁用词 / 范本台词，Scribe 自动 OOC 检测 |
| 📏 **字数硬约束** | 目标字数 ±10% 自动循环调整（expand/shrink） |
| 🪝 **钩子守卫** | 章末 200 字无悬念自动只重渲染结尾段 |
| 📡 **平台预设** | 起点/番茄/晋江/纵横/七猫，一键切换 Render Mixer 默认值 |
| ✏️ **SoftPatch** | 手动改事实走软层 delta，不脏化历史快照 |
| 🆘 **卡文救急** | 一键生成 3 个 Spark 候选，方向不同（激烈/情感/日常） |
| 💾 **Scratchpad 持久化** | 推演日志追加到 JSONL，进程崩了能恢复 |
| 🔥 **日更连胜** | Commit 自动 +1 天，断更 >48h 重置 |

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/Vincenttao/GrimoireStudio.git
cd GrimoireStudio

# 2. 配置 LLM（推荐 DashScope qwen-turbo，~¥0.5/章）
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 3. 装依赖
uv sync && (cd frontend && npm install)

# 4. 起后端（第一个终端）
uv run uvicorn backend.main:app --reload --port 8000

# 5. 起前端（第二个终端）
cd frontend && npm run dev
```

打开 **http://localhost:5173**。

**完整部署 + 第一次使用 + 日常流 + FAQ 见 [USAGE.md](./USAGE.md)。**

## 文档索引

| 文件 | 用途 |
|---|---|
| [USAGE.md](./USAGE.md) | **使用说明书** — 部署 / 冷启动 / 日常流 / FAQ / 成本预估 |
| [CLAUDE.md](./CLAUDE.md) | 代码架构指引（给开发者） |
| [docs/PRD_Genesis.md](./docs/PRD_Genesis.md) | 产品需求文档（含北极星用户、V1.1/V2.0/V3.0 路线图） |
| [docs/SPEC.md](./docs/SPEC.md) | 技术契约（Schema / 状态机 / API） |
| [docs/USER_PERSONA.md](./docs/USER_PERSONA.md) | 用户画像 + 平台分层 + Token 预算 |
| [docs/Architecture_Design.md](./docs/Architecture_Design.md) | 架构设计（Snapshot Chain / 3-Layer Prompt） |
| [AGENT.md](./AGENT.md) | 开发工作流 + TDD 规范 |

---

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 + FastAPI + aiosqlite + LiteLLM + Pydantic V2 |
| 前端 | React 19 + TypeScript + Vite + Tailwind + Framer Motion + wouter |
| 数据 | SQLite (WAL) — **单个 `.sqlite` 文件 = 整个作品** |
| LLM | 多供应商（OpenAI / DashScope / DeepSeek / Anthropic / 自定义 OpenAI 兼容端点） |
| 测试 | pytest + Playwright |

**工程原则：**
- 程序化编排 > 自主 Agent（Maestro 用确定的 for 循环，不搞 LangGraph 式自主路由）
- 单用户单体 > 微服务（FastAPI 单进程 + SQLite 单文件）
- 快照链 > 事件溯源（append-only，支持任意回档）
- 本地优先 > SaaS（无账号、无云同步、无 Langfuse / OpenTelemetry 等外部依赖）

## 成本预估

单章 3000 字典型消耗（默认 qwen-turbo）：

| 环节 | 调用次数 | 成本 |
|---|---|---|
| Maestro 决策 + 评分 | 5-8 次 | ¥0.07-0.23 |
| Character 发言 | 3-6 次 | ¥0.03-0.10 |
| Camera 渲染 | 1-3 次 | ¥0.05-0.30 |
| Hook Guard + VoiceSig | 0-1 次 | ¥0.01 |
| **合计** | | **¥0.15-0.65 / 章** |

**100 章长篇：¥15-65**（对比 GPT-4 全线 ~¥2000）。详见 [USAGE.md §成本预估](./USAGE.md)。

---

## 版本路线图

| 版本 | 目标 | 状态 |
|---|---|---|
| **V1.0 Core Engine** | 推演 → 脱水 → 渲染核心管线 | ✅ 完成 |
| **V1.1 Web Novel Workshop** | 网文作者日更特化（beat_type / 字数 / 钩子 / VoiceSignature / 平台预设 / SoftPatch / 卡文救急） | ✅ **当前版本** |
| **V2.0 Co-Pilot** | 爽点节奏表、模拟读者反馈、VoiceSig 漂移追踪、Token 预算前瞻、FTS5 全文检索 | 📋 规划中 |
| **V3.0 Studio** | 百万字长篇专业工作站、多分支漫游、一键导出多平台 | 📋 规划中 |

## 项目结构

```
GrimoireStudio/
├── backend/              # FastAPI 单体
│   ├── main.py           # App 入口 + 路由注册
│   ├── models.py         # Pydantic V2 Schema（BeatType / VoiceSignature / SoftPatch ...）
│   ├── database.py       # SQLite WAL + schema 迁移
│   ├── routers/          # HTTP / WebSocket 端点
│   ├── services/         # Maestro 循环 / Camera / LLM client / WS manager
│   ├── crud/             # 数据访问（含 soft_patches / scribe / entities）
│   └── tests/            # pytest（含 test_v1_1_web_novel.py 33 条端到端）
├── frontend/src/
│   ├── components/       # MusePanel / Monitor / RenderMixer / CharacterModal ...
│   ├── pages/            # Storyboard / Characters / Archive / Settings
│   └── lib/              # api.ts / ws.ts / utils.ts
├── docs/                 # PRD / SPEC / Architecture / USER_PERSONA
├── USAGE.md              # 用户使用说明书
├── CLAUDE.md             # 代码架构指引
└── e2e_smoke.py          # 真 LLM 端到端烟雾测试
```

## 开发

```bash
uv run pytest backend/tests/ -m "not llm" -v   # 单元 + 端到端（不调真 LLM）
uv run pytest backend/tests/ -m llm -v         # 带真 LLM 的联通测试（需 .env 配置）
uv run python e2e_smoke.py                     # 真 DashScope 烟雾测试

ruff format backend/ && ruff check backend/ --fix
cd frontend && npm run lint && npm run build
```

## License

MIT

## 致谢

设计灵感：
- 《赘婿》等顶级网文的长篇叙事结构（宁毅 / 苏檀儿是架构讨论的默认举例角色）
- 《博德之门3》的回合制推演与掷骰干预机制
- MemGPT / Pi Agent 的有状态认知循环
- Cursor / Claude Code 的 AI-Native 交互范式

---

**愿你日更不断更，码字不卡文。** 🔥
