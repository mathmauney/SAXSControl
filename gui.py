"""This script creates the SAXS control GUI.

Pollack Lab-Cornell
Alex Mauney
"""


import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog
from widgets import FluidLevel, FlowPath, ElveflowDisplay, TextHandler, MiscLogger, COMPortSelector, ConsoleUi
import tkinter.ttk as ttk
import time
import SPEC
import FileIO
from configparser import ConfigParser
import logging
import threading
import SAXSDrivers
import os.path
import csv
import solocomm
import numpy as np
import warnings
import matplotlib
from matplotlib import pyplot as plt
matplotlib.use('TkAgg')
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

        self.main_window = window
        self.main_window.report_callback_exception = self.handle_exception
        self.main_window.title('Main Window')
        self.adxIsDone = False
        self.illegalChars = '!@#$%^&*()."\\|:;<>?=~ ' + "'"
        self.OldBaseDirectory = '/mnt/currentdaq/BioSAXS/'
        self.OldSubDirectory = ''
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

        # Button Bar
        self.buttons = tk.Frame(self.main_window)
        self.exit_button = tk.Button(self.main_window, text='X', command=self.exit_)
        self.stop_button = tk.Button(self.main_window, text='STOP', command=self.stop, fg='red', font='Arial 16 bold')

        # Main Structures
        self.core = ttk.Notebook(self.main_window, width=core_width, height=core_height)
        self.auto_page = tk.Frame(self.core)
        self.config_page = tk.Frame(self.core)
        self.manual_page = tk.Frame(self.core)
        self.setup_page = tk.Frame(self.core)
        self.elveflow_page = tk.Frame(self.core)
        self.logs = ttk.Notebook(self.main_window, width=log_width, height=log_height)
        self.python_logs = tk.Frame(self.logs)
        self.Instrument_logs = tk.Frame(self.logs)
        self.state_frame = tk.Frame(self.main_window, width=window_width, height=state_height, bg='blue')
        # Widgets on Main page
        self.spec_base_directory_label = tk.Label(self.auto_page, text='Spec Base Directory:')
        self.spec_base_directory = tk.StringVar(value='')
        self.spec_base_directory_box = tk.Entry(self.auto_page, textvariable=self.spec_base_directory)
        self.spec_sub_directory_label = tk.Label(self.auto_page, text='Spec Subdirectory:')
        self.spec_sub_directory = tk.StringVar(value='')
        self.spec_sub_directory_box = tk.Entry(self.auto_page, textvariable=self.spec_sub_directory)
        self.spec_directory_button = tk.Button(self.auto_page, text='Change/Make Directory', command=self.ChangeDirectory)
        self.spec_filename_label = tk.Label(self.auto_page, text='Filename:')
        self.spec_filename = tk.StringVar(value='')
        self.spec_filename_box = tk.Entry(self.auto_page, textvariable=self.spec_filename)
        self.spec_fileno_label = tk.Label(self.auto_page, text='File #:')
        self.spec_fileno = tk.IntVar(value=0)
        self.spec_fileno_box = tk.Entry(self.auto_page, textvariable=self.spec_fileno)
        self.buffer_sample_buffer_button = tk.Button(self.auto_page, text='Run Buffer/Sample/Buffer', command=self.buffer_sample_buffer_command)
        self.clean_button = tk.Button(self.auto_page, text='Clean/Refill', command=self.clean_and_refill_command)
        self.load_button = tk.Button(self.auto_page, text='Load Position', command=self.load_command)
        self.clean_only_button = tk.Button(self.auto_page, text='Clean Only', command=self.clean_only_command)
        #self.clean_only_button = tk.Button(self.auto_page, text='Clean Only', commmand=self.clean_only_command)
        self.refill_only_button = tk.Button(self.auto_page, text='Refill Only', command=self.refill_only_command)

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
        self.config_spec_address_label = tk.Label(self.config_page, text='SPEC Address')
        self.spec_connect_button = tk.Button(self.config_page, text='Connect to SPEC', command=self.connect_to_spec)
        self.volumes_label = tk.Label(self.config_page, text='Buffer/Sample/Buffer volumes in uL:')
        self.first_buffer_volume = tk.IntVar(value=25)     # May need ot be a doublevar
        self.first_buffer_volume_box = tk.Entry(self.config_page, textvariable=self.first_buffer_volume)
        self.sample_volume = tk.IntVar(value=25)           # May need ot be a doublevar
        self.sample_volume_box = tk.Entry(self.config_page, textvariable=self.sample_volume)
        self.last_buffer_volume = tk.IntVar(value=25)      # May need ot be a doublevar
        self.last_buffer_volume_box = tk.Entry(self.config_page, textvariable=self.last_buffer_volume)
        self.sample_flowrate_label = tk.Label(self.config_page, text="Sample-Buffer Infuse flowrate (ul/min)")
        self.sample_flowrate = tk.DoubleVar(value=10)
        self.sample_flowrate_box = tk.Entry(self.config_page, textvariable=self.sample_flowrate)
        self.oil_refill_flowrate_label = tk.Label(self.config_page, text="Oil refill rate (ul/min)")
        self.oil_refill_flowrate = tk.DoubleVar(value=10)
        self.oil_refill_flowrate_box = tk.Entry(self.config_page, textvariable=self.oil_refill_flowrate)
        self.oil_valve_names_label = tk.Label(self.config_page, text='Oil Valve Hardware Port Names')
        self.oil_valve_names = []
        self.oil_valve_name_boxes = []
        self.set_oil_valve_names_button = tk.Button(self.config_page, text='Set Names', command=self.set_oil_valve_names)
        self.loading_valve_names_label = tk.Label(self.config_page, text='Loading Valve Hardware Port Names')
        self.loading_valve_names = []
        self.loading_valve_name_boxes = []
        self.set_loading_valve_names_button = tk.Button(self.config_page, text='Set Names', command=self.set_loading_valve_names)
        self.tseries_time = tk.IntVar(value=0)
        self.tseries_time_box = tk.Entry(self.config_page, textvariable=self.tseries_time)
        self.tseries_frames = tk.IntVar(value=0)
        self.tseries_frames_box = tk.Entry(self.config_page, textvariable=self.tseries_frames)
        self.tseries_label = tk.Label(self.config_page, text='tseries parameters:')
        for i in range(6):
            self.oil_valve_names.append(tk.StringVar(value=''))
            self.oil_valve_name_boxes.append(tk.OptionMenu(self.config_page, self.oil_valve_names[i], ""))
            self.loading_valve_names.append(tk.StringVar(value=''))
            self.loading_valve_name_boxes.append(tk.OptionMenu(self.config_page, self.loading_valve_names[i], ""))
        self.elveflow_sourcename = tk.StringVar()
        self.low_soap_time_label = tk.Label(self.config_page, text="Low soap time:")
        self.low_soap_time = tk.IntVar(value=0)
        self.low_soap_time_box = tk.Spinbox(self.config_page, from_=0, to=1000, textvariable=self.low_soap_time)
        self.high_soap_time_label = tk.Label(self.config_page, text="High soap time:")
        self.high_soap_time = tk.IntVar(value=0)
        self.high_soap_time_box = tk.Spinbox(self.config_page, from_=0, to=1000, textvariable=self.high_soap_time)
        self.water_time_label = tk.Label(self.config_page, text="Water time:")
        self.water_time = tk.IntVar(value=0)
        self.water_time_box = tk.Spinbox(self.config_page, from_=0, to=1000, textvariable=self.water_time)
        self.air_time_label = tk.Label(self.config_page, text="Air time:")
        self.air_time = tk.IntVar(value=0)
        self.air_time_box = tk.Spinbox(self.config_page, from_=0, to=1000, textvariable=self.air_time)

        def _set_elveflow_sourcename(*args):
            self.config['Elveflow']['elveflow_sourcename'] = self.elveflow_sourcename.get()
        self.elveflow_sourcename.trace('w', _set_elveflow_sourcename)
        self.elveflow_sourcename_label = tk.Label(self.config_page, text='Elveflow sourcename')
        self.elveflow_sourcename_box = tk.Entry(self.config_page, textvariable=self.elveflow_sourcename)
        self.elveflow_sensortypes_label = tk.Label(self.config_page, text='Elveflow sensor types')
        self.elveflow_sensortypes = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.elveflow_sensortypes_optionmenu = [None, None, None, None]
        for i in range(4):
            self.elveflow_sensortypes_optionmenu[i] = tk.OptionMenu(self.config_page, self.elveflow_sensortypes[i], None)
            self.elveflow_sensortypes_optionmenu[i]['menu'].delete(0, 'end')  # there's a default empty option, so get rid of that first
            for item in FileIO.SDK_SENSOR_TYPES:
                def _set_elveflow_sensor(i=i, item=item):
                    # weird default argument for scoping; not sure if it's needed but whatever, it works; don't touch it
                    print("GYAAA SETTING CHANNEL %i to %s" % (i+1, item))
                    self.elveflow_sensortypes[i].set(item)
                    self.config['Elveflow']['sensor%d_type' % (i+1)] = item
                self.elveflow_sensortypes_optionmenu[i]['menu'].add_command(label=item, command=_set_elveflow_sensor)
        self.elveflow_oil_channel_pressure_label = tk.Label(self.config_page, text='Elveflow oil channel, pressure [mbar]')
        self.elveflow_oil_channel = tk.StringVar()
        self.elveflow_oil_pressure = tk.StringVar()
        self.elveflow_oil_channel_box = tk.Entry(self.config_page, textvariable=self.elveflow_oil_channel)
        self.elveflow_oil_pressure_box = tk.Entry(self.config_page, textvariable=self.elveflow_oil_pressure)

        # Make Instrument
        self.AvailablePorts = SAXSDrivers.list_available_ports()
        self.controller = SAXSDrivers.SAXSController(timeout=0.1)
        self.Instruments = []
        self.pump = None
        self.NumberofPumps = 0
        # Setup Page
        self.hardware_config_options = ("Pump", "Oil Valve", "Sample/Buffer Valve", "Loading Valve")
        self.AvailablePorts = SAXSDrivers.list_available_ports()
        self.setup_page_buttons = []
        self.setup_page_variables = []
        self.refresh_com_ports = tk.Button(self.setup_page, text="Refresh COM", command=lambda: self.RefreshCOMList())
        self.AddPump = tk.Button(self.setup_page, text="Add Pump", command=lambda: self.add_pump_set_buttons())
        self.AddRheodyne = tk.Button(self.setup_page, text="Add Rheodyne", command=lambda: self.AddRheodyneSetButtons())
        self.AddVICI = tk.Button(self.setup_page, text="Add VICI Valve", command=lambda: self.AddVICISetButtons())
        self.ControllerCOM = COMPortSelector(self.setup_page, exportselection=0, height=3)
        self.ControllerSet = tk.Button(self.setup_page, text="Set Microntroller", command=lambda: self.controller.set_port(self.AvailablePorts[int(self.ControllerCOM.curselection()[0])].device))
        self.I2CScanButton = tk.Button(self.setup_page, text="Scan I2C line", command=lambda: self.controller.scan_i2c())

        # logs
        log_length = 39  # in lines
        self.python_logger_gui = ConsoleUi(self.python_logs)
        #self.python_logger_gui = ScrolledText(self.python_logs, state='disabled', height=log_length)
        #self.python_logger_gui.configure(font='TkFixedFont')
        self.Instrument_logger = MiscLogger(self.Instrument_logs, state='disabled', height=log_length)
        self.Instrument_logger.configure(font='TkFixedFont')
        self.controller.logger = self.Instrument_logger
        #
        # Flow setup frames
        self.load_config(filename='config.ini', preload=True)
        if self.sucrose:
            self.flowpath = FlowPath(self.state_frame, self, sucrose=True)
        else:
            self.flowpath = FlowPath(self.state_frame, self)
        time.sleep(0.6)   # I have no idea why we need this but everything crashes and burns if we don't include it
        # It acts as though there's a race condition, but aren't we still single-threaded at this point?
        # I suspect something might be going wrong with the libraries, then, especially tkinter and matplotlib
        self.RefreshDropdown(self.oil_valve_name_boxes, self.flowpath.valve2.gui_names, self.oil_valve_names)
        self.RefreshDropdown(self.loading_valve_name_boxes, self.flowpath.valve4.gui_names, self.loading_valve_names)
        self.draw_static()
        self.elveflow_display = ElveflowDisplay(self.elveflow_page, core_height, core_width, self.config['Elveflow'], self.python_logger)
        self.elveflow_display.grid(row=0, column=0)
        self.queue = solocomm.controlQueue
        self.queue_busy = False
        self.listen_run_flag = threading.Event()
        self.listen_run_flag.set()
        # self.listen_thread = threading.Thread(target=self.listen)
        # self.listen_thread.start()
        self.load_config(filename='config.ini')
        self.connect_to_spec()
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
        self.logs.add(self.python_logs, text='Python')
        self.logs.add(self.Instrument_logs, text='Instruments')
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
        self.buffer_sample_buffer_button.grid(row=5, column=0)
        self.load_button.grid(row=5, column=1)
        self.clean_button.grid(row=6, column=0)
        self.clean_only_button.grid(row=6, column=1)
        self.refill_only_button.grid(row=6, column=2)
        self.canvas.get_tk_widget().grid(row=0, column=2, rowspan=6, columnspan=8, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        # Manual page
        # Config page
        rowcounter = 0
        self.save_config_button.grid(row=rowcounter, column=0)
        self.load_config_button.grid(row=rowcounter, column=1)
        rowcounter += 1
        rowcounter += 1 # not sure why we do this twice, but we do
        self.config_spec_address_label.grid(row=rowcounter, column=0)
        self.config_spec_address.grid(row=rowcounter, column=1)
        self.spec_connect_button.grid(row=rowcounter, column=2)
        rowcounter += 1
        rowcounter += 1 # not sure why we do this twice, but we do
        self.volumes_label.grid(row=rowcounter, column=0)
        self.first_buffer_volume_box.grid(row=rowcounter, column=1)
        self.sample_volume_box.grid(row=rowcounter, column=2)
        self.last_buffer_volume_box.grid(row=rowcounter, column=3)
        rowcounter += 1
        self.sample_flowrate_label.grid(row=rowcounter, column=0)
        self.sample_flowrate_box.grid(row=rowcounter, column=1)
        self.oil_refill_flowrate_label.grid(row=rowcounter, column=2)
        self.oil_refill_flowrate_box.grid(row=rowcounter, column=3)
        rowcounter += 1
        self.oil_valve_names_label.grid(row=rowcounter, column=0)
        self.set_oil_valve_names_button.grid(row=rowcounter, column=7)
        for i in range(6):
            self.oil_valve_name_boxes[i].grid(row=rowcounter, column=i+1)
        rowcounter += 1
        self.loading_valve_names_label.grid(row=rowcounter, column=0)
        self.set_loading_valve_names_button.grid(row=rowcounter, column=7)
        for i in range(6):
            self.loading_valve_name_boxes[i].grid(row=rowcounter, column=i+1)
        rowcounter += 2
        self.elveflow_sourcename_label.grid(row=rowcounter, column=0)
        self.elveflow_sourcename_box.grid(row=rowcounter, column=1)
        rowcounter += 1
        self.elveflow_sensortypes_label.grid(row=rowcounter, column=0)
        for i in range(4):
            self.elveflow_sensortypes_optionmenu[i].grid(row=rowcounter, column=i+1)
        rowcounter += 1
        self.elveflow_oil_channel_pressure_label.grid(row=rowcounter, column=0)
        self.elveflow_oil_channel_box.grid(row=rowcounter, column=1)
        self.elveflow_oil_pressure_box.grid(row=rowcounter, column=2)
        rowcounter += 1
        self.tseries_label.grid(row=rowcounter, column=0)
        self.tseries_time_box.grid(row=rowcounter, column=1)
        self.tseries_frames_box.grid(row=rowcounter, column=2)
        rowcounter += 1
        self.low_soap_time_label.grid(row=rowcounter, column=0)
        self.low_soap_time_box.grid(row=rowcounter, column=1)
        self.high_soap_time_label.grid(row=rowcounter, column=2)
        self.high_soap_time_box.grid(row=rowcounter, column=3)
        self.water_time_label.grid(row=rowcounter, column=4)
        self.water_time_box.grid(row=rowcounter, column=5)
        self.air_time_label.grid(row=rowcounter, column=6)
        self.air_time_box.grid(row=rowcounter, column=7)
        # Setup page
        self.refresh_com_ports.grid(row=0, column=0)
        self.AddPump.grid(row=0, column=2)
        self.AddRheodyne.grid(row=0, column=3)
        self.AddVICI.grid(row=0, column=4)
        self.ControllerCOM.grid(row=1, column=0)
        self.ControllerSet.grid(row=1, column=2)
        self.I2CScanButton.grid(row=1, column=3)
        self.RefreshCOMList()
        # FlowPath
        self.flowpath.grid(row=0, column=0)
        # Python Log
        # self.python_logger_gui.grid(row=0, column=0, sticky='NSEW')
        nowtime = time.time()
        # python_handler = TextHandler(self.python_logger_gui)
        file_handler = logging.FileHandler(os.path.join(LOG_FOLDER, "log%010d.txt" % nowtime), encoding='utf-8')
        # python_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        # python_handler.setLevel(logging.DEBUG)
        file_handler.setLevel(logging.DEBUG)
        # SPEC Log
        self.Instrument_logger.grid(row=0, column=0, sticky='NSEW')
        # logging.basicConfig(level=logging.INFO,
        #                     format='%(asctime)s - %(levelname)s - %(message)s')
        self.python_logger = logging.getLogger("python")
        self.python_logger.setLevel(logging.DEBUG)
        # self.python_logger.addHandler(python_handler)  # logging to the screen
        self.python_logger_gui.pass_logger(self.python_logger)
        self.python_logger.addHandler(file_handler)  # logging to a file

    def stop(self):
        """Stop all running widgets."""
        with self.queue.mutex:
            self.queue.queue.clear()
        SAXSDrivers.InstrumentTerminateFunction(self.Instruments)
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
            oil_config = self.config['Oil Valve']
            loading_config = self.config['Loading Valve']
            main_config = self.config['Main']
            elveflow_config = self.config['Elveflow']
            spec_config = self.config['SPEC']
            self.spec_sub_directory_box.delete(0, 'end')
            self.spec_sub_directory_box.insert(0, spec_config.get('sub_dir', self.OldSubDirectory))
            self.OldSubDirectory = self.spec_sub_directory.get()
            self.spec_base_directory_box.delete(0, 'end')
            self.spec_base_directory_box.insert(0, spec_config.get('base_dir', self.OldBaseDirectory))
            self.OldBaseDirectory = self.spec_base_directory.get()
            self.sucrose = main_config.getboolean('Sucrose', False)
            self.config_spec_address.delete(0, 'end')
            self.config_spec_address.insert(0, main_config.get('spec_host', ''))
            self.tseries_time_box.delete(0, 'end')
            self.tseries_time_box.insert(0, main_config.get('tseries_time', '10'))
            self.tseries_frames_box.delete(0, 'end')
            self.tseries_frames_box.insert(0, main_config.get('tseries_frames', '10'))
            oil_vars = []
            loading_vars = []
            for i in range(0, 6):
                field = 'name'+str(i+1)
                self.oil_valve_names[i].set(oil_config.get(field, ''))
                self.loading_valve_names[i].set(loading_config.get(field, ''))
            self.elveflow_sourcename.set(elveflow_config['elveflow_sourcename'])
            self.elveflow_sensortypes[0].set(elveflow_config['sensor1_type'])
            self.elveflow_sensortypes[1].set(elveflow_config['sensor2_type'])
            self.elveflow_sensortypes[2].set(elveflow_config['sensor3_type'])
            self.elveflow_sensortypes[3].set(elveflow_config['sensor4_type'])
            self.elveflow_oil_channel.set(elveflow_config['elveflow_oil_channel'])
            self.elveflow_oil_pressure.set(elveflow_config['elveflow_oil_pressure'])
        if not preload:
            self.set_oil_valve_names()
            self.set_loading_valve_names()

    def save_config(self):
        """Save a config.ini file."""
        filename = filedialog.asksaveasfilename(initialdir=".", title="Select file", filetypes=(("config files", "*.ini"), ("all files", "*.*")))
        if filename != '':
            oil_config = self.config['Oil Valve']
            loading_config = self.config['Loading Valve']
            elveflow_config = self.config['Elveflow']
            spec_config = self.config['SPEC']

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
        if self.elveflow_display.run_flag.is_set():
            self.elveflow_display.stop(shutdown=True)
        # if self.SPEC_Connection.run_flag.is_set():
        #    self.SPEC_Connection.stop()
        if self.listen_run_flag.is_set():
            self.listen_run_flag.clear()
        self.main_window.destroy()

    def update_graph(self):
        """look into self's ElveflowDisplay and reproduce it on self.main_tab_fig"""

        self.main_tab_ax1.set_title("Elveflow readout for most recent scan", fontsize=16)
        dataXLabel_var = self.elveflow_display.dataXLabel_var.get()
        dataY1Label_var = self.elveflow_display.dataY1Label_var.get()
        dataY2Label_var = self.elveflow_display.dataY2Label_var.get()
        self.main_tab_ax1.set_xlabel(dataXLabel_var, fontsize=14)
        self.main_tab_ax1.set_ylabel(dataY1Label_var, fontsize=14, color=ElveflowDisplay.COLOR_Y1)
        self.main_tab_ax2.set_ylabel(dataY2Label_var, fontsize=14, color=ElveflowDisplay.COLOR_Y2)
        try:
            dataX = np.array([elt[dataXLabel_var] for elt in self.elveflow_display.data])
            dataY1 = np.array([elt[dataY1Label_var] for elt in self.elveflow_display.data])
            dataY2 = np.array([elt[dataY2Label_var] for elt in self.elveflow_display.data])

            # self.python_logger.info("Current time %s, end time %s" % (int(time.time() - self.elveflow_display.starttime), self.graph_end_time))
            dataX_viable = (dataX >= self.graph_start_time) # & (dataX < self.graph_end_time)
            dataX = dataX[dataX_viable]
            dataY1 = dataY1[dataX_viable]
            dataY2 = dataY2[dataX_viable]

            if dataXLabel_var == self.elveflow_display.elveflow_handler.header[0]:
                dataX -= self.elveflow_display.starttime
            if dataY1Label_var == self.elveflow_display.elveflow_handler.header[0]:
                dataY1 -= self.elveflow_display.starttime
            if dataY2Label_var == self.elveflow_display.elveflow_handler.header[0]:
                dataY2 -= self.elveflow_display.starttime

            extremes = [np.nanmin(dataX), np.nanmax(dataX), np.nanmin(dataY1), np.nanmax(dataY1), np.nanmin(dataY2), np.nanmax(dataY2)]
            if len(dataX) > 0:
                self.the_line1.set_data(dataX, dataY1)
                self.the_line2.set_data(dataX, dataY2)
        except (ValueError, KeyError):
            extremes = [*self.main_tab_ax1.get_xlim(), *self.main_tab_ax1.get_ylim(), *self.main_tab_ax2.get_ylim()]
        limits = [item if item is not None else extremes[i]
                  for (i, item) in enumerate(self.elveflow_display.axisLimits_numbers)]
        self.main_tab_ax1.set_xlim(*extremes[0:2])
        self.main_tab_ax1.set_ylim(*limits[2:4])
        self.main_tab_ax2.set_ylim(*limits[4:6])

        self.canvas.draw() # may need the stupid hack from widgets.py

    def graph_vline(self):
        self.main_tab_ax1.axvline(int(time.time() - self.elveflow_display.starttime), color='k', linewidth=5)

    def pump_refill_command(self):
        """Do nothing. It's a dummy command."""
        self.flowpath.set_unlock_state(False)
        self.queue.put((self.elveflow_display.elveflow_handler.setPressure, 4, 100))  # Pressurize Oil with Elveflow
        #   Switch valve (may be hooked to pump)
        self.queue.put(self.pump.set_mode_vol)
        self.queue.put((time.sleep, 0.1))
        self.queue.put(self.pump.refill)    # Set pump refill params
        self.queue.put((time.sleep, 0.1))
        self.queue.put((self.pump.set_target_vol, (self.first_buffer_volume.get()+self.sample_volume.get()+self.last_buffer_volume.get())/1000))
        self.queue.put((time.sleep, 0.1))
        self.queue.put(self.pump.start_pump)     # Refill pump
        self.queue.put((time.sleep, 10))
        self.queue.put(self.pump.infuse)    # Set pump to injection mode
        #   Switch valve
        self.queue.put((self.elveflow_display.elveflow_handler.setPressure, 4, 0))  # Vent Oil
        pass

    def buffer_sample_buffer_command(self):
        """Run a buffer-sample-buffer cycle."""
        if self.elveflow_display is None or self.elveflow_display.elveflow_handler is None:
            self.python_logger.error("Elveflow connection not initialized! Please start the connection on the Elveflow tab.")
            return

        # before scheduling anything, clear the graph
        self.main_tab_ax1.clear()
        self.main_tab_ax2.clear()
        self.the_line1 = self.main_tab_ax1.plot([], [], color=ElveflowDisplay.COLOR_Y1)[0]
        self.the_line2 = self.main_tab_ax2.plot([], [], color=ElveflowDisplay.COLOR_Y2)[0]
        self.graph_start_time = int(time.time())
        self.flowpath.set_unlock_state(False)

        self.update_graph()

        self.queue.put((self.python_logger.info, "Starting to run buffer-sample-buffer"))
        self.queue.put(self.update_graph)
        self.queue.put(self.elveflow_display.start_saving)

        self.queue.put((self.python_logger.info, "Starting to run pre-buffer"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Run"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Run"))
        self.queue.put((self.pump.infuse_volume, self.first_buffer_volume.get()/1000, self.sample_flowrate.get()))
        self.queue.put((self.pump.wait_until_stopped, 2*self.first_buffer_volume.get()/self.sample_flowrate.get()*60))

        self.queue.put(self.graph_vline)
        self.queue.put(self.update_graph)
        self.queue.put((self.python_logger.info, "Starting to run sample"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Run"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 1))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Run"))
        self.queue.put((self.pump.infuse_volume, self.sample_volume.get()/1000, self.sample_flowrate.get()))
        self.queue.put((self.pump.wait_until_stopped, 2*self.sample_volume.get()/self.sample_flowrate.get()*60))

        self.queue.put(self.graph_vline)
        self.queue.put(self.update_graph)
        self.queue.put((self.python_logger.info, "Starting to run post-buffer"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Run"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 0))
        self.queue.put((self.flowpath.valve4.set_auto_position, "Run"))
        self.queue.put((self.pump.infuse_volume, self.last_buffer_volume.get()/1000, self.sample_flowrate.get()))
        self.queue.put((self.pump.wait_until_stopped, 2*self.last_buffer_volume.get()/self.sample_flowrate.get()*60))

        self.queue.put(self.elveflow_display.stop_saving)
        self.queue.put(self.update_graph)

        def update_end_time():
            self.graph_end_time = int(time.time())
        self.queue.put(update_end_time)
        self.queue.put((self.python_logger.info, "Done with running buffer-sample-buffer"))

    def clean_and_refill_command(self):
        elveflow_oil_channel = int(self.elveflow_oil_channel.get()) #throws an error if the conversion doesn't work
        elveflow_oil_pressure = self.elveflow_oil_pressure.get()

        self.queue.put((self.python_logger.info, "Starting to run clean/refill command"))
        self.flowpath.set_unlock_state(False)
        self.queue.put((self.elveflow_display.pressureValue_var[elveflow_oil_channel - 1].set, elveflow_oil_pressure))  # Set oil pressure
        self.queue.put((self.elveflow_display.start_pressure, elveflow_oil_channel))
        self.queue.put((self.pump.refill_volume, (self.sample_volume.get()+self.first_buffer_volume.get()+self.last_buffer_volume.get())/1000, self.oil_refill_flowrate.get()))

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

        self.queue.put((self.python_logger.info, "Starting to clean sample"))
        self.queue.put((self.flowpath.valve2.set_auto_position, "Waste"))
        self.queue.put((self.flowpath.valve3.set_auto_position, 1))
        self.queue.put((self.flowpath.valve4.set_auto_position,"Water"))
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
        self.queue.put((self.flowpath.valve3.set_auto_position,0))
        self.queue.put((self.pump.wait_until_stopped, 120))
        self.queue.put(self.pump.infuse)
        self.queue.put((self.elveflow_display.pressureValue_var[elveflow_oil_channel - 1].set, "0"))  # Set oil pressure to 0
        self.queue.put((self.elveflow_display.start_pressure, elveflow_oil_channel))

        self.queue.put((self.python_logger.info, 'cleaning done'))

    def clean_only_command(self):
        pass

    def refill_only_command(self):
        pass

    def load_command(self):
        pass

    def toggle_buttons(self):
        """Toggle certain buttons on and off when they should not be allowed to add to queue."""
        buttons = (self.buffer_sample_buffer_button, self.clean_button)
        if self.queue_busy:
            for button in buttons:
                button['state'] = 'disabled'
        else:
            for button in buttons:
                button['state'] = 'normal'

    def configure_to_hardware(self, keyword, InstrumentIndex):
        # TODO: Add checks for value type
        if keyword == self.hardware_config_options[0]:
            self.pump = self.Instruments[InstrumentIndex]
        elif keyword == self.hardware_config_options[1]:
            self.flowpath.valve2.hardware = self.Instruments[InstrumentIndex]
        elif keyword == self.hardware_config_options[2]:
            self.flowpath.valve3.hardware = self.Instruments[InstrumentIndex]
        elif keyword == self.hardware_config_options[3]:
            self.flowpath.valve4.hardware = self.Instruments[InstrumentIndex]
        else:
            raise ValueError

    def add_pump_set_buttons(self):
        """Add pump buttons to the setup page."""
        self.Instruments.append(SAXSDrivers.HPump(logger=self.Instrument_logger))
        self.NumberofPumps += 1
        InstrumentIndex = len(self.Instruments)-1

        newvars = [tk.IntVar(value=0), tk.StringVar(), tk.StringVar()]
        self.setup_page_variables.append(newvars)

        newbuttons = [
         COMPortSelector(self.setup_page, exportselection=0, height=4),
         tk.Button(self.setup_page, text="Set Port", command=lambda: self.Instruments[InstrumentIndex].set_port(self.AvailablePorts[int(self.setup_page_buttons[InstrumentIndex][0].curselection()[0])].device)),
         tk.Label(self.setup_page, text="or"),
         tk.Button(self.setup_page, text="Send to Controller", command=lambda: self.Instruments[InstrumentIndex].set_to_controller(self.controller)),
         tk.Label(self.setup_page, text="   Pump Address:"),
         tk.Spinbox(self.setup_page, from_=0, to=100, textvariable=self.setup_page_variables[InstrumentIndex][0]),
         tk.Label(self.setup_page, text="   Pump Name:"),
         tk.Entry(self.setup_page, textvariable=self.setup_page_variables[InstrumentIndex][1]),
         tk.Button(self.setup_page, text="Set values", command=lambda: self.InstrumentChangeValues(InstrumentIndex)),
         tk.Label(self.setup_page, text="Instrument configuration"),
         tk.OptionMenu(self.setup_page, self.setup_page_variables[InstrumentIndex][2], *self.hardware_config_options),
         tk.Button(self.setup_page, text="Set", command=lambda: self.configure_to_hardware(self.setup_page_variables[InstrumentIndex][2].get(), InstrumentIndex))
         ]

        # Pumps share a port-> Dont need extra ones
        if self.NumberofPumps > 1:
            newbuttons[0] = tk.Label(self.setup_page, text="     ")
            newbuttons[1] = tk.Label(self.setup_page, text="     ")
            newbuttons[2] = tk.Label(self.setup_page, text="     ")

        self.setup_page_buttons.append(newbuttons)
        for i in range(len(self.setup_page_buttons)):
            for y in range(len(self.setup_page_buttons[i])):
                self.setup_page_buttons[i][y].grid(row=i+2, column=y)
        self.RefreshCOMList()
        self.AddPumpControlButtons()

    def RefreshDropdown(self, OptionMenulist, OptionstoPut, VariableLocation):
        # Update Values in Config Selector
        for i in range(6):
            m = OptionMenulist[i].children['menu']
            m.delete(0, tk.END)
            m.add_command(label="", command=lambda var=VariableLocation[i], val="": var.set(val))  # Add option to leave empty
            for name in OptionstoPut:
                if not name == "":
                    m.add_command(label=name, command=lambda var=VariableLocation[i], val=name: var.set(val))

    def InstrumentChangeValues(self, InstrumentIndex, isvalve=False):
        self.Instruments[InstrumentIndex].change_values(int((self.setup_page_variables[InstrumentIndex][0]).get()), (self.setup_page_variables[InstrumentIndex][1]).get())
        self.manual_page_variables[InstrumentIndex][0].set(self.Instruments[InstrumentIndex].name+":  ")
        if isvalve:
            self.manual_page_buttons[InstrumentIndex][2].config(to=self.setup_page_variables[InstrumentIndex][2].get())
        # self.RefreshDropdown()

    def AddPumpControlButtons(self):
        InstrumentIndex = len(self.Instruments)-1
        newvars = [tk.StringVar(), tk.DoubleVar(value=0), tk.DoubleVar(value=0), tk.DoubleVar(value=0)]
        newvars[0].set(self.Instruments[InstrumentIndex].name+":  ")
        self.manual_page_variables.append(newvars)
        newbuttons = [
         tk.Label(self.manual_page, textvariable=self.manual_page_variables[InstrumentIndex][0]),
         tk.Button(self.manual_page, text="Run", command=lambda: self.queue.put(self.Instruments[InstrumentIndex].start_pump)),
         tk.Button(self.manual_page, text="Stop", command=lambda:self.queue.put(self.Instruments[InstrumentIndex].stop_pump)),
         tk.Label(self.manual_page, text="  Infuse Rate:"),
         tk.Spinbox(self.manual_page, from_=0, to=1000, textvariable=self.manual_page_variables[InstrumentIndex][1]),
         tk.Button(self.manual_page, text="Set", command=lambda: self.queue.put((self.Instruments[InstrumentIndex].set_infuse_rate, self.manual_page_variables[InstrumentIndex][1].get()))),
         tk.Label(self.manual_page, text="  Refill Rate:"),
         tk.Spinbox(self.manual_page, from_=0, to=1000, textvariable=self.manual_page_variables[InstrumentIndex][2]),
         tk.Button(self.manual_page, text="Set", command=lambda: self.queue.put((self.Instruments[InstrumentIndex].set_refill_rate, self.manual_page_variables[InstrumentIndex][2].get()))),
         tk.Label(self.manual_page, text="  Direction:"),
         tk.Button(self.manual_page, text="Infuse", command=lambda: self.queue.put(self.Instruments[InstrumentIndex].infuse)),
         tk.Button(self.manual_page, text="Refill", command=lambda: self.queue.put(self.Instruments[InstrumentIndex].refill)),
         tk.Label(self.manual_page, text="Mode"),
         tk.Button(self.manual_page, text="Pump", command=lambda: self.queue.put(self.Instruments[InstrumentIndex].set_mode_pump)),
         tk.Button(self.manual_page, text="Vol", command=lambda: self.queue.put(self.Instruments[InstrumentIndex].set_mode_vol)),
         tk.Label(self.manual_page, text="  Target Vol:"),
         tk.Spinbox(self.manual_page, from_=0, to=1000, textvariable=self.manual_page_variables[InstrumentIndex][3]),
         # tk.Button(self.manual_page, text="Set", command=lambda: self.queue.put((self.Instruments[InstrumentIndex].set_target_vol, self.manual_page_variables[InstrumentIndex][3].get())))
         tk.Button(self.manual_page, text="Set", command=lambda: self.queue.put((self.Instruments[InstrumentIndex].set_target_vol, self.manual_page_variables[InstrumentIndex][3].get())))
         ]
        # Bind Enter to Spinboxes
        newbuttons[4].bind('<Return>', lambda event: self.queue.put((self.Instruments[InstrumentIndex].set_infuse_rate, self.manual_page_variables[InstrumentIndex][1].get())))
        newbuttons[7].bind('<Return>', lambda event: self.queue.put((self.Instruments[InstrumentIndex].set_refill_rate, self.manual_page_variables[InstrumentIndex][2].get())))
        newbuttons[16].bind('<Return>', lambda event: self.queue.put((self.Instruments[InstrumentIndex].set_target_vol, self.manual_page_variables[InstrumentIndex][3].get())))
        self.manual_page_buttons.append(newbuttons)
        # Build Pump
        for i in range(len(self.manual_page_buttons)):
            for y in range(len(self.manual_page_buttons[i])):
                self.manual_page_buttons[i][y].grid(row=i, column=y)

    def RefreshCOMList(self):
        self.ControllerCOM.updatelist(SAXSDrivers.list_available_ports(self.AvailablePorts))
        for button in self.setup_page_buttons:
            if isinstance(button[0], COMPortSelector):
                button[0].updatelist(SAXSDrivers.list_available_ports(self.AvailablePorts))

    def AddRheodyneSetButtons(self):
        self.Instruments.append(SAXSDrivers.Rheodyne(logger=self.Instrument_logger))
        InstrumentIndex = len(self.Instruments)-1
        newvars = [tk.IntVar(value=-1), tk.StringVar(), tk.IntVar(value=2), tk.StringVar()]
        self.setup_page_variables.append(newvars)
        newbuttons = [
         COMPortSelector(self.setup_page, exportselection=0, height=4),
         tk.Button(self.setup_page, text="Set Port", command=lambda: self.Instruments[InstrumentIndex].set_port(self.AvailablePorts[int(self.setup_page_buttons[InstrumentIndex][0].curselection()[0])].device)),
         tk.Label(self.setup_page, text="or"),
         tk.Button(self.setup_page, text="Send to Controller", command=lambda: self.Instruments[InstrumentIndex].set_to_controller(self.controller)),
         tk.Label(self.setup_page, text="   Type:"),
         tk.Spinbox(self.setup_page, values=(2, 6), textvariable=self.setup_page_variables[InstrumentIndex][2]),
         tk.Label(self.setup_page, text="   I2C Address:"),
         tk.Spinbox(self.setup_page, from_=-1, to=100, textvariable=self.setup_page_variables[InstrumentIndex][0]),
         tk.Label(self.setup_page, text="   Valve Name:"),
         tk.Entry(self.setup_page, textvariable=self.setup_page_variables[InstrumentIndex][1]),
         tk.Button(self.setup_page, text="Set values", command=lambda: self.InstrumentChangeValues(InstrumentIndex, True)),
         tk.OptionMenu(self.setup_page, self.setup_page_variables[InstrumentIndex][3], *self.hardware_config_options),
         tk.Button(self.setup_page, text="Set", command=lambda: self.configure_to_hardware(self.setup_page_variables[InstrumentIndex][3].get(), InstrumentIndex))
         ]
        self.setup_page_buttons.append(newbuttons)
        for i in range(len(self.setup_page_buttons)):
            for y in range(len(self.setup_page_buttons[i])):
                self.setup_page_buttons[i][y].grid(row=i+2, column=y)
        self.AddRheodyneControlButtons()
        self.RefreshCOMList()
        # self.RefreshDropdown()

    def AddRheodyneControlButtons(self):
        InstrumentIndex = len(self.Instruments)-1
        newvars = [tk.StringVar(), tk.IntVar(value=0)]
        newvars[0].set(self.Instruments[InstrumentIndex].name+":  ")
        self.manual_page_variables.append(newvars)

        newbuttons = [
         tk.Label(self.manual_page, textvariable=self.manual_page_variables[InstrumentIndex][0]),
         tk.Label(self.manual_page, text="   Position:"),
         tk.Spinbox(self.manual_page, from_=1, to=self.setup_page_variables[InstrumentIndex][2].get(), textvariable=self.manual_page_variables[InstrumentIndex][1]),
         tk.Button(self.manual_page, text="Change", command=lambda: self.queue.put((self.Instruments[InstrumentIndex].switchvalve, self.manual_page_variables[InstrumentIndex][1].get()))),
         ]
        newbuttons[2].bind('<Return>', lambda event: self.queue.put((self.Instruments[InstrumentIndex].switchvalve, self.manual_page_variables[InstrumentIndex][1].get())))
        self.manual_page_buttons.append(newbuttons)
        # Place buttons
        for i in range(len(self.manual_page_buttons)):
            for y in range(len(self.manual_page_buttons[i])):
                self.manual_page_buttons[i][y].grid(row=i, column=y)

    def AddVICISetButtons(self):
        self.Instruments.append(SAXSDrivers.VICI(logger=self.Instrument_logger))
        InstrumentIndex = len(self.Instruments)-1
        newvars = [tk.IntVar(value=-1), tk.StringVar(), tk.StringVar()]
        self.setup_page_variables.append(newvars)
        newbuttons = [
         COMPortSelector(self.setup_page, exportselection=0, height=4),
         tk.Button(self.setup_page, text="Set Port", command=lambda: self.Instruments[InstrumentIndex].set_port(self.AvailablePorts[int(self.setup_page_buttons[InstrumentIndex][0].curselection()[0])].device)),
         tk.Label(self.setup_page, text="or"),
         tk.Button(self.setup_page, text="Send to Controller", command=lambda:self.Instruments[InstrumentIndex].set_to_controller(self.controller)),
         tk.Label(self.setup_page, text="   Valve Name:"),
         tk.Entry(self.setup_page, textvariable=self.setup_page_variables[InstrumentIndex][1]),
         tk.Button(self.setup_page, text="Set values", command=lambda: self.InstrumentChangeValues(InstrumentIndex, False)),
         tk.OptionMenu(self.setup_page, self.setup_page_variables[InstrumentIndex][2], *self.hardware_config_options),
         tk.Button(self.setup_page, text="Set", command=lambda: self.configure_to_hardware(self.setup_page_variables[InstrumentIndex][2].get(), InstrumentIndex))
         ]
        self.setup_page_buttons.append(newbuttons)
        for i in range(len(self.setup_page_buttons)):
            for y in range(len(self.setup_page_buttons[i])):
                self.setup_page_buttons[i][y].grid(row=i+2, column=y)
        self.AddVICIControlButtons()
        self.RefreshCOMList()
        # self.RefreshDropdown()

    def AddVICIControlButtons(self):
        InstrumentIndex = len(self.Instruments)-1
        newvars = [tk.StringVar(), tk.StringVar(value="A")]
        newvars[0].set(self.Instruments[InstrumentIndex].name+":  ")
        self.manual_page_variables.append(newvars)

        newbuttons = [
         tk.Label(self.manual_page, textvariable=self.manual_page_variables[InstrumentIndex][0]),
         tk.Label(self.manual_page, text="   Position:"),
         tk.Spinbox(self.manual_page, values=("A", "B"), textvariable=self.manual_page_variables[InstrumentIndex][1]),
         tk.Button(self.manual_page, text="Change", command=lambda: self.queue.put((self.Instruments[InstrumentIndex].switchvalve, self.manual_page_variables[InstrumentIndex][1].get()))),
         ]
        newbuttons[2].bind('<Return>', lambda event: self.queue.put((self.Instruments[InstrumentIndex].switchvalve, self.manual_page_variables[InstrumentIndex][1].get())))
        self.manual_page_buttons.append(newbuttons)
        # Place buttons
        for i in range(len(self.manual_page_buttons)):
            for y in range(len(self.manual_page_buttons[i])):
                self.manual_page_buttons[i][y].grid(row=i, column=y)

    def ChangeDirectory(self):
        BaseDirectory = self.spec_base_directory.get()
        SubDirectory = self.spec_sub_directory.get()

        for eachChar in SubDirectory:
            if eachChar in self.illegalChars:
                tk.messagebox.showinfo("Error", 'Directory name contains invalid characters. \nThese include: %s (includes spaces).' % (self.illegalChars), 'Invalid Input')
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

        OldDirectory = os.path.join(self.OldBaseDirectory, self.OldSubDirectory)

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

            # print 'Index: %i' %(index)


            cmd = ''
            for a in range(index+1, len(nd_parts)):
                self.adxIsDone = False
                # print 'New directories to make'
                tdirectory = '/'.join(nd_parts[:a])
                # print tdirectory
                if a < len(nd_parts)-1:
                    cmd = cmd + 'MKDIR_NO ' + str(tdirectory)+','
                    # solocomm.controlQueue.put([('A', 'MKDIR_NO ' + str(tdirectory))])
                else:
                    cmd = cmd + 'MKDIR ' + str(tdirectory)

            solocomm.controlQueue.put([('A', cmd)])

            self.main_window.after(1000, self.OnMkdirTimer)

        self.OldBaseDirectory = BaseDirectory
        self.OldSubDirectory = SubDirectory

        return (True, Directory)

    def OnMkdirTimer(self):
        if self.adxIsDone:
            if not self.exposing:
                solocomm.controlQueue.put([('G', 'ADXDONE_OK')])
        pass


    def OnExposeButton(self, postfix=None):

        ### Input Sanitation ###
        try:
            NoOfFrames = self.tseries_frames.get()
            ExposureTime = self.tseries_time.get()
            FileNumber = self.spec_fileno.get()

            if NoOfFrames < 1 or FileNumber < 0:
                raise ValueError

        except ValueError:
            tk.messagebox.showinfo('Error', 'Exposure time, number of frames or filenumber is invalid.', 'Invalid Input')
            return
        ###

        Filename = self.spec_filename.get().strip()

        for eachChar in Filename:
            if eachChar in self.illegalChars:
                tk.messagebox.showinfo('Error', 'Filename contains invalid characters. \nThese include: %s (includes spaces).' %(self.illegalChars), 'Invalid Input')
                return

        if Filename == '':
            tk.messagebox.showinfo('Error', 'File must have a name.', 'Invalid Input')
            return

        changedir, Directory = self.ChangeDirectory()

        if changedir:
            #try:
            #    self.writeLogFile()
            #except:
            #    pass
            self.exposing = True
            FileNumber = FileNumber = self.spec_fileno.get()
            # NewDark = self.exposureChkboxForceDark.GetValue()
            #self.exposeButton.Enable(False)
            #self.SetStatus('Exposing Sample')

            #self.counter.SetTime((ExposureTime+0.04) * int(NoOfFrames)+1)
            #self.soundInitiatingExposure.Play()

            NewDark = '0'

            print(('A EXPOSE '+Filename + '_' + FileNumber + ',' + str(ExposureTime) + ',' + str(NoOfFrames)))

            file = Filename
            file += '_' + FileNumber
            if postfix is not None:
                file += '_' + postfix

            solocomm.controlQueue.put([('A', 'EXPOSE '+ file + ',' +
                                         str(ExposureTime) + ',' + str(NoOfFrames) +
                                         ',' + str(Directory) + ',' + str(NewDark))])

            self.spec_fileno.delete(0, 'end')
            self.spec_fileno.insert(0, FileNumber+1)


if __name__ == "__main__":
    window = tk.Tk()
    Main(window)
    window.mainloop()
    print("Main window now destroyed. Exiting.")
