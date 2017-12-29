from bs4 import BeautifulSoup
from kik_unofficial.cryptographic_utils import KikCryptographicUtils


class Message:
    def __init__(self):
        self.message_id = KikCryptographicUtils.make_kik_uuid()

    def serialize(self) -> bytes:
        raise NotImplementedError


class Response:
    def __init__(self, data: BeautifulSoup):
        self.message_id = data['id']
