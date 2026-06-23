# ZOS-API Quick Reference (v0.2.0)

Key classes and methods from the Zemax OpticStudio API (v252).
For library wrappers, see `scripts/zos_utils.py`.

## Connection & Application

```python
# Connection setup (handled by zos_utils.ZOSConnection)
TheConnection = ZOSAPI.ZOSAPI_Connection()
TheApplication = TheConnection.CreateNewApplication()
TheSystem = TheApplication.PrimarySystem
```

### IApplication Properties
- `PrimarySystem` — The current optical system
- `SamplesDir` — Path to Zemax sample files
- `ObjectsDir` — Path to object catalogs
- `LicenseStatus` — LicenseStatusType enum
- `IsValidLicenseForAPI` — bool

## System Operations

### ISystem — Core
- `LoadFile(filepath, saveIfNeeded)` — Open .zos/.zmx/.zda file
- `New(flag)` — Create new system
- `Save()` / `SaveAs(filepath)` — Save system
- `Close(save)` — Close system

### Editors
- `LDE` — ILensDataEditor (sequential surfaces)
- `NCE` — INonSeqEditor (non-sequential components)
- `MFE` — IMeritFunctionEditor (optimization operands)
- `TDE` — IToleranceDataEditor (tolerances)

### System Data
- `SystemData` — ISystemData
  - `Aperture` — Aperture settings (ApertureValue, ApertureType)
  - `Fields` — Field points (GetField, AddField, NumberOfFields)
  - `Wavelengths` — Wavelength data (SelectWavelengthPreset, NumberOfWavelengths)
  - `MaterialCatalogs` — AddCatalog("SCHOTT") etc.

### Tools
- `Tools.OpenQuickFocus()` — Quick focus tool
- `Tools.OpenLocalOptimization()` — Local optimization
- `Tools.OpenHammerOptimization()` — Global Hammer optimization
- `Tools.OpenNSCRayTrace()` — NSC ray trace
- `Tools.OpenBatchRayTrace()` — Sequential batch ray trace
- `Tools.OpenTolerancing()` — Tolerance analysis
- `Tools.OpenExportCAD()` — CAD export
- `Tools.OpenConvertToNSCGroup()` — Convert seq to non-seq

## Sequential Mode (LDE)

### ILensDataEditor
- `NumberOfSurfaces` — int
- `InsertNewSurfaceAt(position)` — Insert surface
- `RemoveSurfaceAt(position)` — Remove surface
- `GetSurfaceAt(position)` — Returns ILDERow

### ILDERow
- `Radius` / `RadiusCell` — Surface curvature
- `Thickness` / `ThicknessCell` — Thickness to next surface
- `Material` / `MaterialCell` — Glass/material name
- `Comment` / `CommentCell` — Surface comment
- `Glass` / `GlassCell` — Glass catalog entry
- `Coating` / `CoatingCell` — Surface coating

### Solves (via Cells)
```python
# F/# solve on radius
solver = surface.RadiusCell.CreateSolveType(ZOSAPI.Editors.SolveType.FNumber)
solver._S_FNumber.FNumber = 10.0
surface.RadiusCell.SetSolveData(solver)

# Make variable for optimization
surface.ThicknessCell.MakeSolveVariable()
surface.RadiusCell.MakeSolveVariable()
```

## Analysis

### IAnalyses
```python
analyses = TheSystem.Analyses
# Create specific analyses:
analyses.New_FftMtf()        # FFT MTF
analyses.New_BatRayTrace()   # Batch ray trace
analyses.New_Analysis(AnalysisIDM.StandardSpot)  # Spot diagram
analyses.New_Analysis(AnalysisIDM.WavefrontMap)  # Wavefront
analyses.New_Analysis(AnalysisIDM.FFTPSF)        # FFT PSF
analyses.New_Analysis(AnalysisIDM.RayFan)        # Ray fan
```

### IAnalysis (window)
- `GetSettings()` — Returns settings interface
- `ApplyAndWaitForCompletion()` — Run analysis
- `GetResults()` — Returns IAnalysisResults

### IAnalysisResults
- `NumberOfDataSeries` — int
- `GetDataSeries(index)` — Returns IDataSeries
- `SpotData.GetRMSSpotSizeFor(field, wave)` — RMS spot radius
- `SpotData.GetGeoSpotSizeFor(field, wave)` — GEO spot radius

### IDataSeries
- `XData.Data` — X-axis values (System.Double[])
- `YData.Data` — Y-axis values (System.Double[,])

## NSC Mode (NCE)

### INonSeqEditor
- `NumberOfObjects` — int
- `GetObjectAt(position)` — Returns INSCEditorRow
- `GetDetectorData(detObj, pixel, dataType, flux)` — Read detector

