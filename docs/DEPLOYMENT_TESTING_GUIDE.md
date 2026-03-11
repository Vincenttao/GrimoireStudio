# Genesis Engine MVP — 部署与测试指南

## 1. 环境准备

### 系统要求
| 依赖 | 最低版本 | 用途 |
|:---|:---|:---|
| Python | 3.12+ | 后端运行时 |
| Node.js | 18+ | 前端构建 |
| uv | 0.4+ | Python 包管理 |
| npm | 9+ | 前端包管理 |

### 克隆与安装

```bash
# 1. 进入项目
cd grimoire

# 2. 安装后端依赖
uv venv && uv pip install -r backend/requirements.txt

# 3. 安装前端依赖
cd frontend && npm install && cd ..
```

---

## 2. 启动服务

### 后端 (FastAPI + SQLite)

```bash
# 从项目根目录启动
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

验证：访问 `http://localhost:8000/health`，应返回 `{"status": "ok"}`

### 前端 (Vite + React)

```bash
cd frontend && npm run dev
```

验证：访问 `http://localhost:5173/`，应看到暗色主题侧边栏 + The Muse 聊天界面

> [!NOTE]
> 前端 Vite 已配置代理，`/api/*` 和 `/ws/*` 请求自动转发至后端 `localhost:8000`

> [!IMPORTANT]
> **WSL2 用户须知：** WSL2 的网络为独立虚拟网段，服务必须绑定 `0.0.0.0` 才能被 Windows 宿主机通过 `localhost` 访问。后端已在启动命令中添加 `--host 0.0.0.0`，前端已在 `vite.config.ts` 中配置 `host: true`。

---

## 3. 运行自动化测试

```bash
# 从项目根目录运行全部后端测试
uv run pytest backend/tests/ -v

# 仅运行指定测试套件
uv run pytest backend/tests/test_database.py -v    # 数据库 WAL 模式
uv run pytest backend/tests/test_models.py -v      # Pydantic 模型校验
uv run pytest backend/tests/test_maestro.py -v     # Maestro CUT 打断
uv run pytest backend/tests/test_api.py -v         # REST API 集成
uv run pytest backend/tests/test_crud.py -v        # CRUD + Scribe Delta

# 前端类型检查
cd frontend && npx tsc --noEmit
```

**预期结果：14 tests passed, 0 errors**

---

## 4. 手动测试用例

### 测试用户角色定义

以下是 3 组预设的测试角色数据，覆盖不同的实体类型和复杂度：

---

### 👤 测试角色 1：Artemis Blackthorn（主角）

```json
{
  "entity_id": "char-001-artemis",
  "type": "CHARACTER",
  "name": "Artemis Blackthorn",
  "base_attributes": {
    "aliases": ["The Shadow", "Art"],
    "personality": "冷静、精于算计，但内心深处渴望被接纳。表面的冷漠是对过往伤痛的盾牌。",
    "core_motive": "找到失落的家族魔典，解开血脉诅咒。",
    "background": "出生于没落的术士家族。12岁时家族惨遭屠灭，独自在黑市成长为顶级情报贩子。左臂有一道银色的诅咒纹路，每到月圆之夜会剧烈疼痛。"
  },
  "current_status": {
    "health": "85/100",
    "inventory": ["暗影匕首", "情报密函", "月光药剂 x2"],
    "relationships": {
      "char-002-elena": "信任但保持距离的搭档",
      "char-003-voss": "宿敌，杀父仇人"
    },
    "recent_memory_summary": [
      "在酒馆暗道中从线人处得到了魔典的线索",
      "与 Elena 发生了激烈争执，但最终达成了合作协议"
    ]
  },
  "is_deleted": false,
  "created_at": "2026-03-11T10:00:00+08:00",
  "updated_at": "2026-03-11T10:00:00+08:00"
}
```

---

### 👤 测试角色 2：Elena Rosewood（搭档）

