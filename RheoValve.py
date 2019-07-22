"""
Class definition to control Rheodyne MXII
Initial set up using UART communication directly through USB
All functions in this version need testing. with actual pump.
"""

import serial  # Needed for direct communication


class Valve:
    def __init__(self, name="", valvetype=0, position=0, pc_connect=True, address_ic2=-1):
        self.name = name                      # valve nickname
        self.valvetype = valvetype            # int to mark max number of valve possions 2 or 6
        self.position = position
        self.pc_connect = pc_connect
        # now lets create a serial object within the class to address the valve
        # I am presetting baudrate to that expdcted from rheodyne valves.
        # Actual baudrate can change- they just must agree.
        self.serial_object = serial.Serial(baudrate=19200, timeout=1)
        # set port throughuh another function.

    def __init2__(self, name="", valvetype=0, position=0):
        self.name = name                      # valve nickname
        self.valvetype = valvetype            # int to mark max number of valve possions 2 or 6
        self.position = position
        # now lets create a serial object within the class to address the valve
        # I am presetting baudrate to that expdcted from rheodyne valves.
        # Actual baudrate can change- they just must agree.
        self.serial_object = serial.Serial(baudrate=19200, timeout=1)
        # set port through another function.
        # TODO: error handler to  avoid using withouth port being configured!!!

    def set_port(self, number):  # will keep set port accross different classes
        if self.serial_object.is_open:
            self.serial_object.close()
        self.serial_object.port = "COM" + str(number)

    def set_to_controller(self, controller):
        self.pc_connect = False
        self.controller = controller

    def switchvalve(self, position):     # Lets take int
        """Control the valve position"""
        # this function wont work for positions>10
        # to add that functionality the number must be
        # in hex format => P##  so 10 P0A
        # Need errror handler to check position is integer and less than valve type
        if self.pc_connect:
            if not self.serial_object.is_open:
                self.serial_object.open()
            self.serial_object.write(("P0" + str(position) + "\n\r").encode())
            ans = self.serial_object.read()
            # self.serial_object.close()           #Trying to be polite and leaving the ports closed
            if ans == b'\r':     # pump returns this if command acknowledged
                self.position = position
                return 0    # Valve acknowledged command
            else:
                return -1   # error valve didnt acknowledge
        elif self.address_ic2 == -1:
            return -1
        else:
            if not self.controller.is_open:
                self.controller.open()
            self.controller.write(("P%03i%i" % (self.address_ic2, position)).encode())
            ans = self.controller.read()
            # self.controller.close()           #Trying to be polite and leaving the ports closed
            if ans == b'0':  # pump returns this if command acknowledged
                self.position = position
                return 0    # Valve acknowledged commsnd
            else:
                return -1   # error valve didnt acknowledge

        # todo maybe incorporate status check to confirm valve is in the right position
    def statuscheck(self):
        if self.pc_connect:
            if not self.serial_object.is_open:
                self.serial_object.open()
            self.serial_object.write("S\n\r".encode())
            ans = self.serial_object.read(2)  # need to ensure thwt buffer doesnt build up-> if so switch to readln
            self.serial_object.close()
            return int(ans)   # returns valve position
            # TODO: add error handlers
        elif self.address_ic2 == -1:
            return -1
        else:
            if not self.controller.is_open:
                self.controller.open()
                self.controller.write(("S%03i" % self.address_ic2).encode())
                ans = self.controller.read()     # need to ensure thwt buffer doesnt build up-> if so switch to readln
            # self.controller.close()
        return int(ans)   # returns valve position
        # TODO: add error handlers

    def seti2caddress(self, address: int):  # Address is in int format
        # Address needs to be even int
        if address % 2 == 0:
            if self.pc_connect:
                s = hex(address)
                self.serial_object.open()
                self.serial_object.write(("N"+s[2:4]+"\n\r").encode())
                self.serial_object.close()
                return 0
            elif self.address_ic2 == -1:
                return -1
            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("N%03i%03i" % (self.address_ic2, address)).encode())
                while(self.controller.in_waiting() > 0):
                    print(self.controller.readline())
                # self.controller.close()
                return 0
        else:
            return -1  # TODO: Error because value is not even
        return  # ans
