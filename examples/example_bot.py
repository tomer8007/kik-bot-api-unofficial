#!/usr/bin/env python3
"""
A Kik bot that just logs every event that it gets (new message, message read, etc.),
and will send an image in PM if you say image and show a ping response in PM if you say Ping
"""
import argparse
import json
import time
from typing import Union
import os

import kik_unofficial.datatypes.xmpp.chatting as chatting
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.account import GetMyProfileResponse
from kik_unofficial.datatypes.xmpp.chatting import KikPongResponse, IncomingGifMessage
from kik_unofficial.datatypes.xmpp.errors import SignUpError, LoginError, ServiceRequestError
from kik_unofficial.datatypes.xmpp.history import HistoryResponse
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeersInfoResponse, GroupSearchResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, UsernameUniquenessResponse
from kik_unofficial.datatypes.xmpp.login import LoginResponse, ConnectionFailedResponse, TempBanElement
from kik_unofficial.datatypes.xmpp.xiphias import UsersResponse, UsersByAliasResponse


def main():
    # The credentials file where you store the bot's login information
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--creds', default='creds.json', help='Path to credentials file')
    args = parser.parse_args()

    # Changes the current working directory to /examples
    if not os.path.isfile(args.creds):
        print("Can't find credentials file.")
        return

    # load the bot's credentials from creds.json
    with open(args.creds, "r") as f:
        creds = json.load(f)

    # create the bot
    bot = ExampleBot(creds)


