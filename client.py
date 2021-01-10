
import cmd2
from cmd2 import with_argparser
from colorama import Fore, Style
from util.communicator import Communicator
import getpass
import argparse
from util.command import Command
from util.status import Status
from lazyme.string import color_print, color_str

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

	#TODO: for security, the server should remember what user has logged in so that someone
	#	   cannot simply populate this field manually and magically gain access to the server.
	def check_if_logged_in(self):
		"""Checks if there is a user that has had their credentials verified by the server."""
		if self.user == "":
			print("User must be logged in for this command to function")

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

		self.communicator.encrypt_and_send(self.encode(username))
		self.communicator.encrypt_and_send(self.encode(password))

		result = self.communicator.receive_and_decrypt().decode('utf8')

		if Status(result) == Status.SUCCESS:
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

	def do_view_cart(self, args):
		"""Display contents of cart.
		
		Lists each item in the shopping cart along with quantity and price. 
		Total is also listed. 
		""" 

		self.check_if_logged_in()
		print("To be implemented")

	complete_add = cmd2.Cmd.path_complete

	argparser_add = argparse.ArgumentParser()
	argparser_add.add_argument('path', type=str)
	argparser_add.add_argument('price', type=float)

	@with_argparser(argparser_add)
	def do_add(self, opts):
		"""Adds an image (product) to Image Repository.
		
		Uploads the image specified by path to the server along with the price.
		
		Args: (within argument parser opts)
			path (str): URL or local path to an image file.
			price (float): Cost of the iamge (product).
		"""
		print(opts.path)
		print(opts.price)

		# 1) load the file at path into memory
		# 2) send the image to server (encrypt first)

		print("Not yet implemented")

	def send_command(self, command):
		"""Sends a command to the server.
		
		Encodes the command as a string then encrypts it and sends it to 
		the server. 
		
		Args:
			command (Command): The command representing the operation to be performed. 
		"""
		self.communicator.encrypt_and_send(self.encode(command.value))

	def encode(self, string):
		"""Encodes a string as bytes.
		
		Encodes as string into it's utf8 representation as bytes. Converting the 
		string to its byte representation is required for the encryption process. 
		
		Args:
			string: The string to be encoded. 
		
		Returns:
			bytes: Byte representation of the string. 
		"""
		return string.encode('utf8')

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
		self.communicator.encrypt_and_send(self.encode(username))
		self.communicator.encrypt_and_send(self.encode(password))

		result = self.communicator.receive_and_decrypt().decode('utf8')

		return Status(result)

	def do_exit(self, args):
		"""Exits the image repository.
		
		Exits the repository and closes the connection to the server. 
		""" 
		print(self.goodbye)

		self.communicator.shutdown()

		raise SystemExit

if __name__ == '__main__':
	prompt = ClientPrompt()
	prompt.cmdloop()