from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .base import Base

class Tag(Base):
	__tablename__ = 'tag'

	id = Column(Integer, primary_key=True)
	description = Column(String, unique=True)

	image_tags = relationship("ImageTag", cascade="all, delete")
