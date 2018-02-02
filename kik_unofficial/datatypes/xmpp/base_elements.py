from bs4 import BeautifulSoup

from kik_unofficial.utilities.cryptographics import CryptographicUtils


class XMPPElement:
    def __init__(self):
        self.message_id = CryptographicUtils.make_kik_uuid()

    def serialize(self) -> bytes:
        raise NotImplementedError


class XMPPResponse:
    def __init__(self, data: BeautifulSoup):
        self.message_id = data['id']
        if data.kik:
            self.metadata = XMPPResponseMetadata(data.kik)


class XMPPResponseMetadata:
    def __init__(self, data: BeautifulSoup):
        self.timestamp = data['timestamp']
        self.app = data['app']
        self.qos = data['qos'] == 'true'
        self.push = data['push'] == 'true'
        self.hop = data['hop'] == 'true' if 'hop' in data.attrs else None
