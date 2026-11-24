# AGENTS.md

给 AI 协作者的工作约定。

## 这个仓库是什么

独立游戏开发的 AI Skill 导航站。**它同时是产品和技术骨架**：

- 对外：可视化导航页 + 可导入的技能包
- 对内：策展脚本 + 目录校验 + 构建流水线

## 目录职责

| 路径 | 职责 | 谁改 |
|------|------|------|
| `data/catalog.json` | 目录唯一数据源 | **只由 `scripts/curate.py` 生成**，不要手改 |
| `scripts/curate.py` | 策展逻辑：选哪些条目、分类、摘要、许可证 | 人工策展时改 |
| `src/search.mjs` | 检索核心（站点与技能共用） | 加检索维度时改 |
| `src/app.mjs` | 站点逻辑 | 改交互时改 |
| `src/style.css` | 样式，设计 token 来自 Hashrise 美术圣经 | 改视觉时改 |
| `skills/hashrise-find-game-dev-skills/` | 导航技能包 | 改导航说明时改 |
| `skills/hashrise-<其他>/` | 第一方技能 | 加新技能时建 |

## 硬规矩

1. **`data/catalog.json` 不能手改。** 改 `scripts/curate.py` 然后重新策展。
2. **中文摘要手写。** 不做机器翻译。
3. **第三方条目 `tested` 永远是 `false`。** 只有第一方能标 `true`，且必须有 `evidence`。
4. **许可证如实登记。** 非 MIT/Apache 的必须带 `license_note`。
5. **`catalog.json` 必须是 LF。** CRLF 会改变 sha256，导致完整性校验失败。构建脚本会检测并报错。

## 改完必须跑

```bash
node scripts/validate.mjs
npm test
node scripts/build.mjs
```

## 两段式提交（重要）

第一方条目的 `source_commit` 必须指向**真正包含该技能文件的那次提交**，否则外部无法核实哈希。

流程：

1. 先提交技能源码（不含 `data/catalog.json`）
2. `git rev-parse HEAD > data/first-party-commit.txt`
3. `python scripts/curate.py` —— 目录会引用上面这个 commit
4. 再提交 `data/catalog.json` 与 `data/first-party-commit.txt`

这样目录里的 commit + sha256 可以被独立验证。
