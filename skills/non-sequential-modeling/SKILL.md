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
# Use CLAUDE_PLUGIN_ROOT set by Claude Code at runtime
_plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
if _plugin_root:
    sys.path.insert(0, os.path.join(_plugin_root, 'scripts'))
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

# Orientation (degrees)
obj.TiltX = 0.0
obj.TiltY = 0.0
obj.TiltZ = 45.0

# Material
obj.Material = 'N-BK7'
```

### Accessing Detector Properties

Detector objects have pixel data accessible via ObjectData:

```python
det_obj = 4  # Detector is object #4
obj = TheNCE.GetObjectAt(det_obj)

num_x_pixels = obj.ObjectData.NumberXPixels
num_y_pixels = obj.ObjectData.NumberYPixels
x_half_width = obj.ObjectData.XHalfWidth
y_half_width = obj.ObjectData.YHalfWidth

print(f"Detector: {num_x_pixels}x{num_y_pixels} pixels")
print(f"Size: {2*x_half_width} x {2*y_half_width} mm")
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

## Notes

- NSC mode models light as rays interacting with 3D objects
- Sources emit rays, objects interact with them, detectors capture results
- `GetDetectorData` parameters: (object_number, pixel_index, data_type, flux)
  - data_type: 0 = incoherent irradiance, 1 = coherent, etc.
- CAD files (STEP, IGES, etc.) can be imported as NSC objects
- Bulk scattering requires defining scattering properties on materials
