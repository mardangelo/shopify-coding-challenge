from sqlalchemy import Column, String, Integer, Float, LargeBinary
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

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

	image_tags = relationship("ImageTag", cascade="all, delete")