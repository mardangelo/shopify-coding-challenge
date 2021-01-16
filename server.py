#!/usr/bin/env python3

import socket

from lazyme.string import color_print
from pathlib import Path

from PIL import UnidentifiedImageError

from db.database import Database

from util.batch_transfer import BatchTransfer
from util.communicator import Communicator
from util.enum.command import Command
from util.enum.signal import Signal

import util.similarity as tf

HOST = '127.0.0.1'
PORT = 65432

def main():
	# use IPv4 and TCP
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.bind((HOST, PORT))

		color_print("Listening for connections...", color='green')

		while True:
			s.listen()

			(conn, addr) = s.accept()

			with conn:
				color_print("Client %s connected" % str(addr), color='blue')

				commander = ServerCommander(conn)

				while True:
					try: 
						commander.receive_and_execute_command()
					except ConnectionError:
						commander.close_connection()
						break
					except ClientDisconnectException:
						break

				color_print("Client %s disconnected" % str(addr), color='blue')

class ClientDisconnectException(Exception):
	"""Exception for when a client has disconnected."""
	pass						

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
		self.batch_transfer = BatchTransfer(self.communicator)

		self.commands = {
			Command.CREATE_USER : self.create_user,
			Command.LOGIN : self.login, 
			Command.ADD_IMAGE : self.add_image,
			Command.UPDATE_IMAGE : self.update_image, 
			Command.DELETE_IMAGE : self.delete_image,
			Command.SEARCH_BY_IMAGE : self.search_by_image, 
			Command.BROWSE_BY_TAG : self.browse_by_tag, 
			Command.EXIT : self.close_connection
		}

		self.db = Database()

	def receive_and_execute_command(self):
		"""Receives a command from the server and executes it.
		
		Receives and decrypts a command from the client and determines the correct 
		method to execute the command. 
		"""
		try:
			command = self.communicator.receive_enum(Command)
			color_print("Received command: %s" % command.value, color='green')
			self.dispatch_command(command)
		except (ValueError, UnicodeDecodeError, OverflowError, MemoryError, UnidentifiedImageError): 
			# This often happens if the user kills the client in the middle of a protocol
			# and the server has some state and expects signals/data instead of EXIT command.
			# If the communication gets "misaligned" because of an abort a string may be 
			# interpreted as an integer and overflow (for example).
			color_print("Error: Unexpected data received", color='red')
			raise ClientDisconnectException

	def dispatch_command(self, command):
		"""Dispatches a command to the appropriate method. 
		
		Using the command, looks up the method that should be run in order to 
		execute the operation the client has requested. The string representation 
		of each command is mapped to a function in the commands dictionary. 
		
		Args:
			command (str): The string representation of the issued command.
		"""
		self.commands[command]()

	def check_if_logged_in(self):
		"""Checks if the client has logged in as a user.
		
		When a user logs in, their username is stored and used for quick and simple checks 
		that the client has been authenticated. 
		
		Returns:
			bool: True if a user has logged in previously, False otherwise.
		"""
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
			self.communicator.send_enum(Signal.SUCCESS)
		else: 
			self.communicator.send_enum(Signal.FAILURE)

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
			self.communicator.send_enum(Signal.SUCCESS)
		else: 
			self.communicator.send_enum(Signal.FAILURE)

	def add_image(self):
		"""Adds an image to the repository.
		
		Receives the encrypted image, filename, price, and quantity from the client
		and saves the image to disk. The database is populated with the remaining information.
		
		Future Work: Save the encrypted images to disk using random filenames. The code for 
					 encrypting an decrypting is here, and the image is actually received 
					 encrypted. Just need to decrypt after reading from disk. Latency will
					 increase a bit, espeically when serving large numbers of images.
		"""
		if not self.check_if_logged_in():
			return

		(image, filename) = self.receive_image()

		cost = self.communicator.receive_float()
		quantity = self.communicator.receive_int()
		tag_selection = self.communicator.receive_list()

		if Path("images/%s" % filename).exists():
			color_print("Error: Image %s could not be added because a file with that name already exists" % filename, color='red')
			self.communicator.send_enum(Signal.FAILURE)
			return

		image_path = self.save_image_to_directory("images", image, filename)
		
		feature_tensor = tf.calculate_feature_vector(str(image_path))
		serialized_tensor = tf.serialize_feature_vector(feature_tensor)

		image_id = self.db.add_image(str(image_path), serialized_tensor, quantity, cost, self.username)
		
		if image_id is None:
			color_print("Error: Image %s could not be added because it already exists" % filename, color='red')
			self.communicator.send_enum(Signal.FAILURE)
			return

		self.db.add_tags(image_id, tag_selection)

		self.communicator.send_enum(Signal.SUCCESS)
		self.communicator.send_int(image_id)

	def update_image(self):
		"""Updates an image in the repository.
		
		Receives the image identifier, price, and quantity from the client and updates the image information 
		if the image exists in the database. 
		"""
		if not self.check_if_logged_in():
			return

		image_id = self.communicator.receive_int()
		cost = self.communicator.receive_float()
		quantity = self.communicator.receive_int()

		if not self.db.update_image(image_id, cost, quantity):
			color_print("Error: the requested image does not exist in the database", color='red')
			self.communicator.send_enum(Signal.FAILURE)
			return

		color_print("Image [%d] updated with ($%.2f, %d)" % (image_id, cost, quantity), color='blue')
		self.communicator.send_enum(Signal.SUCCESS)

	def delete_image(self):
		"""Deletes an image in the repository.
		
		Receives the image identifier and checks if the image exists in the database, if it exists 
		the image path is pulled and used to delete the file on disk (in addition to the information 
		in the database). 
		"""
		if not self.check_if_logged_in():
			return

		image_id = self.communicator.receive_int()

		image_path = self.db.delete_image(image_id)

		if not image_path:
			color_print("Error: the requested image does not exist in the database", color='red')
			self.communicator.send_enum(Signal.FAILURE)
			return

		# delete the image on disk
		Path(image_path).unlink()

		color_print("Image [%d] deleted" % image_id, color='blue')
		self.communicator.send_enum(Signal.SUCCESS)

	def search_by_image(self):
		"""Searches images (products) similar to the provided image.
		
		Receives an image from the client, computes a feature vector, and computes 
		the nearest neighbours of the image within the image repository. The similar 
		images are sent in order of most similar to least in batches to the client. 
		"""
		if not self.check_if_logged_in():
			return

		(image, filename) = self.receive_image()

		# tensorflow wants to load images off disk, so let's store it there temporarily
		image_path = self.save_image_to_directory("temp", image, filename)
		
		feature_tensor = tf.calculate_feature_vector(str(image_path))

		# clean up the temporary file
		image_path.unlink()

		neighbour_ids = tf.compute_nearest_neighbours(feature_tensor, self.db.get_feature_vectors())

		if len(neighbour_ids) == 0:
			color_print("No images similar to the provided image were found", color='magenta')
			self.communicator.send_enum(Signal.NO_RESULTS)

		self.batch_transfer.send_images_in_batches(len(neighbour_ids), self.db.get_image_attributes, [neighbour_ids])

	def browse_by_tag(self):
		"""Browses images (products) filtered by given tags.
		
		Receives tag identifiers from the client and queries the database for images 
		matching all of the tags. If no tags are provided, all images are considered to 
		be matches. Matching images are sent in batches to the client. 
		"""
		if not self.check_if_logged_in():
			return

		tags = self.communicator.receive_list()

		images_to_be_displayed = self.db.count_images_with_tags(tags)

		if images_to_be_displayed == 0:
			color_print("No images found matching the given tags", color='magenta')
			self.communicator.send_enum(Signal.NO_RESULTS)
			return

		self.batch_transfer.send_images_in_batches(images_to_be_displayed, self.db.retrieve_images_with_tags, [tags])

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

	def close_connection(self):
		"""Closes any open connections (e.g., database)."""
		self.db.close_connection()
		self.communicator.shutdown()
		raise ClientDisconnectException

if __name__ == '__main__':
	main()