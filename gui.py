"""This script creates the SAXS control GUI."""

import tkinter as tk
from tkinter import filedialog
from widgets import FluidLevel
import tkinter.ttk as ttk
from configparser import ConfigParser
import csv
import time

class main:
    """Class for the main window of the SAXS Control."""
    CSV_HEADERS = ["Unix time (s)", "oil level (%)"]

    def __init__(self, window):
        """Set up the window and button variables."""
        self.main_window = window
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
        # Button Bar
        self.buttons = tk.Frame(self.main_window)
        self.exit_button = tk.Button(self.main_window, text='X', command=self.main_window.destroy)
        self.stop_button = tk.Button(self.buttons, text='STOP', command=self.stop, fg='red', font='Arial 16 bold')

        # Main Structures
        self.core = ttk.Notebook(self.main_window, width=core_width, height=core_height)
        self.auto_page = tk.Frame(self.core)
        self.config_page = tk.Frame(self.core)
        self.manual_page = tk.Frame(self.core)
        self.setup_page = tk.Frame(self.core)
        self.log_frame = tk.Frame(self.main_window, width=log_width, height=log_height, bg='white')
        self.state_frame = tk.Frame(self.main_window, width=window_width, height=state_height, bg='blue')
        # Widgets on Main page
        self.oil_ticksize = tk.IntVar(value=5)
        self.oil_meter = FluidLevel(self.auto_page, color='black', ticksize=self.oil_ticksize)
        self.oil_refill_button = tk.Button(self.auto_page, text='Refill Oil', command=lambda: self.oil_meter.update(100))
        self.oil_start_button = tk.Button(self.auto_page, text='Start Oil', command=self.oil_meter.start)
        # Config page
        self.save_config_button = tk.Button(self.config_page, text='Save Config', command=self.save_config)
        self.load_config_button = tk.Button(self.config_page, text='Load Config', command=self.load_config)
        self.config_oil_tick_size_label = tk.Label(self.config_page, text='Oil Use (mL/min)')
        self.config_oil_tick_size = tk.Spinbox(self.config_page, from_=0, to=10, textvariable=self.oil_ticksize, increment=0.01)

        #
        # TODO: also autosave, as a backup in case of crashing
        # initialize an empty history
        self.history = [
            (time.time(), 99 if time.sleep(0.5) else 93),
            (time.time(), 44)
        ]
        self.save_button = tk.Button(self.buttons, text='Save History', command=self.save_history) # TODO
        self.save_button.grid(row=0, column=4) # TODO

        self.draw_static()
        self.load_config(filename='config.ini')

    def draw_static(self):
        """Define the geometry of the frames and objects."""
        self.buttons.grid(row=0, column=0, columnspan='2')
        self.exit_button.grid(row=0, column=1, sticky='NE')
        self.core.grid(row=1, column=0)
        self.log_frame.grid(row=1, column=1, sticky='S', pady=1)
        self.state_frame.grid(row=2, column=0, columnspan=2)
        # Tab Bar
        self.core.add(self.auto_page, text='Auto')
        self.core.add(self.manual_page, text='Manual')
        self.core.add(self.config_page, text='Config')
        self.core.add(self.setup_page, text='Setup')
        # Buttons
        self.stop_button.grid(row=0, column=0)
        # Main Page
        self.oil_meter.grid(row=0, columnspan=2)
        self.oil_refill_button.grid(row=1, column=0)
        self.oil_start_button.grid(row=1, column=1)
        # Config page
        self.save_config_button.grid(row=0, column=0)
        self.load_config_button.grid(row=0, column=1)
        self.config_oil_tick_size_label.grid(row=1, column=0)
        self.config_oil_tick_size.grid(row=1, column=1)

    def stop(self):
        """Stop all running widgets."""
        self.oil_meter.stop()

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


if __name__ == "__main__":
    window = tk.Tk()
    main(window)
    window.mainloop()
