# encoding: utf-8
"""This module implements custom tkinter widgets for the SAXS control panel."""

import tkinter as tk
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
import FileIO
import threading
import time

class FluidLevel(tk.Canvas):
    """Build a widget to show the fluid level in a syringe."""

    def __init__(self, window,  **kwargs):
        """Start the FluidLevel object with default paramaters."""
        self.color = kwargs.pop('color', 'blue')
        border = kwargs.pop('border', 10)
        self.ticksize = kwargs.pop('ticksize', tk.IntVar(value=1))
        self.tickperiod = kwargs.pop('tickperiod', 1000)
        # Use pop to remove kwargs that aren't a part of Canvas
        super().__init__(window, **kwargs)
        width = kwargs.get('width', 200)
        height = kwargs.get('height', 100)
        self.config(width=width, height=height)
        self.create_rectangle(0, 0, width, height, fill="grey", outline="grey")
        self.max = self.create_rectangle(border, border, width-border, height-border, fill="white", outline="white")
        self.level = self.create_rectangle(border, border, border, height-border, fill='white', outline='white')
        self.running = False
        self.tick()

    def update(self, percent):
        """Update the fluid level to s given value."""
        percent = min(percent, 100)
        percent = max(percent, 0)
        x0, y0, x1, y1 = self.coords(self.max)
        x1 = round((x1-x0)*percent/100) + x0
        self.coords(self.level, x0, y0, x1, y1)
        self.percent = percent
        if x1 == x0:
            self.itemconfig(self.level, fill='white', outline='white')
        else:
            self.itemconfig(self.level, fill=self.color, outline=self.color)

    def tick(self):
        """Remove a tick worth of fluid from the gauge."""
        if self.running:
            percent = self.percent - self.ticksize.get()
            self.update(percent)
            self.percent = percent
        self.after(self.tickperiod, self.tick)

    def start(self):
        """Turn on ticking behavior."""
        self.running = True

    def stop(self):
        """Turn off ticking behavior."""
        self.running = False

class ElveflowDisplay(tk.Canvas):
    """Build a widget to show the Elveflow graph."""
    SLEEPTIME = 2

    def __init__(self, window,  **kwargs):
        """Start the FluidLevel object with default paramaters."""
        # Use pop to remove kwargs that aren't a part of Canvas
        super().__init__(window, **kwargs)
        width = kwargs.get('width', 500)
        height = kwargs.get('height', 150)
        self.config(width=width, height=height)
        self.create_rectangle(0, 0, width, height, fill="grey", outline="grey")
        self.elveflow_handler = None
        self.dataX = []
        self.dataY = []
        self.dataXLabel = "Time [s]"
        self.dataYLabel = "hplc(Read)[µl/min]"

        # https://stackoverflow.com/questions/31440167/placing-plot-on-tkinter-main-window-in-python
        self.the_fig = plt.Figure(figsize=(6,6))
        self.ax = self.the_fig.add_subplot(111)
        self.the_line = self.ax.plot(self.dataX, self.dataY) [0]
        self.ax.set_title ("Elveflow Output", fontsize=16)
        self.ax.set_ylabel("Y", fontsize=14)
        self.ax.set_xlabel("X", fontsize=14)

        self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.the_fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0)

        self.stop_flag = False

    def start(self):
        if self.elveflow_handler is not None:
            raise RuntimeError("Stop that.")
        self.elveflow_handler = FileIO.ElveflowHandler()
        self.elveflow_handler.start()
        def pollElveflowThread():
            while True:
                if self.stop_flag:
                    self.elveflow_handler = None
                    self.stop_flag = False
                    self.dataX = []
                    self.dataY = []
                    self.the_line = self.ax.plot(self.dataX, self.dataY) [0]
                    return
                time.sleep(ElveflowDisplay.SLEEPTIME)
                newData = self.elveflow_handler.fetchAll()

                self.dataX.extend(elt[self.dataXLabel] for elt in newData)
                self.dataY.extend(elt[self.dataYLabel] for elt in newData)

                self.the_line.set_data(self.dataX, self.dataY)
                self.ax.set_xlim(np.min(self.dataX), np.max(self.dataX))
                self.ax.set_ylim(np.min(self.dataY), np.max(self.dataY))
                self.canvas.draw()



        the_thread = threading.Thread(target=pollElveflowThread)
        the_thread.start()

    def stop(self):
        self.stop_flag = True
