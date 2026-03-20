# Genesis Engine (创世引擎)

**AI-Native Story Generation System — 让你成为故事的上帝**

> 不再是 AI 代笔，而是你作为导演，让 AI 角色们在你构建的世界里自动演戏。

---

## 设计理念

### 为什么选择 Genesis Engine？

传统 AI 写作工具存在三大痛点：

| 痛点 | 传统工具 | Genesis Engine |
|------|----------|----------------|
| **角色崩坏 (OOC)** | AI 容易遗忘初始设定 | Grimoire + 快照链，永不遗忘 |
| **节奏拖沓** | AI 顺延生成，缺乏张力 | Maestro 张力评分，主动把控冲突 |
| **文风平庸** | 无法区分视角和风格 | Camera Agent，精确控制 POV 和文风 |

### 核心理念：你不是打字机，你是上帝

Genesis Engine 将文学创作解耦为 **"发生"** 与 **"表达"** 两个独立阶段：

```
┌─────────────────────────────────────────────────────────────────┐
│                        创作工作流                                │
├─────────────────────────────────────────────────────────────────┤
│  用户意图 → Muse 解析 → Maestro 编排 → 角色博弈 → IR 脱水 → 渲染  │
│     ↓                                                        ↓  │
│  自然语言对话                           结构化剧情骨架 → 文学正文  │
└─────────────────────────────────────────────────────────────────┘
```

**你的角色**：导演 / 上帝 — 抛出冲突，观看推演，必要时干预
**AI 的角色**：演员 — 基于角色设定和动机，在你的世界里自主博弈

---

## 系统架构

### 四大核心 Agent

| Agent | 角色 | 职责 |
|-------|------|------|
| 🧚‍♀️ **The Muse** | 责编/助理 | 自然语言交互代理，翻译口语为系统操作 |
| 🎭 **Character** | 演员 | 每个角色独立 AI，基于隐藏动机在沙盒中博弈 |
| 🎛️ **The Maestro** | 指挥家 | 编排推演循环，评估张力，判定场景收束 |
| 🎥 **Camera** | 渲染大师 | 将结构化剧本渲染为文学正文 |

### 三层数据架构

```
The Grimoire (世界观)     — 角色属性、势力关系、世界规则
The Storyboard (大纲树)   — 卷 → 章 → Block 的故事骨架
The IR Block (剧本块)     — 单次推演的结构化输出，支持 LexoRank 任意插入
```

---

## 功能特性

### V1.0 核心引擎

- ✅ **Maestro 编排循环** — 异步回合制推演，张力评分，自动收束
- ✅ **3-Layer Prompting** — System / Scene / Director 三层提示组装
- ✅ **Story IR 结构化输出** — 脱水剧本块，支持任意位置插入
- ✅ **WebSocket 实时通信** — 推演状态实时广播

### V2.0 造梦控制台

- ✅ **The Muse Agent** — 自然语言交互，支持实体 CRUD、火花生成
- ✅ **The Monitor** — 实时推演监视器，状态时间线，角色调度日志
- ✅ **God's Hand** — 点击回合冻结，覆写角色意图，释放后继续推演
- ✅ **God's Pardon** — Maestro 拒绝动作时，一键 Override 强行通过
- ✅ **Render Mixer** — POV / Style / Subtext 三参数控制渲染风格
- ✅ **Vector Memory** — sqlite-vec + sentence-transformers，语义记忆检索

### V2.0 P1 命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `override_turn` | 微操推演 | "让宁毅态度再狂一点" |
| `adjust_render` | 调整渲染 | "潜台词多一点，风格改成肃杀风" |
| `create_branch` | 创建分支 | "在第 490 章切一个暗黑线分支" |
| `rollback` | 回滚快照 | "回到第 200 章的状态" |

---

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- SQLite 3 (支持 WAL 模式)

### 部署步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-repo/grimoire.git
cd grimoire
```

#### 2. 配置 LLM API

创建 `.env` 文件：

```bash
# 选择你的 LLM 供应商
LLM_MODEL=openai/qwen3.5-plus
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=your-api-key-here

