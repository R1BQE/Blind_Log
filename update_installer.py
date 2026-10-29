import sys as _sys
from services import update_installer as _implementation
_sys.modules[__name__] = _implementation
