"""Simple code implenting pump class to control pumps.

Pollack Lab-Cornell
Josue San Emeterio
04/04/19
"""
from HPump import HPump
import tkinter as tk

# Create pump resource
firstpump = HPump()

top = tk.Tk()

s = tk.Spinbox(top, from_=1, to=10)
s.pack()

Bset = tk.Button(top, text="Set", command=lambda: firstpump.setport(s.get()))
Bset.pack()

Brun = tk.Button(top, text="RUN", command=firstpump.startpump)
Brun.pack()

Bstop = tk.Button(top, text="STOP", command=firstpump.stoppump)
Bstop.pack()

top.mainloop()
