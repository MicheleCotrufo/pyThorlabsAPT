# pyThorlabsAPT

```pyThorlabsAPT``` is a Python library/GUI interface to control any motor compatible with the Thorlabs APT communication protocol. The package is composed of two parts, a
low-level driver to perform basic operations, and a high-level GUI, written with PyQt5, which can be easily embedded into other GUIs. The low-level driver is essentially a wrapper of the excellent
package [thorlabs_apt](https://github.com/qpit/thorlabs_apt), with a few tweaks to speed up loading time and error handling.
Since [thorlabs_apt](https://github.com/qpit/thorlabs_apt) is not available via ```pip```, its code has been embedded in the code of this package, [here](https://github.com/MicheleCotrufo/pyThorlabsAPT/tree/master/pyThorlabsAPT/thorlabs_apt).

The interface can work either as a stand-alone application, or as a module of [ergastirio](https://github.com/MicheleCotrufo/ergastirio).

## Table of Contents
 - [Installation](#installation)
  - [Usage via the low-level driver](#usage-via-the-low-level-driver)
	* [Examples](#examples)
 - [Usage as a stand-alone GUI interface](#usage-as-a-stand-alone-GUI-interface)
 - [Embed the GUI within another GUI](#embed-the-gui-within-another-gui)


## Installation
The package uses the Thorlabs APT.dll shared library, and therefore it only works under Windows. To install, follow these steps:

1. Install the script via the package manager pip,
```bash
pip install pyThorlabsAPT==0.11
```
Important: due to a bug of pypi, if you run just '''pip install pyThorlabsAPT''' it will default to version 0.21, which was wrongly uploaded on pypi in the past and it does not work. Make sure you specify the version

2. Install the APT software from [here](https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control). The version of the software (32 or 64 bit) must match the one of your python installation.

3. Locate the file APT.dll which has been installed on your computer by the APT software. This file will typically be in the folder "[APT Installation Folder]\APT Server", where
[APT Installation Folder] is the installation folder of the APT software (typically [APT Installation Folder] = C:\Program Files\Thorlabs\APT). Copy the APT.dll into one of these locations:
	<ul>
	      <li>C:\Windows\System32.</li>
	      <li>The folder of your python application.</li>
	      <li>Inside the "[Python packages folder]\pyThorlabsAPT\thorlabs_apt". Most of the times [Python packages folder] = "[Python folder]\Lib\site-packages".</li>
	</ul>

These steps are enough to run the low-level driver of ```pyThorlabsAPT```. In order to use the GUI, it is necessary to install additional libraries,
specified in the ```requirements.txt``` file,
```bash
pip install abstract_instrument_interface>=0.6
pip install "PyQt5>=5.15.6"
pip install "pyqtgraph>=0.12.4"
pip install numpy
```

## Usage via the low-level driver

`pyThorlabsAPT` can be used to control a device from the command line or from your Python script.

### Example

```python
from pyThorlabsAPT.driver import pyThorlabsAPT
instrument = pyThorlabsAPT()
available_devices = instrument.list_devices()
print(available_devices)
instrument.connect_device(device_addr = available_devices[0][0])
instrument.hardware_info
instrument.move_home()
instrument.move_by(10)
instrument.is_in_motion # returns True when instrument is moving
instrument.position = 10 # Goes to position 10
```
Most of the properties and methods of the class `pyThorlabsAPT` are actually inherited from the [thorlabs_apt](https://github.com/qpit/thorlabs_apt) package. 
Here below the main properties and methods are summarized for quick reference.

**Properties**

| Property | Type | Description | <div style="width:300px"> Can be set?</div> | Notes |
| --- | --- | --- | --- | --- |
| `position` | float | Read or set current position of the motor. | Yes |
|`stage_info`|(float,float,int,float)| Read current stage parameters | No |

**Methods**
| Method | Returns | Description  |
| --- | --- | --- | 
| `list_devices()` | list |  Returns a list of all available devices. Each element of the list identifies a different device, and it is a three-element list in the form `[address,identity,model]`. The string `address` contains the physical address of the device. The string `idn` contains the 'identity' of the device. The string `model` contains the device model.| 
| `connect_device(device_addr: str)` | (str,int) |  Attempt to connect to the device identified by the address in the string  `device_addr`. It returns a list of two elements. The first element is a string containing either the address of the connected device or an error message. The second element is an integer, equal to 1 if connection was succesful or to 0 otherwise. | 
| `disconnect_device()` | (str,int)  | Attempt to disconnect the currently connected device. It returns a list of two elements. The first element is a string containing info on succesful disconnection or an error message. The second element is an integer, equal to 1 if disconnection was succesful or to 0 otherwise.  |
| `move_home()` |   |    | 
| `move_by(movement: float)` | int | Set the zero to the currently connected (if any) console. The returned value is 1 if the operation was successful, or 0 if any error occurred. | 
| `set_stage_axis_info(min:float, max:float, units:int, pitch:float)`|  |  | 

## Usage as a stand-alone GUI interface
The installation sets up an entry point for the GUI. Just typing
```bash
pyThorlabsAPT
```
in the command prompt will start the GUI.

## Embed the GUI within another GUI
The GUI controller can also be easily integrated within a larger graphical interface, as shown in the [TO DO] 
