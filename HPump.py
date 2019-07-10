"""
Class definition to control a Hardvard pump through UART serial communication
The class shares a COM port. This ennables to configure several pumps though a
PUMP chai- Therefore it doesn't support multiple pumps connected directly to
Computer

Version 1-04/04/19
Pollack Lab- Ccornell University
Josue San Emeterio
"""

import serial  # needs serial- does import need to be elsewhere?


class SAXSController(serial.Serial):
    # function to initialize ports
    def set_port(self, number):
        if self.is_open:
            self.close()
        self.port = "COM"+str(number)
    # Init


class HPump:

    # need a single serisl for the clsss
    pumpserial = serial.Serial()

    # Set port protperties
    pumpserial.baudrate = 9600
    pumpserial.stopbits = 2
    pumpserial.timeout = 1

    def set_port(self, number, resource=pumpserial):
        """Set the port of a pump and initialize"""
        if resource.is_open:
            resource.close()
        resource.port = "COM"+str(number)
        # TODO: implent for things other than COM(num)

    # Pump intialization need pump number
    # need to set defsults fpr simpler impoementation
    def __init__(self, address=0, PCConnect=True, running=False, infusing=True):
        self.address = str(address)
        self.running = running
        self.infusing = infusing
        self.PCConnect = PCConnect
        # add init for syringe dismeter,flowrate, Direction etc

    # function  to send control over the controller
    def set_to_controller(self, controller):
        """Send control to the controller"""
        self.PCConnect = False
        self.controller = controller

# Pump action commands
# To do in all. Read in confirmstion from pump.

    def start_pump(self, resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+"RUN\n\r").encode())  # needs both terminators
            # val=resource.read_until("\n\r")
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"RUN\n\r").encode())

        self.running = True     # Consider switching to after checking with pump
        # return val.decode()

    def stop_pump(self, resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+"STP\n\r").encode())
            # val=resource.read_until("\n\r")
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"STP\n\r").encode())

        self.running = False     # consider moving to after checking with pump
        # return val.decode()

    def set_infuse_rate(self, rate, units="UM", resource=pumpserial):
        # consider moving to after checking with pump
        ratestr = str(rate).zfill(5)
        if self.PCConnect:
            resource.open()
            resource.write((self.address+"RAT"+ratestr+units+"\n\r").encode())
            # val = resource.read(4)
            # TODO: add possibillity to change units
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"RAT"+ratestr+units+"\n\r").encode())

        self.infuserate = rate   # consider moving to after checking with pump
        # return val.decode()

    def set_refill_rate(self, rate, units="UM", resource=pumpserial):
        # consider moving to after checking with pump
        ratestr = str(rate).zfill(5)
        if self.PCConnect:
            resource.open()
            resource.write((self.address+"RFR"+ratestr+units+"\n\r").encode())
            resource.close()
            # val=resource.read(4)
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"RFR"+ratestr+units+"\n\r").encode())

        # TODO: add possibillity to change units
        self.fillrate = rate  # consider moving to after checking with pump
        # return val.decode()

    def set_flow_rate(self, rate, units="UM", resource=pumpserial):
        """Change the current flowrate whether infuse or withdraw"""
        if(self.infusing):
            return self.set_infuse_rate(rate, units)
        else:
            return self.set_refill_rate(rate, units)

    def send_command(self, command, resource=pumpserial):  # sends an albitrary command
        resource.open()
        resource.write((command).encode())
        resource.close()

    def infuse(self, resource=pumpserial):
        self.infusing = True
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'DIRINF'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"DIRINF"+"\n\r").encode())

    def refill(self,  resource=pumpserial):
        self.infusing = False
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'DIRREF'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"DIRREF"+"\n\r").encode())

    def reverse(self,  resource=pumpserial):
        self.infusing = not self.infusing
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'DIRREV'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"DIRREV"+"\n\r").encode())

    def set_mode_pump(self,  resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'MOD PMP'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD PMP"+"\n\r").encode())

    def set_mode_vol(self,  resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'MOD VOL'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD VOL"+"\n\r").encode())

    def set_mode_program(self, resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'MOD PGM'+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+"MOD PGM"+"\n\r").encode())

    def set_target_vol(self, vol, resource=pumpserial):
        volstr = str(vol).zfill(5)
        if self.PCConnect:
            resource.open()
            resource.write((self.address+'TGT'+volstr+"\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("-"+self.address+'TGT'+volstr+"\n\r").encode())

    def stop_all(self, resource=pumpserial):
        if self.PCConnect:
            resource.open()
            resource.write(("\n\r").encode())
            resource.close()
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("\n\r").encode())


# TODO: Add functions to querry pump- double check Diameter, fslowraate, and check volume
