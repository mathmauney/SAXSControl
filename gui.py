"""This script creates the SAXS control GUI."""

import tkinter as tk
from tkinter import filedialog
from widgets import FluidLevel
import tkinter.ttk as ttk
from configparser import SafeConfigParser


class main:
    """Class for the main window of the SAXS Control."""

    def __init__(self, window):
        """Set up the window and button variables."""
        self.main_window = window
        self.main_window.title('Main Window')
        # self.main_window.attributes("-fullscreen", True)  # Makes the window fullscreen
        # Button Bar
        self.buttons = tk.Frame(self.main_window)
        self.exit_button = tk.Button(self.buttons, text='Exit', command=self.main_window.destroy)
        self.stop_button = tk.Button(self.buttons, text='Stop', command=self.stop)
        self.save_config_button = tk.Button(self.buttons, text='Save Config', command=self.save_config)
        self.load_config_button = tk.Button(self.buttons, text='Load Config', command=self.load_config)
        # Main Structures
        self.core = ttk.Notebook(self.main_window)
        self.main_page = tk.Frame(self.core)
        self.config_page = tk.Frame(self.core)
        # Widgets on Main page
        self.oil_ticksize = tk.IntVar(value=5)
        self.oil_meter = FluidLevel(self.main_page, color='black', ticksize=self.oil_ticksize)
        self.oil_refill_button = tk.Button(self.main_page, text='Refill Oil', command=lambda: self.oil_meter.update(100))
        self.oil_start_button = tk.Button(self.main_page, text='Start Oil', command=self.oil_meter.start)
        # Config Entrys
        self.config_oil_tick_size_label = tk.Label(self.config_page, text='Oil Use (mL/min)')
        self.config_oil_tick_size = tk.Spinbox(self.config_page, from_=0, to=10, textvariable=self.oil_ticksize, increment=0.01)

        self.draw_static()
        self.load_config(filename='config.ini')

    def draw_static(self):
        """Define the geometry of the frames and objects."""
        self.buttons.grid(row=0, column=0)
        self.core.grid(row=1, column=0)
        # Tab Bar
        self.core.add(self.main_page, text='Main')
        self.core.add(self.config_page, text='Config')
        # Buttons
        self.exit_button.grid(row=0, column=0)
        self.stop_button.grid(row=0, column=1)
        self.save_config_button.grid(row=0, column=2)
        self.load_config_button.grid(row=0, column=3)
        # Main Page
        self.oil_meter.grid(row=0, columnspan=2)
        self.oil_refill_button.grid(row=1, column=0)
        self.oil_start_button.grid(row=1, column=1)
        # Config page
        self.config_oil_tick_size_label.grid(row=0, column=0)
        self.config_oil_tick_size.grid(row=0, column=1)

    def stop(self):
        """Stop all running widgets."""
        self.oil_meter.stop()

    def load_config(self, filename=None):
        """Load a config.ini file."""
        self.config = SafeConfigParser()
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


if __name__ == "__main__":
    window = tk.Tk()
    main(window)
    window.mainloop()
