import base64
import math
import pathlib
import io
import os
import hashlib
from PIL import Image
from kik_unofficial.utilities.blockhash import blockhash


def get_file_bytes(file_location: str or bytes or pathlib.Path or io.IOBase):
    if isinstance(file_location, (str, pathlib.Path)):
        if not os.path.exists(file_location):
            raise Exception('The file path %s does not exist', file_location)
        with open(file_location, "rb") as f:
            data = f.read()
    elif isinstance(file_location, io.IOBase) or hasattr(file_location, 'getvalue'):
        data = file_location.getvalue()
    elif isinstance(file_location, bytes):
        data = file_location
    else:
        raise ValueError('File cannot be a type of %s', type(file_location))
    return data


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
        data = base64.b64encode(get_file_bytes(file_location))
        return data.decode()

    @staticmethod
    def read_file_as_sha1(file_location):
        x = hashlib.sha1()
        x.update(get_file_bytes(file_location))
        return x.hexdigest()

    @staticmethod
    def parse_image(file_location: str or bytes or pathlib.Path or io.IOBase) -> dict:
        '''
        Converts images to .jpg and compresses/upscales them so that large image files can be sent after compression.
        '''
        preview_out = io.BytesIO()
        image_out = io.BytesIO()
        image_out.name = "temp.jpg"

        file_location = get_file_bytes(file_location)
        if isinstance(file_location, bytes):
            file_location = io.BytesIO(file_location)

        img = Image.open(file_location)
        width, height = img.size
        larger_dim = height if height > width else width
        if img.mode != "RGB":
            img = img.convert('RGB')
        ratio = larger_dim/1600
        image = img.resize((round(width / ratio), round(height / ratio)))
        preview_ratio = larger_dim/400
        preview_image = img.resize((round(width / preview_ratio), round(height / preview_ratio)))

        image.save(image_out, format='JPEG')
        preview_image.save(preview_out, format='JPEG')

        size = image_out.tell()
        final_og = image_out.getvalue()
        final_pre = preview_out.getvalue()

        base64 = ParsingUtilities.read_file_as_base64(final_pre)
        sha1_og = ParsingUtilities.read_file_as_sha1(final_og)
        sha1_scaled = ParsingUtilities.read_file_as_sha1(final_pre)
        block_scaled = blockhash(preview_image, 16)
        md5 = hashlib.md5(final_og).hexdigest()
        image_out.close()
        preview_out.close()
        preview_image.close()
        img.close()

        final = {
            'base64': base64,
            'size': size,
            'original': final_og,
            'SHA1': sha1_og,
            'SHA1Scaled': sha1_scaled,
            'blockhash': block_scaled,
            'MD5': md5
        }
        return final

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
