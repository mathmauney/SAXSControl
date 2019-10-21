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


class COMPortSelector(tk.Listbox):
    def updatelist(self, com_list):
        self.delete(0, tk.END)
        for item in com_list:
            self.insert(tk.END, item.device+"  "+item.description)
