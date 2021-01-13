#!/usr/bin/env python3

import socket

from lazyme.string import color_print
from pathlib import Path

from db.database import Database

from util.communicator import Communicator
from util.enum.command import Command
from util.enum.status import Status

import util.similarity as tf

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
			Command.CREATE_USER.value: self.create_user, 
			Command.SEARCH_BY_IMAGE.value: self.search_by_image
		}

		self.db = Database()

	def receive_and_execute_command(self):
		"""Receives a command from the server and executes it.
		
		Receives and decrypts a command from the client and determines the correct 
		method to execute the command. 
		"""
		self.dispatch_command(self.communicator.receive_string())

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
			color_print("User must be logged in to perform operations on the repository", color='magenta')
		return not is_not_logged_in

	def create_user(self):
		"""Creates a user using the credentials provided by the client.
		
		Receives the username and password from the client and stores a salted 
		and hashed version of the password in the database if the username does 
		not already exist. If the user already exists in the database, FAILURE 
		is sent to the client, else a SUCCESS signal is sent. Once a user is 
		created they are automatically logged in.
		"""
		username = self.communicator.receive_string()
		password = self.communicator.receive_string()

		if self.db.create_user(username, password):
			self.username = username
			self.communicator.send_enum(Status.SUCCESS)
		else: 
			self.communicator.send_enum(Status.FAILURE)

	def login(self):
		"""Verifies the credentials of a user attempting to log in. 
		
		Receives the username and password from the client, then the password is 
		salted so that it can be compared to the salted copy in the database. (The 
		database should never store a plaintext password)
		"""
		username = self.communicator.receive_string()
		password = self.communicator.receive_string()

		if self.db.verify_user(username, password):
			self.username = username
			self.communicator.send_enum(Status.SUCCESS)
		else: 
			self.communicator.send_enum(Status.FAILURE)

	def add_image(self):
		"""Adds an image to the repository.
		
		Receives the encrypted image, filename, price, and quantity from the client
		and saves the image to disk. The database is populated with the remaining information.
		"""
		#TODO: is there a reason why the image wouldn't be added succesfully? Should image names be unique?
		# Or are similarity vectors the proper way to go?

		if not self.check_if_logged_in():
			return

		(image, filename) = self.receive_image()

		cost = receive_float()
		quantity = receive_int()
		tag_selection = self.communicator.receive_list()

		image_path = self.save_image_to_directory("images", image, filename)
		
		feature_tensor = tf.calculate_feature_vector(str(image_path))
		serialized_tensor = tf.serialize_feature_vector(feature_tensor)

		image_id = self.db.add_image(str(image_path), serialized_tensor, quantity, cost, self.username)
		
		if image_id is None:
			color_print("Image could not be added because it already exists", color='red')
			return

		self.db.add_tags(image_id, tag_selection)

	def search_by_image(self):
		"""Searches images (products) similar to the provided image.
		
		Receives an image from the client, computes a feature vector, and computes 
		the nearest neighbours of the image within the image repository. 
		"""
		if not self.check_if_logged_in():
			return

		(image, filename) = self.receive_image()

		# tensorflow wants to load images off disk, so let's store it there temporarily
		image_path = self.save_image_to_directory("temp", image, filename)
		
		feature_tensor = tf.calculate_feature_vector(str(image_path))

		# clean up the temporary file
		image_path.unlink()

		neighbours = tf.compute_nearest_neighbours(feature_tensor, self.db.get_feature_vectors())

		# first send the client the number of neighbours to expect, then send them individually
		self.communicator.send_int(len(neighbours))
		for neighbour in neighbours:
			self.send_image_to_client(neighbour)

	def send_image_to_client(self, image_id):
		(image_path, quantity, cost) = self.db.get_image_attributes(image_id)

		color_print(str((image_path, quantity, cost)), color='green')

		self.communicator.send_image(image_path)
		self.communicator.send_string(image_path.name)
		self.communicator.send_float(cost)
		self.communicator.send_int(quantity)

	def save_image_to_directory(self, directory, image, filename):
		"""Saves an image into a directory.
		
		Creates a directory if it does not exist and saves the provided image under 
		as the given filename into said directory.
		
		Args:
			directory (str): The path to the directory (or simply a name).
			image (Image): The image being saved to disk. 
			filename (str): The filename to be used to save the image.
		
		Returns:
			Path: path to the saved image file.
		"""
		# TODO: make this relative to main project directory if moved to another file?
		# TODO: should I be able to retrieve images and display them somehow (image.show())
		image_directory = Path(directory) 
		image_directory.mkdir(parents=True, exist_ok=True)
		image_path = image_directory / filename # append to path, uses '/' operator
		image.save(image_path) 

		return image_path

	def receive_image(self):
		"""Receives an image from the client.
		
		Receives the byte representation of the image from the client and decodes it. 
		Also receives the filename of the image. 

		Returns:
			Image: A PIL image.
			str: The filename of the image.
		"""
		image = self.communicator.receive_image()
		filename = self.communicator.receive_string()

		return (image, filename)

	def exit(self):
		"""Closes any open connections (e.g., database)."""
		self.db.close_connection()
		color_print("Client disconnected", 'blue')

if __name__ == '__main__':
	main()