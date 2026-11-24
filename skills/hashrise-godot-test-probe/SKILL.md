---
name: hashrise-godot-test-probe
description: 用无头探针脚本（extends SceneTree）在 Godot 4.x 里做逻辑自检、UI 面板驱动测试与存档往返验证，产出可被 CI 抓取的 PASS/FAIL 文本结果。当用户要写 Godot 自动化测试、排查灰屏/空面板、验证数值边界与老档兼容、或想把测试接进 CI 时使用。
---

# Godot 无头探针式验证

Godot 的单元测试生态（GUT / gdUnit4）适合纯逻辑单测。但**场景级问题**——面板是空的、灰屏、存档往返丢数据、事件连发崩溃——用探针脚本更直接。

Hashrise 用的是 `extends SceneTree` 的无头探针：不引入测试框架依赖，CI 里一条命令就能跑。

## 运行方式

```bash
godot --headless -s res://tests/logic_check.gd
```

## 骨架（直接复制）

```gdscript
# tests/logic_check.gd
# <覆盖范围说明>
# 运行：godot --headless -s res://tests/logic_check.gd
extends SceneTree

var _fails: int = 0
var _pass: int = 0
var _lf: FileAccess = null  # 直写文件，绕开 stdout 缓冲

func _log(line: String) -> void:
	if _lf == null:
		_lf = FileAccess.open("res://_logic_out.txt", FileAccess.WRITE)
	if _lf != null:
		_lf.store_line(line)
		_lf.flush()

func _t(cond: bool, label: String) -> void:
	if cond:
		_pass += 1
		_log("PASS  " + label)
	else:
		_fails += 1
		_log("FAIL  " + label)

func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)

func _run() -> void:
	# 真正的检查逻辑写在这里
	_t(true, "示例检查")
	_log("=== %d passed, %d failed ===" % [_pass, _fails])
```

四个关键点，缺一不可：

| 元素 | 为什么必须 |
|------|-----------|
| `extends SceneTree` | 无头模式下以 SceneTree 为入口，不需要挂节点 |
| `_initialize()` + `process_frame.connect(_run, CONNECT_ONE_SHOT)` | 等场景树就绪再跑，且只跑一次 |
| **直写文件**（`FileAccess`）+ `flush()` | **headless 重定向下 `print` 的尾部会被吞掉**，必须落盘 |
| PASS/FAIL 前缀 + 末尾汇总行 | CI 用 `grep -q "FAIL"` 就能判定 |

## 为什么必须直写文件

这是 Hashrise 实际踩出来的坑：

```gdscript
# ❌ headless 下末尾输出会丢
print("=== 42 passed, 0 failed ===")
```

```gdscript
# ✅ 直写并 flush
_lf.store_line("=== %d passed, %d failed ===" % [_pass, _fails])
_lf.flush()
```

CI 里读文件，不要指望 stdout。

## 逻辑自检探针

检查**系统行为**时，直接从 `/root/` 拿单例：

```gdscript
func _run() -> void:
	var sim = root.get_node_or_null("/root/Simulation")
	_t(sim != null, "Simulation 单例存在")
	if sim == null:
		return
	# 边界值逐个打
	_t(sim.get_net_rate(0) == 0, "算力为 0 时净收益为 0")
```

**Hashrise 逻辑探针实际覆盖的**（可作为覆盖清单参考）：

- 超时时长上限（300s 封顶）与广告叠加封顶（1800）
- 电力系统：容量 / 供电系数 / 变压器买卖 / 槽位上限
- 挖矿 10% 分流铸造
- 随机事件 30 连发不崩
- 存档往返一致性与老档兼容

## UI 面板驱动探针

排查"灰屏 / 面板打不开 / 点了没反应"这类问题，用探针**程序化打开每个面板**并检查内容。

```gdscript
# tests/ui_drive_check.gd
# 面板驱动测试（headless 运行：godot --headless -s res://tests/ui_drive_check.gd）
extends SceneTree

# 统计"有效"子节点（排除 pending queue_free 的旧节点）
func _live_children(vb: Node) -> int:
	var n: int = 0
	for c in vb.get_children():
		if not c.is_queued_for_deletion():
			n += 1
	return n
```

要点：

1. **逐个打开面板**，而不是一次性全开——要复刻玩家真实的导航路径。
2. **打开前先关掉上一个**，确认切换链路正常。
3. **统计有效子节点数**，`> 0` 才算面板有内容。空面板 = 灰屏根因。
4. 统计时**排除 `is_queued_for_deletion()`** 的节点：上一个面板的旧节点还没真正销毁，不排除会误判。

```gdscript
	for panel in ["upgrade", "shop", "market", "settings", "overview"]:
		_open(panel)
		var n := _live_children(_panel_root())
		_t(n > 0, "面板 %s 有内容 (子节点 %d)" % [panel, n])
		_close()
```

## 存档往返验证

存档是最容易"看着对其实丢数据"的地方。探针要**写 → 读 → 比对**：

```gdscript
	var before := GameState.get_snapshot()
	SaveManager.save()
	GameState.reset()
	SaveManager.load()
	var after := GameState.get_snapshot()
	_t(before.hash() == after.hash(), "存档往返数据一致")
```

老档兼容要单独测：构造一个旧版本存档的字典，走 `SaveManager` 的迁移函数后读回来。

## 接进 CI

```yaml
- name: Headless logic check
  run: |
    set +e
    tools/godot --headless -s res://tests/logic_check.gd 2>&1 | tee "build/logic.txt"
    set -e
    if grep -q "^FAIL" "res://_logic_out.txt"; then
      echo "::error::Logic check failed"
      cat "res://_logic_out.txt"
      exit 1
    fi
```

- `set +e`：Godot headless 即使全部通过也可能返回非零（与导出同一个坑，见 `hashrise-godot-ci-build`）。
- 判定读**落盘文件**，不读 stdout。
- 失败时把文件内容打进日志，`::error::` 让 GitHub 侧栏直接显示。

## 什么时候用探针而不是 GUT/gdUnit4

| 场景 | 用什么 |
|------|--------|
| 纯函数、工具类、算法 | GUT / gdUnit4（单测更快更规范） |
| 单例系统行为（经济、库存、存档） | 探针脚本 |
| 场景级 UI 问题（灰屏、空面板） | 探针脚本 |
| 视觉正确性 | 探针 + 截图，人工或视觉比对 |

**理由**：探针零依赖、能在任何 CI runner 上跑、不需要测试框架的导入与配置。对 solo / AI 协作的项目，这个"能跑起来"的优势往往比"更规范"更重要。

## 常见坑

| 现象 | 根因 | 修法 |
|------|------|------|
| 脚本跑完什么都没有 | headless 下 stdout 尾部被吞 | 直写文件 + flush |
| `print` 有输出但 CI 判定失败 | 判定读 stdout，而尾部丢了 | 判定读落盘文件 |
| 面板有节点但判定为灰屏 | 没排除待删除节点 | `is_queued_for_deletion()` 过滤 |
| CI 报失败但本地跑过 | Godot headless 返回非零 | `set +e` + 自行判定 |
| 探针里拿不到单例 | 自动加载未注册 | 查 `project.godot` 的 `[autoload]` |
| 探针改坏了正式存档 | 直接写了 `user://` 正式存档 | 探针用独立的存档路径或临时目录 |
