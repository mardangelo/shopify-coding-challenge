"""Methods enabling image similarity computations via Spotify's Annoy.

This helper can compute feature vectors for images and provides serialization
and deserialization methods so that the vectors can be computed once per image 
and stored directly into the database. These vectors can then be used to find 
the most similar images (i.e., the nearest neigbours). 

Note: Feature vectors are computing using Google's MobileNet model from TensorflowHub.
	  Image similarity is determined by creating a forest of feature vectors using 
	  Spotify's Annoy and finding the nearest neighbours. 

Caveat: This implementation works at the level of an entire image and does not provide 
		good results if the backgrounds for the images are different, even if the 
		objects are similar. That being said, it was chosen for this prototype based
		on the assuming that product images will typically appear on a transparent 
		or white background rather than products being used in real settings. 


Attributes:
	module (Module): MobileNet Tensorflow module for computing feature vectors.

	RESIZE_DIMENSIONS (int): Dimensions of the resized image when preprocessing.
	COLOUR_CHANNELS (int): Number of colour channels used to represent the image.

	FEATURE_VECTOR_DIMENSIONS (int): Size of the feature vector.
	N_NEAREST_NEIGHBOURS (int): The number of nearest neighbours to find.
	NUM_TREES (int): The number of trees to populate the Annoy forest with. More 
					 trees improves precision when querying.
"""

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from annoy import AnnoyIndex

import tensorflow as tf
import tensorflow_hub as hub

module_handle = "https://tfhub.dev/google/imagenet/mobilenet_v2_140_224/feature_vector/4"
module = hub.load(module_handle)

RESIZE_DIMENSIONS = 224
COLOUR_CHANNELS = 3

FEATURE_VECTOR_DIMENSIONS = 1792
N_NEAREST_NEIGHBOURS = 20
NUM_TREES = 10000

def preprocess_image(path):
	"""Converts an image to a tensor representation (for use with Tensorflow). 
	
	Given the path to an image, a tensor is created, resized, and represented as floats. 
	
	Args:
		path (str): Path to an image file.
	
	Returns:
		Tensor: Representation of a portion of the image (e.g., 224 x 224 x 3).
	"""
	tf_image = tf.io.read_file(path)

	# Converts the image bytes into a tensor with given colour channels (e.g., W x H x 3).
	tf_image = tf.io.decode_image(tf_image, channels=COLOUR_CHANNELS)

	# Resizes (optionally pads) the image so all images are compared at a uniform size (e.g., 224 x 224 x 3).
	tf_image = tf.image.resize_with_pad(tf_image, RESIZE_DIMENSIONS, RESIZE_DIMENSIONS)

	# Converts the image values to floats (instead of integers).
	tf_image = tf.image.convert_image_dtype(tf_image, tf.float32)[tf.newaxis, ...]

	return tf_image

def calculate_feature_vector(path):
	"""Computes a feature vector for a given image.
	
	Given the path to an image, creates a tensor for the image and applies the 
	tensorflow hub feature vector calculation module. 
	
	Args:
		path (str): Path to an image file.
	
	Returns:
		Tensor: Representation of the feature vector (1 x 1792).
	"""
	tf_image = preprocess_image(path)
	return module(tf_image)

def serialize_feature_vector(feature_tensor):
	"""Serializes a feature tensor into bytes.
	
	Given a tensor for the feature vector, converts it to a byte representation.
	
	Args:
		feature_tensor (Tensor): Feature vector in tensor format. 
	
	Returns:
		bytes: A bytes object representing the feature tensor. 
	"""
	tf_features = tf.make_tensor_proto(feature_tensor)

	# Despite the fact that the function name suggests the result to be a string, 
	# the result is actually of type bytes (but bytes are strings in python3, so...?)
	return tf_features.SerializeToString()

def deserialize_feature_vector(serialized_tensor):
	"""Deserializes bytes into a feature tensor. 
	
	Given a sequence of bytes, converts them into a tensor for the feature vector. 
	
	Args:
		serialized_tensor (bytes): Byte representation of the feature tensor. 
	
	Returns:
		Tensor: Representation of the feature vector (1 x 1792).
	"""
	return tf.io.parse_tensor(serialized_tensor, tf.float32)

def compute_nearest_neighbours(source_tensor, feature_tensors):
	"""Calculates the items most similar to the given item.
	
	Uses Annoy to construct a forest for the feature vectors provided and determines 
	the nearest neighbours to the provided source vector (e.g., a reference image).
	
	Args:
		source_tensor (Tensor): A feature tensor representing the reference image.
		feature_tensors (list): List of identifier, feature tensor pairs.
	
	Returns:
		list(int): An ordered list of identifiers where the identifiers of the most  
			  	   similar images to the reference image appear first. 
	"""
	# create an index and stores vectors with given dimensions
	t = AnnoyIndex(FEATURE_VECTOR_DIMENSIONS, metric='angular')

	# add the existing feature vectors and their identifiers to the index
	for (id, feature_vector) in feature_tensors:
		t.add_item(id, feature_vector[0])

	# builds a forest of trees, more trees gives higher precision when querying
	t.build(NUM_TREES)

	# calculates the nearest neighbours to the source tensor in the forest
	neighbour_ids = t.get_nns_by_vector(source_tensor[0], N_NEAREST_NEIGHBOURS)

	return neighbour_ids
