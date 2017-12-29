import asyncio
import logging
import time
from asyncio import Transport, Protocol
from threading import Thread

from bs4 import BeautifulSoup
from kik_unofficial.callback import KikCallback
from kik_unofficial.handler import CheckUniqueHandler, RegisterHandler, RosterHandler, MessageHandler, \
    GroupMessageHandler
from kik_unofficial.message.chat import GroupChatMessage, ChatMessage
from kik_unofficial.message.message import Message
from kik_unofficial.message.roster import RosterMessage
from kik_unofficial.message.unauthorized.checkunique import CheckUniqueMessage
from kik_unofficial.message.unauthorized.register import LoginMessage, RegisterMessage, EstablishConnectionMessage
from kik_unofficial.peer import Peer, Group

HOST, PORT = "talk1110an.kik.com", 5223

FORMAT = '%(asctime)-15s %(levelname)-8s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')


class KikApi:
    def __init__(self, callback: KikCallback, username=None, password=None):
        self.callback = callback
        self.handlers = {
            'kik:iq:check-unique': CheckUniqueHandler(callback, self),
            'jabber:iq:register': RegisterHandler(callback, self),
            'jabber:iq:roster': RosterHandler(callback, self),
            'jabber:client': MessageHandler(callback, self),
            'kik:groups': GroupMessageHandler(callback, self),
        }
        self.connected = False
        self.loop = asyncio.get_event_loop()
        self._connect('<k anon="">'.encode())
        self.username = username
        self.password = password
        if username and password:
            self.login(self.username, self.password)

    def _connect(self, payload):
        self.kik_connection_thread = Thread(target=self._kik_connection, args=[payload])
        self.kik_connection_thread.start()
        while not self.connected:
            print(".")
            time.sleep(0.1)
        logging.info("Connected.")

    def login(self, username, password, captcha_url=None):
        self.username = username
        self.password = password
        login_message = LoginMessage(username, password, captcha_url)
        return self._send(login_message)

    def register(self, email, username, password, first_name, last_name, birthday="1974-11-20", captcha_result=None):
        self.username = username
        self.password = password
        register_message = RegisterMessage(email, username, password, first_name, last_name, birthday, captcha_result)
        return self._send(register_message)

    def check_unique(self, username):
        return self._send(CheckUniqueMessage(username))

    def roster(self):
        return self._send(RosterMessage())

    def send(self, peer: Peer, message: str):
        if isinstance(peer, Group):
            return self._send(GroupChatMessage(peer.jid, message))
        else:
            return self._send(ChatMessage(peer.jid, message))

    def establish_connection(self, node, username, password):
        message = EstablishConnectionMessage(node, username, password)
        self._connect(message.serialize())

    def _kik_connection(self, payload):
        """ Kik connection thread """
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.connection.close)
            while self.loop.is_running():
                time.sleep(0.1)
        self.connection = KikConnection(self.loop, self, payload)
        coro = self.loop.create_connection(lambda: self.connection, HOST, PORT, ssl=True)
        self.loop.run_until_complete(coro)
        self.connected = True
        self.loop.run_forever()

    def _send(self, message: Message):
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
            if message['ok'] == "1":
                self.callback.on_authorized()

    def _handle_iq(self, message: BeautifulSoup):
        self._handle(message.query['xmlns'], message)

    def _handle_message(self, message: BeautifulSoup):
        self._handle(message['xmlns'], message)

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
        self.api.data_received(data)

    def connection_lost(self, exc):
        logging.warning('Connection lost')
        self.loop.stop()

    def send(self, data: bytes):
        logging.debug("Sending %s", data)
        self.transport.write(data)

    def close(self):
        self.transport.write(b'</k>')
        logging.debug("Transport closed")