# 或者使用 OpenAI
# LLM_MODEL=openai/gpt-4
# LLM_API_KEY=sk-xxx
```

#### 3. 启动后端

```bash
# 安装依赖
uv sync

# 启动服务
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

#### 5. 访问系统

打开浏览器访问 `http://localhost:5173`

---

## 使用指南

### 第一次使用：冷启动创作

Genesis Engine 采用 **"边演边建"** 策略，你不需要先填完所有设定表。

#### Step 1: 与 Muse 对话建立世界观

在右侧 **The Muse** 面板中输入：

```
我想写一个赛博朋克修仙的故事。主角是个搞笑道士，
别人修仙靠吐纳，他修仙靠赛博义体和物理超度。
```

Muse 会帮你提炼核心设定并请求确认：

```
太棒了！我建议设置：
- 主角：李玄机
- 核心武器：附魔加特林
- 隐藏动机：物理超度赚金币升级义体

确认这样修改吗？
```

回复 **"确认"**，设定即刻入库。

#### Step 2: 创建第一章

继续与 Muse 对话：

```
帮我构思第一章的冲突。道观快破产了，
有个赛博黑社会来讨债要拆道观。
```

Muse 会生成火花 (Spark)：

```
已创建第一章：大人时代变了
Spark: 道观讨债危机，主角李玄机准备物理超度
点击 [Confirm Spark] 开始推演
```

#### Step 3: 观看推演

点击确认后，**The Monitor** (底部面板) 开始显示实时推演：

```
[STATE] REASONING
[TURN 1] Maestro: 评估场景走向...
[DISPATCH] 李玄机 开始行动
[CHAR_STREAM] 李玄机: "大人，时代变了。"（掏出加特林）
[EVALUATING] 张力评分: 85/100
...
[SCENE_COMPLETE] 场景收束
```

#### Step 4: 上帝之手干预

如果觉得李玄机的态度不够狂：

1. 在 Monitor 中点击该回合
2. 进入 **冻结模式**
3. 输入新指令：`"更狂一点，边吃葡萄边说"`
4. 点击 **Release** 释放

后续角色会基于新设定继续推演。

#### Step 5: 渲染成文

推演完成后，在顶部 **Render Mixer** 设置：

- **POV**: OMNISCIENT / FIRST_PERSON / CHARACTER_LIMITED
- **Style**: 商战肃杀风 / 仙侠飘逸风 / 自定义
- **Subtext**: 0% (纯白描) ↔ 100% (意识流)

系统自动渲染出文学正文。

---

### 日常连载工作流

```
┌──────────────────────────────────────────────────────────────────┐
│                     每日创作循环                                  │
├──────────────────────────────────────────────────────────────────┤
│  1. 登录系统 → Grimoire 自动更新昨日状态                          │
│  2. 与 Muse 对话 → 确定今日冲突 (Spark)                           │
│  3. 观看推演 → Monitor 实时显示角色博弈                           │
│  4. 必要时干预 → God's Hand 冻结并覆写                            │
│  5. 设置渲染 → Render Mixer 控制文风                              │
│  6. Commit → Scribe 自动提取事实回写 Grimoire                     │
└──────────────────────────────────────────────────────────────────┘
```

### 进阶功能

#### 创建分支宇宙

在 Muse 中输入：

```
在第 490 章切一个分支，走暗黑路线
```

Muse 会创建一个独立的时间线分支，你可以探索不同的剧情走向而不影响主线。

#### 回滚到历史快照

```
回到第 200 章的状态
```

系统会恢复当时的所有角色属性和世界状态。

---

## 界面布局

