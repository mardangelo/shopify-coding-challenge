
import cmd2
from cmd2 import with_argparser
from util.communicator import Communicator
import getpass
import argparse
from util.enum.command import Command
from util.enum.status import Status
from util.enum.tags import Tags
from lazyme.string import color_print, color_str
from pathlib import Path
import matplotlib.pyplot as plt

#TODO: rename util to shared?
#TODO: create a demo database so they don't have to upload files with prices and tags, etc.

class ClientPrompt(cmd2.Cmd):
	"""Interface for user to interact with image repository.
	
	Allows a user to manage the image repository. Use `help` to list
	available commands. 
	
	Attributes:
		prompt (str): Command prompt displayed to the user. 
		intro (str): Welcome message displayed when the application is launched.
		user (str): Initially an empty string until a user logs in, upon which 
					it stores the username of the logged in user. 
			  		Used as a proxy for identifying whether a user is logged in. 
	"""

	prompt =  color_str("image-repo> ", color='green')
	intro =  color_str("Welcome to Image Repository. Type ? to list commands", color='blue')
	goodbye =  color_str("Thank you for using Image Repository. Goodbye.", color='blue')

	def __init__(self):
		self.user = None 
		self.communicator = Communicator()
		super().__init__()

	# TODO: flesh out this doc string
	def check_if_logged_in(self):
		"""Checks if there is a user that has had their credentials verified by the server."""
		is_not_logged_in = (self.user is None)
		if is_not_logged_in:
			color_print("User must be logged in for this command to function", color='magenta')
		return not is_not_logged_in

	def do_create_user(self, username):
		"""Creates a user with the given username.
		
		Prompts the user for the password to be associated with the username. 
		The username and password are encrypted and sent to the server where 
		they are stored in the database. Note: the password is not stored as 
		plaintext in that database, a salted hashed version is stored instead. 
		
		Args:
			username (str): Username of the user to be created. 
		"""
		if username == "":
			color_print("Must provide a username", color='red')
			return

		color_print("Attempting to create user %s" % username, 'blue')
		password = getpass.getpass()

		self.send_command(Command.CREATE_USER)

		self.communicator.send_string(username)
		self.communicator.send_string(password)

		result = self.communicator.receive_enum(Status)

		if result == Status.SUCCESS:
			color_print("Successfully created user %s" % username, color='blue')
		else: 
			color_print("Error: User already exists", color='red')

	def do_login(self, username):
		"""Logs user in as given username.
		
		Prompts user for the password associated with username. If the 
		password is incorrect the command fails. Most commands for 
		the repository don't function unless the user is logged in. 
		
		Arguments:
			username (str): Username to log in with.
		""" 
		if username == "":
			color_print("Must provide a username", color='red')
			return

		color_print("Attempting to log in as %s" % username, color='blue')

		password = getpass.getpass()

		self.send_command(Command.LOGIN)
		
		if self.verify_password(username, password) == Status.SUCCESS:
			self.user = username
			color_print("Successfully logged in as %s" % username, color='blue')
		else:
			# Note: failure could be owed to two reasons: (1) incorrect password, 
			# (2) user doesn't exist. It is intentional that the status of a user
			# not be revealed - as is standard when usernames can be global
			# identifiers such as emails, etc. It would be trivial to enhance
			# the Status codes to specifically specify INCORRECT_PASSWORD and
			# USER_DOES_NOT_EXIST should confidentiality of existing users not
			# be required. 
			color_print("Error: Failed to log in as %s" % username, color='red')

	complete_add_image = cmd2.Cmd.path_complete

	argparser_add_image = argparse.ArgumentParser()
	argparser_add_image.add_argument('path', type=str, help='path to an image file')
	argparser_add_image.add_argument('price', type=float, help='price of the image (product)')
	argparser_add_image.add_argument('quantity', type=int, help='number of image (product) to stock')

	@with_argparser(argparser_add_image)
	def do_add_image(self, opts):
		"""Adds an image (product) to Image Repository.
		
		Uploads the image specified by path to the server along with the price.
		
		Args: (within argument parser opts)
			path (str): Path to an image file.
			price (float): Cost of the image (product).
			quantity (int): Quantity of the image (product) in the inventory.
		"""
		if not self.check_if_logged_in():
			return 

		Tags.display_tags_for_selection()
		selection_raw = input(color_str("Enter the number(s) of the relevant tag(s): ", color='green'))
		selection = [int(s) for s in selection_raw.split(',') if s.isdigit()]
		
		self.send_command(Command.ADD_IMAGE)

		image_path = Path(opts.path)
		self.communicator.send_image(image_path)
		self.communicator.send_string(image_path.name)

		self.communicator.send_float(opts.price)
		self.communicator.send_int(opts.quantity)
		self.communicator.send_list(selection)

	#TODO: search function that can take (a) an image, (b) a string (filename?), (c) a tag?
	#	   should the tags be displayed and chosen? should multiple tags be possible?
	#	   search_by_image, search_by_image_name, search_by_tag?
	
	complete_search_by_image = cmd2.Cmd.path_complete

	argparser_search_by_image = argparse.ArgumentParser()
	argparser_search_by_image.add_argument('path', type=str, help='path to an image file')

	@with_argparser(argparser_search_by_image)
	def do_search_by_image(self, opts):
		"""Find images (products) similar to the provided image.
		
		Uploads the given image to the server and performs a similarity computation
		on the other images in the database using nearest neighbours. 
		
		Args: (within argument parser opts)
			path (str): Path to an image file.
		"""
		if not self.check_if_logged_in():
			return 

		self.send_command(Command.SEARCH_BY_IMAGE)

		image_path = Path(opts.path)
		self.communicator.send_image(image_path)
		self.communicator.send_string(image_path.name)

		num_neighbours = self.communicator.receive_int()
		neighbours = list()

		for _ in range(num_neighbours):
			image = self.communicator.receive_image()
			filename = self.communicator.receive_string()
			cost = self.communicator.receive_float()
			quantity = self.communicator.receive_int()

			neighbours.append((image, filename, cost, quantity))

		self.display_all_images(neighbours)

	def display_all_images(self, images):
		"""Displays the provided images.
		
		Creates a figure in pyplot consisting of a row for each image. The image is displayed 
		in the left column and image information is displayed on the right. 
		
		Args:
			images (list(tuple)): A list where each element is a tuple (image data, filename, 
								  quantity, cost).
		"""
		figure = plt.figure()

		columns = 2
		rows = len(images)

		j = 1

		for i in range(rows):
			(image, filename, cost, quantity) = images[i]

			figure.add_subplot(rows, columns, j)
			plt.axis('off')
			plt.imshow(image)

			ax = figure.add_subplot(rows, columns, j+1)
			image_data = "[%s]" % filename
			ax.text(0.5, 0.75, image_data, size=12, ha='center', va='center', wrap=True)
			image_data = "Stock: %d" % quantity
			ax.text(0.5, 0.5, image_data, size=12, ha='center', va='center', wrap=True)
			image_data = "Price: %.2f" % cost
			ax.text(0.5, 0.25, image_data, size=12, ha='center', va='center', wrap=True)
			plt.axis('off')

			j += 2

		plt.axis('off')
		plt.show()

	def do_view_cart(self, args):
		"""Display contents of cart.
		
		Lists each item in the shopping cart along with quantity and price. 
		Total is also listed. 
		""" 

		self.check_if_logged_in()
		print("To be implemented")

	def do_exit(self, args):
		"""Exits the image repository.
		
		Exits the repository and closes the connection to the server. 
		""" 
		print(self.goodbye)

		self.communicator.shutdown()

		raise SystemExit

	def send_command(self, command):
		"""Sends a command to the server.
		
		Encodes the command as a string then encrypts it and sends it to 
		the server. 
		
		Args:
			command (Command): The command representing the operation to be performed. 
		"""
		self.communicator.send_enum(command)

	def verify_password(self, username, password):
		"""Verifies the username and password with the server. 
		
		Sends encrypted versions of the username and password to the server and 
		receives a result in return stating whether the combination was valid. 
		
		Args:
			username: Username of the user attempting to log in. 
			password: Password provided by the user attempting to log in. 
		
		Returns:
			Status: Either SUCCESS or FAILURE depending on whether the username
					password combination was valid. 
		"""
		self.communicator.send_string(username)
		self.communicator.send_string(password)

		return self.communicator.receive_enum(Status)

if __name__ == '__main__':
	prompt = ClientPrompt()
	prompt.cmdloop()