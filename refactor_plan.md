# App.py Refactoring Plan

This document outlines the plan and progress for refactoring the monolithic `app.py` file into a more maintainable, service-oriented architecture.

## Key Architectural Decisions

During our session, we made the following key architectural decisions:

1.  **Separation of Concerns:** We agreed to decompose `app.py` by separating API endpoint definitions (the "what") from the business logic (the "how").
2.  **Router Layer:** All FastAPI endpoints will be moved into dedicated files within a new `/routers` directory. This keeps the main `app.py` file clean and focused on application setup.
3.  **Service Layer:** All business logic and state management will be encapsulated within dedicated files in a new `/services` directory. Routers will call these services, but services will not expose their internal state directly.
4.  **Circular Dependency Resolution:** We identified and resolved a circular dependency between the `app` and the `downloads` router by creating a dedicated `auth_service` to manage user sessions. This was a critical step to enable further modularization.

## Refactoring Status

### Completed
- [x] **Phase 1: Full Authentication Refactor**
- [x] **Phase 2: Download Logic Refactor**

### Pending
- [ ] **Phase 3: Chat Logic Refactor**
  - [ ] Create `routers/chat.py` and `services/chat_service.py`.
  - [ ] Move the `/api/chat` endpoint and its helper functions (`_format_messages_for_llm`, `_normalize_stream`) to the new modules.
  - [ ] Refactor the chat router to be a thin layer that calls the chat service.
- [ ] **Phase 4: Bot Management & Webhook Refactor**
  - [ ] Create `routers/bot_management.py` and `routers/bot_webhooks.py`.
  - [ ] Create a `services/bot_service.py`.
  - [ ] Move the bot management and webhook endpoints to their respective routers.
  - [ ] Move the bot-related helper functions to the bot service.
  - [ ] Refactor the bot routers to use the bot service.
- [ ] **Phase 5: Final Cleanup & Validation**
  - [ ] Update `app.py` to include all new routers.
  - [ ] Remove any remaining business logic from `app.py`.
  - [ ] Perform a full validation of the entire application.