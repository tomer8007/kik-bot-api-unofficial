import asyncio
import logging
import sys
import time
from asyncio import Transport, Protocol
from threading import Thread

from bs4 import BeautifulSoup
from kik_unofficial.datatypes.callbacks import KikClientCallback
from kik_unofficial.datatypes.exceptions import KikApiException
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
from typing import Union, List

HOST, PORT = "talk1110an.kik.com", 5223


class KikClient:
    def __init__(self, callback: KikClientCallback, username=None, password=None, log_level=logging.INFO):
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
        self.initial_connection_payload = '<k anon="">'.encode()
        self.username = username
        self.password = password
        self.authenticate_on_connection = username and password
        self._connect()

    def _connect(self):
        self.kik_connection_thread = Thread(target=self._kik_connection_thread_function, name="KikConnection")
        self.kik_connection_thread.start()

    def login(self, username, password, captcha_result=None):
        self.username = username
        self.password = password
        login_message = LoginRequest(username, password, captcha_result)
        return self._send(login_message)

    def register(self, email, username, password, first_name, last_name, birthday="1974-11-20", captcha_result=None):
        self.username = username
        self.password = password
        register_message = RegisterRequest(email, username, password, first_name, last_name, birthday, captcha_result)
        return self._send(register_message)

    def check_unique(self, username):
        return self._send(CheckUsernameUniquenessRequest(username))

    def request_roster(self):
        return self._send(FetchRoasterRequest())

    def send(self, peer_jid: str, message: str):
        if self.is_group_jid(peer_jid):
            return self._send(OutgoingGroupChatMessage(peer_jid, message))
        else:
            return self._send(OutgoingChatMessage(peer_jid, message))

    @staticmethod
    def is_group_jid(jid):
        if '@talk.kik.com' in jid:
            return False
        elif '@groups.kik.com' in jid:
            return True
        else:
            raise KikApiException('Not a valid jid')

    def send_read_receipt(self, peer_jid: str, receipt_message_id: str):
        return self._send(OutgoingReadReceipt(peer_jid, receipt_message_id))

    def send_delivered_receipt(self, peer_jid: str, receipt_message_id: str):
        return self._send(OutgoingDeliveredReceipt(peer_jid, receipt_message_id))

    def send_is_typing(self, peer_jid: str, is_typing: bool):
        if self.is_group_jid(peer_jid):
            return self._send(OutgoingGroupIsTypingEvent(peer_jid, is_typing))
        else:
            return self._send(OutgoingIsTypingEvent(peer_jid, is_typing))

    def request_info_from_jid(self, peer_jids: Union[str, List[str]]):
        return self._send(BatchPeerInfoRequest(peer_jids))

    def request_info_from_username(self, username: str):
        return self._send(FriendRequest(username))

    def add_friend(self, peer_jid):
        return self._send(AddFriendRequest(peer_jid))

    def add_to_group(self, group_jid, peer_jid):
        return self._send(AddToGroupRequest(group_jid, peer_jid))

    def remove_from_group(self, group_jid, peer_jid):
        return self._send(RemoveFromGroupRequest(group_jid, peer_jid))

    def ban(self, group_jid, peer_jid):
        return self._send(BanMemberRequest(group_jid, peer_jid))

    def unban(self, group_jid, peer_jid):
        return self._send(UnbanRequest(group_jid, peer_jid))

    def _establish_auth_connection(self):
        self.connect_auth = True
        logging.debug("[+] Establishing authenticated connection on node {}".format(self.node))
        self._connect()

    def _kik_connection_thread_function(self):
        """ Runs in Kik connection thread """
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

    def _send(self, message: XMPPElement):
        while not self.connected:
            logging.debug("[!] Waiting for connection.")
            time.sleep(0.1)
        self.loop.call_soon_threadsafe(self.connection.send, (message.serialize()))
        return message.message_id

    def data_received(self, data: bytes):
        if data == b' ':
            # Happens every half hour. Disconnect after 10th time. Some kind of keep-alive? Let's send it back.
            self.loop.call_soon_threadsafe(self.connection.send, b' ')
        message = BeautifulSoup(data.decode(), features='xml')
        if len(message) > 0:
            message = next(iter(message))

        if message.name == "iq":
            self._handle_iq(message)
        elif message.name == "message":
            self._handle_message(message)
        elif message.name == "k":
            if message['ok'] == "1":
                self.connected = True
                if 'ts' in message.attrs:
                    self.authenticated = True
                    self.callback.on_authorized()
                elif self.authenticate_on_connection:
                    self.authenticate_on_connection = False
                    self.login(self.username, self.password)
            else:
                self.callback.on_connection_failed(ConnectionFailedResponse(message))

    def _handle_iq(self, message: BeautifulSoup):
        self._handle(message.query['xmlns'], message)

    def _handle_message(self, message: BeautifulSoup):
        if 'xmlns' in message.attrs:
            self._handle(message['xmlns'], message)
        elif message['type'] == 'receipt':
            self.callback.on_group_receipts_received(IncomingGroupReceiptsEvent(message))

    def _handle(self, xmlns: str, message: BeautifulSoup):
        if xmlns not in self.handlers:
            raise NotImplementedError
        self.handlers[xmlns].handle(message)

    def connection_lost(self):
        self.connected = False

    def connection_made(self):
        if self.node:
            message = EstablishAuthConnectionRequest(self.node, self.username, self.password)
            self.initial_connection_payload = message.serialize()
        self.connection.send(self.initial_connection_payload)

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

    def disconnect(self):
        self.connection.close()
        self.loop.call_later(200, self.loop.stop)

    def search_group(self, search_query):
        return self._send(GroupSearchRequest(search_query))

    def join_group_with_token(self, group_hashtag, group_jid, join_token):
        return self._send(GroupJoinRequest(group_hashtag, join_token, group_jid))

class KikConnection(Protocol):
    def __init__(self, loop, api: KikClient):
        self.api = api
        self.loop = loop
        self.partial_data = None  # type: bytes
        self.transport = None  # type: Transport

    def connection_made(self, transport: Transport):
        self.transport = transport
        logging.debug("[!] Connected to kik server.")
        self.api.connection_made()

    def data_received(self, data: bytes):
        logging.debug("[+] Received raw data: %s", data)
        if self.partial_data is None:
            if data.endswith(b'>'):
                self.loop.call_soon_threadsafe(self.api.data_received, data)
            else:
                logging.debug("Multi-packet data, waiting for next packet.")
                self.partial_data = data
        else:
            if data.endswith(b'>'):
                self.loop.call_soon_threadsafe(self.api.data_received, self.partial_data + data)
                self.partial_data = None
            else:
                logging.debug("Waiting for another packet, size={}".format(len(self.partial_data)))
                self.partial_data += data

    def connection_lost(self, exc):
        logging.debug('[-] Connection lost')
        self.loop.call_soon_threadsafe(self.api.connection_lost)
        self.loop.stop()

    def send(self, data: bytes):
        logging.debug("[+] Sending raw data: %s", data)
        self.transport.write(data)

    def close(self):
        if self.transport:
            self.transport.write(b'</k>')
        logging.debug("[!] Transport closed")
