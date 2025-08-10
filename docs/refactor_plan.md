# App.py Refactoring Plan

This document outlines the plan and progress for refactoring the monolithic `app.py` file into a more maintainable, service-oriented architecture.

## Key Architectural Decisions

During our session, we made the following key architectural decisions:

1.  **Separation of Concerns:** We agreed to decompose `app.py` by separating API endpoint definitions (the "what") from the business logic (the "how").
2.  **Router Layer:** All FastAPI endpoints will be moved into dedicated files within a new `/routers` directory. This keeps the main `app.py` file clean and focused on application setup.
3.  **Service Layer:** All business logic and state management will be encapsulated within dedicated files in a new `/services` directory. Routers will call these services, but services will not expose their internal state directly.
4.  **Circular Dependency Resolution:** We identified and resolved a circular dependency between the `app` and the `downloads` router by creating a dedicated `auth_service` to manage user sessions. This was a critical step to enable further modularization.
5.  **LLM Abstraction:** We introduced an `LLMManager` to encapsulate all LLM client logic, providing a single, unified interface for the rest of the application. This removes global state and decouples the services from the specifics of the LLM clients.

## Refactoring Status

### Completed
- [x] **Phase 1: Full Authentication Refactor**
- [x] **Phase 2: Download Logic Refactor**

- [x] **Phase 3: Chat Logic Refactor**
- [x] **Phase 4: Bot Management & Webhook Refactor**
- [x] **Phase 5: Final Cleanup & Validation**
- [x] **Phase 6: LLM Manager Refactor**