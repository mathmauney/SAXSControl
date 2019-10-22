import sys
import glob
import serial


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    ports += ["01A377A5"]
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


if __name__ == '__main__':
    print(serial_ports())









# exit()
import serial.tools.list_ports

ports = list(serial.tools.list_ports.grep("USB"))
print(ports)
print(len(ports))
print("aaaaaaaaaaaaaaaaa")
for p in ports:
    print(p)
    print("device (", type(p.device), "): ", p.device)
    print("name (", type(p.name), "): ", p.name)
    print("description (", type(p.description), "): ", p.description)
    print("hwid (", type(p.hwid), "): ", p.hwid)
    print("vid (", type(p.vid), "): ", p.vid)
    print("pid (", type(p.pid), "): ", p.pid)
    print("serial_number (", type(p.serial_number), "): ", p.serial_number)
    print("location (", type(p.location), "): ", p.location)
    print("manufacturer (", type(p.manufacturer), "): ", p.manufacturer)
    print("product (", type(p.product), "): ", p.product)
    print("interface (", type(p.interface), "): ", p.interface)
    print()
