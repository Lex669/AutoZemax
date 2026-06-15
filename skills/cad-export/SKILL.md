---
name: cad-export
description: This skill should be used when the user asks to "export to CAD", "export to STEP", "save as CAD file", "export IGES", "export STL", "export SAT", "convert Zemax to CAD", "export optical model to CAD", or exports Zemax geometry to CAD formats.
version: 0.1.0
---

# CAD Export — STEP, IGES, SAT, STL

Export optical system geometry to CAD file formats for mechanical integration.

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

## Supported Export Formats

| Format | CADFileType Enum | Extension |
|--------|-----------------|-----------|
| STEP | STEP | .step / .stp |
| IGES | IGES | .iges / .igs |
| SAT (ACIS) | SAT | .sat |
| STL (mesh) | STL | .stl |

## Workflow

### Basic CAD Export (NSC System)

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # Load system to export
    TheSystem.LoadFile(zos.samples_dir() +
        "\\Non-Sequential\\Miscellaneous\\Digital_projector_flys_eye_homogenizer.zos",
        False)

    # Open export tool
    export_cad = TheSystem.Tools.OpenExportCAD()

    # Object range
    export_cad.FirstObject = 1
    export_cad.LastObject = 8

    # Layer settings
    export_cad.RayLayer = 1
    export_cad.LensLayer = 0
    export_cad.DummyThickness = 1

    # Geometry quality
    export_cad.SplineSegments = ZOSAPI.Tools.General.SplineSegmentsType.N_032

    # File format and tolerance
    export_cad.FileType = ZOSAPI.Tools.General.CADFileType.STEP
    export_cad.Tolerance = ZOSAPI.Tools.General.CADToleranceType.N_TenEMinus4

    # Configuration
    export_cad.SetCurrentConfiguration()
    # Alternatives:
    # export_cad.SetConfigurationAllAtOnce()
    # export_cad.SetConfigurationAllByFile()
    # export_cad.SetConfigurationAllByLayer()
    # export_cad.SetSingleConfiguration(1)

    # Surface options
    export_cad.SurfacesAsSolids = True
    export_cad.ScatterNSCRays = False
    export_cad.ExportDummySurfaces = False
    export_cad.SplitNSCRays = False
    export_cad.UsePolarization = False

    # Output path
    output_file = zos.objects_dir() + "\\CAD Files\\exported_model.step"
    export_cad.OutputFileName = output_file

    # Run export
    print('Starting CAD export...')
    export_cad.Run()
    runstatus = export_cad.WaitWithTimeout(180.0)  # 3 minutes

    if runstatus == ZOSAPI.Tools.RunStatus.Completed:
        print(f'Export completed: {output_file}')
    elif runstatus == ZOSAPI.Tools.RunStatus.FailedToStart:
        print('Failed to start')
    elif runstatus == ZOSAPI.Tools.RunStatus.InvalidTimeout:
        print('Invalid timeout')
    else:
        print('Timed out')

    if runstatus != ZOSAPI.Tools.RunStatus.Completed and export_cad.CanCancel:
        export_cad.Cancel()

    export_cad.Close()
```

## Spline Segment Quality

| Enum | Segments | Quality |
|------|----------|---------|
| N_032 | 32 | Draft |
| N_064 | 64 | Medium |
| N_128 | 128 | High |
| N_256 | 256 | Maximum |

## CAD Tolerance

| Enum | Value | Use Case |
|------|-------|----------|
| N_TenEMinus4 | 1e-4 | Precise optics |
| N_TenEMinus5 | 1e-5 | High precision |
| N_TenEMinus6 | 1e-6 | Ultra precision |
| N_TenEMinus7 | 1e-7 | Maximum precision |

## Notes

- Export works best with NSC systems; for sequential, convert to NSC first (`Tools.OpenConvertToNSCGroup()`)
- Higher spline segments = smoother curves but larger files
- STEP format is recommended for most CAD packages
- STL is a mesh format useful for 3D printing
- Export time scales with object count and spline segment quality
- Always check the `RunStatus` after export to verify success
