from bs4 import BeautifulSoup

from kik_unofficial.message.message import Message, Response


class CheckUniqueMessage(Message):
    def __init__(self, username):
        super().__init__()
        self.username = username

    def serialize(self) -> bytes:
        data = self.format(('<iq type="get" id="{}">'
                            '<query xmlns="kik:iq:check-unique">'
                            '<username>{}</username>'
                            '</query>'
                            '</iq>'), self.message_id, self.username)

        return data.encode()


class CheckUniqueResponse(Response):
    def __init__(self, data: BeautifulSoup):
        super().__init__(data)
        username_element = data.find('username')
        self.unique = True if username_element['is-unique'] == "true" else False
        self.username = username_element.text
