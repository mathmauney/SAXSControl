import tkinter as tk
import logging

logger = logging.getLogger('python')


class COMPortSelector(tk.Listbox):
    def updatelist(self, com_list):
        self.delete(0, tk.END)
        for item in com_list:
            self.insert(tk.END, item.device+"  "+item.description)
