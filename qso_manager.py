import sys as _sys
from journal import manager as _implementation
_sys.modules[__name__] = _implementation