class ExampleBot(KikClientCallback):
    def __init__(self, creds: dict):
        self.bot_display_name = None
        self.pong_list = []

        username = creds['username']
        password = creds.get('password') or input("Enter your password: ")

        # optional parameters
        device_id = creds['device_id']
        android_id = creds['android_id']
        node = creds.get('node')  # If you don't know it, set it to None

        self.client = KikClient(self, username, str(password), node, device_id=device_id, android_id=android_id, logger_name="example_bot",
                                log_file_path="var/example_bot.log", log_level=1)

        # Utilize the APIs Logging for bot
        self.log = self.client.log

        self.client.wait_for_messages()

    # --------------------------------------------
    #  API - Login/Authentication Event Listeners
    # --------------------------------------------
    def on_authenticated(self):
        self.log.info('Authenticated')
        self.client.request_roster()

    def on_login_ended(self, response: LoginResponse):
        self.log.info(f'Full name: {response.first_name} {response.last_name}')
        self.bot_display_name = response.first_name + " " + response.last_name

    # ------------------------------------
    #  API - Private Message Event Listeners
    # ------------------------------------

    # Listener for Private Messages
    def on_chat_message_received(self, chat_message: chatting.IncomingChatMessage):
        pm = chat_message.body.lower()
        if pm == "image":
            self.client.send_chat_image(chat_message.from_jid, "var/test_image.png")
        elif pm == "gifr":
            self.client.send_gif_image(chat_message.from_jid, "robot", API_key="", random_gif=True)
        elif pm == "gif":
            self.client.send_gif_image(chat_message.from_jid, "robot", API_key="", random_gif=False)
        elif pm == "gifs":
            self.client.send_saved_gif_image(chat_message.from_jid, "var/test_gif.json")
        elif pm == "video":
            self.client.send_video_message(chat_message.from_jid, "var/test_video.mp4", auto_play=True, looping=True)
        elif pm == "ping":
            self.pong_list.append((time.time(), chat_message.from_jid))
            self.client.send_ping()
        else:
            self.log.info(f"'{chat_message.from_jid}' says: {chat_message.body}")
            self.log.info("Replaying.")
            self.client.send_chat_message(chat_message.from_jid, "You said \"" + chat_message.body + "\"!")

    # Listener for Is Typing in PM
    def on_is_typing_event_received(self, response: chatting.IncomingIsTypingEvent):
        if not response.is_typing:
            self.log.debug(f'{response.from_jid} is now not typing.')
        else:
            self.log.debug(f'{response.from_jid} is now typing.')

    # Listener for Message Delivered for PM
    def on_message_delivered(self, response: chatting.IncomingMessageDeliveredEvent):
        self.log.debug(f'Chat message with ID {response.message_id} is delivered.')

    # Listener for Message Read for PM
    def on_message_read(self, response: chatting.IncomingMessageReadEvent):
        self.log.debug(f'Human has read the message with ID {response.message_id}.')

    # ------------------------------------
    #  API - Group Event Listeners
    # ------------------------------------

    # Listener for Group Message Read/Delivered
    def on_group_receipts_received(self, response: chatting.IncomingGroupReceiptsEvent):
        self.log.debug(f'Message with ID {response.message_id} has been {response.type}.')

    # Listener for Group Message Received.
    def on_group_message_received(self, chat_message: chatting.IncomingGroupChatMessage):
        self.log.info(f"'{chat_message.from_jid}' from group ID {chat_message.group_jid} says: {chat_message.body}")

    # Listener for Group Typing Events
    def on_group_is_typing_event_received(self, response: chatting.IncomingGroupIsTypingEvent):
        if not response.is_typing:
            self.log.debug(f'{response.from_jid} is now not typing in group {response.group_jid}.')
        else:
            self.log.debug(f'{response.from_jid} is now typing in group {response.group_jid}.')

    # Listener for when a group Status Message as been received.
    def on_group_status_received(self, response: chatting.IncomingGroupStatus):
        self.log.info(f"Status message in {response.group_jid}: {response.status}")

    # Listener for when a group System Message as been received.
    def on_group_sysmsg_received(self, response: chatting.IncomingGroupSysmsg):
        self.log.info(f"System message in {response.group_jid}: {response.sysmsg}")

    # ------------------------------------
    #  API - Media Event Listeners
    # ------------------------------------

    # Listener for when Image received from group or PM
    def on_image_received(self, image_message: chatting.IncomingImageMessage):
        if not image_message.group_jid:
            self.log.info(f"PM Image message was received from {image_message.from_jid}")
        else:
            self.log.info(f"Group Image message was received from {image_message.from_jid}")

    # Listener for when Video received, group or PM
    def on_video_received(self, response: chatting.IncomingVideoMessage):
        if not response.group_jid:
            self.log.info(f"PM Video message was received from {response.video_url}")
        else:
            self.log.info(f"Group Video message was received from {response.group_jid}")

    # Listener for when GIF received, group or PM
    def on_gif_received(self, response: IncomingGifMessage):
        if not response.group_jid:
            self.log.info(f"PM GIF message was received from {response.from_jid}")
        else:
            self.log.info(f"Group GIF message was received from {response.group_jid}")

    # Listener for when Card received, group or PM
    def on_card_received(self, response: chatting.IncomingCardMessage):
        if not response.group_jid:
            self.log.info(f"PM Card message was received from {response.from_jid}")
        else:
            self.log.info(f"Group Card message was received from {response.group_jid}")

    # Listener for when Sticker received, group or PM
    def on_group_sticker(self, response: chatting.IncomingGroupSticker):
        if not response.group_jid:
            self.log.info(f"PM Sticker message was received from {response.from_jid}")
        else:
            self.log.info(f"Group Sticker message was received from {response.group_jid}")

    # ------------------------------------
    #  API - Peer Info Event Listeners
    # ------------------------------------

    # Listener for when Peer Info received.
    def on_peer_info_received(self, response: PeersInfoResponse):
        users = '\n'.join([str(member) for member in response.users])
        self.log.info(f'Peer info: {users}')

    # Listener for when Peer Info received through Xiphias request.
    def on_xiphias_get_users_response(self, response: Union[UsersResponse, UsersByAliasResponse]):
        users = '\n'.join([str(member) for member in response.users])
        self.log.info(f'Peer info: {users}')

    # ------------------------------------
    #  API - Misc Event Listeners
    # ------------------------------------

    def on_status_message_received(self, response: chatting.IncomingStatusResponse):
        self.log.info(f'Status message from {response.from_jid}: {response.status}.')

    def on_message_history_response(self, response: HistoryResponse):
        self.log.info(f'Message History Response: {response.messages}.')

    def on_get_my_profile_response(self, response: GetMyProfileResponse):
        profile_message = "+++ Bot Profile +++\n"
        profile_message += f"Username - {response.username}\n"
        profile_message += f"Display Name - {response.first_name} {response.last_name}\n"
        profile_message += f"Email - {response.email}\n"
        profile_message += f"Profile Pic URL - {response.pic_url}"
        self.log.info(f"Profile Response:\n {profile_message}")

    def on_username_uniqueness_received(self, response: UsernameUniquenessResponse):
        self.log.info(f'Is {response.username} a unique username? {response.unique}.')

    def on_sign_up_ended(self, response: RegisterResponse):
        self.log.info(f'Is Registered as {response.kik_node}.')

    # Listener for when group search is received.
    def on_group_search_response(self, response: GroupSearchResponse):
        self.log.info(f'Search Response: {response.groups}.')

    def on_pong(self, response: KikPongResponse):
        if len(self.pong_list) >= 1:
            self.client.send_chat_message(self.pong_list[0][1],
                                          f"Pong Received Took {round((response.received_time - self.pong_list[0][0]) * 1000, 2)} ms")
            self.pong_list.pop()

        self.log.info(f'Pong returned: {response.received_time}')

    def on_roster_received(self, response: FetchRosterResponse):
        groups = []
        users = []
        for peer in response.peers:
            if "groups.kik.com" in peer.jid:
                groups.append(peer.jid)
            else:
                users.append(peer.jid)

        user_text = '\n'.join([str(us) for us in users])
        group_text = '\n'.join([str(gr) for gr in groups])
        partner_count = len(response.peers)
        self.log.info(
            f'Roster Recieved\nTotal Peers: {str(partner_count)}\n Groups:\n{group_text}\nUsers:\n{user_text}\n')

    # Listener for friend attributions
    def on_friend_attribution(self, response: chatting.IncomingFriendAttribution):
        self.log.info(f'Friend Request From: {response.referrer_jid}.')

    # ------------------------------------
    #  API - Error Event Listeners
    # ------------------------------------

    def on_service_request_error(self, response: ServiceRequestError):
        self.log.warning(f'Service request error: {response.error_code} {response.message_id}.')

    def on_connection_failed(self, response: ConnectionFailedResponse):
        self.log.error(f'Connection failed: {response.message}.')

    def on_login_error(self, login_error: LoginError):
        self.log.error(f'Login failed: {login_error.error_code}, {login_error.error_messages}.')

        if login_error.is_captcha():
            login_error.solve_captcha_wizard(self.client)

    def on_temp_ban_received(self, response: TempBanElement):
        self.log.error(f'Temporary Ban: {response.ban_title}, {response.ban_message}\nEnds: {response.ban_end_time}.')

    def on_register_error(self, response: SignUpError):
        self.log.error(f'Registration Error: {response.message}.')

    def on_disconnected(self):
        self.log.error(f'Disconnected From KIK')


if __name__ == '__main__':
    main()