```
┌──────────────────────────────────────────────────────────────────┐
│  [🧭 Compass] [🕸️ Network] [📚 Archive] [⚙️ Settings]   [The Muse] │
├────────────────┬─────────────────────────────────────────┬───────┤
│                │                                         │       │
│   The Compass  │           The Manuscript               │ Muse  │
│   ┌──────────┐ │  ┌─────────────────────────────────┐   │ Panel │
│   │ 大纲树    │ │  │                                 │   │       │
│   │ ├ 卷一   │ │  │         正文编辑器               │   │ 对话  │
│   │ │ ├ 章1  │ │  │                                 │   │ 历史  │
│   │ │ └ 章2  │ │  └─────────────────────────────────┘   │       │
│   └──────────┘ │  ┌─────────────────────────────────┐   │ 确认  │
│   ┌──────────┐ │  │         The Monitor              │   │ 卡片  │
│   │ 设定树    │ │  │  [STATE] [TURN] [LOGS] [ACTORS]  │   │       │
│   │ 角色/势力│ │  └─────────────────────────────────┘   │       │
│   └──────────┘ │                                         │       │
└────────────────┴─────────────────────────────────────────┴───────┘
```

---

## API 参考

### REST API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/muse/chat` | POST | 与 Muse 对话 (SSE 流式) |
| `/api/v1/sandbox/spark` | POST | 启动推演 |
| `/api/v1/sandbox/commit` | POST | 提交场景 |
| `/api/v1/sandbox/branch` | POST | 创建分支 |
| `/api/v1/sandbox/rollback` | POST | 回滚快照 |
| `/api/v1/render/adjust` | POST | 调整渲染参数 |
| `/api/v1/memory` | POST | 创建向量记忆 |
| `/api/v1/memory/search` | POST | 语义搜索记忆 |

### WebSocket 事件

| 事件 | 方向 | 描述 |
|------|------|------|
| `STATE_CHANGE` | 下行 | 状态机状态变更 |
| `TURN_STARTED` | 下行 | 新回合开始 |
| `DISPATCH` | 下行 | 角色被调度 |
| `CHAR_STREAM` | 下行 | 角色对话流 |
| `SYS_DEV_LOG` | 下行 | Maestro 推理日志 |
| `SCENE_COMPLETE` | 下行 | 场景完成 |
| `OVERRIDE` | 上行 | 发送上帝指令 |
| `CUT` | 上行 | 强制终止推演 |

---

## 开发指南

### 运行测试

```bash
# 后端测试
uv run pytest backend/tests/ -v

# 前端 E2E 测试
cd frontend && npm run test:e2e
```

### 代码风格

```bash
# 后端
ruff format backend/ && ruff check backend/ --fix

# 前端
cd frontend && npm run lint
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python 3.12 + FastAPI + aiosqlite + LiteLLM |
| **前端** | React 19 + TypeScript + Vite + Tailwind + Framer Motion |
| **数据库** | SQLite (WAL) + sqlite-vec (向量) |
| **LLM** | 多供应商支持 (OpenAI / Qwen / DeepSeek / ...) |

---

## 项目结构

```
grimoire/
├── backend/
│   ├── routers/          # API 路由
│   ├── crud/             # 数据库操作
│   ├── services/         # 业务逻辑 (LLM, Maestro, Camera)
│   ├── models.py         # Pydantic 模型
│   └── database.py       # SQLite 初始化
├── frontend/
│   ├── src/
│   │   ├── components/   # React 组件
│   │   ├── pages/        # 页面
│   │   └── lib/          # API 客户端, WebSocket
│   └── e2e/              # Playwright 测试
└── docs/                 # 设计文档
```

---

## 路线图

| 版本 | 目标 | 状态 |
|------|------|------|
| **V1.0** | 核心引擎：推演 → 脱水 → 渲染 | ✅ 完成 |
| **V2.0** | 造梦控制台：Muse + Monitor + God's Hand | ✅ 完成 |
| **V3.0** | 专业工作站：分支树、关系网、全文检索 | 📋 规划中 |

---

## 许可证

MIT License

---

## 致谢

Genesis Engine 的设计灵感来源于：

- 《赘婿》等顶级网文的长篇叙事智慧
- 《博德之门3》等 RPG 游戏的回合制推演机制
- Cursor 等 AI-Native 工具的交互范式

---

**愿每一位创作者都能成为自己故事的上帝。**