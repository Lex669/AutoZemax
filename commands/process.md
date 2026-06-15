---
name: autozemax:process
description: Zemax data processing — visualize results, export data, generate reports
argument-hint: "[task description]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion", "Skill"]
---

# /autozemax:process — Data Processing & Export

Process, visualize, and export Zemax simulation results. Generate plots,
performance reports, and export to CAD or CSV formats.

## When Invoked

When the user runs `/autozemax:process`, first ask what they want to do
using AskUserQuestion. Present these categories:

1. **Plot analysis results** — MTF curves, spot diagrams, PSF, detector heatmaps
2. **Generate performance report** — Text/markdown report with key metrics
3. **Export data** — Save results to CSV, NumPy, or other formats
4. **Export CAD** — Export optical geometry to STEP/IGES/SAT/STL
5. **Custom visualization** — Specialized plots and dashboards

After the user chooses, load the appropriate skill:

| User Intent | Skill to Load |
|------------|---------------|
| Plots, visualization, reports, data export | `data-processing` |
| CAD export (STEP, IGES, etc.) | `cad-export` |

## Workflow

1. Ask the user what processing task they need using AskUserQuestion
2. Load the corresponding skill via the Skill tool
3. Follow the skill's workflow to generate Python script
4. Use the Python interpreter documented in `references/environment.md`
5. Scripts import from `${CLAUDE_PLUGIN_ROOT}/scripts/zos_utils.py`
6. Display generated plots, save reports, confirm file locations

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
Field | RMS (µm) | GEO (µm)
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
```

## Notes

- Always close ZOS connection before calling `plt.show()`
- Use `plt.savefig()` for non-interactive report workflows
- For publication figures, set `plt.figure(dpi=150)` or higher
- Export CAD with appropriate spline segments and tolerance settings
