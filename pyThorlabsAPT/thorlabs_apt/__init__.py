from .core import *
from . import core as _core


def list_available_devices():
    """
    Lists all devices currently connected to the computer.

    This re-initializes the underlying APT library connection before querying for devices (overriding
    core.list_available_devices(), which does not do this), so that devices plugged in after this
    package was imported -- or since the last call to this function -- can be discovered.

    Returns
    -------
    out : list
        list of available devices. Each device is described by a tuple (hardware type, serial number)
    """
    _core._cleanup()
    _core._lib = _core._load_library()
    return _core.list_available_devices()
