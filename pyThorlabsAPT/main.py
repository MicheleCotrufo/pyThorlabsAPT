import os
import PyQt5
dirname = os.path.dirname(PyQt5.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
import PyQt5.QtWidgets as Qt# QApplication, QWidget, QMainWindow, QPushButton, QHBoxLayout
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import logging
import sys
import argparse

import abstract_instrument_interface
import pyThorlabsAPT.driver_virtual
import pyThorlabsAPT.driver
import pyThorlabsAPT.thorlabs_apt as apt

graphics_dir = os.path.join(os.path.dirname(__file__), 'graphics')

##This application follows the model-view-controller paradigm, but with the view and controller defined inside the same object (the GUI)
##The model is defined by the class 'interface', and the view+controller is defined by the class 'gui'. 

class interface(abstract_instrument_interface.abstract_interface):
    """
    Create a high-level interface with the device, validates input data and perform high-level tasks such as periodically reading data from the instrument.
    It uses signals (i.e. QtCore.pyqtSignal objects) to notify whenever relevant data has changes or event has happened. These signals are typically received by the GUI
    Several general-purpose attributes and methods are defined in the class abstract_interface defined in abstract_instrument_interface
    ...

    Attributes specific for this class (see the abstract class abstract_instrument_interface.abstract_interface for general attributes)
    ----------
    instrument
        Instance of driver.pyThorlabsAPT
    connected_device_name : str
        Name of the physical device currently connected to this interface 
    settings = {    'step_size': 1,
                    'ramp' : {  
                                ....
                                }
                    }
    ramp 
        Instance of abstract_instrument_interface.ramp class 

    Methods defined in this class (see the abstract class abstract_instrument_interface.abstract_interface for general methods)
    -------
    refresh_list_devices()
        Get a list of compatible devices from the driver. Store them in self.list_devices, send signal to populate the combobox in the GUI.
    connect_device(device_full_name)
        Connect to the device identified by device_full_name
    disconnect_device()
        Disconnect the currently connected device
    close()
        Closes this interface, close plot window (if any was open), and calls the close() method of the parent class, which typically calls the disconnect_device method
   
    set_connected_state()
        This method also calls the set_connected_state() method defined in abstract_instrument_interface.abstract_interface

    TO FINISH

    """

    output = {'Position':0}  #We define this also as class variable, to make it possible to see which data is produced by this interface without having to create an object
    
    ## SIGNALS THAT WILL BE USED TO COMMUNICATE WITH THE GUI
    #                                                           | Triggered when ...                                        | Sends as parameter    
    #                                                       #   -----------------------------------------------------------------------------------------------------------------------         
    sig_list_devices_updated = QtCore.pyqtSignal(list)      #   | List of devices is updated                                | List of devices   
    sig_update_position = QtCore.pyqtSignal(object)         #   | Position has changed/been read                            | New position
    # REMOVED, now using jogging for steps # sig_step_size = QtCore.pyqtSignal(float)                #   | Step size has been changed or resetted                    | Step size
    sig_change_moving_status = QtCore.pyqtSignal(int)       #   | A movement has started or has ended                       | 1 = movement has started,  2 = movement has ended
    sig_change_homing_status = QtCore.pyqtSignal(int)       #   | Homing has started or has ended                           | 1 = homing has started,  2 = homing has ended
    sig_stage_info = QtCore.pyqtSignal(list)                #   | Stage parameters have been written/read                   | List containing the stage parameters
    sig_jog_step_size = QtCore.pyqtSignal(float)            #   | Jog step size has been changed or resetted                | Jog Step size
    sig_jog_max_vel = QtCore.pyqtSignal(float)              #   | Jog max vel has been changed or resetted                  | Jog Max Vel
    sig_jog_accel = QtCore.pyqtSignal(float)                #   | Jog acceleration has been changed or resetted             | Jog Acceleration
    sig_jog_mode = QtCore.pyqtSignal(int)                   #   | Jog mode has been changed or resetted                     | Jog Mode
    sig_jog_stop_mode = QtCore.pyqtSignal(int)              #   | Jog stop mode has been changed or resetted                | Jog Stod Mode
    
    
    ##
    # Identifier codes used for view-model communication. Other general-purpose codes are specified in abstract_instrument_interface
    SIG_MOVEMENT_STARTED = 1
    SIG_MOVEMENT_ENDED = 2
    SIG_HOMING_STARTED = 1
    SIG_HOMING_ENDED = 2

    def __init__(self, **kwargs):
        """Initialize the class instance.

        Args: (Other Args are specified in the __init__ method of abstract_instrument_interface.abstract_interface)
            no_ramp (bool, optional): If set true, the ramp is not generated for this interface

        """
        self.output = {'Position':0} 
        ### Default values of settings (might be overlapped by settings saved in .json files later)
        self.settings = {   
                            # REMOVED, now using jogging for steps # 'step_size' : 1,
                            'ramp' : {  
                                        'ramp_step_size': 1,            #Increment value of each ramp step
                                        'ramp_wait_1': 1,               #Wait time (in s) after each ramp step
                                        'ramp_send_trigger' : True,     #If true, the function self.func_trigger is called after each 'movement'
                                        'ramp_wait_2': 1,               #Wait time (in s) after each (potential) call to trigger, before doing the new ramp step
                                        'ramp_numb_steps': 10,          #Number of steps in the ramp
                                        'ramp_repeat': 1,               #How many times the ramp is repeated
                                        'ramp_reverse': 1,              #If True (or 1), it repeates the ramp in reverse
                                        'ramp_send_initial_trigger': 1, #If True (or 1), it calls self.func_trigger before starting the ramp
                                        'ramp_reset' : 1                #If True (or 1), it resets the value of the instrument to the initial one after the ramp is done
                                        }
                            }
        self.list_devices = []              #list of devices found 
        self.connected_device_name = ''
        self._units = {'mm':1,'deg':2}
        
        self._jog_directions = {1: apt.MOVE_FWD,-1: apt.MOVE_REV}
        self._jog_directions_string = {1: 'forward',-1: 'backward'}
        ###
        if ('virtual' in kwargs.keys()) and (kwargs['virtual'] == True):
            self.instrument =  pyThorlabsAPT.driver_virtual. pyThorlabsAPT() 
        else:    
            self.instrument =  pyThorlabsAPT.driver. pyThorlabsAPT() 
        ###
        super().__init__(**kwargs)

        self._add_ramp = not kwargs.get('no_ramp')

        if self._add_ramp:
            # Setting up the ramp object, which is defined in the package abstract_instrument_interface
            self.ramp = abstract_instrument_interface.ramp(interface=self)  
            self.ramp.set_ramp_settings(self.settings['ramp'])
            self.ramp.set_ramp_functions(func_move = self.jog_by,
                                        func_check_step_has_ended = self.is_device_not_moving, 
                                        func_trigger = self.update, 
                                        func_trigger_continue_ramp = None,
                                        func_set_value = self.set_position, 
                                        func_read_current_value = self.read_position, 
                                        list_functions_step_not_ended = [self.read_position],  
                                        list_functions_step_has_ended = [lambda:self.end_movement(send_signal=False)],  
                                        list_functions_ramp_ended = [])
            self.ramp.sig_ramp.connect(self.on_ramp_state_changed)
        
        #self.refresh_list_devices()

    def refresh_list_devices(self):
        '''
        Get a list of all devices connected, by using the method list_devices() of the driver. For each device obtain its identity and its address.
        '''            
        self.logger.info(f"Looking for devices...") 
        list_valid_devices = self.instrument.list_devices()
        self.logger.info(f"Found {len(list_valid_devices)} devices.") 
        self.list_devices = list_valid_devices
        self.send_list_devices()

    def send_list_devices(self):
        if(len(self.list_devices)>0):
            list_IDNs_and_devices = [str(dev[1]) + " --> " + str(dev[0]) for dev in self.list_devices] 
        else:
            list_IDNs_and_devices =[]
        self.list_IDNs_and_devices = list_IDNs_and_devices
        self.sig_list_devices_updated.emit(list_IDNs_and_devices)

    def connect_device(self,device_full_name):
        if(device_full_name==''): # Check  that the name is not empty
            self.logger.error("No valid device has been selected")
            return
        self.set_connecting_state()
        device_name = device_full_name.split(' --> ')[0].lstrip() # We extract the device address from the device name
        self.logger.info(f"Connecting to device {device_name}...")
        try:
            (Msg,ID) = self.instrument.connect_device(device_name) # Try to connect by using the method ConnectDevice of the powermeter object
            if(ID==1):  #If connection was successful
                self.logger.info(f"Connected to device {device_name}.")
                self.connected_device_name = device_name
                if not 'jog_step_size' in list(self.settings.keys()): #if the config file that was loaded at startup does not have stored settings for the jog, we load them from the instrument. Otherwise, we use the ones currently stored in self.settings
                    self.logger.info(f"Reading jog parameters from device.")
                    self.get_jog_params()
                else:
                    self.logger.info(f"Using jog parameters previously stored in the config file.")
                    self.set_jog_params() #This makes sure that the jog parameters currently store in self.settings are "applied" to the device.
                self.set_connected_state()
            else: #If connection was not successful
                self.logger.error(f"Error: {Msg}")
                self.set_disconnected_state()
                pass
        except Exception as e:
            self.logger.error(f"Error: {e}")
            self.set_disconnected_state()

    def disconnect_device(self):
        self.logger.info(f"Disconnecting from device {self.connected_device_name}...")
        self.set_disconnecting_state()
        (Msg,ID) = self.instrument.disconnect_device()
        if(ID==1): # If disconnection was successful
            self.logger.info(f"Disconnected from device {self.connected_device_name}.")
            #self.continuous_read = 0 # We set this variable to 0 so that the continuous reading from the powermeter will stop
            self.set_disconnected_state()
        else: #If disconnection was not successful
            self.logger.error(f"Error: {Msg}")
            self.set_disconnected_state() #When disconnection is not succeful, it is typically because the device alredy lost connection
                                          #for some reason. In this case, it is still useful to have the widget reset to disconnected state                                       
    def close(self,**kwargs):
        if self._add_ramp:
            self.settings['ramp'] = self.ramp.settings
        super().close(**kwargs)     
        
    def set_connected_state(self):
        super().set_connected_state()
        self.read_position()
        self.read_stage_info()         
        
    def set_moving_state(self):
        self.sig_change_moving_status.emit(self.SIG_MOVEMENT_STARTED)
                             
    def set_non_moving_state(self): 
        self.sig_change_moving_status.emit(self.SIG_MOVEMENT_ENDED)

    def is_device_moving(self):
        return self.instrument.is_in_motion

    def is_device_not_moving(self):
        return not(self.instrument.is_in_motion)

    def stop_any_movement(self):
        if self.is_device_not_moving():
            self.logger.error(f"Motors cannot be stopped because they are not moving.")
        else:
            try:
                self.instrument.stop_profiled()
                self.logger.info(f"Movement was stopped by user.")
            except Exception as e:
                self.logger.error(f"Some error occured while trying to stop the motor: {e}")
                        
    def on_ramp_state_changed(self,status):
        '''
        Slot for signals coming from the ramp object
        '''
        if status == self.ramp.SIG_RAMP_STARTED:
            self.set_moving_state()
            self.settings['ramp'] = self.ramp.settings
        if status == self.ramp.SIG_RAMP_ENDED:
            self.set_non_moving_state()
    
    # REMOVED, now using jogging for steps #
    # def set_step_size(self, s):
        # try: 
            # step_size = float(s)
            # if self.settings['step_size'] == step_size: #if the value passed is the same as the one currently stored, we end here
                # return True
        # except ValueError:
            # self.logger.error(f"The step size must be a valid float number.")
            # self.sig_step_size.emit(self.settings['step_size'])
            # return False
        # self.logger.info(f"The step size is now {step_size}.")
        # self.settings['step_size'] = step_size
        # self.sig_step_size.emit(self.settings['step_size'])
        # return True
        
    def set_jog_step_size(self,s):
        try: 
            step_size = float(s)
            if self.settings['jog_step_size'] == step_size: #if the value passed is the same as the one currently stored, we end here
                return True
        except ValueError:
            self.logger.error(f"The jog step size must be a valid float number.")
            self.sig_jog_step_size.emit(self.settings['jog_step_size'])
            return False
        self.logger.info(f"Changing jog step size to {step_size}...")
        try:
            self.settings['jog_step_size'] = step_size
            self.set_jog_params()
            self.sig_jog_step_size.emit(self.settings['jog_step_size'])
            self.logger.info(f"Done.")
            return True
        except Exception as e:
            self.logger.error(f"Some error occured while trying to change the jog step size: {e}")
            return False    
        
    def set_jog_max_vel(self,mv):
        try: 
            max_vel = float(mv)
            if self.settings['jog_max_vel'] == max_vel: #if the value passed is the same as the one currently stored, we end here
                return True
        except ValueError:
            self.logger.error(f"The jog max velocity must be a valid float number.")
            self.sig_jog_max_vel.emit(self.settings['jog_max_vel'])
            return False
        if max_vel <=0:
            self.logger.error(f"The jog max velocity must be positive.")
            self.sig_jog_max_vel.emit(self.settings['jog_max_vel'])
            return False
            
        self.logger.info(f"Changing jog max velocity to {max_vel}...")
        
        try:
            self.settings['jog_max_vel'] = max_vel
            self.set_jog_params()
            self.sig_jog_max_vel.emit(self.settings['jog_max_vel'])
            self.logger.info(f"Done.")
            return True
        except Exception as e:
            self.logger.error(f"Some error occured while trying to change the jog max velocity: {e}")
            return False
            
    def set_jog_accel(self,ac):
        try: 
            max_acc = float(ac)
            if self.settings['jog_acceleration'] == max_acc: #if the value passed is the same as the one currently stored, we end here
                return True
        except ValueError:
            self.logger.error(f"The jog max acceleration must be a valid float number.")
            self.sig_jog_accel.emit(self.settings['jog_acceleration'])
            return False
        if max_acc <=0:
            self.logger.error(f"The jog max acceleration must be positive.")
            self.sig_jog_accel.emit(self.settings['jog_acceleration'])
            return False
            
        self.logger.info(f"Changing jog max acceleration to {max_acc}...")
        
        try:
            self.settings['jog_acceleration'] = max_acc
            self.set_jog_params()
            self.sig_jog_accel.emit(self.settings['jog_acceleration'])
            self.logger.info(f"Done.")
            return True
        except Exception as e:
            self.logger.error(f"Some error occured while trying to change the jog max acceleration: {e}")
            return False
            
    def set_jog_mode(self,mode):
        try: 
            mode = int(mode)
            if self.settings['jog_mode'] == mode: #if the value passed is the same as the one currently stored, we end here
                return True
        except ValueError:
            self.logger.error(f"The jog mode must be a valid integer number.")
            self.sig_jog_mode.emit(self.settings['jog_mode'])
            return False
        if not mode in [1,2]:
            self.logger.error(f"The jog mode must either 1 or 2.")
            self.sig_jog_mode.emit(self.settings['jog_mode'])
            return False
            
        self.logger.info(f"Changing jog mode to {mode}...")
        
        try:
            self.settings['jog_mode'] = mode
            self.set_jog_params()
            self.sig_jog_mode.emit(self.settings['jog_mode'])
            self.logger.info(f"Done.")
            return True
        except Exception as e:
            self.logger.error(f"Some error occured while trying to change the jog mode: {e}")
            return False
            
    def set_jog_stop_mode(self,mode):
        try: 
            mode = int(mode)
            if self.settings['jog_stop_mode'] == mode: #if the value passed is the same as the one currently stored, we end here
                return True
        except ValueError:
            self.logger.error(f"The jog stop mode must be a valid integer number.")
            self.sig_jog_stop_mode.emit(self.settings['jog_stop_mode'])
            return False
        if not mode in [1,2]:
            self.logger.error(f"The jog stop mode must either 1 or 2.")
            self.sig_jog_stop_mode.emit(self.settings['jog_stop_mode'])
            return False
            
        self.logger.info(f"Changing jog stop mode to {mode}...")
        
        try:
            self.settings['jog_stop_mode'] = mode
            self.set_jog_params()
            self.sig_jog_stop_mode.emit(self.settings['jog_stop_mode'])
            self.logger.info(f"Done.")
            return True
        except Exception as e:
            self.logger.error(f"Some error occured while trying to change the jog stop mode: {e}")
            return False
        
    def get_jog_params(self):
        Mode, StopMode, StepSize, MinVel, Accn, MaxVel =self.instrument.get_jog_parameters()
        self.settings['jog_mode'] = Mode
        self.settings['jog_stop_mode'] = StopMode
        self.settings['jog_step_size'] = StepSize
        self.settings['jog_min_vel'] = MinVel
        self.settings['jog_acceleration'] = Accn
        self.settings['jog_max_vel'] = MaxVel
        return True
        
    def set_jog_params(self):
        self.instrument.set_jog_parameters(self.settings['jog_mode'], self.settings['jog_stop_mode'], self.settings['jog_step_size'], self.settings['jog_min_vel'], self.settings['jog_acceleration'], self.settings['jog_max_vel'])
        return True
    
    def home(self):
        if self.is_device_moving():
            self.logger.error(f"Cannot start homing while device is moving.")
            return
        self.logger.info(f"Homing device...")
        self.set_moving_state()
        self.sig_change_homing_status.emit(self.SIG_HOMING_STARTED)
        self.instrument.move_home()
        #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
        #position and update it in the GUI. When it becomes False, call self.end_movement
        self.check_property_until(lambda : self.instrument.is_in_motion,[True,False],
                                  [
                                      [self.read_position],
                                      [self.end_movement,
                                       lambda x=None:self.sig_change_homing_status.emit(self.SIG_HOMING_ENDED)
                                      ]
                                   ])

    def jog(self,direction):
        if self.is_device_moving():
            self.logger.error(f"Cannot jog while device is already moving.")
            return
        if not direction in list(self._jog_directions.keys()):
            self.logger.error(f"Value of direction is not valid.")
            return
        self.logger.info(f"Jogging {self._jog_directions_string[direction]}. Begin moving...")
        self.set_moving_state()
        self.instrument.move_jog(self._jog_directions[direction]) 
        #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
        #position. When it becomes False, call self.end_movement
        self.check_property_until(lambda : self.instrument.is_in_motion,[True,False],[[self.read_position],[self.end_movement]])
        
    def jog_by(self,step):
        direction = +1 if step > 0 else -1
        if not(step == self.settings['jog_step_size']):
            self.set_jog_step_size(step)
        self.jog(direction)

    # REMOVED, now using jogging for steps #
    # def move_single_step(self,direction,step_size = None):
        # if self.is_device_moving():
            # self.logger.error(f"Cannot start moving while device is already moving.")
            # return
        # if step_size == None:
            # step_size = self.settings['step_size']
        # movement = direction*step_size
        # self.logger.info(f"Will move by {movement}. Begin moving...")
        # self.set_moving_state()
        # self.instrument.move_by(movement)
        # #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
        # #position. When it becomes False, call self.end_movement
        # self.check_property_until(lambda : self.instrument.is_in_motion,[True,False],[[self.read_position],[self.end_movement]])
        
    def end_movement(self,send_signal = True):
        # When send_signal = False, the method self.set_non_moving_state() is NOT called, which means the signal self.sig_change_moving_status.emit(self.SIG_MOVEMENT_ENDED) is not emitted
        # This is useful, e.g., when doing a ramp, when at each step of the ramp we want to read the position but we do not want to send the signal that the movement has ended, so that the GUI remains disabled
        self.read_position()
        self.logger.info(f"Movement ended. New position = {self.output['Position']}")
        if send_signal:
            self.set_non_moving_state()

    def read_stage_info(self):
        #    # Stage units
        #    STAGE_UNITS_MM = 1
        #    """Stage units in mm"""
        #    STAGE_UNITS_DEG = 2
        #    """Stage units in degrees"""
        temp = list(self.instrument.get_stage_axis_info())
        temp[2] = list(self._units.keys())[list(self._units.values()).index(temp[2])]
        self.stage_info = temp
        self.sig_stage_info.emit(self.stage_info)
        self.logger.info(f"Current stage parameters: {self.stage_info}")
        return self.stage_info

    def set_stage_info(self, min_pos, max_pos, units, pitch):
        #units must be specified as a string, and it gets converted according to self._units = {'mm':1,'deg':2}
        try: 
            min_pos = float(min_pos)
            max_pos = float(max_pos)
            pitch = float(pitch)
        except ValueError:
            self.logger.error(f"min_pos, max_pos, and pitch must be valid numbers.")
            return False
        if not units in self._units.keys():
            self.logger.error(f"Value of units is not valid.")
            return False
        try:
            self.instrument.set_stage_axis_info(min_pos,max_pos, self._units[units], pitch)
        except:
            self.logger.error(f"Some error occurred when setting stage parameters.")
            return False
        self.logger.info(f"Stage parameters set correctly.")
        self.read_stage_info()

    def read_position(self):
        self.output['Position'] = self.instrument.position
        self.sig_update_position.emit(self.output['Position'])
        return self.output['Position']
        
    def set_position(self,position):
        if self.is_device_moving():
            self.logger.error(f"Cannot start moving while device is already moving.")
            return
        try:
            position = float(position)
        except:
            return
        self.logger.info(f"Moving to {position}...")
        self.instrument.position = position
        self.set_moving_state()
        #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
        #position and update it in the GUI. When it becomes False, call self.end_movement
        self.check_property_until(lambda : self.instrument.is_in_motion,[True,False],[[self.read_position],[self.end_movement]])

class gui(abstract_instrument_interface.abstract_gui):
    """
    Attributes specific for this class (see the abstract class abstract_instrument_interface.abstract_gui for general attributes)
    ----------
    """
    def __init__(self,interface,parent):
        super().__init__(interface,parent)
        self.initialize()
       
    def initialize(self):
        self.create_widgets()
        self.connect_widgets_events_to_functions()
        
        ### Call the initialize method of the super class. 
        super().initialize()
        
        ### Connect signals from model to event slots of this GUI
        self.interface.sig_list_devices_updated.connect(self.on_list_devices_updated)
        self.interface.sig_connected.connect(self.on_connection_status_change) 
        self.interface.sig_update_position.connect(self.on_position_change)
        
        # REMOVED, now using jogging for steps #
        # self.interface.sig_step_size.connect(self.on_step_size_change)
        
        self.interface.sig_jog_step_size.connect(self.on_jog_step_size_change)
        self.interface.sig_jog_max_vel.connect(self.on_jog_max_vel_change)
        self.interface.sig_jog_accel.connect(self.on_jog_accel_change)
        self.interface.sig_jog_mode.connect(self.on_jog_mode_change)
        self.interface.sig_jog_stop_mode.connect(self.on_jog_stop_mode_change)
        
        self.interface.sig_change_moving_status.connect(self.on_moving_state_change)
        self.interface.sig_change_homing_status.connect(self.on_homing_state_change)
        self.interface.sig_stage_info.connect(self.on_stage_info_change)
        #self.interface.ramp.sig_ramp.connect(self.on_ramp_state_change)
        self.interface.sig_close.connect(self.on_close)
        
        ### SET INITIAL STATE OF WIDGETS
        self.interface.send_list_devices() 
        self.on_moving_state_change(self.interface.SIG_MOVEMENT_ENDED)
        self.on_homing_state_change(self.interface.SIG_HOMING_ENDED)
        self.on_connection_status_change(self.interface.SIG_DISCONNECTED) #When GUI is created, all widgets are set to the "Disconnected" state              
        
    def create_widgets(self):
        """
        Creates all widgets and layout for the GUI. Any Widget and Layout must assigned to self.containter, which is a pyqt Layout object
        """ 
       
        #Use the custom connection/listdevices panel, defined in abstract_instrument_interface.abstract_gui
        hbox1, widgets_dict = self.create_panel_connection_listdevices()
        for key, val in widgets_dict.items(): 
            setattr(self,key,val) 

        hbox2 = Qt.QHBoxLayout()
        self.label_Position = Qt.QLabel("Position: ")
        self.edit_Position = Qt.QLineEdit(self.parent)
        self.edit_Position.setAlignment(QtCore.Qt.AlignRight)
        #self.label_PositionUnits = Qt.QLabel(" deg")
        
        # REMOVED, now using jogging for steps #
        # self.label_Move = Qt.QLabel("Move: ")
        # self.button_MoveNegative = Qt.QPushButton("<")
        # self.button_MoveNegative.setToolTip('')
        # self.button_MoveNegative.setMaximumWidth(30)
        # self.button_MovePositive = Qt.QPushButton(">")
        # self.button_MovePositive.setToolTip('')
        # self.button_MovePositive.setMaximumWidth(30)
        # self.label_By  = Qt.QLabel("By ")
        # self.edit_StepSize = Qt.QLineEdit()
        # self.edit_StepSize.setToolTip('')
        
        self.button_Home = Qt.QPushButton("Home")
        self.button_Stop = Qt.QPushButton("Stop any movement")
        widgets_row2 = [self.label_Position,self.edit_Position,
                        # self.label_Move,self.button_MoveNegative,self.button_MovePositive,self.label_By,self.edit_StepSize, # REMOVED, now using jogging for steps #
                        self.button_Home,self.button_Stop]
        widgets_row2_stretches = [0]*len(widgets_row2)
        for w,s in zip(widgets_row2,widgets_row2_stretches):
            hbox2.addWidget(w,stretch=s)
        hbox2.addStretch(1)

        hbox3 = Qt.QHBoxLayout()
        self.label_Jog = Qt.QLabel("Jog: ")
        self.button_JogNegative = Qt.QPushButton("<")
        self.button_JogNegative.setToolTip('')
        self.button_JogNegative.setMaximumWidth(30)
        self.button_JogPositive = Qt.QPushButton(">")
        self.button_JogPositive.setToolTip('')
        self.button_JogPositive.setMaximumWidth(30)
        self.label_JogBy  = Qt.QLabel("By ")
        self.edit_JogStepSize = Qt.QLineEdit()
        self.edit_JogStepSize.setToolTip('Units are typically mm or deg. Check the specs of your APT controller/motor')
        self.label_JogMaxVel  = Qt.QLabel("Max Vel.:")
        self.edit_JogMaxVel = Qt.QLineEdit()
        self.edit_JogMaxVel.setToolTip('Units are typically mm/s or deg/s. Check the specs of your APT controller/motor')
        self.label_JogAcc  = Qt.QLabel("Max Accel.:")
        self.edit_JogAcc = Qt.QLineEdit()
        self.edit_JogAcc.setToolTip('Units are typically mm/s^2 or deg/s^2. Check the specs of your APT controller/motor')
        self.label_JogMode  = Qt.QLabel("Jog Mode:")
        self.edit_JogMode = Qt.QLineEdit()
        self.edit_JogMode.setToolTip('Leave this unchanged unless you know what you are doing.')
        self.edit_JogMode.setFixedWidth(20)
        self.label_JogStopMode  = Qt.QLabel("Jog Stop Mode:")
        self.edit_JogStopMode = Qt.QLineEdit()
        self.edit_JogStopMode.setToolTip('Leave this unchanged unless you know what you are doing.')
        self.edit_JogStopMode.setFixedWidth(20)
        widgets_row3 = [self.label_Jog,self.button_JogNegative,self.button_JogPositive,self.label_JogBy,self.edit_JogStepSize,
                            self.label_JogMaxVel, self.edit_JogMaxVel, self.label_JogAcc, self.edit_JogAcc,
                            self.label_JogMode,self.edit_JogMode, self.label_JogStopMode,self.edit_JogStopMode]
        widgets_row3_stretches = [0]*len(widgets_row3)
        for w,s in zip(widgets_row3,widgets_row3_stretches):
            hbox3.addWidget(w,stretch=s)
        hbox3.addStretch(1)

        #min_pos, max_pos, units, pitch
        stageparams_groupbox = Qt.QGroupBox()
        stageparams_groupbox.setTitle(f"Stage Parameters [ONLY CHANGE THESE IF YOU KNOW WHAT YOU ARE DOING]")
        stageparams_hbox = Qt.QHBoxLayout()
        self.label_min_pos = Qt.QLabel("Min Pos: ")
        self.edit_min_pos = Qt.QLineEdit()
        self.label_max_pos = Qt.QLabel("Max Pos: ")
        self.edit_max_pos = Qt.QLineEdit()
        self.label_units = Qt.QLabel("Units: ")
        self.combo_units = Qt.QComboBox()
        self.combo_units.addItems(self.interface._units.keys())
        self.label_pitch = Qt.QLabel("Pitch: ")
        self.edit_pitch = Qt.QLineEdit()
        self.button_set_stageparams = Qt.QPushButton("Set")
        tooltip = 'The correct values of these parameters depend on the particular motor, and changing them will affect the motor behaviour. \nDo not change them unless you know what you are doing.'
        self.button_set_stageparams.setToolTip(tooltip)
        stageparams_groupbox.setToolTip(tooltip)
        widgets_row4_stageparams = [self.label_min_pos,self.edit_min_pos,self.label_max_pos,self.edit_max_pos,self.label_units,self.combo_units,self.label_pitch,self.edit_pitch,self.button_set_stageparams]
        widgets_row4_stageparams_stretches = [0]*len(widgets_row4_stageparams)
        for w,s in zip(widgets_row4_stageparams,widgets_row4_stageparams_stretches):
             stageparams_hbox.addWidget(w,stretch=s)
        stageparams_hbox.addStretch(1)    
        stageparams_groupbox.setLayout(stageparams_hbox) 
        
        if hasattr(self.interface, 'ramp'):
            self.ramp_groupbox = abstract_instrument_interface.ramp_gui(ramp_object=self.interface.ramp)     
        
        self.tabs = Qt.QTabWidget()
        self.tab1 = Qt.QWidget()
        self.container_tab1 = Qt.QVBoxLayout()
        self.tab2 = Qt.QWidget()
        self.container_tab2 = Qt.QVBoxLayout()
        self.tabs.addTab(self.tab1,"General")
        self.tabs.addTab(self.tab2,"Stage settings") 
        
        for box in [hbox1,hbox2,hbox3]:
            self.container_tab1.addLayout(box)  
        if hasattr(self.interface, 'ramp'):    
            self.container_tab1.addWidget(self.ramp_groupbox)
        self.container_tab1.addStretch(1)
        
        self.container_tab2.addWidget(stageparams_groupbox)
        self.container_tab2.addStretch(1)
        
        self.tab1.setLayout(self.container_tab1)
        self.tab2.setLayout(self.container_tab2)
        
        self.container = Qt.QVBoxLayout()
        self.container.addWidget(self.tabs)
        
        # Widgets for which we want to constraint the width by using sizeHint()
        widget_list = [self.label_Position, self.label_Jog, self.label_JogBy, self.button_Home,stageparams_groupbox, self.button_Stop]
        for w in widget_list:
            w.setMaximumSize(w.sizeHint())
        
        self.widgets_disabled_when_doing_ramp = [self.button_ConnectDevice,self.combo_Devices,
                                                #self.label_Position,self.edit_Position,self.button_Home, self.label_Move,self.button_MoveNegative,self.button_MovePositive,self.label_By,self.edit_StepSize, # REMOVED, now using jogging for steps #
                                                 self.button_Home,self.button_set_stageparams
                                               ] + widgets_row3 + widgets_row4_stageparams
        #These widgets are enabled ONLY when interface is connected to a device
        self.widgets_enabled_when_connected = [self.combo_Devices , self.button_RefreshDeviceList,
                                               #self.label_Position, self.edit_Position,self.button_Home,self.button_Stop,self.label_Move,self.button_MoveNegative,self.button_MovePositive,self.label_By,self.edit_StepSize, # REMOVED, now using jogging for steps #
                                               self.button_Home,self.button_set_stageparams,
                                               ] + widgets_row3 + widgets_row4_stageparams

        #These widgets are enabled ONLY when interface is NOT connected to a device   
        self.widgets_enabled_when_disconnected = [self.combo_Devices,  self.button_RefreshDeviceList]

        self.widgets_disabled_when_moving = widgets_row4_stageparams + [self.button_ConnectDevice,
                                                                        #self.edit_StepSize,self.edit_Position,self.button_MoveNegative ,self.button_MovePositive, # REMOVED, now using jogging for steps #
                                                                        self.button_set_stageparams,self.button_Home] + widgets_row3

    def connect_widgets_events_to_functions(self):
        self.button_RefreshDeviceList.clicked.connect(self.click_button_refresh_list_devices)
        self.button_ConnectDevice.clicked.connect(self.click_button_connect_disconnect)
        self.edit_Position.returnPressed.connect(self.press_enter_edit_Position)
        #self.button_MoveNegative.clicked.connect(lambda x:self.click_button_Move(-1)) # REMOVED, now using jogging for steps #
        #self.button_MovePositive.clicked.connect(lambda x:self.click_button_Move(+1)) # REMOVED, now using jogging for steps #
        self.button_Home.clicked.connect(self.click_button_Home)
        self.button_Stop.clicked.connect(self.click_button_Stop)
        #self.edit_StepSize.returnPressed.connect(self.press_enter_edit_StepSize) # REMOVED, now using jogging for steps #
        
        self.button_JogNegative.clicked.connect(lambda x:self.click_button_Jog(-1))
        self.button_JogPositive.clicked.connect(lambda x:self.click_button_Jog(+1))
        self.edit_JogStepSize.returnPressed.connect(self.press_enter_edit_JogStepSize)
        self.edit_JogMaxVel.returnPressed.connect(self.press_enter_edit_JogMaxVel)
        self.edit_JogAcc.returnPressed.connect(self.press_enter_edit_JogAcc)
        self.edit_JogMode.returnPressed.connect(self.press_enter_edit_JogMode)
        self.edit_JogStopMode.returnPressed.connect(self.press_enter_edit_JogStopMode)
        
        self.button_set_stageparams.clicked.connect(self.click_button_set_stageparams)
        
        
###########################################################################################################
### Event Slots. They are normally triggered by signals from the model, and change the GUI accordingly  ###
###########################################################################################################

    def on_connection_status_change(self,status):
        if status == self.interface.SIG_DISCONNECTED:
            self.disable_widget(self.widgets_enabled_when_connected)
            self.enable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Connect")
        if status == self.interface.SIG_DISCONNECTING:
            self.disable_widget(self.widgets_enabled_when_connected)
            self.enable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Disconnecting...")
        if status == self.interface.SIG_CONNECTING:
            self.disable_widget(self.widgets_enabled_when_connected)
            self.enable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Connecting...")
        if status == self.interface.SIG_CONNECTED:
            self.enable_widget(self.widgets_enabled_when_connected)
            self.disable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Disconnect")
            
            self.edit_JogStepSize.setText(str(self.interface.settings['jog_step_size']))
            self.edit_JogMaxVel.setText(str(self.interface.settings['jog_max_vel']))
            self.edit_JogAcc.setText(str(self.interface.settings['jog_acceleration']))
            self.edit_JogMode.setText(str(self.interface.settings['jog_mode']))
            self.edit_JogStopMode.setText(str(self.interface.settings['jog_stop_mode']))
            
    def on_list_devices_updated(self,list_devices):
        self.combo_Devices.clear()  #First we empty the combobox  
        self.combo_Devices.addItems(list_devices) 

    def on_position_change(self,position):
        self.edit_Position.setText(str(position))
            
    def on_moving_state_change(self,status):
        if status == self.interface.SIG_MOVEMENT_STARTED:
            self.disable_widget(self.widgets_disabled_when_moving)
        if (status == self.interface.SIG_MOVEMENT_ENDED):
            if hasattr(self.interface, 'ramp'):
                if self.interface.ramp.is_not_doing_ramp(): 
                    self.enable_widget(self.widgets_disabled_when_moving)
            else:
                self.enable_widget(self.widgets_disabled_when_moving)

    def on_homing_state_change(self,status):
        self.on_moving_state_change(status)
 
    def on_jog_step_size_change(self,value):
        self.edit_JogStepSize.setText(str(value))
        
    def on_jog_max_vel_change(self,value):
        self.edit_JogMaxVel.setText(str(value))
        
    def on_jog_accel_change(self,value):
        self.edit_JogAcc.setText(str(value))
        
    def on_jog_mode_change(self,value):
        self.edit_JogMode.setText(str(value))
        
    def on_jog_stop_mode_change(self,value):
        self.edit_JogStopMode.setText(str(value))
 
    #def on_step_size_change(self,value): # REMOVED, now using jogging for steps #
    #    pass #self.edit_StepSize.setText(str(value)) 
        
    def on_stage_info_change(self,value):
        self.edit_min_pos.setText(str(value[0])) 
        self.edit_max_pos.setText(str(value[1])) 
        self.edit_pitch.setText(str(value[3])) 
        self.edit_pitch.setCursorPosition(0)
        self.combo_units.setCurrentText(value[2])
    def on_close(self):
        pass
        
#######################
### END Event Slots ###
#######################

###################################################################################################################################################
### GUI Events Functions. They are triggered by direct interaction with the GUI, and they call methods of the interface (i.e. the model) object.###
###################################################################################################################################################

    def click_button_refresh_list_devices(self):
        self.interface.refresh_list_devices()

    def click_button_connect_disconnect(self):
        if(self.interface.instrument.connected == False): # We attempt connection   
            device_full_name = self.combo_Devices.currentText() # Get the device name from the combobox
            self.interface.connect_device(device_full_name)
        elif(self.interface.instrument.connected == True): # We attempt disconnection
            self.interface.disconnect_device()
            
    def press_enter_edit_Position(self):
        return self.interface.set_position(self.edit_Position.text())
    
    #def press_enter_edit_StepSize(self): # REMOVED, now using jogging for steps #
    #    pass
        #return self.interface.set_jog_step_size(self.edit_StepSize.text())
        
    def press_enter_edit_JogStepSize(self):
        return self.interface.set_jog_step_size(self.edit_JogStepSize.text())
    
    def press_enter_edit_JogMaxVel(self):
        return self.interface.set_jog_max_vel(self.edit_JogMaxVel.text())
        
    def press_enter_edit_JogAcc(self):
        return self.interface.set_jog_accel(self.edit_JogAcc.text())
        
    def press_enter_edit_JogMode(self):
        return self.interface.set_jog_mode(self.edit_JogMode.text())
        
    def press_enter_edit_JogStopMode(self):
        return self.interface.set_jog_stop_mode(self.edit_JogStopMode.text())
    
    #def click_button_Move(self,direction): # REMOVED, now using jogging for steps #
    #    pass
        #self.press_enter_edit_StepSize()
        #self.interface.jog(direction)
        #self.interface.move_single_step(direction)
        
    def click_button_Jog(self,direction):
        self.press_enter_edit_JogStepSize()
        self.interface.jog(direction)
        
    def click_button_Home(self):
        self.interface.home()

    def click_button_Stop(self):
        self.interface.stop_any_movement()

    def click_button_set_stageparams(self):
            self.interface.set_stage_info( min_pos =   self.edit_min_pos.text(),
                                            max_pos =   self.edit_max_pos.text(),
                                            units =     self.combo_units.currentText(),
                                            pitch =     self.edit_pitch.text(),
                                            )
#################################
### END GUI Events Functions ####
#################################

class MainWindow(Qt.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(__package__)
        # Set the central widget of the Window.
        # self.setCentralWidget(self.container)
#    def closeEvent(self, event):
#        #if self.child:
#        pass#self.child.close()

def main():
    parser = argparse.ArgumentParser(description = "",epilog = "")
    parser.add_argument("-s", "--decrease_verbose", help="Decrease verbosity.", action="store_true")
    parser.add_argument('-virtual', help=f"Initialize the virtual driver", action="store_true")
    args = parser.parse_args()
    virtual = args.virtual
    
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    Interface = interface(app=app,virtual=virtual) 
    Interface.verbose = not(args.decrease_verbose)
    app.aboutToQuit.connect(Interface.close) 
    view = gui(interface = Interface, parent=window) #In this case window is the parent of the gui
    
    window.show()
    app.exec()# Start the event loop.

if __name__ == '__main__':
    main()
