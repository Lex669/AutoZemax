---
name: nsc-modeling
description: This skill should be used when the user asks to "NSC modeling", "non-sequential", "NSC object", "add source", "add detector", "NSC editor", "create NSC", "NSC geometry", "source ellipse", "source point", "collimated source", "detector rectangle", "NSC position", "NSC orientation", "TiltAboutX", "TiltAboutY", "TiltAboutZ", "NSC material", or creates and configures non-sequential components in Zemax OpticStudio.
version: 0.2.0
---

# NSC Modeling — Sources, Detectors, Position & Orientation

Create and configure non-sequential components via the NSC Editor (TheNCE).
Covers source objects (elliptical, point, collimated, rectangle), detector
objects (rectangle, surface, volume), object positioning and orientation
using the correct TiltAboutX/Y/Z property names, and material assignment.
Corresponds to ZOS-API Samples 02 and 24.

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
from zos_utils import ZOSConnection, set_seed

set_seed(42)
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## The NSC Editor (TheNCE)

All non-sequential objects live in TheNCE (NSC Editor). Objects are 1-indexed.
A new NSC system starts with three default objects: a SourceEllipse (Object 1),
a DetectorRectangle (Object 2), and a geometry object (Object 3).

```python
with ZOSConnection() as zos:
    TheNCE = zos.TheSystem.NCE
    n_objects = TheNCE.NumberOfObjects
    print(f"NSC system has {n_objects} objects")

    # Inspect existing objects
    for i in range(1, n_objects + 1):
        obj = TheNCE.GetObjectAt(i)
        print(f"  Object {i}: type={obj.ObjectType}, comment={obj.Comment}")
```

### Inserting and Deleting Objects

```python
# Insert a new object at a specific position (shifts others down)
TheNCE.InsertNewObjectAt(2)   # Becomes new object 2, old 2→3

# Delete an object
TheNCE.DeleteObjectAt(3)

# Get number of objects after changes
print(f"Objects: {TheNCE.NumberOfObjects}")
```

## Creating Sources

Use `zos.create_nsc_source()` to configure any NSC object as a source.
Supports elliptical, point, collimated, and rectangle source types.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    zos.new_file(ZOSAPI.SystemType.NonSequential)
    TheNCE = zos.TheSystem.NCE

    # Object 1 is the default Source Ellipse — reconfigure it
    source = zos.create_nsc_source(
        obj_number=1,
        source_type='elliptical',
        x_half_width=2.0,        # X half-width (mm)
        y_half_width=2.0,        # Y half-width (mm)
        total_rays=500000,       # Total rays for analysis
        layout_rays=50,          # Rays shown in layout view
        power_lumens=100.0,      # Source power (lumens)
        num_analysis_rays=500000 # Analysis rays
    )

    # Insert and configure a point source
    TheNCE.InsertNewObjectAt(2)
    point = zos.create_nsc_source(
        obj_number=2,
        source_type='point',
        total_rays=1000000,
        power_lumens=50.0
    )

    # Insert and configure a collimated source
    TheNCE.InsertNewObjectAt(3)
    collimated = zos.create_nsc_source(
        obj_number=3,
        source_type='collimated',
        x_half_width=10.0,
        y_half_width=10.0,
        total_rays=2000000
    )
