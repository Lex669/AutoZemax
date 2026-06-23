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
- "Load the Double Gauss, run tolerance analysis with 100 Monte Carlo trials, and export a performance report"
- "Create an F/5 100mm focal length singlet with a multi-config zoom, trace rays, and show the spot diagram"
- "Model an NSC system with a bulk scatter volume, analyze the detector data, and export CAD"

## Pipeline Phases

Every pipeline follows three phases:

### Phase 1: Modeling
Load or create the optical system. Use:
- `Skill: system-setup` — for creating/loading, aperture, fields, wavelengths
- `Skill: sequential-modeling` — for LDE surfaces, solves, materials, tilts
- `Skill: nsc-modeling` — for NSC sources, detectors, objects

**After Phase 1**: Run `model-validator` agent to verify system configuration.

### Phase 2: Simulation
Run the requested simulations. Use:
- `Skill: sequential-analysis` — for MTF, PSF, spot, wavefront, ray fan, ZRD
- `Skill: optimization` — for DLS and Hammer optimization, merit function
- `Skill: tolerance-analysis` — for sensitivity and Monte Carlo analysis
- `Skill: nsc-analysis` — for NSC detector data, phase maps, ZRD filters
- `Skill: nsc-scattering` — for bulk scatter and phosphor modeling
- `Skill: multi-configuration` — for zoom lenses and MCE operations

**After Phase 2**: Run `result-analyzer` agent to interpret simulation results.

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

All pipeline scripts must use the compact import with `set_seed(42)`:

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
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## Pipeline Coordination

- Each phase's output (e.g., saved .zmx file) becomes the next phase's input
- Save intermediate results to `zmx/pipeline_output/` (auto-created via `ensure_zmx_dir()`)
- Track progress and report to the user after each phase
- If a pipeline phase fails, preserve results from earlier phases
- The pipeline can be run partially (e.g., only modeling + simulation)

## Validation Between Phases

- **After Phase 1 (Modeling)**: Run `model-validator` agent to check system configuration
- **After Phase 2 (Simulation)**: Run `result-analyzer` agent to interpret results
- **Inside every script**: Call `zos.validate_system_ready()` after system setup
- **Before optimization**: Verify variables are set and merit function has operands
- **Before ray trace**: Verify aperture, fields, and wavelengths are configured
- **Before NSC analysis**: Verify detectors and sources are configured

## Error Handling

- If Zemax is not running, suggest starting OpticStudio
- If license check fails, report the license status
- If file not found, suggest alternative paths or creating a new system
- If Python fails, use the `script-debugger` agent to diagnose
- **Common template bugs to watch for**: Hammer `Cancel()` unconditional, missing `set_seed()`, `TiltX` vs `TiltAboutX`, `from System import ...` instead of `zos.Int32/Double/Enum`

## Notes

- The full pipeline may take several minutes for complex systems
- Save work at each phase boundary
- Users can abort between phases without losing all progress
- For production use, save the generated script for repeatability
- Reference `zos-api-reference.md` for ZOS-API details
