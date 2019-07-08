"""
Class definition to control Rheodyne MXII
Initial set up using UART communication directly through USB
All functions in this version need testing. with actual pump.
"""

import serial #Needed for direct communication

class Rheodyne:

    def __init__(self,name="",valvetype=0,possition=0, PCConnect=True,addressI2C=-1):
        self.name=name                      #valve nickname
        self.valvetype=valvetype            #int to mark max number of valve possions 2 or 6
        self.possition=possition
        self.PCConnect=PCConnect
        #now lets create a serial object within the class to address the valve
        #I am presetting baudrate to that expdcted from rheodyne valves.
        #Actual baudrate can change- they just must agree.
        self.serialobject=serial.Serial(baudrate=19200,timeout=1)
        #set port throughuh another function.

        ## TODO: error handler to  avoid using withouth port being configured!!!

    def setport(self,number): #will keep set port accross different classes
        if self.serialobject.is_open:
            self.serialobject.close()
        self.serialobject.port="COM"+str(number)

    def settocontroller(self,controller):
        self.PCConnect=False
        self.controller=controller


    #"""Now the function to actually control de valve."""
    def switchvalve(self,possition): #Lets take int
    #this function wont work for possitions>10
    #to add that functionality the number must be
    #in hex format => P##  so 10 P0A
    #Need errror handler to check possition is integer and less than valve type
        if self.PCConnect:
            if not self.serialobject.is_open:
                self.serialobject.open()
            self.serialobject.write(("P0"+str(possition)+"\n\r").encode())
            ans=self.serialobject.read()
            #self.serialobject.close()           #Trying to be polite and leaving the ports closed
            if ans==b'\r': #pump returns this if command acknowledged
                self.possition=possition
                return 0    #Valve acknowledged commsnd
            else:
                return -1   #error valve didnt acknowledge
        elif self.addressI2C==-1:
            return -1
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("P%03i%i"%(self.addressI2C,possition)).encode())
            ans=self.controller.read()
            #self.controller.close()           #Trying to be polite and leaving the ports closed
            if ans==b'0': #pump returns this if command acknowledged
                self.possition=possition
                return 0    #Valve acknowledged commsnd
            else:
                return -1   #error valve didnt acknowledge


        #todo maybe incorporate status check to confirm valve is in the right possition
    def statuscheck(self):
        if self.PCConnect:
            if not self.serialobject.is_open:
                self.serialobject.open()
            self.serialobject.write("S\n\r".encode())
            ans=self.serialobject.read(2) #need to ensure thwt buffer doesnt build up-> if so switch to readln
            self.serialobject.close()
            return int(ans)   #returns valve possition
            # TODO: add error handlers
        elif self.addressI2C==-1:
            return -1
        else:
            if not self.controller.is_open:
                self.controller.open()
                self.controller.write(("S%03i"%self.addressI2C).encode())
                ans=self.controller.read() #need to ensure thwt buffer doesnt build up-> if so switch to readln
            #self.controller.close()
        return int(ans)   #returns valve possition
            # TODO: add error handlers






    def seti2caddress(self,address: int): #Address is in int format
    # Addres needs to be even int
        if address%2==0:
            if self.PCConnect:
                s=hex(address)
                self.serialobject.open()
                self.serialobject.write(("N"+s[2:4]+"\n\r").encode())
                self.serialobject.close()
                return 0
            elif self.addressI2C==-1:
                return -1
            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("N%03i%03i"%(self.addressI2C,address)).encode())
                while(self.controller.in_waiting()>0):
                    print(self.controller.readline())
                #self.controller.close()
                return 0
        else:
            return -1 # TODO: Error because value is not even

        return ans
