# Kik Bot API #
The Unofficial Kik Bot API is a Python library developed to automate interactions on [Kik Messenger](https://www.kik.com).

It's essentially a way to create bots that behave like humans on the platform. This library enables your bot to interact with the official Kik app by emulating a real smartphone client. It communicates with Kik's servers at `talk1110an.kik.com:5223` over a modified version of the [XMPP](https://xmpp.org/about/technology-overview.html) protocol.

This library is ideal for developers, hobbyists, and businesses who want to build automated bots to interact with users, groups, and other bots on Kik.

We do not endorse the use of this library for spamming or other malicious purposes. Please use this library responsibly.

## Installation and dependencies ##
Make sure you have Python 3.8 or above installed on your system. You can install this library directly from GitHub:
```
git clone -b new https://github.com/tomer8007/kik-bot-api-unofficial
pip3 install ./kik-bot-api-unofficial
```
## Quick Start Guide ##
Here's a simple example of how to use the Kik Bot API:

```python
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
import kik_unofficial.datatypes.xmpp.chatting as chatting

# Your kik login credentials (username and password)
username = "your_kik_username"
password = "your_kik_password"

# This bot class handles all the callbacks from the kik client
class EchoBot(KikClientCallback):
    def __init__(self):
        self.client = KikClient(self, username, password)
        self.client.wait_for_messages()

    def on_authenticated(self):
        self.client.request_roster() # request list of chat partners

    def on_chat_message_received(self, chat_message: chatting.IncomingChatMessage):
        self.client.send_chat_message(chat_message.from_jid, f'You said "{chat_message.body}"!')
    
if __name__ == '__main__':
    # Creates the bot and start listening for incoming chat messages
    callback = EchoBot()
    client = KikClient(callback=callback, kik_username=username, kik_password=password)
    client.wait_for_messages()
        
```
Please replace "your_kik_username" and "your_kik_password" with your actual Kik username and password.

You can run this example by running `python3 examples/simple_echo_bot.py`. Visit the [examples](examples) directory for more examples.

## Features ##
With the Kik Bot API, you can:

- Log in with kik username and password, retrieve user information (such as email, name, etc).
- Fetch chat partners information
- Send text messages to users/groups and listen for incoming messages
- Send and receive 'is-typing' status
- Send and receive read receipts
- Fetch group information (name, participants, etc.)
- Fetch past message history
- Administer groups (add, remove or ban members, etc)
- Search for groups and join them (experimental feature)
- Receive media content: camera, gallery, stickers
- Add a kik user as a friend
- Send images (including GIFs, using a [Tenor](https://developers.google.com/tenor/guides/quickstart) API key)

Sending videos or recordings is not supported yet.

## Captcha Solving ##
Once the bot starts running, you might see a message like this:
`To continue, complete the captcha in this URL using a browser: https://captcha.kik.com/?id=...`


This means that Kik has detected that you are using a bot and requires you to solve a captcha to continue. You can solve the captcha by opening the URL in a browser and following these steps:

- Press F12 to open the developer tools
- Open the network tab
- Solve the captcha
- Look for a file header that starts with `captcha-url?response=[your captcha response]`
- Click on it and copy the response from the response tab
- Paste the response in the terminal where the bot is running


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
    docker compose up --build -d && docker attach kik-bot-api-unofficial
    ```
    <sub>**Note**: You only need to use `--build` when you first clone the repo, or if you make changes to the code.</sub>

## More functionality
Before investigating the format of certain requests/responses, it's worth checking if they are already documented in the [Message Formats](https://github.com/tomer8007/kik-bot-api-unofficial/wiki/Message-Formats) wiki page.

## Troubleshooting
If you are on Windows and you are unable to install the `lxml` package, use the binary installers from PyPi [here](https://pypi.python.org/pypi/lxml/3.3.5#downloads).

If you are using [Termux](https://termux.com/), then use `pkg install libxml2 libxslt` to install `lxml` and `pkg install zlib libpng libjpeg-turbo` to install `pillow` dependencies.

## Contact ##
For any questions, suggestions, or discussions about the Kik Bot API, feel free to open an issue on the GitHub repository.