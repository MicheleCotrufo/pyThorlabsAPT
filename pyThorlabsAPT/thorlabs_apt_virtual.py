"""
Note: most of docstrings in this file have been generated automatically by Claude. AI can make mistakes

Drop-in replacement for pyThorlabsAPT.thorlabs_apt that simulates two Thorlabs APT motors.
Exposes the same Motor / list_available_devices() API that driver.py uses, so that
pyThorlabsAPT.driver.pyThorlabsAPT(virtual=True) can run without any real hardware, APT.dll, or
serial connection.
"""

import time

# Stage units (mirrors pyThorlabsAPT.thorlabs_apt.core)
STAGE_UNITS_MM = 1
"""Stage units in mm"""
STAGE_UNITS_DEG = 2
"""Stage units in degrees"""

# Move direction, used with move_jog (mirrors pyThorlabsAPT.thorlabs_apt.core)
MOVE_FWD = 1
"""Move forward."""
MOVE_REV = 2
"""Move reverse."""

# Per-device configuration. Each entry describes one simulated motor.
_DEVICE_CONFIGS = [
    {'hwtype': 31, 'serial_number': 123456, 'min_pos': 0, 'max_pos': 360, 'units': STAGE_UNITS_DEG, 'pitch': 1},
    {'hwtype': 31, 'serial_number': 7890,   'min_pos': 0, 'max_pos': 25,  'units': STAGE_UNITS_MM,  'pitch': 1},
]


def list_available_devices():
    '''
    Returns the (hardware type, serial number) of the simulated devices, mimicking
    pyThorlabsAPT.thorlabs_apt.list_available_devices().

    Returns
    -------
    out : list
        list of available (virtual) devices. Each device is described by a tuple
        (hardware type, serial number)
    '''
    return [(cfg['hwtype'], cfg['serial_number']) for cfg in _DEVICE_CONFIGS]


class Motor:
    '''
    Simulated Thorlabs motor. Exposes the same API as pyThorlabsAPT.thorlabs_apt.core.Motor (the real,
    ctypes-based motor object), but all motion is computed in software based on elapsed time and a
    fixed simulated speed: no hardware, DLL, or serial connection is involved.

    Only the subset of the real Motor's API that is used elsewhere in pyThorlabsAPT is implemented.

    Parameters
    ----------
    serial_number : int
        Serial number identifying the (virtual) device. Must match one of the serial numbers returned
        by list_available_devices().

    Raises
    ------
    Exception
        If serial_number does not match any of the simulated devices.
    '''

    _speed = 2  # simulated speed, in position units per second

    def __init__(self, serial_number):
        for cfg in _DEVICE_CONFIGS:
            if cfg['serial_number'] == serial_number:
                self._stage_axis_info = [cfg['min_pos'], cfg['max_pos'], cfg['units'], cfg['pitch']]
                break
        else:
            raise Exception("Could not initialize device: no virtual device with serial number %s" % serial_number)
        self._serial_number = serial_number
        self._jog_parameters = [2, 2, 1, 0, 1, self._speed]  # Mode, StopMode, StepSize, MinVel, Accn, MaxVel
        self._position = 0
        self._position_target = 0
        self._last_position_update = time.time()

    @property
    def serial_number(self):
        '''
        Returns the serial number of the motor.
        '''
        return self._serial_number

    def _update_position(self):
        # Advances self._position towards self._position_target, based on elapsed time and self._speed.
        # Snaps exactly to the target once within 0.1 units, to avoid an endless tail of tiny moves.
        if self._position_target == self._position:
            return
        now = time.time()
        direction = 1 if self._position_target > self._position else -1
        self._position += direction * self._speed * (now - self._last_position_update)
        self._last_position_update = now
        if abs(self._position_target - self._position) < 0.1:
            self._position = self._position_target

    @property
    def is_in_motion(self):
        '''
        Returns whether motor is in motion.
        '''
        self._update_position()
        return self._position != self._position_target

    @property
    def position(self):
        '''
        Position of motor. Setting the position is absolute and non-blocking.
        '''
        self._update_position()
        return self._position

    @position.setter
    def position(self, value):
        self._update_position()
        self._last_position_update = time.time()
        self._position_target = value

    def move_to(self, value, blocking=False):
        '''
        Move to absolute position.

        Parameters
        ----------
        value : float
            absolute position of the motor
        blocking : bool
            Ignored in the virtual driver (motion is always simulated as non-blocking, and is meant to
            be polled via is_in_motion). Provided for API compatibility with the real Motor.
        '''
        self.position = value

    def move_by(self, value, blocking=False):
        '''
        Move relative to current position.

        Parameters
        ----------
        value : float
            relative distance
        blocking : bool
            Ignored in the virtual driver. See move_to.
        '''
        self.position = self.position + value

    def move_jog(self, direction, blocking=False):
        '''
        Move jog: moves by the simulated StepSize (see get_jog_parameters/set_jog_parameters), in the
        given direction.

        Parameters
        ----------
        direction : int
            MOVE_FWD = 1 : move in forward direction.
            MOVE_REV = 2 : move in reverse direction.
        blocking : bool
            Ignored in the virtual driver. See move_to.
        '''
        step = self._jog_parameters[2]
        self.position = self.position + (step if direction == MOVE_FWD else -step)

    def move_home(self, blocking=False):
        '''
        Move to home position (position = 0).

        Parameters
        ----------
        blocking : bool
            Ignored in the virtual driver. See move_to.
        '''
        self.position = 0

    def stop_profiled(self):
        '''
        Stop motor. In the real Motor this ramps the velocity down smoothly; in this simulation the
        motor stops immediately at its current (interpolated) position.
        '''
        self._update_position()
        self._position_target = self._position

    def get_stage_axis_info(self):
        '''
        Returns axis information of stage.

        Returns
        -------
        out : tuple
            (minimum position, maximum position, stage units, pitch)
        '''
        return tuple(self._stage_axis_info)

    def set_stage_axis_info(self, min_pos, max_pos, units, pitch):
        '''
        Sets axis information of stage.

        Parameters
        ----------
        min_pos : float
            minimum position
        max_pos : float
            maximum position
        units : int
            stage units: STAGE_UNITS_MM = 1, STAGE_UNITS_DEG = 2
        pitch : float
            pitch
        '''
        self._stage_axis_info = [min_pos, max_pos, units, pitch]

    def get_jog_parameters(self):
        '''
        Returns jog parameters.

        Returns
        -------
        out : tuple
            (Mode, StopMode, StepSize, MinVel, Accn, MaxVel)
        '''
        return tuple(self._jog_parameters)

    def set_jog_parameters(self, Mode, StopMode, StepSize, MinVel, Accn, MaxVel):
        '''
        Sets jog parameters.

        Parameters
        ----------
        Mode : int
        StopMode : int
        StepSize : float
        MinVel : float
        Accn : float
        MaxVel : float
        '''
        self._jog_parameters = [Mode, StopMode, StepSize, MinVel, Accn, MaxVel]
