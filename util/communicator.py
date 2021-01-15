import socket 
from enum import Enum

from pathlib import Path
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import struct

from lazyme.string import color_print

from .cipher import Cipher
from .enum.signal import Signal

DEBUG = False

class Code(Enum):
	"""Short codes used for communication. 
	
	Fixed length codes that are intended to be sent unencrypted between the client and 
	the server. They are meant to denote simple signals that are of no consequence if 
	an attacker reads them.
	
	Attributes:
		ACKNOWLEDGE (str): Acknowledge the receipt of some data.
		ERROR (str): Error receiving the data, sending party should reattempt. 
	"""

	ACKNOWLEDGE = 'ack'
	ERROR = 'err'

	@classmethod
	def get_size(cls):
		return 3

class Communicator:
	"""Utility class for managing communication between client and server.
	
	Provides functions for communicating over the network given a socket which is
	connected between client and server. The most important methods are encrypt_and_send 
	and receive_and_decrypt. Note that these methods accept and produce bytes and that
	any strings should be encoded and decoded (e.g., as utf8) as necessary. 

	Attributes:
		HOST (str): Host name or IP address of the server. 
		PORT (int): Port open to receive connections on the server.
						
		socket (Socket): Represents the connection between client and server.
		cipher (Cipher): Manages cryptographic operations.  
	"""

	HOST = '127.0.0.1'
	PORT = 65432

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

	def send_int(self, integer):
		"""Sends an integer over the connection.
		
		Encodes the integer into a 4 byte representation, encrypts it, 
		and send it to the other party. 

		Note: Integers are treated as being fixed width in order to simplify 
			  network communication, however, integers in python aren't actually
			  limited in size so loss of precision may occur in odd cases.
		
		Args:
			integer (int): The number to be sent.
		"""
		self.encrypt_and_send(integer.to_bytes(4, byteorder='big'))

	def receive_int(self):
		"""Receives an integer over the connection.
		
		Receives and decrypts the integer bytes, then converts the bytes back into 
		an integer.
		
		Returns:
			int: The integer sent by the other party.
		"""
		return int.from_bytes(self.receive_and_decrypt(), byteorder='big')

	def send_float(self, floating_point_number):
		"""Sends a floating point number over the connection.
		
		Encodes the floating point number into bytes, encrypts it,
		and sends it to the other party. 
		
		Args:
			floating_point_number (float): The number to be sent.
		"""
		self.encrypt_and_send(struct.pack('>f', floating_point_number))

	def receive_float(self):
		"""Receives a floating point number over the connection.
		
		Receives and decrypts the float bytes, then converts the bytes back into 
		the float representation.
		
		Returns:
			float: The float sent by the other party.
		"""
		return struct.unpack('>f', self.receive_and_decrypt())[0]

	def send_string(self, string):
		"""Sends a string over the connection.
		
		Encodes the string into bytes using utf8, encrypts it, and sends it to the 
		other party.
		
		Args:
			string (str): The string to be sent.
		"""
		self.encrypt_and_send(string.encode('utf8'))

	def receive_string(self):
		"""Receives a string over the connection.
		
		Receives and decrypts the string bytes, then decodes them using utf8.
		
		Returns:
			string: The string sent by the other party.
		"""
		return self.receive_and_decrypt().decode('utf8')

	def send_image(self, image_path):
		"""Sends an image over the connection.
		
		Encodes the image into bytes using PIL and BytesIO, encrypts the data, and
		sends it to the other party.
		
		Args:
			image_path (Path): The path to the image on disk.
		"""
		try:
			with BytesIO() as output_image:
				with Image.open(image_path) as source_image:
					# jpeg can have two extensions, but only one is valid for PIL (jpeg)
					extension = image_path.suffix.lstrip('.')
					source_image.save(output_image, 'jpeg' if extension.lower() == 'jpg' else extension)

				self.encrypt_and_send(output_image.getvalue())
		except FileNotFoundError:
			color_print("Error: Could not locate image at given path", color='red')
		except UnidentifiedImageError:
			color_print("Error: File could not be opened as an image", color='red')

	def receive_image(self):
		"""Receives an image over the connection.
		
		Receives and decrypts the image bytes, then loads the bytes into a PIL Image.
		
		Returns:
			Image: The image sent by the other party.
		"""
		image_bytes = BytesIO(self.receive_and_decrypt())
		image_bytes.seek(0) # return file cursor to beginning of file

		return Image.open(image_bytes)

	def send_list(self, list_variable):
		"""Sends a list over the connection.
		
		Encodes the list into bytes, encrypts it, and sends it to the other party.
		
		Args:
			list_variable (list): The list to be sent.
		"""
		if not list_variable:
			self.send_enum(Signal.EMPTY)
			return

		self.send_enum(Signal.POPULATED)
		self.encrypt_and_send(bytes(list_variable))

	def receive_list(self):
		"""Receives a list over the connection.
		
		Receives and decrypts the list bytes, then initializes a list using the bytes.
		
		Returns:
			list: The list sent by the other party.
		"""
		if self.receive_enum(Signal) == Signal.EMPTY:
			return list()

		return list(self.receive_and_decrypt())

	def send_enum(self, enumerable):
		"""Sends an enumerable over the connection.
		
		Encodes the string representation of the enumerable into bytes, encrypts it, 
		and sends it to the other party.
		
		Args:
			enumerable (Enum): The enumerable to be sent.
		"""
		self.send_string(enumerable.value)
	
	def receive_enum(self, enum_type):
		"""Receives an enumerable over the connection.
		
		Receives and decrypts the enumerable string bytes, then decodes the string using utf8
		and initializes an enumerable using the given type and the decrypted value.
		
		Args:
			enum_type (Enum): An enumerable class that will be used to create an instance given the value.

		Returns:
			Enum<enum_type>: The enumerable sent by the other party.
		"""
		return enum_type(self.receive_string())

	def receive_code(self):
		"""Receive a short code.
		
		Receives a string signal and converts it into a Code enum. 
		
		Returns:
			Code: The code that was received as an enum. 
		"""
		code = self.socket.recv(Code.get_size())

		if not code:
			raise ConnectionError("Failed to receive a code")

		return Code(code.decode('utf8'))

	def send_code(self, code):
		"""Sends a short code.
		
		Sends a signal to the other party. The signal is provided as a Code enum 
		which is sent using its string value. Note that this signal is intentionally
		not encrypted because it does not give away any extraneous information and 
		the overhead of encrypting these messages would not be worth it. 

		Args:
			code (Code): The code to be sent. 
		"""
		self.socket.sendall(code.value.encode('utf8'))

	def encrypt_and_send(self, message):
		"""Sends a message to the server.
		
		Encrypts the provided message and sends it over the socket.

		Args:
			message (bytes): Data to be sent.
		"""
		if DEBUG:
			color_print("Sending: %.30s" % message, color='red')
			
		(ciphertext, tag, nonce) = self.cipher.encrypt(message)

		# The only length that needs to be computed is that of the ciphertext
		# as all other items (tag, nonce) are of fixed length. 
		ciphertext_length = len(ciphertext).to_bytes(Cipher.LENGTH_SIZE, byteorder='big')

		code = Code.ERROR

		while code != Code.ACKNOWLEDGE: 
			self.send_data(ciphertext_length)
			self.send_data(ciphertext)
			self.send_data(tag)
			self.send_data(nonce)

			code = self.receive_code()

			if not code: 
				raise ConnectionError("Failed to receive a code")

			elif code == Code.ERROR: 
				color_print("Received error code after transmission, resending", color='red')
				continue

	def receive_and_decrypt(self):
		"""Receives a message. 
		
		Receives a message over the socket and decrypts it. 
		
		Returns:
			bytes: Plaintext of the decrypted data.
		"""
		data = None
		while not data:
			try:
				# Of the three pieces of information sent, only the ciphertext is variable
				# length so we determine its length before attempting to receive it 
				length = self.receive_data(Cipher.LENGTH_SIZE)
				ciphertext_length = int.from_bytes(length, byteorder='big')

				ciphertext = self.receive_data(ciphertext_length)
				tag = self.receive_data(Cipher.TAG_SIZE)
				nonce = self.receive_data(Cipher.NONCE_SIZE)

				data = self.cipher.decrypt(ciphertext, tag, nonce)
				self.send_code(Code.ACKNOWLEDGE)
			except ValueError:
				color_print("Error receiving item, sender should retransmit", color='red')
				self.send_code(Code.ERROR)

		if DEBUG:
			color_print("Received: %.30s" % data, color='red')

		return data

	def send_data(self, data):
		"""Sends data using the socket.
		
		Sends data to the recipient and waits to for an acknowledgement of receipt.
		
		Args:
			data (bytes): Data to be sent.

		Raises:
      		ConnectionError: If the acknowledgement fails to be received.
		"""
		self.socket.sendall(data)

		code = self.socket.recv(Code.get_size())

		if not code: 
			raise ConnectionError("Failed to receive acknowledgement")

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
		data = bytearray()

		while len(data) < length:
			data.extend(self.socket.recv(length))

		if not data:
			raise ConnectionError("Failed to receive data")

		self.send_code(Code.ACKNOWLEDGE)

		return data

	def shutdown(self):
		"""Severs the connection between client and server.
		
		Blocks communication in both directions (send and receive) for client/server. 
		Subsequently, destroys the socket. 
		"""
		try:
			self.socket.shutdown(socket.SHUT_RDWR)
		except OSError:
			# the socket was already shutdown by the other party
			pass

		self.socket.close()
