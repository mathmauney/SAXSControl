"""Class definition to control a Hardvard pump through UART serial communication.

The class shares a COM port. This ennables to configure several pumps though a
PUMP chai- Therefore it doesn't support multiple pumps connected directly to
Computer

Version 1-04/04/19
Pollack Lab- Ccornell University
Josue San Emeterio
"""
import serial
import serial.tools.list_ports


def list_available_ports(optional_list=[]):   # Does the optional list input do anything? Should we just initialize an empty list for the output?
    """Find and return all available COM ports. If passed a list will update that list with the current set of COM ports."""
    optional_list.clear()
    for item in list(serial.tools.list_ports.comports()):
        optional_list.append(item)
    return optional_list


def stop_instruments(instrument_list):
    """Stop all instruments in a list if they can be stopped."""
    for instrument in instrument_list:
        if hasattr(instrument,"stop"):
            instrument.stop()


class SAXSController(serial.Serial):
    """Class for communication with devices using the USB box."""

    def __init__(self, logger=[], **kwargs):
        """Initialize class."""
        super().__init__(**kwargs)
        self.logger = logger

    def set_port(self, port):
        """Set the serial port."""
        if self.is_open:
            self.close()
        self.port = port
        self.open()
        self.logger.append("Controller set to port "+port)

    def scan_i2c(self):
        """Scan I2C line."""
        if not self.is_open:
            self.open()
        self.write(b'I')
        while self.in_waiting > 0:
            self.logger.append(self.readline().decode())


class HPump:
    """Class for controlling Harvard Pumps."""

    # need a single serisl for the class
    pumpserial = serial.Serial()

    # Set port protperties
    pumpserial.baudrate = 9600
    pumpserial.stopbits = 2
    pumpserial.timeout = 0.1

    # Variable to keep track if pump has a valid port-> Avoids crashing when not set up
    enabled = False

    def __init__(self, address=0, pc_connect=True, running=False, infusing=True, name="Pump", logger=[]):
        """Initialize HPump."""
        self.address = str(address)
        self.running = running
        self.infusing = infusing
        self.pc_connect = pc_connect
        self.logger = logger
        self.name = name
        # add init for syringe dismeter,flowrate, Direction etc

    # function to initialize ports
    def set_port(self, port, resource=pumpserial):
        """Set the pump port."""
        if resource.is_open:
            resource.close()
        resource.port = port
        self.pc_connect = True
        HPump.enabled = True
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
            self.logger.append("Setting "+ self.name+" address :"+str(address))
            self.address=str(address)


    # Pump intialization need pump number
    # need to set defsults fpr simpler impoementation

    def set_to_controller(self, controller):
        """Set the control to a controller rather than direct."""
        self.pc_connect = False
        self.controller = controller
        HPump.enabled = True
        self.logger.append(self.name+" set to Microntroller")

    def change_values(self, address, name):
        """Change the name or address of the instrument."""
        if self.name != name:
            self.logger.append("Changing Name: "+self.name+" to "+name)
            self.name = name
        if not self.address != address:
            self.logger.append("Setting"+self.name+"address :"+name)
            self.address = address

