from sqlalchemy import Column, String, Integer
from .base import Base

class User(Base):
	__tablename__ = 'user'
	id = Column(Integer, primary_key=True)
	username = Column(String, unique=True)
	password = Column(String)