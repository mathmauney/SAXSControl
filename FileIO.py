# encoding: utf8
import csv
import time
import threading
from queue import Queue, Empty as Queue_Empty, Full as Queue_Full
from tkinter import filedialog

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
    import sys, os.path
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Elveflow_SDK"))#add the path of the LoadElveflow.py
    import Elveflow64 as Elveflow_SDK

class ElveflowHandler_ESI:
    """a class that handles reading in Elveflow-generated log files"""
    SLEEPTIME = 0.2 #if no line exists, wait this many seconds before trying again
    QUEUE_MAXLEN = 0 #zero means infinite

    TESTING_FILENAME = 'Elveflow/temp.txt'

    def __init__(self, sourcename=None, errorlogger=None):
        """Start actually trying to read in data from an Elveflow log. If the sourcename is
        empty (even after selecting from a file dialog), this instance exists but does
        nothing when you try to start it"""
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
        self.buffer_queue = Queue(maxsize=ElveflowHandler_ESI.QUEUE_MAXLEN)
        self.run_flag = threading.Event()
        self.run_flag.set()

    def start(self, getheader_handler=None):
        """Start actually trying to read in data from an Elveflow log. Do not call this function more than once"""
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
                            time.sleep(ElveflowHandler_ESI.SLEEPTIME)
                        else:
                            # DANGER: next() can raise a StopIteration. If this does, this entire thread silently exits prematurely
                            # I think I've avoided this with if statements, but you can't be sure.
                            if self.header is None:
                                # the first line should be the header
                                self.header = next( csv.reader([line], delimiter='\t') )  #get the first (only) row from the iterator
                                self.errorlogger.info("SETTING HEADER %s" % threading.current_thread())
                                if getheader_handler is not None:
                                    getheader_handler()
                            else:
                                # otherwise, we already have a header, so just read in data
                                parsedline = next( csv.DictReader([line], fieldnames=self.header, delimiter='\t') )
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
            except Queue_Full as e:
                pass
            finally:
                self.errorlogger.info("ENDING HANDLER THREAD %s" % threading.current_thread())

        if self.sourcename is not None:
            self.reading_thread = threading.Thread(target=start_thread)
            self.reading_thread.start()

    def stop(self):
        """Stops the reading thread."""
        self.run_flag.clear()

    def fetchOne(self):
        """retrieve the oldest element from the buffer. Afterwards, the element is no longer in the buffer.
        If nothing is in there, return None. (You cannot tell the difference between the leftmost element of
        the buffer holding None and the buffer being empty, but in this class, the former case should never happen)"""
        try:
            return self.buffer_queue.get(False)
        except IndexError:
            return None

    def fetchAll(self):
        """retrieve all elements from the buffer as a list. Afterwards, all elements returned are no longer in the buffer.
        In this class, the elements of the buffer are all dicts whose keys are the entries of the header"""
        def generateElements():
            try:
                while True:
                    yield self.buffer_queue.get(False)
            except Queue_Empty:
                return
        return [elt for elt in generateElements()]

    def getHeader(self):
        """returns the header, a list of strings"""
        return self.header

