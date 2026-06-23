"""
AutoZemax Shared Utilities — ZOS-API Connection & Data Handling.

Encapsulates the .NET interop boilerplate from official Zemax examples into a
reusable Python class. All AutoZemax skills generate scripts that import this module.

Includes safe wrappers for known pythonnet silent-failure traps, pre-flight
validation, and deterministic random seeding — so generated scripts run correctly
on the first attempt.

Usage:
    from zos_utils import ZOSConnection, ensure_zmx_dir, set_seed

    set_seed(42)  # reproducible ray traces

    with ZOSConnection() as zos:
        zos.validate_system_ready()          # pre-flight check
        zos.set_nsc_orientation(obj, 0, 45, 0)  # safe: uses TiltAboutX/Y/Z
        # ... your automation code ...

Environment:
    Python: C:\\Users\\Lex\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe
    Zemax:  Ansys Zemax OpticStudio 2025 R2 (v252)
"""

import clr
import os
import sys
import math
import random
import winreg
from itertools import islice

# ------------------------------------------------------------------
# Deterministic random seed — call set_seed() once at script start
# ------------------------------------------------------------------

_SEED = None

def set_seed(seed=42):
    """Set a deterministic seed for numpy.random and Python random.

    Call this ONCE at the top of any generated script to ensure
    reproducible ray-trace sampling across runs.

    Args:
        seed: Integer seed value. Default 42.
    """
    global _SEED
    _SEED = seed
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass

def get_seed():
    """Return the current seed, or None if not set."""
    return _SEED

# ------------------------------------------------------------------
# MFE Cell Index Constants
# ------------------------------------------------------------------
# Instead of magic numbers like GetCellAt(2), use named constants.
# Maps MeritOperandType → {parameter_name: cell_index}
# Cell indices per official Zemax documentation.

MFE_CELL = {
    # Surface-range operands: MNCA, MXCA, MNEA, MXEA, MNCG, MXCG, MNEG, MXEG
    "SURF1": 2,   # Start surface for boundary operands
    "SURF2": 3,   # End surface for boundary operands
    # Common for many operands
    "FIELD": 2,   # Field number
    "WAVE":  3,   # Wavelength number
    "ZONE":  4,   # Zone (for SPHA)
    "TARGET": None,  # Use .Target property directly
    "WEIGHT": None,  # Use .Weight property directly
}

def mfe_set_cell(operand, cell_index, value):
    """Set an MFE operand cell with proper integer/float typing.

    Args:
        operand: MFE operand object from TheSystem.MFE
        cell_index: Cell index (1-based). Use MFE_CELL constants.
        value: Value to set. Floats use DoubleValue, ints use IntegerValue.
    """
    cell = operand.GetCellAt(cell_index)
    if isinstance(value, int):
        cell.IntegerValue = value
    else:
        cell.DoubleValue = float(value)

# ------------------------------------------------------------------
# Safe NSC property names — blocks the TiltX vs TiltAboutX trap
# ------------------------------------------------------------------

# The ONLY valid orientation property names in pythonnet/ZOS-API:
_NSC_VALID_PROPS = {
    'TiltAboutX', 'TiltAboutY', 'TiltAboutZ',
    'XPosition', 'YPosition', 'ZPosition',
    'Material', 'Comment', 'ObjectData',
}

_NSC_TRAP_MAP = {
    'TiltX': 'TiltAboutX',
    'TiltY': 'TiltAboutY',
    'TiltZ': 'TiltAboutZ',
    'tiltX': 'TiltAboutX',
    'tiltY': 'TiltAboutY',
    'tiltZ': 'TiltAboutZ',
    'tilt_x': 'TiltAboutX',
    'tilt_y': 'TiltAboutY',
    'tilt_z': 'TiltAboutZ',
}

