---
name: multi-configuration
description: This skill should be used when the user asks to "multi configuration", "zoom lens", "multi-config", "add configuration", "set config operand", "config parameter", "MCE", "multi-configuration editor", "zoom system", "multiple configurations", or configures multi-state systems in the Zemax Multi-Configuration Editor.
version: 0.2.0
---

# Multi-Configuration Editor (MCE) — Zoom Lenses & Multi-State Systems

Manage multiple configurations in a single optical system file for zoom
lenses, switchable illumination paths, or any design with varying parameters
across states. Covers the Multi-Configuration Editor (MCE), adding
configurations, and setting operands (THIC, CRVT, PRAM, WLWT).
Corresponds to ZOS-API Sample 18.

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

## Multi-Configuration Concepts

A multi-configuration system stores multiple "states" in one file. Each
state can have different thicknesses, curvatures, glasses, semi-diameters,
or any other configurable parameter. This is how zoom lenses work — the same
group of surfaces takes on different airspaces (and sometimes curvatures) at
each zoom position.

The MCE (Multi-Configuration Editor) has two dimensions:
- **Columns** = Configurations (zoom positions, focus states, etc.)
- **Rows** = Operands (which parameter changes and where)

The `zos.add_configuration()` and `zos.set_config_operand()` library
functions wrap the MCE API with proper error handling.

## Adding Configurations

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    MCE = TheSystem.MCE

    # Check current state
    n_configs = MCE.NumberOfConfigurations
    print(f"Current configurations: {n_configs}")

    # Add configurations for a 3x zoom lens
    # Library wrapper checks if config already exists
    zos.add_configuration(1)  # Wide
    zos.add_configuration(2)  # Mid
    zos.add_configuration(3)  # Tele

    print(f"Configurations after: {MCE.NumberOfConfigurations}")
    # Each new config duplicates the current system state
```

## Setting Multi-Configuration Operands

Use `zos.set_config_operand()` to define which parameter changes in each
configuration. The library function calls `MCE.GetOperand()` and sets
Param1 through Param4 as needed.

### THIC — Thickness Control (most common for zoom)

```python
# Surface 2 thickness in configuration 2 (Mid zoom)
zos.set_config_operand(
    config_num=2,
    operand_type=ZOSAPI.Editors.MCE.MultiConfigOperandType.THIC,
    param1=2      # Surface number
)
# Now set the value via the returned operand object (cell 1 = value)
op = zos.set_config_operand(2, ZOSAPI.Editors.MCE.MultiConfigOperandType.THIC, 2)
op.GetCellAt(1).DoubleValue = 25.0

# Surface 3 thickness in configuration 3 (Tele zoom)
op = zos.set_config_operand(3, ZOSAPI.Editors.MCE.MultiConfigOperandType.THIC, 3)
op.GetCellAt(1).DoubleValue = 5.0
```

### Bulk Setup — Complete Zoom Lens Example

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    MCE = TheSystem.MCE

    # Load a zoom lens design (Sample 18)
    zos.open_file(zos.samples_dir() +
        "\\Sequential\\Objectives\\Cooke 40 degree field.zos")

    # Ensure 3 configurations exist
    for cfg in [1, 2, 3]:
        zos.add_configuration(cfg)

    # Define airspace changes for each zoom position
    # Surface 2-3 airspace = zooming group
    zoom_configs = {
        1: {2: 35.0, 3: 10.0},  # Wide: thick airspace, thin rear
        2: {2: 20.0, 3: 25.0},  # Mid: balanced
        3: {2: 5.0,  3: 40.0},  # Tele: thin airspace, thick rear
    }

    for cfg_num, surfaces in zoom_configs.items():
        for surf_num, thick in surfaces.items():
            op = zos.set_config_operand(
                cfg_num,
                ZOSAPI.Editors.MCE.MultiConfigOperandType.THIC,
                surf_num
            )
            op.GetCellAt(1).DoubleValue = thick
            print(f"Config {cfg_num}, Surf {surf_num}: thickness = {thick} mm")
```

### CRVT — Curvature Operand

Control the inverse radius of a surface per configuration. Useful for
focus or aberration balancing across zoom positions.

```python
# Vary surface 5 curvature in configuration 3
op = zos.set_config_operand(
    3,
    ZOSAPI.Editors.MCE.MultiConfigOperandType.CRVT,
    5          # Surface number
)
# Curvature = 1 / Radius. R=100mm → C=0.01
op.GetCellAt(1).DoubleValue = 0.01

# Surface 6 curvature in configuration 1
op = zos.set_config_operand(
    1,
    ZOSAPI.Editors.MCE.MultiConfigOperandType.CRVT,
    6
)
op.GetCellAt(1).DoubleValue = 0.008
```

### PRAM — Surface Parameter Operand

Control extra data parameters (aspheric coefficients, grating lines, etc.)
per configuration. Param2 specifies the parameter number.

```python
# Vary the 4th-order aspheric coefficient (parameter 1) on surface 4
op = zos.set_config_operand(
    2,
    ZOSAPI.Editors.MCE.MultiConfigOperandType.PRAM,
    4,         # Surface number
    1          # Parameter number (1 = 4th order term)
)
op.GetCellAt(1).DoubleValue = -1.5e-6

# Vary parameter 2 (6th-order term) on surface 4
op = zos.set_config_operand(
    2,
    ZOSAPI.Editors.MCE.MultiConfigOperandType.PRAM,
    4,
    2
)
op.GetCellAt(1).DoubleValue = 2.3e-8
```

### WLWT — Wavelength Weight Operand

Vary the weight of a specific wavelength per configuration. Useful for
multi-spectral or variable-filter systems.

