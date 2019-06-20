# encoding: utf8
import csv
import time
import threading
from collections import deque
from tkinter import filedialog

USE_SDK = True

if USE_SDK:
    from ctypes import c_int32, c_double, byref
    import sys, os.path
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Elveflow_SDK"))#add the path of the LoadElveflow.py
    import Elveflow64


class ElveflowHandler_ESI:
    """a class that handles reading in Elveflow-generated log files"""
    SLEEPTIME = 0.5 #if no line exists, wait this many seconds before trying again
    DEQUE_MAXLEN = None #this can be a number if memory becomes an issue

    TESTING_FILENAME = 'Elveflow/temp.txt'

    def __init__(self, sourcename=None):
        """Start actually trying to read in data from an Elveflow log. If the sourcename is
        empty (even after selecting from a file dialog), this instance exists but does
        nothing when you try to start it"""
        if sourcename is None:
            self.sourcename = filedialog.askopenfilename(initialdir=".", title="Choose file", filetypes=(("tab-separated value", "*.tsv"), ("tab-separated value", "*.txt"), ("all files", "*.*")))
        else:
            self.sourcename = sourcename
        if self.sourcename == '':
            self.sourcename = None
        self.header = None
        self.buffer_deque = deque(maxlen=ElveflowHandler_ESI.DEQUE_MAXLEN)
        self.run_flag = threading.Event()
        self.run_flag.clear()

    def start(self, getheader_handler=None):
        """Start actually trying to read in data from an Elveflow log. Do not call this function more than once"""
        def start_thread():
            print("STARTING HANDLER THREAD %s" % threading.current_thread())
            def line_generator():
                with open(self.sourcename, 'a+', encoding="latin-1", newline='') as f:
                    # a+ creates the file if it doesn't exist, or just reads it if not
                    # we can then jump to the beginning and then continue as though the mode is r
                    f.seek(0)
                    self.run_flag.set()
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
                                print("SETTING HEADER %s" % threading.current_thread())
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
                    self.buffer_deque.append(line)
            finally:
                print("ENDING HANDLER THREAD %s" % threading.current_thread())

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
            return self.buffer_deque.popleft()
        except IndexError:
            return None

    def fetchAll(self):
        """retrieve all elements from the buffer as a list. Afterwards, all elements returned are no longer in the buffer.
        In this class, the elements of the buffer are all dicts whose keys are the entries of the header"""
        def generateElements():
            try:
                while True:
                    yield self.buffer_deque.popleft()
            except IndexError:
                return
        return [elt for elt in generateElements()]

    def getHeader(self):
        """returns the header, a list of strings"""
        return self.header

class ElveflowHandler_SDK:
    """a class that handles interfacing with the Elveflow directly"""
    SLEEPTIME = 0.5 #how many seconds between each read of the Elveflow output
    DEQUE_MAXLEN = None #this can be a number if memory becomes an issue

    def __init__(self, sourcename=None):
        print("Initializing Elveflow")
        if sourcename is None:
            self.sourcename = b'01C9D9C3'
        else:
            self.sourcename = bytes(sourcename)
        self.instr_ID = c_int32()
        self.calib =(c_double*1000)() # always define array that way, calibration should have 1000 elements
        print(self.instr_ID.value)

        err_code = Elveflow64.OB1_Initialization(self.sourcename, 0, 0, 0, 0, byref(self.instr_ID))
        print("Initialization error code", err_code)

        # TODO: calibrations?
        err_code = Elveflow64.Elveflow_Calibration_Default(byref(self.calib), 1000)
        print("Calibration error code", err_code)
        print(list(self.calib))
        print("Done initializing Elveflow")

        self.header = ["time [s]", "Pressure 1 [mbar]","Pressure 2 [mbar]","Pressure 3 [mbar]","Pressure 4 [mbar]","Volume flow rate 1 [µL/min]","Volume flow rate 2 [µL/min]","Volume flow rate 3 [µL/min]","Volume flow rate 4 [µL/min]"]
        self.buffer_deque = deque(maxlen=ElveflowHandler_SDK.DEQUE_MAXLEN)
        self.run_flag = threading.Event()
        self.run_flag.clear()

    def start(self, getheader_handler=None):
        def start_thread():
            self.run_flag.set()
            while self.run_flag.is_set():
                data_sens = c_double()
                get_pressure = c_double()

                time.sleep(ElveflowHandler_SDK.SLEEPTIME)

                newline = {}
                for i in range(1, 5):
                    error = Elveflow64.OB1_Get_Press(self.instr_ID.value, i, 1, byref(self.calib), byref(get_pressure), 1000)
                    if error != 0:
                        print('ERROR CODE PRESSURE %i: %s' % (i, error))
                    newline[self.header[i]] = get_pressure.value

                for i in range(1, 5):
                    error = Elveflow64.OB1_Get_Sens_Data(self.instr_ID.value, i, 1, byref(data_sens))
                    if error != 0:
                        print('ERROR CODE PRESSURE %i: %s' % (i, error))
                    newline[self.header[i+4]] = get_pressure.value

                newline[self.header[0]] = time.time()

                self.buffer_deque.append(newline)


            error = Elveflow64.OB1_Destructor(self.instr_ID.value)
            print("Closing connection with Elveflow%s." % ("" if error==0 else (" (Error code %i)" % error)))

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
            return self.buffer_deque.popleft()
        except IndexError:
            return None

    def fetchAll(self):
        """retrieve all elements from the buffer as a list. Afterwards, all elements returned are no longer in the buffer.
        In this class, the elements of the buffer are all dicts whose keys are the entries of the header"""
        def generateElements():
            try:
                while True:
                    yield self.buffer_deque.popleft()
            except IndexError:
                return
        return [elt for elt in generateElements()]

    def getHeader(self):
        """returns the header, a list of strings"""
        return self.header

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
        print(myhandler.fetchAll())
        time.sleep(4)
        print("AFTER 8 SECONDS")
        print(myhandler.fetchAll())
        time.sleep(4)
        print("AFTER 12 SECONDS")
        print(myhandler.fetchAll())
    finally:
        myhandler.stop()