### INSCEditorRow
- `ObjectData` — Object properties
- `XPosition`, `YPosition`, `ZPosition` — Placement
- `TiltAboutX`, `TiltAboutY`, `TiltAboutZ` — Orientation (degrees).
  CRITICAL: `TiltX`/`TiltY`/`TiltZ` do NOT exist on the .NET interface;
  pythonnet will silently create Python-only attributes that are ignored
  by Zemax. Always use `TiltAboutX`/`TiltAboutY`/`TiltAboutZ`.
- `Material` — Material name
- `Coating` — Coating name (e.g. "I.50" for 50% intensity split)

## Optimization

### IMeritFunctionEditor
- `NumberOfOperands` — int
- `GetOperandAt(position)` — Returns IMeritFunctionRow
- `InsertNewOperandAt(position)` — Insert operand
- `AddOperand()` — Append operand

### IMeritFunctionRow
- `ChangeType(MeritOperandType)` — Set operand type
- `Target` — Target value
- `Weight` — Weight
- `GetCellAt(col).IntegerValue` / `DoubleValue` — Cell access

### Common Merit Operand Types
- `ASTI` — Astigmatism
- `COMA` — Coma
- `SPHA` — Spherical aberration
- `DIST` — Distortion
- `EFFL` — Effective focal length
- `MNCA` / `MXCA` — Min/max center air thickness
- `MNEA` / `MXEA` — Min/max edge air thickness
- `MNCG` / `MXCG` — Min/max center glass thickness
- `MNEG` / `MXEG` — Min/max edge glass thickness

## Tolerance Analysis

### ITolerancingTool
- `SetupMode` — SetupModes enum (Sensitivity, InverseSensitivity, MonteCarlo)
- `Criterion` — Criterions enum (RMSSpotRadius, RMSWavefront, MTF, etc.)
- `CriterionSampling` — Sampling density
- `CriterionComp` — CriterionComps enum (OptimizeAll_DLS, etc.)
- `CriterionCycle` — Optimization cycles
- `CriterionField` — CriterionFields enum
- `NumberOfRuns` — Monte Carlo trials
- `NumberToSave` — Files to save
- `RunAndWaitForCompletion()`

### IToleranceDataEditor (TDE)
- `SEQToleranceWizard` — The tolerance wizard
  - Surface tolerances: SurfaceRadius, SurfaceThickness, SurfaceDecenterX/Y, SurfaceTiltX/Y
  - Element tolerances: ElementDecenterX/Y, ElementTiltXDegrees/YDegrees
  - Flags: IsSurfaceSandAIrregularityUsed, IsIndexUsed, IsIndexAbbePercentageUsed
  - `OK()` — Apply and close wizard

## CAD Export

### IExportCAD
- `FirstObject` / `LastObject` — Object range
- `RayLayer` / `LensLayer` / `DummyThickness` — Layers
- `SplineSegments` — SplineSegmentsType enum
- `FileType` — CADFileType enum (STEP, IGES, SAT, STL)
- `Tolerance` — CADToleranceType enum
- `SetCurrentConfiguration()` — Current config only
- `SurfacesAsSolids` / `ScatterNSCRays` / `ExportDummySurfaces` — Options
- `SplitNSCRays` / `UsePolarization` — Options
- `OutputFileName` — Full output path
- `Run()` / `WaitWithTimeout(seconds)` / `Cancel()` / `Close()`

## Multi-Configuration

### IMultiConfigEditor (MCE)
- `NumberOfConfigurations` — int
- `AddConfiguration(configNum)` — Add configuration
- `GetOperand(configNum, operandType)` — Returns IMCERow
- `GetOperandValue(configNum, operandType)` — Read current value

### Common Multi-Config Operand Types
- `THIC` — Thickness
- `CRVT` — Curvature (1/radius)
- `PRAM` — Aspheric parameter
- `WLWT` — Wavelength weight
- `TEXI` — Tilt/Decenter X
- `GLAS` — Glass type
- `SDIA` — Semi-diameter
- `COFN` — Configuration offset

## NSC Scattering & Phosphors

### Volume Physics (per object)
```python
obj = TheNCE.GetObjectAt(n)
vp = obj.VolumePhysics  # IVolumePhysics
```
- `ScatteringModel` — 0=None, 1=Mie, 2=Rayleigh, 4=Phosphor
- `MieAnisotropy` — g factor (-1 to 1)
- `MeanPath` — Mean free path (mm)
- `ParticlesPerCubicMm` — Particle density
- `PhosphorQuantumEfficiency` — QE (0-1)

