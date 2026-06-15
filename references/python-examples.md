# ZOS-API Python Examples Reference

Annotated patterns extracted from official Zemax 2025 R2 Python examples.

## Source Directory

```
C:\Apps\ANSYS Inc\v252\Zemax OpticStudio\ZemaxData\ZOS-API Sample Code\Python\
```

## Example Index

| # | File | Topic |
|---|------|-------|
| 01 | `PythonStandalone_01_new_file_and_quickfocus.py` | New system, LDE, QuickFocus |
| 02 | `PythonStandalone_02_NSC_ray_trace.py` | NSC ray trace, detector data |
| 03 | `PythonStandalone_03_open_file_and_optimise.py` | MFE, DLS, Hammer optimization |
| 04 | `PythonStandalone_04_pull_data_from_FFTMTF.py` | FFT MTF analysis, data extraction |
| 05 | `PythonStandalone_05_Read_ZRD_File.py` | ZRD ray database reading |
| 06 | `PythonStandalone_06_nsc_phase.py` | NSC phase data |
| 07 | `PythonStandalone_07_TiltDecenterAndMFOperand.py` | Tilt/decenter, MFE operands |
| 08 | `PythonStandalone_08_NSCEDetectorData.py` | NSC detector data (advanced) |
| 09 | `PythonStandalone_09_NSC_CAD.py` | NSC CAD import |
| 10 | `PythonStandalone_10_NSC_ZRD_filter_string.py` | ZRD filtering |
| 11 | `PythonStandalone_11_BASIC_SEQ.py` | Sequential mode basics |
| 12 | `PythonStandalone_12_SEQ_SystemExplorer.py` | System Explorer settings |
| 14 | `PythonStandalone_14_Seq_Tolerance.py` | Tolerance wizard & analysis |
| 15 | `PythonStandalone_15_Seq_Optimization.py` | Advanced optimization |
| 17 | `PythonStandalone_17_NSC_BulkScatter.py` | Bulk scattering in NSC |
| 18 | `PythonStandalone_18_SetMultiConfiguration.py` | Multi-configuration systems |
| 19 | `PythonStandalone_19_Surface_Properties.py` | Surface properties & coatings |
| 20 | `PythonStandalone_20_export_CAD_File.py` | CAD export to STEP |
| 21 | `PythonStandalone_21_White_LED_Phosphor.py` | White LED with phosphor |
| 22 | `PythonStandalone_22_seq_spot_diagram.py` | Batch ray trace + spot diagram |
| 23 | `PythonStandalone_23_ray_fan_native_manual_comparison.py` | Ray fan analysis |
| 24 | `PythonStandalone_24_nsc_detectors.py` | NSC detectors (advanced) |
| 25 | `PythonStandalone_25_source_spectrum_diffraction_grating.py` | Spectrum & diffraction |
| 26 | `PythonStandalone_26_modify_opticstudio_preferences.py` | OpticStudio preferences |

## Universal Pattern (All Examples)

Every official example follows this structure:

```python
import clr, os, winreg
from itertools import islice

class PythonStandaloneApplication(object):
    # Exception classes
    # __init__: registry → NetHelper → Initialize → ZOSAPI.dll → Connection → Application → System
    # __del__: CloseApplication
    # OpenFile / CloseFile / SamplesDir
    # reshape / transpose utilities

if __name__ == '__main__':
    zos = PythonStandaloneApplication()
    ZOSAPI = zos.ZOSAPI
    TheApplication = zos.TheApplication
    TheSystem = zos.TheSystem
    # ... work ...
    del zos
    zos = None
```

AutoZemax's `zos_utils.py` encapsulates this pattern into a clean `ZOSConnection`
class with context manager support, eliminating the need for boilerplate in
each generated script.

## Key Patterns Learned

### 1. .NET Array → Python Conversion

The official `reshape()` method converts `System.Double[,]` to 2D Python lists:

```python
def reshape(data, x, y, transpose=False):
    if type(data) is not list:
        data = list(data)
    var_lst = [y] * x
    it = iter(data)
    res = [list(islice(it, i)) for i in var_lst]
    if transpose:
        return transpose(res)
    return res
```

### 2. Solves via Cell Pattern

Solves are created through the cell system, not set directly:

```python
solver = surface.RadiusCell.CreateSolveType(ZOSAPI.Editors.SolveType.FNumber)
solver._S_FNumber.FNumber = 10.0
surface.RadiusCell.SetSolveData(solver)
```

### 3. Tool Lifecycle

All tools follow: Open → Configure → Run → WaitForCompletion → Close

```python
tool = TheSystem.Tools.OpenSomething()
tool.Property = value
tool.RunAndWaitForCompletion()
tool.Close()
```

### 4. Analysis Results Extraction

```python
analysis = TheSystem.Analyses.New_Analysis(id)
analysis.ApplyAndWaitForCompletion()
results = analysis.GetResults()
for i in range(results.NumberOfDataSeries):
    series = results.GetDataSeries(i)
    x = list(series.XData.Data)
    y = zos.reshape(series.YData.Data, rows, cols)
```

### 5. matplotlib After ZOS Cleanup

Always close the ZOS connection before `plt.show()`:

```python
del zos
zos = None
plt.show()
```

## Environment Verification

The official examples use this Python path pattern:

```python
# Python 3.x with pythonnet installed
# clr module bridges .NET assemblies into Python
import clr
```

The environment Python must have `pythonnet` installed for `clr` to work.
