import socket 
import sys
from cipher import Cipher

class Communicator:
	"""Utility class for managing communication between client and server.
	
	[description]

	Attributes:
		HOST (str): Host name or IP address of the server. 
		PORT (int): Port open to receive connections on the server.
		socket (Socket): Socket representing the connection between client and server.
	"""

	HOST = '127.0.0.1'
	PORT = 65432

	def __init__(self):
		self.socket = self.connect_to_server()
		self.cipher = Cipher()

	def connect_to_server(self):
		"""Connects to the server.
		
		Creates a connection to the server at (HOST, PORT) using IPv4 and TCP. 

		Returns:
			Socket: Plaintext of the decrypted data.
		"""
		server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		server_socket.connect((self.HOST, self.PORT))

		return server_socket

	def send_to_server(self, message):
		"""Sends a message to the server.
		
		Encrypts the provided message and sends it to the connected server.

		Args:
			message (bytes): Data to be sent.
		"""

		(ciphertext, tag, nonce) = self.cipher.encrypt(message)

		ciphertext_length = len(ciphertext).to_bytes(32, byteorder='big')

		self.socket.sendall(ciphertext_length)

		ack = self.socket.recv(28)
		if not ack: # TODO: make this raise an exception?
			print("Failed to receive acknowledgement")
			return

		self.socket.sendall(ciphertext)

		ack = self.socket.recv(3)
		if not ack: # TODO: make this raise an exception?
			print("Failed to receive acknowledgement")
			return

		self.socket.sendall(tag)

		ack = self.socket.recv(3)
		if not ack: # TODO: make this raise an exception?
			print("Failed to receive acknowledgement")
			return

		self.socket.sendall(nonce)

		ack = self.socket.recv(3)
		if not ack: # TODO: make this raise an exception?
			print("Failed to receive acknowledgement")
			return


if __name__ == '__main__':
	communicator = Communicator()
	communicator.send_to_server("test".encode('utf8'))
