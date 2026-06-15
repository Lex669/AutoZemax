---
name: autozemax:pipeline
description: Full Zemax automation pipeline — modeling → simulation → data processing in one workflow
argument-hint: "[pipeline description]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion", "Skill"]
---

# /autozemax:pipeline — Full Automation Pipeline

Execute a complete end-to-end Zemax workflow: model → simulate → process.
The user describes what they want, and Claude orchestrates the full pipeline
across all AutoZemax skills.

## When Invoked

When the user runs `/autozemax:pipeline`, parse their description to understand
the full workflow they need. The pipeline accepts free-form descriptions like:

- "Design a Cooke triplet, optimize for minimum spot size, then plot the MTF"
- "Load the Double Gauss, run tolerance analysis with 100 Monte Carlo trials, and export a performance report"
- "Create an F/5 100mm focal length singlet, trace rays, and show the spot diagram"

## Pipeline Phases

Every pipeline follows this structure:

### Phase 1: Modeling
Load or create the optical system. Use:
- `Skill: system-setup` — for creating/loading
- `Skill: sequential-modeling` — for surface editing in sequential mode
- `Skill: non-sequential-modeling` — for NSC systems

### Phase 2: Simulation
Run the requested simulations. Use:
- `Skill: ray-tracing` — for ray traces
- `Skill: analysis` — for MTF, PSF, spot diagrams
- `Skill: optimization` — for local/global optimization
- `Skill: tolerance-analysis` — for sensitivity/Monte Carlo

### Phase 3: Processing
Extract, visualize, and export results. Use:
- `Skill: data-processing` — for plots and reports
- `Skill: cad-export` — for CAD file export

## Workflow

1. Parse the user's pipeline description to identify phases
2. Present the planned pipeline steps to the user for confirmation
3. Execute each phase in sequence:
   a. Load the relevant skill
   b. Generate the Python script for that phase
   c. Execute with: `the Python interpreter (see `references/environment.md` for path)`
   d. Verify output before proceeding to next phase
4. If any phase fails, diagnose the issue and offer to retry or adjust
5. Present final results: plots, reports, and saved file locations

## Python Execution

All pipeline scripts use the shared utility:

```python
import sys, os
# Use CLAUDE_PLUGIN_ROOT set by Claude Code at runtime
_plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
if _plugin_root:
    sys.path.insert(0, os.path.join(_plugin_root, 'scripts'))
from zos_utils import ZOSConnection
```

Execute with:
```
the Python interpreter (see `references/environment.md` for path) <script>.py
```

## Pipeline Coordination

- Each phase's output (e.g., saved .zos file) becomes the next phase's input
- Save intermediate results to `Samples/API/Python/pipeline_output/`
- Track progress and report to the user after each phase
- If a pipeline phase fails, preserve results from earlier phases
- The pipeline can be run partially (e.g., only modeling + simulation)

## Error Handling

- If Zemax is not running, suggest starting OpticStudio
- If license check fails, report the license status
- If file not found, suggest alternative paths or creating a new system
- If Python fails, use the script-debugger agent to diagnose

## Notes

- The full pipeline may take several minutes for complex systems
- Save work at each phase boundary
- Users can abort between phases without losing all progress
- For production use, consider saving the generated script for repeatability
