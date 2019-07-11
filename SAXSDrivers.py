"""
Class definition to control a Hardvard pump through UART serial communication
The class shares a COM port. This ennables to configure several pumps though a
PUMP chai- Therefore it doesn't support multiple pumps connected directly to
Computer

Version 1-04/04/19
Pollack Lab- Ccornell University
Josue San Emeterio
"""
import serial
import serial.tools.list_ports


def ListAvailablePorts(optional_list=[]):
    optional_list=list(serial.tools.list_ports.comports())
    return optional_list
class SAXSController(serial.Serial):
    #function to initialize ports
    def setport(self,number):
        if self.is_open:
            self.close()
        self.port="COM"+str(number)
    #Init


class HPump:


    #need a single serisl for the clsss
    pumpserial=serial.Serial()

    #Set port protperties
    pumpserial.baudrate=9600
    pumpserial.stopbits=2
    pumpserial.timeout=1



    #function to initialize ports
    def setport(self,port,resource=pumpserial):
        if resource.is_open:
            resource.close()
        resource.port=port
        #TODO: implent for things other than COM(num)


    #Pump intialization need pump number
    #need to set defsults fpr simpler impoementation
    def __init__(self, address=0,PCConnect=True, running=False, infusing=True, name="Pump"):
        self.address=str(address)
        self.running=running
        self.infusing=infusing
        self.PCConnect=PCConnect
        self.name=name
        #add init for syringe dismeter,flowrate, Direction etc

    # function  to send control over the controller
    def settocontroller(self,controller):
        self.PCConnect=False
        self.controller=controller

    def changevalues(self,address,name):
        self.address=address
        self.name=name

#Pump action commands
#To do in all. Read in confirmstion from pump.
    def startpump(self,resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+"RUN\n\r").encode()) #neets both terminators
            #val=resource.read_until("\n\r")
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"RUN\n\r").encode())

        self.running=True #Consider switching to after checking with pump
        #return val.decode()

    def    stoppump(self,resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+"STP\n\r").encode())
            #val=resource.read_until("\n\r")
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"STP\n\r").encode())

        self.running=False #consider moving to after checking with pump
        #return val.decode()

    def setinfuserate(self,rate,units="UM",resource=pumpserial):
        #consider moving to after checking with pump
        ratestr=str(rate).zfill(5)
        if self.PCConnect:
            resource.open()
            resource.write((self.address+"RAT"+ratestr+units+"\n\r").encode())
            val=resource.read(4)
            #TODO: add possibillity to change units
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"RAT"+ratestr+units+"\n\r").encode())

        self.infuserate=rate #consider moving to after checking with pump
        #return val.decode()


    def setrefillrate(self,rate,units="UM",resource=pumpserial):
        #consider moving to after checking with pump
        ratestr=str(rate).zfill(5)
        if self.PCConnect:
            resource.open()
            resource.write((self.address+"RFR"+ratestr+units+"\n\r").encode())
            resource.close()
            #val=resource.read(4)
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"RFR"+ratestr+units+"\n\r").encode())

        #TODO: add possibillity to change units
        self.fillrate=rate #consider moving to after checking with pump

        return val.decode()


    def setflowrate(self,rate,units="UM",resource=pumpserial):
        #Function to change the current flowrate whether infuse or withdraw
        if(self.infusing):
            return setinfuserate(rate,units)
        else:
            return setrefillrate(rate,units)


    def sendcommand(self,command, resource=pumpserial): #sends an albitrary command
        resource.open()
        resource.write((command).encode())
        resource.close()

    def infuse(self, resource=pumpserial):
        self.infusing=True
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'DIRINF'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"DIRINF"+"\n\r").encode())

    def refill(self,  resource=pumpserial):
        self.infusing=False
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'DIRREF'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"DIRREF"+"\n\r").encode())


    def reverse(self,  resource=pumpserial):
        self.infusing=(not self.infusing)
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'DIRREV'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"DIRREV"+"\n\r").encode())


    def setmodepump(self,  resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'MOD PMP'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD PMP"+"\n\r").encode())


    def setmodevol(self,  resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'MOD VOL'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD VOL"+"\n\r").encode())


    def setmodeprogam(self,  resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'MOD PGM'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD PGM"+"\n\r").encode())


    def settargetvol(self,vol,  resource=pumpserial):
        volstr=str(vol).zfill(5)
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'TGT'+volstr+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+'TGT'+volstr+"\n\r").encode())

    def stopall(self, resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write(("\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("\n\r").encode())



class Rheodyne():
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

    def __init__(self, name="", valvetype=0, position=0):
        self.name = name                      # valve nickname
        self.valvetype = valvetype            # int to mark max number of valve possions 2 or 6
        self.position = position
        # now lets create a serial object within the class to address the valve
        # I am presetting baudrate to that expdcted from rheodyne valves.
        # Actual baudrate can change- they just must agree.
        self.serialobject = serial.Serial(baudrate=19200, timeout=1)
        # set port through another function.
        # TODO: error handler to  avoid using withouth port being configured!!!

    def setport(self, number):  # will keep set port accross different classes
        if self.serialobject.is_open:
            self.serialobject.close()
        self.serialobject.port = "COM" + str(number)

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


        # todo maybe incorporate status check to confirm valve is in the right position
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
            return -1  # TODO: Error because value is not even
        return  # ans
