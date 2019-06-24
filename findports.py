import serial.tools.list_ports

ports = list(serial.tools.list_ports.comports())
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
