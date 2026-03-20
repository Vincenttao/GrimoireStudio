# Genesis Engine 开发指南

**版本:** v1.2
**更新日期:** 2026-03-19
**开发模式:** TDD (Test-Driven Development)

---

## 0. 快速开始

### 0.1 LLM 配置（.env 文件）

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
```

**.env 配置项：**

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_MODEL` | 模型名称 | `gpt-4`, `gpt-3.5-turbo`, `claude-3-sonnet` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API Key | `sk-ant-...` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-...` |
| `LLM_API_BASE` | 自定义 API 端点（可选） | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

**配置优先级：** 环境变量 > 数据库设置

**阿里云 DashScope 配置示例：**
```env
LLM_MODEL=qwen-turbo
OPENAI_API_KEY=sk-your-dashscope-key
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

---

## 1. 核心开发原则

### 1.1 TDD 强制流程

**每项功能开发必须遵循 Red-Green-Refactor 循环：**

```
1. RED   → 先写失败的测试
2. GREEN → 写最少代码让测试通过
3. REFACTOR → 重构代码，保持测试通过
```

**禁止行为：**
- ❌ 先写实现代码，后补测试
- ❌ 跳过测试直接提交
- ❌ 为了让测试通过而删除测试用例

### 1.2 测试分层

| 层级 | 目录 | 测试内容 | 运行命令 |
|------|------|----------|----------|
| 单元测试 | `backend/tests/test_*.py` | 单个函数/模型验证 | `pytest backend/tests/ -v` |
| 集成测试 | `backend/tests/test_api.py` | API 端点 + DB 交互 | `pytest backend/tests/test_api.py -v` |
| 端到端测试 | `backend/tests/test_maestro.py` | 完整推演流程 | `pytest backend/tests/test_maestro.py -v` |

### 1.3 测试命名规范

```python
# 文件命名
test_{module_name}.py

# 函数命名
def test_{function_name}_{scenario}_{expected_result}():
    """
    示例：
    - test_generate_character_action_with_director_note_returns_valid_json()
    - test_score_character_output_invalid_action_rejected()
    """
```

---

## 2. 当前开发任务 (V1.0 范围)

### 2.1 功能清单

根据 SPEC 合规性验证，以下功能已完成：

| ID | 功能 | SPEC 引用 | 状态 | 优先级 |
|----|------|-----------|------|--------|
| **CAM-001** | Camera Agent 渲染管线 | §5.3 | ✅ 已完成 | P0 |
| **SCR-001** | Scribe 异步提炼任务 | §3.4 | ✅ 已完成 | P0 |
| **IR-001** | IR Block 结构化提取 | §3.1 | ✅ 已完成 | P0 |
| **MUS-002** | Muse update_entity | §5.4 | ✅ 已完成 | P1 |
| **MUS-003** | Muse delete_entity | §5.4 | ✅ 已完成 | P1 |
| **MUS-004** | Muse query_memory | §5.4 | ✅ 已完成 | P1 |
| **CHK-001** | 检查点恢复流程 | P1.1 | ✅ 已实现 | P1 |

### 2.2 TDD 开发任务详情

#### CAM-001: Camera Agent 渲染管线 ✅

**测试文件:** `backend/tests/test_camera.py` (7 tests)

```python
# 已通过的测试用例
class TestCameraAgent:
    def test_render_ir_block_omniscient_pov_returns_html()  # ✅
    def test_render_ir_block_first_person_pov_uses_character_voice()  # ✅
    def test_render_ir_block_with_subtext_ratio_adjusts_style()  # ✅
    def test_render_retry_keeps_ir_unchanged()  # ✅
    def test_render_empty_ir_block_raises_error()  # ✅
    def test_render_character_limited_pov_requires_character()  # ✅
    def test_render_includes_style_template()  # ✅
```

**实现文件:**
- `backend/services/camera_client.py` — Camera LLM 调用封装 ✅
- `backend/routers/render.py` — Render API 端点 ✅
- `backend/crud/storyboard.py` — 新增 `get_story_ir_block()` ✅

---

#### SCR-001: Scribe 异步提炼任务 ✅

**测试文件:** `backend/tests/test_scribe.py` (7 tests)

```python
# 已通过的测试用例
class TestScribeExtraction:
    def test_extract_inventory_change_from_action()  # ✅
    def test_extract_relationship_change_from_dialogue()  # ✅
    def test_extract_health_delta_from_action()  # ✅
    def test_apply_delta_to_entity_updates_status()  # ✅
    def test_scribe_ignores_rendered_html_content()  # ✅
    def test_multiple_deltas_applied_sequentially()  # ✅
    def test_sliding_window_memory_cap()  # ✅
```

