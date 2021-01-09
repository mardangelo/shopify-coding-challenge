import socket 
from .cipher import Cipher

class Communicator:
	"""Utility class for managing communication between client and server.
	
	Provides functions for communicating over the network given a socket which is
	connected between client and server. The most important methods are encrypt_and_send 
	and receive_and_decrypt. Note that these methods accept and produce bytes and that
	any strings should be encoded and decoded (e.g., as utf8) as necessary. 

	Attributes:
		HOST (str): Host name or IP address of the server. 
		PORT (int): Port open to receive connections on the server.
		ACK_SIZE (int): The size of an acknowledgement that a message has been received
						over the communication channel. 
						
		socket (Socket): Represents the connection between client and server.
		cipher (Cipher): Manages cryptographic operations.  
	"""

	HOST = '127.0.0.1'
	PORT = 65432

	ACK_SIZE = 3

	def __init__(self, socket=None):
		"""Initializes a Communicator object.
		
		If a socket object is not provided, then one is created. This should be used 
		by a client to create a connection to the server. A server should create the 
		socket (after accepting a connection from the client) and then pass it into 
		this communicator object for use. 
		
		Args:
			socket (Socket): A connection between a client and a server.  (default: {None})
		"""
		if socket == None:
			self.socket = self.connect_to_server()
		else:
			self.socket = socket
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

	#TODO: encrypt and send for images? or somehow detect that the message is str/image?
	def encrypt_and_send(self, message):
		"""Sends a message to the server.
		
		Encrypts the provided message and sends it over the socket.

		Args:
			message (bytes): Data to be sent.
		"""
		(ciphertext, tag, nonce) = self.cipher.encrypt(message)

		# The only length that needs to be computed is that of the ciphertext
		# as all other items (tag, nonce) are of fixed length. 
		ciphertext_length = len(ciphertext).to_bytes(Cipher.LENGTH_SIZE, byteorder='big')

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

		ack = self.socket.recv(self.ACK_SIZE)
		if not ack: 
			raise ConnectionError("Failed to receive acknowledgement")

	def receive_and_decrypt(self):
		"""Receives a message. 
		
		Receives a message over the socket and decrypts it. 
		
		Returns:
			bytes: Plaintext of the decrypted data.
		"""
		# Of the three pieces of information sent, only the ciphertext is variable
		# length so we determine its length before attempting to receive it 
		length = self.receive_data(Cipher.LENGTH_SIZE)
		ciphertext_length = int.from_bytes(length, byteorder='big')

		ciphertext = self.receive_data(ciphertext_length)
		tag = self.receive_data(Cipher.TAG_SIZE)
		nonce = self.receive_data(Cipher.NONCE_SIZE)

		data = self.cipher.decrypt(ciphertext, tag, nonce)

		return data

	def acknowledge_receipt(self):
		"""Sends an acknowledgement.
		
		Sends an ack signal to the other party. Note that this signal is intentionally
		not encrypted because it does not give away any extraneous information and 
		the overhead of encrypting these messages would not be worth it. 
		"""
		self.socket.sendall('ack'.encode('utf8'))

	def receive_data(self, length):
		"""Receives data.
		
		Receives data over the socket and sends an acknowledgement that the data has 
		been received. 
		
		Args:
			length: Length of the item being received. 
		
		Returns:
			bytes: Data received from the other party.
		
		Raises:
			ConnectionError: If data has not been received.
		"""
		data = self.socket.recv(length)

		if not data:
			raise ConnectionError("Failed to receive data")

		self.acknowledge_receipt()

		return data
