"""
Class definition to control Rheodyne MXII
Initial set up using UART communication directly through USB
All functions in this version need testing. with actual pump.
"""

import serial #Needed for direct communication

class Rheodyne:

    def __init__(self,name="",valvetype=0 ,possition=0):
        self.name=name                      #valve nickname
        self.valvetype=valvetype            #int to mark max number of valve possions 2 or 6
        self.possition=possition
        #now lets create a serial object within the class to address the valve
        #I am presetting baudrate to that expdcted from rheodyne valves.
        #Actual baudrate can change- they just must agree.
        self.serialobject=serial.Serial(baudrate=19200,timeout=1)
        #set port throughuh another function.

        ## TODO: error handler to  avoid using withouth port being configured!!!

    def setport(self,number):
        if self.serialobject.is_open:
            self.serialobject.close()
        self.serialobject.port="COM"+str(number)


    #"""Now the function to actually control de valve."""
    def switchvalve(self,possition): #Lets take intiger
    #this function wont work for possitions>10
    #to add that functionality the number must be
    #in hex format => P##  so 10 P0A
    #Need errror handler to check possition is integer and less than valve type
        if not self.serialobject.is_open:
            self.serialobject.open()
        self.serialobject.write("P0"+str(possition)+"\n\r")
        ans=self.serialobject.readln()
        self.serialobject.close()           #Trying to be polite and leaving the ports closed
        if str(possition) in ans.decode():
            self.possition=possition
            return 0    #Valve acknowledged commsnd
        else:
            return -1   #errror valve didnt acknowledge

        #todo maybe incorporate status check to confirm valve is in the right possition
    def statuscheck(self):
        if not self.serialobject.is_open:
            self.serialobject.open()
        self.serialobject.write("S\n\r")
        ans=self.serialobject.read(2) #need to ensure thwt buffer doesnt build up-> if so switch to readln
        self.serialobject.close()
        return ans.decode()   # TODO: ensure that decode returns an integer
        # TODO: aDD A FUNCTION TO CHECK THAT CONFIRM VSLUE.

    def seti2caddress(self,address: int): #imput address in string format
    # TODO: change it to an int imput and a hex conversion....
        s=hex(address)
        self.serialobject.open()
        self.serialobject.write("N"+s[2:4]+"\n\r")
        ans=self.serialobject.read(2) #need to ensure thwt buffer doesnt build up-> if so switch to readln
        self.serialobject.close()

        return ans
