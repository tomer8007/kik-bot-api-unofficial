import uuid
import time
import hashlib
import binascii
import pbkdf2
import base64
from collections import OrderedDict
from kik_unofficial.utilities.parsing_utilities import ParsingUtilities
from kik_unofficial.device_configuration import kik_version_info


class CryptographicUtils:
    """
    A class for generating various cryptographic values needed to establish an authenticated session
    and sending messages.
    """
    def __init__(self):
        pass

    @staticmethod
    def make_kik_timestamp():
        j = int(round(time.time()))

        i1 = (-16777216 & j) >> 24
        i2 = (16711680 & j) >> 16
        i3 = (65280 & j) >> 8
    
        j2 = (30 & i1) ^ i2 ^ i3
        j3 = (224 & j) >> 5
        j4 = -255 & j
    
        if j2 % 4 == 0:
            j3 = j3 // 3 * 3
        else:
            j3 = j3 // 2 * 2
        
        return j4 | (j3 << 5) | j2

    @staticmethod
    def key_from_password(username, password):
        # kik's secret algorithm for encrypting passwords
        # relevant source file: classes1\kik\android\chat\fragment\KikLoginFragmentAbstract.java
        sha1_password = binascii.hexlify(hashlib.sha1(password.encode('UTF-8')).digest())
        salt = username.lower() + "niCRwL7isZHny24qgLvy"
        key = pbkdf2.PBKDF2(sha1_password, salt, 8192).read(16)  # 128-bit key
        return binascii.hexlify(key).decode('UTF-8')

    @staticmethod
    def build_hmac_key():
        # secret algorithm for creating the hmac key
        # relevant kik source files:
        # classes1\kik\android\c.java
        # classes2\kik\core\net\l.java
        # classes2\kik\android\net\communicator\c.java
        kik_version = kik_version_info["kik_version"].encode('UTF-8')
        apk_signature_hex = "308203843082026CA00302010202044C23D625300D06092A864886F70D0101050500308183310B3009060355" \
                            "0406130243413110300E060355040813074F6E746172696F3111300F0603550407130857617465726C6F6F31" \
                            "1D301B060355040A13144B696B20496E74657261637469766520496E632E311B3019060355040B13124D6F62" \
                            "696C6520446576656C6F706D656E74311330110603550403130A43687269732042657374301E170D31303036" \
                            "32343232303331375A170D3337313130393232303331375A308183310B30090603550406130243413110300E" \
                            "060355040813074F6E746172696F3111300F0603550407130857617465726C6F6F311D301B060355040A1314" \
                            "4B696B20496E74657261637469766520496E632E311B3019060355040B13124D6F62696C6520446576656C6F" \
                            "706D656E74311330110603550403130A4368726973204265737430820122300D06092A864886F70D01010105" \
                            "000382010F003082010A0282010100E2B94E5561E9A2378B657E66507809FB8E58D9FBDC35AD2A2381B8D4B5" \
                            "1FCF50360482ECB31677BD95054FAAEC864D60E233BFE6B4C76032E5540E5BC195EBF5FF9EDFE3D99DAE8CA9" \
                            "A5266F36404E8A9FCDF2B09605B089159A0FFD4046EC71AA11C7639E2AE0D5C3E1C2BA8C2160AFA30EC8A0CE" \
                            "4A7764F28B9AE1AD3C867D128B9EAF02EF0BF60E2992E75A0D4C2664DA99AC230624B30CEA3788B23F5ABB61" \
                            "173DB476F0A7CF26160B8C51DE0970C63279A6BF5DEF116A7009CA60E8A95F46759DD01D91EFCC670A467166" \
                            "A9D6285F63F8626E87FBE83A03DA7044ACDD826B962C26E627AB1105925C74FEB77743C13DDD29B55B31083F" \
                            "5CF38FC29242390203010001300D06092A864886F70D010105050003820101009F89DD384926764854A4A641" \
                            "3BA98138CCE5AD96BF1F4830602CE84FEADD19C15BAD83130B65DC4A3B7C8DE8968ACA5CDF89200D6ACF2E75" \
                            "30546A0EE2BCF19F67340BE8A73777836728846FAD7F31A3C4EEAD16081BED288BB0F0FDC735880EBD8634C9" \
                            "FCA3A6C505CEA355BD91502226E1778E96B0C67D6A3C3F79DE6F594429F2B6A03591C0A01C3F14BB6FF56D75" \
                            "15BB2F38F64A00FF07834ED3A06D70C38FC18004F85CAB3C937D3F94B366E2552558929B98D088CF1C45CDC0" \
                            "340755E4305698A7067F696F4ECFCEEAFBD720787537199BCAC674DAB54643359BAD3E229D588E324941941E" \
                            "0270C355DC38F9560469B452C36560AD5AB9619B6EB33705"

        classes_dex_sha1_digest = kik_version_info["classes_dex_sha1_digest"].encode()
        source_bytes = "hello".encode('UTF-8') + binascii.unhexlify(
            apk_signature_hex) + kik_version + classes_dex_sha1_digest + "bar".encode('UTF-8')
        return base64.b64encode(hashlib.sha1(source_bytes).digest())

    @staticmethod
    def make_kik_uuid():
        # a manually converted code from classes2/kik/core/net/f.java
        # used to make UUIDs for messages
        random_uuid = uuid.uuid4().int
        while random_uuid.bit_length() < 121:
            random_uuid = uuid.uuid4().int

        bytes_array = random_uuid.to_bytes((random_uuid.bit_length() + 7) // 8, 'big')
        most_significant_bits = int.from_bytes(bytes_array[:8], byteorder='big')
        least_significant_bits = int.from_bytes(bytes_array[8:], byteorder='big')
        i = 1
        i2 = int((-1152921504606846976 & most_significant_bits) >> 62)
        iArr = [(3, 6), (2, 5), (7, 1), (9, 5)]
        i3 = iArr[i2][0]
        i2 = iArr[i2][1]
        j = (((-16777216 & most_significant_bits) >> 22) ^ ((16711680 & most_significant_bits) >> 16)) ^ (
            (65280 & most_significant_bits) >> 8)
        i2 = (CryptographicUtils.kik_uuid_sub_func(most_significant_bits, i2) + 1) | (
            CryptographicUtils.kik_uuid_sub_func(most_significant_bits, i3) << 1)
        i4 = 0
        while i4 < 6:
            i = (i + (i2 * 7)) % 60
            least_significant_bits = (least_significant_bits & ((1 << (i + 2)) ^ -1)) | (
                (CryptographicUtils.kik_uuid_sub_func(j, i4)) << (i + 2))
            i4 += 1
        mstb = binascii.hexlify(
            (most_significant_bits.to_bytes((most_significant_bits.bit_length() + 7) // 8, 'big') or b'\0'))
        lstb = binascii.hexlify(
            (least_significant_bits.to_bytes((least_significant_bits.bit_length() + 7) // 8, 'big') or b'\0'))
        str1 = mstb + lstb
        uuid_final = uuid.UUID(str1.decode('UTF-8'))
        return str(uuid_final)

    @staticmethod
    def kik_uuid_sub_func(j, i):
        if i > 32:
            return (int(((j >> 32) & ((1 << i))))) >> i
        return (int((((1 << i)) & j))) >> i

    @staticmethod
    def make_connection_payload(ordered_map):
        payload = "<k"
        for key in ordered_map.keys():
            payload += " "
            payload += key + "=\"" + ordered_map[key] + "\""

        payload += ">"
        return payload

    @staticmethod
    def sort_kik_map(original_dictionary):
        # another secret/cryptographic algorithm used by kik to re-sort its first XML elements
        # relevant java sources:
        # classes2\kik\core\datatypes\SortedMap.java
        # classes2\kik\core\datatypes\StrongHashMap.java

        dictionary = original_dictionary.copy()
        new_map = OrderedDict()
        original_length = len(dictionary)
        keys = list(dictionary.keys())
        keys.sort()
        for i in range(0, original_length):
            hash_code = CryptographicUtils.kik_map_hash_code(dictionary)
            hash_code = (hash_code % len(dictionary) if hash_code > 0 else hash_code % -len(dictionary))
            if hash_code < 0:
                hash_code += len(dictionary)
            selected_key = keys[hash_code]
            del keys[hash_code]
            new_map[selected_key] = dictionary[selected_key]
            del dictionary[selected_key]

        return new_map

    @staticmethod
    def kik_map_hash_code(dictionary):
        keys = list(dictionary.keys())
        keys.sort()
        string1 = ""
        for key in keys:
            string1 += key + dictionary[key]
        string2 = ""
        for key in reversed(keys):
            string2 += key + dictionary[key]
        bytes1 = string1.encode('UTF-8')
        bytes2 = string2.encode('UTF-8')
        array = [CryptographicUtils.kik_hash_code_sub_func(0, bytes1),
                 CryptographicUtils.kik_hash_code_sub_func(1, bytes1),
                 CryptographicUtils.kik_hash_code_sub_func(2, bytes1),
                 CryptographicUtils.kik_hash_code_sub_func(0, bytes2),
                 CryptographicUtils.kik_hash_code_sub_func(1, bytes2),
                 CryptographicUtils.kik_hash_code_sub_func(2, bytes2)]
        hash_code_base = -1964139357
        hash_code_offset = 7
        return (((hash_code_base ^ (ParsingUtilities.sign_extend_with_mask(array[0] << hash_code_offset))) ^ (
            ParsingUtilities.sign_extend_with_mask(array[5] << (hash_code_offset * 2)))) ^ (
                    ParsingUtilities.sign_extend_with_mask(array[1] << hash_code_offset))) ^ array[0]

    @staticmethod
    def kik_hash_code_sub_func(hash_id, bytes_array):
        j = 0
        if hash_id == 0:
            digest = hashlib.sha256(bytes_array).digest()
        elif hash_id == 1:
            digest = hashlib.sha1(bytes_array).digest()
        else:
            digest = hashlib.md5(bytes_array).digest()

        for i in range(0, len(digest), 4):
            j ^= ((((ParsingUtilities.byte_to_signed_int(digest[i + 3])) << 24) | (
                (ParsingUtilities.byte_to_signed_int(digest[i + 2])) << 16)) | (
                      (ParsingUtilities.byte_to_signed_int(digest[i + 1])) << 8)) | (ParsingUtilities.byte_to_signed_int(digest[i]))

        return j
