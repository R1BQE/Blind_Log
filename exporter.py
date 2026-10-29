import sys as _sys
from adif import exporter as _implementation
_sys.modules[__name__] = _implementation
