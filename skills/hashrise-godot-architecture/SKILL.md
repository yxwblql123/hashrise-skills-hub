---
name: hashrise-godot-architecture
description: 在 Godot 4.x 项目里落地 Hashrise 的三层架构（UI 层 / 模拟层 / 数据状态层），包括 EventBus 解耦、数值 Resource 资源化、状态与数据分离、模拟与表现分离。当用户要搭 Godot 项目骨架、拆分系统职责、消除 UI 里写逻辑的问题，或审查现有项目架构时使用。
---

# Godot 三层架构落地

Hashrise 用三条原则撑起整个工程骨架。这套结构可直接套用到任何**数据驱动的模拟经营/放置类** Godot 项目。

## 三条原则

1. **数据与状态分离**：静态调参数据用 `Resource`，运行时态用 `GameState`。调平衡只改资源文件，不碰代码。
2. **模拟与表现分离**：经济在模拟层按固定频率推进，UI 只订阅事件被动刷新，**绝不在 `_process` 里重算经济**。
3. **变现与玩法解耦**：广告 / 内购藏在接口背后，玩法代码只调用抽象方法，真实 SDK 后续插入。

## 分层结构

```
┌──────────────────────────────────────────────────────────┐
│  UI 层 (Control 节点)                                     │
│  HUD · 底部导航 · 升级/行情/编年史/设置面板 · 离线/广告弹窗   │
│  只读 GameState 快照 + 订阅 EventBus，不写经济逻辑          │
└───────────────▲ EventBus(signals) ───────────┬───────────┘
                │                               │
┌───────────────┴───────────────────────────────▼───────────┐
│  模拟层 (Autoload 单例)                                    │
│  Simulation → Economy 计算 + Market 游走 + Risk 抽样        │
│  1Hz Timer 主循环；写 GameState；发 EventBus                │
└───────────────▲                │                          │
                │                ▼                          │
┌───────────────┴───────────────────────────────┬───────────┐
│  数据 / 状态层                                            │
│  Config(Resources) · GameState(运行时) · SaveManager        │
└───────────────────────────────────────────────────────┬───┘
                                                        │
                                    ┌───────────────────▼───┐
                                    │  外部 SDK（可后插）     │
                                    │  AdProvider · IAPProvider│
                                    └───────────────────────┘
```

## 自动加载（Autoload）注册表

Hashrise 的 `project.godot` 实际配置，可直接抄：

```ini
[autoload]
EventBus="*res://core/EventBus.gd"
RNG="*res://core/RNG.gd"
Config="*res://core/Config.gd"
GameState="*res://core/GameState.gd"
SaveManager="*res://core/SaveManager.gd"
AuthManager="*res://core/AuthManager.gd"
Simulation="*res://core/Simulation.gd"
Monetization="*res://core/Monetization.gd"
AudioManager="*res://core/audio/AudioManager.gd"
```

**注册顺序有意义**：`EventBus` 最早（所有人依赖它），`Config` 早于 `GameState`（状态初始化要查表），`Simulation` 靠后（它依赖前面全部）。

Hashrise 目录约定：

```
core/          # 单例与全局系统
  data/        # Resource 定义（MinerData / CurrencyData / GlobalUpgradeData）
  ads/         # AdProvider 抽象 + 各平台实现 + Stub
  iap/         # IAPProvider 抽象 + StoreKit 实现 + Stub
  audio/       # AudioManager
scenes/        # .tscn 与配套 .gd（场景驱动）
design/        # GDD 与设计文档（数值的唯一权威源）
docs/          # 架构文档与 ADR
tests/         # 无头探针式验证脚本
tools/         # 引擎二进制与构建脚本
```

## 数值 Resource 资源化

**规则：玩法逻辑里禁止出现具体数值。** 全部走 `Config` 查表。

```gdscript
# ✅ 正确
var miner: MinerData = Config.get_miner("gpu")
var cost := miner.base_price

# ❌ 错误
var cost := 120
```

三个具体资源类型：

| 资源 | 承载内容 |
|------|---------|
| `MinerData` | 矿机静态参数：算力 / 功耗 / 单价 / 升级基准价 / 支持币种 / 解锁方式 |
| `CurrencyData` | 币种参数：产出系数 / 基准行情 / 游走 σ / 游走 band / 均值回归率 |
| `GlobalUpgradeData` | 全局升级：基础成本 / 成本乘数 / 每级效果 / 联动系统 |

