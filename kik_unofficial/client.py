import sys
import time
import asyncio
import logging
from asyncio import Transport, Protocol
from threading import Thread
from typing import Union, List

from bs4 import BeautifulSoup
from kik_unofficial.datatypes.callbacks import KikClientCallback
from kik_unofficial.datatypes.exceptions import KikApiException
from kik_unofficial.http import profilepics
from kik_unofficial.datatypes.xmpp.base_elements import XMPPElement
from kik_unofficial.datatypes.xmpp.chatting import OutgoingGroupChatMessage, OutgoingChatMessage, OutgoingReadReceipt, OutgoingDeliveredReceipt, \
    OutgoingIsTypingEvent, OutgoingGroupIsTypingEvent, IncomingGroupReceiptsEvent
from kik_unofficial.datatypes.xmpp.group_adminship import AddToGroupRequest, RemoveFromGroupRequest, BanMemberRequest, UnbanRequest
from kik_unofficial.datatypes.xmpp.roster import FetchRoasterRequest, BatchPeerInfoRequest, FriendRequest, AddFriendRequest, GroupSearchRequest, \
    GroupJoinRequest
from kik_unofficial.datatypes.xmpp.sign_up import LoginRequest, RegisterRequest, EstablishAuthConnectionRequest, \
    ConnectionFailedResponse, CheckUsernameUniquenessRequest
from kik_unofficial.handlers import CheckUniqueHandler, RegisterHandler, RosterHandler, MessageHandler, \
    GroupMessageHandler, FriendMessageHandler, GroupSearchHandler

HOST, PORT = "talk1110an.kik.com", 5223


