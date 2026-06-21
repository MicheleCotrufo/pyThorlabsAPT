# pyThorlabsAPT

```pyThorlabsAPT``` is a Python library/GUI interface to control any motor compatible with the Thorlabs APT communication protocol. The package is composed of two parts, a
low-level driver to perform basic operations, and a high-level GUI, written with PyQt5, which can be easily embedded into other GUIs. The low-level driver is essentially a wrapper of the excellent
package [thorlabs_apt](https://github.com/qpit/thorlabs_apt), with a few tweaks to speed up loading time and error handling.
Since [thorlabs_apt](https://github.com/qpit/thorlabs_apt) is not available via ```pip```, its code has been embedded in the code of this package, [here](https://github.com/MicheleCotrufo/pyThorlabsAPT/tree/master/pyThorlabsAPT/thorlabs_apt).
A virtual (software-simulated) backend is also included, so the driver and the GUI can be used and tested without any real hardware, APT.dll, or the Thorlabs APT software installed.

The interface can work either as a stand-alone application, or as a module of [ergastirio](https://github.com/MicheleCotrufo/ergastirio).

## Table of Contents
 - [Installation](#installation)
 - [Usage via the low-level driver](#usage-via-the-low-level-driver)
   * [Creating a driver instance](#creating-a-driver-instance)
   * [Virtual mode (no hardware needed)](#virtual-mode-no-hardware-needed)
   * [Properties](#properties)
   * [Other attributes](#other-attributes)
   * [Methods](#methods)
   * [Direction and units constants](#direction-and-units-constants)
   * [Examples](#examples)
 - [Usage as a stand-alone GUI interface](#usage-as-a-stand-alone-GUI-interface)
 - [Embed the GUI within another GUI](#embed-the-gui-within-another-gui)


## Installation
The package uses the Thorlabs APT.dll shared library, and therefore the low-level driver and the real (non-virtual) GUI only work under Windows. The virtual backend, however, works on any platform. To install, follow these steps:

1. Install the script via the package manager pip,
```bash
pip install pyThorlabsAPT==0.11
```
Important: due to a bug of pypi, if you run just '''pip install pyThorlabsAPT''' it might default to a stale version 0.21, which was wrongly uploaded on pypi in the past and it does not work. Make sure you specify the version.

2. Install the APT software from [here](https://www.thorlabs.com/software-pages/motion_control/) (clik on the tab 'Archive'). The version of the software (32 or 64 bit) must match the one of your python installation.

3. Locate the file APT.dll which has been installed on your computer by the APT software. This file will typically be in the folder "[APT Installation Folder]\APT Server", where
[APT Installation Folder] is the installation folder of the APT software (typically [APT Installation Folder] = C:\Program Files\Thorlabs\APT). Copy the APT.dll into one of these locations:
	<ul>
	      <li>C:\Windows\System32.</li>
	      <li>The folder of your python application.</li>
	      <li>Inside the "[Python packages folder]\pyThorlabsAPT\thorlabs_apt". Most of the times [Python packages folder] = "[Python folder]\Lib\site-packages".</li>
	</ul>

Steps 2 and 3 are only needed to talk to real hardware; they can be skipped entirely if you only intend to use the virtual driver (see [Virtual mode](#virtual-mode-no-hardware-needed) below).

These steps are enough to run the low-level driver of ```pyThorlabsAPT```. In order to use the GUI, it is necessary to install additional libraries,
specified in the ```requirements.txt``` file,
```bash
pip install abstract_instrument_interface>=0.10
pip install "PyQt5>=5.15.6"
pip install pyqtgraph
pip install numpy
```

## Usage via the low-level driver

`pyThorlabsAPT` can be used to control a device from the command line or from your Python script.

The class `pyThorlabsAPT` wraps the connected device's low-level `Motor` object (defined in [thorlabs_apt](https://github.com/qpit/thorlabs_apt) for real hardware, or in
`pyThorlabsAPT.thorlabs_apt_virtual` for the simulated backend) and exposes the subset of its properties and methods needed to find, connect to, and operate a stage. A
full list of properties, attributes, and methods is available below. **Note**: the documentation below was partially compiled with the help of Claude - mistakes are possible.

### Creating a driver instance

```python
pyThorlabsAPT(virtual=False)
```

| Parameter | Type | Description |
| --- | --- | --- |
| `virtual` | bool, optional | If `True`, use the virtual backend (`pyThorlabsAPT.thorlabs_apt_virtual`) instead of real hardware (see [Virtual mode](#virtual-mode-no-hardware-needed) below). Default is `False`. |

### Virtual mode (no hardware needed)

Passing `virtual=True` makes the driver simulate APT motors instead of talking to the real APT.dll. Two virtual motors with different specs are available. This is useful for testing or demoing the package without a physical
instrument, and works even if the Thorlabs APT software is not installed.

```python
from pyThorlabsAPT.driver import pyThorlabsAPT
instrument = pyThorlabsAPT(virtual=True)
available_devices = instrument.list_devices()
print(available_devices)
instrument.connect_device(device_addr=available_devices[0][1])
instrument.move_home()
print(instrument.position)   # returns a simulated, time-varying position while homing
instrument.disconnect_device()
```

### Properties

The following are implemented as Python `@property`. Reading or setting either of these requires a device to be connected; otherwise, accessing them raises an `AttributeError` (no underlying `Motor` object has been created yet).

| Property | Type | Description | <div style="width:300px"> Can be set?</div> | Notes |
| --- | --- | --- | --- | --- |
| `position` | float | Current position of the motor. | Yes | Setting it starts a non-blocking absolute move. Poll `is_in_motion` (or call `instrument.motor.position` again) to know when the move has finished. |
| `is_in_motion` | bool | Whether the motor is currently moving. | No | |

### Other attributes

| Attribute | Type | Description |
| --- | --- | --- |
| `connected` | bool | `True` if a device is currently connected, `False` otherwise. |
| `motor` | `Motor` instance | The underlying real or virtual `Motor` object, created by `connect_device()` upon a successful connection. Does not exist until a device has been connected. |
| `list_valid_devices` | list | List of devices found by the most recent call to `list_devices()`. |

### Methods
| Method | Returns | Description  |
| --- | --- | --- | 
| `list_devices()` | list | Returns a list of all available devices. Each element is a 2-element tuple `(identity, address)`, where `identity` is an integer hardware-type code and `address` is the integer serial number to pass to `connect_device()`. |
| `connect_device(device_addr)` | (str or int, int) | Attempts to connect to the device identified by `device_addr` (its serial number, as returned by `list_devices()`). Returns `(Msg, ID)`: `Msg` is `device_addr` on success, or an error message on failure; `ID` is `1` if connection was successful, `0` otherwise. Raises `ValueError` if `device_addr` does not match any device returned by the most recent call to `list_devices()`. |
| `disconnect_device()` | (str, int) | Attempts to disconnect the currently connected device. Returns `(Msg, ID)`, analogous to `connect_device()`. Raises `RuntimeError` if no device is currently connected. |
| `move_home(blocking=False)` | None | Moves the motor to its home position (position 0). |
| `move_jog(direction, blocking=False)` | None | Jogs the motor by the currently configured jog step size (see `get_jog_parameters`/`set_jog_parameters`), in the given `direction` (see [Direction and units constants](#direction-and-units-constants) below). |
| `stop_profiled()` | None | Stops any ongoing movement (profiled stop). |
| `get_stage_axis_info()` | (float, float, int, float) | Returns `(min_pos, max_pos, units, pitch)` for the connected stage. `units` is an integer code (see [Direction and units constants](#direction-and-units-constants) below). |
| `set_stage_axis_info(min_pos, max_pos, units, pitch)` | None | Sets the stage axis parameters. |
| `get_jog_parameters()` | (int, int, float, float, float, float) | Returns `(Mode, StopMode, StepSize, MinVel, Accn, MaxVel)`. |
| `set_jog_parameters(Mode, StopMode, StepSize, MinVel, Accn, MaxVel)` | None | Sets the jog parameters. |

**Note:** unlike earlier versions of this package, `pyThorlabsAPT` no longer subclasses the underlying `Motor` object, so properties/methods of `Motor` that are not listed above (e.g. `hardware_info`, `move_by()`, `move_to()`, `enable()`/`disable()`, velocity/PID parameters, etc.) are not directly exposed on the driver. After connecting, you can still reach them via the `motor` attribute, e.g. `instrument.motor.hardware_info`.

### Direction and units constants

`move_jog()` and `get_stage_axis_info()`/`set_stage_axis_info()` use a few integer constants. These are defined on the backend module in use, not on the `pyThorlabsAPT` class itself:

```python
from pyThorlabsAPT.thorlabs_apt import MOVE_FWD, MOVE_REV, STAGE_UNITS_MM, STAGE_UNITS_DEG
# or, when using the virtual driver:
from pyThorlabsAPT.thorlabs_apt_virtual import MOVE_FWD, MOVE_REV, STAGE_UNITS_MM, STAGE_UNITS_DEG
```

| Constant | Value | Meaning |
| --- | --- | --- |
| `MOVE_FWD` | 1 | Move/jog in the forward direction. |
| `MOVE_REV` | 2 | Move/jog in the reverse direction. |
| `STAGE_UNITS_MM` | 1 | Stage units in millimeters. |
| `STAGE_UNITS_DEG` | 2 | Stage units in degrees. |

### Examples

```python
from pyThorlabsAPT.driver import pyThorlabsAPT
from pyThorlabsAPT.thorlabs_apt import MOVE_FWD
import time

instrument = pyThorlabsAPT()
available_devices = instrument.list_devices()              # Check which devices are available
print(available_devices)

device_addr = available_devices[0][1]                      # The address is the 2nd element of each tuple
instrument.connect_device(device_addr=device_addr)          # Connect to the first available device

instrument.move_home()                                      # Start homing
while instrument.is_in_motion:                               # Poll until homing is done
    time.sleep(0.1)

instrument.position = 10                                    # Start a non-blocking absolute move to position 10
while instrument.is_in_motion:
    time.sleep(0.1)
print(instrument.position)

instrument.move_jog(MOVE_FWD)                                # Jog forward by one jog step
print(instrument.get_stage_axis_info())                      # (min_pos, max_pos, units, pitch)

instrument.disconnect_device()                               # Disconnect the device
```

## Usage as a stand-alone GUI interface
The installation sets up an entry point for the GUI. Just typing
```bash
pyThorlabsAPT
```
in the command prompt will start the GUI. Pass `-virtual` to start it with the simulated driver instead of real hardware (useful for testing without a physical motor):
```bash
pyThorlabsAPT -virtual
```

## Embed the GUI within another GUI
The GUI controller can also be easily integrated within a larger graphical interface, as shown in the example below.

```python
import PyQt5.QtWidgets as Qt  # QApplication, QWidget, QGridLayout, QLabel, QVBoxLayout
import pyThorlabsAPT

app = Qt.QApplication([])
window = Qt.QWidget()

# The GUI needs to be contained inside a widget object
widget_containing_interface_GUI = Qt.QWidget()
widget_containing_interface_GUI.setStyleSheet(
    ".QWidget {\n"
    "border: 1px solid black;\n"
    "border-radius: 4px;\n"
    "}"
)

# Create the interface object for the motor (pass virtual=True to use the simulated driver instead of real hardware)
Interface = pyThorlabsAPT.interface(app=app, virtual=False)
Interface.verbose = False  # set the verbosity of the interface logger to False
# At any time during the software execution, the position read by the instrument can be accessed via Interface.output['Position']
# Moreover, one could also set up a signal to automatically call another function whenever the position is updated, by
#
#       Interface.sig_update_position.connect(foo)
#
# Every time the position is read from the instrument, the function foo is called and the new position is passed as argument

# Create the GUI for the motor
view = pyThorlabsAPT.gui(interface=Interface, parent=widget_containing_interface_GUI)

# Create additional GUI
gridlayoutwidget = Qt.QWidget()
gridlayout = Qt.QGridLayout()
gridlayout.addWidget(Qt.QLabel("Additional GUI 1"), 0, 0)
gridlayout.addWidget(Qt.QLabel("Additional GUI 2"), 1, 0)
gridlayout.addWidget(Qt.QLabel("Additional GUI 3"), 0, 1)
gridlayout.addWidget(Qt.QLabel("Additional GUI 4"), 1, 1)
gridlayoutwidget.setLayout(gridlayout)

layout = Qt.QVBoxLayout()
layout.addWidget(widget_containing_interface_GUI)
layout.addWidget(gridlayoutwidget)
layout.addStretch(1)
window.setLayout(layout)

window.show()
app.exec()  # Start the event loop.
```