### Phosphor Wavelength Setup
- Excitation wavelength as system wavelength 1
- Emission wavelengths as wavelengths 2+
- DetectorVolume with phosphor scattering for conversion measurement

## Diffraction Gratings

```python
surface = TheLDE.GetSurfaceAt(n)
surface.ChangeType(ZOSAPI.Editors.LDE.SurfaceType.DiffractionGrating)
surface.GetCellAt(12).DoubleValue = lines_per_um  # 0.5 = 2 µm period
surface.GetCellAt(13).IntegerValue = order          # Diffraction order
```

## CAD Import (NSC)

```python
# Via library:
obj = zos.import_cad(filename, cad_format='STEP', obj_number=1, material='MIRROR')

# Direct API:
TheNCE.ImportCADFile(filename, ZOSAPI.Editors.NCE.CADImportFormat.STEP, objNum)
```

## NSC Detector Data Types

| Data Type | Value | Description |
|-----------|-------|-------------|
| Incoherent Irradiance | 0 | Total power per pixel |
| Coherent Irradiance | 1 | Phase-aware irradiance |
| Coherent Phase | 2 | Phase distribution |
| Real Part | 3 | Real field component |
| Imaginary Part | 4 | Imaginary field component |

## Library Wrapper Reference (zos_utils.py v0.2.0)

For common operations, use library wrappers instead of raw API:

| Library Function | Raw API Equivalent |
|-----------------|-------------------|
| `zos.extract_mtf_data(results)` | Manual DataSeries iteration |
| `zos.extract_spot_data(results)` | SpotData.GetRMSSpotSizeFor() |
| `zos.extract_wavefront_data(results)` | DataSeries + safe_reshape() |
| `zos.create_nsc_detector(n, type, ...)` | NCE.GetObjectAt + ChangeType + cell config |
| `zos.create_nsc_source(n, type, ...)` | NCE.GetObjectAt + ChangeType + cell config |
| `zos.run_dls_optimization(cycles)` | OpenLocalOptimization + RunAndWaitForCompletion |
| `zos.run_hammer_optimization(timeout)` | OpenHammerOptimization + correct cancel logic |
| `zos.run_tolerance_sensitivity()` | OpenTolerancing + SetSensitivity |
| `zos.run_tolerance_monte_carlo(n)` | OpenTolerancing + SetMonteCarlo |
| `zos.export_cad(filename, format)` | OpenCadExport + format/cells setup |
| `zos.import_cad(filename, format, n)` | NCE.ImportCADFile |
| `plot_mtf(data, title)` | matplotlib boilerplate |
| `plot_spot_diagram(data, title)` | matplotlib bar chart |
| `plot_detector_data(data_2d, title)` | matplotlib imshow |

## Enums Quick Reference

- **SystemType**: Sequential, NonSequential
- **FieldType**: Angle, ObjectHeight, ParaxialImageHeight, RealImageHeight
- **WavelengthPreset** (in `ZOSAPI.SystemData`):
  `d_0p587`, `F_0p486`, `C_0p656`, `HeNe_0p6328`, `FdC_Visible`, etc.
- **SolveType**: FNumber, MarginalRayAngle, PickUp, Position, etc.
- **OptimizationAlgorithm**: DampedLeastSquares, OrthoDescent
- **OptimizationCycles**: Automatic, Fixed
- **CADFileType**: STEP, IGES, SAT, STL
- **CADToleranceType**: N_TenEMinus4 through N_TenEMinus7
- **SplineSegmentsType**: N_032 through N_256
- **SetupModes**: Sensitivity, InverseSensitivity, MonteCarlo
- **Criterions**: RMSSpotRadius, RMSWavefront, MTF, etc.
- **NSC Object Types**: SourceElliptical, SourcePoint, SourceCollimated, SourceRectangle, DetectorRectangle, DetectorSurface, DetectorVolume, CADPart, etc.
- **Surface Type**: Standard, EvenAspheric, DiffractionGrating, CoordinateBreak, etc.
- **ScatteringModel**: None=0, Mie=1, Rayleigh=2, Phosphor=4
- **ApodizationType**: 0=Uniform, 1=Gaussian, 2=CosineCubed
- **AnalysisIDM**: StandardSpot, FFTMTF, FFTPSF, WavefrontMap, RayFan, FieldCurvatureDistortion, LateralColor, RMSWavefront
- **DetectorDataType** (for `GetAllDetectorDataSafe`): 0=Incoherent, 1=Coherent, 2=Phase, 3=Real, 4=Imaginary
- **MultiConfigOperandType**: THIC, CRVT, PRAM, WLWT, TEXI, GLAS, SDIA, COFN