# Pump action commands
# To do in all. Read in confirmstion from pump.

    def start_pump(self, resource=pumpserial):
        """Send a start command to the pump."""
        if not HPump.enabled:
            return
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+"RUN\n\r").encode())   # needs both terminators
            # val=resource.read_until("\n\r")

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"RUN\n\r").encode())

        self.running = True     # Consider switching to after checking with pump
        self.logger.append("Started " + self.name)
        # return val.decode()


    def stoppump(self,resource=pumpserial):
        if not HPump.ennabled:

            return
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+"STP\n\r").encode())
            # val=resource.read_until("\n\r")

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"STP\n\r").encode())

        self.running = False    # consider moving to after checking with pump
        # return val.decode()

    def set_infuse_rate(self, rate, units="UM", resource=pumpserial):
        # consider moving to after checking with pump
        if not HPump.enabled:
            return
        ratestr = str(rate).zfill(5)
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+"RAT"+ratestr+units+"\n\r").encode())
            # val = resource.read(4)
            # TODO: add possibillity to change units

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"RAT"+ratestr+units+"\n\r").encode())

        self.infuserate = rate    # consider moving to after checking with pump
        # return val.decode()

    def set_refill_rate(self, rate, units="UM", resource=pumpserial):
        # consider moving to after checking with pump
        if not HPump.enabled:
            return

        ratestr = str(rate).zfill(5)
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+"RFR"+ratestr+units+"\n\r").encode())

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"RFR"+ratestr+units+"\n\r").encode())

        # TODO: add possibillity to change units
        self.fillrate = rate    # consider moving to after checking with pump
        # return val.decode()

    def set_flow_rate(self, rate, units="UM", resource=pumpserial):
        # Function to change the current flowrate whether infuse or withdraw
        if not HPump.enabled:
            return

        if(self.infusing):
            return self.set_infuse_rate(rate, units)
        else:
            return self.set_refill_rate(rate, units)

    def send_command(self, command, resource=pumpserial):   # sends an albitrary command
        if not HPump.enabled:
            return
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((command).encode())
        else:
            self.controller.write(("-"+command).encode())

    def infuse(self, resource=pumpserial):
        if not HPump.enabled:
            return
        self.infusing = True
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+'DIRINF'+"\n\r").encode())

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"DIRINF"+"\n\r").encode())

    def refill(self, resource=pumpserial):
        if not HPump.enabled:
            return
        self.infusing = False
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+'DIRREF'+"\n\r").encode())

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"DIRREF"+"\n\r").encode())

    def reverse(self, resource=pumpserial):
        if not HPump.enabled:
            return
        self.infusing = not self.infusing
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+'DIRREV'+"\n\r").encode())

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"DIRREV"+"\n\r").encode())

    def setmodepump(self,  resource=pumpserial):
        if not HPump.enabled:
            return
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+'MOD PMP'+"\n\r").encode())

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD PMP"+"\n\r").encode())

    def setmodevol(self,  resource=pumpserial):
        if not HPump.enabled:
            return
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+'MOD VOL'+"\n\r").encode())

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD VOL"+"\n\r").encode())

    def setmodeprogam(self,  resource=pumpserial):
        if not HPump.enabled:
            return
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+'MOD PGM'+"\n\r").encode())

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD PGM"+"\n\r").encode())

    def settargetvol(self, vol, resource=pumpserial):
        if not HPump.enabled:
            return
        volstr = str(vol).zfill(5)
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+'TGT'+volstr+"\n\r").encode())

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+'TGT'+volstr+"\n\r").encode())

    def statuscheck(self, resource=pumpserial):
        if not HPump.enabled:
            return
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((self.address+"\n\r").encode())
            while(resource.in_waiting>0):
                print(resource.read())

        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+'TGT'+volstr+"\n\r").encode())
            while(self.controller.in_waiting>0):
                print(self.controller.read())


    def stop(self, resource=pumpserial):
        if not HPump.enabled:
            return
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write(("\n\r").encode())

        else:
            if not self.controller.is_open:
                self.controller.open()

            self.controller.write(("-\n\r").encode())


    def close(self):
        if HPump.pumpserial.is_open:
            HPump.pumpserial.close()



