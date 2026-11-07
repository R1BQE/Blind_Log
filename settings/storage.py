"""
Settings storage layer - isolates file I/O from business logic.
No dependencies on wx or any UI framework.
"""
import configparser
import os
import tempfile
from logger import log_error, log_exception


class SettingsStorage:
    """
    Isolates file I/O for settings.
    Handles reading/writing settings.ini without any business logic.
    """
    
    def __init__(self, config_file='settings.ini'):
        self.config_file = config_file
    
    def file_exists(self):
        """Check if settings file exists."""
        return os.path.exists(self.config_file)
    
    def load_config(self):
        """
        Load configuration from file.
        
        Returns:
            tuple: (configparser.ConfigParser, bool) 
            bool is True if file was created (didn't exist before)
        """
        config = configparser.ConfigParser()
        file_created = False
        
        if not self.file_exists():
            file_created = True
            return config, file_created
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config.read_file(f)
        except UnicodeDecodeError:
            # Try reading with cp1251 encoding (old Windows encoding).
            try:
                with open(self.config_file, 'r', encoding='cp1251') as f:
                    config.read_file(f)
            except (OSError, configparser.Error) as e:
                log_exception(f"Failed to load settings with cp1251: {e}")
                raise OSError(f"Cannot read settings file '{self.config_file}': {e}") from e
        except (OSError, configparser.Error) as e:
            log_exception(f"Failed to load settings: {e}")
            raise OSError(f"Cannot read settings file '{self.config_file}': {e}") from e

        return config, file_created
    
    def save_config(self, config):
        """Atomically save configuration so an interrupted write keeps old settings."""
        temporary_path = None
        descriptor = None
        try:
            target_path = os.path.abspath(self.config_file)
            target_dir = os.path.dirname(target_path)
            os.makedirs(target_dir, exist_ok=True)
            descriptor, temporary_path = tempfile.mkstemp(
                prefix=os.path.basename(target_path) + ".",
                suffix=".tmp",
                dir=target_dir,
            )
            with os.fdopen(
                descriptor, "w", encoding="utf-8", newline="\\n"
            ) as stream:
                descriptor = None
                config.write(stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, target_path)
            temporary_path = None
        except (OSError, configparser.Error) as error:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass
            log_error(f"Failed to save settings: {error}")
            raise IOError(f"Failed to save settings: {error}") from error
