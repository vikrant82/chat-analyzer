# GitHub Releases & Version Management

## Overview
The Chat Analyzer project uses automated GitHub releases that sync with Docker image versions. The version is displayed in the UI and tracked in a `.version` file.

## Version File Location
- **File**: `.version` (project root)
- **Format**: `MAJOR.MINOR` (e.g., `1.1`, `2.0`)
- **Current Version**: `1.1`
- **Git Tracking**: YES (removed from .gitignore to enable release automation)
- **Docker Image**: YES (removed from .dockerignore - file is copied into image for runtime version display)
- **Purpose**: Single source of truth for version - used by build script, API endpoint, and UI

## Automated Release Workflow

### Components

#### 1. Build Script (`build-and-push.sh`)
**Purpose**: Build Docker images and optionally trigger releases

**Process**:
1. Reads current version from `.version` (e.g., `1.1`)
2. Increments minor version (`1.1` → `1.2`)
3. Builds multi-arch Docker image (arm64, amd64) with `--no-cache`
4. Pushes to Docker Hub:
   - `vikrant82/chat-analyzer:latest`
   - `vikrant82/chat-analyzer:1.2`
5. Updates `.version` file with new version
6. **Prompts user**: "Commit version file and push to GitHub? (y/n)"
   - If **yes**: Commits `.version`, pushes to `main`, triggers release
   - If **no**: Shows manual git commands

**Usage**:
```bash
./build-and-push.sh
# Follow prompts
```

**Manual Version Override**:
```bash
echo "2.0" > .version
./build-and-push.sh
# Next build will be 2.1
```

#### 2. GitHub Actions Workflow (`.github/workflows/release.yml`)
**Purpose**: Automatically create GitHub releases when version changes

**Trigger**: Push to `main` branch with changes to `.version` file

**Process**:
1. Detects `.version` file change
2. Reads version number (e.g., `1.2`)
3. Checks if tag `v1.2` already exists
4. Generates changelog from git commits since last tag
5. Creates GitHub release with:
   - **Tag**: `v1.2`
   - **Title**: `Release v1.2`
   - **Body**:
     - Version number
     - Docker pull commands
     - Automatic changelog
     - Installation instructions
   - **Draft**: No (published immediately)
   - **Prerelease**: No

**Permissions Required**: `contents: write` (already configured)

**Changelog Generation**:
- **First release**: All commits in history
- **Subsequent releases**: Commits since previous tag
- **Format**: `- Commit message (commit_hash)`

#### 3. Version API (`app.py`)
**Purpose**: Expose version to frontend

**Endpoint**: `GET /api/version`

**Implementation**:
```python
VERSION_FILE = ".version"
APP_VERSION = "1.0"  # Default fallback
if os.path.exists(VERSION_FILE):
    try:
        with open(VERSION_FILE, 'r') as f:
            APP_VERSION = f.read().strip()
        logger.info(f"Application version: {APP_VERSION}")
    except Exception as e:
        logger.warning(f"Could not read version file: {e}")

@app.get("/api/version")
async def get_version():
    """Returns the current application version."""
    return {"version": APP_VERSION}
```

**Response**: `{"version": "1.1"}`

#### 4. UI Version Display
**Location**: Footer (fixed bottom position)

**HTML** (`static/index.html`):
```html
<footer class="app-footer">
    <a id="app-version" href="https://github.com/vikrant82/chat-analyzer" 
       target="_blank" rel="noopener noreferrer" title="View on GitHub">v1.0</a>
</footer>
```

**Styling** (`static/style.css`):
- Fixed bottom position
- Semi-transparent background with backdrop blur
- Subtle text color (respects dark/light theme)
- Hover effects: color change to primary gradient, underline
- Clickable link to GitHub repository

**JavaScript** (`static/js/main.js`):
```javascript
fetch('/api/version')
    .then(response => response.json())
    .then(data => {
        const versionElement = document.getElementById('app-version');
        if (versionElement && data.version) {
            versionElement.textContent = `v${data.version}`;
        }
    })
    .catch(error => {
        console.error('Failed to fetch version:', error);
    });
```

**Features**:
- ✅ Dynamically loaded from API
- ✅ Clickable (opens GitHub repo in new tab)
- ✅ Tooltip: "View on GitHub"
- ✅ Secure link (`rel="noopener noreferrer"`)
- ✅ Theme-aware styling

## Release Workflow Diagram

```
┌────────────────────┐
│ Run build script   │
│ ./build-and-push.sh│
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Increment version  │
│ 1.1 → 1.2         │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Build Docker image │
│ Push to Docker Hub │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Prompt: Commit and │
│ push to GitHub?    │
└─────────┬──────────┘
          │ (yes)
          ▼
┌────────────────────┐
│ git push to main   │
│ (.version changed) │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ GitHub Actions     │
│ workflow triggered │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Generate changelog │
│ Create release     │
│ Tag: v1.2         │
└────────────────────┘
```

## Usage Examples

### Create New Release (Fully Automated)
```bash
# 1. Run build script
./build-and-push.sh

# 2. When prompted "Commit version file and push to GitHub?", type 'y'
# → Version automatically committed, pushed, and release created

# 3. View release
# → Visit https://github.com/vikrant82/chat-analyzer/releases
```

### Create New Release (Manual Control)
```bash
# 1. Run build script
./build-and-push.sh

# 2. When prompted, type 'n' to skip auto-commit

# 3. Manually commit later
git add .version
git commit -m "chore: bump version to 1.2"
git push origin main

# 4. GitHub Actions creates release automatically
```

