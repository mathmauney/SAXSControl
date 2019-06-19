import csv
import time
import threading
from collections import deque
from tkinter import filedialog

USE_SDK = True

if USE_SDK:
    import ctypes
    import sys, os.path
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Elveflow_SDK"))#add the path of the LoadElveflow.py
    import Elveflow64


class ElveflowHandler_ESI:
    """a class that handles reading in Elveflow-generated log files"""
    SLEEPTIME = 0.5 #if no line exists, wait this many seconds before trying again
    DEQUE_MAXLEN = None #this can be a number if memory becomes an issue

    TESTING_FILENAME = 'Elveflow/temp.txt'

    def __init__(self, filename=None):
        """Start actually trying to read in data from an Elveflow log. If the filename is
        empty (even after selecting from a file dialog), this instance exists but does
        nothing when you try to start it"""
        if filename is None:
            self.filename = filedialog.askopenfilename(initialdir=".", title="Choose file", filetypes=(("tab-separated value", "*.tsv"), ("tab-separated value", "*.txt"), ("all files", "*.*")))
        else:
            self.filename = filename
        if self.filename == '':
            self.filename = None
        self.header = None
        self.buffer_deque = deque(maxlen=ElveflowHandler_ESI.DEQUE_MAXLEN)
        self.run_flag = threading.Event()
        self.run_flag.clear()

    def start(self, getheader_handler=None):
        """Start actually trying to read in data from an Elveflow log. Do not call this function more than once"""
        def start_thread():
            print("STARTING HANDLER THREAD %s" % threading.current_thread())
            def line_generator():
                with open(self.filename, 'a+', encoding="latin-1", newline='') as f:
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

        if self.filename is not None:
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
        """retrieve all elements from the buffer as a list. Afterwards, all elements returned are no longer in the buffer."""
        def generateElements():
            try:
                while True:
                    yield self.buffer_deque.popleft()
            except IndexError:
                return
        return [elt for elt in generateElements()]

    def getHeader(self):
        return self.header

class ElveflowHandler_SDK:
    """a class that handles interfacing with the Elveflow directly"""
    SLEEPTIME = 0.5 #how many seconds between each read of the Elveflow output
    DEQUE_MAXLEN = None #this can be a number if memory becomes an issue

    def __init__(self):
        self.instr_name = None
        #TODO: selectable
        self.instr_name = b'01C9D9C3'
        self.instr_ID = ctypes.c_int32()
        print(self.instr_ID.value)

        print("Initializing Elveflow")
        err_code = Elveflow64.OB1_Initialization(self.instr_name, 0, 0, 0, 0, ctypes.byref(self.instr_ID))
        print(err_code)
        self.header = None
        self.buffer_deque = deque(maxlen=ElveflowHandler_SDK.DEQUE_MAXLEN)
        self.run_flag = threading.Event()
        self.run_flag.clear()
        print("Done initializing Elveflow")
        # TODO: calibrations?

    def start(self):
        def start_thread():
            self.run_flag.set()
            while self.run_flag.is_set():
                pass
                data_sens=c_double()
                get_pressure=c_double()

                time.sleep(ElveflowHandler_SDK.SLEEPTIME)
                #
                # for i in range(1,5):
                #     error=OB1_Get_Press(self.Instr_ID.value, i, 0, byref(Calib), byref(get_pressure), 1000) #Ch = i;  Acquire_data =0 -> Use the value acquired in OB1_Get_Press
                #     print('error: ', error)
                #     print('Press ch ', i,': ',get_pressure.value)
                #
                # for i in range(1,5):
                #     error=OB1_Get_Sens_Data(self.Instr_ID.value, i, 0, byref(data_sens)) #Ch = i;  Acquire_data =0 -> Use the value acquired in OB1_Get_Press
                #     print('error: ', error)
                #     print('Sens ch ', i,': ',data_sens.value)


        if self.instr_name is not None:
            self.reading_thread = threading.Thread(target=start_thread)
            self.reading_thread.start()

    def stop(self):
        """Stops the reading thread."""
        self.run_flag.clear()

if USE_SDK:
    ElveflowHandler = ElveflowHandler_SDK
else:
    ElveflowHandler = ElveflowHandler_ESI

if __name__ == '__main__':
    myhandler = ElveflowHandler()
    # print("STARTING")
    # myhandler = ElveflowHandler()
    # myhandler.start()
    # time.sleep(4)
    # print("AFTER 4 SECONDS")
    # print(len(myhandler.fetchAll()))
    # time.sleep(4)
    # print("AFTER 8 SECONDS")
    # print(len(myhandler.fetchAll()))
    # time.sleep(4)
    # print("AFTER 12 SECONDS")
    # print(len(myhandler.fetchAll()))
    # myhandler.stop()
