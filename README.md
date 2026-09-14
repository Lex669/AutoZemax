# AutoZemax — Zemax OpticStudio 自动化插件 (v0.3.0)

在 Claude Code / Codex 中用自然语言自动化完整的 Zemax 光学设计工作流——从建模到仿真再到数据处理。

## 概述

AutoZemax 将 Zemax OpticStudio 的 ZOS-API 与 Claude Code 集成，使光学工程师能够通过对话式命令创建、仿真、优化和分析镜头系统。每个功能都被封装为一个技能（skill），Claude 会自动加载。

v0.2.x 版本围绕 26 个官方 ZOS-API 示例模式进行组织，并采用基于库的架构以最大程度减少样板代码。

同时适配 **Claude Code 与 Codex CLI 双插件生态**（`.claude-plugin/plugin.json` + `.codex-plugin/plugin.json`）。

v0.3.0 起支持 **双连接模式**：`standalone`（默认，隐藏实例、最快、可并行）与 `interactive`（接管用户已打开的 OpticStudio GUI，实时可见、复用当前设计）。插件可自动拉起 OpticStudio，并借助 computer use 自动打开 Interactive Extension 建立连接，失败时自动回退 standalone。

## 安装

### Claude Code

```bash
# Claude Code 插件市场安装
/plugin marketplace add Lex669/AutoSim
/plugin install AutoZemax@AutoSim
```

### Codex CLI（v0.121+）

```bash
# 注册 AutoSim 插件市场
codex plugin marketplace add Lex669/AutoSim
# 安装插件（autosim 为清单注册名，可用 codex plugin marketplace list 查看）
codex plugin add AutoZemax@autosim
```

> [!NOTE]
> Codex 端会注册 `skills/` 下的 12 个技能，并在安装时把 `commands/` 下的 4 个斜杠命令迁移为 skills（`source-command-*`）。注意：单个命令迁移后若超过 4 KB 会被 Codex 静默跳过，因此命令文件需保持精简。


## 架构

```
用户 → 斜杠命令 → 技能 → zos_utils.py (库) → ZOS-API → 结果
                              ↑
                         代理 (验证、分析、调试)
```

### 命令（4 个面向用户的入口点）

| 命令 | 用途 |
|---------|---------|
| `/autozemax:model` | 创建/编辑光学系统（序列和非序列模式） |
| `/autozemax:simulate` | 运行光线追迹、分析、优化、公差分析 |
| `/autozemax:analyze` | 可视化结果、生成报告、导出 CAD |
| `/autozemax:pipeline` | 完整端到端工作流：建模 → 仿真 → 分析 |

### 技能（12 个功能模块）

| 技能 | 领域 | 覆盖的 ZOS-API 示例 |
|-------|--------|------------------------|
| `system-setup` | 创建/加载系统、孔径、视场、波长 | 01, 12, 26 |
| `sequential-modeling` | LDE 表面、材料、求解、倾斜、镀膜 | 01, 11, 19, 07 |
| `sequential-analysis` | MTF、PSF、点列图、波前、光线像差曲线、ZRD | 04, 05, 22, 23 |
| `optimization` | DLS 和 Hammer 优化、评价函数操作数 | 03, 15 |
| `multi-configuration` | 变焦镜头、多重结构系统、MCE | 18 |
| `tolerance-analysis` | 灵敏度和蒙特卡洛公差分析 | 14 |
| `nsc-modeling` | 非序列物体、光源、探测器 | 02, 24 |
| `nsc-analysis` | 非序列探测器数据、相位、ZRD 滤波器 | 06, 08, 10 |
| `nsc-scattering` | 体散射、荧光粉、体积物理 | 17, 21 |
| `cad-exchange` | CAD 导入/导出（STEP、IGES、SAT、STL） | 09, 20 |
| `data-processing` | matplotlib 可视化、图表生成、报告 | （全部） |
| `interactive-session` | 连接模式选择、Interactive Extension 建连、回退策略 | （全部） |

### 连接模式（v0.3.0）

| | `standalone`（默认） | `interactive` |
|---|---|---|
| 连接方式 | API 拉起隐藏实例 `CreateNewApplication()` | 接管已打开 GUI 的 `ConnectAsExtension(实例号)` |
| 速度 / 并行 | 快，可多实例 | 慢（界面同步），单实例单连接 |
| 前置条件 | 无 | 需在 GUI 点一次 Programming → Interactive Extension |
| 适用场景 | 批量优化、公差蒙特卡洛、批量分析、无人值守 pipeline | 建模调参实时看效果、复用用户当前设计、调试、演示 |
| 结束行为 | 关闭该隐藏实例 | 仅断开，用户的 OpticStudio 保持打开 |

