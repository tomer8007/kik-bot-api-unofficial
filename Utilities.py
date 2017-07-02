import base64
import xml.dom.minidom


class Utilities():
    @staticmethod
    def sign_extend_with_mask(x):
        x &= 0xffffffff
        if x & (1 << (32-1)):  # is the highest bit (sign) set?
            return x-(1 << 32)  # 2s complement
        return x

    @staticmethod
    def string_between_strings(s, first, last ):
        try:
            start = s.index(first) + len( first )
            end = s.index(last, start)
            return s[start:end]
        except ValueError:
            return ""

    @staticmethod
    def decode_base64(data):
        # decode base64 even with wrong padding
        # based on http://stackoverflow.com/a/9807138/1806873
        missing_padding = len(data) % 4
        if missing_padding != 0:
            data += b'='* (4 - missing_padding)
        return base64.decodestring(data)

    @staticmethod
    def byte_to_signed_int(byte):
        if byte > 127:
            return (256-byte) * (-1)
        else:
            return byte

    @staticmethod
    def extract_tag_from_xml(xml, tag):
        # quick and dirty XML parsing
        try:
            open_bracket = xml[xml.index("<" + tag):xml.index(">", xml.index("<" + tag))+1]
            return Utilities.string_between_strings(xml, open_bracket, "</"+tag+">" if " " not in tag else "</"+tag[:tag.index(" ")]+">")
        except:
            print("[-] Couldn't extract tag \""+tag+"\" from xml, returning None")
            return None

    @staticmethod
    def pretty_print_xml(xml_string):
        try:
            xml_thing = xml.dom.minidom.parseString(xml_string)
            pretty_xml_as_string = xml_thing.toprettyxml()
            print(pretty_xml_as_string)
        except:
            print("[-] XML parsing failed:")
            print(xml_string)

    @staticmethod
    def print_dictionary(dictionary):
        if dictionary is False:
            return
        for x in dictionary:
            data = dictionary[x]
            info = (data[:50] + '...') if isinstance(data, str) and len(data) > 50 else data
            print("\t" + x+':', info)
