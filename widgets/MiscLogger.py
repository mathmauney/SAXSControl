import tkinter as tk
import logging
from tkinter.scrolledtext import ScrolledText


logger = logging.getLogger('python')

class MiscLogger(ScrolledText):
    def append(self, msg):
        self.configure(state='normal')
        self.insert(tk.END, msg + '\n')
        self.configure(state='disabled')
        # Autoscroll to the bottom
        self.yview(tk.END)
