from sqlalchemy import Column, String, Integer, Float, LargeBinary
from sqlalchemy import ForeignKey, UniqueConstraint

from .user import User

from .base import Base

class Image(Base):
	__tablename__ = 'image'
	
	id = Column(Integer, primary_key=True)
	image_path = Column(String, unique=True)
	feature_vector = Column(LargeBinary)
	quantity = Column(Integer)
	cost = Column(Float)
	seller = Column(Integer, ForeignKey(User.id))

	#TODO: instead of forcing a unique filename, one might enforce that the feature vector
	# 	   filename combination must be unique. Features vectors aren't guaranteed to be 
	# 	   unique since they are a reduction in the dimensionality of the image, but the 
	# 	   likelihood that someone may find such a collision and name the file the same way
	# 	   seems acceptable. Plus they would see a message about the filename and they 
	# 	   could change that and re-upload. To use this would need to come up with an file 
	# 	   renaming scheme.
	#UniqueConstraint(image_path, feature_vector, name='unique_images')