class Rheodyne:
    """Class to control Rheodyne valves."""

    def __init__(self, name="Rheodyne", valvetype=0, position=0, pc_connect=True, address_ic2=-1, enabled=False, logger=[]):
        self.name = name                      # valve nickname
        self.valvetype = valvetype            # int to mark max number of valve possions 2 or 6
        self.position = position
        self.pc_connect = pc_connect
        self.enabled = enabled
        self.logger = logger
        self.address_ic2 = address_ic2
        # now lets create a serial object within the class to address the valve
        # I am presetting baudrate to that expdcted from rheodyne valves.
        # Actual baudrate can change- they just must agree.
        self.serial_object = serial.Serial(baudrate=19200, timeout=0.1)
        # set port throughuh another function.

    def set_port(self, port):  # will keep set port accross different classes
        if self.serial_object.is_open:
            self.serial_object.close()
        self.serial_object.port = port
        self.enabled = True
        self.pc_connect = True
        self.logger.append(self.name+" port set to "+port)

    def set_to_controller(self, controller):
        self.pc_connect = False
        self.controller = controller
        self.enabled = True
        self.logger.append(self.name+" set to Microntroller")


    def changevalues(self,address,name):
        if not self.name==name:
            self.logger.append("Changing Name: "+ self.name+" to "+name)
            self.name=name
        if not self.addressI2C==address:
            self.logger.append("Setting "+ self.name+" address:"+address)
            self.addressI2C=address
    #"""Now the function to actually control de valve."""
    def switchvalve(self,position): #Lets take int
    #this function wont work for positions>10
    #to add that functionality the number must be
    #in hex format => P##  so 10 P0A
    #Need errror handler to check position is integer and less than valve type
        if not self.ennabled:

            return

        if self.pc_connect:
            if not self.serial_object.is_open:
                self.serial_object.open()
            self.serial_object.write(("P0"+str(position)+"\n\r").encode())
            ans = self.serial_object.read()
            # self.serial_object.close()           #Trying to be polite and leaving the ports closed

        elif self.address_ic2 == -1:
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
                return 0    #Valve acknowledged command
            else:
                self.logger.append("Error Switching "+self.name)
                return -1   #error valve didnt acknowledge


    # Todo maybe incorporate status check to confirm valve is in the right position
    def statuscheck(self):
        if not self.enabled:
            return

        if self.pc_connect:
            if not self.serial_object.is_open:
                self.serial_object.open()
            while self.serial_object.in_waiting>0:
                self.serial_object.read()
            self.serial_object.write("S\n\r".encode())
            ans = self.serial_object.read(2).decode()
            self.serial_object.read()
            print(ans)
            return int(ans)   # returns valve position
            # TODO: add error handlers
        elif self.address_ic2 == -1:
            self.logger.append("Error: I2C Address not set for "+self.name)
            return
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
        if address % 2 == 0:
            if self.pc_connect:
                s = hex(address)
                if not self.serial_object.is_open:
                    self.serial_object.open()
                self.serial_object.write(("N"+s[2:4]+"\n\r").encode())
                return 0
            elif self.address_ic2 == -1:
                return -1
            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("N%03i%03i" % (self.address_ic2, address)).encode())
                while(self.controller.in_waiting > 0):
                    print(self.controller.readline())
                # self.controller.close()
                return 0
        else:
            return -1  # TODO: Error because value is not even
        return  # ans

    def close(self):
        if self.serial_object.is_open:
            self.serial_object.close()


class VICI:
    """Class to control a VICI valve."""

    def __init__(self, name="VICI", address="", enabled=False, pc_connect=True, position=0, logger=[]):
        self.name = name
        self.address = address
        self.enabled = enabled
        self.pc_connect = pc_connect
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
        self.serialobject = controller
        self.ennabled = True
        self.ControllerKey="+"
        self.serialobject.open()

        self.logger.append(self.name+" set to Microntroller")

    def switchvalve(self, position):
        if isinstance(position,int):
            if position == 0:
                position = 'A'
            if position == 1:
                position = 'B'
        if not self.enabled:
            self.logger.append(self.name+" not set up, switching ignored")
            return

        if not self.serialobject.is_open:
            self.serialobject.open()
        commandtosend=self.ControllerKey+"GO"+position+"\r"
        self.serialobject.write(commandtosend.encode())
        self.logger.append(self.name+" switched to "+position)
        while self.serialobject.in_waiting>0:
            self.logger.append(self.serialobject.readline())

    def currentposition(self):
        if not self.enabled:
            self.logger.append(self.name+" not set up, switching ignored")
            return

        if not self.serialobject.is_open:
            self.serialobject.open()
        commandtosend=self.ControllerKey+"CP"+"\r"
        self.serialobject.write(commandtosend.encode())

        self.logger.append(self.name+" Position Query ")
        while self.serial_object.in_waiting > 0:
            self.logger.append(self.serial_object.readline().decode())

    def change_values(self, address, name):
        if self.name != name:
            self.logger.append("Changing Name: "+self.name+" to "+name)
            self.name = name

    def close(self):
        if self.serial_object.is_open:
            self.serial_object.close()
