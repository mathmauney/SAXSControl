# encoding: utf-8
"""This module implements custom tkinter widgets for the SAXS control panel."""

import tkinter as tk
import math
import tkinter.font
import logging
import csv
from tkinter.scrolledtext import ScrolledText
import numpy as np
import FileIO
import threading
import time
import os.path
from queue import Queue, Empty as Queue_Empty
import matplotlib
matplotlib.use('TkAgg') # noqa
from matplotlib import pyplot as plt


class COMPortSelector(tk.Listbox):
    def updatelist(self, COMList):
        self.delete(0, tk.END)
        for item in COMList:
            self.insert(tk.END, item.device+"  "+item.description)


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
    """This class allows you to log to a Tkinter Text or ScrolledText widget.

    Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    """

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


class MiscLogger(ScrolledText):
    def append(self, msg):
        self.configure(state='normal')
        self.insert(tk.END, msg + '\n')
        self.configure(state='disabled')
        # Autoscroll to the bottom
        self.yview(tk.END)


class Toggle(tk.Label):
    # https://www.reddit.com/r/learnpython/comments/7sx953/how_to_add_a_toggle_switch_in_tkinter/
    def __init__(self, master=None, variable=None, onFile='clicked_button.png', offFile='unclicked_button.png', onToggleOn=None, onToggleOff=None, defaultValue=None, **kwargs):
        tk.Label.__init__(self, master, **kwargs)

        self.ON = onFile
        self.OFF = offFile

        if variable is None:
            self.var = tk.BooleanVar()
            self.set(True)
        else:
            self.var = variable
        self.images = [tk.PhotoImage(file=self.OFF), tk.PhotoImage(file=self.ON)]
        self.get, self.set = self.var.get, self.var.set
        # on click, swap variable if not disabled
        self.bind('<Button-1>', lambda e: self.set(not (self.get() ^ (self['state'] == tk.DISABLED))))
        self.var.trace('w', lambda *_: self.config(image=self.images[self.get()]))

        if defaultValue is None:
            if variable is None:
                defaultValue = True
            else:
                defaultValue = variable.get()
        self.set(defaultValue)

        self.onToggleOn = onToggleOn
        self.onToggleOff = onToggleOff
        self.var.trace("w", lambda *_: self.doToggle())

    def doToggle(self):
        if self['state'] != tk.DISABLED:
            if self.get():
                # we just toggled on
                if self.onToggleOn is not None:
                    self.onToggleOn()
            else:
                if self.onToggleOff is not None:
                    self.onToggleOff()


class PressureVolumeToggle(Toggle):
    ON = 'Pressure_button.png'
    OFF = 'Volume_button.png'

    def __init__(self, master=None, variable=None, **kwargs):
        Toggle.__init__(self, master, variable, self.ON, self.OFF, **kwargs)


