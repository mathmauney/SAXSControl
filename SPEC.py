"""This module has a class for controlling SPEC remotely over sockets."""
import socket
import threading


class connection(socket.socket):
    """Connection to a SPEC socket server and allows for sending commands"""

    def __init__(self, *args, **kwargs):
        self.logger = kwargs.pop('logger')
        self.connected = False
        super(connection, self).__init__(socket.AF_INET, socket.SOCK_STREAM, **kwargs)

    def command(self, string):
        self.send(string.encode())
        self.logger.append('Sent: ' + string)

    def response(self, bytes=4096):
        if self.connected:
            response = self.recv(bytes).decode()
            self.logger.append(response)

    def connect(self, *args, **kwargs):
        super(connection, self).connect(*args, **kwargs)
        self.logger.append('Connected!')
        self.connected = True
        self.settimeout(0.1)
        self.thread = threading.Thread(target=self.check_response)
        self.thread.start()

    def check_response(self):
        try:
            self.response()
        except socket.timeout:
            pass
        self.logger.after(500, self.check_response)
