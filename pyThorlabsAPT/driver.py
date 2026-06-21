'''Note: most of docstrings in this file have been generated automatically by Claude. AI can make mistakes'''

"""
The class pyThorlabsAPT acts as a wrapper around a Thorlabs APT motor, exposing the methods needed to
find, connect to, and operate a device.

Pass virtual=True to __init__ to use the virtual (software-simulated) backend, defined in
pyThorlabsAPT.thorlabs_apt_virtual, instead of talking to real hardware via pyThorlabsAPT.thorlabs_apt.
Both backends expose the same Motor / list_available_devices() API, so the rest of this class does not
need to know which one it is talking to.
"""

class pyThorlabsAPT:

    def __init__(self, virtual=False):
        """
        Parameters
        ----------
        virtual : bool, optional
            If True, use the virtual backend (pyThorlabsAPT.thorlabs_apt_virtual) instead of real
            hardware. This allows the driver to run without any physical device, APT.dll, or serial
            connection, using two simulated motors. Default is False.
        """
        if virtual:
            import pyThorlabsAPT.thorlabs_apt_virtual as _apt
        else:
            import pyThorlabsAPT.thorlabs_apt as _apt
        self._apt = _apt
        self.connected = False
        #Ideally, we would initialize the library here by calling self._apt.list_available_devices().
        #However, the method list_devices (which might be called by the user later) needs to re-query
        #the backend in order to discover devices that were plugged in after this object was created.
        #To avoid slowing down the start-up time, we do not query the backend in the __init__ method,
        #but only in the list_devices method.
        #The drawback is that the user needs to call the method list_devices before connecting to a
        #device (even if the device address is already known)

    def list_devices(self):
        '''
        Look for any connected device

        Returns
        -------
        list_valid_devices, list
            A list of all found valid devices. Each element of the list is a list of two elements, in
            the format [identity,address]

        '''
        self.list_valid_devices = self._apt.list_available_devices()
        return self.list_valid_devices

    def connect_device(self,device_addr):
        '''
        Connect to the device identified by device_addr.

        Parameters
        ----------
        device_addr : str or int
            Address (serial number) of the device to connect to, as returned by list_devices.

        Returns
        -------
        (Msg,ID) : (str,int)
            Msg is device_addr on success, or an error message on failure. ID is 1 if connection was
            successful, 0 otherwise.

        Raises
        ------
        ValueError
            If device_addr does not correspond to any currently available device.
        '''
        device_addresses = [str(dev[1]) for dev in self.list_valid_devices]
        if (str(device_addr) in device_addresses):
            try:
                self.motor = self._apt.Motor(serial_number=int(device_addr))
                Msg = device_addr
                ID = 1
            except Exception as e:
                ID = 0
                Msg = str(e)
        else:
            raise ValueError("The specified address is not a valid device address.")
        if(ID==1):
            self.connected = True
        return (Msg,ID)

    def disconnect_device(self):
        '''
        Disconnect the currently connected device.

        Returns
        -------
        (Msg,ID) : (str,int)
            Msg is a confirmation message, or the exception raised while disconnecting. ID is 1 if
            disconnection was successful, 0 otherwise.

        Raises
        ------
        RuntimeError
            If no device is currently connected.
        '''
        if(self.connected == True):
            try:
                self.list_devices()
                ID = 1
                Msg = 'Successfully disconnected.'
            except Exception as e:
                ID = 0
                Msg = str(e)
            if(ID==1):
                self.connected = False
            return (Msg,ID)
        else:
            self.list_devices()
            raise RuntimeError("Device is already disconnected.")

    # --- The properties/methods below delegate to self.motor (the underlying apt.Motor instance,
    # real or virtual), which only exists once a device has been successfully connected (see
    # connect_device above).

    @property
    def position(self):
        return self.motor.position

    @position.setter
    def position(self, value):
        self.motor.position = value

    @property
    def is_in_motion(self):
        return self.motor.is_in_motion

    def move_jog(self, direction, blocking=False):
        self.motor.move_jog(direction, blocking)

    def move_home(self, blocking=False):
        self.motor.move_home(blocking)

    def stop_profiled(self):
        self.motor.stop_profiled()

    def get_stage_axis_info(self):
        return self.motor.get_stage_axis_info()

    def set_stage_axis_info(self, min_pos, max_pos, units, pitch):
        self.motor.set_stage_axis_info(min_pos, max_pos, units, pitch)

    def get_jog_parameters(self):
        return self.motor.get_jog_parameters()

    def set_jog_parameters(self, Mode, StopMode, StepSize, MinVel, Accn, MaxVel):
        self.motor.set_jog_parameters(Mode, StopMode, StepSize, MinVel, Accn, MaxVel)
