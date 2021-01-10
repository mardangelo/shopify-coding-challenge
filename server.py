#!/usr/bin/env python3

import socket
from util.communicator import Communicator
from util.command import Command
from util.status import Status
from db.database import Database
from lazyme.string import color_print

HOST = '127.0.0.1'
PORT = 65432

def main():
	# use IPv4 and TCP
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.bind((HOST, PORT))
		s.listen()

		(conn, addr) = s.accept()

		with conn:
			print("Connected to by ", addr)

			commander = ServerCommander(conn)

			while True:
				commander.receive_and_execute_command()
				

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
		# receive the image being sent (optionally the URL?)
		# receive the name of the image
		# save the image to disk in an organized fashion
		# compute the similarity vector using tensorflow
		# add a database entry (image path, name, size - computed, similarity vector, image format, price)
		# note: see if this can all be split up somehow? or if one table makes sense to store this information? 
		# 		like price can be in a separate table to denote discounts somehow?
		# 		
		print("Not implemented")

if __name__ == '__main__':
	main()