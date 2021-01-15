"""Manage the shopping experience of a user.

Defines classes to represent a shopping cart consisting of products that define the 
cost and quantity of the item. 
"""

from lazyme.string import color_print

from tabulate import tabulate

class ShoppingCart:
	"""Manages the items the user wishes to purchase.
	
	Containts faculties to add a product to the cart, remove a product from the cart, 
	update a product within a cart, and display the cart along with the calculated total cost.

	Attributes:
		cart (dict): A dictionary representing the shopping cart where the keys are the product ids
					 and the values are Product objects. 
	"""

	def __init__(self):
		"""Intitializes an empty shopping cart."""
		self.cart = dict()

	def add_to_cart(self, product):
		"""Adds a product to the cart.
		
		Adds the given product to the cart as long as it has a non-zero positive quantity. If the 
		quantity is zero and the item is in the cart then the item is removed from the cart. If 
		the item is in the cart, the item is updated with the quantity of the given product. 
		
		Args:
			product (Product): The product to be added to the cart. 
		"""
		if product.id in self.cart:
			if product.quantity == 0:
				self.remove_from_cart(product.id)
				return
			
			self.update_in_cart(product.id, product.quantity)
			return

		if product.quantity > 0:
			color_print("Product [%d] was added to cart" % product.id, color='blue')
			self.cart[product.id] = product

	def remove_from_cart(self, product_id):
		"""Removes a product from the cart. 
		
		Removes the product having the given id from the cart if it exists, otherwise a warning
		message is printed.
		
		Args:
			product_id (int): The id of the product to be removed.
		"""
		if not self.cart.pop(product_id, None):
			color_print("Warning: Product [%d] was not in the cart" % product_id, color='magenta')
		else:
			color_print("Product [%d] was removed from cart" % product_id, color='blue')

	def update_in_cart(self, product_id, quantity):
		"""Updates the quantity of a product in the cart."
		
		If the product is in the cart, updates the quantity. If the provided quantity is 0 then the 
		item is removed from the cart. 
		
		Args:
			product_id (int): The id of the product to be updated.
			quantity (int): The updated quantity of the product.
		"""
		if product_id not in self.cart:
			color_print("Error: product [%d] was not in the cart" % product_id, color='red')
			return

		if quantity < 0: 
			color_print("Error: product [%d] cannot have a negative quantity" % product_id, color='red')
			return
			
		elif quantity == 0: 
			self.remove_from_cart(product_id)
			return

		original = self.cart[product_id]

		if quantity > original.stock:
			color_print("Error: requested quantity exceeds stocked amount %d" % original.stock, color='red')
			return

		color_print("Updating quantity of product [%d]" % product_id, color='blue')
		original.quantity = quantity

	def display_cart(self):
		"""Displays the current shopping cart.
		
		Creates a table to display the id, filename, cost, and quantity of the products being ordered. 
		Also computes and outputs the total cost of the order. 
		"""
		output = list()
		total = 0
		headers = ['id', 'filename', 'cost', 'quantity']

		for product in self.cart.values():
			output.append(product.to_list())
			total += product.total()

		color_print(tabulate(output, headers=headers, tablefmt='pretty'), color='yellow')
		color_print("[=] Total: $%.2f" % total, color='yellow')

class Product:
	"""Represents a product that the user wishes to purchase.
	
	Contains information about the product such as the image, the filename, the cost, the amount in stock, 
	and the quantity. 

	Attributes:
		id (int): Identifier for the product (from Image.id in database).
		image (Image): Image data for the product.
		filename (str): The filename for the image.
		cost (float): The cost of the product.
		stock (int): The number of product currently in stock.
		quantity (int): The number of product that the user would like to order.
	"""

	def __init__(self, image_info):
		"""Initializes a product.
		
		Creates a product that stores information about an image as well as a quantity provided by the user.
		
		Args:
			image_info (tuple): A tuple containing information about an image, specifically (image id, 
								the image itself, filename, cost, stock)
		"""
		self.id = image_info[0]
		self.image = image_info[1]
		self.filename = image_info[2]
		self.cost = float(image_info[3])

		# in a real system with simultaneous connections, this would need to be read from the server
		# caching in an object like this would not provide a consistent view to all users
		self.stock = image_info[4] 
		self.quantity = 0

	def to_list(self):
		"""Converts the product to a list representation for pretty printing with tabulate"""
		return [self.id, self.filename, ("$%.2f" % self.cost), self.quantity]

	def total(self):
		"""Computes the total cost of the product.
		
		The total cost is the number of items (quantity) multipled by the cost per item.
		
		Returns:
			float: The total cost for the desired quantity of the product.
		"""
		return self.quantity * self.cost

	def __str__(self):
		return "[%d] %s (%d/%d, $%.2f)" % (self.id, self.filename, self.quantity, self.stock, self.cost)