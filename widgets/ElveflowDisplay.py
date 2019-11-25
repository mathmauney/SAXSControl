import tkinter as tk
import tkinter.font
import logging
import csv
import numpy as np
from hardware import FileIO
import threading
import time
import os.path
import warnings
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import pyplot as plt

warnings.filterwarnings("ignore", message="Attempting to set identical bottom==top")
warnings.filterwarnings("ignore", message="Attempting to set identical left==right")

logger = logging.getLogger('python')


class ElveflowDisplay(tk.Canvas):
    """Build a widget to show the Elveflow graph."""
    POLLING_PERIOD = 1
    PADDING = 2
    OUTPUT_FOLDER = "Elveflow"
    COLOR_Y1 = 'tab:red'
    COLOR_Y2 = 'tab:blue'
    COLOR_Y3 = 'xkcd:ochre'
    DEFAULT_X_LABEL = 'time [s]'
    DEFAULT_Y1_LABEL = 'Pressure 1 [mbar]'
    DEFAULT_Y2_LABEL = 'Volume flow rate 1 [µL/min]'
    DEFAULT_Y3_LABEL = 'Volume flow rate 4 [µL/min]'

    def __init__(self, window, height, width, elveflow_config, errorlogger, maingui, **kwargs):
        """Start the FluidLevel object with default paramaters."""
        super().__init__(window, **kwargs)

        self.window = window
        # variables attached to tkinter elements
        self.data_x_label_var = tk.StringVar()
        self.data_y1_label_var = tk.StringVar()
        self.data_y2_label_var = tk.StringVar()
        self.data_y3_label_var = tk.StringVar()
        self.sensorTypes_var = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.pressureValue_var = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.isPressure_var = [tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar()]
        self.pressureSettingActive_var = [tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar()]
        self.setPressureStop_flag = [None, None, None, None]
        self.axisLimits_var = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]  # x, y1, y2, y3
        self.axisLimits_numbers = [None, None, None, None, None, None, None, None]
        self.saveFileName_var = tk.StringVar()
        self.saveFileNameSuffix_var = tk.StringVar()
        self.maingui = maingui
        (self.kp_var, self.ki_var, self.kd_var) = (tk.StringVar(), tk.StringVar(), tk.StringVar())
        self.kp_var.set(50)
        self.ki_var.set(50)

        self.dataTitle = "Elveflow data"
        self.errorlogger = errorlogger
        self.elveflow_config = elveflow_config
        self.saveFile = None
        self.saveFileWriter = None
        self.started_shutting_down = False
        self.done_shutting_down = False

        self.starttime = int(time.time())
        self.errorlogger.debug("start time is %d" % self.starttime)

        self.exit_lock = threading.Lock() # to make shutdown not hang.
        self.run_flag = threading.Event()
        self.save_flag = threading.Event()
        self.saveFileNameSuffix_var.set("_%d.csv" % time.time())

        # tkinter elements
        # https://stackoverflow.com/questions/31440167/placing-plot-on-tkinter-main-window-in-python
        remaining_width_per_column = width / 9
        dpi = 96  # this shouldn't matter too much (because we normalize against it) except in how font sizes are handled in the plot
        self.the_fig = plt.Figure(figsize=(width*2/3/dpi, height*3/4/dpi), dpi=dpi)
        self.ax1 = self.the_fig.add_subplot(111)
        self.ax1.set_title(self.dataTitle, fontsize=16)
        self.ax2 = self.ax1.twinx()
        self.ax3 = self.ax1.twinx() # two right axes
        self.ax3.spines["right"].set_position(("outward", 60)) # offset second right axis

        rowcounter = 0
        self.start_button = tk.Button(self, text='Start Connection', command=self.start)
        self.start_button.grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.stop_button = tk.Button(self, text='Stop Connection', command=self.stop)
        self.stop_button.grid(row=rowcounter, column=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        # TODO: this is just a dummy element that is never displayed on screen. But I get the fontsize from it.
        self.sourcename_entry = tk.Entry(self, textvariable=None, justify="left")
        fontsize = tkinter.font.Font(font=self.sourcename_entry['font'])['size']

        tk.Label(self, text="X axis").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.data_x_label_optionmenu = tk.OptionMenu(self, self.data_x_label_var, None)
        self.data_x_label_optionmenu.config(width=int(remaining_width_per_column * 2 / fontsize))  # width is in units of font size
        self.data_x_label_optionmenu.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        tk.Label(self, text="Y axis (left)").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.data_y1_label_optionmenu = tk.OptionMenu(self, self.data_y1_label_var, None)
        self.data_y1_label_optionmenu.config(width=int(remaining_width_per_column * 2 / fontsize))
        self.data_y1_label_optionmenu.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        tk.Label(self, text="Y axis (right)").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.data_y2_label_optionmenu = tk.OptionMenu(self, self.data_y2_label_var, None)
        self.data_y2_label_optionmenu.config(width=int(remaining_width_per_column * 2 / fontsize))
        self.data_y2_label_optionmenu.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        rowcounter += 1

        tk.Label(self, text="Y axis (right 2)").grid(row=rowcounter, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.data_y3_label_optionmenu = tk.OptionMenu(self, self.data_y3_label_var, None)
        self.data_y3_label_optionmenu.config(width=int(remaining_width_per_column * 2 / fontsize))
        self.data_y3_label_optionmenu.grid(row=rowcounter, column=2, columnspan=2, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
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
        tk.Label(self, text="y axis (left) limits:").grid(row=rowcounter+1, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        tk.Label(self, text="y axis (right) limits:").grid(row=rowcounter+2, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        tk.Label(self, text="y axis (right 2) limits:").grid(row=rowcounter+3, column=1, padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
        self.axisLimits_entry = [None, None, None, None, None, None, None, None]
        for i in range(8):
            self.axisLimits_entry[i] = tk.Entry(self, textvariable=self.axisLimits_var[i], justify="left")
            self.axisLimits_entry[i].config(width=int(remaining_width_per_column / fontsize))  # width is in units of font size
            self.axisLimits_entry[i].grid(row=rowcounter+i//2, column=2+(i % 2), padx=ElveflowDisplay.PADDING, pady=ElveflowDisplay.PADDING)
            self.axisLimits_var[i].set("")
            self.axisLimits_entry[i].bind('<Return>', lambda event: self.set_axis_limits())
        rowcounter += 4
        self.axisLimits_button = tk.Button(self, text='Set graph limits (leave blank for auto)', command=self.set_axis_limits)
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
        self.the_line1 = self.ax1.plot([], [], color=ElveflowDisplay.COLOR_Y1)[0]
        self.the_line2 = self.ax2.plot([], [], color=ElveflowDisplay.COLOR_Y2)[0]
        self.the_line3 = self.ax3.plot([], [], color=ElveflowDisplay.COLOR_Y3)[0]
        self.data_x_label_optionmenu.config(state=tk.DISABLED)
        self.data_y1_label_optionmenu.config(state=tk.DISABLED)
        self.data_y2_label_optionmenu.config(state=tk.DISABLED)
        self.data_y3_label_optionmenu.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if not FileIO.USE_SDK:
            pass
            # self.sourcename_var.set("None")
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
        self.data_x_label_optionmenu['menu'].delete(0, 'end')
        self.data_y1_label_optionmenu['menu'].delete(0, 'end')
        self.data_y2_label_optionmenu['menu'].delete(0, 'end')
        self.data_y3_label_optionmenu['menu'].delete(0, 'end')  # these deletions shouldn't be necessary, but I'm afraid of weird race conditions that realistically won't happen even if they're possible
        for item in self.elveflow_handler.header:
            self.data_x_label_optionmenu['menu'].add_command(label=item, command=lambda item=item: self.data_x_label_var.set(item))  # weird default argument for scoping
            self.data_y1_label_optionmenu['menu'].add_command(label=item, command=lambda item=item: self.data_y1_label_var.set(item))
            self.data_y2_label_optionmenu['menu'].add_command(label=item, command=lambda item=item: self.data_y2_label_var.set(item))
            self.data_y3_label_optionmenu['menu'].add_command(label=item, command=lambda item=item: self.data_y3_label_var.set(item))

    def start(self):
        if self.elveflow_handler is not None:
            raise RuntimeError("the elveflow_handler is already running!")
        self.data_x_label_optionmenu.config(state=tk.NORMAL)
        self.data_y1_label_optionmenu.config(state=tk.NORMAL)
        self.data_y2_label_optionmenu.config(state=tk.NORMAL)
        self.data_y3_label_optionmenu.config(state=tk.NORMAL)

        if FileIO.USE_SDK:
            # self.sourcename_entry.config(state=tk.DISABLED)
            for item in self.pressureSettingActive_toggle:
                item.config(state=tk.NORMAL)
            for item in self.pressureValue_entry:
                item.config(state=tk.NORMAL)
            # for item in self.sensorTypes_optionmenu:
            #     item.config(state=tk.DISABLED)

            self.errorlogger.debug("The four sensors are %s" % [self.elveflow_config['sensor1_type'], self.elveflow_config['sensor2_type'], self.elveflow_config['sensor3_type'], self.elveflow_config['sensor4_type']])
            self.elveflow_handler = FileIO.ElveflowHandler(sourcename=self.elveflow_config['elveflow_sourcename'],
                                                           errorlogger=self.errorlogger,
                                                           sensortypes=list(map(lambda x: FileIO.SDK_SENSOR_TYPES[x],
                                                                                [self.elveflow_config['sensor1_type'], self.elveflow_config['sensor2_type'], self.elveflow_config['sensor3_type'], self.elveflow_config['sensor4_type']])),  # TODO: make this not ugly
                                                           )
            # self.sourcename_var.set(str(self.elveflow_handler.sourcename, encoding='ascii'))
        else:
            self.elveflow_handler = FileIO.ElveflowHandler()
            # if self.elveflow_handler.sourcename is None:
            #     # abort if empty
            #     self._initialize_variables()
            #     return
            # self.sourcename_var.set(self.elveflow_handler.sourcename)

        self.data_x_label_optionmenu['menu'].delete(0, 'end')
        self.data_y1_label_optionmenu['menu'].delete(0, 'end')
        self.data_y2_label_optionmenu['menu'].delete(0, 'end')
        self.data_y3_label_optionmenu['menu'].delete(0, 'end')
        self.data_x_label_var.set(ElveflowDisplay.DEFAULT_X_LABEL)
        self.data_y1_label_var.set(ElveflowDisplay.DEFAULT_Y1_LABEL)
        self.data_y2_label_var.set(ElveflowDisplay.DEFAULT_Y2_LABEL)
        self.data_y3_label_var.set(ElveflowDisplay.DEFAULT_Y3_LABEL)
        self.elveflow_handler.start(getheader_handler=self.populate_dropdowns)

        self.run_flag.set()  # reset in preparation for if we start up the connection again
        def pollElveflowThread(run_flag, save_flag):
            print("STARTING DISPLAY THREAD %s" % threading.current_thread())
            try:
                while True:
                    with self.exit_lock:
                        if not run_flag.is_set():
                            # simulate `while run_flag.is_set()` but protected by a lock
                            # really only useful during closedown
                            break
                        new_data = self.elveflow_handler.fetchAll()
                        self.data.extend(new_data)
                        self.update_plot()
                    if save_flag.is_set():
                        for dict_ in new_data:
                            self.saveFileWriter.writerow([str(dict_[key]) for key in self.elveflow_handler.header])
                    time.sleep(ElveflowDisplay.POLLING_PERIOD)
            finally:
                if self.started_shutting_down:
                    self.done_shutting_down = True
                else:
                    self.stop()
                print("DONE WITH THIS DISPLAY THREAD, %s" % threading.current_thread())

        self.the_thread = threading.Thread(target=pollElveflowThread, args=(self.run_flag, self.save_flag))
        self.the_thread.start()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        if FileIO.USE_SDK:
            self.startSaving_button.config(state=tk.NORMAL)
            self.saveFileName_entry.config(state=tk.NORMAL)
            self.saveFileNameSuffix_var.set("_%d.csv" % time.time())

    def stop(self, shutdown=False):
        import traceback
        self.errorlogger.debug(f"Elveflow Display is stopping now. Shutdown flag={shutdown}; current thread is {threading.current_thread()}")
        self.errorlogger.debug('\n'.join(traceback.format_stack()))
        if self.elveflow_handler is not None:
            self.elveflow_handler.stop()
        if FileIO.USE_SDK:
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
        if shutdown:
            self.started_shutting_down = True

            if not self.run_flag.is_set():
                # wait, there's no elveflow polling thread to set the done_shutting_down flag
                # so we have to do everything ourselves
                self.done_shutting_down = True

            # only clear the run flag after setting the started_shutting_down flag
            self.run_flag.clear()
        else:
            self.run_flag.clear()
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
            self.errorlogger.debug('started saving to %s' % self.saveFile.name)
        else:
            self.errorlogger.error('cannot start saving (header is unknown). Try again in a moment')

    def stop_saving(self, shutdown=False):
        if self.save_flag.is_set():
            self.errorlogger.debug('stopped saving')
        self.save_flag.clear()
        if FileIO.USE_SDK and not shutdown:
            self.stopSaving_button.config(state=tk.DISABLED)
            self.startSaving_button.config(state=tk.NORMAL)
            self.saveFileName_entry.config(state=tk.NORMAL)

        self.saveFileNameSuffix_var.set("_%d.csv" % time.time())

        if self.saveFile is not None:
            self.saveFile.close()

    def update_plot(self):
        data_x_label_var = self.data_x_label_var.get()
        data_y1_label_var = self.data_y1_label_var.get()
        data_y2_label_var = self.data_y2_label_var.get()
        data_y3_label_var = self.data_y3_label_var.get()
        self.ax1.set_xlabel(data_x_label_var, fontsize=14)
        self.ax1.set_ylabel(data_y1_label_var, fontsize=14, color=ElveflowDisplay.COLOR_Y1)
        self.ax2.set_ylabel(data_y2_label_var, fontsize=14, color=ElveflowDisplay.COLOR_Y2)
        self.ax3.set_ylabel(data_y3_label_var, fontsize=14, color=ElveflowDisplay.COLOR_Y3)
        try:
            data_x = np.array([elt[data_x_label_var] for elt in self.data])
            data_y1 = np.array([elt[data_y1_label_var] for elt in self.data])
            data_y2 = np.array([elt[data_y2_label_var] for elt in self.data])
            data_y3 = np.array([elt[data_y3_label_var] for elt in self.data])
            if data_x_label_var == self.elveflow_handler.header[0]:
                data_x -= self.starttime
            if data_y1_label_var == self.elveflow_handler.header[0]:
                data_y1 -= self.starttime
            if data_y2_label_var == self.elveflow_handler.header[0]:
                data_y2 -= self.starttime
            if data_y3_label_var == self.elveflow_handler.header[0]:
                data_y3 -= self.starttime
            extremes = [np.nanmin(data_x), np.nanmax(data_x), np.nanmin(data_y1), np.nanmax(data_y1), np.nanmin(data_y2), np.nanmax(data_y2), np.nanmin(data_y3), np.nanmax(data_y3)]
            if len(data_x) > 0:
                self.the_line1.set_data(data_x, data_y1)
                self.the_line2.set_data(data_x, data_y2)
                self.the_line3.set_data(data_x, data_y3)
        except (ValueError, KeyError):
            extremes = [*self.ax1.get_xlim(), *self.ax1.get_ylim(), *self.ax2.get_ylim(), *self.ax3.get_ylim()]
        if extremes[1] - extremes[0] == 0:
            extremes[1] += 1
        if extremes[3] - extremes[2] == 0:
            extremes[3] += 1
        if extremes[5] - extremes[4] == 0:
            extremes[5] += 1
        if extremes[7] - extremes[6] == 0:
            extremes[7] += 1

        limits = [item if item is not None else extremes[i]
                  for (i, item) in enumerate(self.axisLimits_numbers)]
        self.ax1.set_xlim(*limits[0:2])
        self.ax1.set_ylim(*limits[2:4])
        self.ax2.set_ylim(*limits[4:6])
        self.ax3.set_ylim(*limits[6:8])

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

        # also update the main tab's sheath pressure display
        # TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        try:
            self.maingui.initialize_sheath_display_var.set('Sheath pressure:\n%d' % self.data[-1][
                "Pressure %s [mbar]" %
                (FileIO.ELVEFLOW_DATA_COLUMNS["Pressure 1 [mbar]"] + int(self.elveflow_config["elveflow_sheath_channel"]) - 1)
                ])
        except IndexError:
            pass

    def start_pressure(self, channel=1, isPressure=True):
        i = channel - 1
        pressureValue = self.pressureValue_var[i]
        self.setPressureStop_flag[i] = threading.Event()
        self.setPressureStop_flag[i].clear()
        try:
            if isPressure:
                pressure_to_set = int(float(pressureValue.get()))
                pressureValue.set(str(pressure_to_set))
                self.elveflow_handler.set_pressure_loop(channel, pressure_to_set, interrupt_event=self.setPressureStop_flag[i],
                                                        on_finish=lambda: self.pressureSettingActive_var[i].set(False))
            else:  # volume control
                if self.elveflow_config['sensor%i_type' % i] == "none":
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
                self.elveflow_handler.set_volume_loop(channel, flowrate_to_set, interrupt_event=self.setPressureStop_flag[i], pid_constants=(kp, ki, kd))
        except ValueError:
            self.errorlogger.error("unknown value for channel %i (pressure value is %r)" % (channel, pressureValue.get()))
            pressureValue.set("")
            self.pressureSettingActive_var[i].set(False)

    def stop_pressure(self, channel=1):
        '''stop changing the pressure. Pressure-controlled systems will remain at whatever value it is currently set at;
        volume-controlled systems will drop to zero pressure'''
        i = channel - 1
        # self.errorlogger.info('Stopping Elveflow Channel %d', channel)
        try:
            self.setPressureStop_flag[i].set()
        except AttributeError:
            pass

    def run_volume(self, channel=1, target=0, margin=0.15, stable_time=2):
        """run a volume PID loop until you are within +/- margin of the target
        for at least stable_time (in seconds) amount of time.

        Unlike start_pressure(isPressure=False), this stops when it reaches the
        target and blocks until then.
        """
        i = channel - 1
        pressureValue = self.pressureValue_var[i]
        self.setPressureStop_flag[i] = threading.Event()
        self.setPressureStop_flag[i].clear()

        if self.elveflow_config['sensor%i_type' % i] == "none":
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
        self.pressureValue_var[i].set(target)
        pressureValue.set(str(target))
        end_pressure = self.elveflow_handler.run_volume(channel, target, interrupt_event=self.setPressureStop_flag[i], pid_constants=(kp, ki, kd), margin=margin, stable_time=stable_time)
        self.errorlogger.info("Done setting the pressure in Channel %s to %.3f" % (channel, end_pressure))
        self.pressureValue_var[i].set(round(end_pressure))

    def set_axis_limits(self):
        for i, x in enumerate(self.axisLimits_var):
            try:
                value = float(x.get())
                x.set(str(value))
                self.axisLimits_numbers[i] = value
            except ValueError:
                x.set("")
                self.axisLimits_numbers[i] = None
        self.update_plot() # just, like, don't do this and also close the program at the same time

class Toggle(tk.Label):
    # https://www.reddit.com/r/learnpython/comments/7sx953/how_to_add_a_toggle_switch_in_tkinter/
    def __init__(self, master=None, variable=None, onFile='img/clicked_button.png', offFile='img/unclicked_button.png', onToggleOn=None, onToggleOff=None, defaultValue=None, **kwargs):
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
    ON = 'img/Pressure_button.png'
    OFF = 'img/Volume_button.png'

    def __init__(self, master=None, variable=None, **kwargs):
        Toggle.__init__(self, master, variable, self.ON, self.OFF, **kwargs)
