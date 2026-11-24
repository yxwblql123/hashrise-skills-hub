---
name: hashrise-godot-ci-build
description: 为 Godot 4.x 项目搭建可靠的持续集成与每日构建流水线，含无头导出、产物判定、缓存策略、签名密钥探测、artifact 上传与 tag 发版。当用户要写 Godot 的 GitHub Actions、排查 CI 导出失败、配置 Android/iOS 签名、或要"每次提交自动出一个可玩包"时使用。
---

# Godot CI 与每日构建

Hashrise 的 `daily-build.yml` 是一份能在真实项目里长期跑住的工作流。这份技能提炼其中**真正踩过坑**的部分，不是通用教程。

## 目标形态

| 触发 | 产出 |
|------|------|
| 每日定时（UTC 19:00 / 北京 03:00） | Linux + Windows 桌面包 |
| push 到 main/master | 同上 |
| 手动 `workflow_dispatch` | 同上，带备注 |
| 打 `v*` tag | 汇总桌面包 + 建 Draft Release |
| 配置了 Android 密钥 | Android AAB + universal APK |
| 配置了 iOS 密钥 | iOS 包 |

**日常无密钥时自动跳过，不报错**——这是关键：CI 不能因为"日常没人配密钥"而红。

## 骨架

```yaml
name: Hashrise Daily Build

on:
  schedule:
    - cron: "0 19 * * *"
  push:
    branches: [main, master]
  workflow_dispatch:
    inputs:
      note: { description: "Manual trigger note (optional)", required: false, default: "" }

concurrency:
  group: hashrise-daily-build
  cancel-in-progress: false

env:
  GODOT_VERSION: "4.2.2"
  GODOT_BUILD: "4.2.2-stable"
  GODOT_TEMPLATES: "4.2.2.stable"
  PROJECT_PATH: "."
```

`concurrency` 必须写：并发构建会互相覆盖 artifact 和缓存目录，`cancel-in-progress: false` 保证手动触发不会被定时任务打断。

## 坑 1 · secrets 上下文不能出现在 if 条件里

**这是最常见的 CI 失败原因。** GitHub Actions 的校验器禁止在 `if:` 里直接引用 `secrets.*`：

```yaml
# ❌ 被校验器拒绝
- name: Export Android
  if: ${{ secrets.ANDROID_KEYSTORE_BASE64 != '' }}
```

**解法**：用一个 `config` job 在 `run` 步骤里读 secrets，把结果写成 job output，下游只判 output。

```yaml
jobs:
  config:
    name: "Config - detect secrets"
    runs-on: ubuntu-latest
    outputs:
      android: ${{ steps.detect.outputs.android }}
      ios: ${{ steps.detect.outputs.ios }}
    steps:
      - id: detect
        run: |
          if [ -n "${{ secrets.ANDROID_KEYSTORE_BASE64 }}" ]; then
            echo "android=true" >> "$GITHUB_OUTPUT"
          else
            echo "android=false" >> "$GITHUB_OUTPUT"
          fi
          # iOS 同理
```

```yaml
  android:
    needs: config
    if: needs.config.outputs.android == 'true'   # ✅ 合规上下文
```

## 坑 2 · Godot headless 导出成功也会返回非零退出码

**这是 Godot CI 的头号误报源。** Godot 遇到 warning 就可能返回非零，很多 runner 会因此把成功构建判成失败。

**解法：不依赖退出码，用"产物非空 + 日志无致命错误串"判定。**

```yaml
- name: Export ${{ matrix.platform }}
  run: |
    mkdir -p "$(dirname "${{ steps.out.outputs.path }}")"
    set +e
    tools/godot --headless --export-release "${{ matrix.platform }}" \
      "${{ steps.out.outputs.path }}" 2>&1 | tee "build/log-${{ matrix.platform }}.txt"
    set -e
    if [ ! -s "${{ steps.out.outputs.path }}" ] \
       || grep -qiE "SCRIPT ERROR|Cannot export|Failed to load script" "build/log-${{ matrix.platform }}.txt"; then
      echo "::error::Export failed for ${{ matrix.platform }} — see log"
      tail -n 40 "build/log-${{ matrix.platform }}.txt"
      exit 1
    fi
```

注意这里 `set +e` / `set -e` 的配合：**故意让 Godot 的退出码不中断脚本**，然后自己判定。判定条件有两项，缺一不可：

