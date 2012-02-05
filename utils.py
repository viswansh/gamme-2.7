
class Bunch(object):
    def __init__(self, **kwds):
        self.__dict__ = kwds

    def __setitem__(self, key, val):
        self.__dict__[key] = val

    def __getitem__(self, key):
        if key in  self.__dict__:
            return self.__dict__[key]
        return None
