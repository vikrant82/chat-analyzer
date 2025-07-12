### **Project Knowledge Base: `[chat_analyzer]`**

**1. High-Level Summary**
   - **Purpose:** What is the primary goal of this project? What problem does it solve?
   - **User:** Who is the intended user of this application? (e.g., developers, end-consumers, business analysts)
   - **Core Functionality:** In a few bullet points, describe the main features.

**2. Technology Stack**
   - **Languages:** List all programming languages used (e.g., Python, TypeScript, Java).
   - **Frameworks:** Identify major frameworks for frontend, backend, and testing (e.g., React, Node.js/Express, Django, pytest, Jest).
   - **Key Libraries/Dependencies:** List the most critical third-party libraries and their purpose (e.g., `axios` for HTTP requests, `pandas` for data manipulation, `Mongoose` for MongoDB interaction). Reference the primary dependency file (e.g., `package.json`, `requirements.txt`).
   - **Database:** Identify the database system used, if any (e.g., PostgreSQL, MongoDB, SQLite).

**3. Directory Structure Map**
   - Provide a high-level map of the most important directories and their roles. Do not list every file, but explain the purpose of the key folders.
   - **Example:**
     - `/src`: Main application source code.
     - `/src/components`: Reusable UI components.
     - `/src/api`: Logic for making external API calls.
     - `/server`: Backend server code.
     - `/tests`: All automated tests.
     - `/scripts`: Build or utility scripts.
     - `/public`: Static assets served to the client.

**4. Execution & Entry Points**
   - **How to Run Locally:** What command(s) are used to start the application for development? (e.g., `npm run dev`, `python main.py`).
   - **Main Entry Files:** What are the primary entry point files for the application? (e.g., `src/index.tsx` for the frontend, `server/index.js` for the backend).
   - **Build Process:** How is the project built for production? (e.g., `npm run build`).

**5. Architecture & Core Logic**
   - **Key Modules/Components:** Identify and describe the most critical files or modules that contain the core business logic. Explain their responsibility.
     - **File:** `[path/to/important/file.js]`
     - **Responsibility:** [Brief description of what this file does].
   - **Data Flow:** Describe how data moves through the system. For a web app, this might be: `User Interaction -> React Component -> State Management (Redux/Context) -> API Service Call -> Backend API Endpoint -> Database`.
   - **State Management:** If applicable, describe the state management strategy (e.g., Redux, Zustand, React Context, Vuex).

**6. API & External Interactions**
   - **Internal APIs:** If the project has a backend, list the main API endpoints defined and what they do.
     - `POST /api/users`: Creates a new user.
     - `GET /api/products/:id`: Fetches a single product.
   - **External Services:** List any external APIs or services the application communicates with (e.g., Stripe for payments, S3 for file storage, Google Maps API).

**7. Configuration & Environment**
   - **Configuration Files:** Where is the project configuration stored? (e.g., `.env`, `config.json`, `settings.py`).
   - **Environment Variables:** List the key environment variables required to run the application and a brief description of each (e.g., `DATABASE_URL`, `API_KEY`). Do not include actual secret values.

**8. Testing**
   - **Testing Frameworks:** What frameworks are used for testing? (e.g., Jest, pytest, Cypress).
   - **Test Location:** Where are the tests located? (e.g., `__tests__` directories, `tests/` folder).
   - **How to Run Tests:** What command is used to execute the test suite? (e.g., `npm test`).

**9. Missing Information & Inferences**
   - Explicitly state any critical information that appears to be missing (e.g., "No clear deployment script found," "Testing strategy is not defined," "Error handling seems inconsistent").