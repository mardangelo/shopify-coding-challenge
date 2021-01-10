#!/usr/bin/env python3

import socket
from util.communicator import Communicator
from util.command import Command
from util.status import Status
from db.database import Database
from lazyme.string import color_print
from PIL import Image
from io import BytesIO
import struct
from pathlib import Path

HOST = '127.0.0.1'
PORT = 65432

def main():
	# use IPv4 and TCP
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.bind((HOST, PORT))

		while True:
			s.listen()

			(conn, addr) = s.accept()

			with conn:
				color_print("Connected to by %s" % str(addr), 'blue')

				commander = ServerCommander(conn)

				while True:
					try: 
						commander.receive_and_execute_command()
					except ConnectionError:
						commander.exit()
						break

				

class ServerCommander():
	"""Receives commands from the client and processes them. 
	
	Receives and decrypts command from the client and dispatches their execution to the 
	appropriate method.
	
	Attributes:
		username (str): The name of the currently logged in user.
		commands (dict{str -> func}): Mapping of string command to function. 
		communicator (Communicator): Manages encrypted communciation between client and server. 
		db (Database): Manages operations on the database.
	"""

	def __init__(self, connection):
		"""Initalizes server command processor.
		
		Stores the connection between client and server to continue the communication 
		depending on the command issued. 
		
		Args:
			connection (Socket): The established connection between client and server. 
		"""
		self.username = None

		self.communicator = Communicator(connection)

		self.commands = {
			Command.LOGIN.value : self.login, 
			Command.ADD_IMAGE.value : self.add_image,
			Command.CREATE_USER.value: self.create_user
		}

		self.db = Database()

	def receive_and_execute_command(self):
		"""Receives a command from the server and executes it.
		
		Receives and decrypts a command from the client and determines the correct 
		method to execute the command. 
		"""
		command = self.communicator.receive_and_decrypt()
		self.dispatch_command(command.decode('utf8'))

	def dispatch_command(self, command):
		"""Dispatches a command to the appropriate method. 
		
		Using the command, looks up the method that should be run in order to 
		execute the operation the client has requested. The string representation 
		of each command is mapped to a function in the commands dictionary. 
		
		Args:
			command (str): The string representation of the issued command.
		"""
		self.commands[command]()

	# TODO: flesh out this doc string
	def check_if_logged_in(self):
		"""Checks if there is a user that has logged in and can perform operations."""
		is_not_logged_in = (self.username is None)
		if is_not_logged_in:
			color_print("User must be logged in to perform operations on the repository", color='orange')
		return not is_not_logged_in

	def create_user(self):
		"""Creates a user using the credentials provided by the client.
		
		Receives the username and password from the client and stores a salted 
		and hashed version of the password in the database if the username does 
		not already exist. If the user already exists in the database, FAILURE 
		is sent to the client, else a SUCCESS signal is sent. Once a user is 
		created they are automatically logged in.
		"""
		username = self.communicator.receive_and_decrypt().decode('utf8')
		password = self.communicator.receive_and_decrypt().decode('utf8')

		if self.db.create_user(username, password):
			self.username = username
			self.communicator.encrypt_and_send(Status.SUCCESS.value.encode('utf8'))
		else: 
			self.communicator.encrypt_and_send(Status.FAILURE.value.encode('utf8'))

	def login(self):
		"""Verifies the credentials of a user attempting to log in. 
		
		Receives the username and password from the client, then the password is 
		salted so that it can be compared to the salted copy in the database. (The 
		database should never store a plaintext password)
		"""
		username = self.communicator.receive_and_decrypt().decode('utf8')
		password = self.communicator.receive_and_decrypt().decode('utf8')

		if self.db.verify_user(username, password):
			self.username = username
			self.communicator.encrypt_and_send(Status.SUCCESS.value.encode('utf8'))
		else: 
			self.communicator.encrypt_and_send(Status.FAILURE.value.encode('utf8'))

	def add_image(self):
		"""Adds an image to the repository.
		
		Receives the encrypted image, filename, price, and quantity from the client
		and saves the image to disk. The database is populated with the remaining information.
		"""

		#TODO: is there a reason why the image wouldn't be added succesfully? Should image names be unique?
		# Or are similarity vectors the proper way to go?
		
		#TODO: compute the similarity vector using tensorflow
		#TODO: add a database entry (image path, name, size - computed, similarity vector, image format, price)
		# note: see if this can all be split up somehow? or if one table makes sense to store this information? 
		# 		like price can be in a separate table to denote discounts somehow?

		# if not self.check_if_logged_in():
		# 	return

		image_bytes = BytesIO(self.communicator.receive_and_decrypt())
		image_bytes.seek(0) # return file cursor to beginning of file
		image = Image.open(image_bytes)
		filename = self.communicator.receive_and_decrypt().decode('utf8')
		price = struct.unpack('>f', self.communicator.receive_and_decrypt())
		quantity = int.from_bytes(self.communicator.receive_and_decrypt(), byteorder='big')

		# TODO: make this relative to main project directory if moved to another file?
		# TODO: should I be able to retrieve images and display them somehow (image.show())
		image_directory = Path("images") 
		image_directory.mkdir(parents=True, exist_ok=True)

		# sort of weird syntax for appending to a path object, uses '/' operator
		image.save(image_directory / filename)

	def exit(self):
		"""Closes any open connections (e.g., database)."""
		self.db.close_connection()
		color_print("Client disconnected", 'blue')

if __name__ == '__main__':
	main()