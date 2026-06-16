---
name: tolerance-analysis
description: This skill should be used when the user asks to "run tolerance analysis", "set up tolerances", "run sensitivity analysis", "Monte Carlo tolerance", "tolerance wizard", "analyze manufacturing tolerances", "configure tolerance data editor", or performs tolerance analysis in Zemax.
version: 0.1.0
---

# Tolerance Analysis — Sensitivity & Monte Carlo

Configure and run tolerance sensitivity analysis and Monte Carlo simulations
to evaluate manufacturing robustness.

## Prerequisites

```python
import sys, os
# Robust import: tries CLAUDE_PLUGIN_ROOT env var first,
# then falls back to cache path and dev path
_PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
_SCRIPTS_PATH = None
if _PLUGIN_ROOT:
    _SCRIPTS_PATH = os.path.join(_PLUGIN_ROOT, 'scripts')
else:
    _CANDIDATES = [
        r'C:\Users\Lex\.claude\plugins\cache\AutoSim\AutoZemax\0.1.0\scripts',
        r'C:\Users\Lex\Desktop\AutoSim\AutoZemax\scripts',
    ]
    for _p in _CANDIDATES:
        if os.path.isdir(_p):
            _SCRIPTS_PATH = _p
            break
if _SCRIPTS_PATH:
    sys.path.insert(0, _SCRIPTS_PATH)
from zos_utils import ZOSConnection
```

Execute with the Python interpreter documented in `references/environment.md`.

## Workflow

### Step 1: Load System

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # Load design to tolerance
    design_file = zos.samples_dir() + \
        "\\Sequential\\Objectives\\Double Gauss 28 degree field.zos"
    TheSystem.LoadFile(design_file, False)
```

### Step 2: Configure Tolerance Wizard

The tolerance wizard sets up default tolerances for all surfaces/elements:

```python
tWiz = TheSystem.TDE.SEQToleranceWizard

# Surface tolerances
tWiz.SurfaceRadius = 0.1        # Fringes (test plate fit)
tWiz.SurfaceThickness = 0.1    # mm
tWiz.SurfaceDecenterX = 0.1    # mm
tWiz.SurfaceDecenterY = 0.1    # mm
tWiz.SurfaceTiltX = 0.2        # degrees
tWiz.SurfaceTiltY = 0.2        # degrees

# Element tolerances
tWiz.ElementDecenterX = 0.1    # mm
tWiz.ElementDecenterY = 0.1    # mm
tWiz.ElementTiltXDegrees = 0.2 # degrees
tWiz.ElementTiltYDegrees = 0.2 # degrees

# Disable certain tolerance types (optional)
tWiz.IsSurfaceSandAIrregularityUsed = False
tWiz.IsIndexUsed = False
tWiz.IsIndexAbbePercentageUsed = False

# Apply wizard
tWiz.OK()
```

### Step 3: Save Toleranced File

```python
import os
output_dir = zos.ensure_api_dir() + "\\tolerance_analysis"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

toleranced_file = output_dir + "\\toleranced_design.zos"
TheSystem.SaveAs(toleranced_file)
```

### Step 4: Run Tolerance Analysis

```python
tol = TheSystem.Tools.OpenTolerancing()

# Sensitivity analysis
tol.SetupMode = ZOSAPI.Tools.Tolerancing.SetupModes.Sensitivity

# Set criterion
tol.Criterion = ZOSAPI.Tools.Tolerancing.Criterions.RMSSpotRadius
tol.CriterionSampling = 3
tol.CriterionComp = ZOSAPI.Tools.Tolerancing.CriterionComps.OptimizeAll_DLS
tol.CriterionCycle = 2
tol.CriterionField = ZOSAPI.Tools.Tolerancing.CriterionFields.UserDefined

# Number of Monte Carlo runs (relevant for MonteCarlo mode)
tol.NumberOfRuns = 20
tol.NumberToSave = 20

# Run
tol.RunAndWaitForCompletion()
tol.Close()
```

### Monte Carlo Analysis

For Monte Carlo simulation instead of sensitivity:

```python
tol.SetupMode = ZOSAPI.Tools.Tolerancing.SetupModes.MonteCarlo
tol.NumberOfRuns = 100
tol.NumberToSave = 10  # Save top N files
tol.RunAndWaitForCompletion()
tol.Close()
```

## Tolerance Criterion Options

| Criterion | Description |
|-----------|-------------|
| RMSSpotRadius | RMS spot radius |
| RMSWavefront | RMS wavefront error |
| MTF | MTF at specified frequency |
| DiffractionMTF | Diffraction MTF |
| BoresightError | Boresight error |
| AngularRadius | Angular radius |

## Setup Modes

| Mode | Description |
|------|-------------|
| Sensitivity | Evaluate each tolerance individually |
| InverseSensitivity | Inverse sensitivity (compute max tolerance for given degradation) |
| MonteCarlo | Random perturbation of all tolerances simultaneously |

## Notes

- The tolerance wizard must run BEFORE opening the tolerancing tool
- Surface tolerances apply to individual surfaces; element tolerances apply to grouped surfaces
- Tolerance values are in lens units (mm for thickness/decenter, degrees for tilt, fringes for radius)
- Report the worst offenders after sensitivity analysis
- Monte Carlo results show statistical distribution of performance
- Save the toleranced file before running analysis for traceability
