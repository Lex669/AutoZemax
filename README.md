# AutoZemax — Zemax OpticStudio 自动化插件 (v0.2.0)

通过 Claude Code 中的自然语言，自动化完整的 Zemax 光学设计工作流——从建模到仿真再到数据处理。

## 概述

AutoZemax 将 Zemax OpticStudio 的 ZOS-API 与 Claude Code 集成，使光学工程师能够通过对话式命令创建、仿真、优化和分析镜头系统。每个功能都被封装为一个技能（skill），Claude 会自动加载。

v0.2.0 是一次完整的重构，围绕 26 个官方 ZOS-API 示例模式进行组织，并采用基于库的架构以最大程度减少样板代码。

## 安装

```bash
# Claude Code 插件市场安装
/plugin marketplace add Lex669/AutoSim
/plugin install AutoZemax@AutoSim
```





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

### 技能（11 个功能模块）

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

### 代理（3 个自主助手）

| 代理 | 触发条件 | 角色 |
|-------|---------|------|
| `model-validator` | 建模变更后 | 验证系统设置，查找错误 |
| `result-analyzer` | 仿真完成后 | 解读结果，提出改进建议 |
| `script-debugger` | Python 脚本失败时 | 诊断并修复 ZOS-API 错误 |

### 核心库（`scripts/zos_utils.py` — 1650+ 行）

该库提供 ZOS-API 的高级封装，消除样板代码：
- **连接** — 上下文管理器，自动清理
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

## 文件结构

```
AutoZemax/
├── .claude-plugin/
│   └── plugin.json              # 插件清单
├── commands/                     # 4 个斜杠命令
│   ├── model.md                 # 阶段 1：创建/编辑系统
│   ├── simulate.md              # 阶段 2：运行分析和优化
│   ├── analyze.md               # 阶段 3：绘制结果并导出
│   └── pipeline.md             # 完整端到端编排器
├── skills/                       # 11 个功能技能
│   ├── system-setup/SKILL.md
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
│   └── zos_utils.py             # 核心库（1650+ 行）
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
- 环境验证命令

## API 参考

请参阅 `references/zos-api-reference.md`，了解以下内容：
- 关键 ZOSAPI 类和方法
- 常用枚举值
- 库封装函数参考
- 数据提取模式

## 许可证

MIT