```json
{
  "entity_id": "char-002-elena",
  "type": "CHARACTER",
  "name": "Elena Rosewood",
  "base_attributes": {
    "aliases": ["The Healer"],
    "personality": "热情、正义感极强，容易冲动。相信每个人都值得被拯救。",
    "core_motive": "建立一个不受贵族控制的自由治疗所。",
    "background": "教廷叛逃的牧师。因治愈了一名异端教徒而被驱逐，从此游走于灰色地带。精通光系治愈术和解毒术。"
  },
  "current_status": {
    "health": "100/100",
    "inventory": ["圣光权杖", "草药背包", "旧教廷通行令（伪造）"],
    "relationships": {
      "char-001-artemis": "对其冷漠感到不满但认可其能力",
      "char-003-voss": "不了解，只听 Artemis 提起过"
    },
    "recent_memory_summary": [
      "在码头的贫民窟免费为伤员治疗，赢得了当地人的信任"
    ]
  },
  "is_deleted": false,
  "created_at": "2026-03-11T10:05:00+08:00",
  "updated_at": "2026-03-11T10:05:00+08:00"
}
```

---

### 👤 测试角色 3：Lord Voss（反派）

```json
{
  "entity_id": "char-003-voss",
  "type": "CHARACTER",
  "name": "Lord Voss",
  "base_attributes": {
    "aliases": ["The Crimson Duke", "血爵"],
    "personality": "优雅、残忍、极度自恋。享受操控他人命运的快感。谈吐极其文雅，杀人时也保持微笑。",
    "core_motive": "收集所有失落魔典，完成'永恒仪式'以获得不朽之身。",
    "background": "大陆北部最强大的贵族。表面是慈善家和艺术赞助人，暗地里经营着横跨三国的地下奴隶贸易网络。十年前主导了 Blackthorn 家族的覆灭。"
  },
  "current_status": {
    "health": "100/100",
    "inventory": ["猩红权杖", "第一魔典（残页）", "灵魂契约卷轴 x5"],
    "relationships": {
      "char-001-artemis": "视为猎物，有趣的玩具",
      "char-002-elena": "未知"
    },
    "recent_memory_summary": [
      "收到密探报告：Blackthorn 家族的幸存者仍在活动",
      "命令副官加强对黑市的监控，不惜代价找到第二魔典"
    ]
  },
  "is_deleted": false,
  "created_at": "2026-03-11T10:10:00+08:00",
  "updated_at": "2026-03-11T10:10:00+08:00"
}
```

---

## 5. 手动测试流程

### 测试 A：角色 CRUD 全流程

| 步骤 | 操作 | 预期结果 |
|:---:|:---|:---|
| A1 | 打开 `http://localhost:5173/characters` | 看到空态页面："No Characters Yet" |
| A2 | 点击 **"Summon First Character"** | 右侧滑出角色创建面板 |
| A3 | 填入 Artemis 的数据并点击 **"Summon Character"** | 面板关闭，网格中出现 Artemis 卡片 |
| A4 | 重复创建 Elena 和 Lord Voss | 网格显示 3 张角色卡片 |
| A5 | 在搜索框输入 "Voss" | 仅显示 Lord Voss 一张卡片 |
| A6 | 悬浮 Lord Voss 卡片，点击 ✏️ 编辑 | 右侧滑出编辑面板，预填 Voss 数据 |
| A7 | 修改 Health 为 "75/100"，点击 **"Save Changes"** | 面板关闭，卡片底部 ❤️ 显示 `75/100` |
| A8 | 点击 🗑️ 删除 Lord Voss | 弹出确认对话框 |
| A9 | 点击 **"Remove"** | 卡片从网格消失，仅剩 2 张 |

### 测试 B：The Muse 对话触发

| 步骤 | 操作 | 预期结果 |
|:---:|:---|:---|
| B1 | 打开 `http://localhost:5173/` | 看到 The Muse 欢迎消息 |
| B2 | 输入 `"Artemis 在暗巷中被 Voss 的刺客伏击"` | 用户消息气泡出现，下方出现 Muse 回复 |
| B3 | 观察侧边栏引擎状态灯 | 状态应从 `IDLE` 变为彩色脉冲 |
| B4 | 点击红色 **CUT** 按钮 | 出现系统消息 "🛑 CUT — Scene interrupted" |

### 测试 C：故事板章节管理