配套约定：

- `Config` 提供 `get_miner(id)` / `get_currency(id)` / `get_upgrade(id)`，逻辑层**不直接 `load()`** 资源。
- 资源内数值与设计文档严格一致；**任何数值调整先回写设计文档，再改 `.tres`**，保持单一权威源。
- 运行时态（余额、数量、当前行情价）**不**放进 Resource，归 `GameState`。

### 为什么不用其他方案

| 方案 | 否决理由 |
|------|---------|
| 常量脚本 `const BASE_PRICE=30` | 仍是代码内数值，无法可视化调参，与设计文档双源 |
| JSON/CSV 外部配置表 | 失去 Godot 类型安全与 `.tres` 引用，需自建解析校验 |
| 远程配置（Firebase 等） | 严重过度工程，MVP 不需要，引入网络依赖与合规成本 |

## EventBus 解耦

EventBus 是**全局单例 + 带类型信号**，只放"跨层广播"的事件，不放内部调用。

```gdscript
extends Node
# 只放跨层事件：状态变了、货币变了、结算完成
signal currency_changed(new_amount: int)
signal state_saved()
signal offline_reward_ready(amount: int)
signal risk_event_triggered(kind: String, loss: float)
```

**纪律**：

- UI 订阅 EventBus 刷新，**不反向调用** `Simulation` 内部方法改状态。
- 事件名用过去式或状态名（`currency_changed`），不用命令式（`update_currency`）——后者会诱导别人把它当方法调。
- 单一职责：一次事件只带够用的数据，不要把整个 `GameState` 塞进信号参数。
- 新增事件前先问：这是"跨层广播"还是"内部调用"？内部调用就用直接方法调用。

## 模拟与表现分离

```gdscript
# ✅ 模拟层：1Hz Timer 推进
func _ready() -> void:
    var t := Timer.new()
    t.wait_time = 1.0
    t.timeout.connect(_tick)
    add_child(t)
    t.start()

func _tick() -> void:
    _advance_economy()   # 算力产出
    _walk_market()       # 行情游走
    _sample_risk()       # 风险事件抽样
    _emit_changes()      # 只在值真的变了才发信号
```

**纪律**：

- 模拟层**不碰任何 UI 节点**。
- UI 层**不读也不改**经济内部变量，只通过 `GameState` 快照读、通过 `EventBus` 响应。
- 计时用 `Timer`，不要用 `_process` 累加帧时间——切后台、掉帧、低帧率都会让时间膨胀。
- 值没变化就不要发信号。UI 收到无变化信号会做无用刷新，移动端尤其致命。

## 渲染器与性能

Hashrise 面向移动端，选 **GL Compatibility** 渲染器：

```ini
config/features=PackedStringArray("4.2", "GL Compatibility")
```

理由：低端安卓机对 Vulkan 支持参差，GL Compatibility 覆盖面最广。

性能预算参考（`docs/architecture/architecture-review.md`）：

- 目标帧率 60fps，移动端低端机 ≥ 30fps
- 屏内可交互元素 ≤ 6 类（认知负载红线，见 `hashrise-gdd-author`）
- 特效用 GPUParticles，纹理图集打包，避免运行时重复 load

## 常见坑

| 现象 | 根因 | 修法 |
|------|------|------|
| UI 里数值跳得比模拟快 | UI 在 `_process` 里自己算 | 删掉，改为订阅 EventBus |
| 改数值要找十几处代码 | 数值硬编码 | Resource 资源化 + Config 查表 |
| 切后台回来时间对不上 | 用帧时间累加 | 改用 `OS.get_unix_time()` 时间差 |
| 场景一多就卡 | 节点过多 / 每帧创建节点 | 复用节点，池化，关注 `is_queued_for_deletion()` |
| 事件越加越乱 | 把 EventBus 当万能方法表 | 内部调用直接方法调用，EventBus 只放跨层广播 |

## 参考

- `references/三层架构清单.md` —— 落地时的逐项检查清单
- `references/架构决策记录.md` —— ADR-001/002/003 的决策与后果
