from sqlalchemy import create_engine, MetaData
from sqlalchemy.sql import exists
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from lazyme.string import color_print

from passlib.hash import pbkdf2_sha256

from .table.user import User
from .table.base import Base

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
		if user_exists[0] == True:
			color_print("Username %s is already in use" % username, color='red')
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
		user_info = self.session.query(User).filter(User.username == username).one()
		return pbkdf2_sha256.verify(password, user_info.password)

