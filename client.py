
import cmd2
from cmd2 import with_argparser
from util.communicator import Communicator
import getpass
import argparse
from util.enum.command import Command
from util.enum.signal import Signal
from util.enum.tags import Tags
from lazyme.string import color_print, color_str
from pathlib import Path
import matplotlib.pyplot as plt

#TODO: rename util to shared?
#TODO: create a demo database so they don't have to upload files with prices and tags, etc.
#	   maybe do a database of photos of mythological figures? or just from hades? and price
#	   them based on how much I like them...

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
		plt.switch_backend('Qt5Agg') #TODO: move plotting stuff to another file
		super().__init__()

	def check_if_logged_in(self):
		"""Checks if the user has successfully logged in.
		
		When a user logs in, their username is stored and used for quick and simple checks 
		that the client has been authenticated before performing operations. 
		
		Returns:
			bool: True if the user has logged already, False otherwise.
		"""
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

		result = self.communicator.receive_enum(Signal)

		if result == Signal.SUCCESS:
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
		
		if self.verify_password(username, password) == Signal.SUCCESS:
			self.user = username
			color_print("Successfully logged in as %s" % username, color='blue')
		else:
			# Note: failure could be owed to two reasons: (1) incorrect password, 
			# (2) user doesn't exist. It is intentional that the status of a user
			# not be revealed - as is standard when usernames can be global
			# identifiers such as emails, etc. It would be trivial to enhance
			# the Signal codes to specifically specify INCORRECT_PASSWORD and
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
		
		Uploads the image specified by path to the server along with the price. Prompts the user 
		to select tags from a displayed list. Pre-defined tags are used as opposed to freeform 
		text in order to avoid the issue of typos leading to missed matches.
		
		Args: (within argument parser opts)
			path (str): Path to an image file.
			price (float): Cost of the image (product).
			quantity (int): Quantity of the image (product) in the inventory.
		"""
		if not self.check_if_logged_in():
			return 

		tags = self.prompt_user_for_tags()
		
		self.send_command(Command.ADD_IMAGE)

		image_path = Path(opts.path)
		self.communicator.send_image(image_path)
		self.communicator.send_string(image_path.name)

		self.communicator.send_float(opts.price)
		self.communicator.send_int(opts.quantity)
		self.communicator.send_list(tags)

		if self.communicator.receive_enum(Signal) == Signal.FAILURE:
			color_print("Error: Image %s could not be added because it already exists" % image_path.name, color='red')

	def prompt_user_for_tags(self):
		"""Displays tags and prompts user to select using integer identifiers.
		
		Shows all of the tags to the user, where each tag is associated with an integer 
		identifier. The user may enter nothing, which results in no tags being associated 
		with the image. The user may enter a single identifier, or the user may enter a comma 
		separated list of identifiers. In order to address errors in input, the user will be 
		prompted for input until they meet one of those conditions. 
		
		Returns:
			list(int): A list containing any tag identifiers selected by the user, or an empty list 
				  	   if the user did not make any selections.
		"""
		Tags.display_tags_for_selection()

		# ask for input until successful in case of errors in entry
		while True:
			selection_raw = input(color_str("Enter the number(s) of the relevant tag(s): ", color='green'))

			# actual first check if it's an empty input, ask them to confirm or have them retry
			if not selection_raw:
				confirmation = input(color_str("No tags have been selected, would you like to proceed? (y/n) ", color='magenta'))
				if confirmation == 'y':
					return list()
				else: 
					continue

			# check if input is a single integer
			elif selection_raw.isdigit():
				return [int(selection_raw)]

			# check if input is a comma separated string
			elif ',' in selection_raw:
				selection_list = selection_raw.split(',')

				try:
					# convert the list of integers to a set so duplicates get removed, this eliminates
					# errors on the server side (so technically this could just be an error, but for
					# a better user experience it gets fixed here)
					return list(set([int(s.strip()) for s in selection_list]))
				except:
					color_print("Error: invalid selection, provide a comma separated list of integers", color='red')
					continue

			# if the input didn't fall into any of the valid categories, prompt again
			else:
				color_print("Error: invalid selection, provide a comma separated list of integers", color='red')
		
	
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

		signal = self.communicator.receive_enum(Signal)

		if signal == Signal.NO_RESULTS: 
			color_print("No images similar to the provided image were found", color='magenta')
			return

		self.receive_batches_of_images()

	def do_browse_by_tag(self, args):
		"""Browses for images (products) matching the given tag(s).
		
		Prompts user to select tags and retrieves images (products) matching those tags 
		from the database. If the user enters no tags, all images can be shown. If the user 
		enters multiple tags, then images matching the _intersection_ of those tags will be 
		retrieved and displayed. 
		
		Args:
			args: unused
		"""
		if not self.check_if_logged_in():
			return 

		tags = self.prompt_user_for_tags() 

		self.send_command(Command.BROWSE_BY_TAG)

		self.communicator.send_list(tags)

		signal = self.communicator.receive_enum(Signal)

		if signal == Signal.NO_RESULTS: 
			color_print("No matches found for the given tags", color='magenta')
			return

		self.receive_batches_of_images()

	def receive_batches_of_images(self):
		"""Receives batches of images from the server.
		
		Receives one or more batches of images from the server. Waits until the server
		signals that it will begin sending and receives the continuously waits for signals 
		indicating the beginning/end of an individual image or batch. Prompts the user 
		to continue after each batch and signals the end transfer accordingly.
		"""
		# keep processing batches unless the server signals otherwise
		signal = self.communicator.receive_enum(Signal) 
		while signal != Signal.END_TRANSFER:
			image_batch = list()

			# within a batch keep receiving images until the server signals a stop
			if self.communicator.receive_enum(Signal) == Signal.START_BATCH:
				while self.communicator.receive_enum(Signal) != Signal.END_BATCH:
					self.receive_image(image_batch)

				self.display_batch_of_images(image_batch)

			#TODO: ask user for selection to add to cart *(need image id)*

			# the server will signal whether it has more images to send
			signal = self.communicator.receive_enum(Signal) 

			if signal == Signal.CONTINUE_TRANSFER:
				show_next = input("Display more images? (y/n) ")
				if show_next == 'y':
					self.communicator.send_enum(Signal.CONTINUE_TRANSFER) 
				else: 
					self.communicator.send_enum(Signal.END_TRANSFER)
					break

	def receive_image(self, image_batch):
		"""Receives an image from the server and adds it to the batch.
		
		Receives the image and related information from the server and adds all 
		of the information to the batch as a tuple.
		
		Args:
			image_batch (list(tuple)): A list representing a batch of images, each
									   image in the batch is a tuple.
		"""
		image_id = self.communicator.receive_int()
		image = self.communicator.receive_image()
		filename = self.communicator.receive_string()
		cost = self.communicator.receive_float()
		quantity = self.communicator.receive_int()

		selection_id = color_str("[%d] " % len(image_batch), color='cyan')
		image_details = color_str("%s (%d, $%.2f)" % (filename, quantity, cost), color='blue')
		print(selection_id + image_details)

		image_batch.append((image_id, image, filename, cost, quantity))

	def display_batch_of_images(self, images):
		"""Displays the provided images.
		
		Creates a figure in pyplot consisting of a row for each image. The image is displayed 
		in the left column and image information is displayed on the right. 
		
		Args:
			images (list(tuple)): A list where each element is a tuple (image data, filename, 
								  quantity, cost).
		"""
		figure = plt.figure(figsize=(5,10))

		columns = 2
		rows = len(images)

		j = 1

		for i in range(rows):
			(image_id, image, filename, cost, quantity) = images[i]

			figure.add_subplot(rows, columns, j)
			plt.axis('off')
			plt.imshow(image)

			ax = figure.add_subplot(rows, columns, j+1)
			image_data = "[%s]" % filename
			ax.text(0.5, 0.75, image_data, size=12, ha='center', va='center', wrap=True)
			image_data = "Stock: %d" % quantity
			ax.text(0.5, 0.5, image_data, size=12, ha='center', va='center', wrap=True)
			image_data = "Price: $%.2f" % cost
			ax.text(0.5, 0.25, image_data, size=12, ha='center', va='center', wrap=True)
			plt.axis('off')

			j += 2

		plt.axis('off')
		plt.show(block=True)

	def do_view_cart(self, args):
		"""Display contents of cart.
		
		Lists each item in the shopping cart along with quantity and price. 
		Total is also listed. 
		""" 

		self.check_if_logged_in()
		print("To be implemented")

	def do_exit(self, args):
		"""Exits the image repository.
		
		Closes the connection to the server and exits the client. 
		""" 
		print(self.goodbye)

		try:
			self.send_command(Command.EXIT)
		except (BrokenPipeError, ConnectionError):
			pass

		self.communicator.shutdown()

		raise SystemExit

	def do_eof(self, args):
		"""Exits the image repository.
		
		Closes the connection to the server and exits the client.
		""" 
		self.do_exit(args)

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
			Signal: Either SUCCESS or FAILURE depending on whether the username
					password combination was valid. 
		"""
		self.communicator.send_string(username)
		self.communicator.send_string(password)

		return self.communicator.receive_enum(Signal)

if __name__ == '__main__':
	prompt = ClientPrompt()
	prompt.cmdloop()