```python
with ZOSConnection() as zos:                      # standalone（默认，行为不变）
with ZOSConnection(mode="interactive") as zos:    # 实时驱动 GUI
    zos.save_interactive_copy()                   # 先另存副本，原文件不动
with ZOSConnection(mode="auto") as zos:           # 有等待中的会话就复用，否则 standalone
```

模式可通过 `mode=` 参数或 `AUTOZEMAX_MODE` 环境变量指定；`interactive` 建连失败会抛出 `InteractiveNotAvailable`，由代理自动回退到 `standalone` 并在结果中说明。完整的建连与排障流程见 `skills/interactive-session/SKILL.md`。

### 代理（3 个自主助手）

| 代理 | 触发条件 | 角色 |
|-------|---------|------|
| `model-validator` | 建模变更后 | 验证系统设置，查找错误 |
| `result-analyzer` | 仿真完成后 | 解读结果，提出改进建议 |
| `script-debugger` | Python 脚本失败时 | 诊断并修复 ZOS-API 错误 |

### 会话助手（`scripts/zemax_session.py`）

```
status            查看 OpticStudio 进程与窗口（外部实例 / 已开 GUI），不连接
wait --timeout 90 等待 GUI 窗口出现
launch --wait     启动 OpticStudio（可等待窗口就绪）
```

只做观测与启动：不发起 API 连接（连接会消耗掉 "Waiting for connection..." 会话），也不终止任何进程。

### 核心库（`scripts/zos_utils.py` — 2000+ 行）

该库提供 ZOS-API 的高级封装，消除样板代码：
- **双模式连接** — `ZOSConnection(mode="standalone" | "interactive" | "auto")`、`mode`/`is_interactive`/`instance`、`save_interactive_copy()`、`set_ui_updates()`、`InteractiveNotAvailable`；上下文管理器自动清理，interactive 下只断开、不关闭用户的 OpticStudio
- **分析数据提取器** — `extract_mtf_data()`、`extract_spot_data()`、`extract_wavefront_data()`、`extract_psf_data()`、`extract_ray_fan_data()`
- **非序列辅助函数** — `create_nsc_detector()`、`create_nsc_source()`、`get_detector_data()`、`get_coherent_data()`
- **优化运行器** — `run_dls_optimization()`、`run_hammer_optimization()`
- **公差分析** — `run_tolerance_sensitivity()`、`run_tolerance_monte_carlo()`
- **多重结构** — `add_configuration()`、`set_config_operand()`
- **CAD** — `export_cad()`、`import_cad()`
- **图表生成器** — `plot_mtf()`、`plot_spot_diagram()`、`plot_wavefront_map()`、`plot_ray_fan()`、`plot_detector_data()`、`plot_tolerance_cdf()`
- **脚本模板** — `generate_script()` 用于可重复的工作流

## 先决条件

- **Zemax OpticStudio 2025 R2 (v252)**
- **专业版或高级版许可证**（标准版的 API 支持有限）
- **Python 3.14 64-bit**，路径：`C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe`
- Python 包：`pythonnet`、`numpy`、`matplotlib`

## 快速开始

### 创建并分析一个简单镜头

```
/autozemax:pipeline "创建一个 F/5、焦距 100mm 的 N-BK7 单透镜，
对 0° 和 7° 视场以最小弥散斑为目标进行优化，然后绘制 MTF 曲线"
```

### 分步工作流

```
/autozemax:model     → 创建系统，添加表面
/autozemax:simulate  → 优化，运行 MTF 分析
/autozemax:analyze   → 绘制结果，导出报告
```

### 用 interactive 模式「看着跑」

直接对插件说话即可，插件会自己拉起 OpticStudio、用 computer use 点开 Interactive Extension、连上后在 GUI 里实时显示每一步改动：

```
用 interactive 模式在当前打开的模型上跑，我要看着它优化
```

脚本层等价于：

```python
with ZOSConnection(mode="interactive") as zos:
    zos.save_interactive_copy()   # 先另存 zmx/<名称>_interactive.zos，原文件不动
    # ... 建模 / 优化 / 分析，GUI 实时可见 ...
```

批量化任务（优化、公差蒙特卡洛、批量分析）不需要指定，默认就是更快的 `standalone`。

## 文件结构

