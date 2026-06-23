---
name: nsc-scattering
description: This skill should be used when the user asks to "NSC scattering", "bulk scatter", "phosphor", "volume scattering", "scatter model", "Mie scattering", "scatter function", "white LED", "phosphor layer", "NSC bulk scatter", "Rayleigh scattering", or configures non-sequential scattering models and phosphor layers for LED and lighting simulation in Zemax OpticStudio.
version: 0.2.0
---

# NSC Scattering — Bulk Scatter, Phosphor & Volume Physics

Configure non-sequential scattering models for lighting and illumination
simulation. Covers bulk scattering (Mie, Rayleigh), phosphor modeling for
white LEDs with excitation/emission spectra, volume physics objects,
and scatter function definitions. Corresponds to ZOS-API Samples 17 and 21.

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

## Scattering Models Overview

NSC supports three categories of scattering:

| Model | Object Type | Description |
|-------|-------------|-------------|
| Surface Scattering | Any NSC object | Scatter at surface interface (roughness) |
| Bulk Scattering | Volume objects | Scatter inside the volume (particles, phosphor) |
| Gradient Index | Volume objects | Index varies with position |

This skill covers **bulk scattering** — volume objects with embedded
particles or phosphor materials.

## Configuring Bulk Scatter on Volume Objects

Bulk scattering applies to objects with volume extent. The scatter model
is set via the object's scatter function properties.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    zos.new_file(ZOSAPI.SystemType.NonSequential)
    TheNCE = zos.TheSystem.NCE

    # Insert a volume object to serve as the scattering medium
    TheNCE.InsertNewObjectAt(3)
    vol = TheNCE.GetObjectAt(3)
    vol.ChangeType(ZOSAPI.Editors.NCE.ObjectType.VolumePhysics)
    vol.Material = 'N-BK7'

    # Set volume dimensions
    vol.GetCellAt(1).DoubleValue = 10.0   # X half-width (mm)
    vol.GetCellAt(2).DoubleValue = 10.0   # Y half-width (mm)
    vol.GetCellAt(3).DoubleValue = 5.0    # Z half-width (mm)
    vol.GetCellAt(4).IntegerValue = 20    # X pixels
    vol.GetCellAt(5).IntegerValue = 20    # Y pixels
    vol.GetCellAt(6).IntegerValue = 10    # Z voxels

    # Enable bulk scattering
    # Cell 7 = scatter model (0=off, 1=Mie, 2=Rayleigh, 3=user-defined)
    vol.GetCellAt(7).IntegerValue = 1     # Mie scattering

    # Set scattering coefficient (mm^-1)
    vol.GetCellAt(8).DoubleValue = 2.0    # Scattering coefficient

    # Set anisotropy factor g (Mie only)
    # g = 0 isotropic, g > 0 forward-peaked, g < 0 backward-peaked
    vol.GetCellAt(9).DoubleValue = 0.85   # Forward-scattering

    # Set absorption coefficient (mm^-1)
    vol.GetCellAt(10).DoubleValue = 0.1   # Absorption coefficient

    print("Bulk scatter volume configured")
