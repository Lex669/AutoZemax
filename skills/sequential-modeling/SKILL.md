---
name: sequential-modeling
description: This skill should be used when the user asks to "add a surface", "modify lens data", "set surface radius", "set thickness", "assign glass material", "add a solve", "configure lens data editor", "insert a lens surface", "set F/# solve", "make a variable for optimization", "add coating", or edits the Lens Data Editor (LDE) of a sequential optical system.
version: 0.1.0
---

# Sequential Mode — Lens Data Editor (LDE)

Insert, modify, and configure surfaces in the sequential Lens Data Editor.
Covers surface properties (radius, thickness, material, glass, coating),
F/# solves, variable setup, and surface comments.

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

## Surface Indexing

Surfaces are 1-indexed:
- Surface 1 = Object surface
- Last surface = Image surface
- Insert at position N shifts existing surfaces down

## Workflows

### Inserting Surfaces

```python
with ZOSConnection() as zos:
    TheLDE = zos.TheSystem.LDE

    # Insert surfaces at position 2 (after object)
    TheLDE.InsertNewSurfaceAt(2)
    TheLDE.InsertNewSurfaceAt(2)

    # Now surfaces are: 1=Object, 2=front lens, 3=rear lens, 4=Image
    surface_1 = TheLDE.GetSurfaceAt(1)  # Object
    surface_2 = TheLDE.GetSurfaceAt(2)  # Front of lens
    surface_3 = TheLDE.GetSurfaceAt(3)  # Rear of lens
    surface_4 = TheLDE.GetSurfaceAt(4)  # Image
```

### Setting Surface Properties

```python
# Stop surface (surface 1)
surface_1.Thickness = 50.0
surface_1.Comment = 'Stop is free to move'

# Front lens surface
surface_2.Radius = 100.0         # Positive = convex toward object
surface_2.Thickness = 10.0       # mm
surface_2.Material = 'N-BK7'     # From SCHOTT catalog
surface_2.Comment = 'front of lens'

# Rear lens surface
surface_3.Comment = 'rear of lens'
```

### Adding Solves

F/# solve (common for the last optical surface radius):

```python
ZOSAPI = zos.ZOSAPI
solver = surface_3.RadiusCell.CreateSolveType(ZOSAPI.Editors.SolveType.FNumber)
solver._S_FNumber.FNumber = 10.0
surface_3.RadiusCell.SetSolveData(solver)
```

Marginal ray angle solve on thickness:

```python
solver = surface_2.ThicknessCell.CreateSolveType(
    ZOSAPI.Editors.SolveType.MarginalRayAngle
)
solver._S_MarginalRayAngle.Angle = -0.1
surface_2.ThicknessCell.SetSolveData(solver)
```

### Making Variables for Optimization

```python
surface_1.ThicknessCell.MakeSolveVariable()
surface_2.RadiusCell.MakeSolveVariable()
surface_2.ThicknessCell.MakeSolveVariable()
surface_3.ThicknessCell.MakeSolveVariable()
```

### Checking Surface Count

```python
num_surfaces = TheLDE.NumberOfSurfaces
print(f"System has {num_surfaces} surfaces")

for i in range(1, num_surfaces + 1):
    s = TheLDE.GetSurfaceAt(i)
    print(f"Surface {i}: R={s.Radius}, T={s.Thickness}, "
          f"Glass={s.Material}, Comment={s.Comment}")
```

## Surface Cell Access

Each property has a corresponding Cell for fine control:
- `surface.Radius` / `surface.RadiusCell`
- `surface.Thickness` / `surface.ThicknessCell`
- `surface.Material` / `surface.MaterialCell`
- `surface.Comment` / `surface.CommentCell`

Cells support:
- `MakeSolveVariable()` — Make the parameter variable in optimization
- `CreateSolveType(type)` — Add a solve
- `SetSolveData(solver)` — Apply solve configuration
- `IntegerValue` / `DoubleValue` — Direct cell data access

## Notes

- Always configure aperture, fields, and wavelengths BEFORE adding surfaces
- Surface order: Object (1) → optical surfaces → Image (last)
- Radius sign convention: positive = center of curvature to the right
- Thickness is the distance to the NEXT surface along the z-axis
- Material name must match a loaded catalog (use SCHOTT catalog for N-BK7, etc.)
