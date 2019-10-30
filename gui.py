"""This script creates the SAXS control GUI.

Pollack Lab-Cornell
Alex Mauney
"""


import tkinter as tk
from tkinter import filedialog, messagebox
from widgets import FlowPath, ElveflowDisplay, MiscLogger, COMPortSelector, ConsoleUi
import tkinter.ttk as ttk
import time
from hardware import FileIO
from configparser import ConfigParser
import logging
import winsound

import threading
from hardware import SAXSDrivers
import os.path
import csv
from hardware import solocomm
import numpy as np
import warnings
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import pyplot as plt
matplotlib.rcParams.update({'figure.autolayout': True})
warnings.filterwarnings("ignore", message="Attempting to set identical bottom==top")


FULLSCREEN = True   # For testing, turn this off
LOG_FOLDER = "log"


class Main:
    """Class for the main window of the SAXS Control."""

    def __init__(self, window):
        """Set up the window and button variables."""
        print("initializing GUI...")
        if not os.path.exists(LOG_FOLDER):
            print('Double checking log folder')
            time.sleep(1)
            if not os.path.exists(LOG_FOLDER):
                raise FileNotFoundError("%s folder not found" % LOG_FOLDER)
        elif not os.path.isdir(LOG_FOLDER):
            raise NotADirectoryError("%s is not a folder" % LOG_FOLDER)
        if not os.path.exists(ElveflowDisplay.OUTPUT_FOLDER):
            raise FileNotFoundError("%s folder not found" % ElveflowDisplay.OUTPUT_FOLDER)
        elif not os.path.isdir(ElveflowDisplay.OUTPUT_FOLDER):
            raise NotADirectoryError("%s is not a folder" % ElveflowDisplay.OUTPUT_FOLDER)
        self._lock = threading.RLock()
        self.python_logger = logging.getLogger("python")
        self.main_window = window
        self.oil_refill_flag = False
        self.main_window.report_callback_exception = self.handle_exception
        self.main_window.title('Main Window')
        self.adxIsDone = False
        self.illegal_chars = '!@#$%^&*()."\\|:;<>?=~ ' + "'"
        self.old_base_directory = '/mnt/currentdaq/BioSAXS/'
        self.old_sub_directory = ''
        self.main_window.attributes("-fullscreen", True)  # Makes the window fullscreen
        # Figure out geometry
        window_width = self.main_window.winfo_screenwidth()
        window_height = self.main_window.winfo_screenheight()
        core_width = round(2*window_width/3)
        log_width = window_width - core_width - 10
        state_height = 400
        core_height = window_height - state_height - 50
        log_height = core_height
        if not FULLSCREEN:
            self.main_window.attributes("-fullscreen", False)  # Makes the window fullscreen
            window_width = self.main_window.winfo_screenwidth() * 2//3
            window_height = self.main_window.winfo_screenheight() * 2//3
            state_height = 1
            core_width = round(2*window_width/3)
            log_width = window_width - core_width - 3
            core_height = window_height - state_height - 50
            log_height = core_height

        # Make it pretty
        self.gui_bg_color = "thistle3"
        self.label_bg_color = self.gui_bg_color
        #self.gui_bg_color = "lavender"
        #self.gui_bg_color = "deep pink"
        #self.gui_bg_color = "steel blue"

        self.main_window.configure(bg=self.gui_bg_color)
        ttk.Style().configure("TNotebook", background=self.gui_bg_color)

        # Button Bar
        self.buttons = tk.Frame(self.main_window)
        self.exit_button = tk.Button(self.main_window, text='X', command=self.exit_)
        self.stop_button = tk.Button(self.main_window, text='STOP', command=self.stop, fg='red', font='Arial 16 bold')

        # Main Structures

        self.core = ttk.Notebook(self.main_window, width=core_width, height=core_height)
        self.auto_page = tk.Frame(self.core, bg=self.gui_bg_color)
        self.config_page = tk.Frame(self.core, bg=self.gui_bg_color)
        self.manual_page = tk.Frame(self.core, bg=self.gui_bg_color)
        self.setup_page = tk.Frame(self.core, bg=self.gui_bg_color)
        self.elveflow_page = tk.Frame(self.core, bg=self.gui_bg_color)
        self.logs = ttk.Notebook(self.main_window, width=log_width, height=log_height)
        self.user_logs = tk.Frame(self.logs)
        self.advanced_logs = tk.Frame(self.logs)
        # self.instrument_logs = tk.Frame(self.logs)
        self.state_frame = tk.Frame(self.main_window, width=window_width, height=state_height, bg=self.gui_bg_color)
        # Widgets on Main page
        spec_width = 20
        self.spec_base_directory_label = tk.Label(self.auto_page, text='Spec Base Directory:', width=spec_width, bg=self.label_bg_color)
        self.spec_base_directory = tk.StringVar(value='')
        self.spec_base_directory_box = tk.Entry(self.auto_page, textvariable=self.spec_base_directory,  width=spec_width)
        self.spec_sub_directory_label = tk.Label(self.auto_page, text='Spec Subdirectory:',  width=spec_width, bg=self.label_bg_color)
        self.spec_sub_directory = tk.StringVar(value='')
        self.spec_sub_directory_box = tk.Entry(self.auto_page, textvariable=self.spec_sub_directory,  width=spec_width)
        self.spec_directory_button = tk.Button(self.auto_page, text='Change/Make Directory', command=self.ChangeDirectory,  width=spec_width)
        self.spec_filename_label = tk.Label(self.auto_page, text='Filename:',  width=spec_width, bg=self.label_bg_color)
        self.spec_filename = tk.StringVar(value='')
        self.spec_filename_box = tk.Entry(self.auto_page, textvariable=self.spec_filename,  width=spec_width)
        self.spec_fileno_label = tk.Label(self.auto_page, text='File #:',  width=spec_width, bg=self.label_bg_color)
        self.spec_fileno = tk.IntVar(value=0)
        self.spec_fileno_box = tk.Entry(self.auto_page, textvariable=self.spec_fileno,  width=spec_width)
        # Auto buttons
        auto_button_font = 'Arial 20 bold'
        auto_button_width = 10
        self.buffer_sample_buffer_button = tk.Button(self.auto_page, text='Auto Run', command=self.buffer_sample_buffer_command, font=auto_button_font, width=auto_button_width, height=3)
        self.clean_button = tk.Button(self.auto_page, text='Clean/Refill', command=self.clean_and_refill_command, font=auto_button_font, width=auto_button_width, height=3)
        self.load_sample_button = tk.Button(self.auto_page, text='Load Sample', command=self.load_sample_command, font=auto_button_font, width=auto_button_width)
        self.load_buffer_button = tk.Button(self.auto_page, text='Load Buffer', command=self.load_buffer_command, font=auto_button_font, width=auto_button_width)
        self.clean_only_button = tk.Button(self.auto_page, text='Clean Only', command=self.clean_only_command, font=auto_button_font, width=auto_button_width)
        self.refill_only_button = tk.Button(self.auto_page, text='Refill Only', command=self.refill_only_command, font=auto_button_font, width=auto_button_width)
        self.purge_button = tk.Button(self.auto_page, text='Purge', command=self.purge_command, font=auto_button_font, width=auto_button_width, height=3)
        self.purge_soap_button = tk.Button(self.auto_page, text='Purge Soap', command=self.purge_soap_command, font=auto_button_font, width=auto_button_width)
        self.purge_dry_button = tk.Button(self.auto_page, text='Dry Sheath', command=self.purge_dry_command, font=auto_button_font, width=auto_button_width)
        self.initialize_sheath_button = tk.Button(self.auto_page, text='Initialize Sheath', command=self.initialize_sheath_command, font=auto_button_font, width=auto_button_width)
        # Elveflow Plots
        self.fig_dpi = 96  # this shouldn't matter too much (because we normalize against it) except in how font sizes are handled in the plot
        self.main_tab_fig = plt.Figure(figsize=(core_width*2/3/self.fig_dpi, core_height*3/4/self.fig_dpi), dpi=self.fig_dpi)
        self.main_tab_ax1 = self.main_tab_fig.add_subplot(111)
        self.main_tab_ax2 = self.main_tab_ax1.twinx()
        self.graph_start_time = 0
        self.graph_end_time = np.inf
        self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.main_tab_fig, self.auto_page)
        self.canvas.draw()
        # Manual Page
        self.manual_page_buttons = []
        self.manual_page_variables = []
        # Config page
        self.config = None
        self.save_config_button = tk.Button(self.config_page, text='Save Config', command=self.save_config)
        self.load_config_button = tk.Button(self.config_page, text='Load Config', command=self.load_config)
        self.spec_address = tk.StringVar(value='')
        self.config_spec_address = tk.Entry(self.config_page, textvariable=self.spec_address)
        self.config_spec_address_label = tk.Label(self.config_page, text='SPEC Address', bg=self.label_bg_color)
        self.spec_connect_button = tk.Button(self.config_page, text='Connect to SPEC', command=self.connect_to_spec)
        self.volumes_label = tk.Label(self.config_page, text='Buffer/Sample/Buffer volumes in uL:', bg=self.label_bg_color)
        self.first_buffer_volume = tk.IntVar(value=25)     # May need ot be a doublevar
        self.first_buffer_volume_box = tk.Entry(self.config_page, textvariable=self.first_buffer_volume)
        self.sample_volume = tk.IntVar(value=25)           # May need ot be a doublevar
        self.sample_volume_box = tk.Entry(self.config_page, textvariable=self.sample_volume)
        self.last_buffer_volume = tk.IntVar(value=25)      # May need ot be a doublevar
        self.last_buffer_volume_box = tk.Entry(self.config_page, textvariable=self.last_buffer_volume)
        self.sample_flowrate_label = tk.Label(self.config_page, text="Sample-Buffer Infuse flowrate (ul/min)", bg=self.label_bg_color)
        self.sample_flowrate = tk.DoubleVar(value=10)
        self.sample_flowrate_box = tk.Entry(self.config_page, textvariable=self.sample_flowrate)
        self.oil_refill_flowrate_label = tk.Label(self.config_page, text="Oil refill rate (ul/min)", bg=self.label_bg_color)
        self.oil_refill_flowrate = tk.DoubleVar(value=10)
        self.oil_refill_flowrate_box = tk.Entry(self.config_page, textvariable=self.oil_refill_flowrate)
        self.oil_valve_names_label = tk.Label(self.config_page, text='Oil Valve Hardware Port Names', bg=self.label_bg_color)
        self.oil_valve_names = []
        self.oil_valve_name_boxes = []
        self.set_oil_valve_names_button = tk.Button(self.config_page, text='Set Names', command=self.set_oil_valve_names)
        self.loading_valve_names_label = tk.Label(self.config_page, text='Loading Valve Hardware Port Names', bg=self.label_bg_color)
        self.loading_valve_names = []
        self.loading_valve_name_boxes = []
        self.set_loading_valve_names_button = tk.Button(self.config_page, text='Set Names', command=self.set_loading_valve_names)
        self.tseries_time = tk.IntVar(value=0)
        self.tseries_time_box = tk.Entry(self.config_page, textvariable=self.tseries_time)
        self.tseries_frames = tk.IntVar(value=0)
        self.tseries_frames_box = tk.Entry(self.config_page, textvariable=self.tseries_frames)
        self.tseries_label = tk.Label(self.config_page, text='tseries parameters:', bg=self.label_bg_color)
        for i in range(6):
            self.oil_valve_names.append(tk.StringVar(value=''))
            self.oil_valve_name_boxes.append(tk.OptionMenu(self.config_page, self.oil_valve_names[i], ""))
            self.loading_valve_names.append(tk.StringVar(value=''))
            self.loading_valve_name_boxes.append(tk.OptionMenu(self.config_page, self.loading_valve_names[i], ""))
        self.elveflow_sourcename = tk.StringVar()
        self.low_soap_time_label = tk.Label(self.config_page, text="Low soap time:", bg=self.label_bg_color)
        self.low_soap_time = tk.IntVar(value=0)
        self.low_soap_time_box = tk.Spinbox(self.config_page, from_=0, to=1000, textvariable=self.low_soap_time)
        self.high_soap_time_label = tk.Label(self.config_page, text="High soap time:", bg=self.label_bg_color)
        self.high_soap_time = tk.IntVar(value=0)
        self.high_soap_time_box = tk.Spinbox(self.config_page, from_=0, to=1000, textvariable=self.high_soap_time)
        self.water_time_label = tk.Label(self.config_page, text="Water time:", bg=self.label_bg_color)
        self.water_time = tk.IntVar(value=0)
        self.water_time_box = tk.Spinbox(self.config_page, from_=0, to=1000, textvariable=self.water_time)
        self.air_time_label = tk.Label(self.config_page, text="Air time:", bg=self.label_bg_color)
        self.air_time = tk.IntVar(value=0)
        self.air_time_box = tk.Spinbox(self.config_page, from_=0, to=1000, textvariable=self.air_time)

        self.purge_possition_label = tk.Label(self.config_page, text="Purge valve possitions:", bg=self.label_bg_color)
        self.purge_running_label = tk.Label(self.config_page, text="running:", bg=self.label_bg_color)
        self.purge_running_pos = tk.IntVar(value=0)
        self.purge_running_box = tk.Spinbox(self.config_page, from_=0, to=100, textvariable=self.purge_running_pos)

        self.purge_water_label = tk.Label(self.config_page, text="Water Purge:", bg=self.label_bg_color)
        self.purge_water_pos = tk.IntVar(value=0)
        self.purge_water_box = tk.Spinbox(self.config_page, from_=0, to=100, textvariable=self.purge_water_pos)

        self.purge_soap_label = tk.Label(self.config_page, text="Soap:", bg=self.label_bg_color)
        self.purge_soap_pos = tk.IntVar(value=0)
        self.purge_soap_box = tk.Spinbox(self.config_page, from_=0, to=100, textvariable=self.purge_soap_pos)

        self.purge_air_label = tk.Label(self.config_page, text="Air:", bg=self.label_bg_color)
        self.purge_air_pos = tk.IntVar(value=0)
        self.purge_air_box = tk.Spinbox(self.config_page, from_=0, to=100, textvariable=self.purge_air_pos)

        def _set_elveflow_sourcename(*args):
            self.config['Elveflow']['elveflow_sourcename'] = self.elveflow_sourcename.get()
        self.elveflow_sourcename.trace('w', _set_elveflow_sourcename)
        self.elveflow_sourcename_label = tk.Label(self.config_page, text='Elveflow sourcename', bg=self.label_bg_color)
        self.elveflow_sourcename_box = tk.Entry(self.config_page, textvariable=self.elveflow_sourcename)
        self.elveflow_sensortypes_label = tk.Label(self.config_page, text='Elveflow sensor types', bg=self.label_bg_color)
        self.elveflow_sensortypes = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.elveflow_sensortypes_optionmenu = [None, None, None, None]
        for i in range(4):
            self.elveflow_sensortypes_optionmenu[i] = tk.OptionMenu(self.config_page, self.elveflow_sensortypes[i], None)
            self.elveflow_sensortypes_optionmenu[i]['menu'].delete(0, 'end')  # there's a default empty option, so get rid of that first
            for item in FileIO.SDK_SENSOR_TYPES:
                def _set_elveflow_sensor(i=i, item=item):
                    # weird default argument for scoping; not sure if it's needed but whatever, it works; don't touch it
                    self.elveflow_sensortypes[i].set(item)
                    self.config['Elveflow']['sensor%d_type' % (i+1)] = item
                self.elveflow_sensortypes_optionmenu[i]['menu'].add_command(label=item, command=_set_elveflow_sensor)
        self.elveflow_oil_channel_pressure_label = tk.Label(self.config_page, text='Elveflow oil channel, pressure [mbar]', bg=self.label_bg_color)
        self.elveflow_oil_channel = tk.StringVar()
        self.elveflow_oil_pressure = tk.StringVar()
        self.elveflow_oil_channel_box = tk.Entry(self.config_page, textvariable=self.elveflow_oil_channel)
        self.elveflow_oil_pressure_box = tk.Entry(self.config_page, textvariable=self.elveflow_oil_pressure)
        self.elveflow_sheath_channel_pressure_label = tk.Label(self.config_page, text='Elveflow sheath channel, volume [µL/min]', bg=self.label_bg_color)
        self.elveflow_sheath_channel = tk.StringVar()
        self.elveflow_sheath_volume = tk.StringVar()
        self.elveflow_sheath_channel_box = tk.Entry(self.config_page, textvariable=self.elveflow_sheath_channel)
        self.elveflow_sheath_volume_box = tk.Entry(self.config_page, textvariable=self.elveflow_sheath_volume)

        # Make Instrument
        self.AvailablePorts = SAXSDrivers.list_available_ports()
        self.controller = SAXSDrivers.SAXSController(timeout=0.1)
        self.instruments = []
        self.pump = None
        self.purge_valve = None
        self.NumberofPumps = 0
        # Setup Page
        self.hardware_config_options = ("Pump", "Oil Valve", "Sample/Buffer Valve", "Loading Valve", "Purge")
        self.AvailablePorts = SAXSDrivers.list_available_ports()
        self.setup_page_buttons = []
        self.setup_page_variables = []
        self.refresh_com_ports = tk.Button(self.setup_page, text="Refresh COM", command=lambda: self.refresh_com_list())
        self.AddPump = tk.Button(self.setup_page, text="Add Pump", command=lambda: self.add_pump_set_buttons())
        self.AddRheodyne = tk.Button(self.setup_page, text="Add Rheodyne", command=lambda: self.add_rheodyne_set_buttons())
        self.AddVICI = tk.Button(self.setup_page, text="Add VICI Valve", command=lambda: self.AddVICISetButtons())
        self.ControllerCOM = COMPortSelector(self.setup_page, exportselection=0, height=3)
        self.ControllerSet = tk.Button(self.setup_page, text="Set Microntroller", command=lambda: self.controller.set_port(self.AvailablePorts[int(self.ControllerCOM.curselection()[0])].device, self.instruments))
        self.I2CScanButton = tk.Button(self.setup_page, text="Scan I2C line", command=lambda: self.controller.scan_i2c())

        # logs
        log_length = 39  # in lines
        self.user_logger_gui = ConsoleUi(self.user_logs, True)
        self.user_logger_gui.set_levels((logging.INFO, logging.WARNING))
        self.advanced_logger_gui = ConsoleUi(self.advanced_logs)
        # self.instrument_logger = MiscLogger(self.instrument_logs, state='disabled', height=log_length)
        # self.instrument_logger.configure(font='TkFixedFont')

        #
        # Flow setup frames
        self.sucrose = False


        if self.sucrose:
            self.flowpath = FlowPath(self.state_frame, self, sucrose=True, bg=self.gui_bg_color)
        else:
            self.flowpath = FlowPath(self.state_frame, self, bg=self.gui_bg_color)
        time.sleep(0.6)   # I have no idea why we need this but everything crashes and burns if we don't include it
        # It acts as though there's a race condition, but aren't we still single-threaded at this point?
        # I suspect something might be going wrong with the libraries, then, especially tkinter and matplotlib
        self.refresh_dropdown(self.oil_valve_name_boxes, self.flowpath.valve2.gui_names, self.oil_valve_names)
        self.refresh_dropdown(self.loading_valve_name_boxes, self.flowpath.valve4.gui_names, self.loading_valve_names)
        self.draw_static()
        self.elveflow_display = ElveflowDisplay(self.elveflow_page, core_height, core_width, self.config['Elveflow'], self.python_logger)
        self.elveflow_display.grid(row=0, column=0)
        self.queue = solocomm.controlQueue
        self.manual_queue = solocomm.ManualControlQueue
        self.queue_busy = False
        self.listen_run_flag = threading.Event()
        self.listen_run_flag.set()
        # self.listen_thread = threading.Thread(target=self.listen)
        # self.listen_thread.start()
        #self.load_config(filename='config.ini')
        self.connect_to_spec()
        self.start_manual_thread()
        self.elveflow_display.start()

    def draw_static(self):
        """Define the geometry of the frames and objects."""
        self.stop_button.grid(row=0, column=0, columnspan=2, rowspan=2, sticky='N')
        self.exit_button.grid(row=0, column=1, sticky='NE')
        self.core.grid(row=1, column=0)
        self.logs.grid(row=1, column=1)
        self.state_frame.grid(row=2, column=0, columnspan=2)
        self.stop_button.lift()
        # Main Tab Bar
        self.core.add(self.auto_page, text='Auto')
        self.core.add(self.manual_page, text='Manual')
        self.core.add(self.config_page, text='Config')
        self.core.add(self.setup_page, text='Setup')
        self.core.add(self.elveflow_page, text='Elveflow')
        # Log Tab Bar
        self.logs.add(self.user_logs, text='Simple')
        self.logs.add(self.advanced_logs, text='Advanced')
        # self.logs.add(self.instrument_logs, text='Instruments')
        # Main Page
        self.spec_base_directory_label.grid(row=0, column=0)
        self.spec_base_directory_box.grid(row=1, column=0)
        self.spec_sub_directory_label.grid(row=0, column=1)
        self.spec_sub_directory_box.grid(row=1, column=1)
        self.spec_directory_button.grid(row=4, column=1)
        self.spec_filename_label.grid(row=2, column=0)
        self.spec_filename_box.grid(row=3, column=0)
        self.spec_fileno_label.grid(row=2, column=1)
        self.spec_fileno_box.grid(row=3, column=1)
        # Main Page Buttons
        self.buffer_sample_buffer_button.grid(row=11, column=0, rowspan=2)
        self.load_sample_button.grid(row=11, column=3)
        self.load_buffer_button.grid(row=12, column=3)
        self.clean_button.grid(row=11, column=1, rowspan=2)
        self.clean_only_button.grid(row=11, column=2)
        self.refill_only_button.grid(row=12, column=2)
        self.purge_button.grid(row=11, column=4, rowspan=2)
        self.purge_soap_button.grid(row=11, column=5)
        self.purge_dry_button.grid(row=12, column=5)
        self.canvas.get_tk_widget().grid(row=0, column=2, rowspan=10, columnspan=8, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)

        self.initialize_sheath_button.grid(row=8, column=0, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S)  # TODO: make buttons play nice with Josue's buttons
        # Manual page
        # Config page
        rowcounter = 0
        self.save_config_button.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.load_config_button.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.config_spec_address_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.config_spec_address.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.spec_connect_button.grid(row=rowcounter, column=2, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.volumes_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.first_buffer_volume_box.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.sample_volume_box.grid(row=rowcounter, column=2, sticky=tk.W+tk.E+tk.N+tk.S)
        self.last_buffer_volume_box.grid(row=rowcounter, column=3, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.sample_flowrate_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.sample_flowrate_box.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.oil_refill_flowrate_label.grid(row=rowcounter, column=2, sticky=tk.W+tk.E+tk.N+tk.S)
        self.oil_refill_flowrate_box.grid(row=rowcounter, column=3, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.oil_valve_names_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.set_oil_valve_names_button.grid(row=rowcounter, column=7, sticky=tk.W+tk.E+tk.N+tk.S)
        for i in range(6):
            self.oil_valve_name_boxes[i].grid(row=rowcounter, column=i+1, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.loading_valve_names_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.set_loading_valve_names_button.grid(row=rowcounter, column=7, sticky=tk.W+tk.E+tk.N+tk.S)
        for i in range(6):
            self.loading_valve_name_boxes[i].grid(row=rowcounter, column=i+1, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 2
        self.elveflow_sourcename_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.elveflow_sourcename_box.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.elveflow_sensortypes_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        for i in range(4):
            self.elveflow_sensortypes_optionmenu[i].grid(row=rowcounter, column=i+1, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.elveflow_oil_channel_pressure_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.elveflow_oil_channel_box.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.elveflow_oil_pressure_box.grid(row=rowcounter, column=2, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.elveflow_sheath_channel_pressure_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.elveflow_sheath_channel_box.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.elveflow_sheath_volume_box.grid(row=rowcounter, column=2, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.tseries_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.tseries_time_box.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.tseries_frames_box.grid(row=rowcounter, column=2, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.low_soap_time_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.low_soap_time_box.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.high_soap_time_label.grid(row=rowcounter, column=2, sticky=tk.W+tk.E+tk.N+tk.S)
        self.high_soap_time_box.grid(row=rowcounter, column=3, sticky=tk.W+tk.E+tk.N+tk.S)
        self.water_time_label.grid(row=rowcounter, column=4, sticky=tk.W+tk.E+tk.N+tk.S)
        self.water_time_box.grid(row=rowcounter, column=5, sticky=tk.W+tk.E+tk.N+tk.S)
        self.air_time_label.grid(row=rowcounter, column=6, sticky=tk.W+tk.E+tk.N+tk.S)
        self.air_time_box.grid(row=rowcounter, column=7, sticky=tk.W+tk.E+tk.N+tk.S)
        rowcounter += 1
        self.purge_possition_label.grid(row=rowcounter, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        self.purge_running_label.grid(row=rowcounter, column=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.purge_running_box.grid(row=rowcounter, column=2, sticky=tk.W+tk.E+tk.N+tk.S)
        self.purge_water_label.grid(row=rowcounter, column=3, sticky=tk.W+tk.E+tk.N+tk.S)
        self.purge_water_box.grid(row=rowcounter, column=4, sticky=tk.W+tk.E+tk.N+tk.S)
        self.purge_soap_label.grid(row=rowcounter, column=5, sticky=tk.W+tk.E+tk.N+tk.S)
        self.purge_soap_box.grid(row=rowcounter, column=6, sticky=tk.W+tk.E+tk.N+tk.S)
        self.purge_air_label.grid(row=rowcounter, column=7, sticky=tk.W+tk.E+tk.N+tk.S)
        self.purge_air_box.grid(row=rowcounter, column=8, sticky=tk.W+tk.E+tk.N+tk.S)
        # Setup page
        self.refresh_com_ports.grid(row=0, column=0)
        self.AddPump.grid(row=0, column=1)
        self.AddRheodyne.grid(row=0, column=2)
        self.AddVICI.grid(row=0, column=3)
        self.ControllerCOM.grid(row=1, column=0)
        self.ControllerSet.grid(row=1, column=2)
        self.I2CScanButton.grid(row=1, column=3)
        self.refresh_com_list()
        # FlowPath
        self.flowpath.grid(row=0, column=0)
        # Python Log
        nowtime = time.time()
        file_handler = logging.FileHandler(os.path.join(LOG_FOLDER, "log%010d.txt" % nowtime), encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        file_handler.setLevel(logging.DEBUG)
        # SPEC Log
        # self.instrument_logger.grid(row=0, column=0, sticky='NSEW')
        # Should logger definition be in draw function?

        self.python_logger.setLevel(logging.DEBUG)
        self.user_logger_gui.pass_logger(self.python_logger)
        self.advanced_logger_gui.pass_logger(self.python_logger)
        self.python_logger.addHandler(file_handler)  # logging to a file
        self.controller.logger = self.python_logger  # Pass the logger to the controller
        self.load_config(filename='config.ini', preload=False)

    def stop(self):
        """Stop all running widgets."""
        self.solo_controller.abortProcess = True
        self.stop_instruments()

    def stop_instruments(self):
        SAXSDrivers.InstrumentTerminateFunction(self.instruments)
        # Nesting the commands so that if one fails the rest still complete
        for instrument in self.instruments:
            if instrument.enabled and instrument.instrument_type == "Pump":
                if instrument.is_running():
                    return

        try:
            self.flowpath.valve4.set_auto_position("Load")
        except:
            pass
        finally:
            try:
                self.flowpath.valve2.set_auto_position("Waste")
            except:
                pass
            finally:
                try:
                    self.flowpath.valve3.set_auto_position(1)
                except:
                    pass

        # Add Elveflow stop if we use it for non-pressure

    def load_config(self, filename=None, preload=False):
        """Load a config.ini file."""
        if self.config is None:
            # don't create a new one if there's an old one already
            # this lets us keep all the same old pointers to the old config parser
            self.config = ConfigParser()
        if filename is None:
            filename = filedialog.askopenfilename(initialdir=".", title="Select file", filetypes=(("config files", "*.ini"), ("all files", "*.*")))
        if filename != '':
            with open(filename, encoding='utf-8') as f:
                # why does it only sometimes find the file?
                self.config.read_file(f)
            main_config = self.config['Main']
            elveflow_config = self.config['Elveflow']
            spec_config = self.config['SPEC']
            run_config = self.config['Run Params']
            oil_config = self.config['Oil Valve']
            loading_config = self.config['Loading Valve']
            instrument_config = self.config['Instruments']
            # Main Config
            self.sucrose = main_config.getboolean('Sucrose', False)
            # Elveflow Config
            self.elveflow_sourcename.set(elveflow_config.get('elveflow_sourcename', b''))
            self.elveflow_sensortypes[0].set(elveflow_config.get('sensor1_type', 'none'))
            self.elveflow_sensortypes[1].set(elveflow_config.get('sensor2_type', 'none'))
            self.elveflow_sensortypes[2].set(elveflow_config.get('sensor3_type', 'none'))
            self.elveflow_sensortypes[3].set(elveflow_config.get('sensor4_type', 'none'))
            self.elveflow_oil_channel.set(elveflow_config.get('elveflow_oil_channel', -1))
            self.elveflow_oil_pressure.set(elveflow_config.get('elveflow_oil_pressure', 0))
            self.elveflow_sheath_channel.set(elveflow_config.get('elveflow_sheath_channel', -1))
            self.elveflow_sheath_volume.set(elveflow_config.get('elveflow_sheath_volume', 0))
            # SPEC Config
            self.spec_address.set(spec_config.get('spec_host', ''))
            self.tseries_time.set(spec_config.get('tseries_time', '10'))
            self.tseries_frames.set(spec_config.get('tseries_frames', '10'))
            self.spec_sub_directory.set(spec_config.get('sub_dir', self.old_sub_directory))
            self.old_sub_directory = self.spec_sub_directory.get()
            self.spec_base_directory.set(spec_config.get('base_dir', self.old_base_directory))
            self.old_base_directory = self.spec_base_directory.get()
            # Run Config
            self.sample_flowrate.set(run_config.get('sample_rate', 10))
            self.oil_refill_flowrate.set(run_config.get('oil_rate', 10))
            self.first_buffer_volume.set(run_config.get('buffer1_vol', 25))
            self.sample_volume.set(run_config.get('sample_vol', 25))
            self.last_buffer_volume.set(run_config.get('buffer2_vol', 25))
            self.low_soap_time.set(run_config.get('low_soap_time', 0))
            self.high_soap_time.set(run_config.get('high_soap_time', 0))
            self.water_time.set(run_config.get('water_time', 0))
            self.air_time.set(run_config.get('air_time', 0))
            # Valve Config
            for i in range(0, 6):
                field = 'name'+str(i+1)
                self.oil_valve_names[i].set(oil_config.get(field, ''))
                self.loading_valve_names[i].set(loading_config.get(field, ''))

        if not preload:
            self.set_oil_valve_names()
            self.set_loading_valve_names()
        # Instrument Config
        # Clear existing devices
        self.instruments = []
        self.manual_page_buttons = []
        self.manual_page_variables = []
        self.setup_page_buttons = []
        self.setup_page_variables = []
        self.NumberofPumps = 0
        for i in range(int(instrument_config.get("n_pumps", 0))):
            field = "Pump"+str(i)
            self.add_pump_set_buttons(int(instrument_config.get(field+"_address", 0)), instrument_config.get(field+"_name", ""), instrument_config.get(field+"_hardware", ""), pc_connect=instrument_config.getboolean(field+"_pc_connect", True))

        for i in range(int(instrument_config.get("n_rheodyne", 0))):
            field = "Rheodyne"+str(i)
            self.add_rheodyne_set_buttons(int(instrument_config.get(field+"_address", -1)), instrument_config.get(field+"_name", ""), instrument_config.get(field+"_hardware", ""), pc_connect=instrument_config.getboolean(field+"_pc_connect", True))

        for i in range(int(instrument_config.get("n_vici", 0))):
            field = "VICI"+str(i)
            self.AddVICISetButtons(instrument_config.get(field+"_name", ''), instrument_config.get(field+"_hardware", ""), pc_connect=instrument_config.getboolean(field+"_pc_connect", True))

    def save_config(self):
        """Save a config.ini file."""
        filename = filedialog.asksaveasfilename(initialdir=".", title="Select file", filetypes=(("config files", "*.ini"), ("all files", "*.*")))
        if filename != '':
            main_config = self.config['Main']
            elveflow_config = self.config['Elveflow']
            spec_config = self.config['SPEC']
            run_config = self.config['Run Params']
            oil_config = self.config['Oil Valve']
            loading_config = self.config['Loading Valve']
            instrument_config = self.config['Instruments']
            # Main Config
            main_config['Sucrose'] = str(self.sucrose)
            # Elveflow Config
            elveflow_config['elveflow_sourcename'] = self.elveflow_sourcename.get()
            elveflow_config['sensor1_type'] = self.elveflow_sensortypes[0].get()
            elveflow_config['sensor2_type'] = self.elveflow_sensortypes[1].get()
            elveflow_config['sensor3_type'] = self.elveflow_sensortypes[2].get()
            elveflow_config['sensor4_type'] = self.elveflow_sensortypes[3].get()
            elveflow_config['elveflow_oil_channel'] = self.elveflow_oil_channel.get()
            elveflow_config['elveflow_oil_pressure'] = self.elveflow_oil_pressure.get()
            elveflow_config['elveflow_sheath_channel'] = self.elveflow_sheath_channel.get()
            elveflow_config['elveflow_sheath_volume'] = self.elveflow_sheath_volume.get()
            # SPEC Config
            spec_config['spec_host'] = self.spec_address.get()
            spec_config['tseries_time'] = str(self.tseries_time.get())
            spec_config['tseries_frames'] = str(self.tseries_frames.get())
            spec_config['sub_dir'] = self.spec_sub_directory.get()
            spec_config['base_dir'] = self.spec_base_directory.get()
            # Run Config
            run_config['sample_rate'] = str(self.sample_flowrate.get())
            run_config['oil_rate'] = str(self.oil_refill_flowrate.get())
            run_config['buffer1_vol'] = str(self.first_buffer_volume.get())
            run_config['sample_vol'] = str(self.sample_volume.get())
            run_config['buffer2_vol'] = str(self.last_buffer_volume.get())
            run_config['low_soap_time'] = str(self.low_soap_time.get())
            run_config['high_soap_time'] = str(self.high_soap_time.get())
            run_config['water_time'] = str(self.water_time.get())
            run_config['air_time'] = str(self.air_time.get())
            # Valve Configs
            for i in range(0, 6):
                field = 'name'+str(i+1)
                oil_name = self.oil_valve_names[i].get()
                if oil_name is not '':
                    oil_config[field] = oil_name
                loading_name = self.loading_valve_names[i].get()
                if loading_name is not '':
                    loading_config[field] = loading_name

            elveflow_config['elveflow_sourcename'] = self.elveflow_sourcename.get()

            spec_config['tseries_time'] = str(self.tseries_time.get())
            spec_config['tseries_frames'] = str(self.tseries_frames.get())
            # Instrument Config
            npumps = 0
            nrheodyne = 0
            nvici = 0
            for instrument in self.instruments:
                if instrument.instrument_type == "Pump":
                    instrument_config["Pump"+str(npumps)+"_address"] = str(instrument.address)
                    instrument_config["Pump"+str(npumps)+"_name"] = instrument.name
                    instrument_config["Pump"+str(npumps)+"_hardware"] = instrument.hardware_configuration
                    instrument_config["Pump"+str(npumps)+"_pc_connect"] = str(instrument.pc_connect)
                    npumps += 1
                if instrument.instrument_type == "Rheodyne":
                    instrument_config["Rheodyne"+str(nrheodyne)+"_address"] = str(instrument.address_I2C)
                    instrument_config["Rheodyne"+str(nrheodyne)+"_name"] = instrument.name
                    instrument_config["Rheodyne"+str(nrheodyne)+"_hardware"] = instrument.hardware_configuration
                    instrument_config["Rheodyne"+str(nrheodyne)+"_pc_connect"] = str(instrument.pc_connect)
                    nrheodyne += 1
                if instrument.instrument_type == "VICI":
                    instrument_config["VICI"+str(nvici)+"_name"] = instrument.name
                    instrument_config["VICI"+str(nvici)+"_hardware"] = instrument.hardware_configuration
                    instrument_config["VICI"+str(nvici)+"_pc_connect"] = str(instrument.pc_connect)
                    nvici += 1
            instrument_config["n_pumps"] = str(npumps)
            instrument_config["n_rheodyne"] = str(nrheodyne)
            instrument_config["n_vici"] = str(nvici)

            self.config.write(open(filename, 'w', encoding='utf-8'))

    def set_oil_valve_names(self):
        """Send selection valve names to the control gui."""
        self.python_logger.info("Oil valve names set.")
        for i in range(0, 6):
            self.flowpath.valve2.name_position(i, self.oil_valve_names[i].get())

    def set_loading_valve_names(self):
        """Send selection valve names to the control gui."""
        self.python_logger.info("Loading valve names set.")
        for i in range(0, 6):
            self.flowpath.valve4.name_position(i, self.loading_valve_names[i].get())

    def connect_to_spec(self):
        """Connect to SPEC instance."""
        try:
            self.solo_controller.ADXComm.tryReconnect(TryOnce=True, host=self.spec_address.get())
        except AttributeError:
            self.solo_controller = solocomm.initConnections(self, host=self.spec_address.get())

    def start_manual_thread(self):
        """ Creates the thread for running instruments separate from auto thread"""
        manual_thread = solocomm.ManualControlThread(self)
        manual_thread.setDaemon(True)
        manual_thread.start()

    def handle_exception(self, exception, value, traceback):
        """Add python exceptions to the GUI log."""
        self.python_logger.exception("Caught exception:")

    def save_history(self, filename=None):
        """Save a csv file with the current state."""
        if filename is None:
            filename = filedialog.asksaveasfilename(initialdir=".", title="Save file", filetypes=(("comma-separated value", "*.csv"), ("all files", "*.*")))
        if filename == '':
            # empty filename: don't save
            return
        with open(filename, 'w') as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow(Main.CSV_HEADERS)
            csvwriter.writerows(self.history)

    def exit_(self):
        """Exit the GUI and stop all running things."""
        print("STARTING EXIT PROCEDURE")
        self.stop()
        self.elveflow_display.stop(shutdown=True)
        # if self.SPEC_Connection.run_flag.is_set():
        #    self.SPEC_Connection.stop()
        if self.listen_run_flag.is_set():
            self.listen_run_flag.clear()
        print("WAITING FOR OTHER THREADS TO SHUT DOWN...")
        while not self.elveflow_display.done_shutting_down:
            # We could do this smarter by waiting for events. But we're not smarter.
            time.sleep(0.2)
        print("THANK Y'ALL FOR COMING! A LA PROCHAINE !")
        self.main_window.destroy()

    def update_graph(self):
        """Look into self's ElveflowDisplay and reproduce it on self.main_tab_fig."""
        self.main_tab_ax1.set_title("Elveflow readout for most recent scan", fontsize=16)
        data_x_label_var = self.elveflow_display.data_x_label_var.get()
        data_y1_label_var = self.elveflow_display.data_y1_label_var.get()
        data_y2_label_var = self.elveflow_display.data_y2_label_var.get()
        self.main_tab_ax1.set_xlabel(data_x_label_var, fontsize=14)
        self.main_tab_ax1.set_ylabel(data_y1_label_var, fontsize=14, color=ElveflowDisplay.COLOR_Y1)
        self.main_tab_ax2.set_ylabel(data_y2_label_var, fontsize=14, color=ElveflowDisplay.COLOR_Y2)
        try:
            # read it once to avoid a race condition here when reading from
            # self.elveflow_display.data at the same time as it gets data from the machine
            elveflow_display_data = self.elveflow_display.data.copy()
            data_x = np.array([elt[data_x_label_var] for elt in elveflow_display_data])
            data_y1 = np.array([elt[data_y1_label_var] for elt in elveflow_display_data])
            data_y2 = np.array([elt[data_y2_label_var] for elt in elveflow_display_data])

            data_x_viable = (data_x >= self.graph_start_time)  # & (data_x < self.graph_end_time)
            data_x = data_x[data_x_viable]
            data_y1 = data_y1[data_x_viable]
            data_y2 = data_y2[data_x_viable]

            if data_x_label_var == self.elveflow_display.elveflow_handler.header[0]:
                data_x -= self.elveflow_display.starttime
            if data_y1_label_var == self.elveflow_display.elveflow_handler.header[0]:
                data_y1 -= self.elveflow_display.starttime
            if data_y2_label_var == self.elveflow_display.elveflow_handler.header[0]:
                data_y2 -= self.elveflow_display.starttime

            extremes = [np.nanmin(data_x), np.nanmax(data_x), np.nanmin(data_y1), np.nanmax(data_y1), np.nanmin(data_y2), np.nanmax(data_y2)]
            if len(data_x) > 0:
                self.the_line1.set_data(data_x, data_y1)
                self.the_line2.set_data(data_x, data_y2)
        except (ValueError, KeyError):
            extremes = [*self.main_tab_ax1.get_xlim(), *self.main_tab_ax1.get_ylim(), *self.main_tab_ax2.get_ylim()]
        limits = [item if item is not None else extremes[i]
                  for (i, item) in enumerate(self.elveflow_display.axisLimits_numbers)]
        self.main_tab_ax1.set_xlim(*extremes[0:2])
        self.main_tab_ax1.set_ylim(*limits[2:4])
        self.main_tab_ax2.set_ylim(*limits[4:6])

        self.canvas.draw()  # may need the stupid hack from widgets.py

    def graph_vline(self):
        """Add a vertical line to the graph."""
        self.main_tab_ax1.axvline(int(time.time() - self.elveflow_display.starttime), color='k', linewidth=5)

    def buffer_sample_buffer_command(self):
        """Run a buffer-sample-buffer cycle."""
        if self.elveflow_display is None or self.elveflow_display.elveflow_handler is None:
            # TODO: make us not need to do this twice?
            self.python_logger.warning("Elveflow connection not initialized! Please start the connection on the Elveflow tab.")
            raise RuntimeError("Elveflow connection not initialized! Please start the connection on the Elveflow tab.")

        if self.oil_refill_flag is False:
            MsgBox = messagebox.askquestion('Warning', 'Oil may not be full, continue with buffer/sample/buffer?', icon='warning')
            if MsgBox == 'yes':
                pass
            else:
                return

        # before scheduling anything, clear the graph
        self.main_tab_ax1.clear()
        self.main_tab_ax2.clear()
        self.the_line1 = self.main_tab_ax1.plot([], [], color=ElveflowDisplay.COLOR_Y1)[0]
        self.the_line2 = self.main_tab_ax2.plot([], [], color=ElveflowDisplay.COLOR_Y2)[0]
        self.graph_start_time = int(time.time())
        self.graph_end_time = np.inf
        self.python_logger.debug("main page graph start time: %s" % self.graph_start_time)
        self.flowpath.set_unlock_state(False)

        self.update_graph()
        self.oil_refill_flag = False

        self.queue.put((self.python_logger.info, "Starting to run buffer-sample-buffer"))
        self.queue.put(self.update_graph)
        self.queue.put(self.elveflow_display.start_saving)

        self.queue.put((self.python_logger.info, "Starting to run pre-buffer"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Run"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Run"))
        self.queue.put((self.pump.infuse_volume, self.first_buffer_volume.get()/1000, self.sample_flowrate.get()))
        self.queue.put((self.pump.wait_until_stopped, self.first_buffer_volume.get()/self.sample_flowrate.get()*60, self.update_graph))

        self.queue.put(self.graph_vline)
        self.queue.put(self.update_graph)
        self.queue.put((self.python_logger.info, "Starting to run sample"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Run"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 1))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Run"))
        self.queue.put((self.pump.infuse_volume, self.sample_volume.get()/1000, self.sample_flowrate.get()))
        self.queue.put((self.pump.wait_until_stopped, self.sample_volume.get()/self.sample_flowrate.get()*60, self.update_graph))

        self.queue.put(self.graph_vline)
        self.queue.put(self.update_graph)
        self.queue.put((self.python_logger.info, "Starting to run post-buffer"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Run"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Run"))
        self.queue.put((self.pump.infuse_volume, self.last_buffer_volume.get()/1000, self.sample_flowrate.get()))
        self.queue.put((self.pump.wait_until_stopped, self.last_buffer_volume.get()/self.sample_flowrate.get()*60, self.update_graph))

        self.queue.put(self.elveflow_display.stop_saving)
        self.queue.put(self.update_graph)

        def update_end_time():
            self.graph_end_time = int(time.time())
        self.queue.put(update_end_time)
        self.queue.put((self.python_logger.info, "Done with running buffer-sample-buffer"))

        self.clean_and_refill_command()  # Run a clean and refill after finishing

    def clean_and_refill_command(self):
        """Clean the buffer and sample loops, then refill the oil."""
        elveflow_oil_channel = int(self.elveflow_oil_channel.get())  # throws an error if the conversion doesn't work
        elveflow_oil_pressure = self.elveflow_oil_pressure.get()

        self.queue.put((self.python_logger.info, "Starting to run clean/refill command"))
        self.flowpath.set_unlock_state(False)
        self.queue.put((self.elveflow_display.pressureValue_var[elveflow_oil_channel - 1].set, elveflow_oil_pressure))  # Set oil pressure
        self.queue.put((self.elveflow_display.start_pressure, elveflow_oil_channel))
        self.queue.put((self.pump.refill_volume, (self.sample_volume.get()+self.first_buffer_volume.get()+self.last_buffer_volume.get())/1000, self.oil_refill_flowrate.get()))

        self.clean_only_command()

        self.queue.put((self.pump.wait_until_stopped, 120))
        self.queue.put(self.pump.infuse)
        self.queue.put((self.elveflow_display.pressureValue_var[elveflow_oil_channel - 1].set, "0"))  # Set oil pressure to 0
        self.queue.put((self.elveflow_display.start_pressure, elveflow_oil_channel))

        self.queue.put((self.python_logger.info, 'Clean and refill done. 完成了！'))
        self.queue.put(self.set_refill_flag_true)
        self.queue.put(self.play_done_soud)

    def set_refill_flag_true(self):
        """def this_this_dumb - This function is so that the flag setting is done in the queue.
        This way it if it fails the flag isn't reset"""
        self.oil_refill_flag = True

    def clean_only_command(self):
        """Clean the buffer and sample loops."""
        self.queue.put((self.python_logger.info, "Starting to clean buffer"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Low Flow Soap"))
        self.queue.put((time.sleep, self.low_soap_time.get()))

        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))
        self.queue.put((self.flowpath.valve4.set_auto_position, "High Flow Soap"))
        self.queue.put((time.sleep, self.high_soap_time.get()))

        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Water"))
        self.queue.put((time.sleep, self.water_time.get()))

        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Air"))
        self.queue.put((time.sleep, self.air_time.get()))
        self.queue.put((self.python_logger.info, "Finished cleaning buffer"))

        self.queue.put((self.python_logger.info, "Starting to clean sample"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 1))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Water"))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Low Flow Soap"))
        self.queue.put((time.sleep, self.low_soap_time.get()))

        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 1))
        self.queue.put((self.flowpath.valve4.set_auto_position, "High Flow Soap"))
        self.queue.put((time.sleep, self.high_soap_time.get()))

        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 1))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Water"))
        self.queue.put((time.sleep, self.water_time.get()))

        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 1))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Air"))
        self.queue.put((time.sleep, self.air_time.get()))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Load"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))
        self.queue.put((self.python_logger.info, "Finished cleaning sample"))

    def refill_only_command(self):
        """Refill the oil only."""
        elveflow_oil_channel = int(self.elveflow_oil_channel.get())  # throws an error if the conversion doesn't work
        elveflow_oil_pressure = self.elveflow_oil_pressure.get()

        self.queue.put((self.elveflow_display.pressureValue_var[elveflow_oil_channel - 1].set, elveflow_oil_pressure))  # Set oil pressure
        self.queue.put((self.elveflow_display.start_pressure, elveflow_oil_channel))
        self.queue.put((self.pump.refill_volume, (self.sample_volume.get()+self.first_buffer_volume.get()+self.last_buffer_volume.get())/1000, self.oil_refill_flowrate.get()))

        self.queue.put((self.pump.wait_until_stopped, 120))
        self.queue.put(self.pump.infuse)
        self.queue.put((self.elveflow_display.pressureValue_var[elveflow_oil_channel - 1].set, "0"))  # Set oil pressure to 0
        self.queue.put((self.elveflow_display.start_pressure, elveflow_oil_channel))

        self.queue.put((self.python_logger.info, "Finished refilling syringe"))

        self.oil_refill_flag = True

    def load_sample_command(self):
        self.queue.put((self.flowpath.valve4.set_auto_position, "Load"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 1))

    def load_buffer_command(self):
        self.queue.put((self.flowpath.valve4.set_auto_position, "Load"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))

    def purge_command(self):
        run_position = self.purge_running_pos.get()
        purge_position = self.purge_water_pos.get()
        if self.purge_valve.position == purge_position:
            self.manual_queue.put((self.purge_valve.switchvalve, run_position))
            self.purge_button.configure(bg="white smoke")
            self.python_logger.info("Purge stopped")
        else:
            self.manual_queue.put((self.purge_valve.switchvalve, purge_position))
            self.purge_button.configure(bg="green")
            self.python_logger.info("Purging")

    def purge_soap_command(self):
        run_position = self.purge_running_pos.get()
        purge_position = self.purge_soap_pos.get()
        if self.purge_valve.position == purge_position:
            self.manual_queue.put((self.purge_valve.switchvalve, run_position))
            self.purge_soap_button.configure(bg="white smoke")
            self.python_logger.info("Purge stopped")
        else:
            self.manual_queue.put((self.purge_valve.switchvalve, purge_position))
            self.purge_soap_button.configure(bg="green")
            self.python_logger.info("Purging soap")

    def purge_dry_command(self):
        run_position = self.purge_running_pos.get()
        purge_position = self.purge_air_pos.get()
        if self.purge_valve.position == purge_position:
            self.manual_queue.put((self.purge_valve.switchvalve, run_position))
            self.purge_dry_button.configure(bg="white smoke")
            self.python_logger.info("Purge stopped")
        else:
            self.manual_queue.put((self.purge_valve.switchvalve, purge_position))
            self.purge_dry_button.configure(bg="green")
            self.python_logger.info("Purging soap")

    def initialize_sheath_command(self):
        # TODO: make this a toggle button instead
        elveflow_sheath_channel = int(self.elveflow_sheath_channel.get())
        elveflow_sheath_volume = float(self.elveflow_sheath_volume.get())
        # TODO: graph this?
        self.manual_queue.put((self.python_logger.info, "Starting to set sheath flow to %s µL/min..." % elveflow_sheath_volume))
        self.manual_queue.put((self.elveflow_display.run_volume, elveflow_sheath_channel, elveflow_sheath_volume))
        self.manual_queue.put((self.python_logger.info, "Done setting sheath flow to %s µL/min" % elveflow_sheath_volume))

    def toggle_buttons(self):
        """Toggle certain buttons on and off when they should not be allowed to add to queue."""
        buttons = (self.buffer_sample_buffer_button,
                   self.clean_button,
                   self.load_buffer_button,
                   self.load_sample_button,
                   self.refill_only_button,
                   self.clean_only_button)
        if self.queue_busy:
            for button in buttons:
                button['state'] = 'disabled'
        else:
            for button in buttons:
                button['state'] = 'normal'
    def play_done_soud(self):
        duration = 300
        notes = [392, 494, 587, 740, 783]
        for note in notes:
            winsound.Beep(note,duration)

    def configure_to_hardware(self, keyword, instrument_index):
        """Assign an instrument to the software version of it."""
        # TODO: Add checks for value type
        if keyword == self.hardware_config_options[0]:
            if self.instruments[instrument_index].instrument_type == "Pump":
                self.pump = self.instruments[instrument_index]
                self.python_logger.info("Pump configured to FlowPath")
            else:
                self.python_logger.info("Invalid configuration for type " + self.instruments[instrument_index].instrument_type)
        elif keyword == self.hardware_config_options[1]:
            if self.instruments[instrument_index].instrument_type == "Rheodyne":
                self.flowpath.valve2.hardware = self.instruments[instrument_index]
                self.python_logger.info("Oil valve configured to FlowPath")
            else:
                self.python_logger.info("Invalid configuration for type: " + self.instruments[instrument_index].instrument_type)
        elif keyword == self.hardware_config_options[2]:
            if self.instruments[instrument_index].instrument_type == "VICI":
                self.flowpath.valve3.hardware = self.instruments[instrument_index]
                self.python_logger.info("Sample/Buffer valve configured to FlowPath")
            else:
                self.python_logger.info("Invalid configuration for type: " + self.instruments[instrument_index].instrument_type)
        elif keyword == self.hardware_config_options[3]:
            if self.instruments[instrument_index].instrument_type == "Rheodyne":
                self.flowpath.valve4.hardware = self.instruments[instrument_index]
                self.python_logger.info("Loading valve configerd to FlowPath")
            else:
                self.python_logger.info("Invalid configuration for type: " + self.instruments[instrument_index].instrument_type)
        elif keyword == self.hardware_config_options[4]:
            if self.instruments[instrument_index].instrument_type == "Rheodyne":
                self.purge_valve = self.instruments[instrument_index]
                self.python_logger.info("Purge valve configured to FlowPath")
            else:
                self.python_logger.info("Invalid configuration for type: " + self.instruments[instrument_index].instrument_type)
        else:
            raise ValueError
        self.instruments[instrument_index].hardware_configuration = keyword

    def add_pump_set_buttons(self, address=0, name="Pump", hardware="", pc_connect = True):
        """Add pump buttons to the setup page."""
        self.instruments.append(SAXSDrivers.HPump(logger=self.python_logger, name=name, address=address, hardware_configuration=hardware, lock=self._lock, pc_connect=pc_connect))
        self.NumberofPumps += 1
        instrument_index = len(self.instruments)-1
        self.python_logger.info("Added pump")
        newvars = [tk.IntVar(value=address), tk.StringVar(value=name), tk.StringVar(value=hardware)]
        self.setup_page_variables.append(newvars)

        newbuttons = [
         COMPortSelector(self.setup_page, exportselection=0, height=4),
         tk.Button(self.setup_page, text="Set Port", command=lambda: self.instruments[instrument_index].set_port(self.AvailablePorts[int(self.setup_page_buttons[instrument_index][0].curselection()[0])].device)),
         tk.Button(self.setup_page, text="Send to Controller", command=lambda: self.instruments[instrument_index].set_to_controller(self.controller)),
         tk.Label(self.setup_page, text="   Pump Address:", bg=self.label_bg_color),
         tk.Spinbox(self.setup_page, from_=0, to=100, textvariable=self.setup_page_variables[instrument_index][0]),
         tk.Label(self.setup_page, text="   Pump Name:", bg=self.label_bg_color),
         tk.Entry(self.setup_page, textvariable=self.setup_page_variables[instrument_index][1]),
         tk.Button(self.setup_page, text="Set values", command=lambda: self.instrument_change_values(instrument_index)),
         tk.Label(self.setup_page, text="Instrument configuration", bg=self.label_bg_color),
         tk.OptionMenu(self.setup_page, self.setup_page_variables[instrument_index][2], *self.hardware_config_options),
         tk.Button(self.setup_page, text="Set", command=lambda: self.configure_to_hardware(self.setup_page_variables[instrument_index][2].get(), instrument_index))
         ]

        # Pumps share a port-> Dont need extra ones
        if self.NumberofPumps > 1:
            newbuttons[0] = tk.Label(self.setup_page, text="", bg=self.label_bg_color)
            newbuttons[1] = tk.Label(self.setup_page, text="", bg=self.label_bg_color)
            newbuttons[2] = tk.Label(self.setup_page, text="", bg=self.label_bg_color)

        self.setup_page_buttons.append(newbuttons)
        for i in range(len(self.setup_page_buttons)):
            for y in range(len(self.setup_page_buttons[i])):
                self.setup_page_buttons[i][y].grid(row=i+2, column=y)
        self.refresh_com_list()
        self.add_pump_control_buttons()
        if hardware != "":
            self.configure_to_hardware(hardware, instrument_index)

    def refresh_dropdown(self, option_menu_list, options_to_put, VariableLocation):
        # Update Values in Config Selector
        for i in range(6):
            m = option_menu_list[i].children['menu']
            m.delete(0, tk.END)
            m.add_command(label="", command=lambda var=VariableLocation[i], val="": var.set(val))  # Add option to leave empty
            for name in options_to_put:
                if not name == "":
                    m.add_command(label=name, command=lambda var=VariableLocation[i], val=name: var.set(val))

    def instrument_change_values(self, instrument_index, isvalve=False):
        self.instruments[instrument_index].change_values(int((self.setup_page_variables[instrument_index][0]).get()), (self.setup_page_variables[instrument_index][1]).get())
        self.manual_page_variables[instrument_index][0].set(self.instruments[instrument_index].name+":  ")
        if isvalve:
            self.manual_page_buttons[instrument_index][2].config(to=self.setup_page_variables[instrument_index][2].get())
        # self.refresh_dropdown()

    def add_pump_control_buttons(self):
        instrument_index = len(self.instruments)-1
        newvars = [tk.StringVar(), tk.DoubleVar(value=0), tk.DoubleVar(value=0), tk.DoubleVar(value=0)]
        newvars[0].set(self.instruments[instrument_index].name+":  ")
        self.manual_page_variables.append(newvars)
        newbuttons = [
         tk.Label(self.manual_page, textvariable=self.manual_page_variables[instrument_index][0], bg=self.label_bg_color),
         tk.Button(self.manual_page, text="Run", command=lambda: self.manual_queue.put(self.instruments[instrument_index].start_pump)),
         tk.Button(self.manual_page, text="Stop", command=lambda:self.manual_queue.put(self.instruments[instrument_index].stop_pump)),
         tk.Label(self.manual_page, text="  Infuse Rate:", bg=self.label_bg_color),
         tk.Spinbox(self.manual_page, from_=0, to=1000, textvariable=self.manual_page_variables[instrument_index][1]),
         tk.Button(self.manual_page, text="Set", command=lambda: self.manual_queue.put((self.instruments[instrument_index].set_infuse_rate, self.manual_page_variables[instrument_index][1].get()))),
         tk.Label(self.manual_page, text="  Refill Rate:", bg=self.label_bg_color),
         tk.Spinbox(self.manual_page, from_=0, to=1000, textvariable=self.manual_page_variables[instrument_index][2]),
         tk.Button(self.manual_page, text="Set", command=lambda: self.manual_queue.put((self.instruments[instrument_index].set_refill_rate, self.manual_page_variables[instrument_index][2].get()))),
         tk.Label(self.manual_page, text="  Direction:", bg=self.label_bg_color),
         tk.Button(self.manual_page, text="Infuse", command=lambda: self.manual_queue.put(self.instruments[instrument_index].infuse)),
         tk.Button(self.manual_page, text="Refill", command=lambda: self.manual_queue.put(self.instruments[instrument_index].refill)),
         tk.Label(self.manual_page, text="Mode", bg=self.label_bg_color),
         tk.Button(self.manual_page, text="Pump", command=lambda: self.manual_queue.put(self.instruments[instrument_index].set_mode_pump)),
         tk.Button(self.manual_page, text="Vol", command=lambda: self.manual_queue.put(self.instruments[instrument_index].set_mode_vol)),
         tk.Label(self.manual_page, text="  Target Vol (ml):", bg=self.label_bg_color),
         tk.Spinbox(self.manual_page, from_=0, to=1000, textvariable=self.manual_page_variables[instrument_index][3]),
         # tk.Button(self.manual_page, text="Set", command=lambda: self.queue.put((self.instruments[instrument_index].set_target_vol, self.manual_page_variables[instrument_index][3].get())))
         tk.Button(self.manual_page, text="Set", command=lambda: self.manual_queue.put((self.instruments[instrument_index].set_target_vol, self.manual_page_variables[instrument_index][3].get())))
         ]
        # Bind Enter to Spinboxes
        newbuttons[4].bind('<Return>', lambda event: self.manual_queue.put((self.instruments[instrument_index].set_infuse_rate, self.manual_page_variables[instrument_index][1].get())))
        newbuttons[7].bind('<Return>', lambda event: self.manual_queue.put((self.instruments[instrument_index].set_refill_rate, self.manual_page_variables[instrument_index][2].get())))
        newbuttons[16].bind('<Return>', lambda event: self.manual_queue.put((self.instruments[instrument_index].set_target_vol, self.manual_page_variables[instrument_index][3].get())))
        self.manual_page_buttons.append(newbuttons)
        # Build Pump
        for i in range(len(self.manual_page_buttons)):
            for y in range(len(self.manual_page_buttons[i])):
                self.manual_page_buttons[i][y].grid(row=i, column=y)

    def refresh_com_list(self):
        self.ControllerCOM.updatelist(SAXSDrivers.list_available_ports(self.AvailablePorts))
        for button in self.setup_page_buttons:
            if isinstance(button[0], COMPortSelector):
                button[0].updatelist(SAXSDrivers.list_available_ports(self.AvailablePorts))

    def add_rheodyne_set_buttons(self, address=-1, name="Rheodyne", hardware="", pc_connect=True):
        self.instruments.append(SAXSDrivers.Rheodyne(logger=self.python_logger, address_I2C=address, name=name, hardware_configuration=hardware, lock=self._lock, pc_connect=pc_connect))
        instrument_index = len(self.instruments)-1
        newvars = [tk.IntVar(value=address), tk.StringVar(value=name), tk.IntVar(value=2), tk.StringVar(value=hardware)]
        self.setup_page_variables.append(newvars)
        self.python_logger.info("Added Rheodyne")
        newbuttons = [
         COMPortSelector(self.setup_page, exportselection=0, height=4),
         tk.Button(self.setup_page, text="Set Port", command=lambda: self.instruments[instrument_index].set_port(self.AvailablePorts[int(self.setup_page_buttons[instrument_index][0].curselection()[0])].device)),
         tk.Button(self.setup_page, text="Send to Controller", command=lambda: self.instruments[instrument_index].set_to_controller(self.controller)),
         tk.Label(self.setup_page, text="   Type:", bg=self.label_bg_color),
         tk.Spinbox(self.setup_page, values=(2, 6), textvariable=self.setup_page_variables[instrument_index][2]),
         tk.Label(self.setup_page, text="   I2C Address:", bg=self.label_bg_color),
         tk.Spinbox(self.setup_page, from_=-1, to=100, textvariable=self.setup_page_variables[instrument_index][0]),
         tk.Label(self.setup_page, text="   Valve Name:", bg=self.label_bg_color),
         tk.Entry(self.setup_page, textvariable=self.setup_page_variables[instrument_index][1]),
         tk.Button(self.setup_page, text="Set values", command=lambda: self.instrument_change_values(instrument_index, True)),
         tk.OptionMenu(self.setup_page, self.setup_page_variables[instrument_index][3], *self.hardware_config_options),
         tk.Button(self.setup_page, text="Set", command=lambda: self.configure_to_hardware(self.setup_page_variables[instrument_index][3].get(), instrument_index))
         ]
        self.setup_page_buttons.append(newbuttons)
        for i in range(len(self.setup_page_buttons)):
            for y in range(len(self.setup_page_buttons[i])):
                self.setup_page_buttons[i][y].grid(row=i+2, column=y)
        self.AddRheodyneControlButtons()
        self.refresh_com_list()
        if hardware != "":
            self.configure_to_hardware(hardware, instrument_index)
        # self.refresh_dropdown()

    def AddRheodyneControlButtons(self):
        instrument_index = len(self.instruments)-1
        newvars = [tk.StringVar(), tk.IntVar(value=0)]
        newvars[0].set(self.instruments[instrument_index].name+":  ")
        self.manual_page_variables.append(newvars)

        newbuttons = [
         tk.Label(self.manual_page, textvariable=self.manual_page_variables[instrument_index][0], bg=self.label_bg_color),
         tk.Label(self.manual_page, text="   Position:", bg=self.label_bg_color),
         tk.Spinbox(self.manual_page, from_=1, to=self.setup_page_variables[instrument_index][2].get(), textvariable=self.manual_page_variables[instrument_index][1]),
         tk.Button(self.manual_page, text="Change", command=lambda: self.manual_queue.put((self.instruments[instrument_index].switchvalve, self.manual_page_variables[instrument_index][1].get()))),
         ]
        newbuttons[2].bind('<Return>', lambda event: self.manual_queue.put((self.instruments[instrument_index].switchvalve, self.manual_page_variables[instrument_index][1].get())))
        self.manual_page_buttons.append(newbuttons)
        # Place buttons
        for i in range(len(self.manual_page_buttons)):
            for y in range(len(self.manual_page_buttons[i])):
                self.manual_page_buttons[i][y].grid(row=i, column=y)

    def AddVICISetButtons(self, name="VICI", hardware="", pc_connect=True):
        self.instruments.append(SAXSDrivers.VICI(logger=self.python_logger, name=name, hardware_configuration=hardware, lock=self._lock, pc_connect=pc_connect))
        instrument_index = len(self.instruments)-1
        newvars = [tk.IntVar(value=-1), tk.StringVar(value=name), tk.StringVar(value=hardware)]
        self.setup_page_variables.append(newvars)
        self.python_logger.info("Added VICI Valve")
        newbuttons = [
         COMPortSelector(self.setup_page, exportselection=0, height=4),
         tk.Button(self.setup_page, text="Set Port", command=lambda: self.instruments[instrument_index].set_port(self.AvailablePorts[int(self.setup_page_buttons[instrument_index][0].curselection()[0])].device)),
         tk.Button(self.setup_page, text="Send to Controller", command=lambda:self.instruments[instrument_index].set_to_controller(self.controller)),
         tk.Label(self.setup_page, text="   Valve Name:", bg=self.label_bg_color),
         tk.Entry(self.setup_page, textvariable=self.setup_page_variables[instrument_index][1]),
         tk.Button(self.setup_page, text="Set values", command=lambda: self.instrument_change_values(instrument_index, False)),
         tk.OptionMenu(self.setup_page, self.setup_page_variables[instrument_index][2], *self.hardware_config_options),
         tk.Button(self.setup_page, text="Set", command=lambda: self.configure_to_hardware(self.setup_page_variables[instrument_index][2].get(), instrument_index))
         ]
        self.setup_page_buttons.append(newbuttons)
        for i in range(len(self.setup_page_buttons)):
            for y in range(len(self.setup_page_buttons[i])):
                self.setup_page_buttons[i][y].grid(row=i+2, column=y)
        self.AddVICIControlButtons()
        self.refresh_com_list()
        if hardware != "":
            self.configure_to_hardware(hardware, instrument_index)

    def AddVICIControlButtons(self):
        instrument_index = len(self.instruments)-1
        newvars = [tk.StringVar(), tk.StringVar(value="A")]
        newvars[0].set(self.instruments[instrument_index].name+":  ")
        self.manual_page_variables.append(newvars)

        newbuttons = [
         tk.Label(self.manual_page, textvariable=self.manual_page_variables[instrument_index][0], bg=self.label_bg_color),
         tk.Label(self.manual_page, text="   Position:", bg=self.label_bg_color),
         tk.Spinbox(self.manual_page, values=("A", "B"), textvariable=self.manual_page_variables[instrument_index][1]),
         tk.Button(self.manual_page, text="Change", command=lambda: self.manual_queue.put((self.instruments[instrument_index].switchvalve, self.manual_page_variables[instrument_index][1].get()))),
         ]
        newbuttons[2].bind('<Return>', lambda event: self.manual_queue.put((self.instruments[instrument_index].switchvalve, self.manual_page_variables[instrument_index][1].get())))
        self.manual_page_buttons.append(newbuttons)
        # Place buttons
        for i in range(len(self.manual_page_buttons)):
            for y in range(len(self.manual_page_buttons[i])):
                self.manual_page_buttons[i][y].grid(row=i, column=y)

    def ChangeDirectory(self):
        BaseDirectory = self.spec_base_directory.get()
        SubDirectory = self.spec_sub_directory.get()

        for eachChar in SubDirectory:
            if eachChar in self.illegal_chars:
                tk.messagebox.showinfo("Error", 'Directory name contains invalid characters. \nThese include: %s (includes spaces).' % (self.illegal_chars), 'Invalid Input')
                return (False)

        if '//' in SubDirectory:
            tk.messagebox.showinfo("Error", 'Directory path is invalid. Please check path. \nHint: subdirectory name contains "//".', 'Invalid Input')
            return (False)

        if SubDirectory != "":
            if SubDirectory[0] == '/':
                SubDirectory = SubDirectory[1:]
            if SubDirectory[-1] == '/':
                SubDirectory = SubDirectory[:-1]
        if BaseDirectory != "":
            if BaseDirectory[-1] != '/':
                BaseDirectory = BaseDirectory+'/'

        Directory = os.path.join(BaseDirectory, SubDirectory)

        OldDirectory = os.path.join(self.old_base_directory, self.old_sub_directory)

        if OldDirectory != Directory:
            # self.SetStatus('Changing Directory . . .')
            # print 'Directory test:'
            # print OldDirectory
            # print Directory
            if OldDirectory[-1] != '/':
                OldDirectory = OldDirectory+'/'
            if Directory[-1] != '/':
                Directory = Directory+'/'

            od_parts = OldDirectory.split('/')
            nd_parts = Directory.split('/')

            index = 0
            check = min(len(od_parts), len(nd_parts))
            found = False

            for a in range(check):
                if od_parts[a] != nd_parts[a]:
                    index = a
                    found = True
                    break
            if not found:
                index = check

            cmd = ''
            for a in range(index+1, len(nd_parts)):
                self.adxIsDone = False
                tdirectory = '/'.join(nd_parts[:a])
                if a < len(nd_parts)-1:
                    cmd = cmd + 'MKDIR_NO ' + str(tdirectory)+','
                else:
                    cmd = cmd + 'MKDIR ' + str(tdirectory)

            solocomm.controlQueue.put([('A', cmd)])

            self.main_window.after(1000, self.on_mkdir_timer)

        self.old_base_directory = BaseDirectory
        self.old_sub_directory = SubDirectory

        return (True, Directory)

    def on_mkdir_timer(self):
        """After making a new spec directory.

        Don't think this is needed, but would be useful for feedback later if we want.
        """
        if self.adxIsDone:
            if not self.exposing:
                solocomm.controlQueue.put([('G', 'ADXDONE_OK')])
        pass

    def run_tseries(self, postfix=None):
        """Run a tseries."""
        # Input Sanitation
        try:
            number_of_frames = self.tseries_frames.get()
            exposure_time = self.tseries_time.get()
            file_number = self.spec_fileno.get()

            if number_of_frames < 1 or file_number < 0:
                raise ValueError

        except ValueError:
            tk.messagebox.showinfo('Error', 'Exposure time, number of frames or filenumber is invalid.', 'Invalid Input')
            return

        filename = self.spec_filename.get().strip()

        for eachChar in filename:
            if eachChar in self.illegal_chars:
                tk.messagebox.showinfo('Error', 'Filename contains invalid characters. \nThese include: %s (includes spaces).' % (self.illegal_chars), 'Invalid Input')
                return

        if filename == '':
            tk.messagebox.showinfo('Error', 'File must have a name.', 'Invalid Input')
            return

        changedir, directory = self.Changedirectory()

        if changedir:
            self.exposing = True
            file_number = file_number = self.spec_fileno.get()

            new_dark = '0'

            print(('A EXPOSE '+filename + '_' + file_number + ',' + str(exposure_time) + ',' + str(number_of_frames)))

            file = filename
            file += '_' + file_number
            if postfix is not None:
                file += '_' + postfix

            solocomm.controlQueue.put([('A', 'EXPOSE ' + file + ',' +
                                        str(exposure_time) + ',' + str(number_of_frames) +
                                        ',' + str(directory) + ',' + str(new_dark))])

            self.spec_fileno.delete(0, 'end')
            self.spec_fileno.insert(0, file_number+1)


if __name__ == "__main__":
    window = tk.Tk()
    Main(window)
    window.mainloop()
    print("Main window now destroyed. Exiting.")
