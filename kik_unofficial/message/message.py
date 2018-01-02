from bs4 import BeautifulSoup
from kik_unofficial.cryptographic_utils import KikCryptographicUtils


class Message:
    def __init__(self):
        self.message_id = KikCryptographicUtils.make_kik_uuid()

    def serialize(self) -> bytes:
        raise NotImplementedError

    def format_escaped(self, data, *args):
        return data.format(*[self.escape_xml(a) for a in args])

    @staticmethod
    def escape_xml(s):
        s = s.replace("&", "&amp;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        s = s.replace("\"", "&quot;")
        return s


class Response:
    def __init__(self, data: BeautifulSoup):
        self.message_id = data['id']
