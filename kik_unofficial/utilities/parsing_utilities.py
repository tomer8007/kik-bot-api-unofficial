import base64
from PIL import Image
import math
import pathlib


class ParsingUtilities:
    def __init__(self):
        pass

    @staticmethod
    def sign_extend_with_mask(x):
        x &= 0xffffffff
        if x & (1 << (32 - 1)):  # is the highest bit (sign) set?
            return x - (1 << 32)  # 2s complement
        return x

    @staticmethod
    def decode_base64(data):
        # decode base64 even with wrong padding
        # based on http://stackoverflow.com/a/9807138/1806873
        missing_padding = len(data) % 4
        if missing_padding != 0:
            data += b'=' * (4 - missing_padding)
        return base64.decodebytes(data)

    @staticmethod
    def read_file_as_base64(file_location):
        with open(file_location, "rb") as file:
            data = base64.b64encode(file.read())
            return data.decode()

    @staticmethod
    def parse_image(file_location):
        '''
        Converts images to .jpg and compresses/upscales them so that large image files can be sent after compression.
        '''
        file_name = pathlib.PurePath(file_location).name
        img = Image.open(file_location)
        image_out = file_name.split('.')[0] + "_send.jpg"
        width, height = img.size
        if len(img.split()) == 4:
            r, g, b, a = img.split()
            img = Image.merge("RGB", (r, g, b))
        larger_dim = height if height > width else width
        ratio = larger_dim/900
        image = img.resize((math.ceil(width / ratio), math.ceil(height / ratio)))
        image.save(image_out)
        return image_out

    @staticmethod
    def fix_base64_padding(data):
        return data + '=' * (-len(data) % 4)

    @staticmethod
    def byte_to_signed_int(byte):
        if byte > 127:
            return (256 - byte) * (-1)
        else:
            return byte

    @staticmethod
    def print_dictionary(dictionary):
        if dictionary is False:
            return
        for x in dictionary:
            data = dictionary[x]
            info = (data[:50] + '...') if isinstance(data, str) and len(data) > 50 else data
            print("\t" + x + ':', info)

    @staticmethod
    def escape_xml(s: str):
        s = s.replace("&", "&amp;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        s = s.replace("\"", "&quot;")
        return s
