---
name: optimization
description: This skill should be used when the user asks to "optimize the lens", "run optimization", "set up merit function", "add merit operand", "run DLS optimization", "run Hammer optimization", "set optimization targets", "configure merit function editor", "improve optical performance", or performs lens optimization in Zemax.
version: 0.1.0
---

# Optimization — Merit Function & Optimization Algorithms

Set up merit function operands with targets and weights, then run local
(Damped Least Squares) or global (Hammer) optimization.

## Prerequisites

```python
import sys, os
# Use CLAUDE_PLUGIN_ROOT set by Claude Code at runtime
_plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
if _plugin_root:
    sys.path.insert(0, os.path.join(_plugin_root, 'scripts'))
from zos_utils import ZOSConnection
```

Execute with the Python interpreter documented in `references/environment.md`.

## Making Variables

Before optimization, surfaces must have variables defined:

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheLDE = zos.TheSystem.LDE

    # Make specific surfaces variable
    surface_1 = TheLDE.GetSurfaceAt(1)
    surface_2 = TheLDE.GetSurfaceAt(2)
    surface_3 = TheLDE.GetSurfaceAt(3)

    surface_1.ThicknessCell.MakeSolveVariable()
    surface_2.ThicknessCell.MakeSolveVariable()
    surface_2.RadiusCell.MakeSolveVariable()
    surface_3.ThicknessCell.MakeSolveVariable()
```

## Merit Function Editor (MFE)

### Accessing and Modifying Existing Operands

```python
TheMFE = zos.TheSystem.MFE

# Modify first operand (default is usually EFFL or spot)
operand_1 = TheMFE.GetOperandAt(1)
operand_1.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.ASTI)
operand_1.Target = 0.0
operand_1.Weight = 10.0
```

### Adding New Operands

```python
# Insert at specific position
operand_2 = TheMFE.InsertNewOperandAt(2)
operand_2.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.COMA)
operand_2.Target = 0.0
operand_2.Weight = 1.0

# Append to end
operand = TheMFE.AddOperand()
operand.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.MNCA)
operand.Target = 0.5
operand.Weight = 1.0
# Set cell parameters for boundary operands
operand.GetCellAt(2).IntegerValue = 1   # Start surface
operand.GetCellAt(3).IntegerValue = 3   # End surface
```

### Common Merit Operand Types

| Type | Description | Parameters |
|------|-------------|------------|
| ASTI | Astigmatism | Field, Wave |
| COMA | Coma | Field, Wave |
| SPHA | Spherical aberration | Field, Wave, Zone |
| DIST | Distortion | Field, Wave |
| EFFL | Effective focal length | Wave |
| MNCA | Min center air thickness | Surf1, Surf2 |
| MXCA | Max center air thickness | Surf1, Surf2 |
| MNEA | Min edge air thickness | Surf1, Surf2 |
| MXEA | Max edge air thickness | Surf1, Surf2 |
| MNCG | Min center glass thickness | Surf1, Surf2 |
| MXCG | Max center glass thickness | Surf1, Surf2 |
| MNEG | Min edge glass thickness | Surf1, Surf2 |
| MXEG | Max edge glass thickness | Surf1, Surf2 |
| MNIN | Min index of refraction | Surf1, Surf2 |
| MXIN | Max index of refraction | Surf1, Surf2 |
| MNAB | Min Abbe number | Surf1, Surf2 |
| MXAB | Max Abbe number | Surf1, Surf2 |

## Running Optimization

### Local Optimization (Damped Least Squares)

```python
print('Running Local Optimization...')
LocalOpt = zos.TheSystem.Tools.OpenLocalOptimization()
LocalOpt.Algorithm = ZOSAPI.Tools.Optimization.OptimizationAlgorithm.DampedLeastSquares
LocalOpt.Cycles = ZOSAPI.Tools.Optimization.OptimizationCycles.Automatic
LocalOpt.NumberOfCores = 8
LocalOpt.RunAndWaitForCompletion()
LocalOpt.Close()
print('Local optimization complete')
```

### Hammer Optimization (Global)

```python
import time

print('Running Hammer Optimization...')
HammerOpt = zos.TheSystem.Tools.OpenHammerOptimization()

# Run for specified duration (seconds)
HammerOpt.RunAndWaitWithTimeout(30)

# Cancel if still running
HammerOpt.Cancel()
HammerOpt.WaitForCompletion()
HammerOpt.Close()
print('Hammer optimization complete')
```

### Checking Merit Function Value

```python
# After optimization, check the merit function
initial_mf = TheMFE.MeritFunctionValue
print(f"Merit function value: {initial_mf}")
```

## Full Optimization Workflow

1. Create or load optical system
2. Set variables on surfaces (MakeSolveVariable)
3. Configure merit function operands with targets and weights
4. Add boundary constraints (min/max thicknesses, glass limits, etc.)
5. Run local optimization first
6. Follow with Hammer optimization for global search
7. Save optimized system

## Notes

- Always add boundary constraints (MNCA, MXCA, MNCG, MXCG) to prevent unrealistic solutions
- Start with higher weights on primary aberrations, reduce iteratively
- Local optimization is fast but can get stuck in local minima
- Hammer optimization explores globally but requires much more time
- `NumberOfCores` should match available CPU cores for DLS
- Check `IsRunning` to monitor long-running optimizations
