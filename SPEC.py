"""This module has a class for controlling SPEC remotely over sockets."""
import socket
import threading


class connection(socket.socket):
    """Connection to a SPEC socket server and allows for sending commands"""

    def __init__(self, *args, **kwargs):
        self.logger = kwargs.pop('logger')
        self.button = kwargs.pop('button')
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
        try:
            self.settimeout(2.0)
            super(connection, self).connect(*args, **kwargs)
            self.logger.append('Connected!')
            self.connected = True
            self.settimeout(0.1)
            self.thread = threading.Thread(target=self.check_response)
            self.thread.start()
            self.button.config(state="disabled")
        except socket.timeout:
            self.logger.append('Unable to connect (timeout)')
        except OSError:
            self.logger.append('Already connected')

    def check_response(self):
        while self.connected:
            try:
                self.response()
            except socket.timeout:
                pass
        self.thread.exit()
        self.button.config(state="normal")

    def stop(self):
        self.close()
        self.thread.exit()