### First-Time Setup (Already Complete)
```bash
# 1. Commit all version-related files
git add .version .github/ .gitignore app.py build-and-push.sh static/ docs/
git commit -m "feat: add automated GitHub releases and version display"
git push origin main

# 2. This creates initial release v1.1
# 3. Future builds will auto-increment
```

## Versioning Strategy

### Format: MAJOR.MINOR
- **MAJOR**: Breaking changes, major feature additions
- **MINOR**: New features, bug fixes, improvements

### Examples
- `1.0` → Initial release
- `1.1` → Version display feature
- `1.2` → Next feature/bugfix
- `2.0` → Major rewrite or breaking change

### When to Increment
- **Auto-increment** (default): Every Docker build
- **Manual override**: For major versions or resets
  ```bash
  echo "2.0" > .version
  ./build-and-push.sh
  ```

## Release Locations

### 1. GitHub Releases
**URL**: https://github.com/vikrant82/chat-analyzer/releases

**Contains**:
- Release notes with changelog
- Docker pull commands
- Installation instructions
- Git tag (e.g., `v1.2`)

### 2. Docker Hub
**URL**: https://hub.docker.com/r/vikrant82/chat-analyzer/tags

**Tags**:
- `latest` - Always points to most recent build
- `1.1`, `1.2`, etc. - Specific versions

### 3. Application UI
**Location**: Footer (bottom of page)

**Display**: Clickable link to GitHub repository

**API**: `GET /api/version` returns `{"version": "1.2"}`

## Troubleshooting

### Release Not Created

**Check:**
1. Is `.version` file committed?
   ```bash
   git ls-files .version  # Should show: .version
   ```

2. Is GitHub Actions workflow present?
   ```bash
   ls .github/workflows/release.yml
   ```

3. Check GitHub Actions logs:
   - Go to: https://github.com/vikrant82/chat-analyzer/actions
   - Look for "Create Release on Version Change" workflow

### Version Not Showing in UI

**Check:**
1. API endpoint:
   ```bash
   curl http://localhost:8000/api/version
   # Should return: {"version":"1.2"}
   ```

2. `.version` file:
   ```bash
   cat .version
   ```

3. Browser cache: Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)

### Tag Already Exists

If "tag already exists" error:
```bash
# Delete tag and recreate
git tag -d v1.2
git push origin :refs/tags/v1.2

# Or skip - release probably already created
```

## Docker Image Considerations

### Version File in Container
**Critical**: The `.version` file **must be included** in the Docker image for the version to display correctly in the UI.

**Implementation**:
1. **Dockerfile**: Uses `COPY . .` which copies all files
2. **Exclusions**: `.dockerignore` initially excluded `.version` but has been corrected
3. **Current Status**: ✅ `.version` is now included in Docker image

**Verification**:
```bash
# Build image
docker build -t test-version .

# Check if version file exists in container
docker run --rm test-version cat .version
# Should output: 1.1 (or current version)

# Test API endpoint
docker run -d -p 8000:8000 test-version
curl http://localhost:8000/api/version
# Should return: {"version":"1.1"}
```

**Impact if Missing**:
- ❌ API returns fallback version "1.0" instead of actual version
- ❌ UI always shows "v1.0" regardless of Docker image tag
- ❌ Users can't see which version they're running

**Files Involved**:
- `.dockerignore` - Must NOT exclude `.version`
- `Dockerfile` - `COPY . .` includes `.version`
- `app.py` - Reads `.version` at container startup

## Integration Points

### With Docker Build Process
- Build script reads version → increments → builds → pushes → optionally commits
- Docker images tagged with version number
- Both `:latest` and `:version` tags updated

### With Git Workflow
- `.version` file tracked in git (not gitignored)
- Commits to `.version` trigger release workflow
- Releases linked to git tags

### With Application Code
- `app.py` reads `.version` at startup
- API exposes version to frontend
- UI displays version dynamically

### With CI/CD
- GitHub Actions automatically creates releases
- No manual intervention required
- Changelog generated from commit history

## Best Practices

1. **Test locally before pushing**:
   ```bash
   ./build-and-push.sh
   docker run -p 8000:8000 vikrant82/chat-analyzer:latest
   # Verify version displays correctly in UI
   ```

2. **Write meaningful commit messages**:
   ```bash
   git commit -m "feat: add user authentication"
   git commit -m "fix: resolve memory leak in cache"
   git commit -m "chore: bump version to 1.3"
   ```

3. **Tag major releases manually**:
   ```bash
   git tag -a v2.0 -m "Major release: Complete UI redesign"
   ```

4. **Keep .version in sync** with releases

5. **Document breaking changes** in release notes

## Files Involved

### Core Implementation
- `.version` - Version number storage
- `build-and-push.sh` - Build and release orchestration
- `.github/workflows/release.yml` - Automation workflow
- `app.py` - Version reading and API endpoint
- `static/index.html` - Footer with version link
- `static/style.css` - Footer styling
- `static/js/main.js` - Version fetching logic

### Documentation
- `docs/github_releases_guide.md` - Comprehensive guide
- This memory file - Quick reference

## Summary

The Chat Analyzer project has a **fully automated release pipeline**:

✅ **Automated**: Version → Build → Push → Release
✅ **Integrated**: One command builds and optionally releases
✅ **Visible**: Version displayed in UI with GitHub link
✅ **Tracked**: All versions in GitHub releases and Docker Hub
✅ **Documented**: Automatic changelog generation
✅ **User-Friendly**: Simple prompts, no complex commands

**Current Status**: Version 1.1, ready for next release
**Next Build**: Will create version 1.2 and GitHub release v1.2
