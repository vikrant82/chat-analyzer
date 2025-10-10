import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self, bots_file: str = 'bots.json'):
        self.bots_file = bots_file
        self.bots_data = self._load_bots_data()

    def _load_bots_data(self) -> Dict[str, Any]:
        try:
            with open(self.bots_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Bots file not found at {self.bots_file}. A new one will be created.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.bots_file}")
            return {}

    def _save_bots_data(self):
        try:
            with open(self.bots_file, 'w') as f:
                json.dump(self.bots_data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save bots data to {self.bots_file}: {e}")
            raise

    def register_bot(self, user_id: str, backend: str, name: str, token: str, bot_id: str) -> None:
        if user_id not in self.bots_data:
            self.bots_data[user_id] = {}
        if backend not in self.bots_data[user_id]:
            self.bots_data[user_id][backend] = []

        if any(bot['name'] == name for bot in self.bots_data[user_id][backend]):
            raise ValueError(f"A bot with the name '{name}' already exists for {backend} for this user.")

        new_bot = {"name": name, "token": token, "bot_id": bot_id}
        self.bots_data[user_id][backend].append(new_bot)
        self._save_bots_data()

    def get_bots(self, user_id: str, backend: str) -> List[Dict[str, str]]:
        user_bots = self.bots_data.get(user_id, {})
        backend_bots = user_bots.get(backend, [])
        return [{"name": bot["name"]} for bot in backend_bots]

    def get_bot_by_token(self, backend: str, token: str) -> Optional[Dict[str, str]]:
        for user_id, backends in self.bots_data.items():
            if backend in backends:
                for bot in backends[backend]:
                    if bot.get('token') == token:
                        return bot
        return None

    def delete_bot(self, user_id: str, backend: str, name: str) -> None:
        user_bots = self.bots_data.get(user_id, {})
        backend_bots = user_bots.get(backend, [])
        
        bot_to_remove = next((bot for bot in backend_bots if bot['name'] == name), None)
        
        if not bot_to_remove:
            raise ValueError(f"Bot '{name}' not found for {backend} for this user.")
        
        self.bots_data[user_id][backend] = [bot for bot in backend_bots if bot['name'] != name]
        self._save_bots_data()
