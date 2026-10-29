import sys as _sys
from services import update_service as _implementation
_sys.modules[__name__] = _implementation