class ZOSConnection:
    """Manages the ZOS-API .NET interop connection lifecycle.

    Handles registry lookup, assembly loading, application creation,
    and provides utility methods for data reshaping, validation, and
    safe NSC property access.

    Use as a context manager or with explicit connect()/close() calls.
    """

    class LicenseException(Exception):
        pass

    class ConnectionException(Exception):
        pass

    class InitializationException(Exception):
        pass

    class SystemNotPresentException(Exception):
        pass

    class ValidationError(Exception):
        """Raised by validate_system_ready() when system is misconfigured."""
        pass

    class NSCPropertyError(AttributeError):
        """Raised when a trap property name (e.g. TiltX) is used."""
        pass

    def __init__(self, zos_path=None):
        """Initialize ZOS-API connection.

        Args:
            zos_path: Optional custom path to OpticStudio installation.
                      If None, auto-detects from Windows registry.
        """
        self.TheConnection = None
        self.TheApplication = None
        self.TheSystem = None
        self.ZOSAPI = None
        self._zos_path = zos_path
        # System type exports (populated in connect())
        self.Int32 = None
        self.Double = None
        self.Enum = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self):
        """Establish the full ZOS-API connection stack.

        Exports System types (Int32, Double, Enum) as instance attributes
        for use in batch ray traces and other .NET interop.

        Returns self for chaining.
        """
        # Locate ZOSAPI_NetHelper.dll via registry
        aKey = None
        try:
            aKey = winreg.OpenKey(
                winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER),
                r"Software\Zemax", 0, winreg.KEY_READ
            )
            zemaxData = winreg.QueryValueEx(aKey, 'ZemaxRoot')
            NetHelper = os.path.join(
                os.sep, zemaxData[0],
                r'ZOS-API\Libraries\ZOSAPI_NetHelper.dll'
            )
        finally:
            if aKey is not None:
                winreg.CloseKey(aKey)
        clr.AddReference(NetHelper)
        import ZOSAPI_NetHelper

        # Initialize ZOSAPI
        if self._zos_path is None:
            isInitialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize()
        else:
            isInitialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(
                self._zos_path
            )

        if not isInitialized:
            raise ZOSConnection.InitializationException(
                "Unable to locate Zemax OpticStudio. Try using a hard-coded path."
            )

        # Add ZOS-API references
        dir = ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory()
        clr.AddReference(os.path.join(os.sep, dir, "ZOSAPI.dll"))
        clr.AddReference(os.path.join(os.sep, dir, "ZOSAPI_Interfaces.dll"))
        import ZOSAPI
        self.ZOSAPI = ZOSAPI

        # Export System types for batch ray trace (replaces "from System import ...")
        from System import Enum, Int32, Double
        self.Enum = Enum
        self.Int32 = Int32
        self.Double = Double

        # Create connection and application
        self.TheConnection = ZOSAPI.ZOSAPI_Connection()
        if self.TheConnection is None:
            raise ZOSConnection.ConnectionException(
                "Unable to initialize .NET connection to ZOSAPI"
            )

        self.TheApplication = self.TheConnection.CreateNewApplication()
        if self.TheApplication is None:
            raise ZOSConnection.InitializationException(
                "Unable to acquire ZOSAPI application"
            )

        if not self.TheApplication.IsValidLicenseForAPI:
            raise ZOSConnection.LicenseException(
                "License is not valid for ZOSAPI use"
            )

        self.TheSystem = self.TheApplication.PrimarySystem
        if self.TheSystem is None:
            raise ZOSConnection.SystemNotPresentException(
                "Unable to acquire Primary system"
            )

        return self

    def close(self):
        """Close the OpticStudio application and release resources."""
        if self.TheApplication is not None:
            self.TheApplication.CloseApplication()
            self.TheApplication = None
        self.TheConnection = None
        self.TheSystem = None
        self.ZOSAPI = None
        self.Int32 = None
        self.Double = None
        self.Enum = None

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        self.close()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def open_file(self, filepath, save_if_needed=False):
        """Load an existing .zos/.zmx/.zda file."""
        if self.TheSystem is None:
            raise ZOSConnection.SystemNotPresentException(
                "Unable to acquire Primary system"
            )
        self.TheSystem.LoadFile(filepath, save_if_needed)

    def new_file(self, system_type=None):
        """Create a new optical system.

        Args:
            system_type: Optional ZOSAPI.SystemType enum value.
                         Use ZOSAPI.SystemType.NonSequential for NSC mode.
                         If None, creates a default sequential system.
        """
        if self.TheApplication is None:
            raise ZOSConnection.InitializationException(
                "No ZOSAPI application available"
            )
        if system_type is not None:
            self.TheSystem = self.TheApplication.CreateNewSystem(system_type)
        else:
            if self.TheSystem is None:
                raise ZOSConnection.SystemNotPresentException(
                    "Unable to acquire Primary system"
                )
            self.TheSystem.New(False)
        return self.TheSystem

    def save_file(self, filepath=None):
        """Save the current system. If filepath given, uses SaveAs."""
        if filepath:
            self.TheSystem.SaveAs(filepath)
        else:
            self.TheSystem.Save()

    def close_file(self, save=False):
        """Close the current optical system."""
        if self.TheSystem is None:
            raise ZOSConnection.SystemNotPresentException(
                "Unable to acquire Primary system"
            )
        self.TheSystem.Close(save)

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def samples_dir(self):
        """Return the Zemax samples directory path."""
        return self.TheApplication.SamplesDir

    def objects_dir(self):
        """Return the Zemax objects/catalog directory path."""
        return self.TheApplication.ObjectsDir

    def ensure_api_dir(self):
        """Create API/Python sample output directory if missing."""
        api_dir = os.path.join(self.TheApplication.SamplesDir, "API", "Python")
        if not os.path.exists(api_dir):
            os.makedirs(api_dir)
        return api_dir

    def ensure_zmx_dir(self, base_path=None):
        """Create zmx/ output directory if missing.

        Creates a 'zmx' subfolder for storing .zmx and .zda modeling files.
        The folder is created relative to the given base_path, or the current
        working directory if base_path is None.

        Args:
            base_path: Optional parent directory. Defaults to os.getcwd().

        Returns:
            Absolute path to the zmx/ directory.
        """
        if base_path is None:
            base_path = os.getcwd()
        zmx_dir = os.path.join(base_path, "zmx")
        if not os.path.exists(zmx_dir):
            os.makedirs(zmx_dir)
        return zmx_dir

    # ------------------------------------------------------------------
    # Pre-flight validation — catches misconfiguration BEFORE running
    # ------------------------------------------------------------------

    def validate_system_ready(self, require_surfaces=True):
        """Validate that the optical system is properly configured.

        Checks aperture, fields, wavelengths, material catalogs, and
        optionally verifies that surfaces exist. Raises ValidationError
        with a specific message on failure.

        Call this BEFORE adding surfaces or running simulations to
        catch common misconfigurations early.

        Args:
            require_surfaces: If True, requires at least 3 surfaces
                              (Object, at least one lens, Image).

        Raises:
            ValidationError: With specific guidance on what's missing.
        """
        SD = self.TheSystem.SystemData
        issues = []

        # Aperture check
        try:
            av = SD.Aperture.ApertureValue
            if av is None or av <= 0:
                issues.append("Aperture value is not set or <= 0")
        except Exception:
            issues.append("Aperture is not configured. Set: TheSystemData.Aperture.ApertureValue = <value>")

        # Fields check
        try:
            nf = SD.Fields.NumberOfFields
            if nf < 1:
                issues.append("No fields configured. Use: TheSystemData.Fields.AddField(x, y, weight)")
        except Exception:
            issues.append("Fields are not accessible. System may not be initialized.")

        # Wavelengths check
        try:
            nw = SD.Wavelengths.NumberOfWavelengths
            if nw < 1:
                issues.append("No wavelengths configured. Use: TheSystemData.Wavelengths.SelectWavelengthPreset(...)")
        except Exception:
            issues.append("Wavelengths are not accessible. System may not be initialized.")

        # Material catalog check
        try:
            cats = SD.MaterialCatalogs
            if cats.NumberOfCatalogs < 1:
                issues.append("No material catalogs loaded. Use: TheSystemData.MaterialCatalogs.AddCatalog('SCHOTT')")
        except Exception:
            issues.append("Cannot access material catalogs.")

        # Surface check
        if require_surfaces:
            try:
                ns = self.TheSystem.LDE.NumberOfSurfaces
                if ns < 3:
                    issues.append(f"Only {ns} surface(s) exist. Insert surfaces with: TheLDE.InsertNewSurfaceAt(position)")
            except Exception:
                issues.append("Cannot access Lens Data Editor. System may not be initialized.")

        if issues:
            msg = "System validation FAILED:\n  - " + "\n  - ".join(issues)
            raise ZOSConnection.ValidationError(msg)

        return True

    # ------------------------------------------------------------------
    # Safe NSC property access — blocks the TiltX/TiltY/TiltZ trap
    # ------------------------------------------------------------------

    @staticmethod
    def set_nsc_orientation(obj, tilt_x=0.0, tilt_y=0.0, tilt_z=0.0):
        """Safely set NSC object orientation using the CORRECT property names.

        Uses TiltAboutX/Y/Z (the only valid pythonnet properties for NSC
        orientation). The trap names TiltX/TiltY/TiltZ are NOT accepted —
        they silently create Python-only attributes that Zemax ignores.

        Args:
            obj: NSC object from TheNCE.GetObjectAt(n)
            tilt_x: Rotation about X axis (degrees)
            tilt_y: Rotation about Y axis (degrees)
            tilt_z: Rotation about Z axis (degrees)
        """
        obj.TiltAboutX = float(tilt_x)
        obj.TiltAboutY = float(tilt_y)
        obj.TiltAboutZ = float(tilt_z)

    @staticmethod
    def set_nsc_position(obj, x=0.0, y=0.0, z=0.0):
        """Set NSC object position.

        Args:
            obj: NSC object from TheNCE.GetObjectAt(n)
            x: X position (mm)
            y: Y position (mm)
            z: Z position (mm)
        """
        obj.XPosition = float(x)
        obj.YPosition = float(y)
        obj.ZPosition = float(z)

    @staticmethod
    def validate_nsc_property(prop_name):
        """Check if prop_name is a safe NSC property.

        Raises NSCPropertyError if prop_name is a known trap (e.g., 'TiltX').

        Args:
            prop_name: The property name to check.

        Returns:
            True if the property name is safe.

        Raises:
            NSCPropertyError: If prop_name is a known trap name.
        """
        if prop_name in _NSC_TRAP_MAP:
            correct = _NSC_TRAP_MAP[prop_name]
            raise ZOSConnection.NSCPropertyError(
                f"'{prop_name}' is a TRAP! pythonnet will silently create a "
                f"Python-only attribute that Zemax ignores. Use '{correct}' instead."
            )
        if prop_name not in _NSC_VALID_PROPS:
            # Not in known-valid list — warn but allow
            print(f"WARNING: '{prop_name}' is not a known-safe NSC property. "
                  f"Verify it's the correct pythonnet name.")
        return True

    # ------------------------------------------------------------------
    # Safe optimization runners — fix common template bugs
    # ------------------------------------------------------------------

    def run_dls_optimization(self, cycles=None, num_cores=8):
        """Run Damped Least Squares (local) optimization.

        Args:
            cycles: Number of cycles. Default: Automatic.
            num_cores: CPU cores to use. Default 8.
        """
        ZOSAPI = self.ZOSAPI
        print('Running Local Optimization (DLS)...')
        opt = self.TheSystem.Tools.OpenLocalOptimization()
        try:
            opt.Algorithm = ZOSAPI.Tools.Optimization.OptimizationAlgorithm.DampedLeastSquares
            if cycles is not None:
                opt.Cycles = cycles
            else:
                opt.Cycles = ZOSAPI.Tools.Optimization.OptimizationCycles.Automatic
            opt.NumberOfCores = num_cores
            opt.RunAndWaitForCompletion()
        finally:
            opt.Close()
        print('Local optimization complete.')
        return self.TheSystem.MFE.MeritFunctionValue

    def run_hammer_optimization(self, timeout_sec=30):
        """Run Hammer (global) optimization with CORRECT cancel logic.

        Only cancels if STILL running after timeout — fixes the common
        template bug where Cancel() is called unconditionally.

        Args:
            timeout_sec: Maximum runtime in seconds. Default 30.

        Returns:
            Final merit function value.
        """
        print(f'Running Hammer Optimization (timeout={timeout_sec}s)...')
        opt = self.TheSystem.Tools.OpenHammerOptimization()
        try:
            opt.RunAndWaitWithTimeout(timeout_sec)
            # FIX: Only cancel if STILL running
            if opt.IsRunning:
                print(f'  Still running after {timeout_sec}s — cancelling...')
                opt.Cancel()
                opt.WaitForCompletion()
            else:
                print('  Hammer completed within timeout.')
        finally:
            opt.Close()
        mf = self.TheSystem.MFE.MeritFunctionValue
        print(f'Merit function value: {mf:.6f}')
        return mf

    # ------------------------------------------------------------------
    # License helpers
    # ------------------------------------------------------------------

    def license_status(self):
        """Return the license edition string."""
        status = self.TheApplication.LicenseStatus
        mapping = {
            self.ZOSAPI.LicenseStatusType.PremiumEdition: "Premium",
            self.ZOSAPI.LicenseStatusType.ProfessionalEdition: "Professional",
            self.ZOSAPI.LicenseStatusType.StandardEdition: "Standard",
        }
        return mapping.get(status, "Invalid")

    # ------------------------------------------------------------------
    # Data reshaping utilities (from official examples)
    # ------------------------------------------------------------------

    @staticmethod
    def reshape(data, x, y, transpose=False):
        """Convert System.Double[,] to a 2D Python list.

        Args:
            data: .NET 2D array data from ZOS-API.
            x: Width — use data.GetLength(0).
            y: Height — use data.GetLength(1).
            transpose: If True, transpose the result.

        Returns:
            2D list suitable for matplotlib or numpy.asarray().
        """
        if type(data) is not list:
            data = list(data)
        var_lst = [y] * x
        it = iter(data)
        res = [list(islice(it, i)) for i in var_lst]
        if transpose:
            return ZOSConnection.transpose(res)
        return res

    @staticmethod
    def safe_reshape(data):
        """Auto-detect dimensions and reshape .NET 2D array to Python list.

        Simpler than reshape() — reads dimensions from the array itself.
        Use this when you don't need explicit x/y or transpose control.

        Args:
            data: .NET 2D array from ZOS-API.

        Returns:
            2D Python list [rows][cols].
        """
        if type(data) is not list:
            data = list(data)
        cols = data.GetLength(0) if hasattr(data, 'GetLength') else len(data)
        rows = data.GetLength(1) if hasattr(data, 'GetLength') else (len(data[0]) if data else 0)
        if hasattr(data, 'GetLength'):
            return ZOSConnection.reshape(data, cols, rows)
        return data

    @staticmethod
    def transpose(data):
        """Transpose a 2D list."""
        if type(data) is not list:
            data = list(data)
        return list(map(list, zip(*data)))


    # ------------------------------------------------------------------
    # NSC detector data helpers
    # ------------------------------------------------------------------

    def get_detector_data(self, detector_number, data_type=1):
        """Read full detector data array and return (width, height, 2D_list).

        Args:
            detector_number: NSC object number of the detector.
            data_type: 0=incoherent, 1=coherent irradiance, etc.

        Returns:
            (width, height, data_2d_list)
            Dimensions are read from the data array itself, avoiding the
            ObjectData readback issue (ObjectData returns IObject after reload).
        """
        raw = self.TheSystem.NCE.GetAllDetectorDataSafe(detector_number, data_type)
        w = raw.GetLength(0)
        h = raw.GetLength(1)
        return w, h, self.reshape(raw, w, h)

    def get_coherent_data(self, detector_number):
        """Read coherent real + imaginary data and compute phase + amplitude.

        Args:
            detector_number: NSC object number of the detector.

        Returns:
            (width, height, real_2d, imag_2d, phase_deg_2d, amplitude_2d)
            All values are 2D Python lists.
        """
        ZOSAPI = self.ZOSAPI
        # Real part
        raw_real = self.TheSystem.NCE.GetAllCoherentDataSafe(
            detector_number, ZOSAPI.Editors.NCE.DetectorDataType.Real)
        w = raw_real.GetLength(0)
        h = raw_real.GetLength(1)
        real = self.reshape(raw_real, w, h)

        # Imaginary part
        raw_imag = self.TheSystem.NCE.GetAllCoherentDataSafe(
            detector_number, ZOSAPI.Editors.NCE.DetectorDataType.Imaginary)
        imag = self.reshape(raw_imag, raw_imag.GetLength(0), raw_imag.GetLength(1))

        # Compute phase (degrees) and amplitude
        phase_deg = []
        amplitude = []
        for row_real, row_imag in zip(real, imag):
            phase_row = []
            amp_row = []
            for r_val, i_val in zip(row_real, row_imag):
                phase_row.append(math.degrees(math.atan2(i_val, r_val)))
                amp_row.append(math.sqrt(r_val * r_val + i_val * i_val))
            phase_deg.append(phase_row)
            amplitude.append(amp_row)

        return w, h, real, imag, phase_deg, amplitude

    # ------------------------------------------------------------------
    # Batch ray trace helpers
    # ------------------------------------------------------------------

    def sample_pupil_uniform(self, max_rays, seed=None):
        """Generate uniformly-distributed pupil coordinates.

        Uses rejection sampling to create a uniform disk distribution.
        Seeds numpy if set_seed() was called.

        Args:
            max_rays: Grid density (N rays per side).
            seed: Optional per-call seed override.

        Returns:
            List of (px, py) tuples within the unit circle.
        """
        try:
            import numpy as np
            if seed is not None:
                np.random.seed(seed)
            elif _SEED is not None:
                np.random.seed(_SEED + hash(max_rays) % 10000)
            total = (max_rays + 1) * (max_rays + 1)
            samples = []
            for _ in range(total):
                px = np.random.random() * 2 - 1
                py = np.random.random() * 2 - 1
                while px * px + py * py > 1:
                    px = np.random.random() * 2 - 1
                    py = np.random.random() * 2 - 1
                samples.append((px, py))
            return samples
        except ImportError:
            # Pure Python fallback
            if seed is not None:
                random.seed(seed)
            total = (max_rays + 1) * (max_rays + 1)
            samples = []
            for _ in range(total):
                px = random.random() * 2 - 1
                py = random.random() * 2 - 1
                while px * px + py * py > 1:
                    px = random.random() * 2 - 1
                    py = random.random() * 2 - 1
                samples.append((px, py))
            return samples

    def run_batch_ray_trace(self, hx=0.0, hy=0.0, wave_num=1, max_rays=30,
                            mode="None", seed=None):
        """Run a complete sequential batch ray trace.

        Handles all the .NET interop (Int32, Double, Enum) internally.
        Returns a list of (x, y) image-plane coordinates for rays that
        did not vignette or error.

        Args:
            hx: Normalized X field coordinate.
            hy: Normalized Y field coordinate.
            wave_num: Wavelength number.
            max_rays: Grid density.
            mode: OPDMode string ("None" or "UserDefined").
            seed: Optional random seed for pupil sampling.

        Returns:
            List of (x, y) tuples on the image plane.
        """
        ZOSAPI = self.ZOSAPI
        TheSystem = self.TheSystem

        raytrace = TheSystem.Tools.OpenBatchRayTrace()
        try:
            nsur = TheSystem.LDE.NumberOfSurfaces
            normUnPolData = raytrace.CreateNormUnpol(
                (max_rays + 1) * (max_rays + 1),
                ZOSAPI.Tools.RayTrace.RaysType.Real,
                nsur
            )

            # Generate pupil samples
            samples = self.sample_pupil_uniform(max_rays, seed=seed)

            normUnPolData.ClearData()
            for px, py in samples:
                normUnPolData.AddRay(wave_num, hx, hy, px, py,
                    self.Enum.Parse(ZOSAPI.Tools.RayTrace.OPDMode, mode))

            raytrace.RunAndWaitForCompletion()

            # Read results
            normUnPolData.StartReadingResults()
            sysInt = self.Int32(1)
            sysDbl = self.Double(1.0)

            results = []
            output = normUnPolData.ReadNextResult(sysInt, sysInt, sysInt,
                sysDbl, sysDbl, sysDbl, sysDbl, sysDbl, sysDbl, sysDbl,
                sysDbl, sysDbl, sysDbl, sysDbl)

            while output[0]:  # success flag
                if output[2] == 0 and output[3] == 0:  # no error, no vignette
                    results.append((output[4], output[5]))  # (x, y)
                output = normUnPolData.ReadNextResult(sysInt, sysInt, sysInt,
                    sysDbl, sysDbl, sysDbl, sysDbl, sysDbl, sysDbl, sysDbl,
                    sysDbl, sysDbl, sysDbl, sysDbl)

            return results
        finally:
            raytrace.Close()

    # ------------------------------------------------------------------
    # Sequential analysis extractors
    # ------------------------------------------------------------------

    def extract_mtf_data(self, mtf_results):
        """Extract MTF data from an FFT MTF analysis result.

        Args:
            mtf_results: Results object from mtf_win.GetResults()

        Returns:
            List of dicts with keys: frequency, tangential, sagittal, field
        """
        mtf_data = []
        for series_num in range(mtf_results.NumberOfDataSeries):
            data = mtf_results.GetDataSeries(series_num)
            x_raw = list(data.XData.Data)
            y_raw = data.YData.Data
            y = self.reshape(y_raw, y_raw.GetLength(0), y_raw.GetLength(1), True)
            mtf_data.append({
                'frequency': x_raw,
                'tangential': y[0] if len(y) > 0 else [],
                'sagittal': y[1] if len(y) > 1 else [],
                'field': series_num + 1,
            })
        return mtf_data

    def extract_spot_data(self, spot_results):
        """Extract spot diagram data from a Standard Spot analysis result.

        Args:
            spot_results: Results object from spot.GetResults()

        Returns:
            Dict with rms_geo list and summary dict.
        """
        spots = []
        spot_data = spot_results.SpotData
        n_fields = spot_data.NumberOfFields
        for field in range(1, n_fields + 1):
            rms = spot_data.GetRMSSpotSizeFor(field, 1)
            geo = spot_data.GetGeoSpotSizeFor(field, 1)
            spots.append({
                'field': field,
                'rms_spot_um': rms,
                'geo_spot_um': geo,
                'airy_radius_um': spot_data.GetAiryRadiusFor(field, 1) if n_fields > 0 else 0,
            })
        return {'spots': spots, 'n_fields': n_fields}

    def extract_wavefront_data(self, wf_results):
        """Extract wavefront map data from a WavefrontMap analysis.

        Args:
            wf_results: Results object from wavefront.GetResults()

        Returns:
            2D list of wavefront values, plus metadata dict.
        """
        n_series = wf_results.NumberOfDataSeries
        data_grids = []
        for i in range(n_series):
            series = wf_results.GetDataSeries(i)
            y_raw = series.YData.Data
            grid = self.safe_reshape(y_raw)
            data_grids.append(grid)
        return {'grids': data_grids, 'n_series': n_series}

    def extract_psf_data(self, psf_results):
        """Extract PSF data from an FFT PSF analysis.

        Args:
            psf_results: Results object from psf.GetResults()

        Returns:
            List of 2D PSF grids, one per field.
        """
        psf_grids = []
        for i in range(psf_results.NumberOfDataSeries):
            series = psf_results.GetDataSeries(i)
            y_raw = series.YData.Data
            grid = self.safe_reshape(y_raw)
            psf_grids.append(grid)
        return {'grids': psf_grids, 'n_series': psf_results.NumberOfDataSeries}

    def extract_ray_fan_data(self, fan_results):
        """Extract ray fan data from a RayFan analysis.

        Args:
            fan_results: Results object from ray_fan.GetResults()

        Returns:
            List of dicts with pupil_x, tangential_y, sagittal_y per field.
        """
        fan_data = []
        for i in range(fan_results.NumberOfDataSeries):
            series = fan_results.GetDataSeries(i)
            x_raw = list(series.XData.Data)
            y_raw = series.YData.Data
            y = self.reshape(y_raw, y_raw.GetLength(0), y_raw.GetLength(1), True)
            fan_data.append({
                'pupil_x': x_raw,
                'tangential': y[0] if len(y) > 0 else [],
                'sagittal': y[1] if len(y) > 1 else [],
                'field': i + 1,
            })
        return fan_data

    # ------------------------------------------------------------------
    # NSC object helpers
    # ------------------------------------------------------------------

    def create_nsc_detector(self, obj_number, detector_type='rectangle',
                            x_half_width=5.0, y_half_width=5.0,
                            pixels_x=200, pixels_y=200,
                            material='ABSORB', comment='Detector'):
        """Create and configure an NSC detector object.

        Args:
            obj_number: NSC object number to configure as detector.
            detector_type: 'rectangle', 'surface', or 'volume'.
            x_half_width: Half-width in X (mm).
            y_half_width: Half-width in Y (mm).
            pixels_x: Number of X pixels.
            pixels_y: Number of Y pixels.
            material: Detector material (default 'ABSORB').
            comment: Object comment string.

        Returns:
            The configured detector object.
        """
        ZOSAPI = self.ZOSAPI
        TheNCE = self.TheSystem.NCE

        obj = TheNCE.GetObjectAt(obj_number)
        type_map = {
            'rectangle': ZOSAPI.Editors.NCE.ObjectType.DetectorRectangle,
            'surface': ZOSAPI.Editors.NCE.ObjectType.DetectorSurface,
            'volume': ZOSAPI.Editors.NCE.ObjectType.DetectorVolume,
        }
        obj.ChangeType(type_map.get(detector_type,
                                     ZOSAPI.Editors.NCE.ObjectType.DetectorRectangle))
        obj.GetCellAt(1).DoubleValue = x_half_width
        obj.GetCellAt(2).DoubleValue = y_half_width
        obj.GetCellAt(4).IntegerValue = pixels_x
        obj.GetCellAt(5).IntegerValue = pixels_y
        obj.Material = material
        obj.Comment = comment
        return obj

    def create_nsc_source(self, obj_number, source_type='elliptical',
                          x_half_width=1.0, y_half_width=1.0,
                          total_rays=1000000, layout_rays=50,
                          power_lumens=1.0, num_analysis_rays=1000000):
        """Create and configure an NSC source object.

        Args:
            obj_number: NSC object number to configure as source.
            source_type: 'elliptical', 'point', 'collimated', or 'rectangle'.
            x_half_width: Half-width in X (mm) for elliptical/rectangle.
            y_half_width: Half-width in Y (mm) for elliptical/rectangle.
            total_rays: Total rays for analysis.
            layout_rays: Rays shown in layout.
            power_lumens: Source power in lumens.
            num_analysis_rays: Number of analysis rays.

        Returns:
            The configured source object.
        """
        ZOSAPI = self.ZOSAPI
        TheNCE = self.TheSystem.NCE

        obj = TheNCE.GetObjectAt(obj_number)
        type_map = {
            'elliptical': ZOSAPI.Editors.NCE.ObjectType.SourceElliptical,
            'point': ZOSAPI.Editors.NCE.ObjectType.SourcePoint,
            'collimated': ZOSAPI.Editors.NCE.ObjectType.SourceCollimated,
            'rectangle': ZOSAPI.Editors.NCE.ObjectType.SourceRectangle,
        }
        obj.ChangeType(type_map.get(source_type,
                                     ZOSAPI.Editors.NCE.ObjectType.SourceElliptical))
        obj.GetCellAt(1).DoubleValue = x_half_width
        obj.GetCellAt(2).DoubleValue = y_half_width
        obj.GetCellAt(10).IntegerValue = total_rays
        obj.GetCellAt(11).IntegerValue = layout_rays
        obj.GetCellAt(8).DoubleValue = power_lumens
        obj.GetCellAt(12).IntegerValue = num_analysis_rays
        return obj

    # ------------------------------------------------------------------
    # Multi-configuration helpers
    # ------------------------------------------------------------------

    def add_configuration(self, config_number):
        """Add a new configuration to a multi-configuration system.

        Args:
            config_number: Configuration number (1-based).

        Returns:
            The MCE (Multi-Configuration Editor) object.
        """
        MCE = self.TheSystem.MCE
        if config_number > MCE.NumberOfConfigurations:
            MCE.AddConfiguration(config_number)
        return MCE

    def set_config_operand(self, config_num, operand_type, param1, param2=None,
                           param3=None, param4=None):
        """Set a multi-configuration operand value.

        Args:
            config_num: Configuration number (1-based).
            operand_type: ZOSAPI.Editors.MCE.MultiConfigOperandType enum.
            param1-4: Operand parameters (surface number, wavelength, etc.).
        """
        ZOSAPI = self.ZOSAPI
        MCE = self.TheSystem.MCE
        op = MCE.GetOperand(config_num, operand_type)
        op.Param1 = param1
        if param2 is not None:
            op.Param2 = param2
        if param3 is not None:
            op.Param3 = param3
        if param4 is not None:
            op.Param4 = param4
        return op

    # ------------------------------------------------------------------
    # Tolerance analysis helpers
    # ------------------------------------------------------------------

    def run_tolerance_sensitivity(self):
        """Run tolerance sensitivity analysis.

        Returns:
            List of dicts with tolerance operand sensitivities,
            sorted by sensitivity (worst first).
        """
        print('Running Tolerance Sensitivity Analysis...')
        tol = self.TheSystem.Tools.OpenTolerancing()
        try:
            tol.SetCriterion(self.ZOSAPI.Tools.Tolerancing.ToleranceCriterion.RMSWavefront)
            tol.SetSensitivity()
            tol.RunAndWaitForCompletion()
            results = tol.GetResults()
            summary = []
            n_ops = results.NumberOfOperands
            for i in range(1, n_ops + 1):
                op = results.GetOperand(i)
                summary.append({
                    'index': i,
                    'type': str(op.OperandType),
                    'surface': op.Surface,
                    'value': op.Value,
                    'sensitivity': op.Sensitivity,
                    'criterion_change': op.CriterionChange,
                })
            # Sort by sensitivity (worst first)
            summary.sort(key=lambda x: abs(x['sensitivity']), reverse=True)
        finally:
            tol.Close()
        return summary

    def run_tolerance_monte_carlo(self, n_trials=50, criterion=None):
        """Run Monte Carlo tolerance analysis.

        Args:
            n_trials: Number of Monte Carlo trials.
            criterion: ToleranceCriterion enum. Default: RMSWavefront.

        Returns:
            Dict with yield estimates and Monte Carlo statistics.
        """
        ZOSAPI = self.ZOSAPI
        if criterion is None:
            criterion = ZOSAPI.Tools.Tolerancing.ToleranceCriterion.RMSWavefront

        print(f'Running Monte Carlo Tolerance Analysis ({n_trials} trials)...')
        tol = self.TheSystem.Tools.OpenTolerancing()
        try:
            tol.SetCriterion(criterion)
            tol.SetMonteCarlo(n_trials)
            tol.RunAndWaitForCompletion()
            results = tol.GetResults()

            stats = {
                'n_trials': n_trials,
                'nominal': results.NominalCriterion,
                'mean': results.MeanCriterion,
                'std_dev': results.StdCriterion,
                'best': results.BestCriterion,
                'worst': results.WorstCriterion,
                'yield_90': results.GetYield(90.0),
                'yield_80': results.GetYield(80.0),
                'yield_50': results.GetYield(50.0),
                'cdf': [],
            }
            # Extract CDF data for plotting
            try:
                for i in range(results.CDFNumberOfPoints):
                    stats['cdf'].append({
                        'x': results.GetCDFX(i),
                        'y': results.GetCDFY(i),
                    })
            except Exception:
                pass  # CDF not always available
        finally:
            tol.Close()
        print(f'  Nominal: {stats["nominal"]:.4f}, Mean: {stats["mean"]:.4f}, '
              f'90% Yield: {stats["yield_90"]:.1f}%')
        return stats

    # ------------------------------------------------------------------
    # CAD export helpers
    # ------------------------------------------------------------------

    def export_cad(self, filename, cad_format='STEP', solids_only=True):
        """Export the optical system to a CAD file.

        Args:
            filename: Full output file path.
            cad_format: 'STEP', 'IGES', 'SAT', or 'STL'.
            solids_only: If True, export solids only.

        Returns:
            The output file path on success.
        """
        ZOSAPI = self.ZOSAPI
        format_map = {
            'STEP': ZOSAPI.Tools.CadExport.CadExportFormat.STEP,
            'IGES': ZOSAPI.Tools.CadExport.CadExportFormat.IGES,
            'SAT': ZOSAPI.Tools.CadExport.CadExportFormat.SAT,
            'STL': ZOSAPI.Tools.CadExport.CadExportFormat.STL,
        }
        fmt = format_map.get(cad_format.upper(),
                              ZOSAPI.Tools.CadExport.CadExportFormat.STEP)

        print(f'Exporting CAD to {cad_format}: {filename}')
        cad = self.TheSystem.Tools.OpenCadExport()
        try:
            cad.ExportFormat = fmt
            cad.SolidsOnly = solids_only
            cad.OutputFile = filename
            cad.RunAndWaitForCompletion()
            print(f'CAD export complete: {filename}')
            return filename
        finally:
            cad.Close()

    # ------------------------------------------------------------------
    # NSC CAD import
    # ------------------------------------------------------------------

    def import_cad(self, filename, cad_format='STEP', obj_number=1,
                   material='MIRROR'):
        """Import a CAD file into the NSC editor.

        Args:
            filename: CAD file path to import.
            cad_format: 'STEP', 'IGES', 'SAT', 'STL'.
            obj_number: NSC object number to place imported CAD.
            material: Material to assign.

        Returns:
            The imported NSC object.
        """
        ZOSAPI = self.ZOSAPI
        format_map = {
            'STEP': ZOSAPI.Editors.NCE.CADImportFormat.STEP,
            'IGES': ZOSAPI.Editors.NCE.CADImportFormat.IGES,
            'SAT': ZOSAPI.Editors.NCE.CADImportFormat.SAT,
            'STL': ZOSAPI.Editors.NCE.CADImportFormat.STL,
        }
        fmt = format_map.get(cad_format.upper(),
                              ZOSAPI.Editors.NCE.CADImportFormat.STEP)

        TheNCE = self.TheSystem.NCE
        obj = TheNCE.ImportCADFile(filename, fmt, obj_number)
        obj.Material = material
        return obj

    # ------------------------------------------------------------------
    # Grating & spectrum helpers
    # ------------------------------------------------------------------

    def create_diffraction_grating(self, surface_number, lines_per_um=0.5,
                                   order=1):
        """Configure a diffraction grating on a sequential surface.

        Args:
            surface_number: Surface number to apply grating.
            lines_per_um: Lines per micron.
            order: Diffraction order to use.

        Returns:
            The grating surface object.
        """
        surface = self.TheSystem.LDE.GetSurfaceAt(surface_number)
        # Set surface to diffraction grating type
        surface.ChangeType(self.ZOSAPI.Editors.LDE.SurfaceType.DiffractionGrating)
        # Configure grating parameters via coating/grating data
        surface.GetCellAt(12).DoubleValue = lines_per_um
        surface.GetCellAt(13).IntegerValue = order
        return surface

