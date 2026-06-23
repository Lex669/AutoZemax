---
name: optimization
description: This skill should be used when the user asks to "optimize", "run optimization", "DLS optimization", "hammer optimization", "local optimization", "global optimization", "merit function", "add operand", "set target", "set weight", "convergence", "optimization cycles", "quick focus", "QFocus", "make merit function", or performs lens optimization in Zemax.
version: 0.2.0
---

# Optimization — Merit Function, DLS, Hammer & QFocus

Build merit functions (default or custom), set variables, run local
Damped Least Squares optimization, global Hammer optimization, and
Quick Focus. Control convergence settings and CPU core usage.

## Prerequisites

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
from zos_utils import ZOSConnection, set_seed, MFE_CELL, mfe_set_cell

set_seed(42)
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## Optimization Workflow

1. Load or create optical system with aperture, fields, wavelengths configured
2. Declare variables on surfaces (MakeSolveVariable)
3. Build merit function (default or custom operands with targets and weights)
4. Add boundary constraints (min/max thicknesses, edge thicknesses)
5. Run local optimization (DLS) first
6. Optionally follow with Hammer (global) for further improvement
7. Save optimized system
8. Run analyses (MTF, spot diagram) to verify improvement

## Making Variables

Before optimization, declare which surface parameters are free variables:

```python
with ZOSConnection() as zos:
    TheLDE = zos.TheSystem.LDE

    # Access surfaces
    surface_2 = TheLDE.GetSurfaceAt(2)
    surface_3 = TheLDE.GetSurfaceAt(3)

    # Make variables
    surface_2.RadiusCell.MakeSolveVariable()
    surface_2.ThicknessCell.MakeSolveVariable()
    surface_3.RadiusCell.MakeSolveVariable()
    surface_3.ThicknessCell.MakeSolveVariable()

    # Verify by checking IsVariable on relevant cells
```

## Merit Function Editor (MFE)

### Default Merit Function

The quickest way to set up optimization — generates operands for a
standard performance metric (RMS spot radius, wavefront, etc.):

```python
MFE = zos.TheSystem.MFE
SD = zos.TheSystem.SystemData

# Remove existing operands
MFE.RemoveOperands(1, MFE.NumberOfOperands)

# Generate default merit function: RMS spot radius
MFE.MakeMeritFunction(
    ZOSAPI.Editors.MFE.MeritFunctionType.RMS,
    ZOSAPI.Tools.Optimization.OptimizationOperandType.SpotRadius,
    1,                    # Wavelength weight start
    0,                    # Wavelength weight end (0 = all equal)
    0.0,                  # Boundary tolerance
    SD.Wavelengths.NumberOfWavelengths,
    0.0,                  # Starting weight
    0.0,                  # Pupil integration method
    0.0,                  # Reference
    True                  # Overall weight
)

print(f"Default MF created — {MFE.NumberOfOperands} operands")
```

### Custom Operands

Add specific aberration operands with targets and weights:

```python
# EFFL — effective focal length constraint
effl = MFE.AddOperand()
effl.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.EFFL)
effl.Target, effl.Weight = 100.0, 1.0
mfe_set_cell(effl, MFE_CELL["WAVE"], 1)

# SPHA — spherical aberration
spha = MFE.AddOperand()
spha.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.SPHA)
spha.Target, spha.Weight = 0.0, 1.0
mfe_set_cell(spha, MFE_CELL["FIELD"], 1)
mfe_set_cell(spha, MFE_CELL["WAVE"], 1)
mfe_set_cell(spha, MFE_CELL["ZONE"], 0)

# COMA, ASTI, DIST — similar pattern:
for op_type, field, wave in [
    (ZOSAPI.Editors.MFE.MeritOperandType.COMA, 1, 1),
    (ZOSAPI.Editors.MFE.MeritOperandType.ASTI, 1, 1),
    (ZOSAPI.Editors.MFE.MeritOperandType.DIST, 1, 1),
]:
    op = MFE.AddOperand()
    op.ChangeType(op_type)
    op.Target, op.Weight = 0.0, 1.0
    mfe_set_cell(op, MFE_CELL["FIELD"], field)
    mfe_set_cell(op, MFE_CELL["WAVE"], wave)
```

### Boundary Constraints