- 产物文件存在且非空（`-s`）
- 日志里没有 `SCRIPT ERROR` / `Cannot export` / `Failed to load script`

## 坑 3 · 缓存 Godot 二进制与导出模板

缓存键要绑定**版本号**，否则升级 Godot 后拿到旧缓存会出诡异错误：

```yaml
- name: Cache Godot + templates
  id: cache
  uses: actions/cache@v4
  with:
    path: |
      tools/godot
      ~/.local/share/godot/export_templates/${{ env.GODOT_TEMPLATES }}
    key: godot-${{ env.GODOT_BUILD }}-v1
```

缓存命中时必须**恢复执行权限**（缓存不保留 exec bit）：

```yaml
- name: Restore Godot exec perms (cache hit)
  if: steps.cache.outputs.cache-hit == 'true'
  run: chmod +x tools/godot
```

## 坑 4 · 运行时依赖

Godot Linux 无头运行需要一堆系统库，少一个就起不来：

```yaml
- name: Install Godot runtime deps
  run: |
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends \
      libx11-6 libxcursor1 libxinerama1 libxi6 libgl1 libglu1-mesa \
      libasound2t64 libpulse0 libudev1 libxrandr2 libfontconfig1 \
      unzip wget ca-certificates
```

## 坑 5 · artifact 上传要带日志

```yaml
- name: Upload artifact
  if: always()          # 失败也要传日志，否则没法排查
  uses: actions/upload-artifact@v4
  with:
    name: ${{ steps.out.outputs.name }}
    path: |
      ${{ steps.out.outputs.path }}
      build/log-${{ matrix.platform }}.txt
    if-no-files-found: warn
    retention-days: 14
```

`if: always()` + 一起传日志，是排查失败的关键。

## 坑 6 · Android 签名注入

密钥以 base64 存进 secrets，CI 里还原后注入导出预设：

```yaml
- name: Restore keystore & inject into preset
  run: |
    echo "${{ secrets.ANDROID_KEYSTORE_BASE64 }}" | base64 -d > android/keystore.keystore
    # 按预设里引用的凭据名注入 keystore 密码 / 别名 / 密码
```

Android 自定义构建（如集成 AdMob）需要 Android SDK + Gradle，且 **keystore 注入方式要与 Godot 版本对齐**。首次正式发版前务必在本地跑通同一个 job——CI 上第一次调 Android 构建几乎必踩坑。

## 推荐 job 划分

```
config        → 探测密钥，写 output
├─ desktop    → matrix: Linux/X11 + Windows Desktop
├─ android    → needs: config，条件在 android
└─ ios        → needs: config，条件在 ios
release       → tag 触发，汇总 desktop 产物建 Draft Release
```

`fail-fast: false` 用在 desktop 的 matrix 上：Windows 挂了不影响 Linux 产出，反之亦然。

## 配套：无头验证脚本

CI 导出之前，先跑一遍无头逻辑自检（见 `hashrise-godot-test-probe`）：

```yaml
- name: Headless logic check
  run: |
    set +e
    tools/godot --headless -s res://tests/logic_check.gd 2>&1 | tee "build/logic.txt"
    set -e
    grep -q "FAIL" "build/logic.txt" && { echo "::error::Logic check failed"; exit 1; } || true
```

注意：探针脚本把结果**直写文件**而非 stdout，因为在 headless 重定向下 `print` 的尾部会被吞掉。

## 常见坑速查

| 现象 | 根因 | 修法 |
|------|------|------|
| CI 报 YAML 校验错误，提示 secrets | `if:` 里引用了 `secrets.*` | 走 `config` job 的 output |
| 构建成功但 job 失败 | Godot headless 成功也返回非零 | `set +e` + 产物与日志双判定 |
| 缓存命中后报权限错 | 缓存不保留 exec bit | 命中时 `chmod +x` |
| 升级 Godot 后行为诡异 | 缓存了旧版二进制 | 缓存键带版本号 |
| runner 找不到 Godot 依赖库 | 缺系统库 | 显式 `apt-get install` |
| 失败时没有任何线索 | 没传日志 | artifact 带 log，`if: always()` |
| Android job 第一次必挂 | keystore 注入与 Gradle 配置未本地验证 | 本地先跑通同一流程 |
