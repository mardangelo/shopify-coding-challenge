
import cmd2
from cmd2 import with_argparser, with_category

import getpass
import argparse
from pathlib import Path

from lazyme.string import color_print, color_str

import matplotlib.pyplot as plt

from util.batch_transfer import BatchTransfer
from util.communicator import Communicator
from util.input import prompt_for_integers, prompt_for_selection_and_quantity
from util.input import PositiveIntegerAction, PositiveFloatAction
from util.shopping import ShoppingCart, Product

from util.enum.command import Command
from util.enum.signal import Signal
from util.enum.tags import Tags

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

	CMD_CAT_USER_MANAGEMENT = "User Management"
	CMD_CAT_IMAGE_REPOSITORY = "Image Repository"
	CMD_CAT_SHOPPING_CART = "Shopping Cart"

	def __init__(self):
		self.user = None 
		self.shopping_cart = ShoppingCart()
		self.communicator = Communicator()
		self.batch_transfer = BatchTransfer(self.communicator)

		super().__init__()

		del cmd2.Cmd.do_quit

		self.hidden_commands.append('py')
		self.hidden_commands.append('alias')
		self.hidden_commands.append('edit')
		self.hidden_commands.append('history')
		self.hidden_commands.append('macro')
		self.hidden_commands.append('run_pyscript')
		self.hidden_commands.append('run_script')
		self.hidden_commands.append('quit')
		self.hidden_commands.append('set')
		self.hidden_commands.append('shell')
		self.hidden_commands.append('shortcuts')

		self.disable_category(self.CMD_CAT_IMAGE_REPOSITORY, "You must be logged in to manipulate the repository")
		self.disable_category(self.CMD_CAT_SHOPPING_CART, "You must be logged in to manage your shopping cart")

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

	@with_category(CMD_CAT_USER_MANAGEMENT)
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
			color_print("Error: Must provide a username", color='red')
			return

		color_print("Attempting to create user %s" % username, 'blue')

		password = getpass.getpass()
		if password is none:
			color_print("Error: Must enter a password", color='red')
			return

		self.send_command(Command.CREATE_USER)

		self.communicator.send_string(username)
		self.communicator.send_string(password)

		result = self.communicator.receive_enum(Signal)

		if result == Signal.SUCCESS:
			color_print("Successfully created user %s" % username, color='blue')
		else: 
			color_print("Error: User already exists", color='red')

	@with_category(CMD_CAT_USER_MANAGEMENT)
	def do_login(self, username):
		"""Logs user in as given username.
		
		Prompts user for the password associated with username. If the 
		password is incorrect the command fails. Most commands for 
		the repository don't function unless the user is logged in. 
		
		Arguments:
			username (str): Username to log in with.
		""" 
		if username == "":
			color_print("Error: Must provide a username", color='red')
			return

		color_print("Attempting to log in as %s" % username, color='blue')

		password = getpass.getpass()
		if password is none:
			color_print("Error: Must enter a password", color='red')
			return

		self.send_command(Command.LOGIN)
		
		if self.verify_password(username, password) == Signal.SUCCESS:
			self.user = username
			color_print("Successfully logged in as %s" % username, color='blue')

			self.enable_category(self.CMD_CAT_IMAGE_REPOSITORY)
			self.enable_category(self.CMD_CAT_SHOPPING_CART)
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
	argparser_add_image.add_argument('path', type=str, nargs='+', help='path to an image file (backslash escape is not supported)')
	argparser_add_image.add_argument('price', type=float, help='price of the image (product)', action=PositiveFloatAction)
	argparser_add_image.add_argument('quantity', type=int, help='number of image (product) to stock', action=PositiveIntegerAction)

	@with_category(CMD_CAT_IMAGE_REPOSITORY)
	@with_argparser(argparser_add_image)
	def do_add_image(self, opts):
		"""Adds an image (product) to Image Repository.
		
		Uploads the image specified by path to the server along with the price. If the image does 
		not exist or is of an invalid format an error will be reported. Prompts the user 
		to select tags from a displayed list. Pre-defined tags are used as opposed to freeform 
		text in order to avoid the issue of typos leading to missed matches. 

		Note: Paths can be entered using tab for autocompletion.
		"""
		if not self.check_if_logged_in():
			return 

		image_path = Path(" ".join(opts.path)).expanduser().resolve()
		if not self.communicator.check_image(image_path):
			return

		Tags.display_tags_for_selection()
		tags = prompt_for_integers(list(map(int, Tags))) 
		
		self.send_command(Command.ADD_IMAGE)

		self.communicator.send_image(image_path)
		self.communicator.send_string(image_path.name)

		self.communicator.send_float(opts.price)
		self.communicator.send_int(opts.quantity)
		self.communicator.send_list(tags)

		if self.communicator.receive_enum(Signal) == Signal.FAILURE:
			color_print("Error: Image %s could not be added" % image_path.name, color='red')
		else: 
			image_id = self.communicator.receive_int()
			color_print("Added image [%d] %s ($%.2f, %d)" % (image_id, image_path.name, opts.price, opts.quantity), color='blue')

	argparser_update_image = argparse.ArgumentParser()
	argparser_update_image.add_argument('image_id', type=int, help='the identifier of the image to be updated')
	argparser_update_image.add_argument('price', type=float, help='price of the image (product)', action=PositiveFloatAction)
	argparser_update_image.add_argument('quantity', type=int, help='number of image (product) to stock', action=PositiveIntegerAction)

	@with_category(CMD_CAT_IMAGE_REPOSITORY)
	@with_argparser(argparser_update_image)
	def do_update_image(self, opts):
		"""Updates an image (product) in the Image Repository.
		
		Updates the image specified by id with the new cost and quantity. If the image does not 
		exist in the repository, this operation fails and reports an error. 
		"""
		if not self.check_if_logged_in():
			return 

		self.send_command(Command.UPDATE_IMAGE)

		self.communicator.send_int(opts.image_id)
		self.communicator.send_float(opts.price)
		self.communicator.send_int(opts.quantity)

		if self.communicator.receive_enum(Signal) == Signal.FAILURE:
			color_print("Error: Image [%d] could not be updated" % opts.image_id, color='red')
		else:
			color_print("Updated image [%d] with ($%.2f, %d)" % (opts.image_id, opts.price, opts.quantity), color='blue')

	argparser_delete_image = argparse.ArgumentParser()
	argparser_delete_image.add_argument('image_id', type=int, help='the identifier of the image to be deleted')

	@with_category(CMD_CAT_IMAGE_REPOSITORY)
	@with_argparser(argparser_delete_image)
	def do_delete_image(self, opts):
		"""Deletes an image (product) in the Image Repository.
		
		Sends a request to the server to delete the image if it exists. If the image does not exist 
		in the repository, this operation fails and reports an error. 
		"""
		if not self.check_if_logged_in():
			return 

		self.send_command(Command.DELETE_IMAGE)

		self.communicator.send_int(opts.image_id)

		if self.communicator.receive_enum(Signal) == Signal.FAILURE:
			color_print("Error: Image [%d] could not be deleted" % opts.image_id, color='red')
		else:
			color_print("Deleted image [%d]" % opts.image_id, color='blue')
	
	complete_search_by_image = cmd2.Cmd.path_complete

	argparser_search_by_image = argparse.ArgumentParser()
	argparser_search_by_image.add_argument('path', type=str, nargs='+', help='path to an image file (backslash escape is not supported)')

	@with_category(CMD_CAT_IMAGE_REPOSITORY)
	@with_argparser(argparser_search_by_image)
	def do_search_by_image(self, opts):
		"""Find images (products) similar to the provided image.
		
		Uploads the given image to the server and performs a similarity computation
		on the other images in the database using nearest neighbours. 
		"""
		if not self.check_if_logged_in():
			return 

		image_path = Path(" ".join(opts.path)).expanduser().resolve()
		if not self.communicator.check_image(image_path):
			return

		self.send_command(Command.SEARCH_BY_IMAGE)

		self.communicator.send_image(image_path)
		self.communicator.send_string(image_path.name)

		signal = self.communicator.receive_enum(Signal)

		if signal == Signal.NO_RESULTS: 
			color_print("No images similar to the provided image were found", color='magenta')
			return

		self.batch_transfer.receive_batches_of_images(self.add_to_cart_prompt)

	@with_category(CMD_CAT_IMAGE_REPOSITORY)
	def do_browse_by_tag(self, args):
		"""Browses for images (products) matching the given tag(s).
		
		Prompts user to select tags and retrieves images (products) matching those tags 
		from the database. If the user enters no tags, all images can be shown. If the user 
		enters multiple tags, then images matching the _intersection_ of those tags will be 
		retrieved and displayed. 
		"""
		if not self.check_if_logged_in():
			return

		Tags.display_tags_for_selection()
		color_print("Note: if no tags are selected, browse will return all images in the repository", color='blue')
		tags = prompt_for_integers(list(map(int, Tags))) 

		self.send_command(Command.BROWSE_BY_TAG)

		self.communicator.send_list(tags)

		signal = self.communicator.receive_enum(Signal)

		if signal == Signal.NO_RESULTS: 
			color_print("No matches found for the given tags", color='magenta')
			return

		self.batch_transfer.receive_batches_of_images(self.add_to_cart_prompt)

	@with_category(CMD_CAT_IMAGE_REPOSITORY)
	def do_browse_images(self, args):
		"""Browses the images (products) in the repository.
		
		Retrieves batches of images from the repository and displays them to the user from most recently added 
		to least recently added. 
		"""
		if not self.check_if_logged_in():
			return

		self.send_command(Command.BROWSE_IMAGES)

		signal = self.communicator.receive_enum(Signal)

		if signal == Signal.NO_RESULTS: 
			color_print("No images found in the repository", color='magenta')
			return

		self.batch_transfer.receive_batches_of_images(self.add_to_cart_prompt)

	def add_to_cart_prompt(self, image_batch):
		"""Prompts the user to enter desired products and quantities.
		
		Prompts the user to enter an item id and quantity or nothing at all if they do not wish 
		to add any items to their cart. The quantity must not exceed stock, if the user enters 
		such a quantity, they will have to repeat the request.
		
		Args:
			image_batch (list(tuple)): A batch of images where each tuple is an image.
		"""
		prompt = True
		while prompt:
			response = prompt_for_selection_and_quantity([image[0] for image in image_batch])

			if not response:
				break

			(product_id, quantity) = response

			image_product = Product([image for image in image_batch if image[0] == product_id].pop())

			if quantity <= image_product.stock:
				image_product.quantity = quantity
				self.shopping_cart.add_to_cart(image_product)
			else:
				color_print("Error: Quantity entered for [%d] exceeds existing stock of %d" % (image_product.id, image_product.stock), color='red')

	@with_category(CMD_CAT_SHOPPING_CART)
	def do_view_cart(self, args):
		"""Display contents of cart.
		
		Lists each item in the shopping cart along with quantity and price. 
		Total is also listed. 
		""" 
		self.check_if_logged_in()
		self.shopping_cart.display_cart()

	argparser_remove_from_cart = argparse.ArgumentParser()
	argparser_remove_from_cart.add_argument('product_id', type=int, help='id of an image (product)')

	@with_category(CMD_CAT_SHOPPING_CART)
	@with_argparser(argparser_remove_from_cart)
	def do_remove_from_cart(self, opts):
		"""Removes a product from the cart.

		If the product exists in the cart it is removed. If the product was not in the cart a warning 
		is displayed to the user.
		"""
		self.check_if_logged_in()
		self.shopping_cart.remove_from_cart(opts.product_id)	

	argparser_update_cart = argparse.ArgumentParser()
	argparser_update_cart.add_argument('product_id', type=int, help='id of an image (product)')
	argparser_update_cart.add_argument('quantity', type=int, help='new quantity of the image (product)')

	@with_category(CMD_CAT_SHOPPING_CART)
	@with_argparser(argparser_update_cart)
	def do_update_in_cart(self, opts):
		"""Updates the quantity of a product in the cart.

		If the product exists in the cart it is updated with the new quantity. If the product was not in 
		the cart a warning is displayed to the user.
		"""
		self.check_if_logged_in()
		self.shopping_cart.update_in_cart(opts.product_id, opts.quantity)

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