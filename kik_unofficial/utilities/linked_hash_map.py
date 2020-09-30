from collections import OrderedDict
class Mapping:
    """
    The parts of the java class LinkedHashMap needed for MakeAnonymousStreamInitTag
    """
    def __init__(self, map={}):
        self.map = OrderedDict(map) # for backwards compatability

    def __setitem__(self, key, item):
        self.map[key] = item

    def __getitem__(self, key):
        return self.map[key]

    def __repr__(self):
        return repr(self.map)

    def __len__(self):
        return len(self.map)

    def __delitem__(self, key):
        del self.map[key]

    def clear(self):
        return self.map.clear()

    def copy(self):
        return self.map.copy()

    def has_key(self, k):
        return k in self.map

    def update(self, *args, **kwargs):
        return self.map.update(*args, **kwargs)

    def keys(self):
        return self.map.keys()

    def values(self):
        return self.map.values()

    def items(self):
        return self.map.items()

    def pop(self, *args):
        return self.map.pop(*args)

    def __cmp__(self, dict_):
        return self.__cmp__(self.map, dict_)

    def __contains__(self, item):
        return item in self.map

    def __iter__(self):
        return iter(self.map)

    def __unicode__(self):
        return unicode(repr(self.map))

    def get(self, key):
        return self.map.get(key)

    def put(self, key, val):
        self.map[key] = val

    def remove(self, key):
        if key in self.map:
            del self.map[key]