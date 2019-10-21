import tkinter as tk
import math
import tkinter.font
import logging
import csv
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk, VERTICAL, HORIZONTAL, N, S, E, W
import numpy as np
import FileIO
import threading
import time
import os.path
from queue import Queue, Empty as Queue_Empty
import warnings
import matplotlib
from matplotlib import pyplot as plt

matplotlib.use('TkAgg')
warnings.filterwarnings("ignore", message="Attempting to set identical bottom==top")
warnings.filterwarnings("ignore", message="Attempting to set identical left==right")

logger = logging.getLogger('python')

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
