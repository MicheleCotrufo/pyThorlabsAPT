from .core import *
from . import core as _core


def list_available_devices():
    """
    Lists all devices currently connected to the computer.

    Initializes the underlying APT library on the first call (if not already loaded), then queries
    for connected devices. The library is intentionally initialized only once: re-initializing it
    (APTCleanUp + APTInit) would drop all active device connections, breaking any Motor objects that
    are currently in use. As a consequence, devices plugged in after the first call to this function
    will not be discovered without restarting the process.

    Returns
    -------
    out : list
        list of available devices. Each device is described by a tuple (hardware type, serial number)
    """
    if _core._lib is None:
        _core._lib = _core._load_library()
    return _core.list_available_devices()
