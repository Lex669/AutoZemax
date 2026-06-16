"""
AutoZemax Shared Utilities — ZOS-API Connection & Data Handling.

Encapsulates the .NET interop boilerplate from official Zemax examples into a
reusable Python class. All AutoZemax skills generate scripts that import this module.

Usage:
    from zos_utils import ZOSConnection

    with ZOSConnection() as zos:
        # Access API objects
        system = zos.TheSystem
        api = zos.ZOSAPI
        # ... your automation code ...

Environment:
    Python: C:\\Users\\Lex\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe
    Zemax:  Ansys Zemax OpticStudio 2025 R2 (v252)
"""

import clr
import os
import sys
import winreg
from itertools import islice


class ZOSConnection:
    """Manages the ZOS-API .NET interop connection lifecycle.

    Handles registry lookup, assembly loading, application creation,
    and provides utility methods for data reshaping.

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

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self):
        """Establish the full ZOS-API connection stack.

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
        """Load an existing .zos file."""
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
            x: Width (use data.GetLength(0)).
            y: Height (use data.GetLength(1)).
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
        """Read coherent real + imaginary data and compute phase.

        Args:
            detector_number: NSC object number of the detector.

        Returns:
            (width, height, real_2d, imag_2d, phase_deg_2d, amplitude_2d)
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

        # Phase calculation (avoid numpy dependency at this layer)
        return w, h, real, imag, None, None  # Caller computes phase with numpy

# ------------------------------------------------------------------
# Standalone helper — can be imported directly
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
