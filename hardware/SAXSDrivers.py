"""Class definition to control a Hardvard pump through UART serial communication.

The class shares a COM port. This enables to configure several pumps though a
PUMP chain- Therefore it doesn't support multiple pumps connected directly to
Computer

Version 1-04/04/19
Pollack Lab- Ccornell University
Josue San Emeterio
"""
import serial
import serial.tools.list_ports
import time


def list_available_ports(optional_list=[]):   # Does the optional list input do anything? Should we just initialize an empty list for the output?
    """Find and return all available COM ports. If passed a list will update that list with the current set of COM ports."""
    optional_list.clear()
    for item in list(serial.tools.list_ports.comports()):
        optional_list.append(item)
    return optional_list


def InstrumentTerminateFunction(instrument_list):
    """Stop all instruments in a list if they can be stopped."""
    for instrument in instrument_list:
        if hasattr(instrument, "stop"):
            instrument.stop()


class SAXSController(serial.Serial):
    """Class for communication with devices using the USB box."""

    def __init__(self, logger=[], **kwargs):
        """Initialize class."""
        super().__init__(**kwargs)
        self.logger = logger
        self.enabled = False

    def set_port(self, port, instrument_list=[]):
        """Set the serial port."""
        if self.is_open:
            self.close()
        self.port = port
        self.open()
        self.enabled = True
        self.logger.info("Controller set to port "+port)
        for instrument in instrument_list:
            if instrument.pc_connect == False:
                instrument.set_to_controller(self)

    def scan_i2c(self):
        """Scan I2C line."""
        if not self.enabled:
            self.logger.info("Microcontroller not set up")
            raise ValueError
        if not self.is_open:
            self.open()
        self.write(b'I')
        while self.in_waiting > 0:
            self.logger.info(self.readline().decode())

# To finish for Hardware Configure
    def get_addresses(self):
        if not self.enabled:
            self.logger.info("Microcontroller not set up")
            raise ValueError
        if not self.is_open:
            self.open()
        # Check instruments
        self.write(b'I')
        while self.in_waiting > 0:
            self.logger.info(self.readline().decode())


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

    def __init__(self, address=0, pc_connect=True, running=False, infusing=True, name="Pump", logger=[], hardware_configuration="", lock=None):
        """Initialize HPump."""
        self.address = str(address)
        self.running = running
        self.infusing = infusing
        self.pc_connect = pc_connect
        self.logger = logger
        self.name = name
        self.instrument_type = "Pump"
        self.hardware_configuration = hardware_configuration
        self._lock = lock
        # add init for syringe dismeter,flowrate, Direction etc

    # function to initialize ports
    def set_port(self, port, resource=pumpserial):
        """Set the pump port."""
        if resource.is_open:
            resource.close()
        resource.port = port
        self.pc_connect = True
        HPump.enabled = True
        self.logger.info(self.name+" port set to "+port)

    # function  to send control over the controller
    # Pump intialization need pump number
    # need to set defsults fpr simpler impoementation

    def set_to_controller(self, controller):
        """Set the control to a controller rather than direct."""
        self.pc_connect = False
        self.controller = controller
        HPump.enabled = controller.enabled
        self.logger.info(self.name+" set to Microntroller")

    def change_values(self, address, name):
        """Change the name or address of the instrument."""
        if self.name != name:
            self.logger.info("Changing Name: "+self.name+" to "+name)
            self.name = name
        if self.address != address:
            self.logger.info("Setting "+self.name+" address: "+ str(address))
            self.address = str(address)

