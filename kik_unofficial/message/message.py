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
        if data.kik:
            self.metadata = Metadata(data.kik)


class Metadata:
    def __init__(self, data: BeautifulSoup):
        self.timestamp = data['timestamp']
        self.app = data['app']
        self.qos = data['qos'] == 'true'
        self.push = data['push'] == 'true'
        self.hop = data['hop'] == 'true' if 'hop' in data.attrs else None
