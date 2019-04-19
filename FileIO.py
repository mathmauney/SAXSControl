import csv
import time
import threading
from collections import deque
from tkinter import filedialog

class ElveflowHandler:
    """a class that handles reading in Elveflow-generated log files"""
    SLEEPTIME = 0.5 #if no line exists, wait this many seconds before trying again
    DEQUE_MAXLEN = None #this can be a number if memory becomes an issue

    TESTING_FILENAME = 'Elveflow/temp.txt'

    def __init__(self, filename=None):
        """Start actually trying to read in data from an Elveflow log"""
        if filename is None:
            self.filename = filedialog.askopenfilename(initialdir=".", title="Choose file", filetypes=(("comma-separated value", "*.csv"), ("comma-separated value", "*.txt"), ("all files", "*.*")))
        else:
            self.filename = filename
        if filename == '':
            self.filename = None
        self.header = None
        self.buffer_deque = deque(maxlen=ElveflowHandler.DEQUE_MAXLEN)
        self.run_flag = threading.Event()
        self.run_flag.clear()

    def start(self, getheader_handler=None):
        """Start actually trying to read in data from an Elveflow log. Do not call this function more than once"""
        def start_thread():
            def line_generator():
                with open(self.filename, 'a+', encoding="latin-1", newline='') as f:
                    # a+ creates the file if it doesn't exist, or just reads it if not
                    # we can then jump to the beginning and then continue as though the mode is r
                    f.seek(0)
                    self.run_flag.set()

                    # continuously read
                    while self.run_flag.is_set():
                        line = f.readline()
                        if not line:
                            # wait a little before trying to find more lines
                            time.sleep(ElveflowHandler.SLEEPTIME)
                        else:
                            if self.header is None:
                                # the first line should be the header
                                self.header = next( csv.reader([line], delimiter='\t') )  #get the first (only) row from the iterator
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
            for line in line_generator():
                self.buffer_deque.append(line)

        self.reading_thread = threading.Thread(target=start_thread)
        self.reading_thread.start()

    def stop(self):
        """Stops the reading thread."""
        self.run_flag.clear()

    def fetchOne(self):
        """retrieve the oldest element from the buffer. Afterwards, the element is no longer in the buffer."""
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

if __name__ == '__main__':
    print("STARTING")
    myhandler = ElveflowHandler()
    myhandler.start()
    time.sleep(4)
    print("AFTER 4 SECONDS")
    print(len(myhandler.fetchAll()))
    time.sleep(4)
    print("AFTER 8 SECONDS")
    print(len(myhandler.fetchAll()))
    time.sleep(4)
    print("AFTER 12 SECONDS")
    print(len(myhandler.fetchAll()))
    myhandler.stop()
