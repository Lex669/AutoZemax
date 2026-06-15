---
name: autozemax:simulate
description: Zemax optical simulation — ray tracing, analysis, optimization, and tolerance
argument-hint: "[task description]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion", "Skill"]
---

# /autozemax:simulate — Optical Simulation

Guide the user through running Zemax simulations: ray tracing, optical analysis,
optimization, and tolerance analysis.

## When Invoked

When the user runs `/autozemax:simulate`, first ask what they want to do
using AskUserQuestion. Present these categories:

1. **Ray trace** — Run sequential batch or NSC ray trace
2. **MTF / PSF analysis** — Modulation transfer function, point spread function
3. **Spot diagram** — RMS and GEO spot sizes, spot plots
4. **Wavefront / ray fan** — Wavefront error, ray fan analysis
5. **Optimize system** — Merit function setup and optimization (local/global)
6. **Tolerance analysis** — Sensitivity and Monte Carlo tolerance runs

After the user chooses, load the appropriate skill:

| User Intent | Skill to Load |
|------------|---------------|
| Ray trace (sequential or NSC) | `ray-tracing` |
| MTF, PSF, spot, wavefront, ray fan | `analysis` |
| Optimization, merit function | `optimization` |
| Tolerance, sensitivity, Monte Carlo | `tolerance-analysis` |

## Workflow

1. Ask the user what simulation they need using AskUserQuestion
2. Load the corresponding skill via the Skill tool
3. Follow the skill's workflow to generate and execute the Python script
4. Use the Python interpreter documented in `references/environment.md`
5. Scripts import from `${CLAUDE_PLUGIN_ROOT}/scripts/zos_utils.py`
6. Present results — numerical data, plots, or both

## Prerequisites Check

Before running simulations, verify:
- An optical system is loaded (use `/autozemax:model` first if needed)
- The system has appropriate surfaces/objects for the analysis type
- Material catalogs are loaded if using glass materials

## Python Script Template

```python
import sys, os
# Use CLAUDE_PLUGIN_ROOT set by Claude Code at runtime
_plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
if _plugin_root:
    sys.path.insert(0, os.path.join(_plugin_root, 'scripts'))
from zos_utils import ZOSConnection
# ... skill-specific code ...

# IMPORTANT: Close ZOS connection before plt.show()
with ZOSConnection() as zos:
    # ... run simulation, extract data ...
    x_data = ...
    y_data = ...

# Now plot
import matplotlib.pyplot as plt
plt.plot(x_data, y_data)
plt.show()
```

## Notes

- Always close ZOS connection before calling `plt.show()`
- Ray traces can take significant time for large systems
- Optimization may need multiple runs with adjusted weights
- Reference `zos-api-reference.md` for analysis API details
