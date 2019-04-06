"""
Simple code implenting pump class to control pumps. 
Pollack Lab-Cornell
Josue San Emeterio
04/04/19
"""
from HPump import *
from tkinter import *

#create pump resource
firstpump=HPump()



top=Tk()


s=Spinbox(top,from_=1, to=10)
s.pack()

Bset=Button(top,text="Set",command=firstpump.setport(s.get()))
Bset.pack()

Brun=Button(top,text="RUN",command=firstpump.startpump())
Brun.pack()

Bstop=Button(top,text="STOP",command=firstpump.stoppump())
Bstop.pack()

top.mainloop()

