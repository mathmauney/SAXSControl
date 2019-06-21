# encoding: utf-8
"""This module implements custom tkinter widgets for the SAXS control panel."""

import tkinter as tk
import tkinter.font
import logging
import tkinter.scrolledtext as ScrolledText
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


class TextHandler(logging.Handler):
    # This class allows you to log to a Tkinter Text or ScrolledText widget
    # Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06

    def __init__(self, text):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Store a reference to the Text it will log to
        self.text = text

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text.configure(state='normal')
            self.text.insert(tk.END, msg + '\n')
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(tk.END)
        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)


class MiscLogger(ScrolledText.ScrolledText):
    def append(self, msg):
        self.configure(state='normal')
        self.insert(tk.END, msg + '\n')
        self.configure(state='disabled')
        # Autoscroll to the bottom
        self.yview(tk.END)


class ElveflowDisplay(tk.Canvas):
    """Build a widget to show the Elveflow graph."""
    POLLING_PERIOD = 1
    PADDING = 2

    def __init__(self, window, height, width, **kwargs):
        """Start the FluidLevel object with default paramaters."""
        super().__init__(window, **kwargs)
        self.dataXLabel = tk.StringVar()    # Time [s]
        self.dataYLabel = tk.StringVar()    # hplc(Read)[µl/min]
        self.dataTitle = "Elveflow data"

        # https://stackoverflow.com/questions/31440167/placing-plot-on-tkinter-main-window-in-python
        remaining_width_per_column = width / 9
        dpi = 96 #this shouldn't matter too much (because we normalize against it) except in how font sizes are handled in the plot
        self.the_fig = plt.Figure(figsize=(width*2/3/dpi, height*3/4/dpi), dpi=dpi)
        self.ax = self.the_fig.add_subplot(111)
        self.ax.set_title(self.dataTitle, fontsize=16)

        self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.the_fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=4, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)

        self.start_button = tk.Button(self, text='Start Graph', command=self.start)
        self.start_button.grid(row=0, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.stop_button = tk.Button(self, text='Stop Graph', command=self.stop)
        self.stop_button.grid(row=0, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.stop_button = tk.Button(self, text='Clear Graph', command=self.clear_graph)
        self.stop_button.grid(row=0, column=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)


        tk.Label(self, text="X axis").grid(row=1, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.dropdownX = tk.OptionMenu(self, self.dataXLabel, None)
        fontsize = tkinter.font.Font(font=self.dropdownX ['font'])['size']
        self.dropdownX.config(width=int(remaining_width_per_column *2 / fontsize)) # width is in units of font size
        self.dropdownX.grid(row=1, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)

        tk.Label(self, text="Y axis").grid(row=2, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.dropdownY = tk.OptionMenu(self, self.dataYLabel, None)
        self.dropdownY.config(width=int(remaining_width_per_column *2/ fontsize))
        self.dropdownY.grid(row=2, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)

        tk.Label(self, text="Reading from:").grid(row=3, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.reading_from_data = tk.StringVar()
        self.reading_from_entry = tk.Entry(self, textvariable=self.reading_from_data, justify="left")
        if not FileIO.USE_SDK:
            self.reading_from_entry.config(state="readonly")
        self.reading_from_entry.grid(row=3, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)

        self.run_flag = threading.Event()
        self._initialize_variables()

    def _initialize_variables(self):
        """create or reset all the internal variables"""
        self.elveflow_handler = None
        self.data = []
        self.run_flag.clear()
        self.the_line = self.ax.plot([], [])[0]
        try:
            if not FileIO.USE_SDK:
                self.reading_from_data.set("None")
        except RuntimeError as e:
            # happens because the main window is closed
            print("There was a RuntimeError. Ignoring it: %s" % e)
            pass
        # self.the_thread = None

    def populateDropdowns(self):
        self.dropdownX['menu'].delete(0, 'end')
        self.dropdownY['menu'].delete(0, 'end') # these two deletions shouldn't be necessary, but I'm afraid of weird race conditions that realistically won't happen even if they're possible
        for item in self.elveflow_handler.header:
            self.dropdownX['menu'].add_command(label=item, command=lambda item=item: self.dataXLabel.set(item))     # weird default argument for scoping
            self.dropdownY['menu'].add_command(label=item, command=lambda item=item: self.dataYLabel.set(item))

    def start(self):
        if self.elveflow_handler is not None:
            raise RuntimeError("the elveflow_handler is already running!")

        if FileIO.USE_SDK:
            self.reading_from_entry.config(state=tk.DISABLED)
            self.elveflow_handler = FileIO.ElveflowHandler(sourcename=self.reading_from_data.get())
            self.reading_from_data.set(str(self.elveflow_handler.sourcename, encoding='ascii'))
        else:
            self.elveflow_handler = FileIO.ElveflowHandler()
            if self.elveflow_handler.sourcename is None:
                #abort if empty
                self._initialize_variables()
                return
            self.reading_from_data.set(self.elveflow_handler.sourcename)

        self.dropdownX['menu'].delete(0, 'end')
        self.dropdownY['menu'].delete(0, 'end')
        self.dataXLabel.set('')
        self.dataYLabel.set('')
        self.elveflow_handler.start(getheader_handler=self.populateDropdowns)

        def pollElveflowThread(run_flag):
            # technically a race condition here: what if the user tries to stop the thread right here, and then this thread resets it?
            # in practice, I think it's not a concern...?
            print("STARTING DISPLAY THREAD %s" % threading.current_thread())
            run_flag.set()
            try:
                while run_flag.is_set():
                    newData = self.elveflow_handler.fetchAll()
                    self.data.extend(newData)
                    self.update_plot()

                    time.sleep(ElveflowDisplay.POLLING_PERIOD)
            finally:
                self.stop()
                print("DONE WITH THIS THREAD, %s" % threading.current_thread())

        self.the_thread = threading.Thread(target=pollElveflowThread, args=(self.run_flag,))
        self.the_thread.start()

    def stop(self):
        self.run_flag.clear()
        # print("run flag cleared")
        if self.elveflow_handler is not None:
            self.elveflow_handler.stop()
        if FileIO.USE_SDK:
            self.reading_from_entry.config(state=tk.NORMAL)
        self._initialize_variables()

    def clear_graph(self):
        self.ax.clear()
        self.the_line = self.ax.plot([], [])[0]
        self.ax.set_title(self.dataTitle, fontsize=16)
        self.update_plot()
        print("graph CLEARED!")

    def update_plot(self):
        dataXLabel = self.dataXLabel.get()
        dataYLabel = self.dataYLabel.get()

        if dataXLabel != '' and dataYLabel != '':
            dataX = [elt[dataXLabel] for elt in self.data if not np.isnan(elt[dataXLabel]) and not np.isnan(elt[dataYLabel])]
            dataY = [elt[dataYLabel] for elt in self.data if not np.isnan(elt[dataXLabel]) and not np.isnan(elt[dataYLabel])]
            # print(len(dataX))
            # print(len(dataY))
            if len(dataX) > 0:
                self.the_line.set_data(dataX, dataY)
                self.ax.set_xlim(np.nanmin(dataX), np.nanmax(dataX))
                self.ax.set_ylim(np.nanmin(dataY), np.nanmax(dataY))
                self.ax.set_xlabel(self.dataXLabel.get(), fontsize=14)
                self.ax.set_ylabel(self.dataYLabel.get(), fontsize=14)
                self.canvas.draw()
