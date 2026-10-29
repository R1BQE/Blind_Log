import sys as _sys
from journal import operations as _implementation
_sys.modules[__name__] = _implementation
