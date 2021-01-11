from sqlalchemy import Column, String, Integer, Float, LargeBinary
from .base import Base

class Image(Base):
	__tablename__ = 'image'
	id = Column(Integer, primary_key=True)
	image_path = Column(String, unique=True)
	feature_vector = Column(LargeBinary)
	quantity = Column(Integer)
	cost = Column(Float)

