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
from kik_unofficial.datatypes.xmpp.errors import LoginError

# This bot class handles all the callbacks from the kik client
class EchoBot(KikClientCallback):
    def __init__(self):
        # On initialization, the kik client will attempt to login to kik
        self.client = KikClient(self, "your_kik_username", "your_kik_password", enable_console_logging=True)
        self.client.wait_for_messages()

    # This method is called when the bot receives a direct message from a user
    def on_chat_message_received(self, chat_message: chatting.IncomingChatMessage):
        self.client.send_chat_message(chat_message.from_jid, f'You said "{chat_message.body}"!')
    
    # This method is called if the login fails for any reason including requiring a captcha
    def on_login_error(self, login_error: LoginError):
        if login_error.is_captcha():
            login_error.solve_captcha_wizard(self.client)

if __name__ == '__main__':
    # Creates the bot and start listening for incoming chat messages
    callback = EchoBot()
        
```
Please replace "your_kik_username" and "your_kik_password" with your actual Kik username and password. You also have to add the bot as a friend on Kik before you can send it messages.

You can find a similar example by running `python3 examples/simple_echo_bot.py`. Visit the [examples](examples) directory for more examples.

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
Here's a step-by-step guide to solving a captcha when prompted while running a bot, assuming you're using different browsers and VS Code:

1. **Receive Captcha Prompt:** When your bot starts running, you might receive a message indicating that a captcha needs to be solved. It usually provides a URL to solve the captcha.

2. **Open the URL in a Browser:** Copy the provided URL and paste it into the address bar of your preferred browser (e.g., Chrome, Firefox, Edge).

3. **Access Developer Tools:** Once the page loads, open the developer tools by pressing F12 or right-clicking anywhere on the page and selecting "Inspect" or "Inspect Element."

4. **Navigate to the Network Tab:** Within the developer tools, navigate to the "Network" tab. This tab will display all network activity, including requests and responses made by the webpage.

5. **Solve the Captcha:** Follow the instructions on the webpage to solve the captcha. This might involve identifying objects, entering text, or completing a task to prove you're not a bot.

6. **Find Captcha Response:** After successfully solving the captcha, look for a network request with a URL that includes "captcha-url" in the "Name" or "Path" column.

7. **Copy Response:** Click on the network request corresponding to the captcha response. In the request details, navigate to the "Headers" or "Response" tab and locate the parameter containing your captcha response. It typically starts with "captcha-url?response=" followed by a string of characters.

8. **Paste Response:** Copy the captcha response from the developer tools and paste it into the terminal where your bot is running, typically prompted after the captcha message.

By following these steps, you can successfully solve the captcha and continue running your bot seamlessly.


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
Before investigating the format of certain requests/responses, it's worth checking if they are already documented in the [Message Formats](https://github.com/tomer8007/kik-bot-api-unofficial/blob/new/docs/message_formats.md) page.

## Troubleshooting
If you are on Windows and you are unable to install the `lxml` package, use the binary installers from PyPi [here](https://pypi.python.org/pypi/lxml/3.3.5#downloads).

If you are using [Termux](https://termux.com/), then use `pkg install libxml2 libxslt` to install `lxml` and `pkg install zlib libpng libjpeg-turbo` to install `pillow` dependencies.

## Contact ##
For any questions, suggestions, or discussions about the Kik Bot API, feel free to open an issue on the GitHub repository.
