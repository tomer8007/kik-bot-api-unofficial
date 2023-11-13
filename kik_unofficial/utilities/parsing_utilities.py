import base64
import pathlib
import io
import os
import hashlib
import tempfile

from PIL import Image
import imageio_ffmpeg as ffmpeg
from kik_unofficial.utilities.blockhash import blockhash


def get_file_bytes(file_location):
    """
    Reads and returns the bytes of a file given its location.
    Accepts a file location as a string path, bytes, pathlib.Path, or an IOBase object.
    """
    if isinstance(file_location, (str, pathlib.Path)):
        if not os.path.exists(file_location):
            raise FileNotFoundError(f'The file path {file_location} does not exist')
        with open(file_location, "rb") as f:
            return f.read()
    elif isinstance(file_location, io.IOBase) or hasattr(file_location, 'getvalue'):
        return file_location.getvalue()
    elif isinstance(file_location, bytes):
        return file_location
    else:
        raise TypeError(f'File cannot be a type of {type(file_location)}')


class ParsingUtilities:
    def __init__(self):
        pass

    @staticmethod
    def sign_extend_with_mask(x):
        """
        Extends a 32-bit integer with sign bit.
        """
        x &= 0xffffffff
        return x - (1 << 32) if x & (1 << (32 - 1)) else x

    @staticmethod
    def decode_base64(data):
        """
        Decodes base64, fixing incorrect padding if necessary.
        """
        missing_padding = len(data) % 4
        if missing_padding != 0:
            data += b'=' * (4 - missing_padding)
        return base64.b64decode(data)

    @staticmethod
    def encode_to_base64(data):
        """
        Encodes data to base64.
        """
        return base64.b64encode(data).decode()

    @staticmethod
    def calculate_hash(data, hash_type='sha1'):
        """
        Calculates the hash of the data. Default is SHA1. Other types like 'md5' can be specified.
        """
        hash_function = getattr(hashlib, hash_type)()
        hash_function.update(data)
        return hash_function.hexdigest()

    def parse_image(self, file_location) -> dict:
        """
        Converts images to .jpg and compresses/upscales them so that large image files can be sent after compression.
        Accepts file_location as a path (str), bytes, pathlib.Path, or io.BytesIO.
        """
        file_stream = get_file_bytes(file_location)
        if isinstance(file_stream, bytes):
            file_stream = io.BytesIO(file_stream)

        img = Image.open(file_stream)
        width, height = img.size
        larger_dim = max(height, width)
        img = img.convert('RGB') if img.mode != "RGB" else img

        ratio = larger_dim / 1600
        image = img.resize((round(width / ratio), round(height / ratio)))
        preview_ratio = larger_dim / 400
        preview_image = img.resize((round(width / preview_ratio), round(height / preview_ratio)))

        image_out = io.BytesIO()
        preview_out = io.BytesIO()

        image.save(image_out, format='JPEG')
        preview_image.save(preview_out, format='JPEG')

        final_og = image_out.getvalue()
        final_pre = preview_out.getvalue()

        return {
            'base64': self.encode_to_base64(final_pre),
            'size': len(final_og),
            'original': final_og,
            'SHA1': self.calculate_hash(final_og),
            'SHA1Scaled': self.calculate_hash(final_pre),
            'blockhash': blockhash(preview_image, 16),
            'MD5': self.calculate_hash(final_og, 'md5')
        }

    def parse_video(self, file_location) -> dict:
        """
                Extracts metadata from a video file and generates a thumbnail using parse_image.
                Accepts file_location as a path (str), bytes, or io.BytesIO.
                """
        duration = 0
        thumbnail_info = {}

        file_bytes = get_file_bytes(file_location)

        # Write to a temporary file if necessary
        temp_file_path = None
        if not isinstance(file_location, str):
            temp_file_path = self.write_temp_file(file_bytes)
            file_path = temp_file_path
        else:
            file_path = file_location

        try:
            # Extract metadata using FFmpeg
            frame_gen = ffmpeg.read_frames(file_path, pix_fmt='rgb24', output_params=['-vframes', '1'])

            # Yield metadata
            metadata = next(frame_gen)
            duration = metadata.get('duration', 0)
            width, height = metadata['size']

            # Process the first frame for thumbnail
            for frame_data in frame_gen:
                image = Image.frombytes('RGB', (width, height), frame_data)  # Convert frame data to BytesIO
                image_buffer = io.BytesIO()
                image.save(image_buffer, format="JPEG")
                image_buffer.seek(0)
                thumbnail_info = self.parse_image(image_buffer)
                break  # Only process the first frame

        except Exception as e:
            print(f"An error occurred parsing video: {str(e)}")
            thumbnail_info = {}

        finally:
            # Clean up temporary file if created
            if temp_file_path:
                os.remove(temp_file_path)

        return {
            'size': len(file_bytes),
            'original': file_bytes,
            'MD5': self.calculate_hash(file_bytes, 'md5'),
            'thumbnail': thumbnail_info,
            'duration': duration * 1000  # Convert to milliseconds
        }

    @staticmethod
    def write_temp_file(file_bytes):
        """
        Writes bytes to a temporary file and returns the file path.
        Needed if we are loading image or video from direct bytesIO
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            temp_file.write(file_bytes)
            return temp_file.name

    @staticmethod
    def fix_base64_padding(data):
        """
        Ensures that the base64 string has the correct padding.
        This function adds '=' characters to the end of the data string to make its length a multiple of 4.

        :param data: The base64 encoded string.
        :return: The base64 string with proper padding.
        """
        return data + '=' * (-len(data) % 4)

    @staticmethod
    def byte_to_signed_int(byte):
        """
        Converts a byte (0-255) to a signed integer (-128 to 127).

        :param byte: A byte value to convert.
        :return: The corresponding signed integer.
        """
        return (256 - byte) * (-1) if byte > 127 else byte

    @staticmethod
    def print_dictionary(dictionary):
        """
        Prints the contents of a dictionary in a formatted way.
        For string values longer than 50 characters, only the first 50 characters are printed followed by '...'.

        :param dictionary: The dictionary to be printed.
        """
        if not dictionary:
            return
        for key, value in dictionary.items():
            info = f'{value[:50]}...' if isinstance(value, str) and len(value) > 50 else value
            print("\t" + key + ':', info)

    @staticmethod
    def escape_xml(s: str):
        """
        Escapes special characters in a string for XML compatibility.

        :param s: The string to be escaped for XML.
        :return: The XML-escaped string.
        """
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")
