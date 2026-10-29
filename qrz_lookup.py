import sys as _sys
from services import qrz_lookup as _implementation
_sys.modules[__name__] = _implementation
