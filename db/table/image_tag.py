from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint

from .image import Image
from .tag import Tag

from .base import Base

class ImageTag(Base):
	__tablename__ = 'image_tag'

	unused_id = Column(Integer, primary_key=True)

	image_id = Column(Integer, ForeignKey(Image.id))
	tag_id = Column(Integer, ForeignKey(Tag.id))

	UniqueConstraint(image_id, tag_id, name="no_duplicate_tags")

