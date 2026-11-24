# 贡献指南

## 加一条第三方技能

1. 确认上游仓库的 `SKILL.md` **真实存在**，记录其 commit。
2. 克隆到本地临时目录，读取 `SKILL.md` 的 frontmatter 与正文。
3. 在 `scripts/curate.py` 的 `SELECTION` 里加一条：

```python
("owner/repo", "skill-name", "分类", ["引擎"], "能力形态",
 "中文标题", "中文摘要（1～2 句，说明它具体能做什么）",
 ["标签1", "标签2"], False),
```

**中文摘要必须手写**，不要机翻——摘要质量是本站的核心价值。

4. 在 `REPO_LICENSE` 里登记该仓库的许可证。非 MIT/Apache 的还要在 `LICENSE_NOTE` 里加一句提示。
5. 重新策展并校验：

```bash
python scripts/curate.py
node scripts/validate.mjs
npm test
node scripts/build.mjs
```

## 分类与维度取值

只允许以下取值（`scripts/validate.mjs` 会强校验）：

- **分类**：概念与策划 / 引擎与实现 / 美术与音频 / 商业化与发行 / 工程与交付 / 质量与运营 / 平台与后端 / 导航与工具
- **引擎**：Godot / Unity / Unreal / Web / Blender / Steam / 通用
- **能力**：方法指导 / 代码生成 / 自动化 / 平台接入

## 加一个第一方技能

第一方技能放在 `skills/<name>/`，需含：

- `SKILL.md` —— 带 `name` 与 `description` frontmatter
- `meta.json` —— 含 `title` / `summary` / `category` / `platforms` / `capability` / `tags` / `evidence` / `limitations`
- `references/` —— 支撑文档（可选但推荐）

内容必须来自**真实工程实践**：写出具体的坑、具体的参数、具体的文件路径。泛泛而谈的方法论没有价值。

## 提交前必过

```bash
node scripts/validate.mjs   # 字段、commit、哈希、许可证、安装命令
npm test                    # 检索逻辑与目录一致性
node scripts/build.mjs      # 构建
```

## 两条硬规矩

1. **来源必须可核实。** 每条第三方条目都要有真实的 commit 与内容 sha256。查不到就不收录。
2. **验证状态不许夸大。** 第三方条目一律 `tested: false`。只有第一方技能能标 `tested: true`，且必须提供 `evidence`。
