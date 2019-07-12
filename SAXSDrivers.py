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
    optional_list.clear()
    for item in list(serial.tools.list_ports.comports()):
        optional_list.append(item)
    return optional_list

def InstrumentTerminateFunction(InstrumentList):
    for Instrument in InstrumentList:
        if isinstance(Instrument,HPump):
            Instrument.stopall()

class SAXSController(serial.Serial):
    #function to initialize ports
    def __init__(self,logger=[],**kwargs):
        super().__init__(**kwargs)
        self.logger=logger

    def setport(self,port):
        if self.is_open:
            self.close()
        self.port=port
        self.open()
        self.logger.append("Controller set to port "+port)

    def ScanI2C(self):
        if not self.is_open:
            self.open()
        self.write(b'I')
        while self.in_waiting>0:
            self.logger.append(self.readline().decode())
class HPump:


    #need a single serisl for the clsss
    pumpserial=serial.Serial()

    #Set port protperties
    pumpserial.baudrate=9600
    pumpserial.stopbits=2
    pumpserial.timeout=0.1

    # Variable to keep track if pump has a valid port-> Avoids crashing when not set up
    ennabled=False

    #function to initialize ports
    def setport(self,port,resource=pumpserial):
        if resource.is_open:
            resource.close()
        resource.port=port
        self.PCConnect=True
        HPump.ennabled=True
        self.logger.append(self.name+" port set to "+port)
        #TODO: implent for things other than COM(num)


    #Pump intialization need pump number
    #need to set defsults fpr simpler impoementation
    def __init__(self, address=0,PCConnect=True, running=False, infusing=True, name="Pump", logger=[]):
        self.address=str(address)
        self.running=running
        self.infusing=infusing
        self.PCConnect=PCConnect
        self.logger=logger
        self.name=name
        #add init for syringe dismeter,flowrate, Direction etc

    # function  to send control over the controller
    def settocontroller(self,controller):
        self.PCConnect=False
        self.controller=controller
        HPump.ennabled=True
        self.logger.append(self.name+" set to Microntroller")

    def changevalues(self,address,name):
        if not self.name==name:
            self.logger.append("Changing Name: "+ self.name+" to "+name)
            self.name=name
        if not self.address==address:
            self.logger.append("Setting"+ self.name+"address :"+name)
            self.address=address



