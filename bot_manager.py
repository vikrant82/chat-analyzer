import logging
from typing import List, Optional, Dict, Any

from config import settings

logger = logging.getLogger(__name__)

class BotManager:
    def register_bot(self, backend: str, name: str, token: str, bot_id: str) -> None:
        bots = settings.get_bots_config(backend)
        if any(bot['name'] == name for bot in bots):
            raise ValueError(f"A bot with the name '{name}' already exists for {backend}.")

        new_bot = {"name": name, "token": token, "bot_id": bot_id}
        bots.append(new_bot)
        settings.save_bots_config(backend, bots)

    def get_bots(self, backend: str) -> List[Dict[str, str]]:
        bots = settings.get_bots_config(backend)
        return [{"name": bot["name"]} for bot in bots]

    def get_bot_by_token(self, backend: str, token: str) -> Optional[Dict[str, str]]:
        bots = settings.get_bots_config(backend)
        return next((bot for bot in bots if bot.get('token') == token), None)

    def delete_bot(self, backend: str, name: str) -> None:
        bots = settings.get_bots_config(backend)
        bot_to_remove = next((bot for bot in bots if bot['name'] == name), None)
        
        if not bot_to_remove:
            raise ValueError(f"Bot '{name}' not found for {backend}.")
        
        updated_bots = [bot for bot in bots if bot['name'] != name]
        settings.save_bots_config(backend, updated_bots)
