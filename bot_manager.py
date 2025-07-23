import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class BotManager:
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

    def _save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save configuration to {self.config_path}: {e}")
            raise

    def register_bot(self, backend: str, name: str, token: str, bot_id: str) -> None:
        if backend not in self.config.get('bots', {}):
            self.config['bots'][backend] = []
        
        if any(bot['name'] == name for bot in self.config['bots'][backend]):
            raise ValueError(f"A bot with the name '{name}' already exists for {backend}.")

        new_bot = {"name": name, "token": token, "bot_id": bot_id}
        self.config['bots'][backend].append(new_bot)
        self._save_config()

    def get_bots(self, backend: str) -> List[Dict[str, str]]:
        bots = self.config.get('bots', {}).get(backend, [])
        return [{"name": bot["name"]} for bot in bots]

    def get_bot_by_token(self, backend: str, token: str) -> Optional[Dict[str, str]]:
        bots = self.config.get('bots', {}).get(backend, [])
        return next((bot for bot in bots if bot.get('token') == token), None)

    def delete_bot(self, backend: str, name: str) -> None:
        bots = self.config.get('bots', {}).get(backend, [])
        bot_to_remove = next((bot for bot in bots if bot['name'] == name), None)
        
        if not bot_to_remove:
            raise ValueError(f"Bot '{name}' not found for {backend}.")
        
        self.config['bots'][backend] = [bot for bot in bots if bot['name'] != name]
        self._save_config()