```

### Source Type Reference

| Source Type | ObjectType Enum | Description | Key Cell |
|-------------|----------------|-------------|----------|
| elliptical | SourceElliptical | Diverging elliptical beam | Cell 1-2: X/Y half-width |
| point | SourcePoint | Isotropic / angular point source | Cell 1: cone angle |
| collimated | SourceCollimated | Parallel beam, rectangular cross-section | Cell 1-2: X/Y half-width |
| rectangle | SourceRectangle | Diverging rectangular beam | Cell 1-2: X/Y half-width |

## Creating Detectors

Use `zos.create_nsc_detector()` to configure NSC objects as detectors.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    zos.new_file(ZOSAPI.SystemType.NonSequential)
    TheNCE = zos.TheSystem.NCE

    # Object 2 is the default Detector Rectangle — reconfigure it
    detector = zos.create_nsc_detector(
        obj_number=2,
        detector_type='rectangle',
        x_half_width=10.0,    # X half-width (mm)
        y_half_width=10.0,    # Y half-width (mm)
        pixels_x=256,          # X pixel count
        pixels_y=256,          # Y pixel count
        material='ABSORB',     # Detector material
        comment='Main Detector'
    )

    # Insert a DetectorSurface (includes coating/physics properties)
    TheNCE.InsertNewObjectAt(3)
    surface_det = zos.create_nsc_detector(
        obj_number=3,
        detector_type='surface',
        x_half_width=5.0,
        y_half_width=5.0,
        pixels_x=128,
        pixels_y=128,
        material='ABSORB',
        comment='Surface Detector'
    )

    # Insert a DetectorVolume (for volume/phosphor analysis)
    TheNCE.InsertNewObjectAt(4)
    vol_det = zos.create_nsc_detector(
        obj_number=4,
        detector_type='volume',
        x_half_width=3.0,
        y_half_width=3.0,
        pixels_x=64,
        pixels_y=64,
        material='ABSORB',
        comment='Volume Detector'
    )
```

### Detector Type Reference

| Type | ObjectType Enum | Description | Cells |
|------|----------------|-------------|-------|
| rectangle | DetectorRectangle | 2D pixelated irradiance/fluence map | Cell 1-2: X/Y size, Cell 4-5: pixels |
| surface | DetectorSurface | Like rectangle + coating & scattering properties | Same as rectangle |
| volume | DetectorVolume | 3D volume with Z layers | Cell 1-3: X/Y/Z size, Cell 4-6: pixels |

## Object Positioning

Use `zos.set_nsc_position()` to place objects in 3D space. Positions are
relative to the global coordinate system (mm).

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    zos.new_file(ZOSAPI.SystemType.NonSequential)
    TheNCE = zos.TheSystem.NCE

    source = TheNCE.GetObjectAt(1)
    zos.set_nsc_position(source, x=0.0, y=0.0, z=0.0)

    detector = TheNCE.GetObjectAt(2)
    zos.set_nsc_position(detector, x=0.0, y=0.0, z=50.0)

    zos.set_nsc_position(mirror, x=25.0, y=0.0, z=25.0)
```

### Direct Property Access

For advanced use, set position directly. The property names XPosition,
YPosition, ZPosition are always safe (no pythonnet traps):

```python
obj.XPosition = 10.0
obj.YPosition = -5.0
obj.ZPosition = 100.0
```

## Object Orientation — WARNING: TiltAboutX/Y/Z Only

**CRITICAL WARNING**: In pythonnet, `TiltX`, `TiltY`, and `TiltZ` are
NOT valid property names. They silently create Python-only attributes
that Zemax ignores. The only valid names are `TiltAboutX`, `TiltAboutY`,
and `TiltAboutZ`.

**Always use `zos.set_nsc_orientation()`** — it uses the correct names:

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    zos.new_file(ZOSAPI.SystemType.NonSequential)
    TheNCE = zos.TheSystem.NCE

    obj = TheNCE.GetObjectAt(1)

    # Safe: library wrapper uses TiltAboutX/Y/Z
    zos.set_nsc_orientation(obj, tilt_x=0.0, tilt_y=45.0, tilt_z=0.0)

    # Safe: direct property assignment with correct names
    obj.TiltAboutX = 10.0
    obj.TiltAboutY = 0.0
    obj.TiltAboutZ = 0.0

    # DANGER — these SILENTLY FAIL:
    # obj.TiltX = 45.0    <-- TRAP! Creates Python attribute, ignored by Zemax
    # obj.tilt_y = 45.0   <-- TRAP! Case variations are also ignored
```

### Orientation in Practice — Tilted Mirror Example

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    zos.new_file(ZOSAPI.SystemType.NonSequential)
    TheNCE = zos.TheSystem.NCE

    # Fold mirror at 45 degrees
    # Insert at position 3 (after default source and detector)
    TheNCE.InsertNewObjectAt(3)
    mirror = TheNCE.GetObjectAt(3)
    mirror.ChangeType(ZOSAPI.Editors.NCE.ObjectType.StandardRectangle)
    mirror.Material = 'MIRROR'
    zos.set_nsc_position(mirror, x=0.0, y=0.0, z=25.0)
    zos.set_nsc_orientation(mirror, tilt_x=0.0, tilt_y=-45.0, tilt_z=0.0)

    # Reposition detector to intercept the folded beam
    det = TheNCE.GetObjectAt(2)
    zos.set_nsc_position(det, x=-25.0, y=0.0, z=25.0)
    zos.set_nsc_orientation(det, tilt_x=0.0, tilt_y=45.0, tilt_z=0.0)
