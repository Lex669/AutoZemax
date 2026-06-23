---
name: cad-exchange
description: This skill should be used when the user asks to "export CAD", "import CAD", "STEP file", "IGES export", "CAD exchange", "STL export", "SAT file", "export to STEP", "import CAD model", "CAD format", "open CAD file in NSC", "export solid model", or exchanges CAD geometry between Zemax OpticStudio and mechanical CAD packages.
version: 0.2.0
---

# CAD Exchange — Export & Import (STEP, IGES, SAT, STL)

Export optical system geometry to CAD file formats for mechanical
integration, and import CAD models into the Non-Sequential Component (NSC)
editor for stray light analysis or system integration. Uses the library
wrappers `zos.export_cad()` and `zos.import_cad()`.
Corresponds to ZOS-API Samples 09 and 20.

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

## Supported CAD Formats

| Format | Library Tag | Extension | Best For |
|--------|-------------|-----------|----------|
| STEP | `'STEP'` | .step / .stp | General CAD exchange (recommended) |
| IGES | `'IGES'` | .iges / .igs | Legacy CAD interop |
| SAT | `'SAT'` | .sat | ACIS-based CAD (SolidWorks, etc.) |
| STL | `'STL'` | .stl | 3D printing, meshing |

## CAD Export

The library wrapper `zos.export_cad()` handles tool creation, format
mapping, and cleanup. Two parameters control the output:

- `solids_only=True` — export lens volumes as solid bodies; `False`
  produces trimmed surfaces
- `cad_format` — one of `'STEP'`, `'IGES'`, `'SAT'`, `'STL'`

### Basic Export (NSC System)

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI

    # Load an NSC system
    zos.open_file(zos.samples_dir() +
        "\\Non-Sequential\\Miscellaneous\\Digital_projector_flys_eye_homogenizer.zos")

    # Export to STEP (solids, recommended)
    output_path = ensure_zmx_dir() + "\\exported_model.step"
    result = zos.export_cad(
        filename=output_path,
        cad_format='STEP',
        solids_only=True
    )
    print(f"Exported to: {result}")
```

### Export to Multiple Formats

```python
with ZOSConnection() as zos:
    zos.open_file(zos.samples_dir() +
        "\\Non-Sequential\\Miscellaneous\\Digital_projector_flys_eye_homogenizer.zos")

    base = ensure_zmx_dir() + "\\projector"

    # Export all four formats
    for fmt in ['STEP', 'IGES', 'SAT', 'STL']:
        ext = {'STEP': '.step', 'IGES': '.igs', 'SAT': '.sat', 'STL': '.stl'}
        path = f"{base}{ext[fmt]}"
        zos.export_cad(filename=path, cad_format=fmt, solids_only=True)
        print(f"Exported: {path}")
```

### Export with Surface Tessellation

For finer control over tessellation quality (spline segments and CAD
tolerance), use the raw export tool directly:

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    export = TheSystem.Tools.OpenExportCAD()
    try:
        export.OutputFileName = ensure_zmx_dir() + "\\high_quality.step"
        export.FileType = ZOSAPI.Tools.General.CADFileType.STEP

        # Spline quality
        export.SplineSegments = ZOSAPI.Tools.General.SplineSegmentsType.N_128

        # CAD tolerance
        export.Tolerance = ZOSAPI.Tools.General.CADToleranceType.N_TenEMinus5

        # Object range
        export.FirstObject = 1
        export.LastObject = TheSystem.NCE.NumberOfObjects

        # Solids or surfaces
        export.SurfacesAsSolids = True

        # Multi-configuration handling
        export.SetCurrentConfiguration()

        export.Run()
        status = export.WaitWithTimeout(180.0)

        if status == ZOSAPI.Tools.RunStatus.Completed:
            print("High-quality CAD export completed.")
        else:
            print(f"Export status: {status}")
    finally:
        export.Close()
```

### Spline Segment Quality Reference

