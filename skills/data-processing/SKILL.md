---
name: data-processing
description: This skill should be used when the user asks to "plot MTF", "plot spot", "plot wavefront", "plot detector", "plot CDF", "generate report", "visualize results", "save figure", "export chart", "matplotlib plot", "publish figure", "data visualization", "export figure", or creates publication-quality plots and reports from Zemax optical simulation data.
version: 0.2.0
---

# Data Processing — Plots, Figures & Reports

Generate publication-quality visualizations from Zemax analysis results
using library plot functions and custom matplotlib templates. Supports
MTF curves, spot diagrams, wavefront maps, ray fans, NSC detector data,
tolerance CDFs, and multi-panel report figures.

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
from zos_utils import (
    ZOSConnection, set_seed,
    plot_mtf, plot_spot_diagram, plot_wavefront_map,
    plot_ray_fan, plot_detector_data, plot_tolerance_cdf
)

set_seed(42)
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## CRITICAL WARNING: Connection vs. Matplotlib Conflict

**Never call `plt.show()` inside a `with ZOSConnection():` block.**
The .NET interop will crash or hang when matplotlib displays a window.
Always close the connection before showing figures:

```python
# WRONG — will crash:
with ZOSConnection() as zos:
    # ... run analysis ...
    plt.show()  # CRASH: .NET interop conflict

# CORRECT:
with ZOSConnection() as zos:
    # ... run analysis, extract data ...
    zos.close()      # Release .NET resources

plt.show()           # Safe after connection is closed
```

For non-interactive use (scripts, automated reports), always use
`plt.savefig()` instead of `plt.show()` — this avoids the conflict
entirely.

## Library Plot Functions

All library plot functions share the same interface pattern:
- `save_path`: If provided, saves figure to disk (recommended).
- `show`: If True, calls `plt.show()`. Default False — use `zos.close()` first.
- Return `(fig, ax)` for further customization.

### MTF Plot

Extract MTF data using the analysis skill, then plot:

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # Run MTF analysis
    mtf = TheSystem.Analyses.New_FftMtf()
    mtf_settings = mtf.GetSettings()
    mtf_settings.MaximumFrequency = 80
    mtf_settings.SampleSize = ZOSAPI.Analysis.SampleSizes.S_256x256
    mtf.ApplyAndWaitForCompletion()

    # Extract data
    mtf_data = zos.extract_mtf_data(mtf.GetResults())
    zos.close()

# Plot with diffraction limit marker
plot_mtf(
    mtf_data,
    title='Double Gauss — FFT MTF',
    save_path='mtf_plot.png',
    show=False,
    diffraction_limit_freq=72.3  # cycles/mm (optional marker)
)
```

### Spot Diagram Bar Chart

```python
with ZOSConnection() as zos:
    spot = zos.TheSystem.Analyses.New_Analysis(
        zos.ZOSAPI.Analysis.AnalysisIDM.StandardSpot)
    spot.ApplyAndWaitForCompletion()
    spot_data = zos.extract_spot_data(spot.GetResults())
    zos.close()

plot_spot_diagram(
    spot_data,
    title='RMS vs GEO Spot Size by Field',
    save_path='spot_summary.png'
)
```

### Wavefront Map

```python
with ZOSConnection() as zos:
    wf = zos.TheSystem.Analyses.New_Analysis(
        zos.ZOSAPI.Analysis.AnalysisIDM.WavefrontMap)
    wf.ApplyAndWaitForCompletion()
    wf_data = zos.extract_wavefront_data(wf.GetResults())
    zos.close()

plot_wavefront_map(
    wf_data,
    grid_index=0,
    title='Wavefront Map — Field 1',
    save_path='wavefront.png',
    cmap='RdBu_r'
)
```

### Ray Fan Plot

```python
with ZOSConnection() as zos:
    fan = zos.TheSystem.Analyses.New_Analysis(
        zos.ZOSAPI.Analysis.AnalysisIDM.RayFan)
    fan.ApplyAndWaitForCompletion()
    fan_data = zos.extract_ray_fan_data(fan.GetResults())
    zos.close()

plot_ray_fan(
    fan_data,
    title='Ray Fan — All Fields',
    save_path='ray_fan.png'
)
```

### NSC Detector Data

```python
with ZOSConnection() as zos:
    TheNCE = zos.TheSystem.NCE
    TheNCE.ClearDetectors()
    TheNCE.TraceAll()

    w, h, detector_data = zos.get_detector_data(2)
    zos.close()

plot_detector_data(
    detector_data,
    title='NSC Detector Irradiance',
    save_path='detector.png',
    cmap='inferno',
    x_extent=10.0,
    y_extent=10.0
)
```

### Tolerance CDF

```python
with ZOSConnection() as zos:
    stats = zos.run_tolerance_monte_carlo(n_trials=200)
    zos.close()

plot_tolerance_cdf(
    stats,
    title='Manufacturing Yield — CDF (200 trials)',
    save_path='tolerance_cdf.png'
)
```

## Custom Matplotlib Patterns

When the library plot functions do not provide enough control, build
custom figures with matplotlib directly.

### Multi-Panel Report Figure

```python
import matplotlib.pyplot as plt
import numpy as np

with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    mtf = TheSystem.Analyses.New_FftMtf()
    mtf.GetSettings().MaximumFrequency = 80
    mtf.ApplyAndWaitForCompletion()
    mtf_data = zos.extract_mtf_data(mtf.GetResults())

    wf = TheSystem.Analyses.New_Analysis(ZOSAPI.Analysis.AnalysisIDM.WavefrontMap)
    wf.ApplyAndWaitForCompletion()
    wf_data = zos.extract_wavefront_data(wf.GetResults())

    spot = TheSystem.Analyses.New_Analysis(ZOSAPI.Analysis.AnalysisIDM.StandardSpot)
    spot.ApplyAndWaitForCompletion()
    spot_data = zos.extract_spot_data(spot.GetResults())
    zos.close()

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# MTF (top-left)
ax = axes[0, 0]
for e in mtf_data:
    ax.plot(e['frequency'], e['tangential'], label=f"F{e['field']} T")
    ax.plot(e['frequency'], e['sagittal'], '--', label=f"F{e['field']} S")
