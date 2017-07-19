# Kik Bot API #
Use this library to develop bots for [Kik Messenger](https://www.kik.com) that are essentially automated humans.

It basically lets you do the same things as the offical Kik app by pretending to be a real smartphone client: It communicates with Kik's servers at `talk1110an.kik.com:5223` over a modified version of the [XMPP](https://xmpp.org/about/technology-overview.html) protocol.
## Installation and dependencies ##
First, make sure you are using **Python 3.4**, not python 2.7.
Second, just clone it with `git`:
```
git clone https://github.com/tomer8007/kik-bot-api-unofficial
```
And install with `pip`:
```
pip3 install ./kik-bot-unofficial-api
```
## Usage ##
An example is worth a thoursand words. a good place to start is the `examples/` directory. 

It is as simple as:
```python
from kik_unofficial.kikclient import KikClient
username, password = "your_kik_username", "your_kik_password"
kik = KikClient(username, password)
kik.send_message("other_kik_username", "Hello from bot!")
```
Currently Supported Operations:
- Log in with kik username and password, retrieve user information (such as email, name, etc).
- Fetch chat partners information
- Send text messages to users\groups and listen for incoming messages
- Send and receive 'is-typing' status
- Send and receive read receipts
- Fetch group information (name, participants, etc.)
- Receive media content: camera, gallery, stickets
- Add a kik user as a friend

Sending multimedia (images, videos) is not suported yet.

## Troubleshooting
If you are on Windows and you are unable to install the lxml pacakge, use the binary installers from PyPi [here](https://pypi.python.org/pypi/lxml/3.3.5#downloads).
