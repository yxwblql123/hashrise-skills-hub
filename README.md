# Hashrise 游戏开发 Skill 导航

> 面向独立游戏开发的 AI Skill 导航 —— GDD 起草 / Godot 场景与架构 / Steam 商店页 / CI 构建。

🌐 **在线导航**：https://yxwblql123.github.io/hashrise-skills-hub/
📦 **仓库**：https://github.com/yxwblql123/hashrise-skills-hub

**第一方技能来自《算力崛起 Hashrise》的真实工程实践（已验证），第三方技能逐条核实文件、commit 与内容哈希。**

---

## 这是什么

一套**可对外分享**的独立游戏开发 Skill 索引，包含：

- **190 条目录**：9 个第一方技能（已验证）+ 181 个第三方开源技能（核实来源）
- **22 个上游仓库**，覆盖 Godot / Unity / Unreal / Web / Blender / Steam
- **可视化导航页**：按开发阶段、引擎维度、能力形态、来源筛选
- **目录完整性校验**：每条记录锁定来源 commit 与内容 sha256
- **可导入的技能包**：打包成 ZIP，导入任何支持 SKILL.md 的客户端

## 快速开始

```bash
npm install          # 无依赖，仅需 Node.js 22+
npm run validate     # 校验目录完整性
npm run build        # 构建站点 + 便携单文件页 + 技能 ZIP
npm run dev          # 本地预览 http://127.0.0.1:4173
```

构建产物：

| 路径 | 说明 |
|------|------|
| `dist/index.html` | 站点（需 `dist/data/catalog.json`） |
| `dist/preview.html` | **便携单文件版**：目录/CSS/JS/图标全部内联，断网可用 |
| `dist/downloads/hashrise-find-game-dev-skills.zip` | 可导入的导航技能包 |
| `dist/downloads/hashrise-skills-hub-source.zip` | 完整源码包 |

## 目录结构

```
hashrise-skills-hub/
├── data/
│   └── catalog.json              目录数据（唯一数据源）
├── scripts/
│   ├── curate.py                 策展脚本：从候选仓库生成目录
│   ├── build.mjs                 构建：站点 + 便携页 + ZIP
│   └── validate.mjs              目录完整性校验
├── src/
│   ├── index.html                站点骨架
│   ├── app.mjs                   站点逻辑
│   ├── search.mjs                检索核心（站点与技能共用）
│   └── style.css                 样式（设计 token 取自 Hashrise 美术圣经）
├── skills/
│   ├── hashrise-find-game-dev-skills/    导航技能（可安装，旗舰条目）
│   ├── hashrise-gdd-author/              第一方：八节格式 GDD
│   ├── hashrise-design-pillars/          第一方：设计支柱与漂移检查
│   ├── hashrise-godot-architecture/      第一方：Godot 三层架构
│   ├── hashrise-godot-offline-reconcile/ 第一方：离线收益对账
│   ├── hashrise-godot-ci-build/          第一方：CI 与每日构建
│   ├── hashrise-godot-test-probe/        第一方：无头探针验证
│   ├── hashrise-monetization-guard/      第一方：变现 P2W 红线
│   └── hashrise-steam-store-page/        第一方：Steam 商店页
└── tests/
```

## 目录条目结构

每条记录都带可核实的来源信息：

```json
{
  "id": "jame581--GodotPrompter--scene-organization",
  "repo": "jame581/GodotPrompter",
  "path": "skills/scene-organization/SKILL.md",
  "name": "scene-organization",
  "title": "场景树组织",
  "summary": "场景树结构设计：组合还是继承、何时拆分场景、节点层级范式。",
  "category": "引擎与实现",
  "platforms": ["Godot"],
  "capability": "方法指导",
  "license": "MIT",
  "source_commit": "426e8ab5...",
  "content_sha256": "…",
  "checked_at": "2026-11-24",
  "verification": "source-checked",
  "tested": false,
  "origin": "third-party"
}
```

