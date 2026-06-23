---
name: autozemax:analyze
description: Extract results, generate plots, export reports and CAD — Phase 3 of pipeline
argument-hint: "[task description]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion", "Skill", "Agent"]
---

# /autozemax:analyze — Data Processing & Export (Phase 3)

Process, visualize, and export Zemax simulation results. Generate plots,
performance reports, and export to CAD or data formats.
This is Phase 3 of the AutoZemax pipeline (formerly `/autozemax:process`).

## When Invoked

When the user runs `/autozemax:analyze`, first ask what they want to do
using AskUserQuestion. Present these categories:

1. **Plot analysis results** — MTF curves, spot diagrams, PSF, detector heatmaps
2. **Generate performance report** — Text/markdown report with key metrics
3. **Export data** — Save results to CSV, NumPy, or other formats
4. **Export CAD** — Export optical geometry to STEP/IGES/SAT/STL
5. **Custom visualization** — Specialized plots, dashboards, publication figures

After the user chooses, load the appropriate skill:

| User Intent | Skill to Load |
|------------|---------------|
| Plots, visualization, reports, data export | `data-processing` |
| CAD export (STEP, IGES, SAT, STL) | `cad-exchange` |

## Workflow

1. Ask the user what processing task they need using AskUserQuestion
2. Load the corresponding skill via the Skill tool
3. Follow the skill's workflow to generate and execute the Python script
4. Use the Python interpreter with the compact import template below
5. Display generated plots, save reports, confirm file locations
6. If any step fails, use the `script-debugger` agent to diagnose

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
from zos_utils import ZOSConnection, set_seed, ensure_zmx_dir
set_seed(42)

with ZOSConnection() as zos:
    # ... load system, extract data for plotting/export ...

# Plot or export outside the ZOSConnection context
import matplotlib.pyplot as plt
plt.figure(dpi=150)
plt.plot(x_data, y_data)
plt.savefig(os.path.join(ensure_zmx_dir(), 'result.png'))
plt.show()
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## Report Template

When generating analysis reports, include:

```
OPTICAL PERFORMANCE REPORT
==========================
- System: [filename]
- Date: [date]
- License: [edition]

SPOT SIZES
----------
Field | RMS (um) | GEO (um)
------|----------|---------
1     | X.XXX    | X.XXX

MTF SUMMARY
-----------
Field | T (low freq) | S (low freq)
------|-------------|-------------
1     | X.XXXX      | X.XXXX

NOTES
-----
- Manufacturing tolerances considered: [yes/no]
- Optimization status: [final/intermediate]
- NSC detector metrics: [if applicable]
```

## Notes

- Always close ZOS connection before calling `plt.show()` or `plt.savefig()`
- Use `plt.savefig()` for non-interactive report workflows
- For publication figures, set `plt.figure(dpi=150)` or higher
- CAD export with appropriate spline segments and tolerance settings
- Save generated scripts to `zmx/scripts/` for repeatability
- Reference `zos-api-reference.md` for CAD export API details
- On failure, use the `script-debugger` agent to diagnose
