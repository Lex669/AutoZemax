# ZOS-API Quick Reference

Key classes and methods from the Zemax OpticStudio API (v252).

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
- `LoadFile(filepath, saveIfNeeded)` — Open .zos file
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
- `TiltX`, `TiltY`, `TiltZ` — Orientation
- `Material` — Material name

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

## Enums Quick Reference

- **FieldType**: Angle, ObjectHeight, ParaxialImageHeight, RealImageHeight
- **WavelengthPreset**: d_0p587, F_0p486, C_0p656, etc.
- **SolveType**: FNumber, MarginalRayAngle, PickUp, etc.
- **OptimizationAlgorithm**: DampedLeastSquares, OrthoDescent
- **OptimizationCycles**: Automatic, Fixed
- **CADFileType**: STEP, IGES, SAT, STL
- **CADToleranceType**: N_TenEMinus4 through N_TenEMinus7
- **SplineSegmentsType**: N_032 through N_256
- **SetupModes**: Sensitivity, InverseSensitivity, MonteCarlo
- **Criterions**: RMSSpotRadius, RMSWavefront, MTF, etc.
