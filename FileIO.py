import csv
import time
import threading
from collections import deque

class ElveflowHandler:
    """a class that handles reading in Elveflow-generated log files"""
    SLEEPTIME = 0.5 #if no line exists, wait this many seconds before trying again
    DEQUE_MAXLEN = None #this can be a number if memory becomes an issue

    def __init__(self, filename='Elveflow/temp.txt'):
        """Start actually trying to read in data from an Elveflow log"""
        if filename is None:
            self.filename = filedialog.asksaveasfilename(initialdir=".", title="Locate log file", filetypes=(("comma-separated value", "*.csv"), ("all files", "*.*")))
        else:
            self.filename = filename
        if filename == '':
            self.filename = None
        self.header = None
        self.buffer_deque = deque(maxlen=ElveflowHandler.DEQUE_MAXLEN)
        self.stop_flag = False

    def start(self):
        """Start actually trying to read in data from an Elveflow log. Do not call this function more than once"""
        def start_thread():
            def do_read():
                with open(self.filename, 'r', encoding="latin-1", newline='') as f:
                    # get the header manually to handle this continuous file
                    line = None
                    while not line:
                        line = f.readline()
                    self.header = next( csv.reader([line], delimiter='\t') )  #get the first (only) row from the iterator

                    # continuously read
                    while True:
                        line = f.readline()
                        while not line:
                            # keep waiting until we find more lines
                            time.sleep(ElveflowHandler.SLEEPTIME)
                            line = f.readline()
                        parsedline = next( csv.DictReader([line], fieldnames=self.header, delimiter='\t') )
                        for key in parsedline:
                            try:
                                parsedline[key] = float(parsedline[key])
                            except ValueError:
                                pass
                        yield parsedline
                        if self.stop_flag:
                            return
            for line in do_read():
                self.buffer_deque.append(line)

        self.reading_thread = threading.Thread(target=start_thread)
        self.reading_thread.start()

    def stop(self):
        """Stops the reading thread."""
        self.stop_flag = True

    def fetchOne(self):
        """retrieve the oldest element from the buffer. Afterwards, the element is no longer in the buffer."""
        try:
            return self.buffer_deque.popleft()
        except IndexError:
            return None

    def fetchAll(self):
        """retrieve all element from the buffer. Afterwards, all elements returned are no longer in the buffer."""
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
