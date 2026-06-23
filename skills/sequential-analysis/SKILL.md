---
name: sequential-analysis
description: This skill should be used when the user asks to "run MTF", "FFT MTF", "spot diagram", "ray fan", "wavefront map", "FFT PSF", "read ZRD", "pull analysis data", "extract results", "RMS spot", "field curvature", "distortion", "lateral color", "RMS wavefront", "optical analysis", or performs sequential-mode optical analysis in Zemax and needs to extract numerical results.
version: 0.2.0
---

# Sequential Analysis — MTF, PSF, Spot Diagrams & More

Run all standard sequential optical analyses and extract numerical results
using library extractors. Data is extracted as Python-native structures
(arrays of dicts, 2D lists) ready for plotting via the data-processing skill.

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

## FFT MTF Analysis

Run MTF analysis and extract data using the library `extract_mtf_data()`.
For plotting, pass extracted data to the data-processing skill.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    TheSystem.LoadFile(
        zos.samples_dir() + "\\Sequential\\Objectives\\Double Gauss 28 degree field.zos",
        False)

    # Create FFT MTF analysis
    mtf = TheSystem.Analyses.New_FftMtf()
    mtf_settings = mtf.GetSettings()
    mtf_settings.MaximumFrequency = 50        # cycles/mm
    mtf_settings.SampleSize = ZOSAPI.Analysis.SampleSizes.S_256x256

    # Run analysis
    mtf.ApplyAndWaitForCompletion()

    # Extract data using library extractor
    mtf_results = mtf.GetResults()
    mtf_data = zos.extract_mtf_data(mtf_results)

    # mtf_data is a list of dicts with keys:
    #   'frequency', 'tangential', 'sagittal', 'field'
    for entry in mtf_data:
        n = entry['field']
        t05 = entry['tangential'][5] if len(entry['tangential']) > 5 else None
        s05 = entry['sagittal'][5] if len(entry['sagittal']) > 5 else None
        print(f"Field {n}: MTF@5cyc T={t05:.4f} S={s05:.4f}")

    # Pass mtf_data to data-processing skill for plotting:
    # plot_mtf(mtf_data, title='FFT MTF', save_path='mtf_plot.png')
```

## Spot Diagram

Extract RMS and GEO spot sizes, plus Airy disk radii per field.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    TheSystem.LoadFile(
        zos.samples_dir() + "\\Sequential\\Objectives\\Double Gauss 28 degree field.zos",
        False)

    # Create standard spot diagram analysis
    spot = TheSystem.Analyses.New_Analysis(
        ZOSAPI.Analysis.AnalysisIDM.StandardSpot
    )
    spot_settings = spot.GetSettings()
    spot_settings.Field.SetFieldNumber(0)          # All fields
    spot_settings.Wavelength.SetWavelengthNumber(0)  # All wavelengths
    spot_settings.ReferTo = ZOSAPI.Analysis.Settings.RMS.ReferTo.Centroid

    spot.ApplyAndWaitForCompletion()
    spot_results = spot.GetResults()

    # Extract using library extractor
    spot_data = zos.extract_spot_data(spot_results)

    # spot_data is a dict: {'spots': [...], 'n_fields': N}
    for s in spot_data['spots']:
        print(f"Field {s['field']}: RMS={s['rms_spot_um']:.3f} um, "
              f"GEO={s['geo_spot_um']:.3f} um, "
              f"Airy={s['airy_radius_um']:.3f} um")

    # Pass spot_data to data-processing skill for plotting:
    # plot_spot_diagram(spot_data, 'Spot Summary', 'spot_sizes.png')
```

## Wavefront Map

Extract 2D wavefront error grids for visualization.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    wavefront = TheSystem.Analyses.New_Analysis(
        ZOSAPI.Analysis.AnalysisIDM.WavefrontMap
    )
    wavefront.ApplyAndWaitForCompletion()
    wf_results = wavefront.GetResults()

    # Extract using library extractor
    wf_data = zos.extract_wavefront_data(wf_results)

    # wf_data is a dict: {'grids': [2D_lists], 'n_series': N}
    # grids[0] = wavefront error for first field/wavelength
    first_wavefront = wf_data['grids'][0]
    print(f"Wavefront grid: {len(first_wavefront)}x{len(first_wavefront[0])}")

    # Pass wf_data to data-processing skill for plotting:
    # plot_wavefront_map(wf_data, "Wavefront Map", "wavefront.png")
```

## FFT PSF

Extract 2D PSF data arrays.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    psf = TheSystem.Analyses.New_Analysis(
        ZOSAPI.Analysis.AnalysisIDM.FFTPSF
    )
    psf_settings = psf.GetSettings()
    psf_settings.SampleSize = ZOSAPI.Analysis.SampleSizes.S_256x256

    psf.ApplyAndWaitForCompletion()
    psf_results = psf.GetResults()

    # Extract using library extractor
    psf_data = zos.extract_psf_data(psf_results)

    # psf_data is a dict: {'grids': [2D_lists], 'n_series': N}
    print(f"PSF grids: {psf_data['n_series']} series extracted")

    # For plotting, use matplotlib directly or data-processing skill
    # Each grid is a 2D Python list suitable for plt.imshow()
```

## Ray Fan

