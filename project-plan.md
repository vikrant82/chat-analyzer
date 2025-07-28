# Chat Analyzer: Refactoring & Hardening Project Plan

Document Version: 2.4

Date: 2025-07-28

## 1\. Project Goals & Scope

### 1.1. Goals

The primary objectives of this refactoring initiative are to:

1.  **Secure the Application:** Remediate critical security vulnerabilities to protect user data and application integrity.
    
2.  **Improve Scalability:** Re-architect core components to ensure the application can scale beyond a single-process instance.
    
3.  **Reduce Technical Debt:** Refactor monolithic code structures and improve state management to increase maintainability and accelerate future development.
    
4.  **Establish a Quality Baseline:** Introduce an automated testing framework to ensure long-term stability and prevent regressions.
    

### 1.2. Scope

- **In-Scope:**
    
    - Complete replacement of the current session management system with a JWT Access/Refresh Token flow.
        
    - Externalization of all secrets from configuration files to environment variables.
        
    - Securing of public-facing webhook endpoints.
        
    - Migration of all ephemeral state and credential storage from in-memory variables and files to an external Redis instance.
        
    - Decomposition of the main `app.py` file into a modular, router-based structure.
        
    - Establishment of a `pytest` testing framework with initial unit and integration tests for critical paths.
        
    - Modularization of the primary `script.js` frontend file.
        
- **Out-of-Scope:**
    
    - Development of any new user-facing features.
        
    - Major UI/UX redesigns beyond what is necessary to support the refactoring.
        
    - Integration of any new third-party chat services or LLM providers.
        
    - Migration to a persistent database (e.g., PostgreSQL, MongoDB) for application data.
        

## 2\. Project Timeline & Sprints

This project is structured into three sequential sprints, focusing on delivering value incrementally.

- **Sprint 1: Security Hardening (1 Week: Jul 28 - Aug 03)**
    
    - **Goal:** Address all critical security vulnerabilities. The application should be demonstrably more secure by the end of this sprint, using a stateless JWT implementation and encrypted file storage as an interim solution.
- **Sprint 2: Core Architecture Refactor (2 Weeks: Aug 04 - Aug 17)**
    
    - **Goal:** Decouple state management by introducing Redis. This phase makes the application stateless, scalable, and adds robust session revocation.
- **Sprint 3: Quality & Maintainability (1 Week: Aug 18 - Aug 24)**
    
    - **Goal:** Build the foundation for long-term quality by introducing automated testing and refining the code structure.

## 3\. Detailed Task Breakdown

### **Phase 1: Security Hardening (Sprint 1)**

#### Task 1.1: Implement JWT Access/Refresh Token Authentication

- **Owner:** Vikrant
    
- **Estimated Effort:** 3 Days
    
- **Description:** Replace the current simple token system with a standard, secure two-token flow. This iteration will be stateless (no Redis dependency) but will use secure storage for external credentials.
    
- **Acceptance Criteria:**
    
    1.  **Backend - Token Issuance:** Generates a short-lived JWT Access Token and a long-lived JWT Refresh Token, returned in `HttpOnly` cookies. The `sub` claim of the JWT will contain the user's unique ID from the external service (e.g., Webex Person ID).
        
    2.  **Backend - Secure Credential Storage:** The user's external credentials (Webex OAuth tokens, Telegram session data) are stored in a single, server-side encrypted file. This file will contain a dictionary mapping the user's unique ID (the `sub` claim from our JWT) to their respective credentials. This replaces the insecure plaintext files and establishes a clear link between our internal session and the external credentials.
        
    3.  **Backend - Refresh Endpoint:** A `/api/auth/refresh` endpoint validates the refresh token JWT and issues a new access token.
        
    4.  **Frontend - Silent Refresh Logic:** The frontend intercepts `401 Unauthorized` responses and uses the refresh endpoint to get a new access token, then retries the failed request.
        
    5.  **Cleanup:** The old token and credential files (`app_sessions.json`, `webex_tokens.json`) are removed.
        

