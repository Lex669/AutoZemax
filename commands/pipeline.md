---
name: autozemax:pipeline
description: Full end-to-end workflow orchestrator — Model, Simulate, then Analyze
argument-hint: "[pipeline description]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion", "Skill", "Agent"]
---

# /autozemax:pipeline — Full Automation Pipeline

Execute a complete end-to-end Zemax workflow: Model -> Simulate -> Analyze.
The user describes what they want, and Claude orchestrates the full pipeline
across all AutoZemax v0.2.0 skills.

## When Invoked

When the user runs `/autozemax:pipeline`, parse their description to understand
the full workflow they need. The pipeline accepts free-form descriptions like:

- "Design a Cooke triplet, optimize for minimum spot size, then plot the MTF"

## Pipeline Phases

Every pipeline follows three phases:

### Phase 1: Modeling
Load or create the optical system. Use:
- `Skill: system-setup` — for creating/loading, aperture, fields, wavelengths
- `Skill: sequential-modeling` — for LDE surfaces, solves, materials, tilts
- `Skill: nsc-modeling` — for NSC sources, detectors, objects

### Phase 2: Simulation
Run the requested simulations. Use:
- `Skill: sequential-analysis` — for MTF, PSF, spot, wavefront, ray fan, ZRD
- `Skill: optimization` — for DLS and Hammer optimization, merit function
- `Skill: tolerance-analysis` — for sensitivity and Monte Carlo analysis
- `Skill: nsc-analysis` — for NSC detector data, phase maps, ZRD filters
- `Skill: nsc-scattering` — for bulk scatter and phosphor modeling
- `Skill: multi-configuration` — for zoom lenses and MCE operations

### Phase 3: Analysis
Extract, visualize, and export results. Use:
- `Skill: data-processing` — for plots, visualization, reports
- `Skill: cad-exchange` — for CAD import/export (STEP, IGES, SAT, STL)

## Workflow

1. Parse the user's pipeline description to identify which phases are needed
2. Present the planned pipeline steps to the user for confirmation
3. Execute each phase in sequence:
   a. Load the relevant skill via the Skill tool
   b. Follow the skill's workflow to generate the Python script
   c. **Every generated script MUST include**: `set_seed(42)`, compact import, `zos.validate_system_ready()` after system setup
   d. Execute with the Python interpreter
   e. Validate output before proceeding to next phase
4. If any phase fails, diagnose the issue and offer to retry or adjust
5. Present final results: plots, reports, and saved file locations

## Python Execution

统一使用 `references/environment.md` 的标准导入模板（`set_seed(42)` + `ZOSConnection` 上下文管理器）和执行命令；具体脚本结构以对应 skill 为准。

## Pipeline Coordination

- Each phase's output (e.g., saved .zmx file) becomes the next phase's input
- Save intermediate results to `zmx/pipeline_output/` (auto-created via `ensure_zmx_dir()`)
- If a phase fails, preserve results from earlier phases; the pipeline can run partially

## Validation and Errors

- 阶段后运行对应 agent：Phase 1 → `model-validator`，Phase 2 → `result-analyzer`；脚本失败 → `script-debugger`
- 每个脚本先 `set_seed(42)`，系统就绪后调用 `zos.validate_system_ready()`
- 常见坑：Hammer `Cancel()` 需有保护条件、`TiltX` 应为 `TiltAboutX`、类型/枚举用 `zos.Int32/Double/Enum`

## Notes

- 复杂系统全流程可能耗时数分钟，每个阶段之间保存进度
- 支持部分流程执行；生产环境建议保存生成脚本以便复现
- API 细节见 `references/zos-api-reference.md`