### 验证状态的含义

| 字段 | 含义 |
|------|------|
| `origin: first-party` + `tested: true` | 本项目自研，方法来自 Hashrise 真实工程实践，`evidence` 字段说明证据 |
| `origin: third-party` + `tested: false` | **仅核实了文件存在、commit 与内容哈希**，未做业务效果实测 |

**这是刻意的区分。** 第三方技能"来源已核对"不等于"业务已实测"，两者不可混为一谈。

### 许可证如实登记

MIT / Apache-2.0 之外的许可证（BUSL-1.1、CC-BY-NC-4.0、未声明）都会带 `license_note` 说明，前端用醒目样式标出。**CC-BY-NC-4.0 禁止商用**，目录里已标注。

## 策展流程

`scripts/curate.py` 是可重跑的：

1. 本地浅克隆候选仓库
2. 全量抽取 `SKILL.md` frontmatter
3. 路径关键词预筛（超大聚合仓库用）
4. **人工逐条阅读与策展**（中文摘要、分类、引擎维度由人工标注，不做机器翻译）
5. 记录 commit 与内容 sha256

```bash
python scripts/curate.py     # 重新生成 data/catalog.json
```

## Windows 必踩坑

`catalog.json` 自带 sha256 校验，而 Windows 的 Git 默认 `core.autocrlf=true` 会把 LF 转成 CRLF，导致**内容哈希变化、完整性校验失败**（但页面照样能开，极易误判"装好了"）。

```bash
git config core.autocrlf false
git checkout HEAD -- data/catalog.json skills/
```

构建脚本会在检测到 CRLF 时直接报错并给出修复命令。

## 安装导航技能

```bash
# 方式一：直接安装技能包
npx skills add yxwblql123/hashrise-skills-hub --skill hashrise-find-game-dev-skills -a codex

# 方式二：WorkBuddy —— 导入 ZIP
# 1) 下载 dist/downloads/hashrise-find-game-dev-skills.zip
# 2) 「专家·技能·连接器」→「技能」→「添加技能 → 上传技能」
```

## 检索

```bash
cd skills/hashrise-find-game-dev-skills
node scripts/search.mjs --query "Godot 场景架构" --limit 5
node scripts/search.mjs --category "商业化与发行" --engine "Steam"
node scripts/search.mjs --origin first-party
```

## 测试

```bash
npm test          # 检索逻辑与目录一致性测试
npm run validate  # 目录字段、commit、哈希、许可证、安装命令校验
```

## 关于第一方技能

9 个第一方技能——8 个提炼自《算力崛起 Hashrise》的真实文档与代码，1 个是本导航站自身：

| 技能 | 来源 |
|------|------|
| `hashrise-gdd-author` | `design/gdd/` 八节格式与一致性红线 |
| `hashrise-design-pillars` | `design/gdd/gdd-main.md §1` 设计支柱与反例 |
| `hashrise-godot-architecture` | `docs/architecture/main-architecture.md` + ADR-001/002/003 |
| `hashrise-godot-offline-reconcile` | `docs/architecture/adr/adr-002-offline-reconciliation.md` |
| `hashrise-godot-ci-build` | `.github/workflows/daily-build.yml` |
| `hashrise-godot-test-probe` | `tests/logic_check_g5.gd`、`tests/ui_drive_check.gd` |
| `hashrise-monetization-guard` | `design/gdd/systems/monetization.md` |
| `hashrise-steam-store-page` | `design/gdd/gdd-main.md §3.1` 合规红线 + `design/art/asset-spec.md` |
| `hashrise-find-game-dev-skills` | 本仓库自研：策展脚本 + 目录校验 + 构建流水线 |

**方法可迁移，具体数值与配置需按项目调整。**

## 许可证

本仓库 MIT。目录中收录的第三方技能版权归各自作者，遵循其各自许可证。
