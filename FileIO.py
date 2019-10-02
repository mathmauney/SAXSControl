"""Module to support interfacing with an Elveflow either through the official SDK or by reading in datafiles as they are created."""
# encoding: utf8
import csv
import time
import threading
import math
from queue import Queue, Empty as Queue_Empty, Full as Queue_Full
from tkinter import filedialog
from simple_pid import PID

USE_SDK = True
SDK_SENSOR_TYPES = {
    "none": 0,
    "1.5 µL/min": 1,
    "7 µL/min": 2,
    "50 µL/min": 3,
    "80 µL/min": 4,
    "1000 µL/min": 5,
    "5000 µL/min": 6,
    # "Press_340_mbar": 7,
    # "Press_1_bar": 8,
    # "Press_2_bar": 9,
    # "Press_7_bar": 10,
    # "Press_16_bar": 11,
    # "Level": 12
}

if USE_SDK:
    from ctypes import c_int32, c_double, byref
    import sys
    import os.path
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Elveflow_SDK"))   # add the path of the LoadElveflow.py
    try:
        import Elveflow64 as Elveflow_SDK
    except OSError:
        print("Elveflow SDK not found, falling back to non-SDK version.")
        USE_SDK = False


class ElveflowHandlerESI:
    """A class that handles reading in Elveflow-generated log files."""

    SLEEPTIME = 0.2  # if no line exists, wait this many seconds before trying again
    QUEUE_MAXLEN = 0  # zero means infinite

    TESTING_FILENAME = 'Elveflow/temp.txt'

    def __init__(self, sourcename=None, errorlogger=None):
        """Start actually trying to read in data from an Elveflow log.

        If the sourcename is empty (even after selecting from a file dialog), this instance exists but does
        nothing when you try to start it.
        """
        if sourcename is None:
            self.sourcename = filedialog.askopenfilename(initialdir=".", title="Choose file", filetypes=(("tab-separated value", "*.tsv"), ("tab-separated value", "*.txt"), ("all files", "*.*")))
        else:
            self.sourcename = sourcename
        if self.sourcename == '':
            self.sourcename = None

        if errorlogger is None:
            # hack to just redirect logging to the standard print function
            # https://stackoverflow.com/questions/2827623/how-can-i-create-an-object-and-add-attributes-to-it
            self.errorlogger = lambda: None
            self.errorlogger.debug = print
            self.errorlogger.info = print
            self.errorlogger.warning = print
            self.errorlogger.error = print
            self.errorlogger.exception = print
            self.errorlogger.critical = print
        else:
            self.errorlogger = errorlogger

        self.header = None
        self.buffer_queue = Queue(maxsize=ElveflowHandlerESI.QUEUE_MAXLEN)
        self.run_flag = threading.Event()
        self.run_flag.set()

    def start(self, get_header_handler=None):
        """Start actually trying to read in data from an Elveflow log. Do not call this function more than once."""
        def start_thread():
            self.errorlogger.info("STARTING HANDLER THREAD %s" % threading.current_thread())

            def line_generator():
                with open(self.sourcename, 'a+', encoding="latin-1", newline='') as f:
                    # a+ creates the file if it doesn't exist, or just reads it if not
                    # we can then jump to the beginning and then continue as though the mode is r
                    f.seek(0)
                    # continuously read
                    while self.run_flag.is_set():
                        line = f.readline()
                        if not line.strip():
                            # wait a little before trying to find more lines
                            time.sleep(ElveflowHandlerESI.SLEEPTIME)
                        else:
                            # DANGER: next() can raise a StopIteration. If this does, this entire thread silently exits prematurely
                            # I think I've avoided this with if statements, but you can't be sure.
                            if self.header is None:
                                # the first line should be the header
                                self.header = next(csv.reader([line], delimiter='\t'))  # get the first (only) row from the iterator
                                self.errorlogger.info("SETTING HEADER %s" % threading.current_thread())
                                if get_header_handler is not None:
                                    get_header_handler()
                            else:
                                # otherwise, we already have a header, so just read in data
                                parsedline = next(csv.DictReader([line], fieldnames=self.header, delimiter='\t'))
                                for key in parsedline:
                                    try:
                                        parsedline[key] = float(parsedline[key])
                                    except ValueError:
                                        parsedline[key] = float('nan')
                                yield parsedline
            try:
                for line in line_generator():
                    self.buffer_queue.put(line, False)
                    # print("putting line %s" % line)
                    time.sleep(0.1)
            except Queue_Full:
                pass
            finally:
                self.errorlogger.info("ENDING HANDLER THREAD %s, %s" % (threading.current_thread(), threading.enumerate()))

        if self.sourcename is not None:
            self.reading_thread = threading.Thread(target=start_thread)
            self.reading_thread.start()

    def stop(self):
        """Stop the reading thread."""
        self.run_flag.clear()

    def fetch_one(self):
        """Retrieve the oldest element from the buffer.

        Afterwards, the element is no longer in the buffer. If nothing is in there, return None. (You cannot tell the difference between the leftmost element of
        the buffer holding None and the buffer being empty, but in this class, the former case should never happen).
        """
        try:
            return self.buffer_queue.get(False)
        except IndexError:
            return None

    def peek_one(self):
        """Look at the oldest element from the buffer, but does NOT remove it from the buffer.

        If nothing is in there, return None. (You cannot tell the difference between the leftmost element of
        the buffer holding None and the buffer being empty, but in this class, the former case should never happen).

        NOTE that depending on your use-case, you may wish to call this function while holding the mutex.
        """
        try:
            return self.buffer_queue.queue[0]
        except IndexError:
            return None

    def fetch_all(self):
        """Retrieve all elements from the buffer as a list. Afterwards, all elements returned are no longer in the buffer.

        In this class, the elements of the buffer are all dicts whose keys are the entries of the header.
        """
        def generate_elements():
            try:
                while True:
                    yield self.buffer_queue.get(False)
            except Queue_Empty:
                return
        return [elt for elt in generate_elements()]

    def get_header(self):
        """Return the header, a list of strings."""
        return self.header


