import os
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class Cipher:
	"""Utility class for managing encryption operations
	
	Stores the secret key and performs encryption and decryption operations as needed.

	Caveat: this is a very simplified class. Further, if the system was to be used with
	multiple remote clients, it may be worth considering the use of asymmetric keys to 
	reduce the chance of an attacker acquiring a key and, say, impersonating an administrator
	who could set prices on this hypothetical system. There is a tradeoff however, symmetric 
	cryptography is faster than asymmetric cryptography and if the images being uploaded by 
	this application are large then such tradeoffs must be considered. If a secure element 
	were to be available for key storage it could allow asymmetric cryptography to provide
	the best of both worlds. 

	Note: EAX is used to avoid padding the message and to simplify
	the authentication of the message, but is a two pass approach so it will be 
	slower than other modes. 

	Attributes:
		key (str): Secret key used for encrypting messages. 
	"""

	def __init__(self):
		self.key = None
		self.retrieve_secret_key()

	def create_secret_key(self):
		"""Creates secret key and saves it to a file disk.
		
		Generates a 128 bit AES key and saves it to disk as secret.key
		As this is a symmetrical encryption scheme this key must be 
		shared between the client and the server (securely). 
		"""
		key = os.urandom(16) 

		with open('secret.key', 'wb') as f:
			f.write(key)

		print("Generated secret.key")

		return key

	def retrieve_secret_key(self):
		"""Loads secret key into memory.

		Checks disk for secret key and loads into memory. If the secret key 
		does not exist, it is generated. 
		""" 

		if os.path.isfile('secret.key'):
			with open('secret.key', 'rb') as f:
				self.key = f.read(16)
		else:
			self.key = self.create_secret_key()

	def encrypt(self, message):
		"""Encrypts given message using secret key.
		
		Encrypts the message using AES128-EAX authenticated encryption.
		Simulatenously provides authentication and privacy of message. 
		Support messages of arbitrary length (i.e., no padding required).
		
		Args:
			message (bytes): Data to be encrypted.

		Returns:
			bytes: Ciphertext of the encrypted data.
			bytes: Tag used to authenticate the ciphertext.
			bytes: Number used only once, typically used to prevent replay attacks.
		"""

		cipher = AES.new(self.key, AES.MODE_EAX)
		(ciphertext, tag) = cipher.encrypt_and_digest(message)

		return (ciphertext, tag, cipher.nonce)

	def decrypt(self, ciphertext, tag, nonce):
		"""Decrypts the given ciphertext using secret key. 
		
		Decrypts and verifies the ciphertext using AES128-EAX authenticated encryption.
		
		Args:
			ciphertext (bytes): Result of encrypting some data with secret key. 
			tag (bytes): Authentication tag used to verify data has not been tampered with. 
			nonce (bytes): Number used only once, typically used to prevent replay attacks.

		Returns:
			bytes: Plaintext of the decrypted data.
		"""

		cipher = AES.new(self.key, AES.MODE_EAX, nonce)
		message = cipher.decrypt_and_verify(ciphertext, tag)

		return message

if __name__ == '__main__':
	cipher = Cipher()

	# test encryption and decryption using text message 
	original_message = "testing!"
	(ciphertext, tag, nonce) = cipher.encrypt(original_message.encode('utf8'))
	decrypted_message = cipher.decrypt(ciphertext, tag, nonce).decode('utf8')
	assert(original_message == decrypted_message)

	# test encryption and decryption using an image 
	with open("shopify.png", 'rb') as image_file:
		original_image = base64.b64encode(image_file.read())

		(ciphertext, tag, nonce) = cipher.encrypt(original_image)
		decrypted_image = cipher.decrypt(ciphertext, tag, nonce).decode('utf8')
		assert(original_image == decrypted_image)