# ------------------------------------------------------------------
# Standalone plot generators — matplotlib wrappers
# ------------------------------------------------------------------

def plot_mtf(mtf_data, title='MTF Plot', save_path=None, show=False,
             diffraction_limit_freq=None, **kwargs):
    """Generate a publication-quality MTF plot from extracted MTF data.

    Args:
        mtf_data: List of dicts (from zos.extract_mtf_data()).
        title: Plot title.
        save_path: If given, save to this path instead of showing.
        show: If True, call plt.show().
        diffraction_limit_freq: Frequency for diffraction-limited line marker.
        **kwargs: Passed to matplotlib plot().

    Returns:
        (fig, ax) matplotlib objects.
    """
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = plt.cm.tab10(range(len(mtf_data)))
    for i, entry in enumerate(mtf_data):
        color = colors[i]
        label = f"Field {entry['field']}"
        if entry['tangential']:
            ax.plot(entry['frequency'], entry['tangential'], '-',
                    color=color, label=f'{label} Tan', linewidth=1.5)
        if entry['sagittal']:
            ax.plot(entry['frequency'], entry['sagittal'], '--',
                    color=color, label=f'{label} Sag', linewidth=1.5)

    if diffraction_limit_freq is not None:
        ax.axvline(diffraction_limit_freq, color='gray', linestyle=':',
                   alpha=0.6, label=f'Diff. Limit ({diffraction_limit_freq} c/mm)')

    ax.set_xlabel('Spatial Frequency (cycles/mm)')
    ax.set_ylabel('MTF')
    ax.set_title(title)
    ax.legend(loc='upper right', fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'MTF plot saved: {save_path}')
    if show:
        plt.show()
    return fig, ax


