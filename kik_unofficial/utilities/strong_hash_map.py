import hashlib
from kik_unofficial.utilities.linked_hash_map import Mapping
from bitstring import Bits

def convert_byte_to_signed(i):
    b = bin(i).split('b', 1)[1]
    b = f'{b:0>8}'
    if b.startswith('1'):
        b = b[1:]
        i = int(b, 2) - 128
    return i

def signed_bitshift(i,a,left=True):
    if i < 0:
        i = i + 2**32
    
    if left:
        i = i << a
    else:
        i = i >> a
        
    b = bin(i).split('b',1)[1]
    if len(b) > 32:
        b = b[-32:]
        i = Bits(bin=b).int
    return i

class StrongHashMap(Mapping):
    def __init__(self,new_map = {}):
        super().__init__(new_map)
            
        self.hl_s256 = hashlib.sha256
        self.hl_s1 = hashlib.sha1
        self.hl_md5 = hashlib.md5
        
        self.hash_funcs = [self.hl_s256,self.hl_s1,self.hl_md5]
        self.b = 0
        self.c = 0
        
    def set_hash_code_base(self, i):
        self.b = i

    def set_hash_code_offset(self, i):
        self.c = i
        
    def a(self, i, b_arr):
        hash_func = self.hash_funcs[i]
        
        digest = None
        j = 0
        
        if hash_func:
            digest = hash_func(b_arr).digest()
            
            digest = [convert_byte_to_signed(i) for i in digest]
            
            i2 = 0
            while i2 < len(digest):
                
                _a = digest[i2 + 3] << 24
                _b = digest[i2 + 2] << 16
                _c = digest[i2 + 1] << 8
                _d = digest[i2]
                
                pj = ((((_a) | (_b)) | (_c)) | _d)
                
                j ^= pj

                i2 += 4


        return j

    def hash_code(self):
        str_1 = ''
        str_2 = ''
        
        arr = self.keys()
        arr = sorted(arr)
        
        clone = list(arr)
        clone = clone[::-1]
        
        for k in arr:
            str_1 += str(k)
            str_1 += str(self.get(k))
            
        for k in clone:
            str_2 += str(k)
            str_2 += str(self.get(k))

        bytes_1 = str_1.encode()
        bytes_2 = str_2.encode()
        
        i_arr = [
            self.a(0, bytes_1),
            self.a(1, bytes_1),
            self.a(2, bytes_1),
            self.a(0, bytes_2),
            self.a(1, bytes_2),
            self.a(2, bytes_2),
        ]
        
        j = (((self.b ^ signed_bitshift(i_arr[0], self.c)) ^ signed_bitshift(i_arr[5], (self.c * 2))) ^ signed_bitshift(i_arr[1], self.c)) ^ i_arr[0]
        
        return j
