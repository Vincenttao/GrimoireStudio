# 📖 Genesis Engine 使用说明书

**版本:** V1.1 网文作坊版
**目标用户:** 中文网文连载作者
**最低要求:** Linux / macOS / Windows (WSL)，能装 Python 和 Node.js

---

## 目录

1. [一分钟了解](#一分钟了解)
2. [部署：本地一键起飞](#部署本地一键起飞)
3. [第一次使用：冷启动写第一章](#第一次使用冷启动写第一章)
4. [日常连载工作流](#日常连载工作流)
5. [核心概念速查](#核心概念速查)
6. [常见问题 & 故障排查](#常见问题--故障排查)
7. [成本预估](#成本预估)

---

## 一分钟了解

**你不是在用 AI 写作，你是在导演 AI 角色演戏。**

- 你给一个冲突（Spark），AI 角色（Character）按自己的设定博弈。
- Maestro 按你声明的 Beat 类型（装逼打脸 / 爽点兑现 / 悬念铺垫…）判定场景收束。
- Camera 按你指定的平台和字数把剧情骨架渲染成正文。
- 所有作品数据在一个本地 `.sqlite` 文件里，你想删就删、想送人就发。

核心承诺：**60-90 分钟一章 3000 字，单章 LLM 成本 ¥1 以内。**

---

## 部署：本地一键起飞

### 1. 环境要求

| 工具 | 版本 | 检查命令 |
|------|------|---------|
| Python | ≥ 3.12 | `python3 --version` |
| Node.js | ≥ 18 | `node --version` |
| uv（Python 包管理器） | 最新 | `uv --version` |
| git | 任意 | `git --version` |

**没有 uv？** 装它：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或者 pip install uv
```

### 2. 克隆项目

```bash
git clone <this-repo-url> GrimoireStudio
cd GrimoireStudio
```

### 3. 配置 LLM Key

复制示例环境文件：
```bash
cp .env.example .env
```

打开 `.env`，填上你的 API Key。**推荐 DashScope（阿里云百炼）**——支持中文网文调优、价格便宜、OpenAI 兼容接口：

```bash
LLM_MODEL=openai/qwen-turbo
OPENAI_API_KEY=sk-你自己的-dashscope-key
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

**申请 DashScope Key**：
1. 访问 https://dashscope.aliyuncs.com/
2. 用阿里云账号登录 → 创建 API Key
3. 复制到 `.env`

其他平台也支持（看你喜欢）：

```bash
# OpenAI
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-你的-openai-key

# DeepSeek
LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-你的-deepseek-key

# Anthropic Claude
LLM_MODEL=claude-3-5-haiku-latest
ANTHROPIC_API_KEY=sk-ant-你的-claude-key
```

### 4. 装依赖

**后端**（在项目根目录）：
```bash
uv sync
```

**前端**：
```bash
cd frontend
npm install
cd ..
```

### 5. 启动后端（第一个终端）

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

看到这行就 OK：
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 6. 启动前端（第二个终端）

```bash
cd frontend
npm run dev
```

看到这行就 OK：
```
  VITE v7.3.1  ready in 400 ms
  ➜  Local:   http://localhost:5173/
```

### 7. 打开浏览器

访问 **http://localhost:5173**

看到左侧侧边栏（Storyboard / Characters / Archive / Settings）+ 右侧 Muse 对话面板，就成了 ✅

---

## 第一次使用：冷启动写第一章

目标：**30 分钟内产出第一章 3000 字正文。**

### Step 1. 选目标平台（30 秒）

点左侧 **Settings** → 滚到 "网文作坊参数" → 目标平台下拉选你发文的站：
- 起点中文网（爽文 / 打脸多 / 默认 3000 字）
- 番茄小说（短句 / 节奏快 / 默认 2500 字）
- 晋江文学城（情感细腻 / 默认 4000 字）
- 纵横 / 七猫 / 自定义

点右上角 **Save Settings**。之后 Render Mixer 默认值会自动跟着平台走。

### Step 2. 创建主角（2 分钟）

点左侧 **Characters** → 右上角 **Create**。

**最少必填**：
- 姓名：如 `宁毅`
- 性格：如 `散漫玩世不恭，心思缜密`
- 核心动机：如 `让苏家撑下去，顺便找乐子`

**强烈建议展开 "声音签名 (VoiceSignature)"** 填：
- **口头禅** 1-2 个（如 `大人，时代变了`）
- **禁用词** 2-3 个（如 `宝宝`、`亲亲`）— 防止 AI 让角色说人设外的话
- **范本台词** 1-3 条（如 `风投比算命靠谱多了。`）

**再创建 1-2 个反派**（不带 VoiceSignature 也行，但主角必须有）。

> 💡 懒人走位：直接对右边 Muse 说 "帮我加一个主角叫宁毅，散漫道士，喜欢用科技修仙"，Muse 会用 **Markdown Diff** 展示修改，点 **确认执行** 即可入库。

### Step 3. 启动第一个 Spark（1 分钟）

**方式 A：Muse 对话**（推荐）
在右侧 Muse 输入：
```
写第一章：乌家派人来苏家门前勒索，宁毅用散漫态度反将一军，让对方下不来台。
```
Muse 会识别这是 **装逼打脸 (SHOW_OFF_FACE_SLAP)** 类型，生成一个 Tool Call 预览卡片，点 **确认执行**。

**方式 B：卡文救急**
如果不知道写什么，点 Muse 顶部 🆘 **救生圈图标**。它会基于当前世界生成 3 个方向的候选（激烈冲突 / 情感转折 / 日常过渡），点 "选这个开推"。

### Step 4. 观看推演（5-15 分钟）

左下角的 **The Monitor** 会实时显示：
- 🎬 Maestro 思考过程（SYS_DEV_LOG）
- 🎭 哪个角色行动中（DISPATCH + CHAR_STREAM）
- 📊 回合推进（TURN_STARTED）
- ✅ 场景收束（SCENE_COMPLETE）

**中途想改戏？** 点 Monitor 里某个回合 → 输入新指令（如 "让宁毅态度再狂一点"）→ 点 **Release**。Maestro 在下一回合之前会注入这个导演备注。

**想强制结束？** 点 **CUT** 按钮。

### Step 5. 渲染成文（2-3 分钟）

推演完成后，中央区域会出现一个 **Render** 按钮。确认右上角 Render Mixer 的 POV / 文风 / 字数 / 潜台词 / 平台，点 **Render**。

Camera 会：
1. 按 `target_char_count` 渲染（首轮 → 如果 ±10% 内不达标 → 自动 expand/shrink 重试 ≤3 次）
2. 跑章末 **Hook Guard**：检查最后 200 字是否有悬念。没有的话自动重渲染结尾段。
3. 跑水字数检测：同事件重复 3 次 / 长描写 > 500 字 / 对白占比 < 20% 会警告（只提示不自动改）。

### Step 6. 确认提交（30 秒）

满意了点 **Commit** 按钮（或对 Muse 说 "提交这一章"）。

Commit 做四件事：
1. 把最终 HTML 存进 `story_ir_blocks`。
2. 合并所有**待确认的事实修订（SoftPatch）** 进新快照。
3. 连胜 +1 🔥（Sidebar 会显示"连续日更 X 天"）。
4. Scribe 从 IR 提取事实（加物品、伤健康、关系变化），写回角色的 `current_status`。

---

## 日常连载工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                      每天 60-90 分钟一章                         │
├─────────────────────────────────────────────────────────────────┤
│  1. 开项目 → Muse 问候"昨天写到第 X 章，今天..."                 │
│  2. (可选) 点 🆘 卡文救急 → 选方向                              │
│  3. 和 Muse 对话 → Spark（含 beat_type + 目标字数）             │
│  4. Monitor 里看推演 → 必要时 Override                          │
│  5. 推演完成 → Render → 自动对字数 + 钩子守卫                    │
│  6. 自己润色几句（改 HTML 不会掉 Grimoire 记忆）                │
│  7. 如果改了事实（金额/武器）→ 右键"告诉 Muse 这里改了事实"     │
│  8. Commit → 连胜 +1 🔥                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 润色正文的规矩

**改 HTML 随便改** — Camera 下次渲染不会重读，Scribe 也不会看散文。

**改了**事实**（金额、武器、时间线、人物关系）必须告诉 Muse**：
- 方式 A：对 Muse 说 "把第 17 段的 3000 两改成 300 两，苏家账本错了"
- Muse 会生成一个 `apply_soft_patch` Tool Call，点确认 → 下次 Commit 合并入快照

**禁止**：直接去 Characters 页手动改 `inventory` 或 `relationships`——那是 Scribe 的领地，手动改会被下一轮推演覆盖。

### 微操推演（God's Hand）

推演过程中点 Monitor 里某个角色回合：
- **Override**：输入 "让他态度再狂一点" / "这里加一句暗讽苏家"
- **Release**：Maestro 下一回合前注入这个导演备注

推演完了不能 Override 了——用"局部批改"改 HTML 或重推一遍。

### 换一个平台渲染

想把起点连载的稿子改投晋江？
- Settings → 目标平台改 JINJIANG → Save
- 顶部 Render Mixer 默认值会变（潜台词 0.6、字数 4000、江南烟雨风）
- 对之前章节的 Render 按钮重点一次（IR 不变，只重新渲染表达）

---

## 核心概念速查

| 概念 | 一句话 | 在哪用 |
|---|---|---|
| **Spark** | 一段"帮我写某个冲突"的指令 + Beat 类型 + 目标字数 | Muse 对话发起 |
| **Beat Type** | 声明这段戏是哪种（装逼打脸/爽点兑现/悬念铺垫/...） | Spark 必填，Maestro 按此专项判完成 |
| **VoiceSignature** | 角色的口头禅/禁用词/范本台词 | 创建角色时填，Scribe 自动检测 OOC |
| **SoftPatch** | 作者手动改事实的软层 delta | Muse 打 "告诉我改了事实"，Commit 时合并 |
| **Platform** | 起点/番茄/晋江/纵横/七猫 | Settings 选一次，所有默认值跟着走 |
| **Hook Guard** | 章末悬念守卫，不合格自动重渲染结尾 | 默认开启，Settings 可关 |
| **Padding Detector** | 水字数检测（只警告不改） | 默认开启 |
| **连胜（Streak）** | 连续日更天数 | 每次 Commit +1，断更 24h 重置 |
| **Commit** | 锁定本章 + 合并 SoftPatch + 更新连胜 | 每章最后一步 |

### Beat 类型对照表

| 声明 | 网文术语 | 完成判据 |
|---|---|---|
| `SHOW_OFF_FACE_SLAP` | 装逼打脸 | 主角展示 + 反派外显挫败 + 地位反差 |
| `PAYOFF` | 爽点兑现 | 前期铺垫的承诺回报事件出现 |
| `SUSPENSE_SETUP` | 悬念铺垫 | 埋下可追溯的未解冲突 |
| `EMOTIONAL_CLIMAX` | 情感升华 | 角色情感外化的关键对白/动作 |
| `POWER_REVEAL` | 金手指展示 | 能力展示且被见证，效果碾压 |
| `REVERSAL` | 反转 | 强弱易位 / 信息反转 |
| `WORLDBUILDING` | 世界观补完 | 至少 2 条可抽取为 Grimoire 条目的新设定 |
| `DAILY_SLICE` | 日常流 | 达到字数即可收束，无硬要求 |

---

## 常见问题 & 故障排查

### Q1. Muse 不回消息 / 永远 loading

**检查**：
1. 右侧 Sidebar 底部是不是 **OFFLINE**？→ 后端 `uvicorn` 是否在跑？`curl http://localhost:8000/health` 应返回 `{"status":"ok"}`。
2. `.env` 里的 `OPENAI_API_KEY` 填对了吗？
3. 看后端终端里的日志：如果有 `LLMError: No API key found`，就是 Key 问题。

### Q2. 推演 3 分钟都不出东西

**原因**：模型慢。`qwen3.5-plus` / `gpt-4` 一次调用 10-30 秒，一个推演 5-10 轮就要 1-5 分钟。

**方案**：
- `.env` 改 `LLM_MODEL=openai/qwen-turbo`（3-10 秒/次）或 `deepseek-chat`
- 或去 Settings 把 `max_turns` 从 12 改成 8

### Q3. 字数怎么算都不对（要 3000，给 2200）

**检查**：
1. Camera 会自动重试 3 次。3 次后仍不达标会直接返回实际字数。
2. Settings 里 `default_target_char_count` 设对了吗？
3. 你的 IR 本身可能信息量就不够 3000 字——推演再多几轮让 Character 说更多话。

### Q4. 角色突然说出奇怪的词（"宝宝" / "亲亲" 之类）

**方案**：
1. 打开 Characters → 编辑该角色 → 展开 **声音签名** → 往 **禁用词** 里加"宝宝"。
2. 下次推演 Scribe 会在 Commit 前 grep 检测，命中就会阻断 Commit 要求重生成。

### Q5. 渲染完的章节末尾太平，没钩子

V1.1 默认开启 **Hook Guard**，应该已经自动重渲染结尾了。如果还是平：
1. Settings 确认 "章末钩子守卫" 勾上了
2. Spark 时声明 `beat_type=SUSPENSE_SETUP`（悬念铺垫）
3. 最后一招：对 Muse 说 "把第 23 章结尾重写，要有悬念"

### Q6. 一推演就崩溃丢稿？

V1.1 有 `scratchpad.jsonl` 持久化：所有 Turn Log 追加写到磁盘，进程崩了重启时可恢复。

**恢复**：
- 重启后端时看日志，如果检测到未完成的 trace，会在 `sandbox_recovery` 表记录一条。
- 当前版本恢复 UI 没做完，手动方式：看 `scratchpad.jsonl` 找到 `event: STARTED` 但没有对应 `event: COMMITTED` 的 trace_id，把里面的 turn_logs 复制出来自己决定重推还是放弃。

### Q7. 我改了 HTML，下一章推演怎么没同步？

**这是设计**，不是 bug。改 HTML 只是润色表达，Scribe 不会读散文，Grimoire 不会变。

如果你改的是**事实**（金额/武器/身份），走 SoftPatch 通道：对 Muse 说 "把第 X 段的 Y 改成 Z"。

### Q8. 怎么换电脑继续写？

把 `grimoire.sqlite` 这一个文件复制到新电脑的项目根目录即可。**就这一个文件包含你所有作品。**

（也可以复制 `scratchpad.jsonl` 如果有未完成推演想继续。）

### Q9. 我想把作品导出成 txt / epub 给朋友看？

V1.1 暂未实现一键导出。临时方案：
```bash
sqlite3 grimoire.sqlite "SELECT content_html FROM story_ir_blocks ORDER BY chapter_id, lexorank;"
```
然后自己处理 HTML。

V3.0 会加一键导出（txt / epub / 各平台 Markdown）。

### Q10. 忘记 Commit 关电脑了，连胜会断吗？

V1.1 的连胜规则：
- 上次 Commit 距今 < 24h：今天再 Commit 不加天数（同一天内多次 Commit 不刷）
- 24-48h：+1 天
- > 48h：从 1 天重新开始

所以如果你是凌晨 2 点写完，睡醒 10 点再写，连胜会 +1（<24h + 下一日）。

---

## 成本预估

**单章（3000 字）典型 Token 用量：**

| 角色 | 调用次数 | 平均 token | 模型 | 成本（起点） |
|------|---------|------------|------|------|
| Maestro 决策 | 5-8 | 2-4k | qwen-turbo | ¥0.05-0.15 |
| Character Agent | 3-6 | 1-2k | qwen-turbo | ¥0.03-0.10 |
| Maestro 评分 | 3-6 | 1-2k | qwen-turbo | ¥0.02-0.08 |
| Camera 渲染 | 1-3 | 3-8k | qwen-turbo | ¥0.05-0.30 |
| Hook Guard | 0-1 | 500 | qwen-turbo | ¥0.01 |
| **合计** | | | | **¥0.15-0.65 / 章** |

**用 qwen-plus 渲染层**：
- Camera 换 qwen-plus → +¥0.30-1.00 / 章
- 合计约 **¥0.5-1.5 / 章**

**100 章长篇**：
- 全 qwen-turbo：**¥15-65**
- 渲染 qwen-plus：**¥50-150**

对比 GPT-4.6 全线：**$100-300**（¥700-2100）。

**省钱 tips**：
1. Maestro / Scribe / unblock_writer 永远用最便宜的（qwen-turbo / deepseek-chat）
2. 只 Camera 渲染偶尔切 qwen-plus
3. 进 Settings 把 `max_turns` 从 12 降到 8-10（减少 20-30% Token）
4. 写日常流章节时声明 `DAILY_SLICE`，Maestro 判据最松，少推几轮

---

## 下一步想了解什么？

- **开发者**：看 `CLAUDE.md` 了解代码架构，`docs/SPEC.md` 了解技术契约。
- **想扩展功能**：看 `docs/PRD_Genesis.md` §4 版本路线图，V2.0 / V3.0 已规划的东西。
- **想贡献代码**：看 `AGENT.md` 了解 TDD 规范和测试怎么跑。

---

**祝你日更不断更，码字不卡文。** 🔥
