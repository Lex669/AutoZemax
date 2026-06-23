---
name: tolerance-analysis
description: This skill should be used when the user asks to "tolerance analysis", "sensitivity analysis", "Monte Carlo tolerance", "tolerancing", "yield analysis", "tolerance wizard", "manufacturing tolerances", "worst offenders", "tolerance CDF", or evaluates manufacturing robustness via tolerance analysis in Zemax.
version: 0.2.0
---

# Tolerance Analysis — Sensitivity, Monte Carlo & Yield

Configure manufacturing tolerances, run sensitivity analysis to identify
worst offenders, perform Monte Carlo simulation for yield prediction,
and plot the cumulative distribution function (CDF). Uses the library
safe wrappers `zos.run_tolerance_sensitivity()` and
`zos.run_tolerance_monte_carlo()` instead of raw API calls.
Corresponds to ZOS-API Sample 14.

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
from zos_utils import ZOSConnection, set_seed, plot_tolerance_cdf

set_seed(42)
```

Execute with:
```
& "C:\Users\Lex\AppData\Local\Python\pythoncore-3.14-64\python.exe" <script>.py
```

## Workflow

The tolerance analysis workflow follows four steps:

1. **Load** the optical design to be toleranced
2. **Configure** tolerance operands via the Tolerance Wizard (TDE)
3. **Run sensitivity** analysis to identify worst offenders
4. **Run Monte Carlo** to estimate manufacturing yield and plot the CDF

## Step 1: Load the Design

```python
with ZOSConnection() as zos:
    zos.open_file(zos.samples_dir() +
        "\\Sequential\\Objectives\\Double Gauss 28 degree field.zos")
    print(f"Loaded: {zos.TheSystem.LDE.NumberOfSurfaces} surfaces")
```

## Step 2: Configure Tolerance Wizard

The tolerance wizard populates the Tolerance Data Editor (TDE) with default
tolerances. Configure it before running any analysis.

```python
with ZOSConnection() as zos:
    TheSystem = zos.TheSystem
    ZOSAPI = zos.ZOSAPI

    # Access the tolerance wizard
    tWiz = TheSystem.TDE.SEQToleranceWizard

    # Surface tolerances
    tWiz.SurfaceRadius = 0.1           # Fringes (test plate fit)
    tWiz.SurfaceThickness = 0.1        # mm
    tWiz.SurfaceDecenterX = 0.05       # mm
    tWiz.SurfaceDecenterY = 0.05       # mm
    tWiz.SurfaceTiltX = 0.1            # degrees
    tWiz.SurfaceTiltY = 0.1            # degrees
    tWiz.SurfaceSAndAIrregularity = 0.2  # fringes irregularity

    # Element tolerances (grouped surfaces)
    tWiz.ElementDecenterX = 0.1        # mm
    tWiz.ElementDecenterY = 0.1        # mm
    tWiz.ElementTiltXDegrees = 0.2     # degrees
    tWiz.ElementTiltYDegrees = 0.2     # degrees

    # Index and dispersion tolerances
    tWiz.IsIndexUsed = True
    tWiz.IndexVariation = 0.001
    tWiz.IsIndexAbbePercentageUsed = True
    tWiz.IndexAbbePercentage = 0.5     # percent

    # Apply the wizard
    tWiz.OK()
    print("Tolerance wizard applied.")

    # Save toleranced file for traceability
    zos.save_file(zos.ensure_zmx_dir() + "\\toleranced_design.zmx")
