"""Extremely simple method to display images using matplotlib. 

Creates a figure with enough rows to contain a batch of images and a second column 
to display information about a given image.
"""

import matplotlib.pyplot as plt

plt.switch_backend('Qt5Agg') # default backend hangs on macos big sur when closing window

def display_batch_of_images(images):
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
	plt.show(block=False)

