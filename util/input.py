"""Methods to simplify receiving input from user input.

Prompts user for input repeatedly until they enter a valid input. Performs 
checks on the input each time and converts the input into the appropriate 
variable type. 
"""
import argparse

from lazyme import color_str, color_print

class ArgumentParserError(Exception): 
	"""Denotes a error when processing the input."""
	pass

class ThrowingArgumentParser(argparse.ArgumentParser):
	"""Custom argument parser that throws exceptions.

	The original argument parser prints help messages when there are errors because it is intended to 
	be used in a more traditional command line environment, but since we want to repeat until successful 
	and handle errors in input gracefully, we raise an exception when we encounter an error. 
	"""

	def error(self, message):
		"""Raises exceptions when an error is encountered.
		
		Raises an exception if the input cannot be parsed correctly. 
		
		Args:
			message (str): The error message.
		
		Raises:
			ArgumentParserError: An exception representing the error.
		"""
		raise ArgumentParserError(message)

def prompt_for_integers(valid_values):
	"""Prompts the user to select items using integer identifiers.
	
	Receives input from the user and accepts either nothing (empty string) or a series of 
	integers separated by spaces. Each inputted integer is validated against the provided 
	list of valid_values. This prompt repeats until it receives a valid input. 
	
	Returns:
		list(int): A list containing any integers entered by the user, or an empty list 
			  	   if the user did not make any selections.
	"""
	parser = ThrowingArgumentParser()
	parser.add_argument('selection', nargs="+", type=int, choices=valid_values)

	# prompt the user for input until they enter something valid
	while True:
		try:
			raw_selection = input(color_str("Enter the number(s) of the relevant item(s) separated by spaces (or [ENTER] to continue): ", color='green'))
			if not raw_selection:
				color_print("No items selected", color='blue')
				return list()

			args = parser.parse_args(process_input(raw_selection))
			color_print("Selected: %s" % str(args.selection), color='blue')
			return args.selection
		except ArgumentParserError as e:
			color_print("Error: " + str(e)[str(e).find(':') + 2:], color='red')

class PositiveIntegerAction(argparse.Action):
	"""Action that validates input as positive integer.
	
	After the input has been successfully converted to an integer, this action checks that 
	the value is non-negative.
	"""

	def __call__(self, parser, namespace, values, option_string=None):
		"""Validates that a given value is a positive integer.
		
		See base class for more non-customized details.
		"""
		if values < 0:
			parser.error("Error: Minimum quantity is 0")

		setattr(namespace, self.dest, values)

def prompt_for_selection_and_quantity(valid_values):
	"""Prompts the user to present a valid selection and enter a desired quantity.
	
	Receives input from the user and accepts either nothing (empty string) or a pair of 
	integers representing id and quantity. Each inputted id is validated against the 
	provided list of valid_values and the quantity must be a positive integer. This prompt 
	repeats until it receives a valid input. 
	
	Returns:
		tuple(int,int): A tuple consisting of the selection identifier and the quantity. 
						If the user did not provide any input, the tuple is empty.
	"""
	parser = ThrowingArgumentParser()
	parser.add_argument('selection', type=int, choices=valid_values)
	parser.add_argument('quantity', type=int, action=PositiveIntegerAction)

	# prompt the user for input until they enter something valid
	while True:
		try:
			raw_selection = input(color_str("Enter the the id of the product and the desired quantity (or [ENTER] to continue): ", color='green'))
			if not raw_selection:
				color_print("No items selected", color='blue')
				return tuple()

			args = parser.parse_args(process_input(raw_selection))
			color_print("Selected: [%d] x%d" % (args.selection, args.quantity), color='blue')
			return (args.selection, args.quantity)
		except ArgumentParserError as e:
			color_print("Error: " + str(e)[str(e).find(':') + 2:], color='red')

def prompt_for_binary_choice(message):
	parser = ThrowingArgumentParser()
	parser.add_argument('choice', type=str, choices=['y', 'n'])

	# prompt the user for input until they enter something valid
	while True:
		try:
			raw_selection = input(color_str(message, color='green'))
			args = parser.parse_args(process_input(raw_selection))
			color_print("Entered: %s" % args.choice, color='blue')
			return args.choice
		except ArgumentParserError as e:
			color_print("Error: " + str(e)[str(e).find(':') + 2:], color='red')

def process_input(input):
	"""Splits input string into a list of arguments.
	
	Removes leading and trailing spaces, then splits the string on spaces.
	
	Args:
		input (str): The text inputted by the user
	
	Returns:
		list(str): A list of strings.
	"""
	return input.lstrip(' ').rstrip(' ').split()