```python
# Set wavelength 2 weight in configuration 1
op = zos.set_config_operand(
    1,
    ZOSAPI.Editors.MCE.MultiConfigOperandType.WLWT,
    2          # Wavelength number
)
op.GetCellAt(1).DoubleValue = 1.0

# Disable wavelength 2 in configuration 2
op = zos.set_config_operand(
    2,
    ZOSAPI.Editors.MCE.MultiConfigOperandType.WLWT,
    2
)
op.GetCellAt(1).DoubleValue = 0.0
```

### GLAS — Glass Operand

Swap glass types between configurations. Param1 = surface number.

```python
# Different glass for surface 2 in configuration 3
op = zos.set_config_operand(
    3,
    ZOSAPI.Editors.MCE.MultiConfigOperandType.GLAS,
    2
)
# Set glass string via cell 2 (not cell 1 — glass is a string column)
op.GetCellAt(2).StringValue = 'N-SF5'
```

## Reading Back Configuration Data

```python
with ZOSConnection() as zos:
    MCE = zos.TheSystem.MCE

    # Iterate all operands and configurations
    for op_idx in range(1, MCE.NumberOfOperands + 1):
        for cfg_idx in range(1, MCE.NumberOfConfigurations + 1):
            cell_value = MCE.GetOperandCell(cfg_idx, op_idx)
            op_type = MCE.GetOperandAt(op_idx).OperandType
            print(f"Operand {op_idx} ({op_type}), "
                  f"Config {cfg_idx}: {cell_value}")
```

## Complete Zoom Lens Workflow

```python
with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    MCE = TheSystem.MCE
    SD = TheSystem.SystemData

    # 1. Create base lens (e.g., a Cooke triplet)
    TheSystem.New(False)
    SD.MaterialCatalogs.AddCatalog('SCHOTT')
    SD.Aperture.ApertureValue = 25.0
    SD.Wavelengths.SelectWavelengthPreset(
        ZOSAPI.SystemData.WavelengthPreset.d_0p587)
    SD.Fields.AddField(0.0, 14.0, 1.0)

    # Build lens surfaces (simplified example)
    LDE = TheSystem.LDE
    for _ in range(5):
        LDE.InsertNewSurfaceAt(2)
    # (configure radii, thicknesses, glasses — see sequential-modeling skill)

    # 2. Add three zoom configurations
    for cfg in [1, 2, 3]:
        zos.add_configuration(cfg)

    # 3. Set zoom airspaces
    config_data = {
        1: {2: 30.0, 3: 15.0},  # Wide
        2: {2: 18.0, 3: 27.0},  # Mid
        3: {2: 6.0,  3: 39.0},  # Tele
    }
    for cfg_num, surfaces in config_data.items():
        for surf_num, thick in surfaces.items():
            op = zos.set_config_operand(
                cfg_num,
                ZOSAPI.Editors.MCE.MultiConfigOperandType.THIC,
                surf_num
            )
            op.GetCellAt(1).DoubleValue = thick

    # 4. Set variables and optimize each configuration
    for i in range(2, LDE.NumberOfSurfaces):
        LDE.GetSurfaceAt(i).RadiusCell.MakeSolveVariable()
        LDE.GetSurfaceAt(i).ThicknessCell.MakeSolveVariable()

    # 5. Set up multi-configuration merit function
    MFE = TheSystem.MFE
    MFE.RemoveOperands(1, MFE.NumberOfOperands)
    MFE.MakeMeritFunction(
        ZOSAPI.Editors.MFE.MeritFunctionType.RMS,
        ZOSAPI.Tools.Optimization.OptimizationOperandType.SpotRadius,
        1, 0, 0.0, SD.Wavelengths.NumberOfWavelengths,
        0.0, 0.0, 0.0, True)

    # 6. Optimize
    zos.run_dls_optimization()

    # 7. Save multi-config file
    zos.save_file(zos.ensure_zmx_dir() + "\\zoom_lens_3x.zmx")
```

## Common Multi-Config Operand Types

| Type | Description | Param1 | Param2 |
|------|-------------|--------|--------|
| THIC | Thickness | Surface number | — |
| CRVT | Curvature (1/Radius) | Surface number | — |
| PRAM | Surface parameter | Surface number | Parameter index |
| WLWT | Wavelength weight | Wavelength number | — |
| GLAS | Glass type | Surface number | — |
| SDIA | Semi-diameter | Surface number | — |
| TTHI | Thickness sum | Start surface | End surface |
| CONI | Conic constant | Surface number | — |
| NPAR | NSC object parameter | Object number | Parameter number |
| NXTP | NSC object position X/Y/Z | Object number | Axis (1=X, 2=Y, 3=Z) |

## Notes

- Adding a configuration duplicates all current parameter values — set
  operand values AFTER calling `zos.add_configuration()`
- Configuration numbers are 1-based
- The MCE is independent of the LDE — changing a THIC operand does NOT
  change the LDE thickness in the current view; it only stores the
  alternate value for that configuration
- Always set `op.GetCellAt(1).DoubleValue` for numeric operands (THIC,
  CRVT, PRAM). For GLAS, use `op.GetCellAt(2).StringValue`
- Use `zos.validate_system_ready()` before adding surfaces to the base
  lens to verify aperture, fields, and wavelengths are configured
- Run optimization with all configurations active — Zemax optimizes the
  compound merit function across all configurations simultaneously
- For zoom lenses, set THIC on the airspaces that change between zoom
  groups; keep internal element thicknesses fixed across configurations
- The library wrappers `zos.add_configuration()` and
  `zos.set_config_operand()` handle the MCE API boilerplate — use them
  instead of raw `MCE.AddConfiguration()` to avoid duplicate-config errors
- Use `zos.run_dls_optimization()` after setting up MCE operands — it
  naturally optimizes across all active configurations when the merit
  function includes multi-config operands
