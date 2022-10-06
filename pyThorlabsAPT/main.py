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
from pyThorlabsAPT.driver import pyThorlabsAPT

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
                                'ramp_step_size': 1,
                                'ramp_wait_1': 1,
                                'ramp_wait_2': 1,
                                'ramp_numb_steps': 10,
                                'ramp_repeat': 1,
                                'ramp_reverse': 1,
                                'ramp_send_initial_trigger': 1
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
    sig_step_size = QtCore.pyqtSignal(float)                #   | Step size has been changed or resetted                    | Step size
    sig_change_moving_status = QtCore.pyqtSignal(int)       #   | A movement has started or has ended                       | 1 = movement has started,  2 = movement has ended
    sig_change_homing_status = QtCore.pyqtSignal(int)       #   | Homing has started or has ended                           | 1 = homing has started,  2 = homing has ended
    sig_stage_info = QtCore.pyqtSignal(list)                #   | Stage parameters have been written/read                   | List containing the stage parameters
    ##
    # Identifier codes used for view-model communication. Other general-purpose codes are specified in abstract_instrument_interface
    SIG_MOVEMENT_STARTED = 1
    SIG_MOVEMENT_ENDED = 2
    SIG_HOMING_STARTED = 1
    SIG_HOMING_ENDED = 2

    def __init__(self, **kwargs):
        self.output = {'Position':0} 
        ### Default values of settings (might be overlapped by settings saved in .json files later)
        self.settings = {   'step_size': 1,
                            'ramp' : {  
                                        'ramp_step_size': 1,
                                        'ramp_wait_1': 1,
                                        'ramp_wait_2': 1,
                                        'ramp_numb_steps': 10,
                                        'ramp_repeat': 1,
                                        'ramp_reverse': 1,
                                        'ramp_send_initial_trigger': 1
                                        }
                            }
        self.list_devices = []              #list of devices found 
        self.connected_device_name = ''
        self._units = {'mm':1,'deg':2}
        ###
        self.instrument = pyThorlabsAPT() 
        ###
        super().__init__(**kwargs)

        # Setting up the ramp object, which is defined in the package abstract_instrument_interface
        self.ramp = abstract_instrument_interface.ramp(self)  
        self.ramp.set_ramp_settings(self.settings['ramp'])
        self.ramp.set_ramp_functions(func_move = self.instrument.move_by,
                                     func_trigger = self.update, 
                                     func_check_step_has_ended = self.is_device_not_moving, 
                                     list_functions_step_not_ended = [self.read_position],  
                                     list_functions_step_has_ended = [lambda:self.end_movement(send_signal=False)],  
                                     list_functions_ramp_ended = [])
        self.ramp.sig_ramp.connect(self.on_ramp_state_changed)

    def refresh_list_devices(self):
        '''
        Get a list of all devices connected, by using the method list_devices() of the driver. For each device obtain its identity and its address.
        '''            
        self.logger.info(f"Looking for devices...") 
        list_valid_devices = self.instrument.list_devices()
        if(len(list_valid_devices)>0):
            list_IDNs_and_devices = [str(dev[1]) + " --> " + str(dev[0]) for dev in list_valid_devices] 
        else:
            list_IDNs_and_devices =[]
            #list_IDNs_and_devices = [i for i in list_IDN] 
            #self.gui.combo_Devices.addItems(list_IDNs_and_devices)  
        self.logger.info(f"Found {len(list_valid_devices)} devices.") 
        self.sig_list_devices_updated.emit(list_IDNs_and_devices)
        self.list_IDNs_and_devices = list_IDNs_and_devices
        return list_IDNs_and_devices

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
    
    def set_step_size(self, s):
        try: 
            step_size = float(s)
            if self.settings['step_size'] == step_size: #if the value passed is the same as the one currently stored, we end here
                return True
        except ValueError:
            self.logger.error(f"The step size must be a valid float number.")
            self.sig_step_size.emit(self.settings['step_size'])
            return False
        self.logger.info(f"The step size is now {step_size}.")
        self.settings['step_size'] = step_size
        self.sig_step_size.emit(self.settings['step_size'])
        return True
    
    def home(self):
        if self.is_device_moving():
            self.logger.error(f"Cannot start homing while device is moving.")
            return
        self.logger.info(f"Homing device...")
        self.set_moving_state()
        self.sig_change_homing_status.emit(self.SIG_HOMING_STARTED)
        self.sig_change_moving_status.emit(self.SIG_MOVEMENT_STARTED)
        self.instrument.move_home()
        #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
        #position and update it in the GUI. When it becomes False, call self.end_movement
        self.check_property_until(lambda : self.instrument.is_in_motion,[True,False],
                                  [
                                      [self.read_position],
                                      [self.end_movement,
                                       lambda x=None:self.sig_change_homing_status.emit(self.SIG_HOMING_ENDED),
                                       lambda x=None:self.sig_change_moving_status.emit(self.SIG_MOVEMENT_ENDED)
                                      ]
                                   ])

    def move_single_step(self,direction,step_size = None):
        if self.is_device_moving():
            self.logger.error(f"Cannot start moving while device is already moving.")
            return
        if step_size == None:
            step_size = self.settings['step_size']
        movement = direction*step_size
        self.logger.info(f"Will move by {movement}. Begin moving...")
        self.set_moving_state()
        self.instrument.move_by(movement)
        #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
        #position. When it becomes False, call self.end_movement
        self.check_property_until(lambda : self.instrument.is_in_motion,[True,False],[[self.read_position],[self.end_movement]])
        
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
        self.interface.sig_step_size.connect(self.on_step_size_change)
        self.interface.sig_change_moving_status.connect(self.on_moving_state_change)
        self.interface.sig_change_homing_status.connect(self.on_homing_state_change)
        self.interface.sig_stage_info.connect(self.on_stage_info_change)
        #self.interface.ramp.sig_ramp.connect(self.on_ramp_state_change)
        self.interface.sig_close.connect(self.on_close)
        
        ### SET INITIAL STATE OF WIDGETS
        self.edit_StepSize.setText(str(self.interface.settings['step_size']))
        self.interface.refresh_list_devices()    #By calling this method, as soon as the gui is created we also look for devices
        self.on_moving_state_change(self.interface.SIG_MOVEMENT_ENDED)
        self.on_homing_state_change(self.interface.SIG_HOMING_ENDED)
        self.on_connection_status_change(self.interface.SIG_DISCONNECTED) #When GUI is created, all widgets are set to the "Disconnected" state              
        
    def create_widgets(self):
        """
        Creates all widgets and layout for the GUI. Any Widget and Layout must assigned to self.containter, which is a pyqt Layout object
        """ 
        self.container = Qt.QVBoxLayout()
        
        #Use the custom connection/listdevices panel, defined in abstract_instrument_interface.abstract_gui
        hbox1, widgets_dict = self.create_panel_connection_listdevices()
        for key, val in widgets_dict.items(): 
            setattr(self,key,val) 

        hbox2 = Qt.QHBoxLayout()
        self.label_Position = Qt.QLabel("Position: ")
        self.edit_Position = Qt.QLineEdit()
        self.edit_Position.setAlignment(QtCore.Qt.AlignRight)
        #self.label_PositionUnits = Qt.QLabel(" deg")
        self.label_Move = Qt.QLabel("Move: ")
        self.button_MoveNegative = Qt.QPushButton("<")
        self.button_MoveNegative.setToolTip('')
        self.button_MoveNegative.setMaximumWidth(30)
        self.button_MovePositive = Qt.QPushButton(">")
        self.button_MovePositive.setToolTip('')
        self.button_MovePositive.setMaximumWidth(30)
        self.label_By  = Qt.QLabel("By ")
        self.edit_StepSize = Qt.QLineEdit()
        self.edit_StepSize.setToolTip('')
        self.button_Home = Qt.QPushButton("Home")
        self.button_Stop = Qt.QPushButton("Stop any movement")
        widgets_row2 = [self.label_Position,self.edit_Position,self.label_Move,self.button_MoveNegative,self.button_MovePositive,self.label_By,self.edit_StepSize,self.button_Home,self.button_Stop]
        widgets_row2_stretches = [0]*len(widgets_row2)
        for w,s in zip(widgets_row2,widgets_row2_stretches):
            hbox2.addWidget(w,stretch=s)
        hbox2.addStretch(1)

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
        
        self.ramp_groupbox = abstract_instrument_interface.ramp_gui(ramp=self.interface.ramp)
                
        self.container = Qt.QVBoxLayout()
        for box in [hbox1,hbox2]:
            self.container.addLayout(box)  
        self.container.addWidget(self.ramp_groupbox)
        self.container.addWidget(stageparams_groupbox)

        self.container.addStretch(1)
        
        # Widgets for which we want to constraint the width by using sizeHint()
        widget_list = [self.label_Position, self.label_Move, self.label_By, self.button_Home,stageparams_groupbox, self.button_Stop]
        for w in widget_list:
            w.setMaximumSize(w.sizeHint())
        
        self.widgets_disabled_when_doing_ramp = [self.button_ConnectDevice,self.combo_Devices,
                                                 self.label_Position,self.edit_Position,self.button_Home,
                                               self.label_Move,self.button_MoveNegative,self.button_MovePositive,self.label_By,self.edit_StepSize,self.button_Home,self.button_set_stageparams
                                               ] + widgets_row4_stageparams
        #These widgets are enabled ONLY when interface is connected to a device
        self.widgets_enabled_when_connected = [self.combo_Devices , self.button_RefreshDeviceList,
                                               self.label_Position, self.edit_Position,self.button_Home,self.button_Stop,
                                               self.label_Move,self.button_MoveNegative,self.button_MovePositive,self.label_By,self.edit_StepSize,self.button_Home,self.button_set_stageparams,
                                               ] + widgets_row4_stageparams

        #These widgets are enabled ONLY when interface is NOT connected to a device   
        self.widgets_enabled_when_disconnected = [self.combo_Devices,  self.button_RefreshDeviceList]

        self.widgets_disabled_when_moving = widgets_row4_stageparams + [self.button_ConnectDevice,self.edit_StepSize,self.edit_Position,self.button_set_stageparams,self.button_MoveNegative ,self.button_MovePositive,self.button_Home]

    def connect_widgets_events_to_functions(self):
        self.button_RefreshDeviceList.clicked.connect(self.click_button_refresh_list_devices)
        self.button_ConnectDevice.clicked.connect(self.click_button_connect_disconnect)
        self.edit_Position.returnPressed.connect(self.press_enter_edit_Position)
        self.button_MoveNegative.clicked.connect(lambda x:self.click_button_Move(-1))
        self.button_MovePositive.clicked.connect(lambda x:self.click_button_Move(+1))
        self.button_Home.clicked.connect(self.click_button_Home)
        self.button_Stop.clicked.connect(self.click_button_Stop)
        self.edit_StepSize.returnPressed.connect(self.press_enter_edit_StepSize)
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
            
    def on_list_devices_updated(self,list_devices):
        self.combo_Devices.clear()  #First we empty the combobox  
        self.combo_Devices.addItems(list_devices) 

    def on_position_change(self,position):
        self.edit_Position.setText(str(position))
            
    def on_moving_state_change(self,status):
        if status == self.interface.SIG_MOVEMENT_STARTED:
            self.disable_widget(self.widgets_disabled_when_moving)
        if status == self.interface.SIG_MOVEMENT_ENDED:
            self.enable_widget(self.widgets_disabled_when_moving)
            
    def on_homing_state_change(self,status):
        self.on_moving_state_change(status)
    
