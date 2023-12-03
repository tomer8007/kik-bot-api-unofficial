from asyncio import StreamReader
from xml.sax import ContentHandler, ErrorHandler, SAXException

import defusedxml.sax
from bs4 import BeautifulSoup


class KikXmlParser:
    """
    Parses and validates incoming stanzas from the XMPP stream.
    """

    def __init__(self, reader: StreamReader, log):
        self.reader = reader
        self.handler = StanzaHandler(log)

    async def read_initial_k(self) -> BeautifulSoup:
        response = await self.reader.readuntil(separator=b'>')
        if not response.startswith(b'<k '):
            raise Exception('unexpected init stream response tag: ' + response.decode('utf-8'))
        if b' ok="1"' in response or b'</k>' in response:
            return self._parse_from_bytes(response)
        else:
            response += await self.reader.readuntil(separator=b'</k>')
            return self._parse_from_bytes(response)

    async def read_next_stanza(self) -> BeautifulSoup:
        xml = b''
        parser = self._make_parser()

        while True:
            packet = await self.reader.readuntil(separator=b'>')
            xml += packet

            try:
                parser.feed(packet)
            except StopIteration:
                stanza = self._parse_from_bytes(xml)
                return stanza

    def _make_parser(self):
        parser = defusedxml.sax.make_parser()
        parser.setContentHandler(self.handler)
        parser.setErrorHandler(self.handler)
        parser.forbid_dtd = True
        parser.forbid_entities = True
        parser.forbid_external = True
        return parser

    @staticmethod
    def _parse_from_bytes(xml: bytes) -> BeautifulSoup:
        element = BeautifulSoup(xml, features='xml', from_encoding='utf-8')
        return next(iter(element)) if len(element) > 0 else element


class StanzaHandler(ContentHandler, ErrorHandler):
    """
    This validates that a chunk of data is a complete stanza (all start tags are properly closed)

    This also handles a case where Kik sends multiple stanzas back in the same chunk of data from the socket.
    """
    def __init__(self, log):
        super().__init__()
        self.log = log
        self.current_stanza = BeautifulSoup(features='xml')
        self.depth = 0
        self.expected_name = None
        self.stanzas = []

    def startElement(self, name, attrs) -> None:
        # print('start: ' + name + ', depth: ' + str(self.depth + 1))
        self.depth += 1
        if self.expected_name is None:
            self.expected_name = name

    def endElement(self, name) -> None:
        self.depth -= 1
        # print('end: ' + name + ', depth: ' + str(self.depth))
        if self.depth == 0:
            if self.expected_name != name:
                raise SAXException(
                    f"end tag closed with wrong name (expected {self.expected_name}, received {name})")
            else:
                self.expected_name = None
                raise StopIteration

    def error(self, exception):
        self.log.error(exception)

    def fatalError(self, exception):
        self.log.error(exception)

    def warning(self, exception):
        self.log.warn(exception)