ax.set_xlabel('Frequency (c/mm)'); ax.set_ylabel('MTF')
ax.set_title('FFT MTF'); ax.legend(fontsize=7); ax.set_ylim(0, 1.05); ax.grid(True, alpha=0.3)

# Wavefront (top-right)
ax = axes[0, 1]
im = ax.imshow(np.array(wf_data['grids'][0]), cmap='RdBu_r', origin='lower')
ax.set_title('Wavefront Map'); fig.colorbar(im, ax=ax, label='Waves')

# Spot diagram (bottom-left)
ax = axes[1, 0]
fields = [s['field'] for s in spot_data['spots']]
rms = [s['rms_spot_um'] for s in spot_data['spots']]
geo = [s['geo_spot_um'] for s in spot_data['spots']]
x = np.arange(len(fields))
ax.bar(x - 0.35/2, rms, 0.35, label='RMS', color='steelblue')
ax.bar(x + 0.35/2, geo, 0.35, label='GEO', color='darkorange')
ax.set_xlabel('Field'); ax.set_ylabel('Spot Size (um)')
ax.set_title('Spot Summary'); ax.set_xticks(x); ax.legend()

axes[1, 1].axis('off')
fig.suptitle('Optical Design Report', fontsize=14, y=1.02)
fig.tight_layout()
fig.savefig('full_report.png', dpi=200, bbox_inches='tight')
```

### Overlay Plots

```python
import matplotlib.pyplot as plt
import numpy as np

with ZOSConnection() as zos:
    TheNCE = zos.TheSystem.NCE
    TheNCE.ClearDetectors()
    TheNCE.TraceAll()
    w, h, inc_data = zos.get_detector_data(2, data_type=0)
    w, h, coh_data = zos.get_detector_data(2, data_type=1)
    zos.close()

inc_np = np.array(inc_data)
coh_np = np.array(coh_data)

fig, ax = plt.subplots(figsize=(8, 6))
ax.imshow(inc_np, cmap='gray', alpha=0.5, origin='lower',
          extent=[-10, 10, -10, 10])
levels = np.linspace(coh_np.min(), coh_np.max(), 10)
cs = ax.contour(coh_np, levels=levels, cmap='plasma', origin='lower',
                extent=[-10, 10, -10, 10], linewidths=0.8)
ax.clabel(cs, inline=True, fontsize=8)
ax.set_xlabel('X (mm)')
ax.set_ylabel('Y (mm)')
ax.set_title('Incoherent (gray) + Coherent Contours')
fig.tight_layout()
fig.savefig('overlay_analysis.png', dpi=150)
```

## Figure Export Options

| Format | Extension | Usage |
|--------|-----------|-------|
| PNG | .png | Web, reports, documentation |
| PDF | .pdf | Vector graphics, publications, LaTeX |
| SVG | .svg | Vector, editable in Illustrator/Inkscape |
| EPS | .eps | LaTeX, publications |

```python
# Export a figure in multiple formats
fig.savefig('plot.png', dpi=300, bbox_inches='tight')
fig.savefig('plot.pdf', bbox_inches='tight')
fig.savefig('plot.svg', bbox_inches='tight')
```

### Export Directory

```python
output_dir = os.path.join(zos.ensure_zmx_dir(), 'figures')
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
fig.savefig(os.path.join(output_dir, 'mtf.png'), dpi=200)
```

## Style Customization

Apply consistent styling globally:

```python
import matplotlib.pyplot as plt
plt.rcParams.update({'figure.dpi': 150, 'font.size': 11,
    'axes.labelsize': 12, 'axes.titlesize': 13,
    'legend.fontsize': 9, 'lines.linewidth': 1.5})
```

## Plot Function Quick Reference

| Function | Source Data | Use Case |
|----------|-------------|----------|
| `plot_mtf()` | `zos.extract_mtf_data()` | MTF curves |
| `plot_spot_diagram()` | `zos.extract_spot_data()` | RMS/GEO bar chart |
| `plot_wavefront_map()` | `zos.extract_wavefront_data()` | 2D wavefront heatmap |
| `plot_ray_fan()` | `zos.extract_ray_fan_data()` | Aberration curves |
| `plot_detector_data()` | `zos.get_detector_data()` | NSC detector image |
| `plot_tolerance_cdf()` | `zos.run_tolerance_monte_carlo()` | Yield CDF curve |

## Notes

- **CRITICAL: Close ZOS connection before `plt.show()`** — either call
  `zos.close()` or place plotting code outside the `with ZOSConnection():`
  block. Matplotlib displaying a window while .NET is active will crash
  or hang. Use `plt.savefig()` for non-interactive scripts.
- All plot functions accept `save_path` (str), `show` (bool), and
  return `(fig, ax)` for further customization.
- `fig.tight_layout()` and `bbox_inches='tight'` prevent clipped labels.
- Default DPI is 150; use 300+ for publication-quality output.
- `x_extent`/`y_extent` in `plot_detector_data()` set axis range in mm.
- Colormaps: `'hot'`/`'inferno'` for irradiance, `'RdBu_r'` for
  phase/wavefront, `'viridis'`/`'plasma'` for general data.
- SVG/PDF preserve vector art; PNG for web use.