| Enum | Segments | File Size | Quality |
|------|----------|-----------|---------|
| N_032 | 32 | Small | Draft |
| N_064 | 64 | Medium | Standard |
| N_128 | 128 | Large | High |
| N_256 | 256 | Very large | Maximum |

### CAD Tolerance Reference

| Enum | Value | Use Case |
|------|-------|----------|
| N_TenEMinus4 | 1e-4 | Standard mechanical tolerance |
| N_TenEMinus5 | 1e-5 | Precision optics |
| N_TenEMinus6 | 1e-6 | High-precision surfaces |
| N_TenEMinus7 | 1e-7 | Maximum precision (large files) |

## CAD Import (NSC)

The library wrapper `zos.import_cad()` imports CAD files directly into
the Non-Sequential Component editor. The imported part becomes an NSC
object that can be assigned a material, positioned, and included in
non-sequential ray traces.

### Basic Import

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI

    # Create a new NSC system for the imported CAD
    zos.new_file(ZOSAPI.SystemType.NonSequential)

    # Import a STEP file as object 1
    cad_obj = zos.import_cad(
        filename=r"C:\CAD\models\lens_holder.step",
        cad_format='STEP',
        obj_number=1,
        material='MIRROR'  # Reflects rays
    )

    print(f"Imported: {cad_obj.Comment} at object 1")

    # Position the imported part
    zos.set_nsc_position(cad_obj, x=0.0, y=0.0, z=50.0)
    zos.set_nsc_orientation(cad_obj, tilt_x=0.0, tilt_y=0.0, tilt_z=0.0)
```

### Import with Different Materials & Formats

The material assignment determines how rays interact with the imported CAD.
Pass any supported format tag in `cad_format`:

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    zos.new_file(ZOSAPI.SystemType.NonSequential)
    TheNCE = zos.TheSystem.NCE

    # Import multiple CAD parts with different materials and formats
    imports = [
        (1, 'MIRROR',  r'C:\CAD\mirror.step',     'STEP'),
        (2, 'ABSORB',  r'C:\CAD\housing.iges',     'IGES'),
        (3, 'N-BK7',   r'C:\CAD\lens_body.sat',    'SAT'),
        (4, 'MIRROR',  r'C:\CAD\mesh_part.stl',    'STL'),
    ]

    for obj_num, material, cad_file, fmt in imports:
        if obj_num > 1:
            TheNCE.InsertNewObjectAt(obj_num)
        cad_obj = zos.import_cad(
            filename=cad_file,
            cad_format=fmt,
            obj_number=obj_num,
            material=material
        )
        print(f"Object {obj_num}: {fmt} / {material}")

    # Verify imported objects
    for i in range(1, TheNCE.NumberOfObjects + 1):
        obj = TheNCE.GetObjectAt(i)
        print(f"  {i}: {obj.Comment} [{obj.Material}]")
```

## Sequential to CAD Export Workflow

Sequential systems must be converted to NSC before CAD export:

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # 1. Load a sequential design
    zos.open_file(zos.samples_dir() +
        "\\Sequential\\Objectives\\Cooke 40 degree field.zos")

    # 2. Convert to NSC group
    convert = TheSystem.Tools.OpenConvertToNSCGroup()
    try:
        convert.SurfaceRange = ZOSAPI.Tools.OtherSettings.
            ConvertToNSCSurfaceRanges.AllSurfaces
        convert.SplitNSC = False
        convert.ScatterNSC = False
        convert.UsePolarization = False
        convert.DeleteSurfaces = True
        convert.CreateObjectsAt = ZOSAPI.Tools.OtherSettings.
            ConvertToNSCCreateObjectsAt.CoordinateZero
        convert.RunAndWaitForCompletion()
        print(f"Converted to NSC: {TheSystem.NCE.NumberOfObjects} objects")
    finally:
        convert.Close()

    # 3. Export to STEP using library wrapper
    output = zos.export_cad(
        filename=ensure_zmx_dir() + "\\cooke_triplet.step",
        cad_format='STEP',
        solids_only=True
    )
    print(f"CAD export: {output}")