Prevent unrealistic physical solutions (MNCA = min center air thickness,
MNCG = min center glass thickness, MXCA = max center air thickness):

```python
mnca = MFE.AddOperand()
mnca.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.MNCA)
mnca.Target, mnca.Weight = 0.5, 1.0
mfe_set_cell(mnca, MFE_CELL["SURF1"], 1)
mfe_set_cell(mnca, MFE_CELL["SURF2"], 3)

mncg = MFE.AddOperand()
mncg.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.MNCG)
mncg.Target, mncg.Weight = 2.0, 1.0
mfe_set_cell(mncg, MFE_CELL["SURF1"], 3)
mfe_set_cell(mncg, MFE_CELL["SURF2"], 4)

mxca = MFE.AddOperand()
mxca.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.MXCA)
mxca.Target, mxca.Weight = 50.0, 1.0
mfe_set_cell(mxca, MFE_CELL["SURF1"], 1)
mfe_set_cell(mxca, MFE_CELL["SURF2"], 5)
```

## Quick Focus (QFocus)

Quick pre-optimization — adjusts only the image surface thickness and/or
last radius to minimize RMS spot size. Run BEFORE full DLS optimization:

```python
with ZOSConnection() as zos:
    # Run Quick Focus (optimizes image distance)
    qf = zos.TheSystem.Tools.OpenQuickFocus()
    qf.Criterion = ZOSAPI.Tools.Optimization.QuickFocusCriterion.RMSSpotRadius
    qf.NumberOfRays = 20
    qf.RunAndWaitForCompletion()
    qf.Close()
    print("Quick Focus complete")

    # Check improvement
    mf_before = zos.TheSystem.MFE.MeritFunctionValue
    print(f"Merit function after QFocus: {mf_before:.6f}")
```

## Local Optimization (DLS)

### Using the Library Safe Wrapper

```python
# Single call — handles setup, cleanup, and returns final MF value
mf = zos.run_dls_optimization(cycles=None, num_cores=8)
# cycles=None = Automatic; pass an int for fixed cycles
print(f"Merit function after DLS: {mf:.6f}")
```

### Manual Control (full API access)

```python
opt = zos.TheSystem.Tools.OpenLocalOptimization()
try:
    opt.Algorithm = ZOSAPI.Tools.Optimization.OptimizationAlgorithm.DampedLeastSquares
    opt.Cycles = ZOSAPI.Tools.Optimization.OptimizationCycles.Automatic
    opt.NumberOfCores = 8
    opt.AutoConvergence = True
    opt.MinimumChange = 1e-6
    opt.MaximumCycles = 100

    mf_before = zos.TheSystem.MFE.MeritFunctionValue
    opt.RunAndWaitForCompletion()
    mf_after = zos.TheSystem.MFE.MeritFunctionValue
    print(f"MF: {mf_before:.6f} -> {mf_after:.6f}")
finally:
    opt.Close()
```

## Global Optimization (Hammer)

Run after DLS to escape local minima:

### Using the Library Safe Wrapper

```python
# Handles timeout and proper Cancel() logic
mf = zos.run_hammer_optimization(timeout_sec=30)
print(f"Merit function after Hammer: {mf:.6f}")
```

### Manual Control (if full API access needed)

```python
hammer = zos.TheSystem.Tools.OpenHammerOptimization()
try:
    hammer.RunAndWaitWithTimeout(30)
    if hammer.IsRunning:
        print("Still running — cancelling...")
        hammer.Cancel()
        hammer.WaitForCompletion()
    else:
        print("Hammer completed within timeout.")
finally:
    hammer.Close()
```

## Complete Optimization Workflow