Extract pupil coordinate vs ray error curves.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    ray_fan = TheSystem.Analyses.New_Analysis(
        ZOSAPI.Analysis.AnalysisIDM.RayFan
    )
    ray_fan.ApplyAndWaitForCompletion()
    fan_results = ray_fan.GetResults()

    # Extract using library extractor
    fan_data = zos.extract_ray_fan_data(fan_results)

    # fan_data is a list of dicts with keys:
    #   'pupil_x', 'tangential', 'sagittal', 'field'
    for entry in fan_data:
        print(f"Field {entry['field']}: {len(entry['pupil_x'])} pupil samples")

    # Pass fan_data to data-processing skill for plotting:
    # plot_ray_fan(fan_data, "Ray Fan", "ray_fan.png")
```

## Field Curvature & Distortion

```python
fc_dist = TheSystem.Analyses.New_Analysis(
    ZOSAPI.Analysis.AnalysisIDM.FieldCurvatureDistortion
)
fc_dist.ApplyAndWaitForCompletion()
fc_results = fc_dist.GetResults()
# Access DataSeries for field curvature (tangential + sagittal)
# and distortion curves separately

for i in range(fc_results.NumberOfDataSeries):
    series = fc_results.GetDataSeries(i)
    x_raw = list(series.XData.Data)
    y_raw_data = series.YData.Data
    y = zos.safe_reshape(y_raw_data)
    print(f"Series {i}: X={len(x_raw)} pts, Y={len(y)} rows")
```

## Lateral Color

```python
lat_color = TheSystem.Analyses.New_Analysis(
    ZOSAPI.Analysis.AnalysisIDM.LateralColor
)
lat_color.ApplyAndWaitForCompletion()
lc_results = lat_color.GetResults()
# DataSeries contain lateral color vs field for each wavelength pair
```

## RMS Wavefront vs Field

```python
rms_wf = TheSystem.Analyses.New_Analysis(
    ZOSAPI.Analysis.AnalysisIDM.RMSWavefront
)
rms_wf.ApplyAndWaitForCompletion()
rms_results = rms_wf.GetResults()
# DataSeries contain RMS wavefront error vs field position

for i in range(rms_results.NumberOfDataSeries):
    series = rms_results.GetDataSeries(i)
    x = list(series.XData.Data)  # Field positions
    y_raw = series.YData.Data
    y = zos.safe_reshape(y_raw)
    # y[0] = RMS wavefront values
```

## General Data Extraction Pattern

For any analysis that is not covered by a dedicated extractor:

```python
analysis = TheSystem.Analyses.New_Analysis(analysis_id)
analysis.ApplyAndWaitForCompletion()
results = analysis.GetResults()

for i in range(results.NumberOfDataSeries):
    series = results.GetDataSeries(i)
    x_vals = list(series.XData.Data)
    y_vals_raw = series.YData.Data
    y_vals = zos.safe_reshape(y_vals_raw)  # Auto-detect dimensions
    # Process x_vals and y_vals...
```

## Plotting Extracted Data

This skill extracts data as Python-native structures. **For plotting, use the
data-processing skill** which provides:

| Function | Input Data | Output |
|----------|------------|--------|
| `plot_mtf(mtf_data)` | `extract_mtf_data()` result | Publication-quality MTF plot |
| `plot_spot_diagram(spot_data)` | `extract_spot_data()` result | RMS/GEO bar chart |
| `plot_wavefront_map(wf_data)` | `extract_wavefront_data()` result | 2D wavefront heatmap |
| `plot_ray_fan(fan_data)` | `extract_ray_fan_data()` result | Ray fan curves |
| `plot_detector_data(data_2d)` | Non-sequential detector data | 2D heatmap |

All plotting functions support `save_path` and `show` parameters.

## Analysis Types Quick Reference

| AnalysisIDM | Description | Library Extractor |
|-------------|-------------|-------------------|
| FFTMTF | FFT Modulation Transfer Function | `extract_mtf_data()` |
| FFTPSF | FFT Point Spread Function | `extract_psf_data()` |
| StandardSpot | Standard Spot Diagram | `extract_spot_data()` |
| WavefrontMap | Wavefront Map | `extract_wavefront_data()` |
| RayFan | Ray Fan Plot | `extract_ray_fan_data()` |
| FieldCurvatureDistortion | Field Curvature / Distortion | Manual DataSeries |
| LateralColor | Lateral Color | Manual DataSeries |
| RMSWavefront | RMS Wavefront vs Field | Manual DataSeries |

## Notes

- **Always configure settings BEFORE calling `ApplyAndWaitForCompletion()`** — changes made after running have no effect
- **Close the ZOS connection BEFORE calling `plt.show()`** — .NET interop may crash or hang if Zemax is still connected
- Use `plt.savefig()` instead of `plt.show()` for non-interactive report generation
- Extractors return Python-native data (lists, dicts) — no .NET objects remain, so plotting is safe after ZOS connection closes
- MTF data format: YData = [Tangential, Sagittal] columns. The extractor handles transposition automatically
- Spot diagram results include RMS, GEO, and Airy disk radius in microns — field and wavelength indices are 1-based
- Ray fan data: tangential and sagittal are separate columns — use `zos.reshape(y_raw, cols, rows, transpose=True)`
- For large detector arrays (NSC), use `zos.get_detector_data()` which handles dimension detection automatically
- **Use `zos.safe_reshape()` for auto-dimension detection** instead of manual `GetLength(0)`/`GetLength(1)`
