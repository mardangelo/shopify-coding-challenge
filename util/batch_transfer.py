from .gui import display_batch_of_images

from util.input import prompt_for_binary_choice
from util.enum.signal import Signal

from lazyme.string import color_str, color_print

from pathlib import Path

class BatchTransfer():
	"""Protocol for sending and receiving batches of images.

	Implements the protocols that the client and server use to transmit and receive 
	batches of images.

	Attributes:
		communicator (Communicator): Represents connection to client/server. 
	"""

	def __init__(self, communicator):
		"""Initializes BatchTransfer with a communicator"""
		self.communicator = communicator

	def receive_batches_of_images(self, batch_func):
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

				display_batch_of_images(image_batch)
				batch_func(image_batch)

			# the server will signal whether it has more images to send
			signal = self.communicator.receive_enum(Signal) 

			if signal == Signal.CONTINUE_TRANSFER:
				show_next = prompt_for_binary_choice("Display more images? (y/n) ")
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

		selection_id = color_str("[%d] " % image_id, color='cyan')
		image_details = color_str("%s (%d, $%.2f)" % (filename, quantity, cost), color='blue')
		print(selection_id + image_details)

		image_batch.append((image_id, image, filename, cost, quantity))

	def send_images_in_batches(self, image_count, retrieve_func, retrieve_args, batch_size=5):
		"""Sends images to the client in batches.
		
		Given a number of available images to be sent, batches of those images are packaged 
		together and sent in units until the images are exhausted, or the user has declined 
		to received more images.
		
		Args:
			image_count (int): The total number of images that could be sent.
			retrieve_func (function): A function that returns a list of tuples where each 
									  tuple contains: (path to image, quantity, cost). This
									  function should retrieve batch_size items.
			retrieve_args (list): A list of any arguments to be passed to retrieve_func.
			batch_size (int): The number of images to be included in a single batch. (default: {5})
		"""
		# send a signal to the client that images are about to be sent
		self.communicator.send_enum(Signal.SEARCH_RESULTS)

		# send images that do not quite amount to a full batch
		if image_count < batch_size:
			self.communicator.send_enum(Signal.START_TRANSFER)
			images = retrieve_func(*retrieve_args)
			self.send_batch_of_images(images)
			self.communicator.send_enum(Signal.END_TRANSFER)
			return

		# keep sending images in batches until the user sends a stop signal or there are no more images
		images_sent = 0
		self.communicator.send_enum(Signal.START_TRANSFER)

		while image_count - images_sent > 0:
			images = retrieve_func(*retrieve_args, offset=images_sent)
			self.send_batch_of_images(images) 

			# if there are more images left to be sent beyond this batch, let the client know
			# then wait for their response as to whether another batch should be sent
			if image_count - images_sent > batch_size:
				self.communicator.send_enum(Signal.CONTINUE_TRANSFER)
				if self.communicator.receive_enum(Signal) == Signal.END_TRANSFER:
					color_print("Client has stopped requesting images", color='blue')
					break
			else: 
				self.communicator.send_enum(Signal.END_TRANSFER)
				break

			images_sent += batch_size

	def send_batch_of_images(self, images):
		"""Sends a batch of images to the client. 
		
		Signals to the client that a batch is about to be sent, then sends each image 
		individually with a signal that an image about to be sent before each one. Once
		the batch is exhausted, a signal is sent that the batch has been completed. 
		
		Args:
			images (list(tuple)): A list of tuples where each tuple contains information
								  about an image (path, quantity, cost).
		"""
		self.communicator.send_enum(Signal.START_BATCH)

		for image in images:
			self.communicator.send_enum(Signal.CONTINUE_BATCH)
			color_print("Sending image %s to client" % str(image[1]), color='green')

			self.communicator.send_int(image[0])
			self.communicator.send_image(Path(image[1]))
			self.communicator.send_string(Path(image[1]).name)
			self.communicator.send_float(image[3])
			self.communicator.send_int(image[2])
		
		self.communicator.send_enum(Signal.END_BATCH)