| 步骤 | 操作 | 预期结果 |
|:---:|:---|:---|
| C1 | 打开 `http://localhost:5173/storyboard` | 双面板布局，左侧提示空态 |
| C2 | 点击 **"New Chapter"** | 顶部出现行内输入框 |
| C3 | 输入 "第一章：暗巷伏击" 并回车 | 左侧列表出现新节点 |
| C4 | 点击该节点 | 右侧显示章节标题（衬线体） |

### 测试 D：设置持久化

| 步骤 | 操作 | 预期结果 |
|:---:|:---|:---|
| D1 | 打开 `http://localhost:5173/settings` | 看到 LLM 配置和 Maestro 调参面板 |
| D2 | 修改 Model 为 `claude-3-sonnet` | 输入框更新 |
| D3 | 修改 Max Turns 为 `8` | 输入框更新 |
| D4 | 点击 **"Save Settings"** | 按钮显示 ✓ Saved! 动画 |

### 测试 E：API 直接验证 (cURL)

```bash
# E1: 健康检查
curl http://localhost:8000/health

# E2: 创建角色
curl -X POST http://localhost:8000/api/v1/grimoire/entities \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "char-001-artemis",
    "type": "CHARACTER",
    "name": "Artemis Blackthorn",
    "base_attributes": {
      "aliases": ["The Shadow"],
      "personality": "Cold and calculating",
      "core_motive": "Find the lost grimoire",
      "background": "Orphaned sorcerer"
    },
    "current_status": {
      "health": "85/100",
      "inventory": ["Shadow Dagger"],
      "relationships": {},
      "recent_memory_summary": []
    },
    "is_deleted": false,
    "created_at": "2026-03-11T10:00:00+08:00",
    "updated_at": "2026-03-11T10:00:00+08:00"
  }'

# E3: 查询所有角色
curl http://localhost:8000/api/v1/grimoire/entities?type=CHARACTER

# E4: 软删除角色
curl -X DELETE http://localhost:8000/api/v1/grimoire/entities/char-001-artemis

# E5: 确认软删除生效 (应返回空列表)
curl http://localhost:8000/api/v1/grimoire/entities?type=CHARACTER

# E6: 触发 Spark
curl -X POST http://localhost:8000/api/v1/sandbox/spark \
  -H "Content-Type: application/json" \
  -d '{
    "spark_id": "test-spark-001",
    "chapter_id": "chap-001",
    "user_prompt": "Artemis 在暗巷中被伏击"
  }'

# E7: 查询沙盒状态
curl http://localhost:8000/api/v1/sandbox/state
```

---

## 6. 常见问题

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| `ModuleNotFoundError: No module named 'backend'` | Python 路径未正确配置 | 确保从项目根目录 `grimoire/` 运行命令 |
| `sqlite3.OperationalError: database is locked` | 并发写入冲突 | 已通过 WAL 模式解决，确认 `database.py` 中 PRAGMA 正确 |
| 前端 API 请求 404 | 后端未启动或端口不匹配 | 确认后端运行在 `8000` 端口 |
| `CORS error` in browser | 跨域请求被拦截 | 已在 `main.py` 中配置 `allow_origins=["*"]` |
---

## 7. 环境清理与服务关闭

在重新启动服务、运行测试或切换开发分支前，建议确保之前的进程已完全退出。

### 快捷命令 (强制关闭)

如果遇到端口占用，可使用以下命令强制终止残留进程：

```bash
# 关闭后端 (8000 端口)
fuser -k 8000/tcp

# 关闭前端 (5173 端口)
fuser -k 5173/tcp
```

### 手动检查进程

若想确认进程是否仍在运行，可搜索相关的关键词：

```bash
# 检查后端 (Uvicorn)
ps aux | grep uvicorn

# 检查前端 (Vite)
ps aux | grep vite
```

### 检查端口占用

在 Linux/WSL 下，可以使用 `lsof` 查看哪些进程正在监听特定端口：

```bash
lsof -i :8000
lsof -i :5173
```

> [!TIP]
> 如果 `lsof` 或 `fuser` 未安装，可以使用 `sudo apt install lsof psmisc` 进行安装。