```

## Material Assignment

Materials control how rays interact with NSC objects. Common materials:

| Material | Description |
|----------|-------------|
| ABSORB | Perfect absorber (black, no reflection) |
| MIRROR | Ideal reflector |
| LENS | Refractive material (catalog glass type) |
| AIR | No optical effect (pass-through) |
| SCATTER | Scattering surface |

```python
with ZOSConnection() as zos:
    TheNCE = zos.TheSystem.NCE

    # Assign by name
    obj = TheNCE.GetObjectAt(1)
    obj.Material = 'MIRROR'

    # For refractive materials, use catalog glass names
    obj.Material = 'N-BK7'       # SCHOTT glass

    # For detector objects, use ABSORB
    det = TheNCE.GetObjectAt(2)
    det.Material = 'ABSORB'

    # Read current material
    print(f"Object material: {obj.Material}")
```

## Complete Source-Detector System

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    zos.new_file(ZOSAPI.SystemType.NonSequential)
    TheNCE = zos.TheSystem.NCE

    # 1. Source: elliptical at origin, emitting upward (+Z)
    source = zos.create_nsc_source(
        1, source_type='elliptical',
        x_half_width=1.0, y_half_width=1.0,
        total_rays=500000, layout_rays=50,
        power_lumens=10.0, num_analysis_rays=500000
    )
    zos.set_nsc_position(source, x=0.0, y=0.0, z=0.0)

    # 2. Fold mirror at 45 degrees about Y, placed at Z=20
    TheNCE.InsertNewObjectAt(3)
    mirror = TheNCE.GetObjectAt(3)
    mirror.ChangeType(ZOSAPI.Editors.NCE.ObjectType.StandardRectangle)
    mirror.Material = 'MIRROR'
    zos.set_nsc_position(mirror, x=0.0, y=0.0, z=20.0)
    zos.set_nsc_orientation(mirror, tilt_x=0.0, tilt_y=-45.0, tilt_z=0.0)

    # 3. Detector: moved to intercept folded beam at X=-20
    det = zos.create_nsc_detector(
        2, detector_type='rectangle',
        x_half_width=15.0, y_half_width=15.0,
        pixels_x=300, pixels_y=300,
        material='ABSORB', comment='Detection Plane'
    )
    zos.set_nsc_position(det, x=-20.0, y=0.0, z=20.0)
    zos.set_nsc_orientation(det, tilt_x=0.0, tilt_y=45.0, tilt_z=0.0)

    # 4. Clear and trace
    TheNCE.ClearDetectors()
    tray = TheNCE.TraceAll()
    print("Ray trace complete.")

    # 5. Read detector
    w, h, data = zos.get_detector_data(2)
    print(f"Detector 2: {w}x{h}, "
          f"max={max(max(row) for row in data):.4f}")
```

## Notes

- **ALWAYS use `zos.set_nsc_orientation()` or `TiltAboutX/Y/Z`** —
  `TiltX`, `TiltY`, `TiltZ` are pythonnet traps — they silently create
  Python-only attributes Zemax never reads.
- Objects are 1-indexed in TheNCE.
- Default NSC system has 3 objects. Reconfigure rather than delete and re-add.
- Call `TheNCE.ClearDetectors()` before each `TraceAll()`.
- Use `TheNCE.TraceObject(n)` to trace only a specific source.
- `material='ABSORB'` is standard for detectors. For real materials,
  use a catalog glass name (requires loaded material catalog).
- For detector analysis, see the `nsc-analysis` skill.
- Source power: lumens for visible, watts for non-visible.
- Keep detector pixels under 512 per side — 200x200 suffices for most.
- Do NOT use `show=True` in `plot_detector_data()` inside a ZOS connection
  block — close the connection first with `zos.close()`.
