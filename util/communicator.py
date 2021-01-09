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
			Socket: Communication channel between client and server. 
		"""
		server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		server_socket.connect((self.HOST, self.PORT))

		return server_socket

	def encrypt_and_send(self, message):
		"""Sends a message to the server.
		
		Encrypts the provided message and sends it over the socket.

		Args:
			message (bytes): Data to be sent.
		"""
		(ciphertext, tag, nonce) = self.cipher.encrypt(message)

		# The only length that needs to be computed is that of the ciphertext
		# as all other items (tag, nonce) are of fixed length. 
		ciphertext_length = len(ciphertext).to_bytes(32, byteorder='big')

		self.send_data(ciphertext_length)
		self.send_data(ciphertext)
		self.send_data(tag)
		self.send_data(nonce)

	def send_data(self, data):
		"""Sends data using the socket.
		
		Sends data to the recipient and waits to for an acknowledgement of receipt.
		
		Args:
			data (bytes): Data to be sent.

		Raises:
      		ConnectionError: If the acknowledgement fails to be received.
		"""

		self.socket.sendall(data)

		ack = self.socket.recv(3)
		if not ack: 
			raise ConnectionError("Failed to receive acknowledgement")

if __name__ == '__main__':
	communicator = Communicator()
	communicator.encrypt_and_send("test".encode('utf8'))
