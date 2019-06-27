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
import os


FULLSCREEN = True  # For easier testing, turn this off
LOG_FOLDER = "log"

class main:
    """Class for the main window of the SAXS Control."""

    def __init__(self, window):
        """Set up the window and button variables."""
        print("Initializing GUI...")

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

        # Button Bar
        self.buttons = tk.Frame(self.main_window)
        self.exit_button = tk.Button(self.main_window, text='X', command=self.exit)
        self.stop_button = tk.Button(self.buttons, text='STOP', command=self.stop, fg='red', font='Arial 16 bold')

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
        self.spec_connect_button = tk.Button(self.auto_page, text='Connect to SPEC',
                                             command=lambda: self.SPEC_Connection.connect((self.spec_address.get(), self.spec_port.get())))
        self.spec_test_button = tk.Button(self.auto_page, text='SPEC test', command=lambda: self.SPEC_Connection.command('test'))
        # Config page
        self.save_config_button = tk.Button(self.config_page, text='Save Config', command=self.save_config)
        self.load_config_button = tk.Button(self.config_page, text='Load Config', command=self.load_config)
        self.config_oil_tick_size_label = tk.Label(self.config_page, text='Oil Use (mL/min)')
        self.config_oil_tick_size = tk.Spinbox(self.config_page, from_=0, to=10, textvariable=self.oil_ticksize, increment=0.01)
        # self.spec_address = tk.StringVar(value='192.168.1.5')
        self.spec_address = tk.StringVar(value='192.168.0.233')
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

        self.draw_static()
        self.elveflow_display = ElveflowDisplay(self.elveflow_page, core_height, core_width, self.python_logger)
        self.elveflow_display.grid(row=0, column=0)

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
        self.logs.add(self.python_logs, text='Python')
        self.logs.add(self.SPEC_logs, text='SPEC')
        # Main Page
        self.oil_meter.grid(row=0, columnspan=2)
        self.oil_refill_button.grid(row=1, column=0)
        self.oil_start_button.grid(row=1, column=1)
        self.spec_connect_button.grid(row=2, column=0)
        self.spec_test_button.grid(row=3, column=0)
        # Config page
        self.save_config_button.grid(row=0, column=0)
        self.load_config_button.grid(row=0, column=1)
        self.config_oil_tick_size_label.grid(row=1, column=0)
        self.config_oil_tick_size.grid(row=1, column=1)
        self.config_spec_address_label.grid(row=2, column=0)
        self.config_spec_address.grid(row=2, column=1)
        self.config_spec_port_label.grid(row=3, column=0)
        self.config_spec_port.grid(row=3, column=1)
        # Python Log
        self.python_logger_gui.grid(row=0, column=0, sticky='NSEW')
        nowtime = time.time()
        python_handler = TextHandler(self.python_logger_gui)
        file_handler = logging.FileHandler(os.path.join(LOG_FOLDER, "log%010d.txt" % nowtime))
        python_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        # logging.basicConfig(level=logging.INFO,
        #                     format='%(asctime)s - %(levelname)s - %(message)s')
        self.python_logger = logging.getLogger("python")
        self.python_logger.setLevel(logging.DEBUG)
        self.python_logger.addHandler(python_handler) #logging to the screen
        self.python_logger.addHandler(file_handler) #logging to a file

        # SPEC Log
        self.SPEC_logger.grid(row=0, column=0, sticky='NSEW')
        self.SPEC_Connection = SPEC.connection(logger=self.SPEC_logger)

    def stop(self):
        """Stop all running widgets."""
        self.oil_meter.stop()
        print("STOPPING")
        if self.elveflow_display.run_flag.is_set():
            print("NO REALLY, I'M STOPPING")
            self.elveflow_display.stop()

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

    def handle_exception(self, exception, value, traceback):
        self.python_logger.exception("Caught exception:")

    def exit(self):
        self.stop()
        self.main_window.destroy()


if __name__ == "__main__":
    try:
        window = tk.Tk()
        main(window)
        window.mainloop()
        time.sleep(1)
    finally:
        import threading
        print(threading.enumerate())