```
AutoZemax/
├── .claude-plugin/
│   └── plugin.json              # Claude Code 插件清单
├── .codex-plugin/
│   └── plugin.json              # Codex 插件清单
├── commands/                     # 4 个斜杠命令（Claude Code 使用，Codex 安装时迁移为 skills）
│   ├── model.md                 # 阶段 1：创建/编辑系统
│   ├── simulate.md              # 阶段 2：运行分析和优化
│   ├── analyze.md               # 阶段 3：绘制结果并导出
│   └── pipeline.md             # 完整端到端编排器
├── skills/                       # 12 个功能技能
│   ├── system-setup/SKILL.md
│   ├── interactive-session/SKILL.md
│   ├── sequential-modeling/SKILL.md
│   ├── sequential-analysis/SKILL.md
│   ├── optimization/SKILL.md
│   ├── multi-configuration/SKILL.md
│   ├── tolerance-analysis/SKILL.md
│   ├── nsc-modeling/SKILL.md
│   ├── nsc-analysis/SKILL.md
│   ├── nsc-scattering/SKILL.md
│   ├── cad-exchange/SKILL.md
│   └── data-processing/SKILL.md
├── agents/                       # 3 个自主代理
│   ├── model-validator.md
│   ├── result-analyzer.md
│   └── script-debugger.md
├── scripts/
│   ├── zos_utils.py             # 核心库（双模式连接、分析、优化、图表）
│   └── zemax_session.py         # 会话助手：进程/窗口状态、启动、等待（不连接、不杀进程）
├── references/
│   ├── zos-api-reference.md     # ZOS-API 类/方法快速参考
│   └── environment.md           # Python/Zemax 环境配置
├── ZOS-API Samples/              # 26 个官方 Zemax 示例（参考）
├── PythonStandaloneApplication/ # ZOS-API 框架样板代码
├── README.md
└── .gitignore
```

## 支持的 ZOS-API 示例覆盖

覆盖全部 26 个官方 ZOS-API Python 示例：

| 示例 | 技能 |
|---------|-------|
| 01, 12, 26 | system-setup |
| 01, 11, 19, 07 | sequential-modeling |
| 04, 05, 22, 23 | sequential-analysis |
| 03, 15 | optimization |
| 18 | multi-configuration |
| 14 | tolerance-analysis |
| 02, 24 | nsc-modeling |
| 06, 08, 10 | nsc-analysis |
| 17, 21 | nsc-scattering |
| 09, 20 | cad-exchange |

## 环境配置

请参阅 `references/environment.md`，了解以下内容：
- Python 解释器路径和所需软件包
- Zemax 安装和 ZOS-API 程序集位置
- 标准导入代码块和基于库的开发方式
- standalone / interactive 双连接模式与 `zemax_session.py` 会话助手用法
- 环境验证命令

## API 参考

请参阅 `references/zos-api-reference.md`，了解以下内容：
- 关键 ZOSAPI 类和方法
- 连接 API 规则（`CreateNewApplication` / `ConnectAsExtension` / `ConnectToApplication` 的适用边界）
- 常用枚举值
- 库封装函数参考
- 数据提取模式

## 常见问题（interactive 模式）

| 现象 | 原因与处理 |
|------|-----------|
| 提示 `InteractiveNotAvailable` | OpticStudio 没开，或扩展没点开。插件会自动回退 standalone 并在结果中说明；要真正用 interactive，请在 OpticStudio 里点 Programming → Interactive Extension |
| 连接报 `This application was not launched by Optic Studio` | 用了 `ConnectToApplication()`。外部脚本必须走 `ConnectAsExtension(实例号)`，即 `ZOSConnection(mode="interactive")` |
| 第一次跑完，第二次连不上 | Interactive Extension 在客户端断开时会自动关闭，需要在 GUI 里再点一次（插件会自动处理） |
| 运行很慢 | interactive 会把每处改动实时同步到界面。批量改动可先 `zos.set_ui_updates(False)`，最后再打开 |
| 担心模型被改 | interactive 下先调 `zos.save_interactive_copy()`，改动落在 `zmx/` 副本上，原文件 SHA 不变（已实测） |
| 关闭 OpticStudio 时提示保存 | 连接会让文档带上"已修改"标记。这是 OpticStudio 自身的模态框，插件不代答，请自行确认 |

## 更新日志

### v0.3.0 · 2026-09-14 — 双连接模式（standalone + interactive）

- `scripts/zos_utils.py` 支持 `ZOSConnection(mode="standalone" | "interactive" | "auto")`：
  - `interactive` 通过 `ConnectAsExtension(实例号)` 接管已打开的 OpticStudio GUI（自动探测实例号 1–8），`auto` 有等待中的会话就复用，否则回退 standalone。
  - 模式解析顺序：显式 `mode=` → `AUTOZEMAX_MODE` 环境变量 → `standalone`（默认行为与 v0.2.x 完全一致）。
  - 新增 `zos.mode` / `zos.is_interactive` / `zos.instance` / `InteractiveNotAvailable`；`close()` 在 interactive 下只断开，绝不关闭用户的 OpticStudio。
  - `zos.save_interactive_copy()` 先把当前系统另存为 `zmx/<名称>_interactive.zos` 再改，原文件不被覆盖；`zos.set_ui_updates()` 控制是否实时刷新界面。
