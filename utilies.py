from collections import namedtuple
from abc import ABCMeta

ValueRange = namedtuple('ValueRange', ['min', 'default', 'max', 'step'], defaults=(None,))

class RangeCollectorMeta(ABCMeta):
    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)
        params = {}
        for base in reversed(cls.__mro__):
            for k, v in getattr(base, "__dict__", {}).items():
                if k.endswith("_RANGE") and isinstance(v, ValueRange):
                    params[k[:-6].lower()] = v
        cls.PARAMETERS = params
        return cls