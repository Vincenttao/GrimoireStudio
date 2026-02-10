**  

# Grimoire Studio (魔导工坊) 产品需求文档 (PRD)

版本号: v1.2 (The Spellbook Update) 产品代号: Project Alchemist 核心愿景: Glass Box & Co-Pilot —— 将写作从“黑盒赌博”转变为“透明化的精确编排”。

---

## 1. 项目背景与痛点 (Background & Problem)

当前 AI 写作工具存在“中间层真空”：

- Sudowrite: 易用但黑盒，Saliency Engine 用户不可见，导致长文逻辑断裂（Context Amnesia）。
    
- NovelCrafter: 极客化但门槛高，缺乏引导性流程。
    
- 核心痛点: 作者面临决策疲劳 (Decision Fatigue)，在大量 AI 生成的平庸文字中充当“修补工”，且难以维持独特的叙事语调 (Voice Drift)。
    

---

## 2. 核心功能模块 (Functional Requirements)

### 模块一：The Grimoire (动态知识库/数据层)

目标：构建可被 AI 精确检索的实体数据库，作为“世界观的锚点”。

1. 实体管理 (Entity Management):
    

- 支持角色、地点、物品、Lore。
    
- 真名与别名系统 (True Names & Aliases): 支持多 Key 映射（如 ["Bruce", "Batman", "The Dark Knight"] 指向同一 Entity），解决 AI 识别不到昵称的问题。
    

3. 动态关系网 (Dynamic Relationships):
    

- 定义实体间的有向图关系（如 A -> [kill] -> B）。当检测到 A 和 B 同场出现时，优先注入关系描述。
    
    

---

### 模块二：The Ritual (生成引擎与交互流)

目标：确立 Open-Close (发散-收敛) 的标准工作流，采用“智能合成”交互。


#### 2.1 叙事罗盘与老虎机 (The Narrative Compass & Slot Machine)

目标：确立 Open-Close (发散-收敛) 的标准工作流。不仅提供“更多选择”，更提供“不同方向”。

1. **三向生成 (Tri-Directional Generation - Open):**
    
    - 系统后台通过 **单次智能请求 (Single-Shot JSON)**，并发生成 3 个具有鲜明叙事差异的段落变体。
        
    - **动态策略 (Dynamic Strategy):** 变体的具体类型由当前选用的 **Narrative Mode (叙事模式)** 决定（详见 2.2）。不再是随机生成，而是战术性生成。
        
2. **老虎机式切换 (The Slot Machine Interface - Close):**
    
    - **交互:** 鼠标悬停在 AI 生成的段落（Block）上时，显示切换控件 `< Prev | Next >` 以及当前变体的 **“风格标签”** (如: _Action_, _Psychological_, _Minimalist_)。
        
    - **体验:** 用户像玩老虎机一样点击切换，**原地 (In-Place)** 查看不同叙事走向，选中即定稿。
        
3. **智能平滑 (Smart Context Smoothing):**
    
    - (保持不变) 当用户替换了第 2 段（Block B）后，系统自动检测第 3 段（Block C）的衔接性。
    

#### 2.2 叙事模式集 (Narrative Modes / The Spellbook) —— 核心功能

将经典创意写作理论固化为 5 种具体的 AI 续写模式，用户可根据当前写作阶段选择。

| **模式名称**                             | **对应理论**           | **Slot Machine 变体逻辑 (The 3 Slots)**                                                                                                            |
| ------------------------------------ | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mode A: 默认/标准流** (Standard Flow)   | Pacing Control     | **1. Master Track (综合):** 平衡的叙事，作为默认展示。<br>**2. Fast Paced (快穿):** 侧重动作、对话，省略心理描写。<br>**3. Slow Burn (慢燃):** 侧重心理活动、环境氛围，放缓节奏。                 |
| **Mode B: 冲突注入** (Conflict Injector) | Yes, And / No, But | **1. External Block (外阻):** 物理障碍或环境阻挠 (No, But)。<br>**2. Escalation (升级):** 冲突激化，事态失控 (Yes, And)。<br>**3. Internal Conflict (内耗):** 主角自我怀疑或犹豫。 |
| **Mode C: 感官透镜** (Sensory Lens)      | Show, Don't Tell   | **1. Visual (视觉):** 侧重光影、色彩、空间感。<br>**2. Auditory/Olfactory (听/嗅):** 侧重声音、气味、氛围。<br>**3. Tactile/Kinetic (触/动):** 侧重触觉、温度、身体动作。                |
| **Mode D: 沉浸光束** (Focus Beam)        | Flashlight Method  | **1. Immediate Action:** 仅关注当下 5 秒内的动作。<br>**2. Dialogue Focus:** 仅关注对话交互。<br>**3. Micro-Detail:** 仅关注微观细节描写。                                  |
| **Mode E: 分形扩充** (Fractal Expander)  | Snowflake Method   | **1. Logical Path:** 最符合逻辑的剧情发展。<br>**2. Surprising Path:** 意料之外的剧情转折。<br>**3. Emotional Path:** 侧重情感爆发的路径。                                    |
#### 2.3 文风锚点 (Style Anchor)