```

## Step 3: Sensitivity Analysis

The library wrapper `zos.run_tolerance_sensitivity()` runs the sensitivity
analysis and returns a sorted list of dicts — worst offenders first.

```python
with ZOSConnection() as zos:
    zos.open_file(zos.ensure_zmx_dir() + "\\toleranced_design.zmx")

    # Single call — handles tool open, setup, run, cleanup
    results = zos.run_tolerance_sensitivity()
    # Returns list of dicts sorted by |sensitivity| descending

    print(f"Found {len(results)} tolerance operands")
    print("Worst offenders:")
    print(f"{'#':>3} {'Type':<20} {'Surf':>4} {'Value':>10} "
          f"{'Sensitivity':>12} {'Criterion Chg':>14}")
    print("-" * 68)

    for r in results[:10]:  # Top 10 worst offenders
        print(f"{r['index']:>3} {r['type']:<20} {r['surface']:>4} "
              f"{r['value']:>10.4f} {r['sensitivity']:>12.6f} "
              f"{r['criterion_change']:>14.6f}")

    # All results available if needed
    all_types = set(r['type'] for r in results)
    print(f"Tolerance types present: {', '.join(sorted(all_types))}")
```

### Interpreting Sensitivity Results

Each result dict contains:

| Key | Description |
|-----|-------------|
| `index` | Row number in results table |
| `type` | Tolerance operand type name (e.g., "TRAD", "TTHI") |
| `surface` | Surface number the tolerance applies to |
| `value` | Tolerance value |
| `sensitivity` | Change in criterion per unit tolerance |
| `criterion_change` | Absolute change in criterion value |

The worst offenders (highest |sensitivity|) are the tolerances that most
impact performance — tighten these first if yield is insufficient.

## Step 4: Monte Carlo Simulation

The library wrapper `zos.run_tolerance_monte_carlo()` runs the Monte Carlo
simulation and returns yield statistics plus CDF data.

```python
with ZOSConnection() as zos:
    zos.open_file(zos.ensure_zmx_dir() + "\\toleranced_design.zmx")

    # Run with 200 trials, RMS wavefront criterion
    stats = zos.run_tolerance_monte_carlo(
        n_trials=200,
        criterion=zos.ZOSAPI.Tools.Tolerancing.ToleranceCriterion.RMSWavefront
    )

    print(f"Monte Carlo Results ({stats['n_trials']} trials):")
    print(f"  Nominal:       {stats['nominal']:.6f}")
    print(f"  Mean:          {stats['mean']:.6f}")
    print(f"  Std Dev:       {stats['std_dev']:.6f}")
    print(f"  Best:          {stats['best']:.6f}")
    print(f"  Worst:         {stats['worst']:.6f}")
    print(f"  Yield at 90%:  {stats['yield_90']:.1f}%")
    print(f"  Yield at 80%:  {stats['yield_80']:.1f}%")
    print(f"  Yield at 50%:  {stats['yield_50']:.1f}%")
```

## Plotting the CDF

Use the standalone `plot_tolerance_cdf()` function to visualize the
Monte Carlo cumulative distribution:

```python
import os

with ZOSConnection() as zos:
    zos.open_file(zos.ensure_zmx_dir() + "\\toleranced_design.zmx")

    stats = zos.run_tolerance_monte_carlo(n_trials=200)

    # Plot and save
    output_dir = zos.ensure_zmx_dir() + "\\tolerance_plots"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    fig, ax = plot_tolerance_cdf(
        stats,
        title='Double Gauss 28-deg — Tolerance CDF (200 trials)',
        save_path=output_dir + "\\tolerance_cdf.png",
        show=False
    )
    # fig, ax remain open for further customization
    print(f"CDF plot saved to {output_dir}\\tolerance_cdf.png")
```

## Complete Automated Workflow

```python
import os

