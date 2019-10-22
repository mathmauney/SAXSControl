"""This module has a class for controlling SPEC remotely over sockets."""
import socket
import threading


class connection(socket.socket):
    """Connection to a SPEC socket server and allows for sending commands"""

    def __init__(self, *args, **kwargs):
        self.logger = kwargs.pop('logger')
        self.button = kwargs.pop('button')
        self.connected = False
        self.run_flag = threading.Event()
        self.run_flag.clear()
        super(connection, self).__init__(socket.AF_INET, socket.SOCK_STREAM, **kwargs)
        self.settimeout(2.0)

    def command(self, string):
        if string != '':
            try:
                self.send(string.encode())
                self.logger.append('Sent: ' + string)
            except socket.timeout:
                self.logger.append('Unable to send command')

    def response(self, bytes=4096):
        response = self.recv(bytes).decode()
        self.logger.append(response)

    def connect(self, *args, **kwargs):
        try:
            super(connection, self).connect(*args, **kwargs)
            self.logger.append('Connected!')
            self.settimeout(0.1)
            self.thread = threading.Thread(target=self.check_response)
            self.thread.start()
            self.button.config(text="Reconnect")

        except socket.timeout:
            self.logger.append('Unable to connect (timeout)')
        except OSError:
            self.logger.append('Already connected')

    def check_response(self):
        self.run_flag.set()
        while self.run_flag.is_set():
            try:
                self.response()
            except socket.timeout:
                pass

    def stop(self):
        if self.run_flag.is_set():
            self.run_flag.clear()
