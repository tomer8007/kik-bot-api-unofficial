import asyncio
import logging
import time
from asyncio import Transport, Protocol
from threading import Thread

from bs4 import BeautifulSoup
from kik_unofficial.callback import KikCallback
from kik_unofficial.handler import CheckUniqueHandler, RegisterHandler, RosterHandler, MessageHandler, \
    GroupMessageHandler, FriendMessageHandler
from kik_unofficial.kik_exceptions import KikApiException
from kik_unofficial.message.chat import GroupChatMessage, ChatMessage, ReadReceiptMessage, DeliveredReceiptMessage, \
    IsTypingMessage, GroupIsTypingMessage, GroupReceiptResponse
from kik_unofficial.message.message import Message
from kik_unofficial.message.roster import RosterMessage, BatchFriendMesssage, FriendMesssage, AddFriendMessage
from kik_unofficial.message.unauthorized.checkunique import CheckUniqueMessage
from kik_unofficial.message.unauthorized.register import LoginMessage, RegisterMessage, EstablishConnectionMessage

HOST, PORT = "talk1110an.kik.com", 5223


class KikApi:
    def __init__(self, callback: KikCallback, username=None, password=None, node=None, loglevel=logging.INFO):
        """
        Initializes a connection to Kik servers. Use username and password for logging in, use node if possible to
        establish an auhtorized while skipping the login process.

        :param callback: KikCallback containing callback implementation.
        :param username: username.
        :param password: password.
        :param node: node, e.g. "[username]_6ge".
        :param loglevel: logging level.
        """
        logging_format = '%(asctime)-15s %(levelname)-6s %(threadName)-10s %(message)s'
        logging.basicConfig(format=logging_format, level=loglevel, datefmt='%Y-%m-%d %H:%M:%S')
        self.callback = callback
        self.handlers = {
            'kik:iq:check-unique': CheckUniqueHandler(callback, self),
            'jabber:iq:register': RegisterHandler(callback, self),
            'jabber:iq:roster': RosterHandler(callback, self),
            'jabber:client': MessageHandler(callback, self),
            'kik:groups': GroupMessageHandler(callback, self),
            'kik:iq:friend': FriendMessageHandler(callback, self),
        }
        self.connected = False
        self.connection = None
        self.loop = asyncio.get_event_loop()
        self.username = username
        self.password = password
        if username and password:
            if node:
                self._establish_connection(node, self.username, self.password)
            else:
                self._connect('<k anon="">'.encode())
                self.login(self.username, self.password)
        else:
            self._connect('<k anon="">'.encode())

    def _connect(self, payload):
        self.connected = False
        self.kik_connection_thread = Thread(target=self._kik_connection_thread_function, args=[payload])
        self.kik_connection_thread.start()

    def login(self, username, password, captcha_result=None):
        self.username = username
        self.password = password
        login_message = LoginMessage(username, password, captcha_result)
        return self._send(login_message)

    def register(self, email, username, password, first_name, last_name, birthday="1974-11-20", captcha_result=None):
        self.username = username
        self.password = password
        register_message = RegisterMessage(email, username, password, first_name, last_name, birthday, captcha_result)
        return self._send(register_message)

    def check_unique(self, username):
        return self._send(CheckUniqueMessage(username))

    def request_roster(self):
        return self._send(RosterMessage())

    def send(self, peer_jid: str, message: str):
        if self.is_group_jid(peer_jid):
            return self._send(GroupChatMessage(peer_jid, message))
        else:
            return self._send(ChatMessage(peer_jid, message))

    @staticmethod
    def is_group_jid(jid):
        if '@talk.kik.com' in jid:
            return False
        elif '@groups.kik.com' in jid:
            return True
        else:
            raise KikApiException('Not a valid jid')

    def send_read_receipt(self, peer_jid: str, receipt_message_id: str):
        return self._send(ReadReceiptMessage(peer_jid, receipt_message_id))

    def send_delivered_receipt(self, peer_jid: str, receipt_message_id: str):
        return self._send(DeliveredReceiptMessage(peer_jid, receipt_message_id))

    def send_is_typing(self, peer_jid: str, is_typing: bool):
        if self.is_group_jid(peer_jid):
            return self._send(GroupIsTypingMessage(peer_jid, is_typing))
        else:
            return self._send(IsTypingMessage(peer_jid, is_typing))

    def request_info_from_jid(self, peer_jid: str):
        return self._send(BatchFriendMesssage(peer_jid))

    def request_info_from_username(self, username: str):
        return self._send(FriendMesssage(username))

    def add_friend(self, peer_jid):
        return self._send(AddFriendMessage(peer_jid))

    def _establish_connection(self, node, username, password):
        message = EstablishConnectionMessage(node, username, password)
        self._connect(message.serialize())

    def _kik_connection_thread_function(self, payload):
        """ Runs in Kik connection thread """
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.connection.close)
            while self.loop.is_running():
                time.sleep(0.1)
        self.connection = KikConnection(self.loop, self, payload)
        coro = self.loop.create_connection(lambda: self.connection, HOST, PORT, ssl=True)
        self.loop.run_until_complete(coro)
        logging.info("New connection made")
        self.connected = True
        self.loop.run_forever()

    def _send(self, message: Message):
        while not self.connected:
            print(".")
            time.sleep(0.1)
        self.loop.call_soon_threadsafe(self.connection.send, (message.serialize()))
        return message.message_id

    def data_received(self, data: bytes):
        message = BeautifulSoup(data.decode(), features='xml')
        if len(message) > 0:
            message = next(iter(message))

        if message.name == "iq":
            self._handle_iq(message)
        elif message.name == "message":
            self._handle_message(message)
        elif message.name == "k":
            if message['ok'] == "1" and 'ts' in message.attrs:
                self.callback.on_authorized()

    def _handle_iq(self, message: BeautifulSoup):
        self._handle(message.query['xmlns'], message)

    def _handle_message(self, message: BeautifulSoup):
        if 'xmlns' in message.attrs:
            self._handle(message['xmlns'], message)
        elif message['type'] == 'receipt':
            self.callback.on_group_receipt(GroupReceiptResponse(message))

    def _handle(self, xmlns: str, message: BeautifulSoup):
        if xmlns not in self.handlers:
            raise NotImplementedError
        self.handlers[xmlns].handle(message)


class KikConnection(Protocol):
    def __init__(self, loop, api: KikApi, initial_connection_payload: bytes):
        self.api = api
        self.loop = loop
        self.transport = None  # type: Transport
        self.connection_payload = initial_connection_payload

    def connection_made(self, transport: Transport):
        self.transport = transport
        self.send(self.connection_payload)

    def data_received(self, data: bytes):
        logging.debug("Received %s", data)
        self.loop.call_soon_threadsafe(self.api.data_received, data)

    def connection_lost(self, exc):
        logging.warning('Connection lost')
        self.loop.stop()

    def send(self, data: bytes):
        logging.debug("Sending %s", data)
        self.transport.write(data)

    def close(self):
        self.transport.write(b'</k>')
        logging.debug("Transport closed")