**实现文件:**
- `backend/crud/scribe.py` — `ScribeExtractor` 类实现 ✅

---

#### IR-001: IR Block 结构化提取 ✅

**测试文件:** `backend/tests/test_ir_extraction.py` (6 tests)

```python
# 已通过的测试用例
class TestIRExtraction:
    def test_extract_ir_from_turn_logs_returns_valid_block()  # ✅
    def test_extract_ir_includes_all_actors()  # ✅
    def test_extract_ir_generates_summary()  # ✅
    def test_extract_ir_assigns_lexorank()  # ✅
    def test_extract_ir_with_empty_logs_raises_error()  # ✅
    def test_extract_ir_with_previous_block_links_correctly()  # ✅
```

**实现文件:**
- `backend/services/llm_client.py` — `extract_story_ir()` 方法 ✅

---

## 3. 开发流程

### 3.1 每次开发前

```bash
# 1. 确保测试环境干净
uv run pytest backend/tests/ -v

# 2. 确保代码格式正确
ruff format backend/ && ruff check backend/ --fix
```

### 3.2 开发中

```bash
# 监听测试变化
uv run pytest backend/tests/test_{feature}.py -v --watch

# 或单独运行
uv run pytest backend/tests/test_{feature}.py::{test_name} -v
```

### 3.3 提交前验证

```bash
# 必须全部通过
uv run pytest backend/tests/ -v
ruff format backend/ && ruff check backend/ --fix
cd frontend && npm run lint
```

---

## 4. 测试 Mock 策略

### 4.1 LLM 调用 Mock

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mocked_llm():
    with patch('backend.services.llm_client.llm_client._generate_structured') as mock:
        mock.return_value = CharacterAction(
            intent="测试意图",
            action="测试动作",
            dialogue="测试台词"
        )
        # 测试代码...
```

### 4.2 数据库 Mock

```python
@pytest_asyncio.fixture
async def db_setup():
    # 每个测试前删除旧数据库
    if os.path.exists("grimoire.sqlite"):
        os.remove("grimoire.sqlite")
    async with get_db_connection() as conn:
        await init_db()
        yield conn
```

---

## 5. 文档优先级

遇到冲突时，按以下顺序解决：

1. `docs/SPEC.md` — 技术规范最高优先级
2. `docs/AGENT.md` — 本文档
3. `docs/GEMINI.md` — 核心原则
4. `docs/Architecture_Design.md` — 架构设计

---

## 6. 当前 Sprint 目标

**Sprint 1 ✅ 完成**: V1.0 核心功能

| 任务 | 预估 | 负责模块 | 状态 |
|------|------|----------|------|
| CAM-001 Camera Agent | 4h | `services/camera_client.py` | ✅ 完成 |
| SCR-001 Scribe 提炼 | 3h | `crud/scribe.py` | ✅ 完成 |
| IR-001 IR 提取 | 2h | `services/llm_client.py` | ✅ 完成 |

**Sprint 2 ✅ 完成**: Muse Command Matrix

| 任务 | 预估 | 负责模块 | 状态 |
|------|------|----------|------|
| MUS-002 update_entity | 2h | `muse.py` + `MusePanel.tsx` | ✅ 完成 |
| MUS-003 delete_entity | 1h | `muse.py` + `MusePanel.tsx` | ✅ 完成 |
| MUS-004 query_memory | 2h | `grimoire.py` + `MusePanel.tsx` | ✅ 完成 |

**验收标准:**
- [x] 所有测试通过 (50 passed)
- [x] Camera 渲染 API 可用
- [x] Scribe 提取逻辑完整
- [x] IR Block 结构化提取实现
- [x] Muse 完整支持 create/update/delete/query 工具调用
- [x] 真实 LLM API 测试通过 (qwen3.5-plus via DashScope)

**测试统计:**
- 单元测试: 47 passed
- LLM 集成测试: 3 passed (real API)

---

## 7. 禁止行为

- ❌ 提交未测试的代码
- ❌ 删除测试用例来通过测试
- ❌ 使用 `as any` / `@ts-ignore` 抑制类型错误
- ❌ 在推演中引入 Redis 或外部 SaaS
- ❌ 使用第三人称描写角色（Character Agent 限制）
- ❌ Camera 读取渲染后的正文（必须只读 IR）