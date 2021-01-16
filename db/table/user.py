from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from .base import Base

class User(Base):
	__tablename__ = 'user'
	
	id = Column(Integer, primary_key=True)
	username = Column(String, unique=True)
	password = Column(String)

	user_images = relationship("Image", cascade="all, delete")