```python
with ZOSConnection() as zos:
    TheSystem = zos.TheSystem
    TheLDE = TheSystem.LDE
    MFE = TheSystem.MFE
    SD = TheSystem.SystemData

    # 1. Load system
    zos.open_file(zos.samples_dir() +
        "\\Sequential\\Objectives\\Double Gauss 28 degree field.zos")

    # 2. Set variables on multiple surfaces
    for surf_num in [2, 3, 5, 6, 7, 8]:
        s = TheLDE.GetSurfaceAt(surf_num)
        s.RadiusCell.MakeSolveVariable()
        s.ThicknessCell.MakeSolveVariable()

    # 3. Build merit function: default RMS spot + EFFL constraint
    MFE.RemoveOperands(1, MFE.NumberOfOperands)
    MFE.MakeMeritFunction(
        ZOSAPI.Editors.MFE.MeritFunctionType.RMS,
        ZOSAPI.Tools.Optimization.OptimizationOperandType.SpotRadius,
        1, 0, 0.0, SD.Wavelengths.NumberOfWavelengths, 0.0, 0.0, 0.0, True)

    effl = MFE.AddOperand()
    effl.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.EFFL)
    effl.Target = 100.0
    effl.Weight = 1.0

    # 4. Run QFocus first as pre-optimization
    qf = TheSystem.Tools.OpenQuickFocus()
    qf.Criterion = ZOSAPI.Tools.Optimization.QuickFocusCriterion.RMSSpotRadius
    qf.RunAndWaitForCompletion()
    qf.Close()

    # 5. Local optimization
    mf_dls = zos.run_dls_optimization()
    print(f"After DLS: {mf_dls:.6f}")

    # 6. Global optimization
    mf_hammer = zos.run_hammer_optimization(timeout_sec=20)
    print(f"After Hammer: {mf_hammer:.6f}")

    # 7. Save
    zos.save_file(zos.ensure_zmx_dir() + "\\double_gauss_optimized.zmx")
```

## Convergence & CPU Settings

| Parameter | Options | Description |
|-----------|---------|-------------|
| Algorithm | DampedLeastSquares, OrthogonalDescent | Optimization algorithm |
| Cycles | Automatic, Fixed, Cycles_N | Number of DLS cycles |
| AutoConvergence | True, False | Stop automatically when MF stabilizes |
| MinimumChange | 1e-8 to 1e-3 | Minimum MF change for convergence |
| NumberOfCores | 1 to N (max logical cores) | CPU threads for DLS |
| MaximumCycles | 1 to 500 | Hard cycle limit |

## Common Merit Operand Types

| Type | Description | Required Cells |
|------|-------------|----------------|
| EFFL | Effective focal length | WAVE (2) |
| SPHA | Spherical aberration | FIELD (2), WAVE (3), ZONE (4) |
| COMA | Coma | FIELD (2), WAVE (3) |
| ASTI | Astigmatism | FIELD (2), WAVE (3) |
| DIST | Distortion | FIELD (2), WAVE (3) |
| FCUR | Field curvature | FIELD (2), WAVE (3) |
| MNCA | Minimum center air thickness | SURF1 (2), SURF2 (3) |
| MXCA | Maximum center air thickness | SURF1 (2), SURF2 (3) |
| MNEA | Minimum edge air thickness | SURF1 (2), SURF2 (3) |
| MXEA | Maximum edge air thickness | SURF1 (2), SURF2 (3) |
| MNCG | Minimum center glass thickness | SURF1 (2), SURF2 (3) |
| MXCG | Maximum center glass thickness | SURF1 (2), SURF2 (3) |
| MNEG | Minimum edge glass thickness | SURF1 (2), SURF2 (3) |
| MXEG | Maximum edge glass thickness | SURF1 (2), SURF2 (3) |

## Notes

- **Run QFocus BEFORE full optimization** — it provides a quick starting point by adjusting only image distance
- **Always add boundary constraints** (MNCA, MXCA, MNCG, MXCG, MNEA, MXEA) to prevent physically unrealistic solutions (surfaces crossing, negative thicknesses)
- **Use library safe wrappers** `zos.run_dls_optimization()` and `zos.run_hammer_optimization()` — they handle proper cleanup, fix the Cancel() bug, and return the final MF value
- **Use `MFE_CELL` constants** instead of magic cell-index numbers to avoid silent operand misconfiguration
- Run local (DLS) first, then Hammer global — DLS finds a local minimum quickly, Hammer searches for better minima globally
- Hammer is computationally expensive — use `timeout_sec` to limit runtime (typically 20-60 seconds)
- `NumberOfCores` should match or be slightly below available CPU cores
- Check `opt.IsRunning` to monitor long-running optimizations
- Call `zos.validate_system_ready()` before optimization to catch missing variables, fields, or wavelengths
- Use `zos.save_file()` frequently to checkpoint progress before and after optimization