```

### Volume Physics Cell Reference

| Cell | Parameter | Description |
|------|-----------|-------------|
| 1 | X Half-Width | Volume extent in X (mm) |
| 2 | Y Half-Width | Volume extent in Y (mm) |
| 3 | Z Half-Width | Volume extent in Z (mm) |
| 4 | X Voxels | Number of X bins |
| 5 | Y Voxels | Number of Y bins |
| 6 | Z Voxels | Number of Z bins |
| 7 | Scatter Model | 0=Off, 1=Mie, 2=Rayleigh, 3=User |
| 8 | Scattering Coeff | Scattering probability per mm |
| 9 | Anisotropy (g) | -1 to 1 (Mie only) |
| 10 | Absorption Coeff | Absorption probability per mm |

## Mie vs Rayleigh Scattering

Choose the scatter model based on particle size relative to wavelength:

### Mie Scattering (particle size ~ wavelength)

Configured with scatter model = 1. Requires anisotropy factor `g`:

- `g = 0`: Isotropic scattering (equal in all directions)
- `g = 0.3..0.5`: Mild forward bias (small particles)
- `g = 0.7..0.9`: Strong forward bias (larger particles)
- `g = -0.3..-0.5`: Backward bias

```python
# Mie scattering — strong forward peak (common for phosphor layers)
vol.GetCellAt(7).IntegerValue = 1    # Mie model
vol.GetCellAt(8).DoubleValue = 5.0   # High scattering coefficient
vol.GetCellAt(9).DoubleValue = 0.9   # Strong forward anisotropy
vol.GetCellAt(10).DoubleValue = 0.05 # Low absorption
```

### Rayleigh Scattering (particle size << wavelength)

Configured with scatter model = 2. No anisotropy factor (inherently
isotropic with wavelength-dependent cross-section ~ 1/lambda^4):

```python
# Rayleigh scattering — blue light scatters more than red
vol.GetCellAt(7).IntegerValue = 2    # Rayleigh model
vol.GetCellAt(8).DoubleValue = 3.0   # Scattering coefficient (at reference lambda)
vol.GetCellAt(10).DoubleValue = 0.01 # Very low absorption
```

## Phosphor Modeling for White LEDs

Phosphor layers convert short-wavelength light (blue LED) to longer
wavelengths (yellow/red) to produce white light. This requires a
phosphor material definition and a VolumePhysics or DetectorVolume
object with the phosphor properties.

### Step 1: Configure the Volume Physics Object as Phosphor

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheNCE = zos.TheSystem.NCE

    # Volume physics object at position 3
    phosphor = TheNCE.GetObjectAt(3)

    # Set as DetectorVolume for phosphor analysis
    phosphor.ChangeType(ZOSAPI.Editors.NCE.ObjectType.DetectorVolume)
    phosphor.GetCellAt(1).DoubleValue = 5.0    # X half-width
    phosphor.GetCellAt(2).DoubleValue = 5.0    # Y half-width
    phosphor.GetCellAt(3).DoubleValue = 0.5    # Z half-width (thin layer)
    phosphor.GetCellAt(4).IntegerValue = 30    # X pixels
    phosphor.GetCellAt(5).IntegerValue = 30    # Y pixels
    phosphor.GetCellAt(6).IntegerValue = 5     # Z voxels

    # Set material to a phosphor glass
    phosphor.Material = 'N-BK7'

    # Enable phosphor scattering model
    phosphor.GetCellAt(7).IntegerValue = 4     # Phosphor model
    phosphor.GetCellAt(8).DoubleValue = 20.0   # Scattering coefficient
    phosphor.GetCellAt(9).DoubleValue = 0.85   # Anisotropy (Mie component)
    phosphor.GetCellAt(10).DoubleValue = 0.5   # Absorption coefficient

    # Phosphor-specific cells
    phosphor.GetCellAt(11).IntegerValue = 1    # Use predefined phosphor
    phosphor.GetCellAt(12).IntegerValue = 1    # Phosphor material index
```

### Step 2: Configure Blue LED Source for Phosphor Excitation

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    TheNCE = TheSystem.NCE

    # Configure source as a blue LED
    source = TheNCE.GetObjectAt(1)
    source.GetCellAt(3).IntegerValue = 1       # Wavelength 1
    source.GetCellAt(8).DoubleValue = 1.0      # Power (watts)
    source.GetCellAt(14).IntegerValue = 1      # Number of wavelengths

    # Set system wavelengths for blue + phosphor emission
    SD = TheSystem.SystemData
    SD.Wavelengths.RemoveWavelengths(1, SD.Wavelengths.NumberOfWavelengths)
    SD.Wavelengths.AddWavelength(0.450, 1.0)   # Blue pump (450 nm)
    SD.Wavelengths.AddWavelength(0.555, 1.0)   # Green phosphor (555 nm)
    SD.Wavelengths.AddWavelength(0.610, 1.0)   # Red phosphor (610 nm)
```

### Step 3: Configure Detector for Phosphor Output

```python
# Detector captures the converted white light
det = TheNCE.GetObjectAt(2)
det.Material = 'ABSORB'
det.GetCellAt(4).IntegerValue = 200  # X pixels
det.GetCellAt(5).IntegerValue = 200  # Y pixels
```

### Step 4: Trace and Read Phosphor Results

```python
with ZOSConnection() as zos:
    TheNCE = zos.TheSystem.NCE

    TheNCE.ClearDetectors()
    TheNCE.TraceAll()

    # Read detector data for each wavelength
    for wave_idx in range(1, 4):
        # Read incoherent irradiance for specific wavelength
        w, h, data = zos.get_detector_data(2, data_type=0)
        total = sum(sum(row) for row in data)
        print(f"Wavelength {wave_idx}: total power = {total:.4f}")

    # Read phosphor volume detector data
    w_p, h_p, z_p, vol_data = \
        zos.TheSystem.NCE.GetDetectorData(3)  # Volume detector
    print(f"Volume detector: {w_p}x{h_p}x{z_p} voxels")
```

## Scatter Function via Object Properties

For surface scattering (rough surfaces), configure via the object's
scatter function properties rather than volume physics:

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheNCE = zos.TheSystem.NCE

    obj = TheNCE.GetObjectAt(1)

    # Access scatter function through object properties
    # ObjectData.Scattering provides control over surface scatter
    obj_data = obj.ObjectData

    # Lambertian scatter (diffuse surface)
    scatter_type = ZOSAPI.Editors.NCE.ObjectScatterData.ScatteringModel.Lambertian
    obj_data.Scattering.ScatteringModel = scatter_type

    # Number of scatter rays
    obj_data.Scattering.NumberOfScatterRays = 100

    # Scatter fraction (0 = no scatter, 1 = fully diffuse)
    # obj_data.Scattering.ScatterFraction = 1.0
```

