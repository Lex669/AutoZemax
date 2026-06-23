---
name: nsc-analysis
description: This skill should be used when the user asks to "NSC analysis", "NSC detector data", "read detector", "get detector data", "NSC phase", "coherent data", "NSC ZRD", "filter string", "NSC ray trace results", "detector irradiance", "coherent phase", or extracts and analyzes results from non-sequential detector objects in Zemax OpticStudio.
version: 0.2.0
---

# NSC Analysis — Detector Data, Coherent Fields & ZRD Filters

Read irradiance and coherent field data from NSC detector objects, apply
ZRD filter strings for ray database analysis, run batch NSC ray traces,
and visualize detector data. Corresponds to ZOS-API Samples 06, 08, 10.

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
from zos_utils import ZOSConnection, set_seed, plot_detector_data

set_seed(42)
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## Detector Data Types

NSC detectors store multiple data layers. The `data_type` parameter
selects which layer to read:

| data_type | Description | Units |
|-----------|-------------|-------|
| 0 | Incoherent irradiance | W/m^2 or lumens/m^2 |
| 1 | Coherent irradiance | W/m^2 |
| 2 | Phase | degrees (0-360) |
| 3 | Real part (coherent field) | V/m |
| 4 | Imaginary part (coherent field) | V/m |

## Reading Detector Irradiance

Use `zos.get_detector_data()` to read the full 2D data array from a
detector object. Returns (width, height, data_2d_list).

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    TheNCE = TheSystem.NCE

    # Load an NSC file with a detector
    zos.open_file(zos.samples_dir() +
        "\\Non-Sequential\\Illumination\\LED_illumination_system.zos",
        False)

    # Run ray trace FIRST
    TheNCE.ClearDetectors()
    TheNCE.TraceAll()

    # Read incoherent irradiance (data_type=0)
    w, h, incoherent = zos.get_detector_data(detector_number=2, data_type=0)
    print(f"Detector: {w}x{h} pixels")
    print(f"Max irradiance: {max(max(row) for row in incoherent):.4f}")

    # Read coherent irradiance (data_type=1)
    w, h, coherent = zos.get_detector_data(detector_number=2, data_type=1)
```

### Data Shape and Access

The returned `data_2d` is a Python list-of-lists indexed as `data[y][x]`:

```python
w, h, data = zos.get_detector_data(2)
# data[y][x] — row-major, origin at bottom-left

# Access a single pixel
pixel_value = data[100][150]

# Find peak location
peak_val = 0.0
peak_x, peak_y = 0, 0
for y in range(h):
    for x in range(w):
        if data[y][x] > peak_val:
            peak_val = data[y][x]
            peak_x, peak_y = x, y
print(f"Peak at pixel ({peak_x}, {peak_y}) = {peak_val:.4f}")

# Compute total power
total = sum(sum(row) for row in data)
print(f"Total integrated power: {total:.4f}")
```

## Coherent Data (Real, Imaginary, Phase, Amplitude)

Use `zos.get_coherent_data()` to read the full coherent field. Returns
width, height, and four 2D lists: real, imaginary, phase (degrees),
and amplitude.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    TheNCE = TheSystem.NCE

    zos.open_file(zos.samples_dir() +
        "\\Non-Sequential\\Illumination\\LED_illumination_system.zos",
        False)

    TheNCE.ClearDetectors()
    TheNCE.TraceAll()

    # Read coherent data from detector
    w, h, real_data, imag_data, phase_deg, amplitude = \
        zos.get_coherent_data(detector_number=2)

    print(f"Coherent data: {w}x{h}")
    print(f"Phase range: {min(min(row) for row in phase_deg):.1f} to "
          f"{max(max(row) for row in phase_deg):.1f} deg")

    # Plot phase map using data-processing skill
    # plot_detector_data(phase_deg, title='Coherent Phase',
    #                    cmap='RdBu', save_path='phase_map.png')
```

### Phase Computation Details

The library computes phase and amplitude internally:

```
phase_deg  = atan2(imaginary, real) * 180 / pi
amplitude  = sqrt(real^2 + imaginary^2)
```

No unwrapping is applied — the returned phase is wrapped in [-180, 180]
degrees. Use `numpy.unwrap()` for contiguous phase maps:

```python
import numpy as np

# Convert to numpy for unwrapping
phase_np = np.array(phase_deg)
phase_unwrapped = np.unwrap(phase_np, axis=1)  # Unwrap rows
phase_unwrapped = np.unwrap(phase_unwrapped, axis=0)  # Then columns
print(f"Unwrapped phase range: {phase_unwrapped.min():.1f} to "
      f"{phase_unwrapped.max():.1f} deg")
```

## Running NSC Ray Traces

Before reading detector data, run an NSC ray trace. The simplest approach
is `TheNCE.TraceAll()`, but for more control use the tool API:

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    TheNCE = TheSystem.NCE

    # Simple trace — all sources, all objects
    TheNCE.ClearDetectors()  # Reset accumulated data
    TheNCE.TraceAll()
    print("Trace complete.")

    # Advanced trace with progress monitoring
    nsc_trace = TheSystem.Tools.OpenNSCRayTrace()
    try:
        nsc_trace.SplitNSCRays = True
        nsc_trace.ScatterNSCRays = False
        nsc_trace.UsePolarization = True
        nsc_trace.IgnoreErrors = True
        nsc_trace.SaveRays = True  # Save ZRD for later filtering
        nsc_trace.NumberOfAnalysisRays = 1000000

        nsc_trace.Run()
        while nsc_trace.IsRunning:
            print(f"Progress: {nsc_trace.Progress}%")
        nsc_trace.WaitForCompletion()
    finally:
        nsc_trace.Close()

    # Now read detector data
    w, h, data = zos.get_detector_data(2)
