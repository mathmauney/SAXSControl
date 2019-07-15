"""This script creates the SAXS control GUI.

Pollack Lab-Cornell
Alex Mauney
"""

import tkinter as tk
import tkinter.scrolledtext as ScrolledText
from tkinter import filedialog
from widgets import FluidLevel, ElveflowDisplay, TextHandler, MiscLogger
import tkinter.ttk as ttk
import time
import SPEC
from configparser import ConfigParser
import logging
import queue
import threading
import HPump
import time
import os.path


FULLSCREEN = True   # For testing, turn this off
LOG_FOLDER = "log"


class main:
    """Class for the main window of the SAXS Control."""

    def __init__(self, window):
        """Set up the window and button variables."""
        print("initializing GUI...")
        os.makedirs(LOG_FOLDER, exist_ok=True)
        os.makedirs(ElveflowDisplay.OUTPUT_FOLDER, exist_ok=True)
        self.main_window = window
        self.main_window.report_callback_exception = self.handle_exception
        self.main_window.title('Main Window')
        self.main_window.attributes("-fullscreen", True)  # Makes the window fullscreen
        # Figure out geometry
        window_width = self.main_window.winfo_screenwidth()
        window_height = self.main_window.winfo_screenheight()
        core_width = round(2*window_width/3)
        log_width = window_width - core_width - 3
        state_height = 300
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

        # Make Instrumet
        self.controller=HPump.SAXSController()
        self.pump=HPump.HPump()
        # Button Bar
        self.buttons = tk.Frame(self.main_window)
        self.exit_button = tk.Button(self.main_window, text='X', command=self.exit)
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
        self.SPEC_logs = tk.Frame(self.logs)
        self.state_frame = tk.Frame(self.main_window, width=window_width, height=state_height, bg='blue')
        # Widgets on Main page
        self.oil_ticksize = tk.IntVar(value=5)
        self.oil_meter = FluidLevel(self.auto_page, color='black', ticksize=self.oil_ticksize)
        self.oil_refill_button = tk.Button(self.auto_page, text='Refill Oil', command=lambda: self.oil_meter.update(100))
        self.oil_start_button = tk.Button(self.auto_page, text='Start Oil', command=self.oil_meter.start)
        self.spec_connect_button = tk.Button(self.auto_page, text='Connect to SPEC', command=self.connect_to_spec)
        self.spec_send_button = tk.Button(self.auto_page, text='Send', command=lambda: self.SPEC_Connection.command(self.spec_command.get()))
        self.spec_command = tk.StringVar(value='')
        self.spec_command_entry = tk.Entry(self.auto_page, textvariable=self.spec_command)
        self.spec_command_entry.bind("<Return>", lambda event: self.SPEC_Connection.command(self.spec_command.get()))
        self.pump_refill_button = tk.Button(self.auto_page, text='Refill Oil', command=lambda: self.pump_refill_command())
        self.pump_inject_button = tk.Button(self.auto_page, text='Run Buffer/Sample/Buffer', command=lambda: self.pump_inject_command())
        # Manual Page
        self.manualstartpump = tk.Button(self.manual_page, text="Run Pump", command=lambda: self.pump.startpump())
        self.manualstoppump = tk.Button(self.manual_page, text="Stop Pump", command=lambda: self.pump.stoppump())
        # Config page
        self.save_config_button = tk.Button(self.config_page, text='Save Config', command=self.save_config)
        self.load_config_button = tk.Button(self.config_page, text='Load Config', command=self.load_config)
        self.config_oil_tick_size_label = tk.Label(self.config_page, text='Oil Use (mL/min)')
        self.config_oil_tick_size = tk.Spinbox(self.config_page, from_=0, to=10, textvariable=self.oil_ticksize, increment=0.01)
        self.spec_address = tk.StringVar(value='192.168.1.5')
        self.volumes_label = tk.Label(self.config_page, text='Buffer/Sample/Buffer volumes in uL:')
        self.first_buffer_volume = tk.IntVar(value=25)     # May need ot be a doublevar
        self.first_buffer_volume_box = tk.Entry(self.config_page, textvariable=self.first_buffer_volume)
        self.sample_volume = tk.IntVar(value=25)           # May need ot be a doublevar
        self.sample_volume_box = tk.Entry(self.config_page, textvariable=self.sample_volume)
        self.last_buffer_volume = tk.IntVar(value=25)      # May need ot be a doublevar
        self.last_buffer_volume_box = tk.Entry(self.config_page, textvariable=self.last_buffer_volume)
        # Setup Page
        self.controllerportvar = tk.IntVar(value=0)
        self.pumpportvar = tk.IntVar(value=0)
        self.InitiateController = tk.Button(self.setup_page, text="Setup Controller", command=lambda:self.controller.setport(self.controllerportvar.get()))
        self.controllerportselect = tk.Spinbox(self.setup_page,from_=1.0, to=10.0, textvariable=self.controllerportvar)
        self.pumpusecontroller = tk.Button(self.setup_page, text="Set pump port to controller", command=lambda: self.pump.settocontroller(self.controller))
        self.selectpumpport = tk.Spinbox(self.setup_page, from_=1.0, to=10.0, textvariable=self.pumpportvar)
        self.setpumpport = tk.Button(self.setup_page,text="Set Pump port local",command=lambda: self.pump.setport(self.pupmpportvar.get()))
        # self.spec_address = tk.StringVar(value='192.168.0.233')   # For Alex M home use
        self.config_spec_address = tk.Entry(self.config_page, textvariable=self.spec_address)
        self.config_spec_address_label = tk.Label(self.config_page, text='SPEC Address')
        self.spec_port = tk.IntVar(value=7)
        self.config_spec_port = tk.Entry(self.config_page, textvariable=self.spec_port)
        self.config_spec_port_label = tk.Label(self.config_page, text='SPEC Port')
        # logs
        self.python_logger_gui = ScrolledText.ScrolledText(self.python_logs, state='disabled', height=45)
        self.python_logger_gui.configure(font='TkFixedFont')
        self.SPEC_logger = MiscLogger(self.SPEC_logs, state='disabled', height=45)
        self.SPEC_logger.configure(font='TkFixedFont')

        time.sleep(0.6) # I have no idea why we need this but everything crashes and burns if we don't include it
        # It acts as though there's a race condition, but aren't we still single-threaded at this point?
        # I suspect something might be going wrong with the libraries, then, especially tkinter and matplotlib

        self.draw_static()
        self.elveflow_display = ElveflowDisplay(self.elveflow_page, core_height, core_width, self.python_logger)
        self.elveflow_display.grid(row=0, column=0)
        self.queue = queue.Queue()
        self.queue_busy = False
        self.listen_run_flag = threading.Event()
        self.listen_run_flag.set()
        self.listen_thread = threading.Thread(target=self.listen)
        self.listen_thread.start()
        self.load_config(filename='config.ini')

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
        self.logs.add(self.SPEC_logs, text='SPEC')
        self.logs.add(self.python_logs, text='Python')
        # Main Page
        self.oil_meter.grid(row=0, columnspan=2)
        self.oil_refill_button.grid(row=1, column=0)
        self.oil_start_button.grid(row=1, column=1)
        self.spec_connect_button.grid(row=2, column=0)
        self.spec_command_entry.grid(row=3, column=0)
        self.spec_send_button.grid(row=3, column=1)
        self.pump_refill_button.grid(row=4, column=0)
        self.pump_inject_button.grid(row=4, column=1)
        # Manual page
        self.manualstartpump.grid(row=0,column=0)
        self.manualstoppump.grid(row=0,column=1)
        # Config page
        self.save_config_button.grid(row=0, column=0)
        self.load_config_button.grid(row=0, column=1)
        self.config_oil_tick_size_label.grid(row=1, column=0)
        self.config_oil_tick_size.grid(row=1, column=1)
        self.config_spec_address_label.grid(row=2, column=0)
        self.config_spec_address.grid(row=2, column=1)
        self.config_spec_port_label.grid(row=3, column=0)
        self.config_spec_port.grid(row=3, column=1)
        self.volumes_label.grid(row=4, column=0)
        self.first_buffer_volume_box.grid(row=4, column=1)
        self.sample_volume_box.grid(row=4, column=2)
        self.last_buffer_volume_box.grid(row=4, column=3)
        # Setup page
        self.controllerportselect.grid(row=0, column=0)
        self.InitiateController.grid(row=0, column=1)
        self.selectpumpport.grid(row=1, column=0)
        self.setpumpport.grid(row=1, column=1)
        self.pumpusecontroller.grid(row=2, column=0)
        # Python Log
        self.python_logger_gui.grid(row=0, column=0, sticky='NSEW')
        nowtime = time.time()
        python_handler = TextHandler(self.python_logger_gui)
        file_handler = logging.FileHandler(os.path.join(LOG_FOLDER, "log%010d.txt" % nowtime))
        python_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        python_handler.setLevel(logging.DEBUG)
        file_handler.setLevel(logging.DEBUG)
        # SPEC Log
        self.SPEC_logger.grid(row=0, column=0, sticky='NSEW')
        self.SPEC_Connection = SPEC.connection(logger=self.SPEC_logger, button=self.spec_connect_button)

        # logging.basicConfig(level=logging.INFO,
        #                     format='%(asctime)s - %(levelname)s - %(message)s')
        self.python_logger = logging.getLogger("python")
        self.python_logger.setLevel(logging.DEBUG)
        self.python_logger.addHandler(python_handler)  # logging to the screen
        self.python_logger.addHandler(file_handler)  # logging to a file

    def stop(self):
        """Stop all running widgets."""
        self.oil_meter.stop()
        with self.queue.mutex:
            self.queue.queue.clear()
        # TODO Add pump stop
        # Add Elveflow stop if we use it for non-pressure

    def load_config(self, filename=None):
        """Load a config.ini file."""
        self.config = ConfigParser()
        if filename is None:
            filename = filedialog.askopenfilename(initialdir=".", title="Select file", filetypes=(("config files", "*.ini"), ("all files", "*.*")))
        if filename is not '':
            self.config.read(filename)
            self.config_oil_tick_size.delete(0, 'end')
            self.config_oil_tick_size.insert(0, self.config.get('Default', 'oil_tick_size'))

    def save_config(self):
        """Save a config.ini file."""
        filename = filedialog.asksaveasfilename(initialdir=".", title="Select file", filetypes=(("config files", "*.ini"), ("all files", "*.*")))
        if filename is not '':
            self.config.write(open(filename, 'w'))

    def connect_to_spec(self):
        """Connect to SPEC instance."""
        self.SPEC_Connection.connect((self.spec_address.get(), self.spec_port.get()))

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
            csvwriter.writerow(main.CSV_HEADERS)
            csvwriter.writerows(self.history)

    def exit(self):
        """Exit the GUI and stop all running things"""
        print("STARTING EXIT PROCEDURE")
        self.stop()
        if self.elveflow_display.run_flag.is_set():
            self.elveflow_display.stop(shutdown=True)
        if self.SPEC_Connection.run_flag.is_set():
            self.SPEC_Connection.stop()
        if self.listen_run_flag.is_set():
            self.listen_run_flag.clear()

        self.main_window.destroy()

    def pump_refill_command(self):
        """Do nothing. It's a dummy command."""
        self.queue.put((self.elveflow_display.elveflow_handler.setPressure, 4, 100))#   Pressurize Oil with Elveflow
        #   Switch valve (may be hooked to pump)
        self.queue.put(self.pump.setmodevol)
        self.queue.put((time.sleep,0.1))
        self.queue.put(self.pump.refill)#   Set pump refill params
        self.queue.put((time.sleep,0.1))
        self.queue.put((self.pump.settargetvol,(self.first_buffer_volume.get()+self.sample_volume.get()+self.last_buffer_volume.get())/1000))
        self.queue.put((time.sleep,0.1))
        self.queue.put(self.pump.startpump)#   Refill pump
        self.queue.put((time.sleep,10))
        self.queue.put(self.pump.infuse)#   Set pump to injection mode
        #   Switch valve
        self.queue.put((self.elveflow_display.elveflow_handler.setPressure, 4, 0))#   Vent Oil
        pass

    def pump_inject_command(self):
        """Do nothing. It's a dummy command."""
        self.queue.put(self.pump.setmodevol)
        self.queue.put((time.sleep,0.1))
        self.queue.put(self.pump.infuse)#   Set pump refill params
        self.queue.put((time.sleep,0.1))
        self.queue.put((self.pump.settargetvol,self.first_buffer_volume.get()/1000))
        self.queue.put((time.sleep,0.1))
        self.queue.put(self.pump.startpump)
        self.queue.put((time.sleep,10))
        self.queue.put((self.pump.settargetvol,self.sample_volume.get()/1000))
        self.queue.put((time.sleep,0.1))
        self.queue.put(self.pump.startpump)
        self.queue.put((time.sleep,10))
        self.queue.put((self.pump.settargetvol,self.last_buffer_volume.get()/1000))
        self.queue.put((time.sleep,0.1))
        self.queue.put(self.pump.startpump)
        #   Check valve positions
        #   Inject X uL
        #   Switch sample valve to sample loop
        #   Inject Y uL
        #   Switch sample valve to buffer positions
        #   Inject Z uL
        pass

    def listen(self):
        """Look for queues of hardware commands and execute them."""
        print("STARTING QUEUE LISTENING THREAD %s" % threading.current_thread())
        while self.listen_run_flag.is_set():
            if self.queue.empty():
                if self.queue_busy:
                    self.queue_busy = False
                    self.toggle_buttons()
            else:
                if not self.queue_busy:
                    self.queue_busy = True
                    self.toggle_buttons()
                queue_item = self.queue.get()
                if isinstance(queue_item, tuple):
                    queue_item[0](*queue_item[1:])
                elif callable(queue_item):
                    queue_item()
        print("DONE WITH THIS QUEUE LISTENING THREAD %s" % threading.current_thread())

    def toggle_buttons(self):
        """Toggle certain buttons on and off when they should not be allowed to add to queue."""
        buttons = (self.pump_inject_button,
                   self.pump_refill_button)
        if self.queue_busy:
            for button in buttons:
                button['state'] = 'disabled'
        else:
            for button in buttons:
                button['state'] = 'normal'


if __name__ == "__main__":
    window = tk.Tk()
    main(window)
    window.mainloop()
    print("Main window now destroyed. Exiting.")