# Pump action commands
# To do in all. Read in confirmstion from pump.

    def start_pump(self, resource=pumpserial):
        """Send a start command to the pump."""
        with self._lock:
            responceflag = False
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                while resource.in_waiting > 0:  # Clear Buffer
                    resource.readline()
                resource.write((self.address+"RUN\n\r").encode())
                time.sleep(0.2)
                if resource.in_waiting == 0:  # give extra time if it hasn't responded
                    time.sleep(0.2)
                while resource.in_waiting > 0:
                    pumpanswer = resource.readline().decode()
                    if self.address+"<" in pumpanswer:
                        self.running = True
                        self.logger.info("Refilling " + self.name)
                        responceflag = True
                    elif self.address+">" in pumpanswer:
                        self.running = True
                        self.logger.info("Infusing " + self.name)
                        responceflag = True
            else:
                if not self.controller.is_open:
                    self.controller.open()
                while self.controller.in_waiting > 0:  # Clear Buffer
                    self.controller.readline()
                self.controller.write(("-"+self.address+"RUN\n\r").encode())
                time.sleep(0.2)
                if self.controller.in_waiting == 0:  # give more time if it hasn't finished
                    time.sleep(0.2)
                while self.controller.in_waiting > 0:
                    pumpanswer = self.controller.readline().decode()
                    if self.address+"<" in pumpanswer:
                        self.running = True
                        self.logger.info("Refilling " + self.name)
                        responceflag = True
                    elif self.address+">" in pumpanswer:
                        self.running = True
                        self.logger.info("Infusing " + self.name)
                        responceflag = True
            if not responceflag:
                self.logger.info("Error starting pump")
                raise RuntimeError

    def stop_pump(self, resource=pumpserial):
        with self._lock:
            responceflag = False
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                while resource.in_waiting > 0:  # Clear Buffer
                    resource.readline()
                resource.write((self.address+"STP\n\r").encode())
                time.sleep(0.2)
                if resource.in_waiting == 0:  # give extra time if it hasn't responded
                    time.sleep(0.2)
                while resource.in_waiting > 0:  # Clear Buffer
                    pumpanswer = resource.readline()
                    if self.address+"*" in pumpanswer:
                        self.running = False
                        self.logger.info("Paused " + self.name)
                        responceflag = True
                    elif self.address+":" in pumpanswer:
                        self.running = False
                        self.logger.info("Stopped " + self.name)
                        responceflag = True
            else:
                if not self.controller.is_open:
                    self.controller.open()
                while self.controller.in_waiting > 0:  # Clear Buffer
                    self.controller.readline()
                self.controller.write(("-"+self.address+"STP\n\r").encode())
                time.sleep(0.2)
                if self.controller.in_waiting == 0:  # give more time if it hasn't finished
                    time.sleep(0.2)
                while self.controller.in_waiting > 0:
                    pumpanswer = self.controller.readline().decode()
                    if self.address+":" in pumpanswer:
                        self.running = False
                        self.logger.info("Paused " + self.name)
                        responceflag = True
                    elif self.address+"*" in pumpanswer:
                        self.running = False
                        self.logger.info("Stopped " + self.name)
                        responceflag = True
            if not responceflag:
                self.logger.info("Error Stopping Pump")
                raise RuntimeError

    def set_infuse_rate(self, rate, units="UM", resource=pumpserial):
        # consider moving to after checking with pump
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
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
            time.sleep(0.2)
            if rate == self.check_infuse_rate():
                self.logger.info(self.name+" infuse Rate set to "+str(rate))
                self.infuserate = rate
            else:
                self.logger.info("Error setting infuse rate for "+self.name)
                raise RuntimeError

    def set_refill_rate(self, rate, units="UM", resource=pumpserial):
        # consider moving to after checking with pump
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError

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
            time.sleep(0.2)
            if rate == self.check_refill_rate():
                self.logger.info(self.name+" refill rate set to "+str(rate))
                self.fillrate = rate
            else:
                self.logger.info("Error setting refill rate for "+self.name)
                raise RuntimeError

    def set_flow_rate(self, rate, units="UM", resource=pumpserial):
        # Function to change the current flowrate whether infuse or withdraw
        if not HPump.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError

        if(self.infusing):
            return self.set_infuse_rate(rate, units)
        else:
            return self.set_refill_rate(rate, units)

    def send_command(self, command, resource=pumpserial):   # sends an albitrary command
        if not HPump.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            resource.write((command).encode())
        else:
            self.controller.write(("-"+command).encode())

    def infuse(self, resource=pumpserial):
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            self.infusing = True
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                resource.write((self.address+'DIRINF'+"\n\r").encode())

            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("-"+self.address+"DIRINF"+"\n\r").encode())
            time.sleep(0.2)
            self.check_direction("INFUSE")
            self.logger.info(self.name+" set to infuse")

    def refill(self, resource=pumpserial):
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            self.infusing = False
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                resource.write((self.address+'DIRREF'+"\n\r").encode())

            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("-"+self.address+"DIRREF"+"\n\r").encode())
            time.sleep(0.2)
            self.check_direction("REFILL")
            self.logger.info(self.name+" set to refill")

    def reverse(self, resource=pumpserial):
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            self.infusing = not self.infusing
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                resource.write((self.address+'DIRREV'+"\n\r").encode())

            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("-"+self.address+"DIRREV"+"\n\r").encode())

    def set_mode_pump(self,  resource=pumpserial):
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                return
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                resource.write((self.address+'MOD PMP'+"\n\r").encode())

            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("-"+self.address+"MOD PMP"+"\n\r").encode())
            time.sleep(0.2)
            self.check_mode("PUMP")
            self.logger.info(self.name+" mode set to PUMP")

    def set_mode_vol(self,  resource=pumpserial):
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                resource.write((self.address+'MOD VOL'+"\n\r").encode())

            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("-"+self.address+"MOD VOL"+"\n\r").encode())
            time.sleep(0.2)
            self.check_mode("VOL")
            self.logger.info(self.name+" mode set to VOL")

    def set_mode_progam(self,  resource=pumpserial):
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                resource.write((self.address+'MOD PGM'+"\n\r").encode())

            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("-"+self.address+"MOD PGM"+"\n\r").encode())
            time.sleep(0.2)
            self.check_mode("PROG")
            self.logger.info(self.name+" Mode set to program")

    def set_target_vol(self, vol, resource=pumpserial):
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            volstr = str(vol).zfill(5)
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                resource.write((self.address+'TGT'+volstr+"\n\r").encode())

            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("-"+self.address+'TGT'+volstr+"\n\r").encode())

            time.sleep(0.2)
            self.logger.info(self.name+" Target Vol is "+str(self.check_target_volume())+" ml")

    def is_running(self, resource=pumpserial):
        with self._lock:
            running = False
            success = False
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            if self.pc_connect:
                if not resource.is_open:
                    resource.open()
                while resource.in_waiting > 0:  # Clear Buffer
                    resource.readline().decode()
                resource.write((self.address+"\n\r").encode())  # Query Pump
                time.sleep(0.2)
                while resource.in_waiting > 0:
                    answer = resource.readline().decode()
                    if self.address in answer:
                        if "<" in answer:
                            running = True
                            success = True
                        elif ">" in answer:
                            running = True
                            success = True
                        elif ":" in answer:
                            running = False
                            success = True
                        elif "*" in answer:
                            running = False
                            success = True
                if success:
                    return running
                else:
                    self.logger.info("Failure Connecting to Pump")
                    return True
            else:
                if not self.controller.is_open:
                    self.controller.open()
                while self.controller.in_waiting > 0:   # Clear Buffer
                    self.logger.info(self.controller.read().decode())
                self.controller.write(("-"+self.address+"\n\r").encode())
                time.sleep(0.2)
                while self.controller.in_waiting > 0:
                    try:
                        answer = self.controller.readline()
                        answer = answer.decode()
                    except:
                        self.logger.debug(repr(answer))
                        raise RuntimeError
                    if self.address in answer:
                        if "<" in answer:
                            running = True
                            success = True
                        elif ">" in answer:
                            running = True
                            success = True
                        elif ":" in answer:
                            running = False
                            success = True
                        elif "*" in answer:
                            running = False
                            success = True
                if success:
                    return running
                else:
                    self.logger.info("Failure Connecting to Pump")
                    return True
                    # raise RuntimeError Not raising so that if one fails queue isnt dumped

    def wait_until_time(self, wait_time, command_while_waiting=lambda *_: None):
        currenttime = time.time()
        endtime = currenttime + wait_time
        while self.is_running() and time.time() < endtime:
            time.sleep(0.1)
            command_while_waiting()


    def wait_until_stopped(self, timeout=60, command_while_waiting=lambda *_: None):
        currenttime = 0
        while self.is_running() and currenttime < timeout:
            time.sleep(0.1)
            currenttime += 0.1
            command_while_waiting()
        if not currenttime < timeout:
            self.logger.info("Pump wait timeout")
            raise RuntimeError

    def infuse_volume(self, volume, rate):
        self.infuse()
        time.sleep(0.1)
        self.set_mode_vol()
        time.sleep(0.1)
        self.set_target_vol(volume)
        time.sleep(0.1)
        self.set_infuse_rate(rate)
        time.sleep(0.1)
        self.start_pump()
        # self.wait_until_stopped(2*volume*1000/rate)  # wait for it to stop

    def refill_volume(self, volume, rate):
        self.refill()
        time.sleep(0.1)
        self.set_mode_vol()
        time.sleep(0.1)
        self.set_target_vol(volume)
        time.sleep(0.1)
        self.set_refill_rate(rate)
        time.sleep(0.1)
        self.start_pump()
        # self.wait_until_stopped(2*volume*1000/rate)  # wait for it to stop

    def check_direction(self, dirstr="k", resource=pumpserial):
        success = False
        if not HPump.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            while resource.in_waiting > 0:  # Clear Buffer
                resource.readline().decode()
            resource.write((self.address+"DIR"+"\n\r").encode())  # Query Pump
            time.sleep(0.2)
            while resource.in_waiting > 0:
                if dirstr in resource.readline().decode():
                    success = True
            if not success:
                self.logger.info("Failure Connecting to Pump")
                raise RuntimeError
        else:
            if not self.controller.is_open:
                self.controller.open()
            while self.controller.in_waiting > 0:   # Clear Buffer
                self.controller.read().decode()
            self.controller.write(("-"+self.address+"DIR"+"\n\r").encode())
            time.sleep(0.2)
            while self.controller.in_waiting > 0:
                if dirstr in self.controller.readline().decode():
                    success = True
            if not success:
                self.logger.info("Failure Connecting to Pump")
                raise RuntimeError

    def check_mode(self, modestr="k", resource=pumpserial):
        success = False
        if not HPump.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            while resource.in_waiting > 0:  # Clear Buffer
                resource.readline().decode()
            resource.write((self.address+"MOD"+"\n\r").encode())  # Query Pump
            time.sleep(0.2)
            while resource.in_waiting > 0:
                if modestr in resource.readline().decode():
                    success = True
            if not success:
                self.logger.info("Failure Connecting to Pump")
                raise RuntimeError
        else:
            if not self.controller.is_open:
                self.controller.open()
            while self.controller.in_waiting > 0:   # Clear Buffer
                self.controller.read().decode()
            self.controller.write(("-"+self.address+"MOD"+"\n\r").encode())
            time.sleep(0.2)
            while self.controller.in_waiting > 0:
                if modestr in self.controller.readline().decode():
                    success = True
            if not success:
                self.logger.info("Failure Connecting to Pump")
                raise RuntimeError

    def check_target_volume(self, resource=pumpserial):
        success = False
        if not HPump.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            while resource.in_waiting > 0:  # Clear Buffer
                resource.readline().decode()
            resource.write((self.address+"TGT"+"\n\r").encode())  # Query Pump
            time.sleep(0.2)
            while resource.in_waiting > 0:
                answer = (resource.readline().decode())
                if "." in answer:
                    value = float(answer)
                    success = True

        else:
            if not self.controller.is_open:
                self.controller.open()
            while self.controller.in_waiting > 0:   # Clear Buffer
                self.controller.read().decode()
            self.controller.write(("-"+self.address+"TGT"+"\n\r").encode())
            time.sleep(0.2)
            while self.controller.in_waiting > 0:
                answer = (self.controller.readline().decode())
                if "." in answer:
                    value = float(answer)
                    success = True
        if not success:
            self.logger.info("Failure Connecting to Pump")
            raise RuntimeError
        else:
            return value

    def check_infuse_rate(self, resource=pumpserial):
        success = False
        if not HPump.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            while resource.in_waiting > 0:  # Clear Buffer
                resource.readline().decode()
            resource.write((self.address+"RAT"+"\n\r").encode())  # Query Pump
            time.sleep(0.2)
            while resource.in_waiting > 0:
                answer = (resource.readline().decode())
                if "." in answer:
                    value = float(answer[0:-7])
                    success = True

        else:
            if not self.controller.is_open:
                self.controller.open()
            while self.controller.in_waiting > 0:   # Clear Buffer
                self.controller.read().decode()
            self.controller.write(("-"+self.address+"RAT"+"\n\r").encode())
            time.sleep(0.2)
            while self.controller.in_waiting > 0:
                answer = (self.controller.readline().decode())
                if "." in answer:
                    value = float(answer[0:-7])
                    success = True
        if not success:
            self.logger.info("Failure Connecting to Pump")
            raise RuntimeError
        else:
            return value

    def check_refill_rate(self, resource=pumpserial):
        success = False
        if not HPump.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            while resource.in_waiting > 0:  # Clear Buffer
                resource.readline().decode()
            resource.write((self.address+"RFR"+"\n\r").encode())  # Query Pump
            time.sleep(0.2)
            while resource.in_waiting > 0:
                answer = (resource.readline().decode())
                if "." in answer:
                    value = float(answer[0:-7])
                    success = True
        else:
            if not self.controller.is_open:
                self.controller.open()
            while self.controller.in_waiting > 0:   # Clear Buffer
                self.controller.read().decode()
            self.controller.write(("-"+self.address+"RFR"+"\n\r").encode())
            time.sleep(0.2)
            while self.controller.in_waiting > 0:
                answer = (self.controller.readline().decode())
                if "." in answer:
                    value = float(answer[0:-7])
                    success = True
        if not success:
            self.logger.info("Failure Connecting to Pump")
            raise RuntimeError
        else:
            return value

    def get_delivered_volume(self, resource=pumpserial):
        success = False
        if not HPump.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError
        if self.pc_connect:
            if not resource.is_open:
                resource.open()
            while resource.in_waiting > 0:  # Clear Buffer
                resource.readline().decode()
            resource.write((self.address+"DEL"+"\n\r").encode())  # Query Pump
            time.sleep(0.2)
            while resource.in_waiting > 0:
                answer = (resource.readline().decode())
                if "." in answer:
                    value = float(answer[0:-7])
                    success = True
        else:
            if not self.controller.is_open:
                self.controller.open()
            while self.controller.in_waiting > 0:   # Clear Buffer
                self.controller.read().decode()
            self.controller.write(("-"+self.address+"DEL"+"\n\r").encode())
            time.sleep(0.2)
            while self.controller.in_waiting > 0:
                answer = (self.controller.readline().decode())
                if "." in answer:
                    value = float(answer[0:-7])
                    success = True
        if not success:
            self.logger.info("Failure Connecting to Pump")
            raise RuntimeError
        else:
            return value

    def stop(self, resource=pumpserial):
        with self._lock:
            if not HPump.enabled:
                self.logger.info(self.name+" not enabled")
                return  # not raising error so that the remaining of the stop function isnt dumped
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

    def __init__(self, name="Rheodyne", valvetype=0, position=0, pc_connect=True, address_I2C=-1, enabled=False, logger=[], hardware_configuration="", lock=None):
        self.name = name                      # valve nickname
        self.valvetype = valvetype            # int to mark max number of valve possions 2 or 6
        self.position = position
        self.pc_connect = pc_connect
        self.enabled = enabled
        self.logger = logger
        self.address_I2C = address_I2C
        # now lets create a serial object within the class to address the valve
        # I am presetting baudrate to that expdcted from rheodyne valves.
        # Actual baudrate can change- they just must agree.
        self.serial_object = serial.Serial(baudrate=19200, timeout=0.1)
        # set port throughuh another function.
        self.instrument_type = "Rheodyne"
        self.hardware_configuration = hardware_configuration
        self._lock = lock

    def set_port(self, port):  # will keep set port accross different classes
        if self.serial_object.is_open:
            self.serial_object.close()
        self.serial_object.port = port
        self.enabled = True
        self.pc_connect = True
        self.logger.info(self.name+" port set to "+port)

    def set_to_controller(self, controller):
        self.pc_connect = False
        self.controller = controller
        self.enabled = controller.enabled
        self.logger.info(self.name+" set to Microntroller")

    def change_values(self, address, name):
        if not self.name == name:
            self.logger.info("Changing Name: " + self.name+" to "+name)
            self.name = name
        if not self.address_I2C == address:
            self.logger.info("Setting " + self.name+" address:"+str(address))
            self.address_I2C = address

    # """Now the function to actually control de valve."""
    def switchvalve(self, position, attempts=0, max_attemps=3):  # Lets take int
        # this function wont work for positions>10
        # to add that functionality the number must be
        # in hex format => P##  so 10 P0A
        # Need errror handler to check position is integer and less than valve type
        with self._lock:
            if attempts > max_attemps:
                self.logger.info("Error Switching "+self.name)
                raise RuntimeError  # error valve didnt acknowledge
            if not self.enabled:
                self.logger.info(self.name+" not enabled")
                raise ValueError
            if self.pc_connect:
                if not self.serial_object.is_open:
                    self.serial_object.open()
                self.serial_object.write(("P0"+str(position)+"\n\r").encode())
                self.serial_object.read()
                # self.serial_object.close()           #Trying to be polite and leaving the ports closed

            elif self.address_I2C == -1:
                self.logger.info(self.name+"I2C Address not set")
                raise ValueError
                return -1
            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("P%03i%i" % (self.address_I2C, position)).encode())
                self.controller.read()

            # check if switched
            time.sleep(0.1)
            if int(self.statuscheck()) == position:  # pump returns this if command acknowledged
                self.position = position
                self.logger.info(self.name+" switched to "+str(position))
                return 0    # Valve acknowledged commsnd
            else:
                self.logger.info("Switching valve %s failed; retrying %i" % (self.name, attempts))
                self.switchvalve(position, attempts+1, max_attemps)

    # Todo maybe incorporate status check to confirm valve is in the right position
    def statuscheck(self, iter=0):
        maxiterations = 10
        if not self.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError

        if self.pc_connect:
            if not self.serial_object.is_open:
                self.serial_object.open()
            while self.serial_object.in_waiting > 0:
                self.serial_object.read()
            self.serial_object.write("S\n\r".encode())
            ans = self.serial_object.read(2).decode()
            self.serial_object.read()
            while ans not in ["01", "02", "03", "04", "05", "06"]:
                self.logger.info("Rechecking Valve: iteration " + str(iter+1))
                if iter == maxiterations:
                    self.logger.info("Error Checking Valve Status for "+self.name)
                    raise RuntimeError
                time.sleep(0.2)
                ans = self.statuscheck(iter+1)
            return ans   # returns valve position
            # TODO: add error handlers
        elif self.address_I2C == -1:
            self.logger.info("Error: I2C Address not set for "+self.name)
            raise ValueError
            return
        else:
            if not self.controller.is_open:
                self.controller.open()
            while self.controller.in_waiting > 0:
                self.controller.read()
            self.controller.write(("S%03i" % self.address_I2C).encode())
            ans = self.controller.read().decode()  # need to ensure thwt buffer doesnt build up-> if so switch to readln
            while ans not in ["1", "2", "3", "4", "5", "6"]:
                self.logger.info("Rechecking Valve: iteration " + str(iter+1))
                if iter == maxiterations:
                    self.logger.info("Error Checking Valve Status for "+self.name)
                    raise RuntimeError
                time.sleep(0.2)
                ans = self.statuscheck(iter+1)
            return ans   # returns valve position
        # TODO: add error handlers

            self.controller.write(("S%03i" % self.address_I2C).encode())
            ans = self.controller.read()  # need to ensure thwt buffer doesnt build up-> if so switch to readln
            # self.controller.close()
        return int(ans)   # returns valve position
        # TODO: add error handlers

    def seti2caddress(self, address: int):  # Address is in int format
        # Addres needs to be even int
        if not self.enabled:
            self.logger.info(self.name+" not enabled")
            raise ValueError
        if address % 2 == 0:
            if self.pc_connect:
                s = hex(address)
                if not self.serial_object.is_open:
                    self.serial_object.open()
                self.serial_object.write(("N"+s[2:4]+"\n\r").encode())
                return 0
            elif self.address_I2C == -1:
                return -1
            else:
                if not self.controller.is_open:
                    self.controller.open()
                self.controller.write(("N%03i%03i" % (self.address_I2C, address)).encode())
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

    def __init__(self, name="VICI", address="", enabled=False, pc_connect=True, position=0, logger=[], hardware_configuration="", lock=None):
        self.name = name
        self.address = address
        self.enabled = enabled
        self.pc_connect = pc_connect
        self.position = position
        self.logger = logger
        self.ControllerKey = ""
        self.serialobjectPC = serial.Serial(timeout=0.1, baudrate=9600)
        self.serialobject = self.serialobjectPC
        self.instrument_type = "VICI"
        self.hardware_configuration = hardware_configuration
        self._lock=lock

    def set_port(self, port):
        if self.serialobject.is_open:
            self.serialobject.close()
        self.serialobject = self.serialobjectPC
        self.serialobject.port = port
        self.enabled = True
        self.pc_connect = True
        self.ControllerKey = ""
        self.serialobject.open()
        self.logger.info(self.name + " set to port: " + port)

    def set_to_controller(self, controller):
        if self.serialobject.is_open:
            self.serialobject.close()
        self.pc_connect = False
        self.serialobject = controller
        self.enabled = controller.enabled
        self.ControllerKey = "+"
        self.logger.info(self.name+" set to Microntroller")

    def switchvalve(self, position):
        with self._lock:
            success = False
            if isinstance(position, int):
                if position == 0:
                    position = 'A'
                elif position == 1:
                    position = 'B'
                else:
                    self.logger.info("Value not accepted "+str(position))
                    raise ValueError
            if not self.enabled:
                self.logger.info(self.name+" not set up, switching ignored")
                raise ValueError
            if not self.serialobject.is_open:
                self.serialobject.open()
            commandtosend = self.ControllerKey+"GO"+position+"\r"
            while self.serialobject.in_waiting > 0:  # Cler Buffer
                self.serialobject.readline()
            self.serialobject.write(commandtosend.encode())
            time.sleep(0.2)
            if self.serialobject.in_waiting == 0:  # give extra time
                time.sleep(0.2)
            while self.serialobject.in_waiting > 0:  # Read in response
                if position in self.serialobject.readline().decode():
                    self.logger.info(self.name+" switched to "+position)
                    success = True
            if not success:
                self.logger.info("Error switching "+self.name)
                raise RuntimeError

    def currentposition(self):
        if not self.enabled:
            self.logger.info(self.name+" not set up, Query ignored")
            raise ValueError

        if not self.serialobject.is_open:
            self.serialobject.open()
        commandtosend = self.ControllerKey+"CP"+"\r"
        self.serialobject.write(commandtosend.encode())

        self.logger.info(self.name+" Position Query ")
        while self.serial_object.in_waiting > 0:
            self.logger.info(self.serial_object.readline().decode())

    def change_values(self, address, name):
        if self.name != name:
            self.logger.info("Changing Name: "+self.name+" to "+name)
            self.name = name

    def close(self):
        if self.serial_object.is_open:
            self.serial_object.close()