## White LED Phosphor — Complete Example

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    TheNCE = TheSystem.NCE

    # 1. Configure system wavelengths
    SD = TheSystem.SystemData
    SD.Wavelengths.RemoveWavelengths(1, SD.Wavelengths.NumberOfWavelengths)
    SD.Wavelengths.AddWavelength(0.450, 1.0)   # Blue pump
    SD.Wavelengths.AddWavelength(0.550, 1.0)   # Green
    SD.Wavelengths.AddWavelength(0.620, 1.0)   # Red

    # 2. Configure source (blue LED)
    source = TheNCE.GetObjectAt(1)
    source.ChangeType(ZOSAPI.Editors.NCE.ObjectType.SourceElliptical)
    source.GetCellAt(1).DoubleValue = 0.5
    source.GetCellAt(2).DoubleValue = 0.5
    source.GetCellAt(8).DoubleValue = 1.0    # 1 watt optical power
    source.GetCellAt(3).IntegerValue = 1     # Use wavelength 1

    # 3. Insert phosphor volume
    TheNCE.InsertNewObjectAt(3)
    phosphor = TheNCE.GetObjectAt(3)
    phosphor.ChangeType(ZOSAPI.Editors.NCE.ObjectType.DetectorVolume)
    phosphor.Material = 'N-BK7'
    phosphor.GetCellAt(1).DoubleValue = 3.0
    phosphor.GetCellAt(2).DoubleValue = 3.0
    phosphor.GetCellAt(3).DoubleValue = 0.3
    phosphor.GetCellAt(4).IntegerValue = 20
    phosphor.GetCellAt(5).IntegerValue = 20
    phosphor.GetCellAt(6).IntegerValue = 5

    # Phosphor scatter mode
    phosphor.GetCellAt(7).IntegerValue = 4    # Phosphor model
    phosphor.GetCellAt(8).DoubleValue = 10.0  # Scattering coefficient
    phosphor.GetCellAt(10).DoubleValue = 2.0  # Absorption coefficient
    phosphor.GetCellAt(11).IntegerValue = 1   # Use predefined phosphor
    zos.set_nsc_position(phosphor, x=0, y=0, z=10)

    # 4. Position detector
    det = TheNCE.GetObjectAt(2)
    det.GetCellAt(1).DoubleValue = 5.0
    det.GetCellAt(2).DoubleValue = 5.0
    det.GetCellAt(4).IntegerValue = 100
    det.GetCellAt(5).IntegerValue = 100
    zos.set_nsc_position(det, x=0, y=0, z=25)

    # 5. Trace and read per-wavelength results
    TheNCE.ClearDetectors()
    TheNCE.TraceAll()

    for wl_idx in range(1, 4):
        wl = SD.Wavelengths.GetWavelength(wl_idx)
        w, h, data = zos.get_detector_data(2, data_type=0)
        total = sum(sum(r) for r in data)
        print(f"Lambda {wl.Wavelength:.3f} um: total power = {total:.6f}")
```

## Notes

- **Phosphor model (cell 7 = 4) requires a DetectorVolume or VolumePhysics
  object** — standard DetectorRectangle objects do not support bulk
  scattering or phosphor conversion.
- The phosphor model simulates absorption of short-wavelength light and
  re-emission at longer wavelengths. This means **at least two wavelengths
  are needed**: one for excitation (blue, ~450 nm) and one or more for
  emission (green/yellow/red).
- `Cell 11` (use predefined phosphor) = 1 selects a built-in phosphor
  material. Set to 0 for a user-defined phosphor with custom excitation
  and emission spectra.
- Scattering and absorption coefficients are in units of mm^-1. A
  coefficient of 1.0 means a ray has a ~63% chance of interacting within
  1 mm of travel.
- **Mie anisotropy `g` ranges from -1 to 1**. Common values:
  - 0.85-0.95: strongly forward-scattering (phosphor layers, tissue)
  - 0.5-0.7: moderately forward (fog, clouds)
  - 0: isotropic (Rayleigh limit)
  - -0.3 to -0.5: backward-scattering (some paints)
- **Rayleigh scattering coefficient is wavelength-dependent** —
  Zemax scales it as 1/lambda^4 internally. Set the coefficient at the
  reference wavelength.
- For surface scattering (Lambertian, Gaussian, etc.), use
  `ObjectData.Scattering` instead of volume physics cells.
- **DetectorVolume** records absorbed power per voxel, useful for
  analyzing absorption distribution within the phosphor layer.
- `TheNCE.ClearDetectors()` resets both 2D and 3D (volume) detector
  data. Call it before each trace to avoid accumulation.
- For visualization of detector results, see the `data-processing`
  and `nsc-analysis` skills.
- Bulk scattering significantly increases ray trace time —
  reduce `NumberOfAnalysisRays` or increase `ScatteringCoefficient`
  for faster debugging, then increase for final simulation.
