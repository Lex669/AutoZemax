---
name: non-sequential-modeling
description: This skill should be used when the user asks to "add NSC object", "configure non-sequential system", "add detector", "set up NSC source", "import CAD into Zemax", "configure bulk scattering", "edit NSC editor", "add NSC component", "modify non-sequential object", or works with the Non-Sequential Component editor.
version: 0.1.0
---

# Non-Sequential Mode — NSC Editor (NCE)

Configure non-sequential optical systems: objects, sources, detectors,
CAD imports, and bulk scattering properties.

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

## Accessing the NSC Editor

```python
with ZOSConnection() as zos:
    TheNCE = zos.TheSystem.NCE
    num_objects = TheNCE.NumberOfObjects
```

## Workflows

### Inspecting NSC Objects

```python
for i in range(1, TheNCE.NumberOfObjects + 1):
    obj = TheNCE.GetObjectAt(i)
    print(f"Object {i}: Type={obj.TypeName}, "
          f"Material={obj.Material}, "
          f"Pos=({obj.XPosition}, {obj.YPosition}, {obj.ZPosition})")
```

### Modifying Object Properties

```python
obj = TheNCE.GetObjectAt(2)  # Get second object

# Position
obj.XPosition = 10.0
obj.YPosition = 5.0
obj.ZPosition = 0.0

# Orientation (degrees) — MUST use TiltAboutX/Y/Z, NOT TiltX/Y/Z!
# Using TiltX/Y/Z will SILENTLY fail (pythonnet creates Python-only attributes
# without touching the .NET object)
obj.TiltAboutX = 0.0
obj.TiltAboutY = 0.0
obj.TiltAboutZ = 45.0

# Material
obj.Material = 'N-BK7'
```

### Accessing Detector Properties

**IMPORTANT**: Detector ObjectData properties (NumberXPixels, XHalfWidth, etc.)
can be WRITTEN immediately after object creation, but may NOT be readable
after saving and reloading the file. After reload, `obj.ObjectData` returns
`IObject` which lacks detector-specific attributes and raises `AttributeError`.

**Recommended approach** — read dimensions from the data array itself:

```python
det_obj = 4  # Detector is object #4

# Instead of reading ObjectData (may fail after reload), get the
# dimensions from the detector data array:
raw = TheNCE.GetAllDetectorDataSafe(det_obj, 1)
width = raw.GetLength(0)   # X pixels
height = raw.GetLength(1)  # Y pixels
print(f"Detector: {width}x{height} pixels")
```

**Setting detector properties** (write-only, works on newly created objects):

```python
obj = TheNCE.GetObjectAt(det_obj)
obj.ObjectData.XHalfWidth = 3.0
obj.ObjectData.YHalfWidth = 3.0
obj.ObjectData.NumberXPixels = 200
obj.ObjectData.NumberYPixels = 200
# These values may not persist through save/load cycles.
# For reliable persistence, set them in the Zemax UI after saving.
```

### Reading Detector Data (Pixel-by-Pixel)

```python
# Read all pixel data from a detector
detector_data = [[0 for x in range(num_y_pixels)] for x in range(num_x_pixels)]
pix = 0
for x in range(num_y_pixels):
    for y in range(num_x_pixels):
        ret, pixel_val = TheNCE.GetDetectorData(det_obj, pix, 1, 0)
        pix += 1
        if ret == 1:
            detector_data[y][x] = pixel_val
        else:
            detector_data[y][x] = -1
```

### Opening NSC Files

NSC files are opened like any .zos file:

```python
zos.open_file(zos.samples_dir() +
    "\\Non-sequential\\Miscellaneous\\Digital_projector_flys_eye_homogenizer.zos",
    False)
```

## Converting Sequential to NSC

```python
convert_tool = zos.TheSystem.Tools.OpenConvertToNSCGroup()
convert_tool.ConvertFileToNSC = True
convert_tool.RunAndWaitForCompletion()
convert_tool.Close()

# Save as NSC file
zos.save_file(output_dir + "\\system_nsc.zos")
```

## NSC Object Type Quick Reference

Choosing the right object type for each role is critical. Using the wrong
type will produce SILENT failures (no rays reach the detector).

### Mirrors
- **USE**: `Rectangle` + `Material = 'MIRROR'` (flat mirror)
- **DO NOT USE**: `StandardLens` + `Material = 'MIRROR'`
  `StandardLens` is a refractive element in NSC; setting Material='MIRROR'
  does NOT make it reflective — rays will pass through or be absorbed.

```python
mirror = TheNCE.GetObjectAt(3)
mirror.ChangeType(mirror.GetObjectTypeSettings(
    ZOSAPI.Editors.NCE.ObjectType.Rectangle))
mirror.Material = 'MIRROR'
mirror.TiltAboutY = 90.0  # Face normal along X axis
```

### Beam Splitters
- **USE**: `PolygonObject` with `splitter.pob` (has built-in 50% coating)
  Available in `<ZemaxData>\Objects\Polygon Objects\splitter.pob`
- **ALTERNATIVE**: `RectangularVolume` + coating on specific face
  (requires `FaceList` configuration — complex)

```python
bs = TheNCE.GetObjectAt(2)
bs.ChangeType(bs.GetObjectTypeSettings(
    ZOSAPI.Editors.NCE.ObjectType.PolygonObject))
bs.Material = 'N-BK7'
bs.ObjectData.Filename = 'splitter.pob'  # Has 50:50 coating baked in
bs.TiltAboutX = -45.0  # Orient at 45 deg to beam
```

### Detectors
- **USE**: `DetectorRectangle` + `Material = 'ABSORB'`
- For coherent detection (interference), read with `GetAllCoherentDataSafe`

### Source Options
- `SourcePoint` — point source, configurable cone angle
- `SourceRectangle` — extended area source
- For coherence/interference: set a single wavelength, use many analysis rays

## Notes

- NSC mode models light as rays interacting with 3D objects
- Sources emit rays, objects interact with them, detectors capture results
- `GetDetectorData` parameters: (object_number, pixel_index, data_type, flux)
  - data_type: 0 = incoherent irradiance, 1 = coherent, etc.
- CAD files (STEP, IGES, etc.) can be imported as NSC objects
- Bulk scattering requires defining scattering properties on materials
