from enum import Enum

class Signal(Enum):
	# binary signals when communicating with server
	SUCCESS = 'SUCCESS' # denotes that some operation was successful
	FAILURE = 'FAILURE' # denotes that some operation failed

	# binary signals about the status of a list being transmitted
	EMPTY = 'EMPTY' # the list is empty, no bytes will be sent/received
	POPULATED = 'POPULATED' # the list has items, bytes will follow

	# for transferring batches of images
	NO_RESULTS = 'NO_RESULTS' # there are no images to be sent
	SEARCH_RESULTS = 'SEARCH_RESULTS' # there are images to be sent

	START_TRANSFER = 'START_TRANSFER' # about to begin the transfer
	CONTINUE_TRANSFER = 'CONTINUE_TRANSFER' # there is another batch to send
	END_TRANSFER = 'END_TRANSFER' # ending the transfer

	START_BATCH = 'START_BATCH' # about to start sending a batch
	CONTINUE_BATCH = 'CONTINUE_BATCH' # sending the next image in the batch
	END_BATCH = 'END_BATCH' # finished sending the batch

