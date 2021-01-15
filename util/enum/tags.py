from enum import IntEnum, auto

from lazyme import color_str

class Tags(IntEnum):
	# clothing categories
	clothing_accessories = auto()
	footwear = auto()
	accessories_and_jewelry = auto()
	handbags_and_luggage = auto()
	mens_clothing = auto()
	womens_clothing = auto()

	# consumer electronics
	audio_equipment = auto()
	camera_equipment = auto()
	car_and_gps = auto()
	computer_accessories = auto()
	desktop_computers_and_monitors = auto()
	laptops_and_notebooks = auto()
	smartphones = auto()
	tablets_and_ereaders = auto()
	televisions = auto()
	video_games_and_consoles = auto()
	wearables = auto()

	@classmethod
	def display_tags_for_selection(cls):
		for tag_enum in cls:
			tag_id = color_str("[%d] " % tag_enum.value, color='cyan')
			tag_name = color_str("%s" % tag_enum.name, color='blue')

			print(tag_id + tag_name)