import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class Settings:
    """A centralized class for managing application settings."""

    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found at {self.config_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.config_path}")
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value."""
        return self.config.get(key, default)

    def get_telegram_config(self) -> Dict[str, Any]:
        return self.get('telegram', {})

    def get_webex_config(self) -> Dict[str, Any]:
        return self.get('webex', {})

    def get_google_ai_config(self) -> Dict[str, Any]:
        return self.get('google_ai', {})

    def get_openai_compatible_configs(self) -> List[Dict[str, Any]]:
        return self.get('openai_compatible', [])

    def get_bots_config(self, backend: str) -> List[Dict[str, Any]]:
        return self.get('bots', {}).get(backend, [])

    def save_bots_config(self, backend: str, bots: List[Dict[str, Any]]):
        if 'bots' not in self.config:
            self.config['bots'] = {}
        self.config['bots'][backend] = bots
        self._save_config()

    def _save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save configuration to {self.config_path}: {e}")
            raise

# Create a single instance to be used throughout the application
settings = Settings()