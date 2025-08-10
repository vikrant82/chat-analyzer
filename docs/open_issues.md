# Open Issues

## 1. Global Bot Configuration

**Date:** 2025-08-10

**Problem:**
The bot configuration is maintained globally in the `config.json` file. If multiple users are using the application, there is no user-specific section for bots in the configuration. This means all users share the same bot configurations, which is not ideal for a multi-user environment.

**Expected Behavior:**
The bot configuration should be user-specific, allowing each user to register and manage their own bots without affecting other users.

**Task:**
Investigate a solution for user-specific bot configurations. This might involve:
- Modifying the `bot_manager.py` to handle user-specific bot data.
- Changing the storage mechanism for bot configurations (e.g., moving it from `config.json` to a database or user-specific files).
- Updating the bot management UI and API endpoints to support user-specific bot operations.