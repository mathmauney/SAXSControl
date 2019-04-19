"""This module has a class for controlling SPEC remotely over sockets."""
import socket


class connection(socket.socket):
    """Connection to a SPEC socket server and allows for sending commands"""

    def __init__(self, *args, **kwargs):
        super(connection, self).__init__(socket.AF_INET, socket.SOCK_STREAM, **kwargs)

    def command(self, string):
        self.send(string.encode())

    def response(self, bytes=4096):
        response = self.recv(bytes).decode()
        return response
