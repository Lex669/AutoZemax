---
name: data-processing
description: This skill should be used when the user asks to "plot MTF", "generate analysis report", "process simulation data", "visualize results", "plot spot diagram", "create analysis chart", "export data to CSV", "make performance report", "analyze optical performance", "generate plots from Zemax data", or processes and visualizes Zemax simulation output.
version: 0.1.0
---

# Data Processing & Visualization

Extract, process, analyze, and visualize simulation results using
numpy and matplotlib. Generate performance reports and export data.

## Prerequisites

```python
import sys, os
# Use CLAUDE_PLUGIN_ROOT set by Claude Code at runtime
_plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
if _plugin_root:
    sys.path.insert(0, os.path.join(_plugin_root, 'scripts'))
from zos_utils import ZOSConnection
import numpy as np
import matplotlib.pyplot as plt
```

Execute with the Python interpreter documented in `references/environment.md`.

## Core Patterns

### Data Flow

Data extraction (`.NET` array → Python) is handled by the `analysis` skill.
This skill takes already-extracted Python data and processes it.

### Plotting with matplotlib

Always save figures to files (`plt.savefig()`) for reliability.
Use `plt.show()` only in interactive environments.

```python
import matplotlib.pyplot as plt
import numpy as np

# Data should already be extracted by the analysis skill
# Example: mtf_data = [{'frequency': [...], 'tangential': [...], 'sagittal': [...]}, ...]

plt.figure(figsize=(8, 6))
plt.plot(mtf_data[0]['frequency'], mtf_data[0]['tangential'], 'b', label='0° T')
plt.plot(mtf_data[0]['frequency'], mtf_data[0]['sagittal'], 'b--', label='0° S')
plt.title('FFT MTF')
plt.xlabel('Spatial Frequency (cycles/mm)')
plt.ylabel('Modulus of the OTF')
plt.grid(True)
plt.legend()
plt.savefig('mtf_plot.png', dpi=150)
```

## Common Plot Templates

### MTF Plot (from extracted mtf_data)

```python
# mtf_data comes from the analysis skill (FFT MTF → extract)
colors = ('b', 'g', 'r', 'c', 'm', 'y', 'k')
field_labels = ['0°', '14°', '20°']  # adjust to match actual fields

plt.figure(figsize=(8, 6))
for i, field_data in enumerate(mtf_data):
    color = colors[i % len(colors)]
    plt.plot(field_data['frequency'], field_data['tangential'],
             color=color, label=f'{field_labels[i]} T')
    plt.plot(field_data['frequency'], field_data['sagittal'],
             '--', color=color, label=f'{field_labels[i]} S')

plt.title('FFT MTF')
plt.xlabel('Spatial Frequency (cycles/mm)')
plt.ylabel('Modulus of the OTF')
plt.grid(True)
plt.legend()
plt.savefig('mtf_plot.png', dpi=150)
```

### Spot Diagram (from batch ray trace data)

```python
# x_ary and y_ary come from the ray-tracing skill (batch ray trace results)
# Shape: x_ary[num_fields, num_wavelengths, num_rays]
num_fields = x_ary.shape[0]
num_wavelengths = x_ary.shape[1]

plt.figure(figsize=(12, 4))
colors = ('b', 'g', 'r', 'c', 'm', 'y', 'k')

for field in range(num_fields):
    plt.subplot(1, num_fields, field + 1, aspect='equal')
    plt.title(f'Field {field + 1}')

    for wave in range(num_wavelengths):
        x = x_ary[field, wave, :]
        y = y_ary[field, wave, :]
        # Filter out zero entries (missed rays)
        mask = (x != 0) | (y != 0)
        plt.plot(x[mask], y[mask], '.', ms=1, color=colors[wave % len(colors)])

plt.suptitle('Spot Diagram')
plt.subplots_adjust(wspace=0.8)
plt.savefig('spot_diagram.png', dpi=150)
```

### NSC Detector Heatmap