#### Task 1.2: Externalize Application Secrets

- **Owner:** Vikrant
    
- **Estimated Effort:** 1 Day
    
- **Acceptance Criteria:**
    
    - No secrets remain in `config.json`.
        
    - All secrets are loaded from environment variables (`.env` file for local dev).
        
    - `docker-compose.yaml` and `README.md` are updated accordingly.
        

#### Task 1.3: Secure Bot Webhook Endpoints

- **Owner:** Vikrant
    
- **Estimated Effort:** 1 Day
    
- **Acceptance Criteria:**
    
    - The Telegram webhook URL no longer contains the bot token.
        
    - The webhook handler validates the `X-Telegram-Bot-Api-Secret-Token` header.
        

### **Phase 2: Architectural Refactoring (Sprint 2)**

#### Task 2.1: Decouple State Management with Redis

- **Owner:** Vikrant
    
- **Estimated Effort:** 4 Days
    
- **Dependencies:** Docker environment; Task 1.1 complete.
    
- **Description:** Migrate all ephemeral and session-related state from in-memory variables and the interim encrypted file to a centralized Redis instance.
    
- **Acceptance Criteria:**
    
    1.  **Setup:** Redis is added to `docker-compose.yaml` and `redis-py` is added to `requirements.txt`.
        
    2.  **Migration:** All global variables (`message_cache`, `chat_modes`) and the encrypted credential file are replaced with Redis data structures.
        
    3.  **Revocation:** The refresh token logic is enhanced to use a Redis allowlist, enabling immediate session revocation upon logout.
        
    4.  **Statelessness:** The application is now fully stateless and can be scaled horizontally.
        

#### Task 2.2: Decompose Monolithic `app.py`

- **Owner:** Vikrant
    
- **Estimated Effort:** 3 Days
    
- **Dependencies:** Task 2.1.
    
- **Acceptance Criteria:**
    
    - A new `/routers` directory exists.
        
    - API endpoints are logically grouped into separate files (e.g., `auth.py`, `chat.py`, `bots.py`) using `APIRouter`.
        
    - The main `app.py` is significantly smaller.
        

### **Phase 3: Quality & Maintainability (Sprint 3)**

#### Task 3.1: Establish a Testing Framework

- **Owner:** Vikrant
    
- **Estimated Effort:** 3 Days
    
- **Acceptance Criteria:**
    
    - `pytest` is integrated. A `/tests` directory is created.
        
    - Unit tests are written for at least two non-I/O components.
        
    - Integration tests using `TestClient` are written for the main authentication flow (login, refresh, logout).
        
    - `README.md` is updated with instructions on running tests.
        

#### Task 3.2: Refine Frontend Code Structure

- **Owner:** Vikrant
    
- **Estimated Effort:** 2 Days
    
- **Acceptance Criteria:**
    
    - `static/script.js` is broken down into smaller, single-responsibility ES modules.
        
    - `index.html` is updated to load the main script as a module.
        
    - Frontend functionality remains identical.
        

## 4\. Risk Assessment

|     |     |     |     |     |
| --- | --- | --- | --- | --- |
| **Risk ID** | **Description** | **Probability** | **Impact** | **Mitigation Strategy** |
| **R-01** | **Regression:** Refactoring core authentication or state management introduces functional bugs. | Medium | High | **Task 3.1 (Testing):** The introduction of an automated test suite is the primary mitigation. Manual testing will be performed at the end of each sprint. |
| **R-02** | **Scope Creep:** The desire to add "just one more fix" or a small feature during the refactoring process. | Medium | Medium | Adhere strictly to the defined scope. All new feature ideas will be logged in a backlog for consideration after this project is complete. |
| **R-03** | **Effort Underestimation:** The complexity of a task, particularly the Redis integration or the frontend `401` interceptor, is greater than estimated. | Low | Medium | The timeline includes some buffer. Quality of the implementation will be prioritized over meeting a strict deadline. |