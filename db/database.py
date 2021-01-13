from pathlib import Path

from sqlalchemy import create_engine, MetaData
from sqlalchemy.sql import exists
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

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
		engine = create_engine('sqlite:///image-repository.sqlite', echo=True)

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

	#TODO: ponder whether the best comparison would be feature vector or path? what is the
	#	   likelihood of a feature vector being repeated?
	def add_image(self, path, feature_vector, quantity, cost, username):
		"""Adds an image to the repository. 
		
		Stores information about the image as well as a path to the image file. If an image
		by the same name already exists in the database it is not added again. 
		
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

		color_print("Image successfully added to database", color='blue')

		return image.id

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

	#TODO: do some error checking if the image id isn't valid for whatever reason?
	def get_image_attributes(self, image_id):
		"""Retrieves information about an image given its id.
		
		Queries the database for the path of the image, the amount in stock, and the cost.
		
		Args:
			image_id (int): The database identifier of the image.

		Returns:
			str: The path to the image on disk.
			int: The number of items in stock.
			float: The cost of each individual item.
		"""
		(result, ) = self.session.query(Image.image_path, Image.quantity, Image.cost).filter(Image.id == image_id)

		path = Path(result[0])
		quantity = result[1]
		cost = round(result[2], 2)

		return (path, quantity, cost)

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

