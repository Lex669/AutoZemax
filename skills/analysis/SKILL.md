---
name: analysis
description: This skill should be used when the user asks to "run MTF analysis", "calculate PSF", "generate spot diagram", "plot wavefront", "run ray fan", "get RMS spot size", "run FFT MTF", "pull analysis data", "read detector data", "extract simulation results", "get analysis results", or performs optical analysis in Zemax.
version: 0.1.0
---

# Analysis — MTF, PSF, Spot Diagrams & More

Run optical analyses and extract results data for plotting and evaluation.

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

## FFT MTF Analysis

Run MTF analysis and extract data. For plotting, pass results to the
`data-processing` skill.

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # Create FFT MTF analysis
    analyses = TheSystem.Analyses
    mtf_win = analyses.New_FftMtf()

    # Configure settings
    mtf_settings = mtf_win.GetSettings()
    mtf_settings.MaximumFrequency = 50  # cycles/mm
    mtf_settings.SampleSize = ZOSAPI.Analysis.SampleSizes.S_256x256

    # Run
    mtf_win.ApplyAndWaitForCompletion()

    # Extract results
    mtf_results = mtf_win.GetResults()

    # Collect data for each field
    mtf_data = []  # list of (x_values, tangential_y, sagittal_y)
    for series_num in range(mtf_results.NumberOfDataSeries):
        data = mtf_results.GetDataSeries(series_num)
        x_raw = list(data.XData.Data)       # Spatial frequency (cycles/mm)
        y_raw = data.YData.Data             # MTF values (2 columns)
        y = zos.reshape(y_raw, y_raw.GetLength(0), y_raw.GetLength(1), True)
        mtf_data.append({
            'frequency': x_raw,
            'tangential': y[0],  # first column
            'sagittal': y[1],    # second column
        })

    # mtf_data can now be passed to data-processing for plotting
    # Use the data-processing skill to generate MTF plots from this data
```

To plot the extracted `mtf_data`, use the `data-processing` skill which provides
MTF plot templates, export formats, and report generation.

## Spot Diagram

```python
# Create spot diagram analysis
spot = TheSystem.Analyses.New_Analysis(ZOSAPI.Analysis.AnalysisIDM.StandardSpot)

# Configure
spot_settings = spot.GetSettings()
spot_settings.Field.SetFieldNumber(0)       # All fields
spot_settings.Wavelength.SetWavelengthNumber(0)  # All wavelengths
spot_settings.ReferTo = ZOSAPI.Analysis.Settings.RMS.ReferTo.Centroid

# Run and extract
spot.ApplyAndWaitForCompletion()
spot_results = spot.GetResults()

# Get RMS & GEO spot sizes for each field
for field in range(1, spot_results.SpotData.NumberOfFields + 1):
    rms = spot_results.SpotData.GetRMSSpotSizeFor(field, 1)
    geo = spot_results.SpotData.GetGeoSpotSizeFor(field, 1)
    print(f"Field {field}: RMS={rms:.3f}, GEO={geo:.3f}")
```

## Batch Ray Trace + Spot Diagram (Manual)

For custom spot diagrams with individual ray coordinates, see the ray-tracing skill. Combine batch ray trace results with matplotlib scatter plots.

## Wavefront Map

```python
wavefront = TheSystem.Analyses.New_Analysis(
    ZOSAPI.Analysis.AnalysisIDM.WavefrontMap
)
wavefront.ApplyAndWaitForCompletion()
wf_results = wavefront.GetResults()
# Access wavefront data via DataSeries
```

## FFT PSF

```python
psf = TheSystem.Analyses.New_Analysis(
    ZOSAPI.Analysis.AnalysisIDM.FFTPSF
)
psf_settings = psf.GetSettings()
psf_settings.SampleSize = ZOSAPI.Analysis.SampleSizes.S_256x256
psf.ApplyAndWaitForCompletion()
psf_results = psf.GetResults()
# Data available as 2D PSF array via DataSeries
```

## Ray Fan

```python
ray_fan = TheSystem.Analyses.New_Analysis(
    ZOSAPI.Analysis.AnalysisIDM.RayFan
)
ray_fan.ApplyAndWaitForCompletion()
fan_results = ray_fan.GetResults()
```

## General Data Extraction Pattern

```python
analysis = TheSystem.Analyses.New_Analysis(analysis_id)
analysis.ApplyAndWaitForCompletion()
results = analysis.GetResults()

for i in range(results.NumberOfDataSeries):
    series = results.GetDataSeries(i)
    x = list(series.XData.Data)
    y_raw = series.YData.Data
    y = zos.reshape(y_raw, y_raw.GetLength(0), y_raw.GetLength(1))
    # Process x, y...
```

## Available Analysis Types (AnalysisIDM)

| ID | Analysis |
|----|----------|
| StandardSpot | Standard Spot Diagram |
| FFTMTF | FFT Modulation Transfer Function |
| FFTPSF | FFT Point Spread Function |
| WavefrontMap | Wavefront Map |
| RayFan | Ray Fan Plot |
| FieldCurvatureDistortion | Field Curvature / Distortion |
| LateralColor | Lateral Color |
| RMSWavefront | RMS vs. Field |

## Notes

- Always configure settings BEFORE calling `ApplyAndWaitForCompletion()`
- `DataType` 0 for Y data gives the primary y-axis values
- Multi-field data returns one DataSeries per field
- MTF data format: YData columns = [Tangential, Sagittal]
- Close ZOS connection BEFORE calling `plt.show()` to release memory