class KikClient:
    def __init__(self, callback: KikClientCallback, username=None, password=None, node=None, log_level=logging.INFO):
        """
        Initializes a connection to Kik servers. Use username and password for logging in.

        :param callback: KikCallback containing callback implementation.
        :param username: username.
        :param password: password.
        :param log_level: logging level.
        """

        self._set_up_logging(log_level)

        self.callback = callback
        self.handlers = {
            'kik:iq:check-unique': CheckUniqueHandler(callback, self),
            'jabber:iq:register': RegisterHandler(callback, self),
            'jabber:iq:roster': RosterHandler(callback, self),
            'jabber:client': MessageHandler(callback, self),
            'kik:groups': GroupMessageHandler(callback, self),
            'kik:iq:friend': FriendMessageHandler(callback, self),
            'kik:iq:friend:batch': FriendMessageHandler(callback, self),
            'kik:iq:xiphias:bridge': GroupSearchHandler(callback, self),
        }
        self.connected = False
        self.authenticated = False
        self.connection = None
        self.loop = asyncio.get_event_loop()
        self.node = None
        self.username = username
        self.password = password
        self.node = node
        if node:
            message = EstablishAuthConnectionRequest(self.node, self.username, self.password)
            self.initial_connection_payload = message.serialize()
        else:
            self.initial_connection_payload = '<k anon="">'.encode()
        self.authenticate_on_connection = username and password
        self._connect()

    def _connect(self):
        self.kik_connection_thread = Thread(target=self._kik_connection_thread_function, name="KikConnection")
        self.kik_connection_thread.start()

    def login(self, username, password, captcha_result=None):
        self.username = username
        self.password = password
        login_message = LoginRequest(username, password, captcha_result)
        return self.send_xmpp_element(login_message)

    def register(self, email, username, password, first_name, last_name, birthday="1974-11-20", captcha_result=None):
        self.username = username
        self.password = password
        register_message = RegisterRequest(email, username, password, first_name, last_name, birthday, captcha_result)
        return self.send_xmpp_element(register_message)

    def check_username_uniqueness(self, username):
        return self.send_xmpp_element(CheckUsernameUniquenessRequest(username))

    def request_roster(self):
        return self.send_xmpp_element(FetchRoasterRequest())

    def send_chat_message(self, peer_jid: str, message: str):
        if self.is_group_jid(peer_jid):
            return self.send_xmpp_element(OutgoingGroupChatMessage(peer_jid, message))
        else:
            return self.send_xmpp_element(OutgoingChatMessage(peer_jid, message))

    def send_read_receipt(self, peer_jid: str, receipt_message_id: str):
        return self.send_xmpp_element(OutgoingReadReceipt(peer_jid, receipt_message_id))

    def send_delivered_receipt(self, peer_jid: str, receipt_message_id: str):
        return self.send_xmpp_element(OutgoingDeliveredReceipt(peer_jid, receipt_message_id))

    def send_is_typing(self, peer_jid: str, is_typing: bool):
        if self.is_group_jid(peer_jid):
            return self.send_xmpp_element(OutgoingGroupIsTypingEvent(peer_jid, is_typing))
        else:
            return self.send_xmpp_element(OutgoingIsTypingEvent(peer_jid, is_typing))

    def request_info_from_jid(self, peer_jids: Union[str, List[str]]):
        return self.send_xmpp_element(BatchPeerInfoRequest(peer_jids))

    def request_info_from_username(self, username: str):
        return self.send_xmpp_element(FriendRequest(username))

    def add_friend(self, peer_jid):
        return self.send_xmpp_element(AddFriendRequest(peer_jid))

    def add_peer_to_group(self, group_jid, peer_jid):
        return self.send_xmpp_element(AddToGroupRequest(group_jid, peer_jid))

    def remove_peer_from_group(self, group_jid, peer_jid):
        return self.send_xmpp_element(RemoveFromGroupRequest(group_jid, peer_jid))

    def ban_member_from_group(self, group_jid, peer_jid):
        return self.send_xmpp_element(BanMemberRequest(group_jid, peer_jid))

    def unban_member_from_group(self, group_jid, peer_jid):
        return self.send_xmpp_element(UnbanRequest(group_jid, peer_jid))

    def disconnect(self):
        self.connection.close()
        self.loop.call_later(200, self.loop.stop)

    def search_group(self, search_query):
        return self.send_xmpp_element(GroupSearchRequest(search_query))

    def join_group_with_token(self, group_hashtag, group_jid, join_token):
        return self.send_xmpp_element(GroupJoinRequest(group_hashtag, join_token, group_jid))

    def set_profile_picture(self, filename):
        profilepics.set_profile_picture(filename, self.node + '@talk.kik.com', self.username, self.password)

    def set_background_picture(self, filename):
        profilepics.set_background_picture(filename, self.node + '@talk.kik.com', self.username, self.password)

    def send_xmpp_element(self, message: XMPPElement):
        while not self.connected:
            logging.debug("[!] Waiting for connection.")
            time.sleep(0.1)
        self.loop.call_soon_threadsafe(self.connection.send_raw_data, (message.serialize()))
        return message.message_id

    def on_new_data_received(self, data: bytes):
        """
        Gets called whenever we get a whole new XML element from kik's servers.
        :param data: The data received (bytes)
        """
        if data == b' ':
            # Happens every half hour. Disconnect after 10th time. Some kind of keep-alive? Let's send it back.
            self.loop.call_soon_threadsafe(self.connection.send_chat_message, b' ')
            return

        xml_element = BeautifulSoup(data.decode(), features='xml')
        if len(xml_element) > 0:
            xml_element = next(iter(xml_element))

        if xml_element.name == "iq":
            self._handle_iq(xml_element)
        elif xml_element.name == "message":
            self._handle_xmpp_message(xml_element)
        elif xml_element.name == "k":
            if xml_element['ok'] == "1":
                self.connected = True
                if 'ts' in xml_element.attrs:
                    self.authenticated = True
                    self.callback.on_authorized()
                elif self.authenticate_on_connection:
                    self.authenticate_on_connection = False
                    self.login(self.username, self.password)
            else:
                self.callback.on_connection_failed(ConnectionFailedResponse(xml_element))

    def on_connection_lost(self):
        self.connected = False

    def on_connection_made(self):
        if self.node:
            message = EstablishAuthConnectionRequest(self.node, self.username, self.password)
            self.initial_connection_payload = message.serialize()
        self.connection.send_raw_data(self.initial_connection_payload)

    def _handle_iq(self, message: BeautifulSoup):
        self._handle(message.query['xmlns'], message)

    def _handle_xmpp_message(self, xmpp_message: BeautifulSoup):
        if 'xmlns' in xmpp_message.attrs:
            self._handle(xmpp_message['xmlns'], xmpp_message)
        elif xmpp_message['type'] == 'receipt':
            self.callback.on_group_receipts_received(IncomingGroupReceiptsEvent(xmpp_message))

    def _handle(self, xmlns: str, message: BeautifulSoup):
        if xmlns not in self.handlers:
            raise NotImplementedError
        self.handlers[xmlns].handle(message)

    def _establish_auth_connection(self):
        self.connect_auth = True
        logging.debug("[+] Establishing authenticated connection on node {}".format(self.node))
        self._connect()

    def _kik_connection_thread_function(self):
        """ Runs in Kik connection thread """
        # If there is already a connection going, than wait for it to stop
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.connection.close)
            while self.loop.is_running():
                time.sleep(0.1)
                logging.debug("[!] Waiting for loop to stop.")

        self.connection = KikConnection(self.loop, self)
        coro = self.loop.create_connection(lambda: self.connection, HOST, PORT, ssl=True)
        self.loop.run_until_complete(coro)
        logging.debug("[!] New connection made")
        self.loop.run_forever()

    def _set_up_logging(self, log_level):
        log_formatter = logging.Formatter('[%(asctime)-15s] %(levelname)-6s (thread %(threadName)-10s): %(message)s')
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler("kik-debug.log")
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(log_formatter)
        root_logger.addHandler(console_handler)

    @staticmethod
    def is_group_jid(jid):
        if '@talk.kik.com' in jid:
            return False
        elif '@groups.kik.com' in jid:
            return True
        else:
            raise KikApiException('Not a valid jid')



class KikConnection(Protocol):
    def __init__(self, loop, api: KikClient):
        self.api = api
        self.loop = loop
        self.partial_data = None  # type: bytes
        self.transport = None  # type: Transport

    def connection_made(self, transport: Transport):
        self.transport = transport
        logging.debug("[!] Connected to kik server.")
        self.api.on_connection_made()

    def data_received(self, data: bytes):
        logging.debug("[+] Received raw data: %s", data)
        if self.partial_data is None:
            if data.endswith(b'>'):
                self.loop.call_soon_threadsafe(self.api.on_new_data_received, data)
            else:
                logging.debug("Multi-packet data, waiting for next packet.")
                self.partial_data = data
        else:
            if data.endswith(b'>'):
                self.loop.call_soon_threadsafe(self.api.on_new_data_received, self.partial_data + data)
                self.partial_data = None
            else:
                logging.debug("Waiting for another packet, size={}".format(len(self.partial_data)))
                self.partial_data += data

    def connection_lost(self, exc):
        logging.debug('[-] Connection lost')
        self.loop.call_soon_threadsafe(self.api.on_connection_lost)
        self.loop.stop()

    def send_raw_data(self, data: bytes):
        logging.debug("[+] Sending raw data: %s", data)
        self.transport.write(data)

    def close(self):
        if self.transport:
            self.transport.write(b'</k>')
        logging.debug("[!] Transport closed")