```

## ZRD Filter Strings

When `SaveRays=True`, the ray database (ZRD) is available for filtered
queries. Filter strings select subsets of rays by object, segment, status,
or data range.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # After ray trace with SaveRays=True, filter the database:

    # Select rays hitting object 2
    filter_str = "Object=2"

    # Select rays from source 1 that hit detector 2
    filter_str = "Source=1 AND Object=2"

    # Select absorbed rays (status = 4 = absorbed)
    filter_str = "Status=4"

    # Select rays with more than 2 segments
    filter_str = "Segments>2"

    # Select rays with intensity above threshold
    filter_str = "Intensity>0.5"

    # Compound filter
    filter_str = "(Source=1 OR Source=2) AND Object=2 AND Status=4"

    print(f"Filter string: {filter_str}")

    # Apply filter via the ray database tool
    # (ZRD filter application requires OpenNSCRayTrace with SaveRays=True)
```

### Common ZRD Filter Fields

| Field | Description | Example |
|-------|-------------|---------|
| Object | Object number hit | Object=2 |
| Source | Source object number | Source=1 |
| Status | Ray status code | Status=4 |
| Segment | Segment number | Segment=0 |
| Intensity | Ray intensity (normalized) | Intensity>0.1 |
| Wavelength | Wavelength number | Wavelength=1 |
| Segments | Total segment count | Segments>2 |

### Ray Status Codes

| Code | Meaning |
|------|---------|
| 0 | Ray is propagating |
| 1 | Ray missed all objects |
| 2 | Ray was absorbed |
| 3 | Ray was scattered |
| 4 | Ray hit detector |
| -1 | Ray error |

## Visualizing Detector Data

Use `plot_detector_data()` from zos_utils for quick visualization.

IMPORTANT: Call `zos.close()` BEFORE `plt.show()` to avoid .NET interop
crashes. Use `plt.savefig()` for non-interactive use.

```python
import os

with ZOSConnection() as zos:
    TheNCE = zos.TheSystem.NCE
    TheNCE.ClearDetectors()
    TheNCE.TraceAll()

    w, h, data = zos.get_detector_data(2)

    # Close connection BEFORE plotting
    zos.close()

# Now plot safely
plot_detector_data(
    data,
    title='NSC Detector Irradiance',
    save_path='detector_irradiance.png',
    show=False,        # Use savefig, not show
    cmap='hot',
    x_extent=10.0,     # Half-width in mm
    y_extent=10.0
)
```

### Custom Matplotlib Visualization

```python
import matplotlib.pyplot as plt
import numpy as np

with ZOSConnection() as zos:
    TheNCE = zos.TheSystem.NCE
    TheNCE.ClearDetectors()
    TheNCE.TraceAll()
    w, h, data = zos.get_detector_data(2)
    zos.close()

# Convert to numpy for processing
data_np = np.array(data)

# 2D image plot with logarithmic scale
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

im1 = ax1.imshow(data_np, cmap='inferno', origin='lower')
ax1.set_title('Linear Scale')
fig.colorbar(im1, ax=ax1)

# Log scale for better dynamic range
data_log = np.log10(data_np + 1e-10)  # avoid log(0)
im2 = ax2.imshow(data_log, cmap='inferno', origin='lower')
ax2.set_title('Log Scale')
fig.colorbar(im2, ax=ax2)

fig.tight_layout()
fig.savefig('detector_comparison.png', dpi=150)
print("Detector comparison saved.")
```


## Notes

- **Always call `TheNCE.ClearDetectors()` before each ray trace** —
  without this, detector data accumulates across traces and results
  will be incorrect.
- **Always close the ZOS connection before `plt.show()`** —
  use `zos.close()` then call plotting functions. The .NET interop
  crashes or hangs if matplotlib displays a window while the connection
  is active. Use `plt.savefig()` for non-interactive workflows.
- `get_detector_data()` reads the detector at its current resolution
  (pixels_x x pixels_y). Higher pixel counts provide finer spatial
  detail but increase readout time linearly.
- `get_coherent_data()` returns phase wrapped in [-180, 180] degrees.
  Use `numpy.unwrap()` for contiguous phase maps.
- Detector number is the NSC object number (1-indexed in TheNCE).
- `data_type=0` (incoherent irradiance) is the most commonly used layer.
  It reports the physical power per unit area at each pixel.
- For phase analysis (interferometry, coherent systems), use data_type=2
  for direct phase read or `get_coherent_data()` for the full field.
- ZRD filter strings follow the syntax documented in the Zemax manual.
  Compound filters use `AND`, `OR`, and parentheses for grouping.
- The `SaveRays` option increases memory usage considerably —
  disable it (`SaveRays=False`) when only integrated detector values
  are needed.
- For plotting detector data with custom colormaps or multi-panel
  layouts, see the `data-processing` skill.