class ElveflowHandlerSDK:
    """A class that handles interfacing with the Elveflow directly."""

    SLEEPTIME = 0.1  # how many seconds between each read of the Elveflow output
    QUEUE_MAXLEN = 0  # zero means infinite
    PID_SLEEPTIME = 0.05  # how many seconds between each command of the PID loop
    PRESSURELOOP_SLEEPTIME = 0.01  # how many seconds between each command of the pressure loop
    PRESSURE_MAXSLOPE = 1000 * PRESSURELOOP_SLEEPTIME  # in mbar per update frame; 1000 is in mbar/sec
    VOLUME_KP = 0
    VOLUME_KI = 50
    VOLUME_KD = 0

    def __init__(self, sourcename=None, errorlogger=None, sensortypes=[], starttime=0):
        """Start the Elveflow connection."""
        if sourcename is None or sourcename == '':
            self.sourcename = b'Have you loaded the config file?'
        else:
            self.sourcename = bytes(sourcename, encoding='ascii')

        if errorlogger is None:
            # hack to just redirect logging to the standard print function
            # https://stackoverflow.com/questions/2827623/how-can-i-create-an-object-and-add-attributes-to-it
            self.errorlogger = lambda: None
            self.errorlogger.debug = print
            self.errorlogger.info = print
            self.errorlogger.warning = print
            self.errorlogger.error = print
            self.errorlogger.exception = print
            self.errorlogger.critical = print
        else:
            self.errorlogger = errorlogger
        self.errorlogger.info("Initializing Elveflow at %s" % sourcename)
        self.starttime = starttime

        self.instr_ID = c_int32()
        self.calib = (c_double*1000)()  # always define array that way, calibration should have 1000 elements

        err_code = Elveflow_SDK.OB1_Initialization(self.sourcename, 3, 3, 3, 3, byref(self.instr_ID))
        # pressure sensors are hard-coded to be the 0-8000 mbar type (type 3)
        if err_code != 0:
            self.errorlogger.warning("Initialization error code %i" % err_code)

        self.sensortypes = sensortypes
        for i in range(len(sensortypes)):
            err_code = Elveflow_SDK.OB1_Add_Sens(self.instr_ID.value, i+1, SensorType=sensortypes[i], DigitalAnalog=0,
                                                 FSens_Digit_Calib=0, FSens_Digit_Resolution=3)   # TODO: what is the resolution? What does that mean?
            if err_code != 0:
                self.errorlogger.warning("sensor addition error code is %d" % self.instr_ID.value)

        # TODO: calibrations?
        err_code = Elveflow_SDK.Elveflow_Calibration_Default(byref(self.calib), 1000)
        if err_code != 0:
            self.errorlogger.warning("Calibration error code %i" % err_code)
        self.errorlogger.info("Done initializing Elveflow")

        self.header = ["time [s]", "Pressure 1 [mbar]", "Pressure 2 [mbar]", "Pressure 3 [mbar]", "Pressure 4 [mbar]",
                       "Volume flow rate 1 [µL/min]", "Volume flow rate 2 [µL/min]", "Volume flow rate 3 [µL/min]", "Volume flow rate 4 [µL/min]"]
        self.buffer_queue = Queue(maxsize=ElveflowHandlerSDK.QUEUE_MAXLEN)
        self.run_flag = threading.Event()
        self.run_flag.set()

    def start(self, get_header_handler=None):
        """Start the elveflow handler thread."""
        def start_thread():
            print("STARTING HANDLER THREAD %s" % threading.current_thread())
            while self.run_flag.is_set():
                data_sens = c_double()
                get_pressure = c_double()

                time.sleep(ElveflowHandlerSDK.SLEEPTIME)

                newline = {}
                for i in range(1, 5):
                    error = Elveflow_SDK.OB1_Get_Press(self.instr_ID.value, c_int32(i), 1, byref(self.calib), byref(get_pressure), 1000)
                    if error != 0:
                        self.errorlogger.warning('ERROR CODE PRESSURE %i: %s' % (i, error))
                    newline[self.header[i]] = get_pressure.value
                for i in range(1, 5):
                    error = Elveflow_SDK.OB1_Get_Sens_Data(self.instr_ID.value, c_int32(i), 1, byref(data_sens))
                    if error != 0:
                        self.errorlogger.warning('ERROR CODE FLOW SENSOR %i: %s' % (i, error))
                    newline[self.header[i+4]] = data_sens.value

                newline[self.header[0]] = time.time() - self.starttime

                try:
                    self.buffer_queue.put(newline, False)
                except Queue_Full:
                    pass

            try:
                def closing_function(i):
                    if i == 4:
                        def on_finish():
                            print("Closing Elveflow connection")
                            print("Error code: %s" % Elveflow_SDK.OB1_Destructor(self.instr_ID.value))
                    else:
                        def on_finish():
                            closing_function(i+1)

                    self.set_pressure_loop(i, 0, on_finish=on_finish)

                closing_function(1)
            except RuntimeError:
                print("Runtime error detected in IO handler thread %s while trying to close. Ignoring." % threading.current_thread())
            finally:
                print("DONE WITH HANDLER THREAD %s" % threading.current_thread())

        self.reading_thread = threading.Thread(target=start_thread)
        self.reading_thread.start()
        if get_header_handler is not None:
            get_header_handler()

    def stop(self):
        """Stop the reading thread."""
        self.run_flag.clear()

    def fetch_one(self):
        """Retrieve the oldest element from the buffer.

        Afterwards, the element is no longer in the buffer. If nothing is in there, return None. (You cannot tell the difference between the leftmost element of
        the buffer holding None and the buffer being empty, but in this class, the former case should never happen).
        """
        try:
            return self.buffer_queue.get(False)
        except IndexError:
            return None

    def peek_one(self):
        """Look at the oldest element from the buffer, but does NOT remove it from the buffer.

        If nothing is in there, return None. (You cannot tell the difference between the leftmost element of
        the buffer holding None and the buffer being empty, but in this class, the former case should never happen).

        NOTE that depending on your use-case, you may wish to call this function while holding the mutex.
        """
        try:
            return self.buffer_queue.queue[0]
        except IndexError:
            return None

    def fetch_all(self):
        """Retrieve all elements from the buffer as a list.

        Afterwards, all elements returned are no longer in the buffer. In this class, the elements of the buffer are all dicts whose keys are the entries of the header.
        """
        def generate_elements():
            try:
                while True:
                    yield self.buffer_queue.get(False)
            except Queue_Empty:
                return
        return [elt for elt in generate_elements()]

    def get_header(self):
        """Return the header, a list of strings."""
        return self.header

    def set_pressure(self, channel_number=4, value=300):
        """Tell the Elveflow to set the pressure directly."""
        error = Elveflow_SDK.OB1_Set_Press(self.instr_ID.value, channel_number, value, byref(self.calib), 1000)
        self.errorlogger.info('Set pressure of Channel %i to %s' % (channel_number, value))
        if error != 0:
            self.errorlogger.warning('ERROR CODE SET PRESSURE CHANNEL %i: %s' % (channel_number, error))

    def set_pressure_loop(self, channel_number, value, interrupt_event=None, on_finish=None):
        """Start a thread that raises the Elveflow pressure without a big spike.

        TODO: make it stop when it reaches the target.
        """
        if interrupt_event is None:
            # if there isn't one already, create a dummy one
            interrupt_event = threading.Event()
            interrupt_event.clear()
        def start_thread(channel_number, target, interrupt_event):
            if self.sensortypes[channel_number-1] == SDK_SENSOR_TYPES["none"]:
                self.errorlogger.warning("Channel %s is set to \"none\" (%s); ignoring command to set pressure to %s." % (channel_number, self.sensortypes[channel_number-1], target))
            else:
                self.errorlogger.info("CHANNEL %s: starting to set pressure to %s THREAD %s." % (channel_number, target, threading.current_thread()))
                if target > 8000:
                    target = 8000
                if target < 0:
                    target = 0

                get_pressure = c_double()
                error = Elveflow_SDK.OB1_Get_Press(self.instr_ID.value, c_int32(channel_number), 1, byref(self.calib), byref(get_pressure), 1000)
                if error != 0:
                    self.errorlogger.warning('ERROR CODE GETTING PRESSURE %i: %s' % (channel_number, error))
                    if on_finish is not None:
                        on_finish()
                    return

                curr_pressure = get_pressure.value

                while self.run_flag.is_set() and not interrupt_event.is_set():
                    # if we have an error reading, don't try to set anything
                    # self.errorlogger.debug('max slope is %s' % ElveflowHandlerSDK.PRESSURE_MAXSLOPE)
                    self.errorlogger.debug('requested slope is %s, and max slope is %s' % (abs(target - curr_pressure)))
                    if abs(target - curr_pressure) <= ElveflowHandlerSDK.PRESSURE_MAXSLOPE:
                        # if we're close, just set it and hope for the best
                        curr_pressure = target
                        interrupt_event.set()
                    else:
                        # otherwise, just make one PRESSURE_MAXSLOPE-sized step in the correct direction
                        curr_pressure = curr_pressure + math.copysign(ElveflowHandlerSDK.PRESSURE_MAXSLOPE, target - curr_pressure)

                    self.errorlogger.info("setting pressure to %s", curr_pressure)
                    error = Elveflow_SDK.OB1_Set_Press(self.instr_ID.value, channel_number, curr_pressure, byref(self.calib), 1000)
                    if error != 0:
                        self.errorlogger.warning('ERROR CODE SETTING PRESSURE %i: %s' % (channel_number, error))
                    # self.errorlogger.debug("setting pressure to %s", curr_pressure)

                    time.sleep(ElveflowHandlerSDK.PRESSURELOOP_SLEEPTIME)

                self.errorlogger.info("CHANNEL %s: finished setting pressure THREAD %s." % (channel_number, threading.current_thread()))

            try:
                if on_finish is not None:
                    on_finish()
            except RuntimeError:
                print("Runtime error detected in pressure loop channel %s thread %s while trying to close. Ignoring." % (channel_number, threading.current_thread()))

        self.reading_thread = threading.Thread(target=start_thread, args=(channel_number, value, interrupt_event))
        self.reading_thread.start()
        return self.reading_thread

    def set_volume_loop(self, channel_number, value, interrupt_event=None, pid_constants=None):
        """Start a thread that sets the Elveflow flow rate."""
        if interrupt_event is None:
            # if there isn't one already, create a dummy one
            interrupt_event = threading.Event()
            interrupt_event.clear()
        if pid_constants is None:
            pid_constants = (ElveflowHandlerSDK.VOLUME_KP, ElveflowHandlerSDK.VOLUME_KI, ElveflowHandlerSDK.VOLUME_KD)

        def start_thread(channel_number, target, interrupt_event, pid_constants):
            self.errorlogger.info("STARTING PRESSURE LOOP CHANNEL %s THREAD %s." % (channel_number, threading.current_thread()))
            pid = PID(*pid_constants, setpoint=target)
            initial_pressure = c_double()
            error = Elveflow_SDK.OB1_Get_Press(self.instr_ID.value, c_int32(channel_number), 1, byref(self.calib), byref(initial_pressure), 1000)
            if error != 0:
                self.errorlogger.warning('ERROR CODE GETTING PRESSURE %i: %s' % (channel_number, error))
            self.errorlogger.debug("INITIAL PRESSURE IS %f" % initial_pressure.value)

            while self.run_flag.is_set() and not interrupt_event.is_set():
                time.sleep(ElveflowHandlerSDK.PID_SLEEPTIME)
                get_flowrate = c_double()
                error = Elveflow_SDK.OB1_Get_Sens_Data(self.instr_ID.value, c_int32(channel_number), 1, byref(get_flowrate))
                if error != 0:
                    self.errorlogger.warning('ERROR CODE GETTING FLOW RATE %i: %s' % (channel_number, error))
                else:
                    # if we have an error reading, don't try to set anything
                    pressure_to_set = pid(get_flowrate.value) + initial_pressure.value

                    if pressure_to_set > 8000:
                        pressure_to_set = 8000
                    elif pressure_to_set < 0:
                        pressure_to_set = 0

                    error = Elveflow_SDK.OB1_Set_Press(self.instr_ID.value, channel_number, pressure_to_set, byref(self.calib), 1000)
                    if error != 0:
                        self.errorlogger.warning('ERROR CODE SETTING PRESSURE %i: %s' % (channel_number, error))
                    self.errorlogger.debug(pressure_to_set)
                    self.errorlogger.debug(pid.components)

            try:
                self.errorlogger.info("DONE WITH FLOW RATE LOOP CHANNEL %s THREAD %s; setting pressure to zero." % (channel_number, threading.current_thread()))
                a = self.set_pressure_loop(channel_number, 0)
                a.join()
                self.errorlogger.info("ENDING FLOW RATE LOOP CHANNEL %s THREAD %s." % (channel_number, threading.current_thread()))
            except RuntimeError:
                print("Runtime error detected in flow rate loop channel %s thread %s while trying to close. Ignoring." % (channel_number, threading.current_thread()))

        self.reading_thread = threading.Thread(target=start_thread, args=(channel_number, value, interrupt_event, pid_constants))
        self.reading_thread.start()


if USE_SDK:
    ElveflowHandler = ElveflowHandlerSDK
else:
    ElveflowHandler = ElveflowHandlerESI

if __name__ == '__main__':
    print("STARTING")
    myhandler = ElveflowHandler()
    try:
        myhandler.start()
        time.sleep(4)
        print("AFTER 4 SECONDS")
        print(list(map(lambda x: (x["Pressure 1 [mbar]"], x["Volume flow rate 1 [µL/min]"]), myhandler.fetch_all())))
        time.sleep(4)
        print("AFTER 8 SECONDS")
        print(list(map(lambda x: x["Volume flow rate 1 [µL/min]"], myhandler.fetch_all())))
        time.sleep(4)
        print("AFTER 12 SECONDS")
        print(list(map(lambda x: x["Volume flow rate 1 [µL/min]"], myhandler.fetch_all())))
    finally:
        myhandler.stop()