```python
# detector_data, x_half_width, y_half_width come from the
# non-sequential-modeling skill (detector property readout)

plt.figure(figsize=(8, 6))
plt.imshow(detector_data, extent=[
    -x_half_width, x_half_width,
    -y_half_width, y_half_width
])
plt.colorbar(label='Irradiance')
plt.title('NSC Detector Data')
plt.xlabel('X position (mm)')
plt.ylabel('Y position (mm)')
plt.savefig('detector_heatmap.png', dpi=150)
```

### RMS Spot Size Bar Chart

```python
# spot_results comes from the analysis skill (StandardSpot analysis)
num_fields = spot_results.SpotData.NumberOfFields

rms_values = [spot_results.SpotData.GetRMSSpotSizeFor(f, 1) for f in range(1, num_fields + 1)]
geo_values = [spot_results.SpotData.GetGeoSpotSizeFor(f, 1) for f in range(1, num_fields + 1)]

x = np.arange(num_fields)
width = 0.35

plt.figure(figsize=(8, 5))
plt.bar(x - width/2, rms_values, width, label='RMS')
plt.bar(x + width/2, geo_values, width, label='GEO')
plt.xlabel('Field')
plt.ylabel('Spot Radius (µm)')
plt.title('Spot Size by Field')
plt.xticks(x, [f'Field {f+1}' for f in range(num_fields)])
plt.legend()
plt.grid(axis='y')
plt.savefig('spot_sizes.png', dpi=150)
```

## Exporting Data

### To CSV

```python
import csv

with open('analysis_results.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Field', 'RMS_Spot_Radius', 'GEO_Spot_Radius'])
    for field in range(1, num_fields + 1):
        rms = spot_results.SpotData.GetRMSSpotSizeFor(field, 1)
        geo = spot_results.SpotData.GetGeoSpotSizeFor(field, 1)
        writer.writerow([field, rms, geo])
```

### To NumPy Array

```python
# Convert detector data to numpy for advanced processing
detector_array = np.array(detector_data)

# Compute statistics
total_power = np.sum(detector_array)
peak_irradiance = np.max(detector_array)
centroid_x = np.sum(np.sum(detector_array, axis=0) * np.arange(detector_array.shape[1]))
centroid_y = np.sum(np.sum(detector_array, axis=1) * np.arange(detector_array.shape[0]))
print(f"Total power: {total_power:.2e}")
print(f"Peak irradiance: {peak_irradiance:.2e}")
```

## Report Generation Template

```python
def generate_report(filename, spot_data, mtf_data):
    """Generate a text performance report from pre-extracted data.

    Args:
        filename: Output report path (.txt or .md)
        spot_data: dict with 'rms' and 'geo' lists keyed by field number
        mtf_data: list of dicts with 'frequency', 'tangential', 'sagittal' keys
    """
    with open(filename, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("OPTICAL PERFORMANCE REPORT\n")
        f.write("=" * 60 + "\n\n")

        f.write("--- Spot Sizes ---\n")
        f.write(f"{'Field':<10} {'RMS (µm)':<12} {'GEO (µm)':<12}\n")
        f.write("-" * 34 + "\n")
        for field_num in sorted(spot_data.keys()):
            rms, geo = spot_data[field_num]
            f.write(f"{field_num:<10} {rms:<12.3f} {geo:<12.3f}\n")

        f.write("\n--- MTF Summary ---\n")
        for i, field_data in enumerate(mtf_data):
            t0 = field_data['tangential'][0]
            s0 = field_data['sagittal'][0]
            f.write(f"Field {i+1}: T={t0:.4f}, S={s0:.4f} "
                    f"(at low freq)\n")

    print(f"Report saved: {filename}")
```

## Notes

- Always call `plt.show()` AFTER closing the ZOS connection
- Use `plt.savefig()` instead of `plt.show()` for non-interactive report generation
- For large detector arrays, use numpy vectorized operations instead of Python loops
- Set figure DPI for publication-quality output: `plt.figure(dpi=150)`
- Multi-page reports can use `matplotlib.backends.backend_pdf.PdfPages`