1. Few-Shot 注入: 用户上传 3-5 段过往作品。
    
2. In-Context Learning: 系统提取句式长短、用词偏好，注入生成过程，防止“AI 味”。
    
3. 负向约束: 定义“风格禁区”（如：禁止翻译腔、禁止倒装句）。
    

---

### 模块三：Scrying Glass (可观测性/交互层)

目标：解决“黑盒”焦虑，提供上下文的可视化与控制。

1. 上下文透视 (Context Inspector):
    

- 可视化展示 AI 当前的 Lookback Window (回溯窗口)。
    
- 高亮显示当前被 RAG 命中并注入 Prompt 的 Grimoire 卡片。
    

3. 手动干预 (Manual Injection):
    

- @Mention 机制: 输入 @Excalibur 强制注入特定实体。
    
- Mute (临时屏蔽): 在透视面板中临时剔除干扰实体。
- **上下文透视 (Context Inspector):**
    
    - 可视化展示 AI 当前的 Lookback Window。
        
    - 高亮显示 RAG 命中的 Grimoire 卡片。
        
- **决策解释 (Decision Explainer - NEW):**
    
    - 当用户切换变体时，Scrying Glass 会简要说明该变体的生成策略（例如：“Showing Visuals” 或 “Injecting External Conflict”），帮助用户理解不同写法的意图。

---

## 3. 非功能需求 (Non-functional Requirements)

1. 性能:
    

- TTFB: 并发生成模式下，首字响应 < 3秒。
    
- Slot Machine Latency: 段落切换必须是瞬时的（预加载）。
- **Single-Shot Latency:** 三个变体必须在 **一次 LLM 请求** 中返回 (JSON Mode)，严禁串行请求，以控制 Input Token 成本并降低延迟。
- **Slot Machine Experience:** 变体必须 **预加载 (Pre-loaded)**。用户点击切换时，内容必须在 **0ms** 延迟下更新（纯前端状态切换）。
        

2. 兼容性:
    

- 支持 BYOK (OpenRouter/DeepSeek/Claude)。
    
- 导出支持Markdown。
    

3. 隐私:

- Zero-Training Pledge: 承诺 BYOK 模式下数据不用于模型训练。

---

## 4. 交互与体验设计 (UI/UX Design)

- 设计隐喻: 魔法工坊 (Arcane Workshop)。
    
- 布局结构:
    

- Left (Library): 资源树 + Grimoire 折叠面板。
    
- Center (Workbench): 沉浸式编辑器。"Mixer" 功能已内嵌至编辑器段落控件中（Slot Machine UI）。
    
- Right (Sparks): 聊天助手 (Chat) + 模式选择器 (Mode Selector)。
    

- 视觉反馈:
    

- Magic Underline: 知识库引用的紫色辉光下划线。
    
- Mode State: 当开启“沉浸光束”时，编辑器边缘变暗，聚焦中心区域。
    

- 国际化支持：
    

- 默认语言为English
    
- 全局切换按钮切换为中文
    
- 默认支持英文/中文，扩展支持
    

---

## 5. 数据埋点与核心指标 (Metrics)
1. **Mode Utilization (模式使用率):** 用户在不同写作阶段（开篇/中段/结尾）倾向于使用哪种 Narrative Mode？
2. **Variant Selection Rate (变体选择率)：
	- 在 Mode B (冲突注入) 下，用户选择了“外部阻碍”还是“内部冲突”？（分析用户偏好）。
    - 如果 Default (Slot 1) 的保留率 > 80%，说明辅助变体的质量或差异化不足。
3. Acceptance Rate (采纳率): 用户生成的段落中，有多少被保留？
4. Swap Rate (切换率): 用户使用“Slot Machine”切换变体的频率。（验证 Open-Close 流程的有效性，若过低则说明默认版本已足够好，或功能发现率低）。
5. Grimoire Utilization: 每次生成平均引用的实体数量。
6. Retention: 第一章完成后的用户留存率。
    

---

## 总结

Grimoire Studio v1.2 不仅仅是一个工具，它是最佳实践 (Best Practices) 的封装。通过将 "雪花法"、"Show, Don't Tell"、"契诃夫之枪" 等理论固化为具体的 Narrative Modes (叙事模式)，我们构建了极高的产品壁垒，帮助作者像专业人士一样思考和创作。

  
**