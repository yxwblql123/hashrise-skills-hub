#!/usr/bin/env python3
"""Hashrise 独立游戏开发 Skill 导航 · 目录策展脚本

从 `_catalog_probe/skills_raw.json`（本地浅克隆 + frontmatter 抽取的真实元数据）
生成 `data/catalog.json`。

策展原则：
1. 第三方条目只收录**已核实存在**的 SKILL.md，commit 与内容 sha256 来自本地工作区。
2. 中文摘要、分类、引擎维度由人工标注，不做机器翻译。
3. 许可证如实登记：BUSL / CC-BY-NC / 未声明 全部标出，不伪装成 MIT。
4. first-party 条目（Hashrise 自研技能）标 `verification: first-party`，与第三方区分。
"""
import hashlib
import json
import os
import re
import sys

HUB = "D:/workbuddy智能AI/614/hashrise-skills-hub"
PROBE = "D:/workbuddy智能AI/614/_catalog_probe"
RAW = os.path.join(PROBE, "skills_raw.json")
REPORT = os.path.join(PROBE, "probe_report.json")
OUT = os.path.join(HUB, "data", "catalog.json")
CHECKED_AT = "2026-11-24"

# 仓库级许可证（人工核实 LICENSE 文件）
REPO_LICENSE = {
    "elliothimmelfarb/godot-steam-kit": "MIT",
    "GarrettPetersen/indie-game-marketing-skills": "MIT",
    "jame581/GodotPrompter": "MIT",
    "thedivergentai/Game-Dev-Agentic-Skills": "MIT",
    "RandallLiuXin/GodotMaker": "BUSL-1.1",
    "huytran1120/vie-agentic-skills": "MIT",
    "majiayu000/claude-skill-registry": "MIT",
    "NVlabs/Skill2Env": "Apache-2.0",
    "MRCalderon3D/everything-game-dev-code": "MIT",
    "jackli12/codex-game-studio": "MIT",
    "wazzapsenk/steamworks-mcp": "MIT",
    "TMHSDigital/Steam-Cursor-Plugin": "CC-BY-NC-4.0",
    "AlterLab-IEU/AlterLab_GameForge": "MIT",
    "arjun988/blender-skills": "MIT",
    "Randroids-Dojo/Godot-Claude-Skills": "MIT",
    "AlexStormwood/agentic-skills": "MIT",
    "jammyfu/open-game-skills": "MIT",
    "ilezhnin/gamedev-ai-agents": "MIT",
    "baxatron-git/claude-game-design-suite": "未声明",
    "Tiny-Anvil/agent-skills": "MIT",
    "fcsouza/agent-skills": "MIT",
    "nick-vas/hyperdot": "Apache-2.0",
    "modbender/skill-library-mcp": "MIT",
    "haxqer/godot-skill": "MIT",
}

# 许可证提示（许可证不是 MIT 时追加说明）
LICENSE_NOTE = {
    "BUSL-1.1": "BUSL-1.1：可自用与内部分发，对外分发有条件，商用前请读许可原文",
    "CC-BY-NC-4.0": "CC-BY-NC-4.0：禁止商业用途，商用项目请勿直接采用",
    "未声明": "仓库未声明许可证，默认保留全部权利，仅供阅读参考，勿直接采用",
}

