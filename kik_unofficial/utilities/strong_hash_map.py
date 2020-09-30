import hashlib
from kik_unofficial.utilities.linked_hash_map import Mapping
from bitstring import Bits

# from StrongHashMap.java

def convert_byte_to_signed(i):
    b = bin(i).split('b', 1)[1]
    b = '{:0>8}'.format(b) # padding
    
    if b.startswith('1'): # if signed
        b = b[1:]
        i = int(b, 2) - 128
        
    return i

def signed_bitshift(number, amount, left=True):
    if number < 0:
        number = number + 2**32
    
    if left:
        number = number << amount
    else:
        number = number >> amount
        
    b = bin(number).split('b',1)[1] # strip everything but the binary digits
    
    if len(b) > 32:
        b = b[-32:]
        number = Bits(bin=b).int
        
    return number

class StrongHashMap(Mapping):
    def __init__(self,new_map = {}):
        super().__init__(new_map)
        self.hash_funcs = [hashlib.sha256, hashlib.sha1, hashlib.md5]
        self.base = 0
        self.offset = 0
        
    def set_hash_code_base(self, i):
        self.base = i

    def set_hash_code_offset(self, i):
        self.offset = i
        
    def hash_bytes(self, mode, byte_arr):
        hash_func = self.hash_funcs[mode]
        
        digest = None
        j = 0
        
        if hash_func:
            digest = hash_func(byte_arr).digest()
            
            digest = [convert_byte_to_signed(i) for i in digest]
            
            i2 = 0
            while i2 < len(digest):
                
                a = digest[i2 + 3] << 24
                b = digest[i2 + 2] << 16
                c = digest[i2 + 1] << 8
                d = digest[i2]
                
                pj = ((((a) | (b)) | (c)) | d)
                
                j ^= pj

                i2 += 4

        return j

    def hash_code(self):
        str_1 = ''
        str_2 = ''
        
        keys = self.keys()
        keys = sorted(keys)
        
        clone = list(keys)
        clone = clone[::-1]
        
        for key in keys:
            str_1 += str(key)
            str_1 += str(self.get(key))
            
        for key in clone:
            str_2 += str(key)
            str_2 += str(self.get(key))

        bytes_1 = str_1.encode()
        bytes_2 = str_2.encode()
        
        arr = [
            self.hash_bytes(0, bytes_1),
            self.hash_bytes(1, bytes_1),
            self.hash_bytes(2, bytes_1),
            self.hash_bytes(0, bytes_2),
            self.hash_bytes(1, bytes_2),
            self.hash_bytes(2, bytes_2),
        ]
        
        j = (((self.base ^ signed_bitshift(arr[0], self.offset)) ^ signed_bitshift(arr[5], (self.offset * 2))) ^ signed_bitshift(arr[1], self.offset)) ^ arr[0]
        
        return j
