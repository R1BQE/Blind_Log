import sys as _sys
from services import updater as _implementation
_sys.modules[__name__] = _implementation