# (repo, skill_name, category, engines, capability, zh_title, zh_summary, tags, featured)
SELECTION = [
    # ---------- 概念与策划 ----------
    ("MRCalderon3D/everything-game-dev-code", "gdd-writing", "概念与策划", ["通用"], "方法指导",
     "GDD 撰写规范", "创建或更新可执行的 Game Design Document，覆盖设计、工程、QA、制作各角色都能读懂的行动项。",
     ["GDD", "设计文档", "流程"], True),
    ("MRCalderon3D/everything-game-dev-code", "core-loop-design", "概念与策划", ["通用"], "方法指导",
     "核心循环设计", "定义玩家主活动循环与支撑循环，让掌握度、变化与推进都有落点。",
     ["核心循环", "留存", "玩法"], False),
    ("MRCalderon3D/everything-game-dev-code", "economy-balancing", "概念与策划", ["通用"], "方法指导",
     "经济系统调平", "设计并调平货币、消耗点、奖励、价格与通胀控制，使经济支撑推进而非拖垮进度。",
     ["经济", "数值", "通胀"], True),
    ("MRCalderon3D/everything-game-dev-code", "progression-design", "概念与策划", ["通用"], "方法指导",
     "进度与成长设计", "组织长短期成长线，让玩家持续获得成长感、目标感与留存。",
     ["成长", "数值", "留存"], False),
    ("MRCalderon3D/everything-game-dev-code", "monetization-design", "概念与策划", ["通用"], "方法指导",
     "变现系统设计", "设计契合产品定位的变现系统，兼顾玩家信任与技术与法规约束。",
     ["变现", "内购", "广告"], True),
    ("MRCalderon3D/everything-game-dev-code", "level-design", "概念与策划", ["通用"], "方法指导",
     "关卡流程设计", "规划关卡节奏、动线、导航、遭遇布置与空间教学。",
     ["关卡", "节奏", "新手引导"], False),
    ("MRCalderon3D/everything-game-dev-code", "narrative-design", "概念与策划", ["通用"], "方法指导",
     "叙事结构设计", "搭建叙事结构、世界逻辑、对话意图与玩家动机，使故事服务玩法循环。",
     ["叙事", "剧情", "对话"], False),
    ("MRCalderon3D/everything-game-dev-code", "onboarding-tutorial-design", "概念与策划", ["通用"], "方法指导",
     "新手引导设计", "渐进且不劝退地教会玩家规则，支撑留存而不是制造认知负担。",
     ["新手", "教学", "留存"], True),
    ("MRCalderon3D/everything-game-dev-code", "game-feel-design", "概念与策划", ["通用"], "方法指导",
     "手感反馈设计", "设计命中停顿、屏幕震动、补间与响应时序，让操作有实感。",
     ["手感", "反馈", "补间"], False),
    ("MRCalderon3D/everything-game-dev-code", "gameplay-architecture", "概念与策划", ["通用"], "方法指导",
     "玩法架构边界", "定义系统归属、边界、状态流转与可扩展性，避免玩法逻辑互相缠绕。",
     ["架构", "系统边界"], True),
    ("MRCalderon3D/everything-game-dev-code", "risk-register", "概念与策划", ["通用"], "方法指导",
     "风险登记表", "识别并持续跟踪最可能拖垮范围、质量、预算或发布就绪度的风险。",
     ["风险", "项目管理"], False),
    ("MRCalderon3D/everything-game-dev-code", "vertical-slice-planning", "概念与策划", ["通用"], "方法指导",
     "垂直切片规划", "定义一段能同时证明玩法、质量标准与生产可行性的最小完整体验。",
     ["垂直切片", "里程碑"], False),
    ("MRCalderon3D/everything-game-dev-code", "milestone-planning", "概念与策划", ["通用"], "方法指导",
     "里程碑规划", "产出依赖感知、风险感知的交付计划，绑定真实交付结果而非日期口号。",
     ["里程碑", "排期"], False),
    ("MRCalderon3D/everything-game-dev-code", "playtest-analysis", "概念与策划", ["通用"], "方法指导",
     "试玩观察分析", "把原始试玩记录转成可执行的设计、体验、调参与制作决策。",
     ["试玩", "用户研究"], False),
    ("MRCalderon3D/everything-game-dev-code", "technical-design-document", "概念与策划", ["通用"], "方法指导",
     "技术设计文档", "把功能意图转成可实现、可评审、可测试的技术设计文档。",
     ["TDD", "技术方案"], False),
    ("MRCalderon3D/everything-game-dev-code", "liveops-design", "概念与策划", ["通用"], "方法指导",
     "长线运营设计", "设计赛季、活动与上线后内容，在不破坏核心产品的前提下延长参与。",
     ["长线运营", "赛季"], False),
    ("MRCalderon3D/everything-game-dev-code", "accessibility-design", "概念与策划", ["通用"], "方法指导",
     "无障碍设计", "把无障碍做进设计决策，而不是当作收尾期的可选项。",
     ["无障碍", "可访问性"], False),
    ("jackli12/codex-game-studio", "write-gdd", "概念与策划", ["通用"], "方法指导",
     "结构化 GDD 撰写", "从概念、玩法笔记或草稿出发，创建并打磨结构化的游戏设计文档。",
     ["GDD", "设计文档"], True),
    ("jackli12/codex-game-studio", "define-game-concept", "概念与策划", ["通用"], "方法指导",
     "概念定义", "澄清目标受众、玩法钩子、幻想点与玩家体验目标。",
     ["概念", "定位"], False),
    ("jackli12/codex-game-studio", "start-game-project", "概念与策划", ["通用"], "方法指导",
     "立项启动", "把一个原始点子转成项目简报、初步方向与下一步动作。",
     ["立项", "简报"], False),
    ("jackli12/codex-game-studio", "game-designer", "概念与策划", ["通用"], "方法指导",
     "玩法设计", "产出玩法规则、系统、成长与高层关卡设计。",
     ["玩法", "系统设计"], False),
    ("jackli12/codex-game-studio", "creative-director", "概念与策划", ["通用"], "方法指导",
     "创意总监", "确定题材、基调、风格、世界观与创意包装。",
     ["创意", "风格", "世界观"], False),
    ("jackli12/codex-game-studio", "game-director", "概念与策划", ["通用"], "方法指导",
     "游戏总监决策", "在体验目标与产品取舍之间给出明确方向判断。",
     ["方向", "取舍"], False),
    ("jackli12/codex-game-studio", "plan-production", "概念与策划", ["通用"], "方法指导",
     "制作计划", "把游戏设计转成里程碑、优先级、交付阶段与范围控制。",
     ["制作", "排期"], False),
    ("jackli12/codex-game-studio", "tech-director", "概念与策划", ["Godot"], "方法指导",
     "技术总监", "架构指引、实现边界、性能评审与技术风险处理。",
     ["技术", "架构"], False),
    ("jackli12/codex-game-studio", "ui-ux-designer", "概念与策划", ["通用"], "方法指导",
     "UI/UX 设计", "界面线框、信息架构、界面流程与引导流程设计。",
     ["UI", "UX", "线框"], True),
    ("jackli12/codex-game-studio", "visual-artist", "概念与策划", ["通用"], "方法指导",
     "视觉与美术规划", "视觉资产规划、风格方向、美术简报与 UI 资产拆分。",
     ["美术", "风格"], False),
    ("jackli12/codex-game-studio", "audio-designer", "概念与策划", ["通用"], "方法指导",
     "音频设计", "声音方向、音效规划、BGM 规划与音频简报。",
     ["音频", "音效"], False),
    ("baxatron-git/claude-game-design-suite", "game-vision-architect", "概念与策划", ["通用"], "方法指导",
     "游戏愿景架构", "定义游戏愿景、差异化主张与长期意图，作为所有下游决策的锚。",
     ["愿景", "定位"], True),
    ("baxatron-git/claude-game-design-suite", "design-pillars-architect", "概念与策划", ["通用"], "方法指导",
     "设计支柱定义", "确立 3~5 条设计支柱，并为每条写出反例红线，便于评审时判定跑偏。",
     ["设计支柱", "红线"], True),
    ("baxatron-git/claude-game-design-suite", "core-loop-designer", "概念与策划", ["通用"], "方法指导",
     "核心循环推演", "拆解核心循环与支撑循环，检验是否存在唯一最优解与成长断点。",
     ["核心循环", "平衡"], False),
    ("baxatron-git/claude-game-design-suite", "economy-progression-designer", "概念与策划", ["通用"], "方法指导",
     "经济与成长设计", "货币、消耗、成长曲线的联合设计，防止数值墙与软性 pay-to-win。",
     ["经济", "成长"], True),
    ("baxatron-git/claude-game-design-suite", "gdd-author", "概念与策划", ["通用"], "方法指导",
     "GDD 生成器", "从支柱与循环推演直接生成结构完整、可评审的 GDD。",
     ["GDD", "生成"], True),
    ("baxatron-git/claude-game-design-suite", "game-balance-analyst", "概念与策划", ["通用"], "方法指导",
     "数值平衡分析", "审查经济与成长数值，定位失衡点并给出可执行的调整建议。",
     ["平衡", "数值审查"], False),
    ("baxatron-git/claude-game-design-suite", "high-concept-pitch-writer", "概念与策划", ["通用"], "方法指导",
     "高概念提案", "把游戏概念压缩成一段可对外传播的高概念陈述。",
     ["提案", "宣传"], False),
    ("baxatron-git/claude-game-design-suite", "level-encounter-planner", "概念与策划", ["通用"], "方法指导",
     "关卡遭遇规划", "规划关卡内的遭遇顺序与挑战梯度。",
     ["关卡", "遭遇"], False),
    ("baxatron-git/claude-game-design-suite", "design-coherence-engine", "概念与策划", ["通用"], "方法指导",
     "设计一致性校验", "检查各子系统设计是否互相矛盾、是否偏离既定支柱。",
     ["一致性", "评审"], False),
    ("NVlabs/Skill2Env", "game-gdd-author", "概念与策划", ["通用"], "方法指导",
     "游戏设计文档生成", "由玩法要点生成完整 GDD，覆盖核心循环、角色、系统与关卡。",
     ["GDD", "生成"], False),
    ("NVlabs/Skill2Env", "game-unity-specialist", "概念与策划", ["Unity"], "方法指导",
     "Unity 专项顾问", "Unity 引擎专项：架构、渲染管线、性能与平台适配。",
     ["Unity"], False),
    ("NVlabs/Skill2Env", "game-unreal-specialist", "概念与策划", ["Unreal"], "方法指导",
     "Unreal 专项顾问", "Unreal 引擎专项：Gameplay 框架、GAS、复制与打包。",
     ["Unreal"], False),
    ("ilezhnin/gamedev-ai-agents", "gdd", "概念与策划", ["通用"], "方法指导",
     "GDD 起草助手", "在游戏开发 AI 代理集中起草 GDD，覆盖设计意图到可执行条目。",
     ["GDD"], False),
    ("RandallLiuXin/GodotMaker", "gm-gdd", "概念与策划", ["Godot"], "方法指导",
     "GodotMaker GDD 流程", "GodotMaker 流水线中的 GDD 生成环节，衔接后续工程产出。",
     ["GDD", "Godot"], False),

    # ---------- 引擎与实现 ----------
    ("jame581/GodotPrompter", "godot-project-setup", "引擎与实现", ["Godot"], "方法指导",
     "Godot 4 项目脚手架", "新建 Godot 4.x 项目：目录结构、项目设置、自动加载与 .gitignore。",
     ["Godot", "脚手架", "工程"], True),
    ("jame581/GodotPrompter", "scene-organization", "引擎与实现", ["Godot"], "方法指导",
     "场景树组织", "场景树结构设计：组合还是继承、何时拆分场景、节点层级范式。",
     ["Godot", "场景", "架构"], True),
    ("jame581/GodotPrompter", "event-bus", "引擎与实现", ["Godot"], "代码生成",
     "全局事件总线", "用带类型信号的 EventBus 自动加载实现解耦的节点通信。",
     ["Godot", "信号", "解耦"], True),
    ("jame581/GodotPrompter", "dependency-injection", "引擎与实现", ["Godot"], "方法指导",
     "依赖注入选型", "自动加载、服务定位器、@export 注入与场景注入的取舍。",
     ["Godot", "依赖注入"], False),
    ("jame581/GodotPrompter", "resource-pattern", "引擎与实现", ["Godot"], "代码生成",
     "Resource 数据容器", "用自定义 Resource 承载配置、物品与属性，并接入编辑器可视化。",
     ["Godot", "Resource", "数据"], True),
    ("jame581/GodotPrompter", "save-load", "引擎与实现", ["Godot"], "代码生成",
     "存档读写系统", "ConfigFile、JSON、Resource 序列化与存档架构选型。",
     ["Godot", "存档"], True),
    ("jame581/GodotPrompter", "gdscript-patterns", "引擎与实现", ["Godot"], "代码生成",
     "GDScript 惯用法", "静态类型、await 协程、lambda、match 与导出注解等常用写法。",
     ["Godot", "GDScript"], True),
    ("jame581/GodotPrompter", "gdscript-advanced", "引擎与实现", ["Godot"], "代码生成",
     "GDScript 进阶", "生产级写法：性能惯用法、元编程、@tool 生命周期与信号/Callable 权衡。",
     ["Godot", "GDScript", "性能"], False),
    ("jame581/GodotPrompter", "godot-ui", "引擎与实现", ["Godot"], "代码生成",
     "Godot UI 构建", "Control 节点、主题、锚点与容器布局模式。",
     ["Godot", "UI"], True),
    ("jame581/GodotPrompter", "responsive-ui", "引擎与实现", ["Godot"], "代码生成",
     "多分辨率适配", "拉伸模式、宽高比、DPI 缩放与移动端/桌面适配。",
     ["Godot", "适配", "移动端"], True),
    ("jame581/GodotPrompter", "hud-system", "引擎与实现", ["Godot"], "代码生成",
     "HUD 实现", "血条、分数显示、小地图、通知与伤害数字等游戏内 HUD。",
     ["Godot", "HUD"], False),
    ("jame581/GodotPrompter", "localization", "引擎与实现", ["Godot"], "代码生成",
     "本地化实现", "TranslationServer、CSV/PO 翻译文件、语言切换、RTL 与复数形式。",
     ["Godot", "i18n", "本地化"], True),
    ("jame581/GodotPrompter", "mobile-development", "引擎与实现", ["Godot"], "平台接入",
     "移动端开发", "Android/iOS 导出与签名、权限、插件、内购、广告与生命周期。",
     ["Godot", "移动端", "导出"], True),
    ("jame581/GodotPrompter", "godot-debugging", "引擎与实现", ["Godot"], "方法指导",
     "Godot 调试", "远程调试器、打印技巧、信号追踪与常见报错定位。",
     ["Godot", "调试"], False),
    ("jame581/GodotPrompter", "godot-code-review", "引擎与实现", ["Godot"], "方法指导",
     "Godot 代码评审", "GDScript/C# 评审清单、常见反模式与引擎特有陷阱。",
     ["Godot", "评审"], False),
    ("jame581/GodotPrompter", "godot-testing", "引擎与实现", ["Godot"], "自动化",
     "Godot 自动化测试", "用 GUT 与 gdUnit4 走 TDD 流程，覆盖 GDScript 与 C#。",
     ["Godot", "测试", "TDD"], True),
    ("jame581/GodotPrompter", "godot-optimization", "引擎与实现", ["Godot"], "方法指导",
     "Godot 性能优化", "分析器、draw call、物理调优、内存管理与常见瓶颈。",
     ["Godot", "性能"], True),
    ("jame581/GodotPrompter", "export-pipeline", "引擎与实现", ["Godot"], "自动化",
     "Godot 导出与分发", "导出预设、平台设置与基于 GitHub Actions 的 CI/CD。",
     ["Godot", "导出", "CI"], True),
    ("MRCalderon3D/everything-game-dev-code", "godot-scene-architecture", "引擎与实现", ["Godot"], "方法指导",
     "Godot 场景架构", "组织场景、节点、自动加载与资源，使项目可扩展且可理解。",
     ["Godot", "架构"], True),
    ("MRCalderon3D/everything-game-dev-code", "godot-gdscript-standards", "引擎与实现", ["Godot"], "代码生成",
     "GDScript 规范", "让场景驱动的项目保持可读、可维护、可安全重构的 GDScript 规范。",
     ["Godot", "GDScript", "规范"], True),
    ("MRCalderon3D/everything-game-dev-code", "godot-project-structure", "引擎与实现", ["Godot"], "方法指导",
     "Godot 目录结构", "让场景、脚本、资源、插件、测试与导出资产各归其位。",
     ["Godot", "工程结构"], False),
    ("MRCalderon3D/everything-game-dev-code", "godot-signals-patterns", "引擎与实现", ["Godot"], "方法指导",
     "Godot 信号模式", "用信号解耦但不制造隐藏事件网、所有权混乱与生命周期 bug。",
     ["Godot", "信号"], False),
    ("MRCalderon3D/everything-game-dev-code", "godot-input-patterns", "引擎与实现", ["Godot"], "代码生成",
     "Godot 输入系统", "通过 InputMap action 实现输入，含事件传播、设备支持与重绑定。",
     ["Godot", "输入"], False),
    ("MRCalderon3D/everything-game-dev-code", "godot-performance", "引擎与实现", ["Godot"], "方法指导",
     "Godot 性能剖析", "基于代表性构建剖析运行时、场景、渲染与资源行为。",
     ["Godot", "性能"], False),
    ("MRCalderon3D/everything-game-dev-code", "godot-build-release", "引擎与实现", ["Godot"], "自动化",
     "Godot 构建与发布", "用可复现预设与平台化检查执行 Godot 导出、CI 与发布打包。",
     ["Godot", "构建", "发布"], True),
    ("MRCalderon3D/everything-game-dev-code", "save-system-patterns", "引擎与实现", ["通用"], "方法指导",
     "存档系统模式", "定义持久化边界、存档格式、恢复行为与迁移策略。",
     ["存档", "迁移"], True),
    ("MRCalderon3D/everything-game-dev-code", "event-bus-patterns", "引擎与实现", ["通用"], "方法指导",
     "事件总线模式", "用事件与消息而不制造隐藏耦合、顺序 bug 与无法调试的路径。",
     ["事件", "解耦"], False),
    ("MRCalderon3D/everything-game-dev-code", "godot-testing", "引擎与实现", ["Godot"], "方法指导",
     "Godot 测试分层", "为 Godot 功能挑选有效的自动化与手工测试层次，避免过度复杂化。",
     ["Godot", "测试"], False),
    ("elliothimmelfarb/godot-steam-kit", "godot", "引擎与实现", ["Godot"], "自动化",
     "Godot 命令行开发", "用 godot-steam-kit 在命令行构建、运行与测试 Godot 4 项目（macOS/Windows）。",
     ["Godot", "CLI", "自动化"], True),
    ("Randroids-Dojo/Godot-Claude-Skills", "godot", "引擎与实现", ["Godot"], "方法指导",
     "Godot 通用指引", "面向 Godot 的通用开发指引与代理协作方式。",
     ["Godot"], False),
    ("haxqer/godot-skill", "godot", "引擎与实现", ["Godot"], "方法指导",
     "Godot 无头项目操作", "以无头方式创建、检查与编辑 Godot 项目、场景、UI 与资源。",
     ["Godot", "无头", "自动化"], False),
    ("fcsouza/agent-skills", "game-godot", "引擎与实现", ["Godot"], "方法指导",
     "Godot 游戏开发指引", "面向 Godot 的游戏开发代理技能集。",
     ["Godot"], False),
    ("huytran1120/vie-agentic-skills", "scenario-godot-architecture", "引擎与实现", ["Godot"], "方法指导",
     "Godot 架构场景包", "Godot 架构专项的场景化技能包。",
     ["Godot", "架构"], False),
    ("huytran1120/vie-agentic-skills", "godot-audio", "引擎与实现", ["Godot"], "代码生成",
     "Godot 音频系统", "Godot 音频总线、播放器、空间音频与动态混音。",
     ["Godot", "音频"], False),
    ("huytran1120/vie-agentic-skills", "godot-physics", "引擎与实现", ["Godot"], "方法指导",
     "Godot 物理系统", "Godot 物理体、碰撞、射线检测与刚体实践。",
     ["Godot", "物理"], False),
    ("majiayu000/claude-skill-registry", "godot", "引擎与实现", ["Godot"], "方法指导",
     "Godot 技能（注册表）", "注册表收录的 Godot 技能条目。",
     ["Godot"], False),
    ("majiayu000/claude-skill-registry", "godot-ui", "引擎与实现", ["Godot"], "代码生成",
     "Godot UI 技能（注册表）", "注册表收录的 Godot UI 技能条目。",
     ["Godot", "UI"], False),
    ("modbender/skill-library-mcp", "godot", "引擎与实现", ["Godot"], "方法指导",
     "Godot 技能（技能库 MCP）", "技能库服务收录的 Godot 条目，可经 MCP 检索。",
     ["Godot", "MCP"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-godot-specialist", "引擎与实现", ["Godot"], "方法指导",
     "Godot 专项顾问", "GameForge 的 Godot 专项角色，覆盖引擎能力与工程实践。",
     ["Godot"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-unity-specialist", "引擎与实现", ["Unity"], "方法指导",
     "Unity 专项顾问", "GameForge 的 Unity 专项角色。",
     ["Unity"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-unreal-specialist", "引擎与实现", ["Unreal"], "方法指导",
     "Unreal 专项顾问", "GameForge 的 Unreal 专项角色。",
     ["Unreal"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-web2d-specialist", "引擎与实现", ["Web"], "方法指导",
     "Web 2D 专项顾问", "GameForge 的浏览器 2D 专项角色。",
     ["Web"], False),
    ("jackli12/codex-game-studio", "gameplay-programmer", "引擎与实现", ["通用"], "代码生成",
     "玩法程序实现", "把玩法特性或系统拆成可执行的实现步骤与代码。",
     ["玩法", "实现"], True),
    ("jackli12/codex-game-studio", "implement-feature", "引擎与实现", ["通用"], "代码生成",
     "特性落地", "把设计意图推进到实现计划与具体改动。",
     ["实现", "落地"], False),
    ("jackli12/codex-game-studio", "design-ui-flow", "引擎与实现", ["通用"], "方法指导",
     "界面流程设计", "把菜单、HUD、新手引导等界面流程转成线框与交互结构。",
     ["UI", "流程"], False),

    # ---------- 美术与音频 ----------
    ("MRCalderon3D/everything-game-dev-code", "art-bible", "美术与音频", ["通用"], "方法指导",
     "美术圣经", "定义一套可被美术、UI、技术美术与市场共同执行的视觉方向。",
     ["美术", "风格", "规范"], True),
    ("MRCalderon3D/everything-game-dev-code", "technical-art-pipeline", "美术与音频", ["通用"], "方法指导",
     "技术美术流水线", "对齐内容生产、着色器、导入设置、运行时表现与性能约束。",
     ["技术美术", "流水线"], False),
    ("MRCalderon3D/everything-game-dev-code", "localization-pipeline", "美术与音频", ["通用"], "方法指导",
     "本地化流水线", "为翻译、文化适配、文本膨胀与语音字幕差异做准备。",
     ["本地化", "i18n"], True),
    ("jammyfu/open-game-skills", "art-bible", "美术与音频", ["通用"], "方法指导",
     "视觉风格契约", "在剪影、配色、生成美术、UI、敌人与皮肤之间建立稳定的视觉风格契约。",
     ["美术", "风格"], False),
    ("jammyfu/open-game-skills", "sprite-catalog", "美术与音频", ["通用"], "方法指导",
     "精灵清单", "生成前先盘点所需的精灵、图块、UI、图标、头像、道具与动画状态。",
     ["2D", "资产清单"], True),
    ("jammyfu/open-game-skills", "sprite-atlas", "美术与音频", ["通用"], "方法指导",
     "图集与切片", "精灵表切片、锚点稳定、纹理打包与引擎元数据，消除导入抖动与串色。",
     ["2D", "图集"], True),
    ("jammyfu/open-game-skills", "pixel-animation", "美术与音频", ["通用"], "方法指导",
     "像素动画节奏", "当精灵动画与攻击节奏不一致、顿帧跳格时，建立显式的玩法帧映射。",
     ["2D", "动画"], False),
    ("jammyfu/open-game-skills", "hd-sprite-sequence", "美术与音频", ["通用"], "方法指导",
     "高清序列重绘", "从原始帧重绘高清精灵或独立特效，保持身份与比例一致。",
     ["2D", "重绘"], False),
    ("jammyfu/open-game-skills", "spine-skeletal", "美术与音频", ["通用"], "方法指导",
     "骨骼与权重", "整体骨骼、分层部件与逐帧重绘之间的选型与绑定修复。",
     ["2D", "骨骼"], False),
    ("jammyfu/open-game-skills", "skin-weights", "美术与音频", ["通用"], "自动化",
     "2D 权重生成与校验", "生成并校验分层骨骼角色的 2D 蒙皮权重。",
     ["2D", "蒙皮", "校验"], False),
    ("GarrettPetersen/indie-game-marketing-skills", "develop-pixel-art-games", "美术与音频", ["通用"], "方法指导",
     "像素美术游戏开发", "像素美术渲染管线、逻辑像素网格、资产缩放、相机构图、UI 与字体。",
     ["像素", "2D", "渲染"], False),
    ("arjun988/blender-skills", "blender-director", "美术与音频", ["Blender"], "方法指导",
     "Blender 总监", "启动任何 Blender 资产任务时先规划生产流程并协调多资产协作。",
     ["Blender", "流程"], True),
    ("arjun988/blender-skills", "asset-optimization", "美术与音频", ["Blender"], "自动化",
     "资产优化校验", "按面数、拓扑、UV 效率、材质数等维度校验与优化 Blender 资产。",
     ["Blender", "优化"], False),
    ("arjun988/blender-skills", "collision-proxy", "美术与音频", ["Blender"], "方法指导",
     "碰撞代理制作", "面向游戏的碰撞代理：UCX/UHX 命名、凸包、胶囊与简化。",
     ["Blender", "碰撞"], False),
    ("arjun988/blender-skills", "animation", "美术与音频", ["Blender"], "方法指导",
     "游戏级动画", "在 Blender 中制作可直接入游戏的行走、奔跑、待机、战斗与机械动画。",
     ["Blender", "动画"], False),
    ("jame581/GodotPrompter", "assets-pipeline", "美术与音频", ["Godot"], "方法指导",
     "Godot 资产流水线", "图片压缩、3D 导入、音频格式、资源格式与导入配置管理。",
     ["Godot", "资产", "导入"], False),

    # ---------- 商业化与发行 ----------
    ("elliothimmelfarb/godot-steam-kit", "steam-publishing", "商业化与发行", ["Godot", "Steam"], "自动化",
     "Godot 游戏上架 Steam", "把 Godot 4 游戏做成已发售的付费 Steam 产品的完整路径。",
     ["Steam", "Godot", "发行"], True),
    ("GarrettPetersen/indie-game-marketing-skills", "audit-steam-store-page", "商业化与发行", ["Steam"], "方法指导",
     "Steam 商店页审计", "逐项审计商店页的定位、胶囊图、预告片、截图、文案、标签与本地化。",
     ["Steam", "商店页", "审计"], True),
    ("GarrettPetersen/indie-game-marketing-skills", "optimize-steam-tags", "商业化与发行", ["Steam"], "方法指导",
     "Steam 标签优化", "围绕同类游戏与推荐邻域构建有序的标签组合，读懂 Tag Wizard。",
     ["Steam", "标签", "ASO"], True),
    ("GarrettPetersen/indie-game-marketing-skills", "plan-indie-game-marketing", "商业化与发行", ["Steam"], "方法指导",
     "独立游戏营销规划", "从类型选择、预告片优先的垂直切片，到定价、早期本地化与上架节奏。",
     ["Steam", "营销"], True),
    ("GarrettPetersen/indie-game-marketing-skills", "review-game-trailer", "商业化与发行", ["Steam"], "方法指导",
     "预告片评审", "用真实画面、可读节奏与真实特性证据评审或改写游戏预告片。",
     ["Steam", "预告片"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-store-page", "商业化与发行", ["Steam"], "平台接入",
     "Steam 商店页撰写与校对", "从访谈与定位出发撰写短描述与 About This Game 并校对一致性。",
     ["Steam", "商店页", "MCP"], True),
    ("wazzapsenk/steamworks-mcp", "steamworks-store-assets", "商业化与发行", ["Steam"], "方法指导",
     "Steam 图片规格", "胶囊图、库hero、logo、页面背景与应用/成就图标的精确尺寸与裁切。",
     ["Steam", "美术规格"], True),
    ("wazzapsenk/steamworks-mcp", "steamworks-release", "商业化与发行", ["Steam"], "平台接入",
     "Steam 发布全流程", "从零配置到正式在 Steam 上架的完整发布路径。",
     ["Steam", "发布"], True),
    ("wazzapsenk/steamworks-mcp", "steamworks-review-gate", "商业化与发行", ["Steam"], "平台接入",
     "Steam 上线前检查门", "汇总一次 Steam 发布前仍未关闭的事项与接下来的三步。",
     ["Steam", "发布检查"], True),
    ("wazzapsenk/steamworks-mcp", "steamworks-launch-week", "商业化与发行", ["Steam"], "平台接入",
     "Steam 首周运营", "追踪发布后的评价、在线人数与价格变化，定位玩家好评与差评。",
     ["Steam", "运营"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-pricing", "商业化与发行", ["Steam"], "平台接入",
     "Steam 定价决策", "以数据决定定价：同类游戏在美国与各地区的定价、首发折扣与地区价。",
     ["Steam", "定价"], True),
    ("wazzapsenk/steamworks-mcp", "steamworks-sales-calendar", "商业化与发行", ["Steam"], "平台接入",
     "Steam 档期日历", "规划发售日、Steam 新品节、季节促销与折扣档期。",
     ["Steam", "档期"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-playtest-demo", "商业化与发行", ["Steam"], "平台接入",
     "Steam 试玩与 Demo", "何时用 Playtest、何时用 Demo，独立 App 配置、按钮、批次与新品节。",
     ["Steam", "Demo", "Playtest"], True),
    ("wazzapsenk/steamworks-mcp", "steamworks-cloud-saves", "商业化与发行", ["Steam"], "平台接入",
     "Steam 云存档接入", "端到端配置 Steam Cloud 自动存档路径与配额。",
     ["Steam", "云存档"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-build-upload", "商业化与发行", ["Steam"], "自动化",
     "SteamPipe 构建上传", "用 steamcmd 与受限 builder 账号上传构建，管理 beta 分支。",
     ["Steam", "SteamPipe", "CI"], True),
    ("wazzapsenk/steamworks-mcp", "steamworks-sdk-integration", "商业化与发行", ["Godot", "Unity", "Unreal", "Steam"], "代码生成",
     "Steamworks SDK 接入", "向 Unity/Godot/Unreal/C++ 游戏接入 Steamworks SDK，代码使用正确的 app id 与名称。",
     ["Steam", "SDK", "接入"], True),
    ("wazzapsenk/steamworks-mcp", "steamworks-steam-deck", "商业化与发行", ["Steam"], "方法指导",
     "Steam Deck 适配", "通过 Valve 兼容性审核：输入、显示、无缝切换与系统支持。",
     ["Steam", "Steam Deck"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-localize", "商业化与发行", ["Steam"], "方法指导",
     "Steam 内容本地化", "把商店页、成就等面向玩家的文本翻译到所有目标语言。",
     ["Steam", "本地化"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-achievements", "商业化与发行", ["Steam"], "方法指导",
     "Steam 成就设计", "为游戏设计成就的名称、描述与图标简报。",
     ["Steam", "成就"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-input", "商业化与发行", ["Steam"], "方法指导",
     "Steam 输入与手柄", "Steam Input 动作集、手柄模拟与 Xbox/PS/Switch/Deck 按键图标。",
     ["Steam", "手柄"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-review-analysis", "商业化与发行", ["Steam"], "平台接入",
     "Steam 评价分析", "读取同类游戏或自己游戏的最有帮助正负面评价，提炼可改点。",
     ["Steam", "评价"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-market-research", "商业化与发行", ["Steam"], "平台接入",
     "Steam 同类调研", "写商店文案之前，先看同类热门游戏的商店页怎么做。",
     ["Steam", "调研"], True),
    ("wazzapsenk/steamworks-mcp", "steamworks-api-reference", "商业化与发行", ["Steam"], "方法指导",
     "Steamworks 接口地图", "梳理 Steamworks SDK 与 Steam Web API：哪个接口做什么、回调与调用结果的区别。",
     ["Steam", "API"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-testing-sandbox", "商业化与发行", ["Steam"], "平台接入",
     "Steam 测试沙盒", "用 Valve 测试 App 480 试 SDK，再用自有 app 与测试分支验证。",
     ["Steam", "测试"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-dlc", "商业化与发行", ["Steam"], "方法指导",
     "Steam DLC 规划", "扩展包、装饰包、 OST 与 supporter pack 的定价与 roadmap 规划。",
     ["Steam", "DLC"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-community", "商业化与发行", ["Steam"], "方法指导",
     "Steam 社区运营", "与玩家沟通：更新说明、发布、路线图、直播与 Community Hub。",
     ["Steam", "社区"], False),
    ("wazzapsenk/steamworks-mcp", "steamworks-sales-estimate", "商业化与发行", ["Steam"], "平台接入",
     "Steam 销量估算", "由评价数反推相近游戏的销量，并给出首周区间估计。",
     ["Steam", "销量", "估算"], False),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-store-page-optimizer", "商业化与发行", ["Steam"], "方法指导",
     "Steam 商店页转化优化", "围绕曝光与转化优化商店页：胶囊图规格、描述结构、标签与预告片指引。",
     ["Steam", "商店页", "转化"], True),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-release-checklist", "商业化与发行", ["Steam"], "方法指导",
     "Steam 发版检查清单", "发版前逐项验证商店页、depot、成就、云存档、Steam Deck 兼容性。",
     ["Steam", "发版", "清单"], True),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-build-automation", "商业化与发行", ["Steam"], "自动化",
     "Steam 构建自动化", "用 GitHub Actions / GitLab CI / Jenkins 做 depot 上传与 beta 分支管理。",
     ["Steam", "CI", "SteamPipe"], True),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-pricing-strategy", "商业化与发行", ["Steam"], "方法指导",
     "Steam 定价策略", "地区定价、首发折扣、促销参与、捆绑与 F2P 转化策略。",
     ["Steam", "定价"], False),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-market-research", "商业化与发行", ["Steam"], "方法指导",
     "Steam 市场调研", "类型趋势、标签热度、竞品识别与市场空白分析。",
     ["Steam", "市场"], False),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-playtest-setup", "商业化与发行", ["Steam"], "方法指导",
     "Steam Playtest 配置", "创建 Playtest App、开放/NDA 试玩、密钥分发、注册页与反馈闭环。",
     ["Steam", "Playtest"], False),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-community-management", "商业化与发行", ["Steam"], "方法指导",
     "Steam 社区管理", "公告、活动、论坛版务、更新日志模板与 Community Hub 运营。",
     ["Steam", "社区"], False),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-wishlist-estimates", "商业化与发行", ["Steam"], "方法指导",
     "愿望单估算", "由关注者、评价数与公开信号估算愿望单量与转化基准。",
     ["Steam", "愿望单"], False),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-achievement-designer", "商业化与发行", ["Steam"], "方法指导",
     "Steam 成就设计器", "结构化成就定义：API 名、展示名、描述、图标要求与隐藏标记。",
     ["Steam", "成就"], False),
    ("AlexStormwood/agentic-skills", "steam-store-page-editor", "商业化与发行", ["Steam"], "方法指导",
     "Steam 商店页编辑", "撰写与迭代 Steam 商店页文案。",
     ["Steam", "商店页"], False),
    ("Tiny-Anvil/agent-skills", "designing-game-store-pages", "商业化与发行", ["Steam"], "方法指导",
     "游戏商店页设计", "设计游戏商店页的视觉与信息结构。",
     ["Steam", "商店页", "设计"], False),
    ("nick-vas/hyperdot", "store-page", "商业化与发行", ["Steam"], "方法指导",
     "商店页通用方法", "面向各游戏平台的商店页设计与表达方法。",
     ["商店页"], False),
    ("TMHSDigital/Steam-Cursor-Plugin", "steam-store-lookup", "商业化与发行", ["Steam"], "平台接入",
     "Steam 商店查询", "按名称或 App ID 查询商店页数据：价格、描述、标签、评价与发行日。",
     ["Steam", "数据"], False),

    # ---------- 工程与交付 ----------
    ("MRCalderon3D/everything-game-dev-code", "build-pipeline-patterns", "工程与交付", ["通用"], "方法指导",
     "构建流水线模式", "让构建可复现、可诊断、便于发布的 CI 流水线结构。",
     ["CI", "构建", "流水线"], True),
    ("MRCalderon3D/everything-game-dev-code", "performance-budgeting", "工程与交付", ["通用"], "方法指导",
     "性能预算", "在性能债务变成结构性负担前，先定下帧率、加载、内存与带宽预算。",
     ["性能", "预算"], True),
    ("MRCalderon3D/everything-game-dev-code", "tdd-workflow", "工程与交付", ["通用"], "方法指导",
     "测试驱动开发", "对玩法、工具与高风险技术工作应用测试先行的工作流。",
     ["TDD", "测试"], False),
    ("MRCalderon3D/everything-game-dev-code", "release-readiness", "工程与交付", ["通用"], "方法指导",
     "发布就绪评估", "判断一个构建是否真的可以对外测试、送审或上线。",
     ["发布", "就绪评估"], True),
    ("MRCalderon3D/everything-game-dev-code", "store-submission", "工程与交付", ["通用"], "方法指导",
     "商店提交准备", "准备面向商店的素材、元数据、合规文件与打包细节。",
     ["商店", "提交", "合规"], True),
    ("MRCalderon3D/everything-game-dev-code", "qa-test-matrix", "工程与交付", ["通用"], "方法指导",
     "测试覆盖矩阵", "建立覆盖矩阵，说明什么必须在什么配置、什么里程碑置信度下测过。",
     ["QA", "矩阵"], True),
    ("MRCalderon3D/everything-game-dev-code", "bug-triage", "工程与交付", ["通用"], "方法指导",
     "缺陷分级", "按玩家影响、可复现性、严重度与里程碑风险分级，决定先修哪个。",
     ["QA", "缺陷"], False),
    ("MRCalderon3D/everything-game-dev-code", "compliance-checklists", "工程与交付", ["通用"], "方法指导",
     "合规检查清单", "为法务、无障碍、隐私、平台与产品合规义务建立可执行清单。",
     ["合规", "清单"], False),
    ("RandallLiuXin/GodotMaker", "headless-build", "工程与交付", ["Godot"], "自动化",
     "无头构建", "在无图形环境的 CI 上执行 Godot 导入与导出。",
     ["Godot", "无头", "CI"], True),
    ("RandallLiuXin/GodotMaker", "godot-e2e", "工程与交付", ["Godot"], "自动化",
     "Godot 端到端测试", "驱动真实 Godot 运行时的端到端验证。",
     ["Godot", "E2E"], True),
    ("RandallLiuXin/GodotMaker", "visual-qa", "工程与交付", ["Godot"], "自动化",
     "视觉回归 QA", "对游戏画面做自动化视觉比对，拦截 UI 回归。",
     ["QA", "视觉回归"], True),
    ("RandallLiuXin/GodotMaker", "screenshot", "工程与交付", ["Godot"], "自动化",
     "运行时截图", "在无头运行时中抓取游戏画面用于验证与素材。",
     ["Godot", "截图"], False),
    ("RandallLiuXin/GodotMaker", "project-scaffold", "工程与交付", ["Godot"], "自动化",
     "Godot 工程脚手架", "按流水线约定生成标准 Godot 工程结构。",
     ["Godot", "脚手架"], False),
    ("jackli12/codex-game-studio", "qa-lead", "工程与交付", ["通用"], "方法指导",
     "QA 负责人", "测试策略、验收标准、冒烟测试、回归计划与发布阻塞。",
     ["QA", "测试策略"], False),
    ("jackli12/codex-game-studio", "release-manager", "工程与交付", ["通用"], "方法指导",
     "发布管理", "发布就绪检查、打包评审、发布说明与最终交付校验。",
     ["发布", "交付"], False),
    ("jackli12/codex-game-studio", "prepare-release", "工程与交付", ["通用"], "方法指导",
     "发布准备", "发布就绪评审、打包验证与最终交付检查表。",
     ["发布", "检查表"], False),
    ("jackli12/codex-game-studio", "run-qa-pass", "工程与交付", ["通用"], "自动化",
     "执行测试轮次", "跑一轮冒烟、回归或验收评审并做缺陷分级。",
     ["QA", "回归"], False),
    ("jackli12/codex-game-studio", "producer", "工程与交付", ["通用"], "方法指导",
     "制作人", "范围控制、里程碑规划、优先级与交付顺序。",
     ["制作", "范围"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-ci-pipeline", "工程与交付", ["通用"], "自动化",
     "游戏 CI 流水线", "GameForge 的 CI 流水线角色配置与门禁。",
     ["CI", "流水线"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-code-review", "工程与交付", ["通用"], "方法指导",
     "游戏代码评审", "面向游戏项目的代码评审角色与检查点。",
     ["评审"], False),

    # ---------- 质量与运营 ----------
    ("jame581/GodotPrompter", "state-machine", "质量与运营", ["Godot"], "代码生成",
     "状态机实现", "枚举、节点与 Resource 三种状态机范式的取舍与实现。",
     ["Godot", "状态机"], False),
    ("jame581/GodotPrompter", "animation-system", "质量与运营", ["Godot"], "代码生成",
     "动画系统", "AnimationPlayer、AnimationTree、混合树、状态机与精灵动画。",
     ["Godot", "动画"], False),
    ("jame581/GodotPrompter", "particles-vfx", "质量与运营", ["Godot"], "代码生成",
     "粒子与特效", "GPUParticles2D/3D、发射形状、子发射器、拖尾与常见 VFX 配方。",
     ["Godot", "VFX"], False),
    ("jame581/GodotPrompter", "audio-system", "质量与运营", ["Godot"], "代码生成",
     "音频系统", "音频总线、播放器、空间音频、音乐管理与音效池。",
     ["Godot", "音频"], False),
    ("jame581/GodotPrompter", "physics-system", "质量与运营", ["Godot"], "方法指导",
     "物理系统", "物理体、碰撞形状、射线检测、Area 与物理插值。",
     ["Godot", "物理"], False),
    ("jame581/GodotPrompter", "tween-animation", "质量与运营", ["Godot"], "代码生成",
     "补间动画", "属性补间、方法补间、串联、并行、缓动与常见动效配方。",
     ["Godot", "补间"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-design-review", "质量与运营", ["通用"], "方法指导",
     "设计评审", "GameForge 的设计评审角色，检查设计与支柱的一致性。",
     ["评审", "设计"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-balance-check", "质量与运营", ["通用"], "方法指导",
     "数值平衡检查", "对经济与成长数值做系统化平衡体检。",
     ["平衡", "数值"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-analytics-setup", "质量与运营", ["通用"], "方法指导",
     "游戏埋点分析", "搭建游戏分析埋点，回答产品问题而不制造噪声与隐私风险。",
     ["埋点", "分析"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-accessibility-specialist", "质量与运营", ["通用"], "方法指导",
     "无障碍专项", "无障碍专项角色，覆盖可访问性要求与实现。",
     ["无障碍"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-jam-mode", "质量与运营", ["通用"], "方法指导",
     "Game Jam 模式", "限时条件下的范围裁剪与功能取舍策略。",
     ["Game Jam", "范围"], False),
    ("AlterLab-IEU/AlterLab_GameForge", "game-localization-manager", "质量与运营", ["通用"], "方法指导",
     "本地化管理", "协调多语言文案、术语表与文化适配的质量。",
     ["本地化"], False),

    # ---------- 平台与后端 ----------
    ("MRCalderon3D/everything-game-dev-code", "memory-budgeting", "平台与后端", ["通用"], "方法指导",
     "内存预算", "为资源驻留、加载与运行时系统设定内存预算以适配目标平台。",
     ["内存", "预算"], False),
    ("MRCalderon3D/everything-game-dev-code", "telemetry-instrumentation", "平台与后端", ["通用"], "方法指导",
     "遥测与埋点", "实现能回答产品问题的分析与观测钩子，且不制造噪声与隐私风险。",
     ["埋点", "遥测"], False),
    ("jame581/GodotPrompter", "ai-navigation", "平台与后端", ["Godot"], "代码生成",
     "AI 导航", "NavigationAgent2D/3D、转向行为、行为树与巡逻模式。",
     ["Godot", "AI"], False),
    ("jame581/GodotPrompter", "multiplayer-basics", "平台与后端", ["Godot"], "代码生成",
     "多人联机基础", "MultiplayerAPI、ENet/WebSocket 对等端与权限模型。",
     ["Godot", "联机"], False),
    ("jame581/GodotPrompter", "camera-system", "平台与后端", ["Godot"], "代码生成",
     "相机系统", "平滑跟随、屏幕震动、相机区域与 2D/3D 转场。",
     ["Godot", "相机"], False),
    ("jame581/GodotPrompter", "procedural-generation", "平台与后端", ["Godot"], "代码生成",
     "程序化生成", "噪声地形、BSP 地牢、元胞自动机、WFC 与种子化随机。",
     ["Godot", "程序生成"], False),
]


def load_first_party_commit():
    """读取第一方条目使用的仓库 commit。

    第一方技能就在本仓库内，`source_commit` 指向**包含这些技能文件的那次提交**，
    这样目录里的 commit 与内容哈希都能被独立核实。
    两段式提交：先提交技能源码 → 记录该 commit → 生成目录 → 再提交目录。
    """
    p = os.path.join(HUB, "data", "first-party-commit.txt")
    if os.path.isfile(p):
        v = open(p, encoding="utf-8").read().strip()
        if re.fullmatch(r"[0-9a-f]{40}", v):
            return v
    return "0" * 40


def load_raw():
    with open(RAW, encoding="utf-8") as f:
        return json.load(f)


def build():
    raw = load_raw()
    with open(REPORT, encoding="utf-8") as f:
        report = json.load(f)

    index = {}
    for s in raw:
        index[(s["repo"], s["skill_name"])] = s

    entries = []
    seen = set()
    missing = []
    for (repo, name, cat, engines, cap, title, summary, tags, featured) in SELECTION:
        if (repo, name) in seen:
            missing.append(f"重复条目: {repo}#{name}")
            continue
        seen.add((repo, name))
        hit = index.get((repo, name))
        if not hit:
            missing.append(f"未找到: {repo}#{name}")
            continue
        head = report[repo]["head"]
        lic = REPO_LICENSE.get(repo, "未声明")
        e = {
            "id": f"{repo.replace('/', '--')}--{name}",
            "repo": repo,
            "repo_url": f"https://github.com/{repo}",
            "path": hit["path"],
            "name": name,
            "title": title,
            "summary": summary,
            "category": cat,
            "platforms": engines,
            "capability": cap,
            "author": repo.split("/")[0],
            "license": lic,
            "license_url": f"https://github.com/{repo}/blob/{head}/LICENSE",
            "source_url": f"https://github.com/{repo}/blob/{head}/{hit['path']}",
            "source_commit": head,
            "content_sha256": hit["sha256"],
            "content_bytes": hit["bytes"],
            "checked_at": CHECKED_AT,
            "verification": "source-checked",
            "tested": False,
            "cost": "模型调用费用另计；部分技能需要 Steamworks / MCP 服务账号",
            "requirements": [
                "支持 SKILL.md 的 AI 客户端",
                "Node.js 22+（若技能含脚本）",
            ],
            "compatibility": "通用 SKILL.md 格式；未逐客户端实测",
            "limitations": (
                "仅完成来源核对（文件真实存在、内容哈希已记录），未做业务效果实测；"
                "真实数据与外部操作能力需按原文及所连接工具核实。"
            ),
            "tags": tags,
            "featured": featured,
            "origin": "third-party",
        }
        if lic in LICENSE_NOTE:
            e["license_note"] = LICENSE_NOTE[lic]
        entries.append(e)

    if missing:
        print("!! 未解析条目：")
        for m in missing:
            print("   -", m)

    # ---- first-party：Hashrise 自研技能 ----
    fp_root = os.path.join(HUB, "skills")
    fp_commit = load_first_party_commit()
    fp = []
    for d in sorted(os.listdir(fp_root)):
        sk = os.path.join(fp_root, d, "SKILL.md")
        if not os.path.isfile(sk):
            continue
        raw_bytes = open(sk, "rb").read()
        text = raw_bytes.decode("utf-8")
        fm = {}
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
        if m:
            for line in m.group(1).split("\n"):
                line = line.strip()
                if ":" in line and not line.startswith("#"):
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip().strip("'\"")
        name = fm.get("name") or d
        meta_path = os.path.join(fp_root, d, "meta.json")
        meta = {}
        if os.path.isfile(meta_path):
            meta = json.load(open(meta_path, encoding="utf-8"))
        fp.append({
            "id": f"hashrise-studio--hashrise-skills-hub--{name}",
            "repo": "hashrise-studio/hashrise-skills-hub",
            "repo_url": "https://github.com/hashrise-studio/hashrise-skills-hub",
            "path": f"skills/{d}/SKILL.md",
            "name": name,
            "title": meta.get("title", fm.get("title", name)),
            "summary": meta.get("summary", fm.get("description", "")[:120]),
            "category": meta.get("category", "概念与策划"),
            "platforms": meta.get("platforms", ["Godot"]),
            "capability": meta.get("capability", "方法指导"),
            "author": "hashrise-studio",
            "license": "MIT",
            "license_url": f"https://github.com/hashrise-studio/hashrise-skills-hub/blob/{fp_commit}/LICENSE",
            "source_url": f"https://github.com/hashrise-studio/hashrise-skills-hub/blob/{fp_commit}/skills/{d}/SKILL.md",
            "source_commit": fp_commit,
            "content_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "content_bytes": len(raw_bytes),
            "checked_at": CHECKED_AT,
            "verification": "first-party",
            "tested": True,
            "cost": "免费；随《算力崛起 Hashrise》工程实践一起产出",
            "requirements": ["支持 SKILL.md 的 AI 客户端"],
            "compatibility": "通用 SKILL.md 格式",
            "limitations": meta.get("limitations", "首次方技能，方法来自 Hashrise 真实工程实践，未覆盖所有引擎与项目类型。"),
            "tags": meta.get("tags", ["Hashrise"]),
            "featured": True,
            "origin": "first-party",
            "evidence": meta.get("evidence", "来源：Hashrise 项目内对应设计文档与工程实现"),
        })

    entries = fp + entries
    entries.sort(key=lambda e: (e["origin"] != "first-party", -int(e["featured"]), e["category"], e["title"]))

    cats = {}
    engs = {}
    caps = {}
    for e in entries:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
        caps[e["capability"]] = caps.get(e["capability"], 0) + 1
        for p in e["platforms"]:
            engs[p] = engs.get(p, 0) + 1

    catalog = {
        "version": 1,
        "updated_at": CHECKED_AT,
        "coverage": (
            "精选目录：收录 Hashrise 第一方技能与已核实的第三方开源游戏开发 Skill；"
            "未覆盖全网，来源核对不等于业务实测。"
        ),
        "stats": {
            "total": len(entries),
            "first_party": len(fp),
            "third_party": len(entries) - len(fp),
            "repos": len({e["repo"] for e in entries}),
            "categories": len(cats),
            "engines": len(engs),
        },
        "facets": {
            "category": cats,
            "platform": engs,
            "capability": caps,
        },
        "skills": entries,
        "collection": {
            "collected_at": CHECKED_AT,
            "method": (
                "候选仓库本地浅克隆 → 全量 SKILL.md frontmatter 抽取 → 路径关键词预筛 → "
                "人工逐条阅读与策展 → 记录 commit 与内容 sha256。"
            ),
            "scope_complete": False,
            "repositories_scanned": len(report),
            "raw_candidate_files": len(raw),
            "published_skills": len(entries),
            "tested_skills": len(fp),
            "note": (
                "第三方条目均为 source-checked（文件与哈希已核实），tested=false；"
                "第一方条目 tested=true，其证据来自 Hashrise 项目内的真实设计文档与工程实现。"
            ),
        },
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=1)
    print(f"catalog 写入 {OUT}")
    print(f"  总计 {len(entries)} 条｜第一方 {len(fp)}｜第三方 {len(entries) - len(fp)}")
    print(f"  分类 {len(cats)} 个：{cats}")
    print(f"  引擎 {len(engs)} 个：{engs}")
    print(f"  能力 {len(caps)} 个：{caps}")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(build())
