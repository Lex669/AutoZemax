---
name: ray-tracing
description: This skill should be used when the user asks to "run a ray trace", "trace rays", "batch ray trace", "NSC ray trace", "ray trace with polarization", "scatter rays", "split rays", "save ray database", "run sequential ray trace", or executes ray tracing in Zemax.
version: 0.1.0
---

# Ray Tracing — Sequential & Non-Sequential

Run sequential batch ray traces and non-sequential ray traces with
configurable polarization, splitting, and scattering.

## Prerequisites

```python
import sys, os
# Robust import: tries CLAUDE_PLUGIN_ROOT env var first,
# then falls back to cache path and dev path
_PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
_SCRIPTS_PATH = None
if _PLUGIN_ROOT:
    _SCRIPTS_PATH = os.path.join(_PLUGIN_ROOT, 'scripts')
else:
    _CANDIDATES = [
        r'C:\Users\Lex\.claude\plugins\cache\AutoSim\AutoZemax\0.1.0\scripts',
        r'C:\Users\Lex\Desktop\AutoSim\AutoZemax\scripts',
    ]
    for _p in _CANDIDATES:
        if os.path.isdir(_p):
            _SCRIPTS_PATH = _p
            break
if _SCRIPTS_PATH:
    sys.path.insert(0, _SCRIPTS_PATH)
from zos_utils import ZOSConnection
```

Execute with the Python interpreter documented in `references/environment.md`.

## Sequential Batch Ray Trace

Used for spot diagrams and sequential system analysis.

```python
import numpy as np
from System import Enum, Int32, Double

with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # Create batch ray trace
    raytrace = TheSystem.Tools.OpenBatchRayTrace()
    nsur = TheSystem.LDE.NumberOfSurfaces
    max_rays = 30  # grid density

    # Create normalized unpolarized ray data holder
    normUnPolData = raytrace.CreateNormUnpol(
        (max_rays + 1) * (max_rays + 1),
        ZOSAPI.Tools.RayTrace.RaysType.Real,
        nsur
    )

    # Ray trace parameters
    hx = 0.0  # normalized X field
    hy = 0.7  # normalized Y field
    wave_num = 1

    # Clear and add rays
    normUnPolData.ClearData()
    for i in range(1, (max_rays + 1) * (max_rays + 1) + 1):
        # Random pupil sampling (uniform disk)
        px = np.random.random() * 2 - 1
        py = np.random.random() * 2 - 1
        while px*px + py*py > 1:
            px = np.random.random() * 2 - 1
            py = np.random.random() * 2 - 1

        normUnPolData.AddRay(wave_num, hx, hy, px, py,
            Enum.Parse(ZOSAPI.Tools.RayTrace.OPDMode, "None"))

    raytrace.RunAndWaitForCompletion()

    # Read results
    normUnPolData.StartReadingResults()
    sysInt = Int32(1)
    sysDbl = Double(1.0)

    output = normUnPolData.ReadNextResult(sysInt, sysInt, sysInt,
        sysDbl, sysDbl, sysDbl, sysDbl, sysDbl, sysDbl, sysDbl,
        sysDbl, sysDbl, sysDbl, sysDbl)

    while output[0]:  # success flag
        if output[2] == 0 and output[3] == 0:  # no error, no vignette
            ray_num = output[1]
            x = output[4]  # X on image plane
            y = output[5]  # Y on image plane
            # Store or process x, y...
        output = normUnPolData.ReadNextResult(sysInt, sysInt, sysInt,
            sysDbl, sysDbl, sysDbl, sysDbl, sysDbl, sysDbl, sysDbl,
            sysDbl, sysDbl, sysDbl, sysDbl)
```

## NSC Ray Trace

For non-sequential systems with detectors.

```python
with ZOSConnection() as zos:
    # Configure ray trace
    NSCRayTrace = zos.TheSystem.Tools.OpenNSCRayTrace()
    NSCRayTrace.SplitNSCRays = True
    NSCRayTrace.ScatterNSCRays = False
    NSCRayTrace.UsePolarization = True
    NSCRayTrace.IgnoreErrors = True
    NSCRayTrace.SaveRays = False  # Don't save ray database

    # Run with progress monitoring
    NSCRayTrace.Run()
    print('Ray tracing...')
    lastValue = [0]
    while NSCRayTrace.IsRunning:
        currentValue = NSCRayTrace.Progress
        if currentValue % 2 == 0 and lastValue[-1] != currentValue:
            lastValue.append(currentValue)
            print(f"Progress: {currentValue}%")

    NSCRayTrace.WaitForCompletion()
    NSCRayTrace.Close()
    print('Ray trace completed')
```

## NSC Ray Trace with Ray Database

To save rays for later analysis:

```python
NSCRayTrace.SaveRays = True
# Rays are saved and can be accessed via ZRD file
# Use the ZRD reading patterns (see analysis skill)
```

## Ray Trace Options Reference

| Option | Description |
|--------|-------------|
| SplitNSCRays | Enable ray splitting at beam splitters |
| ScatterNSCRays | Enable scattering at surfaces |
| UsePolarization | Track polarization state |
| IgnoreErrors | Continue on non-critical errors |
| SaveRays | Write ray database to ZRD file |

## Notes

- For sequential ray traces, use the BatchRayTrace tool with NormUnpol data
- NSC ray traces support progress monitoring via `IsRunning` / `Progress`
- Always call `WaitForCompletion()` before reading results
- Close ray trace tools after use to free resources