#    def on_ramp_state_change(self,status):
#        if status == SIG_RAMP_STARTED:
#            self.disable_widget(self.widgets_disabled_when_doing_ramp )
#        if status == SIG_RAMP_ENDED:
#            self.enable_widget(self.widgets_disabled_when_doing_ramp )
#            self.set_connected_state()
            
    def on_step_size_change(self,value):
        self.edit_StepSize.setText(str(value))
        
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
    
    def press_enter_edit_StepSize(self):
        return self.interface.set_step_size(self.edit_StepSize.text())
    
    def click_button_Move(self,direction):
        self.press_enter_edit_StepSize()
        self.interface.move_single_step(direction)
        
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
    def closeEvent(self, event):
        #if self.child:
        pass#self.child.close()

def main():
    parser = argparse.ArgumentParser(description = "",epilog = "")
    parser.add_argument("-s", "--decrease_verbose", help="Decrease verbosity.", action="store_true")
    args = parser.parse_args()
    
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    Interface = interface(app=app) 
    Interface.verbose = not(args.decrease_verbose)
    app.aboutToQuit.connect(Interface.close) 
    view = gui(interface = Interface, parent=window) #In this case window is the parent of the gui
    
    window.show()
    app.exec()# Start the event loop.

if __name__ == '__main__':
    main()