with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    # 1. Load design
    zos.open_file(zos.samples_dir() +
        "\\Sequential\\Objectives\\Double Gauss 28 degree field.zos")

    # 2. Configure tolerance wizard
    tWiz = TheSystem.TDE.SEQToleranceWizard
    tWiz.SurfaceRadius = 0.1
    tWiz.SurfaceThickness = 0.1
    tWiz.SurfaceDecenterX = 0.05
    tWiz.SurfaceDecenterY = 0.05
    tWiz.SurfaceTiltX = 0.1
    tWiz.SurfaceTiltY = 0.1
    tWiz.ElementDecenterX = 0.1
    tWiz.ElementDecenterY = 0.1
    tWiz.ElementTiltXDegrees = 0.2
    tWiz.ElementTiltYDegrees = 0.2
    tWiz.IsIndexUsed = True
    tWiz.IndexVariation = 0.001
    tWiz.IsIndexAbbePercentageUsed = True
    tWiz.IndexAbbePercentage = 0.5
    tWiz.OK()

    # Save toleranced baseline
    zos.save_file(zos.ensure_zmx_dir() + "\\toleranced_design.zmx")

    # 3. Sensitivity analysis — find worst offenders
    sensitivity = zos.run_tolerance_sensitivity()
    worst = sensitivity[:5]
    print("Top 5 worst offenders:")
    for r in worst:
        print(f"  {r['type']} on surface {r['surface']}: "
              f"sensitivity = {r['sensitivity']:.6f}")

    # 4. Monte Carlo — estimate yield
    stats = zos.run_tolerance_monte_carlo(n_trials=200)

    # 5. Plot CDF
    output_dir = zos.ensure_zmx_dir() + "\\tolerance_plots"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    plot_tolerance_cdf(
        stats,
        title='Double Gauss — Tolerance CDF',
        save_path=output_dir + "\\cdf.png"
    )

    # 6. Save Monte Carlo system files
    monte_carlo_dir = output_dir + "\\mc_systems"
    if not os.path.exists(monte_carlo_dir):
        os.makedirs(monte_carlo_dir)
    for i in range(1, stats.get('n_saved', 0) + 1):
        # Save individual MC trial files if needed
        pass

    print("Tolerance analysis complete.")
```

## Criterion Types

| Criterion | Enum Value | Use Case |
|-----------|------------|----------|
| RMSWavefront | RMSWavefront | Wavefront error (default) |
| RMSSpotRadius | RMSSpotRadius | Spot size |
| MTF | MTF | MTF at specified frequency |
| DiffractionMTF | DiffractionMTF | Diffraction-limited MTF |
| BoresightError | BoresightError | Pointing stability |
| AngularRadius | AngularRadius | Angular blur |

## Yield Interpretation

| Yield % | Meaning |
|---------|---------|
| > 90% | Excellent — design is robust to manufacturing variations |
| 80-90% | Good — consider tightening worst tolerances |
| 50-80% | Marginal — tighten top 3-5 worst offenders |
| < 50% | Poor — may need design change or much tighter tolerances |

## Notes

- **Always run the tolerance wizard first** — `zos.run_tolerance_sensitivity()`
  and `zos.run_tolerance_monte_carlo()` operate on whatever tolerances are
  already set in the TDE, not a default set
- **Use the library safe wrappers** instead of raw `OpenTolerancing()` —
  they handle proper cleanup and return structured data (lists of dicts
  for sensitivity, stats dict for Monte Carlo)
- Sensitivity and Monte Carlo are **separate runs** — Zemax does not
  combine them. Run sensitivity first to identify which tolerances matter,
  then Monte Carlo to estimate statistical yield
- `zos.run_tolerance_sensitivity()` returns results sorted by
  |sensitivity| descending — the first entries are the worst offenders
- `zos.run_tolerance_monte_carlo()` returns a dict with keys `nominal`,
  `mean`, `std_dev`, `best`, `worst`, `yield_90/80/50`, and `cdf`
- The CDF list contains dicts with `x` (criterion value) and `y`
  (cumulative probability %) for plotting
- Save the toleranced file to `zos.ensure_zmx_dir()` before running
  analysis to maintain traceability between design versions and results
- Use `plot_tolerance_cdf()` from `zos_utils` for a quick visualization —
  it returns `(fig, ax)` for further customization if needed
- Monte Carlo trial files are saved in the system directory when
  `NumberToSave > 0` — configure this via the raw API if needed:
  `tool.NumberToSave = 10`
