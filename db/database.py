from pathlib import Path

from sqlalchemy import create_engine, MetaData, and_, distinct
from sqlalchemy.sql import exists
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from tabulate import tabulate

from lazyme.string import color_print

from passlib.hash import pbkdf2_sha256

from .table.base import Base
from .table.user import User
from .table.image import Image
from .table.image_tag import ImageTag
from .table.tag import Tag

from util.enum.tags import Tags 

import util.similarity as tf

class Database():
	"""Utility class for managing the database.
	
	Provides functions for querying and manipulating the database. The DBMS used 
	is SQLite for the purposes of portability for this demo. A real system should 
	use a more performant database. 

	Attributes:		
		session (Session): Represents the session with the database. 
	"""

	def __init__(self):
		"""Establishes a connection with the database. 
		
		Creates the database and creates all of the tables that are defined as 
		a subclass of Base in the program (as long as they have been imported).
		"""
		engine = create_engine('sqlite:///image-repository.sqlite', echo=False)

		Session = sessionmaker(bind=engine)
		self.session = Session()

		# creates all tables that are "visible" (e.g., imported) 
		Base.metadata.create_all(bind=engine)

		if not self.session.query(Tag).first():
			self.initialize_tags()

	def initialize_tags(self):
		"""Initializes the Tag table with tags defined in the Tags enum."""
		for tag_enum in Tags:
			tag = Tag(id=tag_enum.value, description=tag_enum.name)
			self.session.add(tag)
			self.session.commit()

	def create_user(self, username, password):
		"""Creates a user.
		
		Creates a new user if the user with that username does not already exist. 
		If the username does not exist, the password is hashed and stored in the 
		database along with the username. 
		
		Args:
			username: Username of the user to be created.
			password: Password of the user to be created.
		
		Returns:
			bool: Whether the user was created successfully or not.
		"""
		(user_exists, ) = self.session.query(exists().where(User.username == username))
		if user_exists[0]:
			color_print("Error: Username %s is already in use" % username, color='red')
			return False

		hash = pbkdf2_sha256.hash(password)
		user = User(username=username, password=hash)

		self.session.add(user)
		self.session.commit()

		color_print("Created user %s" % username, color='blue')

		return True

	def verify_user(self, username, password):
		"""Verifies the username, password pair.
		
		Computes the hash of the provided password and compares it with the 
		hashed password (for the same user) stored in the database. 
		
		Args:
			username: Username being checked.
			password: Password being checked.
		
		Returns:
			bool: True if the credentials matched, else False.
		"""
		(user_exists, ) = self.session.query(exists().where(User.username == username))
		if not user_exists[0]:
			color_print("Error: User %s does not exist" % username, color='red')
			return False

		# There will be exactly one row for the username because usernames are 
		# constrained to be unique by the database
		user_info = self.session.query(User).filter(User.username == username).one()
		result = pbkdf2_sha256.verify(password, user_info.password)

		if result:
			color_print("User credentials match those stored in the database", color='blue')
		else: 
			color_print("Error: User credentials are not a match", color='red')

		return result

	def add_image(self, path, feature_vector, quantity, cost, username):
		"""Adds an image to the repository. 
		
		Stores information about the image as well as a path to the image file. If an image
		by the same name already exists in the database it is not added again. Note: this 
		implementation relies on the filename being unique. There is a tradeoff between allowing 
		duplicates (redundancy, database size, access times, etc.) and trying to prevent duplicates 
		by using another attribute. Feature vectors could be considered, but since they are by 
		definition a reduction in dimensionality there is no guarantee that images won't collide 
		even if they are not different. A real implementation should evaluate other options and
		possible tradeoffs. Low hanging fruit may be (filename, feature_vector) combination, but 
		it may still result in redundant database entries.
		
		Args:
			path (str): Path to the image file on disk. 
			feature_vector (bytes): A feature tensor in byte format.  
			quantity (int): The quantity of the image in stock. 
			cost (float): Price of one image (product).

		Returns:
			int: Database id if image was added, None if the image already exists. 
		"""
		(image_exists, ) = self.session.query(exists().where(Image.image_path == path))
		if image_exists[0]:
			color_print("Warning: Image %s already exists in database, skipping." % path, color='magenta')
			return None

		image = Image(image_path=path, feature_vector=feature_vector, quantity=quantity, cost=cost, seller=username)
		self.session.add(image)
		self.session.commit()

		color_print("Image %s successfully added to database" % path, color='blue')

		return image.id

	def update_image(self, image_id, cost, quantity):
		"""Updates the image within the repository.
		
		Checks if the database contains an entry for the given image identifier and updates its cost 
		and quantity. 
		
		Args:
			image_id (int): The repository identifier of the image.
			cost (float): The updated cost of the image.
			quantity (int): The updated quantity of the image in stock.
		
		Returns:
			bool: True if the image was updated, False if the image was not in the repository.
		"""
		image = self.session.query(Image).filter_by(id=image_id).one_or_none()

		if not image:
			return False

		image.cost = cost
		image.quantity = quantity

		self.session.commit()

		return True

	def add_tags(self, image_id, tags):
		"""Associate the given tags with the image in the database.
		
		Insert pairs of (image_id, tag_id) into the database by iterating over the 
		given list of tag identifiers.
		
		Args:
			image_id (int): The database id of the image to add tags for.
			tags (list(int)): A list of tags ids to associate with the image.
		"""
		for tag in tags:
			image_tag = ImageTag(image_id=image_id, tag_id=tag)
			self.session.add(image_tag)

		self.session.commit()

	def count_images_with_tags(self, tags):
		"""Calculates the number of images that have the given tags.
		
		Determines how many images have been associated with all of the given tags. 
		If no tags are provided, the number of total images in the database is reported.
		
		Args:
			tags (list(int)): A list of tag identifiers to be matched.
		
		Returns:
			int: The number of images matching the tags given.
		"""
		if not tags: 
			return self.session.query(Image.id).count()
		
		return self.build_select_images_with_tags_query(tags).count()

	def build_select_images_with_tags_query(self, tags):
		"""Builds a query to find images with all given tags.
		
		Given a list of tags, determines which images have each individual tag and then 
		intersects those images to find the images with all of the tags.
		
		Args:
			tags (list(int)): A list of tag identifiers to be matched.
		
		Returns:
			Query: A query that intersects the checks for each individual tag.
		"""
		queries = list()
		for tag in tags:
			query = self.session.query(ImageTag.image_id.label("image_id")).filter_by(tag_id=tag)
			queries.append(query)

		return queries.pop(0).intersect(*queries)

	def retrieve_images_with_tags(self, tags, batch_size=5, offset=0):
		"""Gets information about the images matching the given tags. 
		
		Finds the images that are associated with all of the given tags, then retrieves 
		necessary attributes about those images (path, cost, quantity). The number of images 
		returned is capped at 5 (but may be less) and an offset can be provided in order to 
		send images in batches (continuing from where the last batch ended). 
		
		Args:
			tags (list(int)): A list of tag identifiers to be matched.
			batch_size (int): The maximum number of images to be returned. (default: {5})
			offset (int): The offset to be passed to the query which denotes the point where 
						  the results should start being retrieved from. (default: {0})

		Returns:
			list(tuple): A list where each element is a tuple representing an image and containing 
						 (id, path to image, quantity, cost).
		"""
		if not tags: 
			return self.session.query(Image.id, Image.image_path, Image.quantity, Image.cost) \
							   .offset(offset).limit(batch_size).all()

		matching_images = self.build_select_images_with_tags_query(tags).subquery()
		first_column = next(iter(matching_images.c)) # get a reference to the column of image ids

		return self.session.query(Image.id, Image.image_path, Image.quantity, Image.cost) \
						   .join(matching_images, first_column == Image.id) \
						   .offset(offset).limit(batch_size).all()

	def get_image_attributes(self, image_ids, batch_size=5, offset=0):
		"""Retrieves the attributes for a batch of images.
		
		Queries the database for each identifer provided and retrieves the path to the image, 
		the quantity, and its cost. This is done for a batch of the provided size that starts
		at the given offset. Note that this is an ordered operation, which is important when 
		gathering the attributes of nearest neighbours! The most similar images retain their 
		position in the resulting list. 
		
		Args:
			image_ids (list(int)): A list of image identifiers.
			batch_size (int): The size of the batch to use. (default: {5})
			offset (int): The offset into the list from where to start processing ids. 
						  (default: {0})
		
		Returns:
			list(tuple): A list of tuples where each tuple contains the attributes of a single
						 image (id, path, quantity, cost).
		"""
		images = list()

		for image_id in image_ids[offset:(offset + batch_size)]:
			image = self.session.query(Image.id, Image.image_path, Image.quantity, Image.cost) \
						        .filter_by(id=image_id).one()
			images.append(image)

		return images

	def get_feature_vectors(self):
		"""Retrieves the feature vectors of all images.
		
		Queries the database for all feature vectors and deserializes them into 
		Tensor objects. 
		
		Returns:
			list((int,Tensor)): A list of pairs of image identifiers and feature vectors.
		"""
		result = self.session.query(Image.id, Image.feature_vector).all()

		transformed_result = list()
		
		for (id, serialized_feature_vector) in result:
			deserialized_tensor = tf.deserialize_feature_vector(serialized_feature_vector)
			transformed_result.append((id, deserialized_tensor))

		return transformed_result

	def close_connection(self):
		"""Ends the session with the database"""
		self.session.close()

