"""This script creates the SAXS control GUI."""

import tkinter as tk
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
        self.save_config_button = tk.Button(self.buttons, text='Save Config', command=lambda: self.save_config(filename=self.config_name_entry.get()))
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
        self.config_name_entry = tk.Entry(self.config_page)

        self.draw_static()
        self.load_config()

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
        # Main Page
        self.oil_meter.grid(row=0, columnspan=2)
        self.oil_refill_button.grid(row=1, column=0)
        self.oil_start_button.grid(row=1, column=1)
        # Config page
        self.config_name_entry.grid()

    def stop(self):
        """Stop all running widgets."""
        self.oil_meter.stop()

    def load_config(self, filename='config.ini'):
        """Load a config.ini file."""
        self.config = SafeConfigParser()
        self.config.read(filename)
        self.config_name_entry.insert(0, self.config.get('Default', 'filename'))

    def save_config(self, filename='config.ini'):
        """Save a config.ini file."""
        self.config.set('Default', 'filename', self.config_name_entry.get())
        self.config.write(open(filename, 'w'))


if __name__ == "__main__":
    window = tk.Tk()
    main(window)
    window.mainloop()
