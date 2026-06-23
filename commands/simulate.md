---
name: autozemax:simulate
description: Run analyses, ray traces, optimization, tolerancing — Phase 2 of pipeline
argument-hint: "[task description]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion", "Skill", "Agent"]
---

# /autozemax:simulate — Optical Simulation (Phase 2)

Guide the user through running Zemax simulations: ray tracing, optical analysis,
optimization, tolerance analysis, NSC analysis, multi-configuration operations,
and scattering simulations. This is Phase 2 of the AutoZemax pipeline.

## When Invoked

When the user runs `/autozemax:simulate`, first ask what they want to do
using AskUserQuestion. Present these categories:

1. **Ray trace** — Run sequential batch or NSC ray trace
2. **MTF / PSF / spot / wavefront / ray fan** — Standard sequential analysis
3. **Optimize system** — Merit function setup, DLS or Hammer optimization
4. **Tolerance analysis** — Sensitivity and Monte Carlo tolerance runs
5. **NSC analysis** — NSC detector data extraction, phase analysis, ZRD filters
6. **NSC scattering** — Bulk scatter modeling, phosphor simulations
7. **Multi-configuration** — Zoom lens or multi-configuration system operations

After the user chooses, load the appropriate skill:

| User Intent | Skill to Load |
|------------|---------------|
| MTF, PSF, spot, wavefront, ray fan, ZRD | `sequential-analysis` |
| Optimization, merit function, DLS, Hammer | `optimization` |
| Tolerance analysis, sensitivity, Monte Carlo | `tolerance-analysis` |
| NSC detector data, phase maps, ZRD filters | `nsc-analysis` |
| Bulk scatter, phosphor modeling | `nsc-scattering` |
| Zoom lenses, multi-configuration editor | `multi-configuration` |

## Prerequisites Check

Before running simulations, verify:
- An optical system is loaded (use `/autozemax:model` first if needed)
- The system has appropriate surfaces/objects for the analysis type
- Material catalogs are loaded if using glass materials
- For multi-configuration: MCE is set up with valid configurations
- For NSC analysis: detectors are configured and sources are valid

## Workflow

1. Ask the user what simulation they need using AskUserQuestion
2. Load the corresponding skill via the Skill tool
3. Follow the skill's workflow to generate and execute the Python script
4. Use the Python interpreter with the compact import template below
5. Present results — numerical data, plots, or both
6. **After completion**, run the `result-analyzer` agent to interpret results

## Python Script Template

Every generated script must use the compact import with `set_seed(42)`:

```python
import sys, os
_PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
for _p in [
    os.path.join(_PLUGIN_ROOT, 'scripts') if _PLUGIN_ROOT else '',
    r'C:\Users\Lex\.claude\plugins\cache\AutoSim\AutoZemax\0.2.0\scripts',
    r'C:\Users\Lex\Desktop\AutoSim\AutoZemax\scripts',
]:
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p); break
from zos_utils import ZOSConnection, set_seed
set_seed(42)

with ZOSConnection() as zos:
    # ... skill-specific simulation code ...
    # Extract data before closing connection

# Plot outside the ZOSConnection context
import matplotlib.pyplot as plt
plt.plot(x_data, y_data)
plt.show()
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## Result Analysis

After simulation completes, run the `result-analyzer` agent:

```
Agent: result-analyzer
Prompt: "Analyze the simulation results from <script>.py output.
  - Report key performance metrics
  - Identify any performance issues
  - Suggest design improvements
  - Recommend next steps"
```

## Notes

- Always close ZOS connection (`with ZOSConnection()`) before calling `plt.show()`
- Ray traces can take significant time for large systems
- Optimization may need multiple runs with adjusted weights
- For Hammer optimization, check that `Cancel()` has proper guard conditions
- Reference `zos-api-reference.md` for analysis API details
- On failure, use the `script-debugger` agent to diagnose
