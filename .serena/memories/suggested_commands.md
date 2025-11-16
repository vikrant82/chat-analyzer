# Development Commands and Workflow

## Running the Application

### Local Development (Python)
```bash
# Recommended: Use virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app:app --reload

# Run on custom host/port
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Deployment

#### Pre-built Image (Docker Hub)
```bash
docker-compose up -d
# Uses vikrant82/chat-analyzer:latest
```

#### Local Build
```bash
docker-compose -f docker-compose-localbuild.yaml up --build -d
```

## Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/services/test_chat_service.py

# Run with output capture disabled
pytest -s

# Configuration in pytest.ini:
# - testpaths = tests
# - python_files = test_*.py
# - python_classes = Test*
# - python_functions = test_*
# - addopts = -v -s
```

### Test Dependencies
- `pytest`
- `pytest-mock`
- `pytest-asyncio`
- `respx`

## Bot Management CLI

```bash
# Add a bot
python bot_cli.py add <backend> <name> <user_id>
# Example: python bot_cli.py add telegram MyBot 123456789

# List bots
python bot_cli.py list <user_id>
# Filter by backend: python bot_cli.py list <user_id> --backend telegram

# Remove a bot
python bot_cli.py remove <user_id> <backend> <name>
# Example: python bot_cli.py remove 123456789 telegram MyBot
```

## Code Quality Tools

### Linting
**Note**: No linting configuration found in the project (no `.flake8`, `pylint.rc`, or `pyproject.toml` with linting config).

Recommended for future:
```bash
# Install linters
pip install flake8 pylint black

# Run linting
flake8 .
pylint **/*.py
```

### Formatting
**Note**: No formatter configuration found.

Recommended for future:
```bash
# Format code with black
black .

# Check formatting without changes
black --check .
```

## Git Workflow

### Repository Info
- **Owner**: vikrant82
- **Repo**: chat-analyzer
- **Branch**: main

### Common Commands (macOS)
```bash
# Check status
git status

# Stage changes
git add .

# Commit
git commit -m "Description of changes"

# Push to remote
git push origin main

# Pull latest
git pull origin main

# View logs
git log --oneline

# Create branch
git checkout -b feature-branch-name

# View diffs
git diff
```

## macOS-Specific System Commands

### File Operations
```bash
# List files
ls -la

# Navigate directories
cd /path/to/directory

# Find files
find . -name "*.py"
mdfind -name "filename"  # macOS Spotlight search

# Search in files
grep -r "pattern" .
```

### Process Management
```bash
# List processes
ps aux | grep python

# Kill process
kill -9 <pid>

# View port usage
lsof -i :8000
```

### Environment
```bash
# Check Python version
python3 --version

# Which Python
which python3

# Environment variables
export VAR_NAME=value
echo $VAR_NAME
```

## Configuration Management

### Required Files
1. **`config.json`**: Create from `example-config.json`
   - Telegram API credentials
   - Webex OAuth settings
   - Reddit OAuth settings
   - LLM provider configurations

### Environment Variables (Optional)
- `HOST`: Server host (default: from config or 0.0.0.0)
- `PORT`: Server port (default: from config or 8000)
- `RELOAD`: Enable auto-reload (default: false)

## Project Maintenance

### Update Dependencies
```bash
# Update requirements.txt after adding packages
pip freeze > requirements.txt

# Install from requirements.txt
pip install -r requirements.txt
```

### Clean Cache
```bash
# Remove Python cache
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Remove session files (if needed)
rm -rf sessions/*

# Clear message cache
rm -rf cache/*
```

### Docker Maintenance
```bash
# View logs
docker-compose logs -f

# Stop containers
docker-compose down

# Rebuild
docker-compose up --build

# Remove volumes
docker-compose down -v
```

## Debugging

### Enable Debug Logging
Modify `app.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Interactive Debugging
```python
# Add breakpoint
import pdb; pdb.set_trace()
```

### Check API Endpoints
```bash
# Test with curl
curl http://localhost:8000/api/session-status

# Test with httpie
http localhost:8000/api/session-status
```