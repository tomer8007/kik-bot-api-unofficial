import time
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
import kik_unofficial.datatypes.xmpp.chatting as chatting
from kik_unofficial.datatypes.xmpp.errors import LoginError

# Your kik login credentials (username and password)
username = "your_kik_username"
password = "your_kik_password"

# This bot class handles all the callbacks from the kik client
class EchoBot(KikClientCallback):
    def __init__(self):
        self.client = KikClient(self, username, password, logging=True)
        self.client.wait_for_messages()
        
    # This method is called when the bot is fully logged in and setup
    def on_authenticated(self):
        self.client.request_roster() # request list of chat partners

    # This method is called when the bot receives a direct message (chat message)
    def on_chat_message_received(self, chat_message: chatting.IncomingChatMessage):
        self.client.send_chat_message(chat_message.from_jid, f'You said "{chat_message.body}"!')
    
    # This method is called when the bot receives a chat message in a group
    def on_group_message_received(self, chat_message: chatting.IncomingGroupChatMessage):
        self.client.send_chat_message(chat_message.group_jid, f'You said "{chat_message.body}"!')
    
    # This method is called if a captcha is required to login
    def on_login_error(self, login_error: LoginError):
        if login_error.is_captcha():
            login_error.solve_captcha_wizard(self.client)


if __name__ == '__main__':
    # Creates the bot and start listening for incoming chat messages
    callback = EchoBot()
    