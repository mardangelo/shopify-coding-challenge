from sqlalchemy import Column, Integer, String

from .base import Base

class Tag(Base):
	__tablename__ = 'tag'

	id = Column(Integer, primary_key=True)
	description = Column(String, unique=True)
