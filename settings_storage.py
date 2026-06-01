"""
Settings storage layer - isolates file I/O from business logic.
No dependencies on wx or any UI framework.
"""
import configparser
import os
from logger import log_error


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
            # Try reading with cp1251 encoding (old Windows encoding)
            try:
                with open(self.config_file, 'r', encoding='cp1251') as f:
                    config.read_file(f)
            except (FileNotFoundError, OSError) as e:
                log_error(f"Failed to load settings with cp1251: {e}")
        except (FileNotFoundError, OSError) as e:
            log_error(f"Failed to load settings: {e}")
        
        return config, file_created
    
    def save_config(self, config):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
        except (FileNotFoundError, OSError) as e:
            log_error(f"Failed to save settings: {e}")
            raise IOError(f"Failed to save settings: {e}")