#Pump action commands
#To do in all. Read in confirmstion from pump.
    def startpump(self,resource=pumpserial):
        if not HPump.ennabled:
            return
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
        if not HPump.ennabled:
            return

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
        if not HPump.ennabled:
            return

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
        if not HPump.ennabled:
            return

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
        if not HPump.ennabled:
            return

        if(self.infusing):
            return setinfuserate(rate,units)
        else:
            return setrefillrate(rate,units)


    def sendcommand(self,command, resource=pumpserial): #sends an albitrary command
        if not HPump.ennabled:
            return
        resource.open()
        resource.write((command).encode())
        resource.close()

    def infuse(self, resource=pumpserial):
        if not HPump.ennabled:
            return
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
        if not HPump.ennabled:
            return
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
        if not HPump.ennabled:
            return
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
        if not HPump.ennabled:
            return
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'MOD PMP'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD PMP"+"\n\r").encode())


    def setmodevol(self,  resource=pumpserial):
        if not HPump.ennabled:
            return
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'MOD VOL'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD VOL"+"\n\r").encode())


    def setmodeprogam(self,  resource=pumpserial):
        if not HPump.ennabled:
            return
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'MOD PGM'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD PGM"+"\n\r").encode())


    def settargetvol(self,vol,  resource=pumpserial):
        if not HPump.ennabled:
            return
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
        if not HPump.ennabled:
            return
        if self.PCConnect:
            resource.open()
            resource.write(("\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("\n\r").encode())

    def close(self):
        if HPump.pumpserial.is_open:
            HPump.pumpserial.close()


class Rheodyne:
    def __init__(self,name="Rheodyne",valvetype=0, position=0, PCConnect=True, addressI2C=-1, ennabled=False, logger=[]):
        self.name=name                      #valve nickname
        self.valvetype=valvetype            #int to mark max number of valve possions 2 or 6
        self.position=position
        self.PCConnect=PCConnect
        self.ennabled=ennabled
        self.logger=logger
        self.addressI2C=addressI2C
        #now lets create a serial object within the class to address the valve
        #I am presetting baudrate to that expdcted from rheodyne valves.
        #Actual baudrate can change- they just must agree.
        self.serialobject=serial.Serial(baudrate=19200,timeout=0.1)
        #set port throughuh another function.

    def setport(self, port):  # will keep set port accross different classes
        if self.serialobject.is_open:
            self.serialobject.close()
        self.serialobject.port = port
        self.ennabled=True
        self.PCConnect=True
        self.logger.append(self.name+" port set to "+port)

    def settocontroller(self,controller):
        self.PCConnect=False
        self.controller=controller
        self.ennabled=True
        self.logger.append(self.name+" set to Microntroller")

    def changevalues(self,address,name):
        if not self.name==name:
            self.logger.append("Changing Name: "+ self.name+" to "+name)
            self.name=name
        if not self.addressI2C==address:
            self.logger.append("Setting"+ self.name+"address :"+name)
            self.addressI2C=address
    #"""Now the function to actually control de valve."""
    def switchvalve(self,position): #Lets take int
    #this function wont work for positions>10
    #to add that functionality the number must be
    #in hex format => P##  so 10 P0A
    #Need errror handler to check position is integer and less than valve type
        if not self.ennabled:
            return

        if self.PCConnect:
            if not self.serialobject.is_open:
                self.serialobject.open()
            self.serialobject.write(("P0"+str(position)+"\n\r").encode())
            ans=self.serialobject.read()
            #self.serialobject.close()           #Trying to be polite and leaving the ports closed
            if ans==b'\r': #pump returns this if command acknowledged
                self.position=position
                self.logger.append(self.name+" switched to "+str(position))
                return 0    #Valve acknowledged commsnd
            else:
                self.logger.append("Error Switching "+self.name)
                return -1   #error valve didnt acknowledge
        elif self.addressI2C==-1:
            self.logger.append(self.name+"I2C Address not set")
            return -1
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("P%03i%i"%(self.addressI2C,position)).encode())
            ans=self.controller.read()
            #self.controller.close()           #Trying to be polite and leaving the ports closed
            if ans==b'0': #pump returns this if command acknowledged
                self.position=position
                self.logger.append(self.name+" switched to "+str(position))
                return 0    #Valve acknowledged commsnd
            else:
                self.logger.append("Error Switching "+self.name)
                return -1   #error valve didnt acknowledge


        # todo maybe incorporate status check to confirm valve is in the right position
    def statuscheck(self):
        if not self.ennabled:
            return

        if self.PCConnect:
            if not self.serialobject.is_open:
                self.serialobject.open()
            self.serialobject.write("S\n\r".encode())
            ans=self.serialobject.read(2) #need to ensure thwt buffer doesnt build up-> if so switch to readln
            self.serialobject.close()
            return int(ans)   #returns valve position
            # TODO: add error handlers
        elif self.addressI2C==-1:
            return -1
        else:
            if not self.controller.is_open:
                self.controller.open()
                self.controller.write(("S%03i"%self.addressI2C).encode())
                ans=self.controller.read() #need to ensure thwt buffer doesnt build up-> if so switch to readln
            #self.controller.close()
        return int(ans)   #returns valve position
            # TODO: add error handlers

    def seti2caddress(self,address: int): #Address is in int format
    # Addres needs to be even int
        if not self.ennabled:
            return
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

    def close(self):
        if self.serialobject.is_open:
            self.serialobject.close()



class VICI:
    def __init__(self,name="VICI", address="", ennabled=False, PCConnect=True, position=0, logger=[]):
        self.name = name
        self.address = address
        self.ennabled = ennabled
        self.PCConnect = PCConnect
        self.position = position
        self.logger = logger

        self.ControllerKey=""
        self.serialobject=serial.Serial( timeout=0.1, baudrate=9600)

    def setport(self,port):
        if self.serialobject.is_open:
            self.serialobject.close()
        self.serialobject.port = port
        self.ennabled = True
        self.PCConnect = True
        self.ControllerKey = ""
        self.serialobject.open()
        self.logger.append(self.name+" set to port: "+ port)

    def settocontroller(self, controller):
        if self.serialobject.is_open:
            self.serialobject.close()
        self.PCConnect = False
        self.serialobject = Controller
        self.ennabled = True
        self.ControllerKey="+"
        self.serialobject.open()
        self.logger.append(self.name+" set to Microntroller")

    def switchvalve(self, position):
        if not self.ennabled:
            self.logger.append(self.name+" not set up, switching ignored")
            return

        if not self.serialobject.is_open():
            self.serialobject.open()
        commandtosend=self.ControllerKey+"GO{:02d}".format(position)
        self.serialobject.write(commandtosend.encode())
        self.logger.append(self.name+" switched to "+position)
        while self.serialobject.in_waiting()>0:
            self.logger.append(self.serialobject.readline())

    def currentposition(self):
        if not self.ennabled:
            self.logger.append(self.name+" not set up, switching ignored")
            return

        if not self.serialobject.is_open():
            self.serialobject.open()
        commandtosend=self.ControllerKey+"CP"
        self.serialobject.write(commandtosend.encode())
        self.logger.append(self.name+" Position Query ")
        while self.serialobject.in_waiting()>0:
            self.logger.append(self.serialobject.readline())

    def close(self):
        if self.serialobject.is_open:
            self.serialobject.close()