class ElveflowHandler_SDK:
    """a class that handles interfacing with the Elveflow directly"""
    SLEEPTIME = 0.2 #how many seconds between each read of the Elveflow output
    QUEUE_MAXLEN = 0 #zero means infinite

    def __init__(self, sourcename=None, errorlogger=None, sensortypes=[], starttime=0):
        if sourcename is None or sourcename == '':
            self.sourcename = b'01A377A5'
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
        self.errorlogger.info("Initializing Elveflow")
        self.starttime = starttime

        self.instr_ID = c_int32()
        self.calib =(c_double*1000)() # always define array that way, calibration should have 1000 elements

        err_code = Elveflow_SDK.OB1_Initialization(self.sourcename, 3, 3, 3, 3, byref(self.instr_ID))
        # pressure sensors are hard-coded to be the 0-8000 mbar type (type 3)
        if err_code != 0:
            self.errorlogger.warning("Initialization error code %i" % err_code)

        for i in range(len(sensortypes)):
            err_code = Elveflow_SDK.OB1_Add_Sens(self.instr_ID.value, i+1, SensorType=sensortypes[i], DigitalAnalog=0, FSens_Digit_Calib=0, FSens_Digit_Resolution=3) # TODO: what is the resolution? What does that mean?
            if err_code != 0:
                self.errorlogger.warning("sensor addition error code is %d" % self.instr_ID.value)

        # TODO: calibrations?
        err_code = Elveflow_SDK.Elveflow_Calibration_Default(byref(self.calib), 1000)
        if err_code != 0:
            self.errorlogger.warning("Calibration error code %i" % err_code)
        self.errorlogger.info("Done initializing Elveflow")

        self.header = ["time [s]", "Pressure 1 [mbar]","Pressure 2 [mbar]","Pressure 3 [mbar]","Pressure 4 [mbar]","Volume flow rate 1 [µL/min]","Volume flow rate 2 [µL/min]","Volume flow rate 3 [µL/min]","Volume flow rate 4 [µL/min]"]
        self.buffer_queue = Queue(maxsize=ElveflowHandler_SDK.QUEUE_MAXLEN)
        self.run_flag = threading.Event()
        self.run_flag.set()

    def start(self, getheader_handler=None):
        def start_thread():
            print("STARTING HANDLER THREAD %s" % threading.current_thread())
            while self.run_flag.is_set():
                data_sens = c_double()
                get_pressure = c_double()

                time.sleep(ElveflowHandler_SDK.SLEEPTIME)

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
                except Queue_Full as e:
                    pass

            try:
                error = Elveflow_SDK.OB1_Destructor(self.instr_ID.value)
                print("Closing connection with Elveflow%s." % ("" if error==0 else (" (Error code %i)" % error)))
            except RuntimeError as e:
                print("Runtime error detected in IO handler thread %s while trying to close. Ignoring." % threading.current_thread())
            finally:
                print("As Handler %s is closing, these are the remaining threads: %s" % (threading.current_thread(), threading.enumerate()))
                print()

        self.reading_thread = threading.Thread(target=start_thread)
        self.reading_thread.start()
        if getheader_handler is not None:
            getheader_handler()

    def stop(self):
        """Stops the reading thread."""
        self.run_flag.clear()

    def fetchOne(self):
        """retrieve the oldest element from the buffer. Afterwards, the element is no longer in the buffer.
        If nothing is in there, return None. (You cannot tell the difference between the leftmost element of
        the buffer holding None and the buffer being empty, but in this class, the former case should never happen)"""
        try:
            return self.buffer_queue.get(False)
        except IndexError:
            return None

    def fetchAll(self):
        """retrieve all elements from the buffer as a list. Afterwards, all elements returned are no longer in the buffer.
        In this class, the elements of the buffer are all dicts whose keys are the entries of the header"""
        def generateElements():
            try:
                while True:
                    yield self.buffer_queue.get(False)
            except Queue_Empty:
                return
        return [elt for elt in generateElements()]

    def getHeader(self):
        """returns the header, a list of strings"""
        return self.header

    def setPressure(self, channel_number, value):
        """tells the Elveflow to set the pressure"""
        error = Elveflow_SDK.OB1_Set_Press(self.instr_ID.value, channel_number, value, byref(self.calib), 1000)
        self.errorlogger.info('Set pressure of Channel %i to %s' % (channel_number, value))
        if error != 0:
            self.errorlogger.warning('ERROR CODE SET PRESSURE CHANNEL %i: %s' % (channel_number, error))

if USE_SDK:
    ElveflowHandler = ElveflowHandler_SDK
else:
    ElveflowHandler = ElveflowHandler_ESI

if __name__ == '__main__':
    print("STARTING")
    myhandler = ElveflowHandler()
    try:
        myhandler.start()
        time.sleep(4)
        print("AFTER 4 SECONDS")
        print(list(map(lambda x: (x["Pressure 1 [mbar]"], x["Volume flow rate 1 [µL/min]"]), myhandler.fetchAll())))
        time.sleep(4)
        print("AFTER 8 SECONDS")
        print(list(map(lambda x: x["Volume flow rate 1 [µL/min]"], myhandler.fetchAll())))
        time.sleep(4)
        print("AFTER 12 SECONDS")
        print(list(map(lambda x: x["Volume flow rate 1 [µL/min]"], myhandler.fetchAll())))
    finally:
        myhandler.stop()