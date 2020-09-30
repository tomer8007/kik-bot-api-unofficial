from kik_unofficial.utilities.strong_hash_map import StrongHashMap
from kik_unofficial.utilities.linked_hash_map import Mapping
from collections import OrderedDict

BaseOrdering = 0
ExtendedOrdering = 1


class SortedMap(StrongHashMap):
    """
    The java SortedMap class translated to python
    """
    def __init__(self, map, sort_mode):
        super().__init__()

        map = OrderedDict(map)

        arr = map.keys()
        arr = sorted(arr)
        new_map = Mapping(map)
        for i in arr:
            new_map[i] = map.get(i)

        hash_code_base = -1964139357
        hash_code_offset = 7
        if sort_mode == BaseOrdering:
            hash_code_base = -310256979
            hash_code_offset = 13

        self.set_hash_code_base(hash_code_base)
        self.set_hash_code_offset(hash_code_offset)

        while len(new_map):
            shm = StrongHashMap(new_map)

            shm.set_hash_code_base(hash_code_base)
            shm.set_hash_code_offset(hash_code_offset)

            if shm.keys():
                next_ = list(shm.keys())[0]
                k = next_
                v = shm.get(k)

                hash_code = shm.hash_code()

                hash_code = hash_code % len(shm)
                indx = hash_code
                if hash_code < 0:
                    indx = hash_code + len(shm)

                remove = arr.pop(indx)
                self.put(remove, new_map.get(remove))
                new_map.remove(remove)

    def to_string(self):
        string_out = ''
        z = True
        for k, v in self.items():
            if not z:
                string_out += ' '

            z = False
            string_out += str(k)
            string_out += '="'
            string_out += str(v)
            string_out += '"'

        return string_out
