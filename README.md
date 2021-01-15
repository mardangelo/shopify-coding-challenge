# shopify-coding-challenge
Summer 2021 - Shopify Developer Intern Coding Challenge

A prototype of an image repository that is managed by a server, which can be manipulated by the provided client application.

## Features

Images can be uploaded by the client to the server where they are saved to disk and recorded into 
the database. 

All encryption between the client and server is encrypted and authenticated. 

Users can browse images in the repository by tags (or simply view all images). Users can also search for images similar to one that they provide. 

Requested images are served to the client in batches that are displayed one batch at a time in a 
graphical manner, subsequent batches are only sent if the user requests it. 

Basic client side shopping cart functionality (add, update, remove). 

## Setup

* Due to incompatibilities between TensorFlow and newer Python versions, this prototype must be run using Python 3.8.x or lower. It has been developed and tested with Python 3.8.3. Ensure that you have pip3 installed.

* Install the required python packages using pip:

	```pip3 install -r requirements.txt```

* Install [SQLite3](https://www.sqlite.org/download.html).

## Usage

1. First start up the server using:

	```python3 server.py```

	The server takes a moment to initialize, but once it displays ```Listening for connections...``` the client can connect without errors. 

2. In another terminal tab/window start the client: 

	```python3 client.py```

3. The client is implemented using cmd2 and can display the list of available commands using ```?``` and can display further information about any given command ```help <command_name>```.

### TODOs

Create a sample database with colours as tags and simple images like logos (maybe modify server so it can be modified using a script?)
