<<<<<<< HEAD

# AutoZemax — Zemax OpticStudio Automation Plugin

Automate the complete Zemax optical design workflow — from modeling through
simulation to data processing — using natural language in Claude Code.

## Overview

AutoZemax integrates Zemax OpticStudio's ZOS-API with Claude Code, enabling
optical engineers to create, simulate, optimize, and analyze lens systems
through conversational commands. Each function is encapsulated as a skill
that Claude loads automatically.

## Architecture

```
User → Slash Command → Skills → Python + ZOS-API → Results
                              ↑
                         Agents (validate, analyze, debug)
```

### Commands (4 user-facing entry points)

| Command | Purpose |
|---------|---------|
| `/autozemax:model` | Create/edit optical systems (sequential & NSC) |
| `/autozemax:simulate` | Run ray traces, analyses, optimization, tolerancing |
| `/autozemax:process` | Visualize results, generate reports, export CAD |
| `/autozemax:pipeline` | Full end-to-end workflow: model → simulate → process |

### Skills (9 functional modules)

| Skill | Domain |
|-------|--------|
| `system-setup` | Create/load systems, aperture, fields, wavelengths |
| `sequential-modeling` | Lens Data Editor: surfaces, materials, solves |
| `non-sequential-modeling` | NSC Editor: objects, sources, detectors |
| `ray-tracing` | Batch ray trace & NSC ray trace |
| `analysis` | MTF, PSF, spot diagrams, wavefront, ray fans |
| `optimization` | Merit function, DLS & Hammer optimization |
| `tolerance-analysis` | Sensitivity & Monte Carlo tolerance analysis |
| `cad-export` | Export to STEP, IGES, SAT, STL |
| `data-processing` | numpy/matplotlib visualization & reporting |

### Agents (3 autonomous assistants)

| Agent | Trigger | Role |
|-------|---------|------|
| `model-validator` | After modeling changes | Validate system setup, find errors |
| `result-analyzer` | After simulation completes | Interpret results, suggest improvements |
| `script-debugger` | On Python script failure | Diagnose and fix ZOS-API errors |

## Prerequisites

- **Zemax OpticStudio 2025 R2 (v252)** installed at `C:\Apps\ANSYS Inc\v252\Zemax OpticStudio`
- **Professional or Premium license** (Standard edition has limited API support)
- **Python 3.14 64-bit** at `C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe`
- Python packages: `pythonnet`, `numpy`, `matplotlib`

## Installation

Copy the plugin directory to your Claude Code plugins:

```powershell
# For project-local use, the plugin is already in:
C:\Users\Lex\Desktop\AutoSim\AutoZemax\
```

Or install globally via marketplace (when published).

## Quick Start

### Create and analyze a simple lens

```
/autozemax:pipeline "Create an F/5 100mm focal length singlet using N-BK7,
optimize for minimum spot size at 0 and 7 degrees, then plot the MTF"
```

### Load and tolerance an existing design

```
/autozemax:pipeline "Load the Double Gauss 28 degree sample, run tolerance
sensitivity analysis with 50 Monte Carlo runs, and generate a performance
report"
```

### Step-by-step workflow

```
/autozemax:model      → Create system, add surfaces
/autozemax:simulate   → Optimize, run MTF analysis
/autozemax:process    → Plot results, export report
```

## File Structure

```
AutoZemax/
├── .claude-plugin/plugin.json    # Plugin manifest
├── commands/                      # 4 slash commands
│   ├── model.md
│   ├── simulate.md
│   ├── process.md
│   └── pipeline.md
├── skills/                        # 9 functional skills
│   ├── system-setup/SKILL.md
│   ├── sequential-modeling/SKILL.md
│   ├── non-sequential-modeling/SKILL.md
│   ├── ray-tracing/SKILL.md
│   ├── analysis/SKILL.md
│   ├── optimization/SKILL.md
│   ├── tolerance-analysis/SKILL.md
│   ├── cad-export/SKILL.md
│   └── data-processing/SKILL.md
├── agents/                        # 3 autonomous agents
│   ├── model-validator.md
│   ├── result-analyzer.md
│   └── script-debugger.md
├── scripts/
│   └── zos_utils.py              # Shared ZOS-API connection utility
├── references/
│   ├── zos-api-reference.md      # API class/method quick reference
│   ├── python-examples.md        # Annotated patterns from official examples
│   └── environment.md            # Python/Zemax environment config
├── README.md
└── .gitignore
```

## Environment Configuration

See `references/environment.md` for full details on:
- Python interpreter path and required packages
- Zemax installation and ZOS-API assembly locations
- Environment verification commands

## API Reference

See `references/zos-api-reference.md` for:
- Key ZOSAPI classes and methods
- Common enum values
- Data extraction patterns

## License

MIT
>>>>>>> a13d4f4 (docs: create the plugin)
