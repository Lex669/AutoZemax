---
name: sequential-modeling
description: This skill should be used when the user asks to "add surface", "insert surface", "modify lens data", "set radius", "set thickness", "assign glass", "add solve", "F/# solve", "make variable", "surface property", "add coating", "configure LDE", "lens data editor", "set tilt and decenter", "add merit function operand", "surface aperture", "surface scattering", or edits the sequential Lens Data Editor in Zemax.
version: 0.2.0
---

# Sequential Mode — Lens Data Editor (LDE)

Insert, delete, reorder, and configure surfaces in the sequential Lens
Data Editor. Covers surface properties (radius, thickness, glass, coating),
solves (F/#, marginal ray angle, pick-up, position), variable setup for
optimization, tilt/decenter via CoordinateBreak, surface apertures, and
merit function operand creation.

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

## Surface Indexing

Surfaces are 1-indexed:
- Surface 1 = Object surface
- Surface 2..N-1 = Optical surfaces (stop, lenses, etc.)
- Surface N = Image surface (always last)

Inserting at position N shifts existing surfaces down by one.

## Accessing the LDE

```python
with ZOSConnection() as zos:
    TheLDE = zos.TheSystem.LDE
    n_surfaces = TheLDE.NumberOfSurfaces
    print(f"System has {n_surfaces} surfaces")
```

## Surface Operations

### Inserting Surfaces

```python
# Insert two surfaces after the object surface
TheLDE.InsertNewSurfaceAt(2)
TheLDE.InsertNewSurfaceAt(2)
# Now: 1=Object, 2=lens_front, 3=lens_rear, 4=Image
```

### Deleting Surfaces

```python
# Delete surface at position 3
TheLDE.DeleteSurfaceAt(3)
```

### Reordering Surfaces

```python
# Move surface 4 to position 2
# TheLDE.MoveSurface(4, 2)
```

## Surface Properties

```python
# Access specific surfaces
surface_2 = TheLDE.GetSurfaceAt(2)
surface_3 = TheLDE.GetSurfaceAt(3)
surface_4 = TheLDE.GetSurfaceAt(4)  # Image

# Radius (mm) — positive = center of curvature to the right
surface_2.Radius = 100.0

# Thickness (mm) — distance to next surface along z-axis
surface_2.Thickness = 10.0
surface_3.Thickness = 50.0

# Glass/material (must be in a loaded catalog)
surface_2.Material = 'N-BK7'

# Comment
surface_2.Comment = 'front of lens'
surface_3.Comment = 'rear of lens'

# Check current values
print(f"Surface 2: R={surface_2.Radius}, T={surface_2.Thickness}, "
      f"Glass={surface_2.Material}")
```

## Surface Type Changes

Change a surface to a different type (e.g., standard, even asphere, coordinate break):

```python
# Change surface to Even Asphere type
asphere_type = TheLDE.GetSurfaceAt(2).GetSurfaceTypeSettings(
    ZOSAPI.Editors.LDE.SurfaceType.EvenAsphere
)
TheLDE.GetSurfaceAt(2).ChangeType(asphere_type)
# Access asphere coefficients:
# Cell 7 = 4th order term, Cell 8 = 6th order, etc.
asphere = TheLDE.GetSurfaceAt(2)
asphere.GetCellAt(7).DoubleValue = 0.0  # 4th order coefficient
asphere.GetCellAt(8).DoubleValue = 0.0  # 6th order coefficient
```

## Solves

### F/# Solve on Radius (common for last optical surface)

```python
ZOSAPI = zos.ZOSAPI
solver = surface_3.RadiusCell.CreateSolveType(
    ZOSAPI.Editors.SolveType.FNumber
)
solver._S_FNumber.FNumber = 10.0
surface_3.RadiusCell.SetSolveData(solver)
```

### Marginal Ray Angle Solve on Thickness

```python
solver = surface_2.ThicknessCell.CreateSolveType(
    ZOSAPI.Editors.SolveType.MarginalRayAngle
)
solver._S_MarginalRayAngle.Angle = -0.1
surface_2.ThicknessCell.SetSolveData(solver)
```

### Pick-Up Solve (copy value from another surface)

```python
solver = surface_3.RadiusCell.CreateSolveType(
    ZOSAPI.Editors.SolveType.Pickup
)
solver._S_Pickup.Surface = 2          # Source surface
solver._S_Pickup.ScaleFactor = 1.0    # Multiply source by this
solver._S_Pickup.Column = 0           # 0=Radius, 1=Thickness, etc.
solver._S_Pickup.Offset = 0.0         # Additive offset
surface_3.RadiusCell.SetSolveData(solver)
```

### Position Solve (maintains thickness to next surface)

```python
solver = surface_3.ThicknessCell.CreateSolveType(
    ZOSAPI.Editors.SolveType.Position
)
solver._S_Position.Surface = 4  # Reference surface
solver._S_Position.Length = 0.0  # Distance from reference
surface_3.ThicknessCell.SetSolveData(solver)
```

## Variables for Optimization

```python
# Make radius and thickness variable
surface_2.RadiusCell.MakeSolveVariable()
surface_2.ThicknessCell.MakeSolveVariable()
surface_3.RadiusCell.MakeSolveVariable()
surface_3.ThicknessCell.MakeSolveVariable()

# Check which surfaces are variable
for i in range(1, TheLDE.NumberOfSurfaces + 1):
    s = TheLDE.GetSurfaceAt(i)
    is_var_r = s.RadiusCell.IsVariable
    is_var_t = s.ThicknessCell.IsVariable
    if is_var_r or is_var_t:
        print(f"Surface {i}: R_var={is_var_r}, T_var={is_var_t}")
```

## Tilt & Decenter (CoordinateBreak)

Use CoordinateBreak surfaces to introduce tilts and decenters:

```python
# Insert CoordinateBreak before a tilted surface
# Suppose surface 2 needs tilt: insert CB at position 2
TheLDE.InsertNewSurfaceAt(2)  # Now surface 2 is the CB
cb = TheLDE.GetSurfaceAt(2)
cb_type = cb.GetSurfaceTypeSettings(
    ZOSAPI.Editors.LDE.SurfaceType.CoordinateBreak
)
cb.ChangeType(cb_type)

# Set decenter and tilt
cb.Thickness = 5.0  # Distance to next surface along tilted axis
cb.GetCellAt(2).DoubleValue = 0.0  # Decenter X (mm)
cb.GetCellAt(3).DoubleValue = 0.0  # Decenter Y (mm)
cb.GetCellAt(4).DoubleValue = 0.0  # Tilt X (degrees)
cb.GetCellAt(5).DoubleValue = 0.0  # Tilt Y (degrees)
cb.GetCellAt(6).DoubleValue = 0.0  # Tilt Z (degrees)

# Add a second CB after tilted surfaces to restore coordinate system
```

## Surface Apertures

Apply apertures (circular, rectangular, etc.) to restrict light on a surface:

```python
# Get surface and access aperture
surf = TheLDE.GetSurfaceAt(2)
surf_aperture = surf.Aperture

# Set aperture type
surf_aperture.Type = ZOSAPI.Editors.LDE.SurfaceApertureTypes.RectangularAperture

# Set aperture dimensions (in lens units)
# Cell indices vary by aperture type
surf_aperture.MinimumX = -5.0
surf_aperture.MaximumX = 5.0
surf_aperture.MinimumY = -5.0
surf_aperture.MaximumY = 5.0

# Common aperture types:
# CircularAperture, RectangularAperture, EllipticalAperture,
# FloatingAperture, UserDefinedAperture, SpiderAperture, Obscuration
```

## Coatings

Apply thin-film coatings to surfaces:

```python
# Apply a coating by name
surface_2.Coating = 'AR'  # Anti-reflection coating
surface_3.Coating = 'ALUMINUM'  # Reflective coating

# Common coating names: 'AR', 'ALUMINUM', 'SILVER', 'GOLD',
# or custom coatings from the coating catalog
```

## Merit Function Operands from LDE Context

Create common merit function operands during lens construction:

```python
TheMFE = zos.TheSystem.MFE
TheMFE.RemoveOperands(1, TheMFE.NumberOfOperands)

# Add an EFFL operand for focal length control
effl = TheMFE.AddOperand()
effl.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.EFFL)
effl.Target = 100.0
effl.Weight = 1.0

# Add boundary constraints with MFE_CELL constants
mnca = TheMFE.AddOperand()
mnca.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.MNCA)
mnca.Target = 0.5
mnca.Weight = 1.0
mfe_set_cell(mnca, MFE_CELL["SURF1"], 1)  # Start surface
mfe_set_cell(mnca, MFE_CELL["SURF2"], 3)  # End surface

# Add a SPHA operand for spherical aberration control
spha = TheMFE.AddOperand()
spha.ChangeType(ZOSAPI.Editors.MFE.MeritOperandType.SPHA)
spha.Target = 0.0
spha.Weight = 1.0
mfe_set_cell(spha, MFE_CELL["FIELD"], 1)  # Field 1
mfe_set_cell(spha, MFE_CELL["WAVE"], 1)   # Wavelength 1
mfe_set_cell(spha, MFE_CELL["ZONE"], 0)   # Zone 0 = all zones
```

## Surface Cell Reference

| Property | Cell | Direct Access |
|----------|------|---------------|
| Radius | surface.RadiusCell | surface.Radius |
| Thickness | surface.ThicknessCell | surface.Thickness |
| Glass/Material | surface.MaterialCell | surface.Material |
| Comment | surface.CommentCell | surface.Comment |
| Coating | surface.CoatingCell | surface.Coating |
| Semi-Diameter | surface.SemiDiameterCell | surface.SemiDiameter |
| Conic | surface.ConicCell | surface.Conic |

Each Cell supports: `MakeSolveVariable()`, `IsVariable`, `CreateSolveType(type)`,
`SetSolveData(solver)`, `DoubleValue`, `IntegerValue`.

## Notes

- Call `zos.validate_system_ready()` BEFORE adding surfaces to catch missing aperture/fields/wavelengths
- Always configure System Explorer (aperture, fields, wavelengths) before inserting surfaces
- Radius sign: positive = center of curvature to the right of the surface
- Thickness = distance to the NEXT surface along the optical axis
- Materials must match a loaded catalog — add 'SCHOTT' before assigning 'N-BK7'
- **For tilt/decenter, ALWAYS use CoordinateBreak surfaces** — never set tilt directly on a standard surface
- After a CoordinateBreak tilt, insert a second CoordinateBreak with opposite tilt to restore the coordinate system
- Use `MFE_CELL` constants from zos_utils instead of magic cell-index numbers to avoid silent operand misconfiguration
- **Never use `obj.TiltX`/`TiltY`/`TiltZ` in NSC mode** — use `zos.set_nsc_orientation()` or `TiltAboutX/Y/Z`
