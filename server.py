#!/usr/bin/env python3

import socket
from util.cipher import Cipher

HOST = '127.0.0.1'
PORT = 65432
ACK = 'ack'.encode('utf8')

cipher = Cipher()

# use IPv4 and TCP
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	s.bind((HOST, PORT))
	s.listen()

	(conn, addr) = s.accept()

	with conn:
		print("Connected to by ", addr)

		while True:
			length = conn.recv(32)
			if not length:
				break

			# Of the three pieces of information sent, only the ciphertext is variable
			# length so we determine its length before attempting to receive it 
			ciphertext_length = int.from_bytes(length, byteorder='big')

			conn.sendall(ACK)

			ciphertext = conn.recv(ciphertext_length)
			if not ciphertext:
				break

			conn.sendall(ACK)

			tag = conn.recv(16)
			if not tag:
				break

			conn.sendall(ACK)

			nonce = conn.recv(16)
			if not nonce:
				break

			conn.sendall(ACK)

			data = cipher.decrypt(ciphertext, tag, nonce)

			print(data.decode('utf8'))

