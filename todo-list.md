# Grimoire Studio v1.5 - TODO List

## 🟢 已完成 (Completed)
- [x] **后端基础架构**：FastAPI + SQLModel + PostgreSQL + pgvector 环境搭建。
- [x] **多租户安全**：严格执行 Strict Ownership Chain (JOIN Project) 校验。
- [x] **用户认证**：JWT 令牌、密码哈希 (bcrypt 兼容性修复) 及注册/登录接口。
- [x] **RAG 核心算法**：基于 LexoRank 的时空查询逻辑（生命周期过滤 + 状态回归）。
- [x] **Prompt 引擎**：Jinja2 模板体系，支持 XML 物理隔离与叙事模式继承。
- [x] **LLM 服务对接**：接入 OpenAI SDK，强制 `json_object` 响应模式。
- [x] **前端基础框架**：Vite + React + Tailwind v4 (CSS 变量驱动)。
- [x] **Sudowrite UI 实现**：高还原度的 Dashboard、三栏式编辑器、TopBar 模式切换。
- [x] **Slot Machine 交互**：自定义 Tiptap 节点，支持变体切换、失焦自动快照同步。
- [x] **API 配置解耦**：前后端均已支持 `.env` 环境变量配置。

## 🟡 正在进行 (In Progress)
- [ ] **前端持久化登录**：实现 `useAuth` 钩子，刷新页面后自动从 localStorage 恢复会话。
- [ ] **数据流全线贯通**：
    - [ ] Dashboard 接入真实 `Project` CRUD 接口。
    - [ ] 编辑器接入真实 `Chapter` 与 `Block` 接口，取代 Mock 内容。

## 🔴 待办事项 (Backlog)

### 1. The Grimoire (实体百科)
- [ ] **Story Bible UI**：实体（角色/地点/物品）的增删改查交互界面。
- [ ] **别名同步增强**：前端别名列表输入与后端集合运算算法对接。
- [ ] **动态关系管理**：建立实体间的有向图关系（A -> B），并在 RAG 中注入。

### 2. 编辑器深度交互 (Advanced Editor)
- [ ] **@Mention 机制**：输入 `@` 触发实体搜索与强制注入 (Manual Injection)。
- [ ] **Magic Underline**：在编辑器中自动高亮已被 RAG 命中的实体文本。
- [ ] **智能平滑触发**：在 SlotMachine 失焦确认后，调用 `/smooth` API 自动修正下文。
- [ ] **模式特效**：如“沉浸光束 (Mode D)”开启时，编辑器边缘变暗的聚焦视觉效果。

### 3. 文风与分析 (Style & Analysis)
- [ ] **Style Anchors**：上传过往作品片段，计算向量并存入 `pgvector` 用于 Few-shot。
- [ ] **负向约束**：在项目设置中定义“风格禁区”，并注入 System Prompt。
- [ ] **Mode E (Snowflake)**：伏笔扫描器与分形扩充模式的 UI 与逻辑。

### 4. 系统维护与非功能
- [ ] **LexoRank 重平衡**：实现后台异步任务，当 Rank 长度超限时自动重分配。
- [ ] **i18n 国际化**：完善全站中英文翻译，添加全局切换按钮。
- [ ] **性能指标监控**：统计 TTFB 和变体采纳率 (Acceptance Rate)。

## 🚀 下一步任务 (Next Steps)
1. **[前端]** 完善登录持久化与 Dashboard 数据加载。
2. **[后端]** 确保所有子资源（Chapter/Block）在读取时都走 `get_current_active_user` 校验。
3. **[集成]** 实现 SlotMachine 节点与 `/generation/beat` 的真实联调。