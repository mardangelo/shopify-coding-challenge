import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class Cipher:
	"""Utility class for managing encryption operations
	
	Stores the secret key and performs encryption and decryption operations as needed.

	Caveat: this is a very simplified class. It merely ensures the confidentiality of 
	data, but does not ensure authenticity (HMACs could be used to do so). Secret keys
	are stored with the code itself in order to demonstrate the functionality, but should
	be securely stored if used for a real system. Further, if the system was to be used with
	multiple remote clients, it may be worth considering the use of asymmetric keys to 
	reduce the chance of an attacker acquiring a key and, say, impersonating an administrator
	who could set prices on this hypothetical system. There is a tradeoff however, symmetric 
	cryptography is faster than asymmetric cryptography and if the images being uploaded by 
	this application are large then such tradeoffs must be considered. If a secure element 
	were to be available for key storage it could allow asymmetric cryptography to provide
	the best of both worlds. 
	"""

	key = ''

	def __init__(self):
		self.retrieve_secret_key()

	def create_secret_key(self):
		"""Creates secret key and saves to file
		
		Generates a 256 bit AES key and saves it to disk as secret.key
		"""
		key = os.urandom(32) 

		with open('secret.key', 'wb') as f:
			f.write(key)

		print("Generated secret key %s" % key.hex())

		return key

	def retrieve_secret_key(self):
		"""Loads secret key into memory

		Checks disk for secret key and loads into memory. If the secret key 
		does not exist, it is generated. 
		""" 

		if os.path.isfile('secret.key'):
			with open('secret.key', 'rb') as f:
				self.key = f.read(32)
		else:
			self.key = self.create_secret_key()

		print("Retrieved secret key %s" % self.key.hex())

	def encrypt(self, message):
		"""Encrypts given message using secret key
		
		Encrypts the message using AES256-CBC encryption.
		
		Arguments:
			message {str} -- Text to be encrypted

		Returns:

		""" 

		iv = get_random_bytes(AES.block_size)
		padded_message = self.pad_message(message.encode('utf8'))

		encrypter = AES.new(self.key, AES.MODE_CBC, iv)
		ciphertext = encrypter.encrypt(padded_message)

		print(type(ciphertext))
		print(type(iv))

		return (ciphertext, iv)

	def pad_message(self, message):
		if len(message) % AES.block_size == 0:
			return message

		# TODO: figure out the padding issue with AES256-CBC and get the encryption and 
		# decryption working, then start using all of this to send messages between the client and server



if __name__ == '__main__':
	cipher = Cipher()
	cipher.retrieve_secret_key()

	cipher.encrypt("testing!")