def plot_spot_diagram(spot_data, title='Spot Diagram Summary', save_path=None,
                      show=False):
    """Generate a bar chart comparing RMS and GEO spot sizes across fields.

    Args:
        spot_data: Dict from zos.extract_spot_data().
        title: Plot title.
        save_path: If given, save to this path.
        show: If True, call plt.show().

    Returns:
        (fig, ax) matplotlib objects.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    fig, ax = plt.subplots(figsize=(8, 5))
    spots = spot_data['spots']
    fields = [s['field'] for s in spots]
    rms_vals = [s['rms_spot_um'] for s in spots]
    geo_vals = [s['geo_spot_um'] for s in spots]

    x = np.arange(len(fields))
    width = 0.35
    ax.bar(x - width / 2, rms_vals, width, label='RMS Spot', color='steelblue')
    ax.bar(x + width / 2, geo_vals, width, label='GEO Spot', color='darkorange')
    ax.set_xlabel('Field')
    ax.set_ylabel('Spot Size (μm)')
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Field {f}' for f in fields])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'Spot diagram saved: {save_path}')
    if show:
        plt.show()
    return fig, ax


def plot_wavefront_map(wf_data, grid_index=0, title='Wavefront Map',
                       save_path=None, show=False, cmap='RdBu_r'):
    """Plot a 2D wavefront map from extracted wavefront data.

    Args:
        wf_data: Dict from zos.extract_wavefront_data().
        grid_index: Which series to plot (default 0).
        title: Plot title.
        save_path: If given, save to this path.
        show: If True, call plt.show().
        cmap: Matplotlib colormap name.

    Returns:
        (fig, ax) matplotlib objects.
    """
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 6))
    grid = wf_data['grids'][grid_index]
    im = ax.imshow(grid, cmap=cmap, aspect='equal', origin='lower')
    cbar = fig.colorbar(im, ax=ax, label='Waves')
    ax.set_title(title)
    ax.set_xlabel('Pupil X')
    ax.set_ylabel('Pupil Y')
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'Wavefront map saved: {save_path}')
    if show:
        plt.show()
    return fig, ax


def plot_ray_fan(fan_data, title='Ray Fan', save_path=None, show=False):
    """Plot ray fan curves from extracted ray fan data.

    Args:
        fan_data: List of dicts from zos.extract_ray_fan_data().
        title: Plot title.
        save_path: If given, save to this path.
        show: If True, call plt.show().

    Returns:
        (fig, ax) matplotlib objects.
    """
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = plt.cm.tab10(range(len(fan_data)))
    for i, entry in enumerate(fan_data):
        color = colors[i]
        if entry['tangential']:
            ax.plot(entry['pupil_x'], entry['tangential'], '-',
                    color=color, label=f"Field {entry['field']} Tan")
        if entry['sagittal']:
            ax.plot(entry['pupil_x'], entry['sagittal'], '--',
                    color=color, label=f"Field {entry['field']} Sag")

    ax.set_xlabel('Normalized Pupil Coordinate')
    ax.set_ylabel('Ray Error (waves or mm)')
    ax.set_title(title)
    ax.legend(loc='best', fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color='gray', linewidth=0.5)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'Ray fan saved: {save_path}')
    if show:
        plt.show()
    return fig, ax


def plot_detector_data(data_2d, title='NSC Detector Data', save_path=None,
                       show=False, cmap='hot', x_extent=5.0, y_extent=5.0):
    """Plot NSC detector data as a 2D image.

    Args:
        data_2d: 2D list from zos.get_detector_data() or similar.
        title: Plot title.
        save_path: If given, save to this path.
        show: If True, call plt.show().
        cmap: Matplotlib colormap.
        x_extent: X-axis extent in mm (half-width).
        y_extent: Y-axis extent in mm (half-width).

    Returns:
        (fig, ax) matplotlib objects.
    """
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(data_2d, cmap=cmap, aspect='equal', origin='lower',
                   extent=[-x_extent, x_extent, -y_extent, y_extent])
    cbar = fig.colorbar(im, ax=ax, label='Irradiance')
    ax.set_xlabel('X Position (mm)')
    ax.set_ylabel('Y Position (mm)')
    ax.set_title(title)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'Detector data saved: {save_path}')
    if show:
        plt.show()
    return fig, ax


def plot_tolerance_cdf(tol_stats, title='Tolerance CDF', save_path=None,
                       show=False):
    """Plot the cumulative distribution function from tolerance analysis.

    Args:
        tol_stats: Dict from zos.run_tolerance_monte_carlo().
        title: Plot title.
        save_path: If given, save to this path.
        show: If True, call plt.show().

    Returns:
        (fig, ax) matplotlib objects.
    """
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 5))
    cdf = tol_stats.get('cdf', [])
    if cdf:
        xs = [p['x'] for p in cdf]
        ys = [p['y'] for p in cdf]
        ax.plot(xs, ys, 'b-', linewidth=2)
        ax.axvline(tol_stats['nominal'], color='green', linestyle='--',
                   label=f"Nominal: {tol_stats['nominal']:.3f}")
        ax.axhline(90, color='red', linestyle=':', alpha=0.5, label='90% yield')
        ax.axhline(80, color='orange', linestyle=':', alpha=0.5, label='80% yield')
        ax.legend()
    else:
        ax.text(0.5, 0.5, 'No CDF data available', ha='center', va='center',
                transform=ax.transAxes)
    ax.set_xlabel('Criterion Value')
    ax.set_ylabel('Cumulative Probability (%)')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f'Tolerance CDF saved: {save_path}')
    if show:
        plt.show()
    return fig, ax


# ------------------------------------------------------------------
# Script template engine
# ------------------------------------------------------------------

SCRIPT_TEMPLATES = {}

def register_template(name, template_func):
    """Register a script template function under a name.

    Args:
        name: Template name (e.g., 'sequential_spot_diagram').
        template_func: Callable that receives keyword params and returns
                       a Python script as a string.
    """
    SCRIPT_TEMPLATES[name] = template_func


def generate_script(template_name, output_path=None, **params):
    """Generate a Python script from a registered template.

    Args:
        template_name: Name of a registered template.
        output_path: If given, write the script to this file path.
        **params: Template-specific parameters.

    Returns:
        The generated Python script as a string.

    Raises:
        ValueError: If template_name is not registered.
    """
    if template_name not in SCRIPT_TEMPLATES:
        available = ', '.join(sorted(SCRIPT_TEMPLATES.keys()))
        raise ValueError(
            f"Unknown template '{template_name}'. Available: {available}"
        )

    script = SCRIPT_TEMPLATES[template_name](**params)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script)
        print(f'Script written: {output_path}')

    return script


# Pre-register common templates
def _template_sequential_system(**p):
    """Template: Basic sequential system with an aperture, fields, wavelengths."""
    zos_path = p.get('zos_path', 'None')
    save_as = p.get('save_as', 'generated_system.zos')
    aperture = p.get('aperture', 20.0)
    wl_preset = p.get('wl_preset', 'd_0p587')
    return f'''"""Generated: Basic sequential optical system."""
import sys, os
_PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
for _p in [
    os.path.join(_PLUGIN_ROOT, 'scripts') if _PLUGIN_ROOT else '',
]:
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p); break
from zos_utils import ZOSConnection, set_seed, ensure_zmx_dir
set_seed(42)

with ZOSConnection({zos_path}) as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    TheSystem.New(False)
    TheSystem.SaveAs(ensure_zmx_dir() + "\\\\{save_as}")

    SD = TheSystem.SystemData
    SD.MaterialCatalogs.AddCatalog('SCHOTT')
    SD.Aperture.ApertureValue = {aperture}
    SD.Wavelengths.SelectWavelengthPreset(
        ZOSAPI.SystemData.WavelengthPreset.{wl_preset})
    Field_1 = SD.Fields.GetField(1)
    SD.Fields.AddField(0, 5.0, 1.0)

    zos.validate_system_ready()
    print('System created and validated.')
'''

register_template('sequential_system', _template_sequential_system)


def _template_sequential_optimization(**p):
    """Template: Sequential system with variables, merit function, and optimization."""
    return f'''"""Generated: Sequential optimization."""
import sys, os
_PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
for _p in [
    os.path.join(_PLUGIN_ROOT, 'scripts') if _PLUGIN_ROOT else '',
]:
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p); break
from zos_utils import ZOSConnection, set_seed, ensure_zmx_dir
set_seed(42)

with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    TheSystem.New(False)

    SD = TheSystem.SystemData
    SD.MaterialCatalogs.AddCatalog('SCHOTT')
    SD.Aperture.ApertureValue = {p.get('aperture', 20.0)}
    SD.Wavelengths.SelectWavelengthPreset(
        ZOSAPI.SystemData.WavelengthPreset.{p.get('wl_preset', 'd_0p587')})
    SD.Fields.AddField(0, {p.get('field_angle', 5.0)}, 1.0)

    zos.validate_system_ready()

    # Add lens surfaces
    LDE = TheSystem.LDE
    for _ in range({p.get('n_surfaces', 2)}):
        LDE.InsertNewSurfaceAt(2)

    {p.get('surface_config', '# Configure surfaces here')}

    # Make variables
    {p.get('variables', '# Add variables here')}

    # Build merit function
    MFE = TheSystem.MFE
    MFE.RemoveOperands(1, MFE.NumberOfOperands)
    # Default merit function with RMS spot
    MFE.MakeMeritFunction(
        ZOSAPI.Editors.MFE.MeritFunctionType.RMS,
        ZOSAPI.Tools.Optimization.OptimizationOperandType.SpotRadius,
        1, 0, 0.0, SD.Wavelengths.NumberOfWavelengths,
        0.0, 0.0, 0.0, True
    )

    # Optimize
    zos.run_dls_optimization({p.get('cycles', 'None')})

    output = ensure_zmx_dir() + "\\\\{p.get('save_as', 'optimized.zos')}"
    zos.save_file(output)
    print(f'Saved: {{output}}')
'''

register_template('sequential_optimization', _template_sequential_optimization)


def _template_nsc_ray_trace(**p):
    """Template: NSC ray trace with source and detector."""
    return f'''"""Generated: NSC ray trace."""
import sys, os
_PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', '')
for _p in [
    os.path.join(_PLUGIN_ROOT, 'scripts') if _PLUGIN_ROOT else '',
]:
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p); break
from zos_utils import ZOSConnection, set_seed, ensure_zmx_dir
set_seed(42)

with ZOSConnection() as zos:
    ZOSAPI = zos.ZOSAPI
    zos.new_file(ZOSAPI.SystemType.NonSequential)
    TheNCE = zos.TheSystem.NCE

    # Source
    source = zos.create_nsc_source(1, source_type='{p.get('source_type', 'elliptical')}',
        x_half_width={p.get('source_hw', 1.0)},
        y_half_width={p.get('source_hw_y', p.get('source_hw', 1.0))},
        total_rays={p.get('total_rays', 1000000)},
        power_lumens={p.get('power_lumens', 1.0)})
    self.set_nsc_position(source, z={p.get('source_z', 0.0)})

    # Detector
    det_num = TheNCE.NumberOfObjects + 1
    TheNCE.InsertNewObjectAt(det_num)
    det = zos.create_nsc_detector(det_num,
        x_half_width={p.get('det_hw', 5.0)},
        y_half_width={p.get('det_hw_y', p.get('det_hw', 5.0))},
        pixels_x={p.get('pixels_x', 200)},
        pixels_y={p.get('pixels_y', 200)})
    self.set_nsc_position(det, z={p.get('det_z', 50.0)})

    # Trace
    TheNCE.ClearDetectors()
    tray = TheNCE.TraceAll()

    # Read detector data
    w, h, data = zos.get_detector_data(det_num)
    print(f'Detector {{det_num}}: {{w}}x{{h}} pixels')
'''

register_template('nsc_ray_trace', _template_nsc_ray_trace)

# ------------------------------------------------------------------
# Standalone helpers — can be imported directly
# ------------------------------------------------------------------

def get_zemax_root():
    """Return the Zemax OpticStudio installation root from registry."""
    aKey = None
    try:
        aKey = winreg.OpenKey(
            winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER),
            r"Software\Zemax", 0, winreg.KEY_READ
        )
        zemaxData = winreg.QueryValueEx(aKey, 'ZemaxRoot')
        return zemaxData[0]
    finally:
        if aKey is not None:
            winreg.CloseKey(aKey)

def ensure_zmx_dir(base_path=None):
    """Standalone: create zmx/ directory and return path.

    Can be called without a ZOSConnection instance.
    """
    if base_path is None:
        base_path = os.getcwd()
    zmx_dir = os.path.join(base_path, "zmx")
    if not os.path.exists(zmx_dir):
        os.makedirs(zmx_dir)
    return zmx_dir