- 新增 `scripts/zemax_session.py`：`status` / `wait` / `launch` 三个子命令，只做进程与窗口观测和启动，不发起连接（避免消耗等待中的扩展会话），也不终止任何进程。
- 新增技能 `interactive-session`：模式选择表、Interactive Extension 建连流程（含 computer use 操作要点）、工作副本策略、失败模式与自动回退规则。
- 其余 11 个技能、4 个斜杠命令的版本号与插件缓存脚本路径同步到 0.3.0；命令新增「连接模式」小节，仍全部低于 Codex 的 4 KB 迁移限制。
- `script-debugger` 代理新增 interactive 相关错误特征；`references/zos-api-reference.md` 更正连接 API 说明（`ConnectToApplication()` 仅适用于 OpticStudio 自身拉起的插件）。
- 修复 `extract_spot_data()` 的既有缺陷：2025 R2 未暴露 `GetAiryRadiusFor()`，原先直接抛 `AttributeError`，现改为兼容探测。
- 实测验证：同一模型（N-BK7 单透镜）在两种模式下跑同一 Standard Spot 分析，RMS/GEO 弥散斑逐位一致；interactive 全程在 `zmx/` 副本上作业，原文件 SHA256 不变。
- 版本号 0.2.1 → 0.3.0。

### v0.2.1 · 2026-09-10 — Codex 命令迁移修复

- 精简 `simulate.md` 与 `pipeline.md`，使 4 个斜杠命令迁移后均低于 Codex 的 4 KB 限制，安装后 `source-command-*` 全部生成。
- 命令文件移除内嵌的 Python 导入模板，统一指向 `references/environment.md`，减少与 skills 的重复。
- 更正 README 说明：Codex 安装时会把 `commands/` 迁移为 skills，不再写“斜杠命令仅 Claude Code 可用”。
- 版本号 0.2.0 → 0.2.1。

### v0.2.0 · 2026-09-07 — Codex CLI 适配

- 新增 `.codex-plugin/plugin.json`，插件同时支持 **Claude Code 与 Codex CLI（v0.121+）** 双生态；Codex 端注册 `skills/` 下的 11 个技能。
- README 增加 Codex CLI 安装指引（`codex plugin marketplace add Lex669/AutoSim` → `codex plugin add AutoZemax@autosim`）。
- 明确两端能力差异：斜杠命令 `/autozemax:*` 与 3 个自主代理仅在 Claude Code 端可用。

### v0.2.0 · 2026-06-23 — 完整重构

- 围绕 26 个官方 ZOS-API 示例重新组织技能体系，技能数量 9 → 11：
  - 新增/拆分：`sequential-analysis`、`nsc-modeling`、`nsc-analysis`、`nsc-scattering`、`multi-configuration`、`cad-exchange`
  - 移除：`analysis`、`ray-tracing`、`cad-export`、`non-sequential-modeling`（能力已并入上述新技能）
- `scripts/zos_utils.py` 由 276 行扩充至 1650+ 行，采用基于库的架构，统一连接管理、分析数据提取、优化/公差运行器、多重结构、CAD 导入导出与图表生成接口。
- 命令层定型为 4 个入口：`process.md` 更名为 `analyze.md`，`model` / `simulate` / `pipeline` 全面改写。
- 3 个代理（`model-validator`、`result-analyzer`、`script-debugger`）全部重写，明确触发条件与职责边界。
- 引入 `ZOS-API Samples/`（26 个官方示例）与 `PythonStandaloneApplication/`（ZOS-API 框架样板）作为参考实现。
- 参考资料调整：移除 `python-examples.md`，重写 `environment.md` 与 `zos-api-reference.md`。
- `.claude-plugin/plugin.json` 补全 `keywords`、`homepage`、`repository` 等元数据。

### v0.1.x · 2026-06-16 — 缺陷修复

- 修复若干 bug：`zos_utils.py` 接口健壮性、非序列建模技能、`script-debugger` 代理与 ZOS-API 参考文档。

### v0.1.0 · 2026-06-15 — 首个版本

- 插件首次成型：`.claude-plugin/plugin.json`、4 个斜杠命令（`model` / `simulate` / `process` / `pipeline`）、9 个技能、3 个自主代理。
- `scripts/zos_utils.py` 初版（276 行）；参考资料 `environment.md`、`zos-api-reference.md`、`python-examples.md`。
- 仓库创建，采用 MIT 许可证。

## 许可证

MIT