```

## Complete End-to-End Workflow

```python
import os

with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # --- CAD EXPORT (Sample 09) ---
    print("=== CAD Export ===")
    zos.open_file(zos.samples_dir() +
        "\\Non-Sequential\\Miscellaneous\\Digital_projector_flys_eye_homogenizer.zos")

    out_dir = ensure_zmx_dir() + "\\cad_exchange"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Export formats
    for fmt, ext in [('STEP', '.step'), ('IGES', '.igs'),
                     ('SAT', '.sat'), ('STL', '.stl')]:
        out_path = os.path.join(out_dir, f"exported{ext}")
        zos.export_cad(out_path, cad_format=fmt, solids_only=True)

    # --- CAD IMPORT (Sample 20) ---
    print("\n=== CAD Import ===")
    zos.new_file(ZOSAPI.SystemType.NonSequential)

    # Import the STEP file we just exported
    imported = zos.import_cad(
        filename=os.path.join(out_dir, "exported.step"),
        cad_format='STEP',
        obj_number=1,
        material='MIRROR'
    )

    # Add a source and detector for stray light analysis
    TheNCE = TheSystem.NCE

    TheNCE.InsertNewObjectAt(2)
    zos.create_nsc_source(2, source_type='point',
                          total_rays=100000, power_lumens=1.0)
    zos.set_nsc_position(TheNCE.GetObjectAt(2), x=0, y=0, z=-20)

    TheNCE.InsertNewObjectAt(3)
    zos.create_nsc_detector(3, x_half_width=10, y_half_width=10,
                            pixels_x=200, pixels_y=200)
    zos.set_nsc_position(TheNCE.GetObjectAt(3), x=0, y=0, z=80)

    print(f"System: {TheNCE.NumberOfObjects} objects "
          f"({TheNCE.GetObjectAt(1).Comment})")
```

## Format Comparison

| Feature | STEP | IGES | SAT | STL |
|---------|------|------|-----|-----|
| Solid bodies | Yes | Yes | Yes | Surface mesh only |
| Precision | High | Medium | High | Low (faceted) |
| File size | Moderate | Large | Moderate | Small |
| CAD compatibility | All major CAD | Legacy CAD | ACIS-native | Universal |
| Zemax export quality | Best | Good | Good | Faceted |
| Zemax import quality | Best | Good | Good | Faceted |
| Industry standard | ISO 10303 | US PRO/IPO-100 | Spatial Corp | 3D Systems |

## Notes

- **Export works best with NSC systems** — for sequential designs, convert
  to NSC group first via `Tools.OpenConvertToNSCGroup()`
- The library wrapper `zos.export_cad()` is a simplified interface with
  defaults (solids-only, standard tessellation). For quality/spline
  control, use the raw `OpenExportCAD()` API shown in the tessellation
  section
- The library wrapper `zos.import_cad()` assigns a material automatically.
  Change it afterward by setting `obj.Material = 'NEW_MATERIAL'`
- STEP is the recommended exchange format for both export and import —
  best compatibility with SolidWorks, CATIA, NX, Creo, and AutoCAD
- STL is a faceted mesh format — sufficient for 3D printing and
  visualization but not suitable for precision optical analysis
- Imported CAD parts must be in an NSC system — they cannot be added to
  the sequential LDE
- After import, run `TheNCE.TraceAll()` to verify ray interaction with
  imported geometry
- Large CAD imports may take several minutes — Zemax tessellates the
  surface into facets for ray tracing
- Use `zos.set_nsc_position()` and `zos.set_nsc_orientation()` to position
  imported parts (never set `TiltX`/`TiltY`/`TiltZ` directly — those are
  known pythonnet traps that silently fail)
- Imported materials must be in a loaded catalog or be a basic type
  (`MIRROR`, `ABSORB`, `PERFECT MIRROR`, `PERFECT ABSORBER`)
