# Task Completion Checklist

When completing a coding task in this project, follow these steps:

## 1. Code Quality
- [ ] **Type hints**: Ensure all function parameters and return types have type hints
- [ ] **Docstrings**: Add docstrings to new classes and complex functions
- [ ] **Error handling**: Wrap API calls and I/O operations in try-except blocks
- [ ] **Logging**: Add appropriate logging statements (INFO, WARNING, ERROR)
- [ ] **Naming**: Follow snake_case for functions/variables, PascalCase for classes

## 2. Testing (When Applicable)
- [ ] **Run existing tests**: `pytest -v`
- [ ] **Add new tests**: If implementing new features, create tests in `/tests/`
- [ ] **Test coverage**: Ensure new code paths are covered

## 3. Code Style
- [ ] **Imports**: Organize imports (stdlib, third-party, local)
- [ ] **Line length**: Keep reasonable line lengths (no strict limit observed)
- [ ] **Private methods**: Prefix helper functions with `_`
- [ ] **Async/await**: Use consistently for I/O operations

## 4. Documentation (If Major Changes)
- [ ] **Update README**: If adding features or changing setup
- [ ] **Update docs/**: Add or modify relevant documentation files
- [ ] **Update config.json**: Document new configuration options

## 5. Dependencies
- [ ] **Update requirements.txt**: If new packages were added
- [ ] **Version compatibility**: Ensure Python 3.9+ compatibility

## 6. Git Workflow
- [ ] **Check status**: `git status`
- [ ] **Stage changes**: `git add <files>`
- [ ] **Commit**: `git commit -m "Descriptive message"`
- [ ] **Pull before push**: `git pull origin main`
- [ ] **Push**: `git push origin main`

## 7. Verification
- [ ] **No syntax errors**: Code runs without import or syntax errors
- [ ] **API endpoints work**: Test affected endpoints if applicable
- [ ] **No breaking changes**: Existing functionality still works
- [ ] **Cache/session handling**: Verify file paths and permissions

## 8. Code Review Points
- [ ] **Security**: No hardcoded credentials, sensitive data properly handled
- [ ] **Performance**: No obvious performance issues or bottlenecks
- [ ] **Resource cleanup**: Async clients properly closed, files properly managed
- [ ] **Thread safety**: Consider concurrent access for shared resources

## Notes
- **No automatic linting/formatting**: Project doesn't have pre-commit hooks or formatter config
- **Manual code review**: Review changes manually before committing
- **Testing optional but recommended**: Test suite exists but coverage is incomplete
- **Documentation appreciated**: Especially for complex algorithms (threading, caching)

## Quick Validation Commands
```bash
# Check syntax
python3 -m py_compile <file>.py

# Run tests
pytest -v

# Start server (verify no errors)
uvicorn app:app --reload

# Check imports
python3 -c "import app; import clients.factory; import services.chat_service"
```