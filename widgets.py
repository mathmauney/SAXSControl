# encoding: utf-8
"""This module implements custom tkinter widgets for the SAXS control panel."""

import tkinter as tk
import tkinter.font
import logging
import csv
import tkinter.scrolledtext as ScrolledText
import numpy as np
import FileIO
import threading
import time
import os.path
from queue import Queue, Empty as Queue_Empty
from simple_pid import PID
import matplotlib
from matplotlib import pyplot as plt
matplotlib.use('TkAgg')


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
    POLLING_PERIOD = 100  # in milliseconds

    def __init__(self, text):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Store a reference to the Text it will log to
        self.text = text
        self.messagesQueue = Queue()

        # TKinter apparently isn't threadsafe. So instead of updating the GUI directly from the
        # emit callback, throw messages into a threadsafe queue and use .after in the main thread
        # instead of actual threading instead.
        self.text.after(TextHandler.POLLING_PERIOD, self._update)

    def emit(self, record):
        msg = self.format(record)
        self.messagesQueue.put(msg, False)

    def _update(self):
        self.text.configure(state='normal')
        did_update = False
        try:
            while True:
                msg = self.messagesQueue.get(False)
                self.text.insert(tk.END, msg + '\n')
                did_update = True
        except Queue_Empty:
            pass

        self.text.configure(state='disabled')
        if did_update:
            # Autoscroll to the bottom if there actually was anything interesting happening
            self.text.yview(tk.END)
        self.text.after(TextHandler.POLLING_PERIOD, self._update)


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
    OUTPUT_FOLDER = "Elveflow"

    def __init__(self, window, height, width, errorlogger, **kwargs):
        """Start the FluidLevel object with default paramaters."""
        super().__init__(window, **kwargs)

        self.window = window
        self.dataXLabel = tk.StringVar()
        self.dataYLabel = tk.StringVar()
        self.sensorTypes = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.pressureValues = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.axis_limits_numbers = [None, None, None, None]
        self.reading_from_data = tk.StringVar()
        self.saveFileName = tk.StringVar()
        self.saveFileName_suffix = tk.StringVar()
        self.dataTitle = "Elveflow data"
        self.errorlogger = errorlogger
        self.saveFile = None
        self.saveFileWriter = None

        self.starttime = int(time.time())
        self.errorlogger.info("start time is %d" % self.starttime)

        self.run_flag = threading.Event()
        self.save_flag = threading.Event()
        self.saveFileName_suffix.set("_%d.csv" % time.time())

        # https://stackoverflow.com/questions/31440167/placing-plot-on-tkinter-main-window-in-python
        remaining_width_per_column = width / 9
        dpi = 96  # this shouldn't matter too much (because we normalize against it) except in how font sizes are handled in the plot
        self.the_fig = plt.Figure(figsize=(width*2/3/dpi, height*3/4/dpi), dpi=dpi)
        self.ax = self.the_fig.add_subplot(111)
        self.ax.set_title(self.dataTitle, fontsize=16)

        rowcounter = 0
        self.start_button = tk.Button(self, text='Start Connection', command=self.start)
        self.start_button.grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.stop_button = tk.Button(self, text='Stop Connection', command=self.stop)
        self.stop_button.grid(row=rowcounter, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1
        # self.clear_button = tk.Button(self, text='Clear Graph', command=self.clear_graph)
        # self.clear_button.grid(row=0, column=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        # # TODO: make the clear button actually work

        tk.Label(self, text="Reading from:").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.reading_from_entry = tk.Entry(self, textvariable=self.reading_from_data, justify="left")
        if not FileIO.USE_SDK:
            self.reading_from_entry.config(state="readonly")
        self.reading_from_entry.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        fontsize = tkinter.font.Font(font=self.reading_from_entry['font'])['size']
        self.reading_from_entry.config(width=2 * int(remaining_width_per_column / fontsize))  # width is in units of font size
        rowcounter += 1

        if FileIO.USE_SDK:
            tk.Label(self, text="Sensors 1, 2:").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            tk.Label(self, text="Sensors 3, 4:").grid(row=rowcounter+1, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.sensorDropdowns = [None, None, None, None]
            for i in range(4):
                self.sensorDropdowns[i] = tk.OptionMenu(self, self.sensorTypes[i], None)
                self.sensorDropdowns[i]['menu'].delete(0, 'end')  # there's a default empty option, so get rid of that first
                self.sensorDropdowns[i].config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size
                self.sensorDropdowns[i].grid(row=rowcounter+i//2, column=2+i % 2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
                self.sensorTypes[i].set("none")
                for item in FileIO.SDK_SENSOR_TYPES:
                    self.sensorDropdowns[i]['menu'].add_command(label=item,
                                                                command=lambda i=i, item=item: self.sensorTypes[i].set(item))  # weird default argument for scoping
            rowcounter += 2

        tkinter.ttk.Separator(self, orient=tk.HORIZONTAL).grid(row=rowcounter, column=1, columnspan=3, sticky='ew', padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        tk.Label(self, text="X axis").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.dropdownX = tk.OptionMenu(self, self.dataXLabel, None)
        self.dropdownX.config(width=int(remaining_width_per_column * 2 / fontsize))  # width is in units of font size
        self.dropdownX.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        tk.Label(self, text="Y axis").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.dropdownY = tk.OptionMenu(self, self.dataYLabel, None)
        self.dropdownY.config(width=int(remaining_width_per_column * 2 / fontsize))
        self.dropdownY.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        if FileIO.USE_SDK:
            self.start_saving_button = tk.Button(self, text='Start Saving Data', command=self.start_saving)
            self.start_saving_button.grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.stop_saving_button = tk.Button(self, text='Stop Saving Data', command=self.stop_saving)
            self.stop_saving_button.grid(row=rowcounter, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            rowcounter += 1

            tk.Label(self, text="Output filename:").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.saveFileName_entry = tk.Entry(self, textvariable=self.saveFileName, justify="left")
            self.saveFileName_entry.grid(row=rowcounter, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            tk.Label(self, textvariable=self.saveFileName_suffix).grid(row=rowcounter, column=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            rowcounter += 1

        if FileIO.USE_SDK:
            tkinter.ttk.Separator(self, orient=tk.HORIZONTAL).grid(row=rowcounter, column=1, columnspan=3, sticky='ew', padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            rowcounter += 1

            tk.Label(self, text="Set 1, 2:").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            tk.Label(self, text="Set 3, 4:").grid(row=rowcounter+1, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.set_pressure_entries = [None, None, None, None]
            for i in range(4):
                self.set_pressure_entries[i] = tk.Entry(self, textvariable=self.pressureValues[i], justify="left")
                self.set_pressure_entries[i].config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size
                self.set_pressure_entries[i].grid(row=rowcounter+i//2, column=2 + i % 2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
                self.pressureValues[i].set("")
            rowcounter += 2
            self.set_pressure_button = tk.Button(self, text='Set pressure (mbar)', command=self.set_pressure) # TODO
            self.set_pressure_button.grid(row=rowcounter, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.set_flow_rate_button = tk.Button(self, text='Set flow rate (µL/min)', command=self.set_flow_rate) # TODO
            self.set_flow_rate_button.grid(row=rowcounter, column=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            rowcounter += 1

        tkinter.ttk.Separator(self, orient=tk.HORIZONTAL).grid(row=rowcounter, column=1, columnspan=3, sticky='ew', padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        tk.Label(self, text="x axis limits:").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        tk.Label(self, text="y axis limits:").grid(row=rowcounter+1, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.set_axis_limits_entries = [None, None, None, None]
        self.axis_limits = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        for i in range(4):
            self.set_axis_limits_entries[i] = tk.Entry(self, textvariable=self.axis_limits[i], justify="left")
            self.set_axis_limits_entries[i].config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size
            self.set_axis_limits_entries[i].grid(row=rowcounter+i//2, column=2 + i % 2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.axis_limits[i].set("")
        rowcounter += 2
        self.set_axis_limits_button = tk.Button(self, text='Set graph limits (leave blank for auto)', command=self.set_axis_limits)  # TODO
        self.set_axis_limits_button.grid(row=rowcounter, column=1, columnspan=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.the_fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=rowcounter, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)

        self._initialize_variables()
        self.run_flag.set()

    def _initialize_variables(self):
        """create or reset all the internal variables"""
        self.elveflow_handler = None
        self.data = []
        self.run_flag.clear()
        self.save_flag.clear()
        self.the_line = self.ax.plot([], [])[0]
        self.dropdownX.config(state=tk.DISABLED)
        self.dropdownY.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if not FileIO.USE_SDK:
            self.reading_from_data.set("None")
        else:
            self.start_saving_button.config(state=tk.DISABLED)
            self.stop_saving_button.config(state=tk.DISABLED)
            self.saveFileName_entry.config(state=tk.DISABLED)
            self.set_pressure_button.config(state=tk.DISABLED)
            self.set_flow_rate_button.config(state=tk.DISABLED)
            for item in self.set_pressure_entries:
                item.config(state=tk.DISABLED)
            self.saveFile = None
            self.saveFileWriter = None

    def populate_dropdowns(self):
        self.dropdownX['menu'].delete(0, 'end')
        self.dropdownY['menu'].delete(0, 'end')  # these two deletions shouldn't be necessary, but I'm afraid of weird race conditions that realistically won't happen even if they're possible
        for item in self.elveflow_handler.header:
            self.dropdownX['menu'].add_command(label=item, command=lambda item=item: self.dataXLabel.set(item))  # weird default argument for scoping
            self.dropdownY['menu'].add_command(label=item, command=lambda item=item: self.dataYLabel.set(item))

    def start(self):
        if self.elveflow_handler is not None:
            raise RuntimeError("the elveflow_handler is already running!")
        self.dropdownX.config(state=tk.NORMAL)
        self.dropdownY.config(state=tk.NORMAL)

        if FileIO.USE_SDK:
            self.reading_from_entry.config(state=tk.DISABLED)
            self.set_pressure_button.config(state=tk.NORMAL)
            self.set_flow_rate_button.config(state=tk.NORMAL)
            for item in self.set_pressure_entries:
                item.config(state=tk.NORMAL)
            for item in self.sensorDropdowns:
                item.config(state=tk.DISABLED)

            self.elveflow_handler = FileIO.ElveflowHandler(sourcename=self.reading_from_data.get(),
                                                           errorlogger=self.errorlogger,
                                                           sensortypes=list(map(lambda x: FileIO.SDK_SENSOR_TYPES[x.get()], self.sensorTypes)),
                                                           starttime=self.starttime)
            self.reading_from_data.set(str(self.elveflow_handler.sourcename, encoding='ascii'))
        else:
            self.elveflow_handler = FileIO.ElveflowHandler()
            if self.elveflow_handler.sourcename is None:
                # abort if empty
                self._initialize_variables()
                return
            self.reading_from_data.set(self.elveflow_handler.sourcename)

        self.dropdownX['menu'].delete(0, 'end')
        self.dropdownY['menu'].delete(0, 'end')
        self.dataXLabel.set('')
        self.dataYLabel.set('')
        self.elveflow_handler.start(getheader_handler=self.populate_dropdowns)

        def pollElveflowThread(run_flag, save_flag):
            # technically a race condition here: what if the user tries to stop the thread right here, and then this thread resets it?
            # in practice, I think it's not a concern...?
            print("STARTING DISPLAY THREAD %s" % threading.current_thread())
            try:
                while run_flag.is_set():
                    newData = self.elveflow_handler.fetchAll()
                    self.data.extend(newData)
                    self.update_plot()
                    if save_flag.is_set():
                        for dict in newData:
                            self.saveFileWriter.writerow([str(dict[key]) for key in self.elveflow_handler.header])  # TODO
                    time.sleep(ElveflowDisplay.POLLING_PERIOD)
            finally:
                try:
                    print("DONE WITH THIS THREAD, %s" % threading.current_thread())
                except RuntimeError:
                    print("Runtime error detected in display thread %s while trying to close. Ignoring." % threading.current_thread())
                finally:
                    print("As Display %s is closing, these are the remaining threads: %s" % (threading.current_thread(), threading.enumerate()))
                    print()
                self.run_flag.set()

        self.the_thread = threading.Thread(target=pollElveflowThread, args=(self.run_flag, self.save_flag))
        self.the_thread.start()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        if FileIO.USE_SDK:
            self.start_saving_button.config(state=tk.NORMAL)
            self.saveFileName_entry.config(state=tk.NORMAL)
            self.saveFileName_suffix.set("_%d.csv" % time.time())

    def stop(self, shutdown=False):
        self.run_flag.clear()
        print("Display run flag cleared")

        if self.elveflow_handler is not None:
            self.elveflow_handler.stop()
        if FileIO.USE_SDK and not shutdown:
            # if we're actually exiting, no need to update the GUI
            self.reading_from_entry.config(state=tk.NORMAL)
            for item in self.sensorDropdowns:
                item.config(state=tk.NORMAL)
            for item in self.set_pressure_entries:
                item.config(state=tk.DISABLED)
            self.set_pressure_button.config(state=tk.DISABLED)
            self.set_flow_rate_button.config(state=tk.DISABLED)
        self.stop_saving(shutdown=shutdown)
        if not shutdown:
            self._initialize_variables()

    def start_saving(self):
        if self.elveflow_handler.header is not None:
            self.save_flag.set()
            self.stop_saving_button.config(state=tk.NORMAL)
            self.start_saving_button.config(state=tk.DISABLED)
            self.saveFileName_entry.config(state=tk.DISABLED)
            self.saveFile = open(os.path.join(ElveflowDisplay.OUTPUT_FOLDER, self.saveFileName.get() + self.saveFileName_suffix.get()), 'a', encoding="utf-8", newline='')
            self.saveFileWriter = csv.writer(self.saveFile)
            self.saveFileWriter.writerow(self.elveflow_handler.header)
            self.errorlogger.info('started saving')
        else:
            self.errorlogger.error('cannot start saving (header is unknown). Try again in a moment')

    def stop_saving(self, shutdown=False):
        if self.save_flag.is_set():
            self.errorlogger.info('stopped saving')
        self.save_flag.clear()
        if FileIO.USE_SDK and not shutdown:
            self.stop_saving_button.config(state=tk.DISABLED)
            self.start_saving_button.config(state=tk.NORMAL)
            self.saveFileName_entry.config(state=tk.NORMAL)

        self.saveFileName_suffix.set("_%d.csv" % time.time())

        if self.saveFile is not None:
            self.saveFile.close()

    def clear_graph(self):
        self.ax.clear()
        self.the_line = self.ax.plot([], [])[0]
        self.ax.set_title(self.dataTitle, fontsize=16)
        self.update_plot()
        print("graph CLEARED!")

    def update_plot(self):
        dataXLabel = self.dataXLabel.get()
        dataYLabel = self.dataYLabel.get()
        try:
            dataX = [elt[dataXLabel] for elt in self.data if not np.isnan(elt[dataXLabel]) and not np.isnan(elt[dataYLabel])]
            dataY = [elt[dataYLabel] for elt in self.data if not np.isnan(elt[dataXLabel]) and not np.isnan(elt[dataYLabel])]
            extremes = [np.nanmin(dataX), np.nanmax(dataX), np.nanmin(dataY), np.nanmax(dataY)]
            if len(dataX) > 0:
                self.the_line.set_data(dataX, dataY)
            self.ax.set_xlabel(self.dataXLabel.get(), fontsize=14)
            self.ax.set_ylabel(self.dataYLabel.get(), fontsize=14)
        except (ValueError, KeyError):
            extremes = [*self.ax.get_xlim(), *self.ax.get_ylim()]
        limits = [item if item is not None else extremes[i]
                  for (i, item) in enumerate(self.axis_limits_numbers)]
        self.ax.set_xlim(*limits[0:2])
        self.ax.set_ylim(*limits[2:4])
        self.canvas.draw()

    def set_pressure(self):
        for i, x in enumerate(self.pressureValues, 1):
            try:
                pressure_to_set = int(float(x.get()))
                self.elveflow_handler.setPressure(i, pressure_to_set)
                x.set(str(pressure_to_set))
            except ValueError:
                self.elveflow_handler.setPressure(i, 0)
                x.set("")

    def set_flow_rate(self, refresh_rate=0.1, stabilization_tolerance=0.01, stabilization_time=1, callback=None):
        """do a PID loop until something happens"""
        for i, x in enumerate(self.pressureValues, 1):
            try:
                pressure_to_set = int(float(x.get()))
                # self.elveflow_handler.setPressure(i, pressure_to_set)
                # TODO: PID control
                x.set(str(pressure_to_set))
                self.errorlogger.debug(self.elveflow_handler.peekOne())
            except ValueError:
                pass
                # self.elveflow_handler.setPressure(i, 0)

    def set_axis_limits(self):
        for i, x in enumerate(self.axis_limits):
            try:
                value = float(x.get())
                x.set(str(value))
                self.axis_limits_numbers[i] = value
            except ValueError:
                x.set("")
                self.axis_limits_numbers[i] = None
        self.update_plot()
