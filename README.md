# shopify-coding-challenge
Summer 2021 - Shopify Developer Intern Coding Challenge

A prototype of an image repository that is managed by a server, which can be manipulated by the provided client application.

## Features

Images can be uploaded by the client to the server where they are saved to disk and recorded into 
the database. 

All communication between the client and server is encrypted and authenticated. 

Users can browse images in the repository by tags (or simply view all images). 

Users can search for images similar to one that they provide (functionality provided by Tensorflow. 

Requested images are served to the client in batches that are displayed one batch at a time in a 
graphical manner, subsequent batches are only sent if the user requests it. 

Basic client side shopping cart functionality (add, update, remove). 

## Setup

* Due to incompatibilities between TensorFlow and newer Python versions, this prototype must be run using Python 3.8.x or lower. It has been developed and tested with Python 3.8.3. Ensure that you have pip3 installed. For certain versions of Python (e.g., 3.6.x, 3.7.x) on macOS you may need to install certificates in order to connect with https, run the ```Install Certificates.command``` executable included in the installation folder. 

* Install the required python packages using pip:

	```pip3 install -r requirements.txt```

* Install [SQLite3](https://www.sqlite.org/download.html).

## Usage

1. First start up the server using:

	```python3 server.py```

	The server takes a moment to initialize, but once it displays ```Listening for connections...``` the client can connect without errors. 

2. In another terminal tab/window start the client: 

	```python3 client.py```

3. The client is implemented using cmd2 and can display the list of available commands using ```?``` or ```help``` and can display further information about any given command using ```? <command_name>``` or ```help <command_name>```. Until a user has logged in there are no commands available for interacting with the image repository.

4. When running the client for the first time you must create a user using ```create_user <username>```, you will be prompted for a password. The username and password will be sent to the server and stored in a database so subsequent uses of the client can just directly login.

5. After a user has been created, use ```login <username>``` to verify your credentials with the server. Now that you have logged in, other commands will become available, you can display the unlocked set of commands using ```help```.

6. You can upload images to the server using ```add_image```. After adding an image you can update the cost and quantity using ```update_image``` or remove the image from the repository using ```delete_image```. Try adding at least 6 images to demo some features. 

7. You can request images from the server using ```browse_by_tags``` and ```search_by_image```. Any images sent by the server will be displayed and you will be able to add items to your cart. 

8. You can use ```view_cart```, ```remove_from_cart```, and ```update_cart``` to interact with your shopping cart. 

9. You can close the client and sever the connection with the server by using ```exit``` or ```ctrl+D (EOF)```. Note that the server will continue to listen for client requests until it itself is killed. 

## Limitations

1. A fixed set of tags has been provided in ```util/enum/tags.py```. The enumerables defined in this file are loaded into the database when the server is launched (when the database is created for the first time). You can modify those tags directly in the enumerable and recreate the database (losing data), or manually edit the database to add new tags. Future work would include the ability to add tags - possibly allowing the client to directly add tags or simply requiring the user to provide a text file of some sort to the server when running it for the first time.  

2. If the client and server experience an error and the protocol being executed that time is interrupted (resulting in a misalignment of messages being send and those being expected to be received), the server will disconnect the client and wait for new connections. The client will have to be restarted in order to re-establish the connection. Future work would include gracefully detecting that the connection was lost and attempting to re-connect to the server. 

3. The server is currently single threaded and can only connect to one client (largely due to the fact that it only uses one secret key). This simplifies the design of the repository itself by not having to worry about threading and race conditions and database transactions or key storage for different clients. Future work would implement support for multiple (potentially simultaneous) clients. 

4. Images can only be searched by similarity or by tag. Other possibilities include searching on file name, but a better solution would be to have the user provide an image name and an image description to be searched. Future work would implement such a change. 

### Future Development Possibilities

1. Access control of users (only owner can modify/remove image, images can be set public/private for browsing/searching).

2. Store encrypted images on disk. 

3. Bulk adds and deletes. 

4. Proper commerce implementation which would communicate with the server to complete orders and decrement stock, etc. 

5. Multiple clients, must have a unique secret key for each client, which could lead to key explosion so consider switching to an asymmetric crypto scheme. 
