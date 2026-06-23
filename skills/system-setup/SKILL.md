---
name: system-setup
description: This skill should be used when the user asks to "create new file", "load zmx file", "open zemax file", "set aperture", "set field", "add wavelength", "configure system explorer", "select wavelength preset", "add material catalog", "check license", "verify zemax", "connect to zemax", "new optical system", "import system", "system preferences", "get zemax version", or initializes and configures a new or existing Zemax optical system.
version: 0.2.0
---

# System Setup — New Files, Loading, System Explorer

Create new optical systems in sequential and non-sequential modes, load
existing .zos/.zmx/.zda files, configure System Explorer (aperture, fields,
wavelengths), manage material catalogs, check license status, and read
system preferences.

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
from zos_utils import ZOSConnection, set_seed, ensure_zmx_dir

set_seed(42)
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## Creating New Systems

### Sequential System

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # Create default sequential system
    TheSystem.New(False)

    # Add material catalog first
    TheSystem.SystemData.MaterialCatalogs.AddCatalog('SCHOTT')

    # Configure SystemData in order: Aperture -> Fields -> Wavelengths
    TheSystem.SystemData.Aperture.ApertureValue = 40.0

    # Validate before editing surfaces
    zos.validate_system_ready(require_surfaces=False)

    # Save to zmx/ output folder
    output_path = zos.ensure_zmx_dir() + "\\new_system.zmx"
    zos.save_file(output_path)
    print(f"Saved: {output_path}")
```

### Non-Sequential System

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI

    # Create NSC system directly via library wrapper
    zos.new_file(ZOSAPI.SystemType.NonSequential)

    TheNCE = zos.TheSystem.NCE
    print(f"NSC system ready — {TheNCE.NumberOfObjects} objects")
```

### Creating a New NSC System (alternative)

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    TheApplication = zos.TheApplication

    # Create via TheApplication
    TheSystem = TheApplication.CreateNewSystem(
        ZOSAPI.SystemType.NonSequential
    )
```

## Loading Existing Files

```python
with ZOSConnection() as zos:
    # Load from Zemax samples directory
    samples_file = zos.samples_dir() + \
        "\\Sequential\\Objectives\\Double Gauss 28 degree field.zos"
    zos.open_file(samples_file, False)
    print(f"Loaded: {samples_file}")

    # Load from arbitrary path
    zos.open_file("C:\\path\\to\\design.zmx")

    # Load .zda analysis data file
    zos.open_file("C:\\path\\to\\results.zda")
```

## Configuring System Explorer

### Aperture

```python
SD = TheSystem.SystemData

# Set aperture type
SD.Aperture.ApertureType = ZOSAPI.SystemData.ApertureType.EntrancePupilDiameter

# Set aperture value (entrance pupil diameter in mm)
SD.Aperture.ApertureValue = 40.0

# Apodization type
SD.Aperture.ApodizationType = ZOSAPI.SystemData.ApodizationType.Gaussian
SD.Aperture.ApodizationFactor = 1.0
```

### Fields

```python
# Access and modify first field
field_1 = SD.Fields.GetField(1)
field_1.X = 0.0
field_1.Y = 0.0
field_1.Weight = 1.0

# Add new field points (X, Y, Weight)
SD.Fields.AddField(0.0, 5.0, 1.0)
SD.Fields.AddField(0.0, 10.0, 1.0)

# Get field type
field_type = SD.Fields.GetFieldType()
print(f"Field type: {field_type}")

# Change field type
SD.Fields.SetFieldType(ZOSAPI.SystemData.FieldType.Angle)
SD.Fields.SetFieldType(ZOSAPI.SystemData.FieldType.ObjectHeight)
```

### Wavelengths

```python
# Standard visible preset (587.6 nm)
SD.Wavelengths.SelectWavelengthPreset(
    ZOSAPI.SystemData.WavelengthPreset.d_0p587
)

# Other common presets:
# F_0p486   — 486.1 nm (F-line, blue)
# C_0p656   — 656.3 nm (C-line, red)
# HeNe_0p633 — 632.8 nm (HeNe laser)
# N_0p880   — 880 nm (NIR)
# N_1p310   — 1310 nm (NIR telecom)
# N_1p550   — 1550 nm (NIR telecom)

