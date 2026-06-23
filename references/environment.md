# AutoZemax Python Environment (v0.2.0)

## Python Interpreter

**Path:** `C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe`

This is the Python 3.14 64-bit interpreter bundled with the system. It has
`pythonnet` (`clr` module) pre-installed for .NET interop with ZOS-API.

## Required Packages

| Package | Purpose | Import |
|---------|---------|--------|
| `pythonnet` | .NET CLR interop for ZOS-API | `import clr` |
| `numpy` | Numerical array operations | `import numpy as np` |
| `matplotlib` | Plotting and visualization | `import matplotlib.pyplot as plt` |

## Verify Environment

```powershell
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "
import clr
import numpy as np
import matplotlib.pyplot as plt
print('numpy:', np.__version__)
print('matplotlib:', plt.matplotlib.__version__)
print('pythonnet (clr): OK')
print('All packages available.')
"
```

## Zemax Installation

**Version:** Ansys Zemax OpticStudio 2025 R2 (v252)
**Install Path:** `C:\Apps\ANSYS Inc\v252\Zemax OpticStudio`

ZOS-API assemblies:
- `ZOSAPI_NetHelper.dll` — `{ZemaxRoot}\ZOS-API\Libraries\`
- `ZOSAPI.dll` — `{ZemaxRoot}\`
- `ZOSAPI_Interfaces.dll` — `{ZemaxRoot}\`

## Running Scripts

All AutoZemax scripts are executed with:

```powershell
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" "<script_path>"
```

### Standard Import Block

Every generated script uses the compact import and path resolution:

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

This resolves the `scripts/` directory across three locations:
1. `CLAUDE_PLUGIN_ROOT` environment variable (plugin install location)
2. Plugin marketplace cache (`~/.claude/plugins/cache/`)
3. Local development path (fallback)

### Library-Based Approach

Scripts are thin wrappers around `zos_utils.py`. The library provides:

| Module | Key Functions |
|--------|--------------|
| Connection | `ZOSConnection()` with context manager, `connect()`, `close()` |
| Validation | `validate_system_ready()`, `set_nsc_orientation()`, `set_nsc_position()` |
| Analysis | `extract_mtf_data()`, `extract_spot_data()`, `extract_wavefront_data()`, `extract_psf_data()`, `extract_ray_fan_data()` |
| NSC | `create_nsc_detector()`, `create_nsc_source()`, `get_detector_data()`, `get_coherent_data()` |
| Optimization | `run_dls_optimization()`, `run_hammer_optimization()` |
| Tolerance | `run_tolerance_sensitivity()`, `run_tolerance_monte_carlo()` |
| Multi-Config | `add_configuration()`, `set_config_operand()` |
| CAD | `export_cad()`, `import_cad()` |
| Plotting | `plot_mtf()`, `plot_spot_diagram()`, `plot_wavefront_map()`, `plot_ray_fan()`, `plot_detector_data()`, `plot_tolerance_cdf()` |
| Templates | `generate_script()`, `register_template()` |

## Important Notes

1. **Zemax must be installed and licensed** — requires a valid OpticStudio license
   (Professional or Premium edition for full API access; Standard has limited API support).

2. **Only one API connection at a time** — ZOS-API allows a single .NET connection.
   Close previous connections before starting a new one.

3. **Use the context manager** — `with ZOSConnection() as zos:` automatically closes
   the connection and releases the OpticStudio server instance.

4. **Matplotlib after cleanup** — call `plt.show()` or `plt.savefig()` AFTER closing
   the ZOS connection. The .NET interop may crash if matplotlib renders while
   OpticStudio is still loaded in memory. Use `plt.savefig()` for non-interactive reporting.

5. **NSC orientation trap** — Use ONLY `TiltAboutX`, `TiltAboutY`, `TiltAboutZ` for
   NSC object orientation. The names `TiltX`, `TiltY`, `TiltZ` silently create
   Python-only attributes that Zemax ignores. Use `zos.set_nsc_orientation()` which
   enforces correct names.

6. **Deterministic seeding** — always call `set_seed(42)` at script start for
   reproducible ray-trace results across runs.
