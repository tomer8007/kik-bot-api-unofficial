import base64


class Utilities:
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
