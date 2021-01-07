from cmd import Cmd
import getpass

class ClientPrompt(Cmd):
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

	prompt = "image-repo> "
	intro = "Welcome to Image Repository. Type ? to list commands"

	user = "" # stores the name of the logged in user 
	def check_if_logged_in(self):
		if self.user == "":
			print("User must be logged in for this command to function")

	#TODO: make a server interaction class for the communication between client and server
	verify_password = True

	def do_view_cart(self, args):
		"""Display contents of cart.
		
		Lists each item in the shopping cart along with quantity and price. 
		Total is also listed. 
		""" 

		self.check_if_logged_in()
		print("To be implemented")

	def do_add(self, path, price):
		"""Adds an image (product) to Image Repository.
		
		Uploads the image specified by path to the server along with the price.
		
		Args:
			path (str): URL or local path to an image file.
			price (float): Cost of the iamge (product).
		"""

		print("Adding image located at %s" % path)

	def do_exit(self, args):
		"""Exits the image repository.
		
		Exits the repository and loses current shopping cart. 
		""" 

		#TODO: implement a database extension that tracks shopping 
		#cart state by user.

		print("Thank you for using Image Repository. Goodbye.")
		raise SystemExit

	def do_login(self, username):
		"""Logs user in as given username.
		
		Prompts user for the password associated with username. If the 
		password is incorrect the command fails. Most commands for 
		the repository don't function unless the user is logged in. 
		
		Arguments:
			username (str): Username to log in with.
		""" 

		#TODO: implement password checking that sends the password to 
		#the server (encrypted) and the server checks against a salted
		#password that it has stored in the database.

		if username == "":
			print("Username must be provided as argument to login command")
			return

		print("Attempting to log in as %s" % username)
		password = getpass.getpass()
		
		if self.verify_password == True: #TODO: call Server.verify_password(username,password)
			self.user = username
			print("Successfully logged in as %s" % username)

if __name__ == '__main__':
	prompt = ClientPrompt()
	prompt.cmdloop()