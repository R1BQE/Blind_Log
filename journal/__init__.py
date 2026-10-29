"""QSO journal domain package with lazy public exports."""

def __getattr__(name):
    if name == "QSOManager":
        from .manager import QSOManager
        return QSOManager
    raise AttributeError(name)