class ElveflowDisplay(tk.Canvas):
    """Build a widget to show the Elveflow graph."""
    POLLING_PERIOD = 1
    PADDING = 2
    OUTPUT_FOLDER = "Elveflow"

    def __init__(self, window, height, width, errorlogger, **kwargs):
        """Start the FluidLevel object with default paramaters."""
        super().__init__(window, **kwargs)

        self.window = window
        # variables attached to tkinter elements
        self.dataXLabel_var = tk.StringVar()
        self.dataYLabel_var = tk.StringVar()
        self.sensorTypes_var = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.pressureValue_var = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.isPressure_var = [tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar()]
        self.pressureSettingActive_var = [tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar()]
        self.setPressureStop_flag = [None, None, None, None]
        self.axisLimits_var = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.axisLimits_numbers = [None, None, None, None]
        self.sourcename_var = tk.StringVar()
        self.saveFileName_var = tk.StringVar()
        self.saveFileNameSuffix_var = tk.StringVar()
        (self.kp_var, self.ki_var, self.kd_var) = (tk.StringVar(), tk.StringVar(), tk.StringVar())
        self.ki_var.set(50)

        self.dataTitle = "Elveflow data"
        self.errorlogger = errorlogger
        self.saveFile = None
        self.saveFileWriter = None
        self.shutdown = False

        self.starttime = int(time.time())
        self.errorlogger.info("start time is %d" % self.starttime)

        self.run_flag = threading.Event()
        self.save_flag = threading.Event()
        self.saveFileNameSuffix_var.set("_%d.csv" % time.time())

        # tkinter elements
        # https://stackoverflow.com/questions/31440167/placing-plot-on-tkinter-main-window-in-python
        remaining_width_per_column = width / 9
        dpi = 96  # this shouldn't matter too much (because we normalize against it) except in how font sizes are handled in the plot
        self.the_fig = plt.Figure(figsize=(width*2/3/dpi, height*3/4/dpi), dpi=dpi)
        self.ax = self.the_fig.add_subplot(111)
        self.ax.set_title(self.dataTitle, fontsize=16)

        rowcounter = 0
        self.start_button = tk.Button(self, text='Start Connection', command=self.start)
        self.start_button.grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        print(self.start_button)
        self.stop_button = tk.Button(self, text='Stop Connection', command=self.stop)
        self.stop_button.grid(row=rowcounter, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1
        # self.clear_button = tk.Button(self, text='Clear Graph', command=self.clear_graph)
        # self.clear_button.grid(row=0, column=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        # # TODO: make the clear button actually work

        tk.Label(self, text="Reading from:").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.sourcename_entry = tk.Entry(self, textvariable=self.sourcename_var, justify="left")
        if not FileIO.USE_SDK:
            self.sourcename_entry.config(state="readonly")
        self.sourcename_entry.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        fontsize = tkinter.font.Font(font=self.sourcename_entry['font'])['size']
        self.sourcename_entry.config(width=2 * int(remaining_width_per_column / fontsize))  # width is in units of font size
        rowcounter += 1

        if FileIO.USE_SDK:
            tk.Label(self, text="Sensors 1, 2:").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            tk.Label(self, text="Sensors 3, 4:").grid(row=rowcounter+1, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.sensorTypes_optionmenu = [None, None, None, None]
            for i in range(4):
                self.sensorTypes_optionmenu[i] = tk.OptionMenu(self, self.sensorTypes_var[i], None)
                self.sensorTypes_optionmenu[i]['menu'].delete(0, 'end')  # there's a default empty option, so get rid of that first
                self.sensorTypes_optionmenu[i].config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size
                self.sensorTypes_optionmenu[i].grid(row=rowcounter+i//2, column=2+(i % 2), padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
                self.sensorTypes_var[i].set("none")
                for item in FileIO.SDK_SENSOR_TYPES:
                    self.sensorTypes_optionmenu[i]['menu'].add_command(label=item,
                                                                       command=lambda i=i, item=item: self.sensorTypes_var[i].set(item))  # weird default argument for scoping
            rowcounter += 2

        tkinter.ttk.Separator(self, orient=tk.HORIZONTAL).grid(row=rowcounter, column=1, columnspan=3, sticky='ew', padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        tk.Label(self, text="X axis").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.dataXLabel_optionmenu = tk.OptionMenu(self, self.dataXLabel_var, None)
        self.dataXLabel_optionmenu.config(width=int(remaining_width_per_column * 2 / fontsize))  # width is in units of font size
        self.dataXLabel_optionmenu.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        tk.Label(self, text="Y axis").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.dataYLabel_optionmenu = tk.OptionMenu(self, self.dataYLabel_var, None)
        self.dataYLabel_optionmenu.config(width=int(remaining_width_per_column * 2 / fontsize))
        self.dataYLabel_optionmenu.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        if FileIO.USE_SDK:
            self.startSaving_button = tk.Button(self, text='Start Saving Data', command=self.start_saving)
            self.startSaving_button.grid(row=rowcounter, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.stopSaving_button = tk.Button(self, text='Stop Saving Data', command=self.stop_saving)
            self.stopSaving_button.grid(row=rowcounter, column=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            rowcounter += 1

            tk.Label(self, text="Output filename:").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.saveFileName_entry = tk.Entry(self, textvariable=self.saveFileName_var, justify="left")
            self.saveFileName_entry.grid(row=rowcounter, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            tk.Label(self, textvariable=self.saveFileNameSuffix_var).grid(row=rowcounter, column=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            rowcounter += 1

        if FileIO.USE_SDK:
            tkinter.ttk.Separator(self, orient=tk.HORIZONTAL).grid(row=rowcounter, column=1, columnspan=3, sticky='ew', padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            rowcounter += 1

            self.setElveflow_frame = tk.Frame(self, bg="#aaddff")
            self.setElveflow_frame.grid(row=rowcounter, column=1, columnspan=3, padx=ElveflowDisplay.PADDING*3, pady=ElveflowDisplay.PADDING*3)

            self.pressureValue_entry = [None, None, None, None]
            self.isPressure_toggle = [None, None, None, None]
            self.pressureSettingActive_toggle = [None, None, None, None]

            for i in range(4):
                self.isPressure_toggle[i] = PressureVolumeToggle(self.setElveflow_frame, variable=self.isPressure_var[i])
                self.isPressure_toggle[i].grid(row=0, column=i, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
                self.pressureValue_entry[i] = tk.Entry(self.setElveflow_frame, textvariable=self.pressureValue_var[i], justify="left")
                self.pressureValue_entry[i].config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size
                self.pressureValue_entry[i].grid(row=1, column=i, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
                self.pressureValue_var[i].set("")
                self.isPressure_var[i].set(True)
                self.pressureSettingActive_toggle[i] = Toggle(self.setElveflow_frame, defaultValue=False, text='Set', variable=self.pressureSettingActive_var[i], compound=tk.CENTER,
                                                              onToggleOn=lambda i=i: self.start_pressure(channel=i+1, isPressure=self.isPressure_var[i].get()), onToggleOff=lambda i=i: self.stop_pressure(channel=i+1))
                self.pressureSettingActive_toggle[i].grid(row=2, column=i, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)

            tk.Label(self.setElveflow_frame, text="P, I, D constants:").grid(row=3, column=0, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.kp_entry = tk.Entry(self.setElveflow_frame, textvariable=self.kp_var)
            self.kp_entry.grid(row=3, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.kp_entry.config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size
            self.ki_entry = tk.Entry(self.setElveflow_frame, textvariable=self.ki_var)
            self.ki_entry.grid(row=3, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.ki_entry.config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size
            self.kd_entry = tk.Entry(self.setElveflow_frame, textvariable=self.kd_var)
            self.kd_entry.grid(row=3, column=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.kd_entry.config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size

            rowcounter += 1

        tkinter.ttk.Separator(self, orient=tk.HORIZONTAL).grid(row=rowcounter, column=1, columnspan=3, sticky='ew', padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        tk.Label(self, text="x axis limits:").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        tk.Label(self, text="y axis limits:").grid(row=rowcounter+1, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.axisLimits_entry = [None, None, None, None]
        for i in range(4):
            self.axisLimits_entry[i] = tk.Entry(self, textvariable=self.axisLimits_var[i], justify="left")
            self.axisLimits_entry[i].config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size
            self.axisLimits_entry[i].grid(row=rowcounter+i//2, column=2+(i % 2), padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.axisLimits_var[i].set("")
        rowcounter += 2
        self.axisLimits_button = tk.Button(self, text='Set graph limits (leave blank for auto)', command=self.set_axis_limits)  # TODO
        self.axisLimits_button.grid(row=rowcounter, column=1, columnspan=3, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
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
        self.dataXLabel_optionmenu.config(state=tk.DISABLED)
        self.dataYLabel_optionmenu.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if not FileIO.USE_SDK:
            self.sourcename_var.set("None")
        else:
            self.startSaving_button.config(state=tk.DISABLED)
            self.stopSaving_button.config(state=tk.DISABLED)
            self.saveFileName_entry.config(state=tk.DISABLED)
            for item in self.pressureSettingActive_toggle:
                item.config(state=tk.DISABLED)
            for item in self.pressureValue_entry:
                item.config(state=tk.DISABLED)
            self.saveFile = None
            self.saveFileWriter = None

    def populate_dropdowns(self):
        self.dataXLabel_optionmenu['menu'].delete(0, 'end')
        self.dataYLabel_optionmenu['menu'].delete(0, 'end')  # these two deletions shouldn't be necessary, but I'm afraid of weird race conditions that realistically won't happen even if they're possible
        for item in self.elveflow_handler.header:
            self.dataXLabel_optionmenu['menu'].add_command(label=item, command=lambda item=item: self.dataXLabel_var.set(item))  # weird default argument for scoping
            self.dataYLabel_optionmenu['menu'].add_command(label=item, command=lambda item=item: self.dataYLabel_var.set(item))

    def start(self):
        if self.elveflow_handler is not None:
            raise RuntimeError("the elveflow_handler is already running!")
        self.dataXLabel_optionmenu.config(state=tk.NORMAL)
        self.dataYLabel_optionmenu.config(state=tk.NORMAL)

        if FileIO.USE_SDK:
            self.sourcename_entry.config(state=tk.DISABLED)
            for item in self.pressureSettingActive_toggle:
                item.config(state=tk.NORMAL)
            for item in self.pressureValue_entry:
                item.config(state=tk.NORMAL)
            for item in self.sensorTypes_optionmenu:
                item.config(state=tk.DISABLED)

            self.elveflow_handler = FileIO.ElveflowHandler(sourcename=self.sourcename_var.get(),
                                                           errorlogger=self.errorlogger,
                                                           sensortypes=list(map(lambda x: FileIO.SDK_SENSOR_TYPES[x.get()], self.sensorTypes_var)),
                                                           starttime=self.starttime)
            self.sourcename_var.set(str(self.elveflow_handler.sourcename, encoding='ascii'))
        else:
            self.elveflow_handler = FileIO.ElveflowHandler()
            if self.elveflow_handler.sourcename is None:
                # abort if empty
                self._initialize_variables()
                return
            self.sourcename_var.set(self.elveflow_handler.sourcename)

        self.dataXLabel_optionmenu['menu'].delete(0, 'end')
        self.dataYLabel_optionmenu['menu'].delete(0, 'end')
        self.dataXLabel_var.set('')
        self.dataYLabel_var.set('')
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
                            self.saveFileWriter.writerow([str(dict[key]) for key in self.elveflow_handler.header])
                    time.sleep(ElveflowDisplay.POLLING_PERIOD)
            finally:
                try:
                    self.stop()
                    print("DONE WITH THIS THREAD, %s" % threading.current_thread())
                except RuntimeError:
                    print("Runtime error detected in display thread %s while trying to close. Ignoring." % threading.current_thread())
                self.run_flag.set()  # reset in preparation for if we start up the connection again

        self.the_thread = threading.Thread(target=pollElveflowThread, args=(self.run_flag, self.save_flag))
        self.the_thread.start()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        if FileIO.USE_SDK:
            self.startSaving_button.config(state=tk.NORMAL)
            self.saveFileName_entry.config(state=tk.NORMAL)
            self.saveFileNameSuffix_var.set("_%d.csv" % time.time())

    def stop(self, shutdown=False):
        self.run_flag.clear()
        if shutdown:
            self.shutdown = True
            # shutdown was a flag I was using to try to solve threading problems
            # I don't think it actually does anything, but at least it's not hurting anything, anyway

        if self.elveflow_handler is not None:
            self.elveflow_handler.stop()
        if FileIO.USE_SDK and not shutdown:
            # if we're actually exiting, no need to update the GUI
            self.sourcename_entry.config(state=tk.NORMAL)
            for item in self.sensorTypes_optionmenu:
                item.config(state=tk.NORMAL)
            for item in self.pressureSettingActive_var:
                item.set(False)
            for item in self.pressureSettingActive_toggle:
                item.config(state=tk.DISABLED)
            for item in self.pressureValue_entry:
                item.config(state=tk.DISABLED)
            for item in self.setPressureStop_flag:
                try:
                    item.set()
                except AttributeError:
                    pass
        self.stop_saving(shutdown=shutdown)
        if not shutdown:
            self._initialize_variables()

    def start_saving(self):
        if self.elveflow_handler.header is not None:
            self.save_flag.set()
            self.stopSaving_button.config(state=tk.NORMAL)
            self.startSaving_button.config(state=tk.DISABLED)
            self.saveFileName_entry.config(state=tk.DISABLED)
            self.saveFile = open(os.path.join(ElveflowDisplay.OUTPUT_FOLDER, self.saveFileName_var.get() + self.saveFileNameSuffix_var.get()), 'a', encoding="utf-8", newline='')
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
            self.stopSaving_button.config(state=tk.DISABLED)
            self.startSaving_button.config(state=tk.NORMAL)
            self.saveFileName_entry.config(state=tk.NORMAL)

        self.saveFileNameSuffix_var.set("_%d.csv" % time.time())

        if self.saveFile is not None:
            self.saveFile.close()

    def clear_graph(self):
        self.ax.clear()
        self.the_line = self.ax.plot([], [])[0]
        self.ax.set_title(self.dataTitle, fontsize=16)
        self.update_plot()
        print("graph CLEARED!")

    def update_plot(self):
        dataXLabel_var = self.dataXLabel_var.get()
        dataYLabel_var = self.dataYLabel_var.get()
        try:
            dataX = [elt[dataXLabel_var] for elt in self.data if not np.isnan(elt[dataXLabel_var]) and not np.isnan(elt[dataYLabel_var])]
            dataY = [elt[dataYLabel_var] for elt in self.data if not np.isnan(elt[dataXLabel_var]) and not np.isnan(elt[dataYLabel_var])]
            extremes = [np.nanmin(dataX), np.nanmax(dataX), np.nanmin(dataY), np.nanmax(dataY)]
            if len(dataX) > 0:
                self.the_line.set_data(dataX, dataY)
            self.ax.set_xlabel(self.dataXLabel_var.get(), fontsize=14)
            self.ax.set_ylabel(self.dataYLabel_var.get(), fontsize=14)
        except (ValueError, KeyError):
            extremes = [*self.ax.get_xlim(), *self.ax.get_ylim()]

        limits = [item if item is not None else extremes[i]
                  for (i, item) in enumerate(self.axisLimits_numbers)]
        self.ax.set_xlim(*limits[0:2])
        self.ax.set_ylim(*limits[2:4])

        # HACK:
        # self.canvas.draw doesn't shut down properly for whatever reason when clicking the exit button
        # so instead, spawn a daemon thread (a thread that automatically dies at the end of the program -
        # we haven't been using them elsewhere because they don't allow for graceful exiting/handling of
        # acquired resources, but I think it shouldn't matter if we crash-exit drawing to the screen
        # because we're closing the screen anyway, even if it becomes corrupted)
        def thisIsDumb():
            self.canvas.draw()
        tempThread = threading.Thread(target=thisIsDumb, daemon=True)
        tempThread.start()
        print(tempThread)

    def start_pressure(self, channel=1, isPressure=True):
        i = channel - 1
        pressureValue = self.pressureValue_var[i]
        self.setPressureStop_flag[i] = threading.Event()
        self.setPressureStop_flag[i].clear()
        try:
            if isPressure:
                pressure_to_set = int(float(pressureValue.get()))
                pressureValue.set(str(pressure_to_set))
                self.elveflow_handler.setPressureLoop(channel, pressure_to_set, interruptEvent=self.setPressureStop_flag[i],
                                                      onFinish=lambda: self.pressureSettingActive_var[i].set(False))
            else:  # volume control
                if self.sensorTypes_var[i].get() == "none":
                    self.errorlogger.error("Channel %d flow meter is not turned on" % channel)
                    self.pressureSettingActive_var[i].set(False)
                    return
                try:
                    kp = float(self.kp_var.get())
                    self.kp_var.set(str(kp))
                except ValueError:
                    kp = 0
                    self.kp_var.set("0.0")
                try:
                    ki = float(self.ki_var.get())
                    self.ki_var.set(str(ki))
                except ValueError:
                    ki = 0
                    self.ki_var.set("0.0")
                try:
                    kd = float(self.kd_var.get())
                    self.kd_var.set(str(kd))
                except ValueError:
                    kd = 0
                    self.kd_var.set("0.0")
                flowrate_to_set = int(float(pressureValue.get()))
                pressureValue.set(str(flowrate_to_set))
                self.elveflow_handler.setVolumeLoop(channel, flowrate_to_set, interruptEvent=self.setPressureStop_flag[i], pid_constants=(kp, ki, kd))
        except ValueError:
            self.errorlogger.error("unknown value for channel %i" % channel)
            pressureValue.set("")
            self.pressureSettingActive_var[i].set(False)

    def stop_pressure(self, channel=1):
        '''stop changing the pressure. Pressure-controlled systems will remain at whatever value it is currently set at;
        volume-controlled systems will drop to zero pressure'''
        i = channel - 1
        self.errorlogger.info('stopping %d', i)
        try:
            self.setPressureStop_flag[i].set()
        except AttributeError:
            pass

    def set_axis_limits(self):
        for i, x in enumerate(self.axisLimits_var):
            try:
                value = float(x.get())
                x.set(str(value))
                self.axisLimits_numbers[i] = value
            except ValueError:
                x.set("")
                self.axisLimits_numbers[i] = None
        self.update_plot()


class FlowPath(tk.Canvas):
    class Valve:
        def __init__(self, canvas, x, y, name):
            self.x = x
            self.y = y
            self.name = name
            self.big_radius = 100 * canvas.valve_scale
            self.small_radius = 20 * canvas.valve_scale
            self.offset = 60 * canvas.valve_scale
            self.arc_radius = self.offset + self.small_radius
            self.position = -1
            self.rads = math.radians(60)
            self.canvas = canvas
            self.big_circle = canvas.create_circle(x, y, self.big_radius, fill='dimgray', outline='dimgray', tag=self.name)
            self.center_circle = canvas.create_circle(x, y, self.small_radius, fill='dimgray', outline='dimgray', tag=self.name)
            self.circles = []
            self.fluid_lines = []
            for i in range(0, 6):
                circle = canvas.create_circle(x+self.offset*math.cos(i*self.rads), y+self.offset*math.sin(i*self.rads), self.small_radius, fill='white', outline='white', tag=self.name)
                self.circles.append(circle)
                self.fluid_lines.append([])
            self.fluid_lines.append([])  # for center circle

        def connect(self, link_object, position):
            """Link a line to an in or out port of the valve"""
            if position == 'center':
                position = 6
            self.fluid_lines[position].append(link_object)   # TODO: Add way to associate real valve to diagram

    class SelectionValve(Valve):
        def __init__(self, canvas, x, y, name):
            super().__init__(canvas, x, y, name)
            self.canvas.itemconfig(self.center_circle, fill='white', outline='white', tag=self.name)
            self.color = 'black'
            for i in range(0, 6):
                self.canvas.itemconfig(self.circles[i], tag=self.name+str(i))
                self.canvas.tag_bind(self.name+str(i), '<Button-1>', lambda event, position=i: self.set_manual_position(position))

        def set_position(self, position, color=None):
            if color is not None:
                self.color = color
            for line in self.fluid_lines[position]:
                self.canvas.itemconfig(line, fill=self.color, outline=self.color)
            self.canvas.itemconfig(self.circles[self.position], fill='white', outline='white')
            self.canvas.itemconfig(self.center_circle, fill=self.color, outline=self.color)
            for line in self.fluid_lines[6]:
                self.canvas.itemconfig(line, fill=self.color, outline=self.color)
            self.position = position
            try:
                self.canvas.delete(self.channel)
            except AttributeError:
                pass
            self.canvas.itemconfig(self.circles[position], fill=self.color, outline=self.color)
            self.channel = self.canvas.create_polygon([self.x+self.small_radius*math.sin(position*self.rads), self.y-self.small_radius*math.cos(position*self.rads),
                                                       self.x+self.offset*math.cos(position*self.rads)+self.small_radius*math.sin(position*self.rads), self.y+self.offset*math.sin(position*self.rads)-self.small_radius*math.cos(position*self.rads),
                                                       self.x+self.offset*math.cos(position*self.rads)-self.small_radius*math.sin(position*self.rads), self.y+self.offset*math.sin(position*self.rads)+self.small_radius*math.cos(position*self.rads),
                                                       self.x-self.small_radius*math.sin(position*self.rads), self.y+self.small_radius*math.cos(position*self.rads)],
                                                      fill=self.color, outline=self.color)
            for i in range(0, 6):
                self.canvas.tag_raise(self.circles[i])

        def set_manual_position(self, position):    # TODO: Add in actual valve switching
            if self.canvas.is_unlocked:
                self.set_position(position)

    class SampleValve(Valve):
        def __init__(self, canvas, x, y, name):
            super().__init__(canvas, x, y, name)
            self.inner_circle = self.canvas.create_circle(x, y, self.offset-self.small_radius, fill='dimgray', outline='dimgray', tag=self.name)
            self.right_color = 'red'
            self.left_color = 'black'
            self.canvas.tag_bind(name, '<Button-1>', lambda event: self.set_manual_position(self.position+1))

        def set_position(self, position, **kwargs):
            self.left_color = kwargs.pop('left_color', self.left_color)
            self.right_color = kwargs.pop('right_color', self.right_color)
            self.position = position % 2
            try:
                self.canvas.delete(self.arc1)
                self.canvas.delete(self.arc2)
            except AttributeError:
                pass
            self.canvas.itemconfig(self.circles[0], fill=self.right_color, outline=self.right_color)
            for line in self.fluid_lines[0]:
                self.canvas.itemconfig(line, fill=self.right_color, outline=self.right_color)
            self.canvas.itemconfig(self.circles[3], fill=self.left_color, outline=self.left_color)
            for line in self.fluid_lines[3]:
                self.canvas.itemconfig(line, fill=self.left_color, outline=self.left_color)
            if self.position == 1:
                self.arc1 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=120, extent=60, fill=self.left_color, outline=self.left_color)
                self.arc2 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=0, extent=60, fill=self.right_color, outline=self.right_color)
                self.canvas.tag_lower(self.arc1)
                self.canvas.tag_lower(self.arc2)
                self.canvas.tag_lower(self.big_circle)
                self.canvas.itemconfig(self.circles[1], fill='white', outline='white')
                self.canvas.itemconfig(self.circles[2], fill='white', outline='white')
                self.canvas.itemconfig(self.circles[4], fill=self.left_color, outline=self.left_color)
                self.canvas.itemconfig(self.circles[5], fill=self.right_color, outline=self.right_color)
                for line in self.fluid_lines[5]:
                    self.canvas.itemconfig(line, fill=self.right_color, outline=self.right_color)
                self.canvas.itemconfig(self.circles[3], fill=self.left_color, outline=self.left_color)
                for line in self.fluid_lines[4]:
                    self.canvas.itemconfig(line, fill=self.left_color, outline=self.left_color)
            elif self.position == 0:
                self.arc1 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=180, extent=60, fill=self.left_color, outline=self.left_color)
                self.arc2 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=300, extent=60, fill=self.right_color, outline=self.right_color)
                self.canvas.tag_lower(self.arc1)
                self.canvas.tag_lower(self.arc2)
                self.canvas.tag_lower(self.big_circle)
                self.canvas.itemconfig(self.circles[4], fill='white', outline='white')
                self.canvas.itemconfig(self.circles[5], fill='white', outline='white')
                self.canvas.itemconfig(self.circles[2], fill=self.left_color, outline=self.left_color)
                self.canvas.itemconfig(self.circles[1], fill=self.right_color, outline=self.right_color)
                for line in self.fluid_lines[1]:
                    self.canvas.itemconfig(line, fill=self.right_color, outline=self.right_color)
                self.canvas.itemconfig(self.circles[3], fill=self.left_color, outline=self.left_color)
                for line in self.fluid_lines[2]:
                    self.canvas.itemconfig(line, fill=self.left_color, outline=self.left_color)
            for i in range(0, 6):
                self.canvas.tag_raise(self.circles[i])

        def set_manual_position(self, position):    # TODO: Add in actual valve switching
            if self.canvas.is_unlocked:
                self.set_position(position)
                print('Set position %i' % position)

    class InjectionValve(Valve):
        def __init__(self, canvas, x, y, name):
            super().__init__(canvas, x, y, name)
            self.color1 = 'white'
            self.color2 = 'white'
            self.color3 = 'white'
            self.name = name
            self.position = 1
            self.inner_circle = self.canvas.create_circle(x, y, self.offset-self.small_radius, fill='dimgray', outline='dimgray', tag=self.name)
            self.canvas.tag_bind(name, '<Button-1>', lambda event: self.set_manual_position(self.position+1))

        def set_position(self, position, **kwargs):
            self.color1 = kwargs.pop('color1', self.color1)
            self.color2 = kwargs.pop('color1', self.color2)
            self.color3 = kwargs.pop('color1', self.color3)
            self.position = position % 2
            try:
                self.canvas.delete(self.arc1)
                self.canvas.delete(self.arc2)
                self.canvas.delete(self.arc3)
            except AttributeError:
                pass
            if self.position == 1:
                self.arc1 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=300, extent=60, fill=self.color2, outline=self.color2)
                self.arc2 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=180, extent=60, fill=self.color1, outline=self.color1)
                self.arc3 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=60, extent=60, fill=self.color3, outline=self.color3)
                self.canvas.tag_lower(self.arc1)
                self.canvas.tag_lower(self.arc2)
                self.canvas.tag_lower(self.arc3)
                self.canvas.tag_lower(self.big_circle)
                self.canvas.itemconfig(self.circles[0], fill=self.color2, outline=self.color2)
                self.canvas.itemconfig(self.circles[1], fill=self.color2, outline=self.color2)
                self.canvas.itemconfig(self.circles[2], fill=self.color1, outline=self.color1)
                self.canvas.itemconfig(self.circles[3], fill=self.color1, outline=self.color1)
                self.canvas.itemconfig(self.circles[4], fill=self.color3, outline=self.color3)
                self.canvas.itemconfig(self.circles[5], fill=self.color3, outline=self.color3)
                for line in self.fluid_lines[0]:
                    if self.color2 != 'white':
                        self.canvas.itemconfig(line, fill=self.color2, outline=self.color2)
                for line in self.fluid_lines[1]:
                    if self.color2 != 'white':
                        self.canvas.itemconfig(line, fill=self.color2, outline=self.color2)
                for line in self.fluid_lines[2]:
                    if self.color1 != 'white':
                        self.canvas.itemconfig(line, fill=self.color1, outline=self.color1)
                for line in self.fluid_lines[3]:
                    if self.color1 != 'white':
                        self.canvas.itemconfig(line, fill=self.color1, outline=self.color1)
                for line in self.fluid_lines[4]:
                    if self.color3 != 'white':
                        self.canvas.itemconfig(line, fill=self.color3, outline=self.color3)
                for line in self.fluid_lines[5]:
                    if self.color3 != 'white':
                        self.canvas.itemconfig(line, fill=self.color3, outline=self.color3)
            elif self.position == 0:
                self.arc1 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=0, extent=60, fill=self.color3, outline=self.color3)
                self.arc2 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=240, extent=60, fill=self.color2, outline=self.color2)
                self.arc3 = self.canvas.create_arc(self.x-self.arc_radius, self.y-self.arc_radius, self.x+self.arc_radius, self.y+self.arc_radius, start=120, extent=60, fill=self.color1, outline=self.color1)
                self.canvas.tag_lower(self.arc1)
                self.canvas.tag_lower(self.arc2)
                self.canvas.tag_lower(self.arc3)
                self.canvas.tag_lower(self.big_circle)
                self.canvas.itemconfig(self.circles[0], fill=self.color3, outline=self.color3)
                self.canvas.itemconfig(self.circles[1], fill=self.color2, outline=self.color2)
                self.canvas.itemconfig(self.circles[2], fill=self.color2, outline=self.color2)
                self.canvas.itemconfig(self.circles[3], fill=self.color1, outline=self.color1)
                self.canvas.itemconfig(self.circles[4], fill=self.color1, outline=self.color1)
                self.canvas.itemconfig(self.circles[5], fill=self.color3, outline=self.color3)
                for line in self.fluid_lines[1]:
                    if self.color2 != 'white':
                        self.canvas.itemconfig(line, fill=self.color2, outline=self.color2)
                for line in self.fluid_lines[2]:
                    if self.color2 != 'white':
                        self.canvas.itemconfig(line, fill=self.color2, outline=self.color2)
                for line in self.fluid_lines[3]:
                    if self.color1 != 'white':
                        self.canvas.itemconfig(line, fill=self.color1, outline=self.color1)
                for line in self.fluid_lines[4]:
                    if self.color1 != 'white':
                        self.canvas.itemconfig(line, fill=self.color1, outline=self.color1)
                for line in self.fluid_lines[5]:
                    if self.color3 != 'white':
                        self.canvas.itemconfig(line, fill=self.color3, outline=self.color3)
                for line in self.fluid_lines[0]:
                    if self.color3 != 'white':
                        self.canvas.itemconfig(line, fill=self.color3, outline=self.color3)
            self.canvas.tag_raise(self.arc1)
            self.canvas.tag_raise(self.arc2)
            self.canvas.tag_raise(self.arc3)
            self.canvas.tag_raise(self.inner_circle)
            for i in range(0, 6):
                self.canvas.tag_raise(self.circles[i])

        def set_manual_position(self, position):    # TODO: Add in actual valve switching
            if self.canvas.is_unlocked:
                self.set_position(position)

    class FluidLevel():
        """Build a widget to show the fluid level in a syringe."""

        def __init__(self, canvas, x, y, **kwargs):
            """Start the FluidLevel object with default paramaters."""
            self.color = kwargs.pop('color', 'blue')
            self.background = kwargs.pop('background', 'white')
            self.orientation = kwargs.pop('orientation', 'left')
            self.name = kwargs.pop('name', '')
            self.canvas = canvas
            border = kwargs.pop('border', 10)
            # Use pop to remove kwargs that aren't a part of Canvas
            width = kwargs.get('width', 150)
            height = kwargs.get('height', 50)
            self.canvas.create_rectangle(x, y, x+width, y+height, fill="grey", outline="grey", tag=self.name)
            self.max = self.canvas.create_rectangle(x+border, y+border, x+width-border, y+height-border, fill=self.background, outline=self.background, tag=self.name)
            self.level = self.canvas.create_rectangle(x+border, y+border, x+border, y+height-border, fill=self.background, outline=self.background, tag=self.name)

        def update(self, percent):
            """Update the fluid level to s given value."""
            percent = min(percent, 100)
            percent = max(percent, 0)
            x0, y0, x1, y1 = self.canvas.coords(self.max)
            if self.orientation == 'left':
                x1 = round((x1-x0)*percent/100) + x0
            elif self.orientation == 'right':
                x0 = x1 - round((x1-x0)*percent/100)
            self.canvas.coords(self.level, x0, y0, x1, y1)
            self.percent = percent
            if x1 == x0:
                self.canvas.itemconfig(self.level, fill='white', outline='white')
            else:
                self.canvas.itemconfig(self.level, fill=self.color, outline=self.color)

    class Lock():
        def __init__(self, canvas, x, y):
            self.x = x
            self.y = y
            self.canvas = canvas
            self.size = 100 * self.canvas.lock_scale
            self.state = 'locked'
            self.color = 'gold'
            self.canvas.create_rectangle(x, y+.8*self.size, x+self.size, y+1.8*self.size, fill=self.color, outline='', tag='lock')
            self.movable_rectangle = self.canvas.create_rectangle(x+.1*self.size, y+.4*self.size, x+.3*self.size, y+self.size, fill=self.color, outline='', tag='lock')
            self.canvas.create_rectangle(x+.7*self.size, y+.4*self.size, x+.9*self.size, y+self.size, fill=self.color, outline='', tag='lock')
            self.moveable_arc1 = self.canvas.create_arc(x+.1*self.size, y, x+.9*self.size, y+.8*self.size, start=0, extent=180, fill=self.color, outline='', tag='lock')
            self.moveable_arc2 = self.canvas.create_arc(x+.3*self.size, y+.2*self.size, x+.7*self.size, y+.6*self.size, start=0, extent=180, fill=self.canvas['background'], outline='', tag='lock')

        def toggle(self, state=None):
            if state is not None:
                self.state = state
            elif self.state == 'locked':
                self.state = 'unlocked'
            else:
                self.state = 'locked'
            dist = .6*self.size
            if self.state == 'unlocked':
                self.canvas.move(self.movable_rectangle, 2*dist, 0)
                self.canvas.move(self.moveable_arc1, dist, 0)
                self.canvas.move(self.moveable_arc2, dist, 0)
            elif self.state == 'locked':
                self.canvas.move(self.movable_rectangle, -2*dist, 0)
                self.canvas.move(self.moveable_arc1, -dist, 0)
                self.canvas.move(self.moveable_arc2, -dist, 0)
            else:
                raise ValueError('Invalid lock state')

    def __init__(self, window, **kwargs):
        super().__init__(window, **kwargs)
        self.is_unlocked = False
        self.valve_scale = 2/3
        self.lock_scale = .3
        self.fluid_line_width = 20
        self.window = window
        self.lock = self.Lock(self, 10, 10)
        self.tag_bind('lock', '<Button-1>', lambda event: self.lock_popup())
        # Add Elements
        self.draw_pumps()
        self.draw_valves()
        self.draw_loops()
        self.draw_fluid_lines()
        self.initialize()
        # Scale for computers smaller than 1800 log_width
        scale = self.window.winfo_screenwidth()/1920
        self.scale("all", 0, 0, scale, scale)
        self.config(width=1800*scale, height=300*scale)

    def draw_pumps(self):
        self.pump1 = self.FluidLevel(self, 0, 125, height=50, color='black', orientation='right', name='pump')

    def draw_valves(self):
        self.valve1 = self.InjectionValve(self, 300, 150, 'valve1')
        self.valve2 = self.SelectionValve(self, 700, 150, 'valve2')
        self.valve3 = self.SampleValve(self, 1100, 150, 'valve3')
        self.valve4 = self.SelectionValve(self, 1500, 150, 'valve4')

    def draw_loops(self):
        self.sample_level = self.FluidLevel(self, 1025, 0, height=30, color='red', background='black', orientation='right', border=0)
        self.buffer_level = self.FluidLevel(self, 1025, 250, height=30, color='cyan', background='black', orientation='right', border=0)

    def draw_fluid_lines(self):
        # Line from syringe to valve 1
        self.syringe_line = self.create_fluid_line('x', 150, 150, 100)
        self.tag_lower(self.syringe_line)
        self.valve1.connect(self.syringe_line, 3)
        # From Valve 1 to Valve 2
        x0, y0, x1, y1 = self.coords(self.valve1.circles[4])
        x_avg = math.floor((x0 + x1) / 2)
        self.oil_line1 = self.create_fluid_line('y', x_avg, y0, -50)
        self.oil_line2 = self.create_fluid_line('x', x_avg, y0-50, 400)
        self.oil_line3 = self.create_fluid_line('y', x_avg+400, y0-50, 50)
        self.valve1.connect(self.oil_line1, 4)
        self.valve1.connect(self.oil_line2, 4)
        self.valve1.connect(self.oil_line3, 4)
        # From Valve 1 to Refill Oil
        x0, y0, x1, y1 = self.coords(self.valve1.circles[2])
        x_avg = math.floor((x0 + x1) / 2)
        self.oil_line3 = self.create_fluid_line('y', x_avg, y1, 50)

    def initialize(self):
        self.pump1.update(25)
        self.sample_level.update(25)
        self.buffer_level.update(25)
        self.valve1.set_position(0, color1='black')
        self.valve2.set_position(4, color='black')
        self.valve3.set_position(1)
        self.valve4.set_position(0, color='red')

    def create_circle(self, x, y, r, **kwargs):
        return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)

    def create_fluid_line(self, direction, x, y, length, **kwargs):
        width = kwargs.pop('width', self.fluid_line_width)
        color = kwargs.pop('color', 'black')
        r = width/2
        if direction == 'x':
            if length > 0:
                return self.create_rectangle(x-r, y-r, x+length+r, y+r, fill=color, outline=color)
            else:
                return self.create_rectangle(x+length-r, y-r, x+r, y+r, fill=color, outline=color)
        elif direction == 'y':
            if length > 0:
                return self.create_rectangle(x-r, y-r, x+r, y+length+r, fill=color, outline=color)
            else:
                return self.create_rectangle(x-r, y+length-r, x+r, y+r, fill=color, outline=color)

    def set_unlock_state(self, state=None):
        if state is None:
            self.is_unlocked = not self.is_unlocked
        else:
            self.is_unlocked = state
        if self.is_unlocked:
            self.lock.toggle('unlocked')
        else:
            self.lock.toggle('locked')

    def manual_switch_lock(self):
        if self.is_unlocked:
            self.is_unlocked = False
        else:
            self.lock_popup()

    def lock_popup(self):
        def check_password(password):
            if password == 'asaxsisgr8':
                self.set_unlock_state(True)
                win.destroy()
        if self.is_unlocked:
            self.set_unlock_state(False)
        else:
            print('Test')
            win = tk.Toplevel()
            win.wm_title("Unlock?")
            label = tk.Label(win, text='Password?')
            label.grid(row=0, column=0)
            pass_entry = tk.Entry(win, show='*')
            pass_entry.grid(row=0, column=1)
            pass_entry.focus()
            pass_entry.bind("<Return>", lambda event: check_password(pass_entry.get()))
            ok_button = tk.Button(win, text="Unlock", command=lambda: check_password(pass_entry.get()))
            ok_button.grid(row=1, column=0)
            cancel_button = tk.Button(win, text="Cancel", command=win.destroy)
            cancel_button.grid(row=1, column=1)
