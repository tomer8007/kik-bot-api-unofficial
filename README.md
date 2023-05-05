# Kik Bot API #
Use this library to develop bots for [Kik Messenger](https://www.kik.com) that are essentially automated humans.

It basically lets you do the same things as the official Kik app by pretending to be a real smartphone client; It communicates with Kik's servers at `talk1110an.kik.com:5223` over a modified version of the [XMPP](https://xmpp.org/about/technology-overview.html) protocol.

This is the new branch of this project and is recommended.
## Installation and dependencies ##
First, make sure you are using **Python 3.6+**, not python 2.7. Second, just install it directly from GitHub:
```
git clone -b new https://github.com/tomer8007/kik-bot-api-unofficial
pip3 install ./kik-bot-api-unofficial
```
## Usage ##
Examples are a great way to understand things. A good place to start is the `examples/` directory. 

It is as simple as:
```python
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
import kik_unofficial.datatypes.xmpp.chatting as chatting

class EchoBot(KikClientCallback):
    def __init__(self):
        self.client = KikClient(self, "your_kik_username", "your_kik_password")

    def on_authenticated(self):
        self.client.request_roster() # request list of chat partners

    def on_chat_message_received(self, chat_message: chatting.IncomingChatMessage):
        self.client.send_chat_message(chat_message.from_jid, 'You said "{}"!'.format(chat_message.body))
```

### Docker ###
After creating a bot, you can bootstrap it to run in a Docker container. This section assumes you have [Docker](https://docs.docker.com/get-docker/) installed on your system.

1. Set up your environment variables. Copy the example file to a new file called `.env`:
    ```shell
    cp .env.example .env
    ```
    <sub>**Note:** You will need to edit the new `.env` file to include your bot's device ID, android ID, username, password, and JID (if you know it).</sub>

2. Update the [Dockerfile](Dockerfile) to copy your `bot.py` file into the container. Change the following line like so:
   ```diff
   - COPY examples/echo_bot.py /app/bot.py
   + COPY path/to/your/bot.py /app/bot.py
   ```
   <sub>**Note:** You can also copy your bot's dependencies into the container by adding a `COPY` line for each dependency.</sub>

3. Deploy the container:
    ```shell
    docker compose up --build
    ```
    <sub>**Note**: You only need to use `--build` when you first clone the repo, or if you make changes to the code.</sub>

Currently Supported Operations:
- Log in with kik username and password, retrieve user information (such as email, name, etc).
- Fetch chat partners information
- Send text messages to users/groups and listen for incoming messages
- Send and receive 'is-typing' status
- Send and receive read receipts
- Fetch group information (name, participants, etc.)
- Fetch past message history
- Admin groups (add, remove or ban members, etc)
- Search for groups and join them [Experimental]
- Receive media content: camera, gallery, stickers
- Add a kik user as a friend
- Send images (including GIFs, using a [Tenor](https://tenor.com/gifapi) API key)

Sending videos or recordings is not supported yet.

## More functionality
Before investigating the format of certain requests/responses, it's worth checking if they are already documented in the [Message Formats](https://github.com/tomer8007/kik-bot-api-unofficial/wiki/Message-Formats) wiki page.

## Troubleshooting
If you are on Windows and you are unable to install the `lxml` package, use the binary installers from PyPi [here](https://pypi.python.org/pypi/lxml/3.3.5#downloads).

If you are using [Termux](https://termux.com/), then use `pkg install libxml2 libxslt` to install `lxml` and `pkg install zlib libpng libjpeg-turbo` to install `pillow` dependencies.
