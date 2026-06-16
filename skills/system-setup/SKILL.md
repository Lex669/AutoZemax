---
name: system-setup
description: This skill should be used when the user asks to "create a new lens system", "set up an optical system", "load a Zemax file", "open a .zos file", "set aperture", "configure wavelengths", "set field points", "configure system parameters", "create a new optical design", or mentions initializing or setting up a Zemax optical system.
version: 0.1.0
---

# Zemax System Setup

Create new optical systems and configure fundamental parameters: aperture,
fields, wavelengths, and material catalogs. Also handles loading existing
.zos files and saving.

## Prerequisites

All scripts must import the shared connection utility:

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

Execute scripts with the environment Python:

```
the Python interpreter (see `references/environment.md` for path)
```

See `references/environment.md` for full environment details.
See `references/zos-api-reference.md` for API class documentation.

## Workflow

### Creating a New System

1. Create a ZOSConnection (context manager or explicit connect/close)
2. Call `zos.new_file()` or `TheSystem.New(False)`
3. Configure SystemData in order: Aperture → Fields → Wavelengths
4. Add material catalogs
5. Save with `zos.save_file(path)`

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    TheApplication = zos.TheApplication

    # Create new file
    TheSystem.New(False)
    output_path = zos.ensure_api_dir() + "\\my_system.zos"
    TheSystem.SaveAs(output_path)

    # Add material catalog (SCHOTT is standard)
    TheSystem.SystemData.MaterialCatalogs.AddCatalog('SCHOTT')

    # Configure aperture
    TheSystemData = TheSystem.SystemData
    TheSystemData.Aperture.ApertureValue = 40  # mm

    # For aperture type changes:
    # TheSystemData.Aperture.ApertureType = ZOSAPI.SystemData.ApertureType.FloatByStopSize
```

### Configuring Field Points

```python
# Access existing field and modify
field_1 = TheSystemData.Fields.GetField(1)
field_1.X = 0.0
field_1.Y = 0.0

# Add new field points (X, Y, Weight)
field_2 = TheSystemData.Fields.AddField(0.0, 5.0, 1.0)
field_3 = TheSystemData.Fields.AddField(0.0, 7.0, 1.0)

# Get field type
field_type = TheSystemData.Fields.GetFieldType()
# Returns: Angle, ObjectHeight, ParaxialImageHeight, or RealImageHeight
```

### Configuring Wavelengths

```python
# Use a standard preset
TheSystemData.Wavelengths.SelectWavelengthPreset(
    ZOSAPI.SystemData.WavelengthPreset.d_0p587  # d-line 587.6 nm
)

# Common presets:
# d_0p587, F_0p486, C_0p656 (visible)
# N_0p880, N_1p310, N_1p550 (NIR)

# Access individual wavelengths
num_waves = TheSystemData.Wavelengths.NumberOfWavelengths
for i in range(1, num_waves + 1):
    wavelength = TheSystemData.Wavelengths.GetWavelength(i)
    print(f"λ{i}: {wavelength.Wavelength} µm, weight: {wavelength.Weight}")
```

### Loading Existing Files

```python
with ZOSConnection() as zos:
    # Load from samples
    test_file = zos.samples_dir() + "\\Sequential\\Objectives\\Double Gauss 28 degree field.zos"
    zos.open_file(test_file, False)  # False = don't save if needed

    # Or load arbitrary path
    zos.open_file("C:\\path\\to\\design.zos", False)
```

### Saving

```python
# Save to current file
TheSystem.Save()

# Save as new file
TheSystem.SaveAs("C:\\path\\to\\new_design.zos")
```

## Important Notes

- Aperture, fields, and wavelengths must be configured before adding surfaces
- The optical system is empty after `New(False)` — only the object surface and image surface exist
- Always add a material catalog (typically SCHOTT) before assigning materials to surfaces
- Use `zos.ensure_api_dir()` to get a writable output directory under Samples/API/Python
