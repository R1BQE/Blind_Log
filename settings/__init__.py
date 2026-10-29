"""Application settings package with lazy public exports."""

def __getattr__(name):
    if name == "SettingsManager":
        from .manager import SettingsManager
        return SettingsManager
    raise AttributeError(name)
