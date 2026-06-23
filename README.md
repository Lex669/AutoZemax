# AutoZemax — Zemax OpticStudio Automation Plugin (v0.2.0)

Automate the complete Zemax optical design workflow — from modeling through
simulation to data processing — using natural language in Claude Code.

## Overview

AutoZemax integrates Zemax OpticStudio's ZOS-API with Claude Code, enabling
optical engineers to create, simulate, optimize, and analyze lens systems
through conversational commands. Each function is encapsulated as a skill
that Claude loads automatically.

v0.2.0 is a complete refactor organized around the 26 official ZOS-API sample
patterns, with a library-based architecture that minimizes boilerplate.

## Architecture

```
User → Slash Command → Skills → zos_utils.py (Library) → ZOS-API → Results
                              ↑
                         Agents (validate, analyze, debug)
```

### Commands (4 user-facing entry points)

| Command | Purpose |
|---------|---------|
| `/autozemax:model` | Create/edit optical systems (sequential & NSC) |
| `/autozemax:simulate` | Run ray traces, analyses, optimization, tolerancing |
| `/autozemax:analyze` | Visualize results, generate reports, export CAD |
| `/autozemax:pipeline` | Full end-to-end workflow: model → simulate → analyze |

### Skills (11 functional modules)

| Skill | Domain | Covers ZOS-API Samples |
|-------|--------|------------------------|
| `system-setup` | Create/load systems, aperture, fields, wavelengths | 01, 12, 26 |
| `sequential-modeling` | LDE surfaces, materials, solves, tilts, coatings | 01, 11, 19, 07 |
| `sequential-analysis` | MTF, PSF, spot diagrams, wavefront, ray fans, ZRD | 04, 05, 22, 23 |
| `optimization` | DLS & Hammer optimization, merit function operands | 03, 15 |
| `multi-configuration` | Zoom lenses, multi-config systems, MCE | 18 |
| `tolerance-analysis` | Sensitivity & Monte Carlo tolerance analysis | 14 |
| `nsc-modeling` | NSC objects, sources, detectors | 02, 24 |
| `nsc-analysis` | NSC detector data, phase, ZRD filters | 06, 08, 10 |
| `nsc-scattering` | Bulk scatter, phosphors, volume physics | 17, 21 |
| `cad-exchange` | CAD import/export (STEP, IGES, SAT, STL) | 09, 20 |
| `data-processing` | matplotlib visualization, plot generation, reporting | (all) |

### Agents (3 autonomous assistants)

| Agent | Trigger | Role |
|-------|---------|------|
| `model-validator` | After modeling changes | Validate system setup, find errors |
| `result-analyzer` | After simulation completes | Interpret results, suggest improvements |
| `script-debugger` | On Python script failure | Diagnose and fix ZOS-API errors |

### Core Library (`scripts/zos_utils.py` — 1650+ lines)

The library provides high-level wrappers around ZOS-API, eliminating boilerplate:
- **Connection** — context manager with auto-cleanup
- **Analysis Extractors** — `extract_mtf_data()`, `extract_spot_data()`, `extract_wavefront_data()`, `extract_psf_data()`, `extract_ray_fan_data()`
- **NSC Helpers** — `create_nsc_detector()`, `create_nsc_source()`, `get_detector_data()`, `get_coherent_data()`
- **Optimization Runners** — `run_dls_optimization()`, `run_hammer_optimization()`
- **Tolerance** — `run_tolerance_sensitivity()`, `run_tolerance_monte_carlo()`
- **Multi-Config** — `add_configuration()`, `set_config_operand()`
- **CAD** — `export_cad()`, `import_cad()`
- **Plot Generators** — `plot_mtf()`, `plot_spot_diagram()`, `plot_wavefront_map()`, `plot_ray_fan()`, `plot_detector_data()`, `plot_tolerance_cdf()`
- **Script Templates** — `generate_script()` for repeatable workflows

## Prerequisites

- **Zemax OpticStudio 2025 R2 (v252)**
- **Professional or Premium license** (Standard edition has limited API support)
- **Python 3.14 64-bit** at `C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe`
- Python packages: `pythonnet`, `numpy`, `matplotlib`

## Quick Start

### Create and analyze a simple lens

```
/autozemax:pipeline "Create an F/5 100mm focal length singlet using N-BK7,
optimize for minimum spot size at 0 and 7 degrees, then plot the MTF"
```

### Step-by-step workflow

```
/autozemax:model     → Create system, add surfaces
/autozemax:simulate  → Optimize, run MTF analysis
/autozemax:analyze   → Plot results, export report
```

## File Structure

```
AutoZemax/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── commands/                     # 4 slash commands
│   ├── model.md                 # Phase 1: Create/edit systems
│   ├── simulate.md              # Phase 2: Run analyses & optimization
│   ├── analyze.md               # Phase 3: Plot results & export
│   └── pipeline.md             # Full end-to-end orchestrator
├── skills/                       # 11 functional skills
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
├── agents/                       # 3 autonomous agents
│   ├── model-validator.md
│   ├── result-analyzer.md
│   └── script-debugger.md
├── scripts/
│   └── zos_utils.py             # Core library (1650+ lines)
├── references/
│   ├── zos-api-reference.md     # ZOS-API class/method quick reference
│   └── environment.md           # Python/Zemax environment config
├── ZOS-API Samples/              # 26 official Zemax samples (reference)
├── PythonStandaloneApplication/ # ZOS-API framework boilerplate
├── README.md
└── .gitignore
```

## Supported ZOS-API Sample Coverage

All 26 official ZOS-API Python samples are covered:

| Samples | Skill |
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

## Environment Configuration

See `references/environment.md` for:
- Python interpreter path and required packages
- Zemax installation and ZOS-API assembly locations
- Standard import block and library-based approach
- Environment verification commands

## API Reference

See `references/zos-api-reference.md` for:
- Key ZOSAPI classes and methods
- Common enum values
- Library wrapper function reference
- Data extraction patterns

## License

MIT
