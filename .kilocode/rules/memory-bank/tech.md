# Technical Stack and Setup

## 1. Core Technologies
- **Backend:** Python 3.11+ with the FastAPI framework.
- **Frontend:** Standard HTML, CSS, and vanilla JavaScript (ES6 Modules). The frontend is built as a modular single-page application without complex frameworks to ensure simplicity and broad compatibility.
- **Containerization:** Docker and Docker Compose are used for building, shipping, and running the application in a consistent environment.

## 2. Key Dependencies
- **`fastapi`:** The core web framework for building the API.
- **`uvicorn`:** The ASGI server that runs the FastAPI application.
- **`telethon`:** A powerful Python library for interacting with the Telegram user API.
- **`httpx`:** A modern, asynchronous HTTP client used for all Webex API interactions and for communicating with bot webhooks.
- **`python-multipart`:** Required by FastAPI for handling form data, used in file uploads and other form-based interactions.
- **`google-generativeai`:** The official Python client for the Google AI (Gemini) API.
- **`pydantic`:** Used extensively by FastAPI for data validation and settings management. It ensures that API requests and responses conform to the defined data models.
- **`fpdf2`:** A library for PDF document generation, used in the download service to create PDF transcripts.

A complete list of dependencies can be found in the [`requirements.txt`](./requirements.txt) file.

## 3. Development Setup
The recommended development setup involves running the application directly with Python in a virtual environment.

1.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Create and configure `config.json`:** This file is essential and must contain API keys for Telegram, Webex, and at least one LLM provider.
4.  **Run the development server:**
    ```bash
    uvicorn app:app --reload
    ```
    The `--reload` flag enables hot-reloading, which automatically restarts the server whenever code changes are detected.

## 4. Deployment
The primary deployment method is via Docker.
- **Pre-built Image:** The `docker-compose.yaml` file is configured to pull the latest pre-built image from Docker Hub, which is the simplest way to get the application running.
- **Local Build:** The `docker-compose-localbuild.yaml` file is provided for developers who need to build the Docker image from the local source code. This is useful for testing changes before pushing them.

Both Docker setups use named volumes to persist the `sessions/` and `cache/` directories, ensuring that user login data and cached messages are not lost when the container is restarted.

## 5. Tool Usage Patterns
- **Linting and Formatting:** While not explicitly enforced by a CI pipeline in this project, standard Python tools like `black` for formatting and `flake8` or `ruff` for linting are recommended to maintain code quality.
- **IDE:** The project is IDE-agnostic, but using an editor with strong Python support like Visual Studio Code is beneficial for development.