# Manual wavelength configuration
SD.Wavelengths.RemoveWavelengths(1, SD.Wavelengths.NumberOfWavelengths)
SD.Wavelengths.AddWavelength(0.486, 1.0)  # F-line, weight 1.0
SD.Wavelengths.AddWavelength(0.587, 1.0)  # d-line, weight 1.0
SD.Wavelengths.AddWavelength(0.656, 1.0)  # C-line, weight 1.0

# Read back wavelengths
for i in range(1, SD.Wavelengths.NumberOfWavelengths + 1):
    wl = SD.Wavelengths.GetWavelength(i)
    print(f"  Lambda {i}: {wl.Wavelength} um, weight={wl.Weight}")
```

## Material Catalog Management

```python
# Add standard catalogs
SD.MaterialCatalogs.AddCatalog('SCHOTT')
SD.MaterialCatalogs.AddCatalog('OHARA')
SD.MaterialCatalogs.AddCatalog('HOYA')
SD.MaterialCatalogs.AddCatalog('CDGM')

# List loaded catalogs
n_cats = SD.MaterialCatalogs.NumberOfCatalogs
print(f"Loaded {n_cats} material catalogs:")
for i in range(n_cats):
    cat = SD.MaterialCatalogs.GetCatalog(i)
    print(f"  [{i}] {cat.Name}")
```

## License Checking

```python
with ZOSConnection() as zos:
    # Use library wrapper for human-readable status
    status = zos.license_status()
    print(f"Zemax License: {status}")
    # Returns: "Premium", "Professional", "Standard", or "Invalid"

    # Or check directly via API
    if zos.TheApplication.IsValidLicenseForAPI:
        edition = zos.TheApplication.LicenseStatus
        print(f"License edition code: {edition}")
    else:
        print("WARNING: License not valid for ZOS-API")
```

## System Preferences & Version

```python
# Read Zemax version string
version = zos.TheApplication.ZemaxVersionString
print(f"Zemax Version: {version}")

# Access System Preferences
prefs = TheSystem.SystemData.Preferences

# Ray aiming
ray_aiming = TheSystem.SystemData.RayAiming
ray_aiming.RayAimingType = ZOSAPI.SystemData.RayAimingType.Real
ray_aiming.PupilSampling = ZOSAPI.SystemData.PupilSamplingType.S_6

# Pupil obscuration settings (for systems with central obstruction)
pupil = TheSystem.SystemData.Pupil
# pupil.ObscurationType, pupil.ObscurationValue as needed

# Glass catalogs path
catalog_path = zos.objects_dir() + "\\Glasscats\\"
print(f"Glass catalogs: {catalog_path}")
```

## Quick Reference

### Aperture Types

| Type (ApertureType) | Description |
|---------------------|-------------|
| EntrancePupilDiameter | Stop surface = ApertureValue |
| ImageSpaceFNumber | F/# in image space |
| ObjectSpaceNA | NA in object space |
| FloatByStopSize | Defined by stop surface semi-diameter |
| ParaxialWorkingFNumber | Paraxial working F/# |
| ObjectSpaceNumericalAperture | NA in object space |

### Field Types

| Type (FieldType) | Description |
|------------------|-------------|
| Angle | Angular field (degrees) |
| ObjectHeight | Object height (lens units) |
| ParaxialImageHeight | Paraxial image height (lens units) |
| RealImageHeight | Real image height (lens units) |

### Common Wavelength Presets

| Preset | Lambda (nm) | Description |
|--------|-------------|-------------|
| d_0p587 | 587.6 | Helium d-line (visible reference) |
| F_0p486 | 486.1 | Hydrogen F-line (blue) |
| C_0p656 | 656.3 | Hydrogen C-line (red) |
| HeNe_0p633 | 632.8 | HeNe laser |
| N_0p880 | 880 | NIR |
| N_1p310 | 1310 | Telecom NIR |
| N_1p550 | 1550 | Telecom NIR |

## Notes

- Always configure aperture, fields, and wavelengths BEFORE inserting surfaces or assigning materials
- Call `zos.validate_system_ready(require_surfaces=False)` after initial configuration to catch missing settings early
- Add material catalogs (SCHOTT, OHARA, HOYA, CDGM) before assigning glass types to surfaces
- NSC files load identically to sequential files via `zos.open_file()` — the system type is embedded in the file
- Use `zos.samples_dir()` to locate built-in Zemax samples; use `zos.ensure_zmx_dir()` to create writable zmx/ output directory
- License must be valid for ZOS-API scripting — `zos.license_status()` provides human-readable check
- After loading a file, verify it loaded correctly by checking `TheSystem.SystemData.Aperture.ApertureValue`
