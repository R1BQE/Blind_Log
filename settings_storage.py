import sys as _sys
from settings import storage as _implementation
_sys.modules[__name__] = _implementation
