# AutoZemax Python Environment

## Python Interpreter

**Path:** `C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe`

This is the Python 3.14 64-bit interpreter bundled with the system. It has
`pythonnet` (`clr` module) pre-installed for .NET interop with ZOS-API.

## Required Packages

The following packages must be available in the Python environment:

| Package | Purpose | Import |
|---------|---------|--------|
| `pythonnet` | .NET CLR interop for ZOS-API | `import clr` |
| `numpy` | Numerical array operations | `import numpy as np` |
| `matplotlib` | Plotting and visualization | `import matplotlib.pyplot as plt` |

## Verify Environment

Run the following to verify the environment is correctly configured:

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

The ZOS-API assemblies are located at:
- `ZOSAPI_NetHelper.dll` — `{ZemaxRoot}\ZOS-API\Libraries\`
- `ZOSAPI.dll` — `{ZemaxRoot}\`
- `ZOSAPI_Interfaces.dll` — `{ZemaxRoot}\`

## Running Scripts

All AutoZemax scripts are executed with:

```powershell
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" "<script_path>"
```

Scripts import `zos_utils.py` from the plugin's `scripts/` directory. The
script should add the `scripts/` path to `sys.path`:

```python
import sys
sys.path.insert(0, r"C:\Users\Lex\Desktop\AutoSim\AutoZemax\scripts")
from zos_utils import ZOSConnection
```

## Important Notes

1. **Zemax must be installed and licensed** — the API requires a valid
   OpticStudio license (Professional or Premium edition for full API access).

2. **Only one API connection at a time** — ZOS-API allows a single connection.
   Close previous connections before starting a new one.

3. **Close connection to release memory** — always call `zos.close()` or use
   the context manager to properly release the OpticStudio server instance.

4. **Matplotlib after cleanup** — call `plt.show()` AFTER closing the ZOS
   connection to release OpticStudio from memory first.
