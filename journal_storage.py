import sys as _sys
from journal import storage as _implementation
_sys.modules[__name__] = _implementation
