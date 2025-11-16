# GitHub Releases Setup Guide

This guide explains how GitHub releases are automated for the Chat Analyzer project.

## Overview

The project uses automated GitHub releases that trigger when the `.version` file is updated. This integrates seamlessly with the Docker build process.

## How It Works

### 1. Build Process (`build-and-push.sh`)

When you run the build script:

```bash
./build-and-push.sh
```

**The script will:**
1. Read current version from `.version` file (e.g., `1.1`)
2. Increment minor version (e.g., `1.1` → `1.2`)
3. Build multi-architecture Docker image (arm64, amd64)
4. Push to Docker Hub with tags:
   - `vikrant82/chat-analyzer:latest`
   - `vikrant82/chat-analyzer:1.2`
5. Save new version to `.version` file
6. **Prompt you** to commit and push to GitHub

### 2. GitHub Actions Workflow (`.github/workflows/release.yml`)

When you push the `.version` file to GitHub:

```bash
git add .version
git commit -m "chore: bump version to 1.2"
git push origin main
```

**GitHub Actions will automatically:**
1. Detect the `.version` file change
2. Read the new version number
3. Generate changelog from git commits
4. Create a new GitHub release with:
   - **Tag**: `v1.2`
   - **Title**: `Release v1.2`
   - **Description**: Changelog, Docker pull commands, installation instructions
   - **Docker image reference**: `vikrant82/chat-analyzer:1.2`

## Quick Start

### First Time Setup

1. **Make .version file trackable** (already done):
   ```bash
   # .version is now tracked in git (not in .gitignore)
   ```

2. **Add the current version to git**:
   ```bash
   git add .version
   git commit -m "chore: add version tracking for releases"
   git push origin main
   ```

3. **Verify GitHub Actions workflow exists**:
   - Check: `.github/workflows/release.yml`
   - This file enables automatic release creation

### Creating a New Release

**Method 1: Automatic (via build script)**

```bash
# Run the build and push script
./build-and-push.sh

# When prompted "Commit version file and push to GitHub?", type 'y'
# This will automatically:
# - Commit the new version
# - Push to GitHub
# - Trigger release creation
```

**Method 2: Manual**

```bash
# 1. Build and push Docker image
./build-and-push.sh

# 2. When prompted, type 'n' to skip auto-commit

# 3. Manually commit and push
git add .version
git commit -m "chore: bump version to 1.2"
git push origin main

# 4. GitHub Actions will create the release automatically
```

## Release Workflow Diagram

```
┌─────────────────────────┐
│  Run build-and-push.sh  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Increment version      │
│  (1.1 → 1.2)           │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Build Docker image     │
│  Push to Docker Hub     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Commit .version file?  │
│  (y/n prompt)          │
└───────────┬─────────────┘
            │
            ▼ (if yes)
┌─────────────────────────┐
│  git push to main       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  GitHub Actions trigger │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Create GitHub Release  │
│  - Tag: v1.2           │
│  - Changelog           │
│  - Docker commands     │
└─────────────────────────┘
```

## Version Display in UI

The version is now displayed in the application:

- **Location**: Footer at bottom of the page
- **Display**: "v1.2" (dynamically loaded from `/api/version`)
- **Clickable**: Opens GitHub repository in new tab
- **Hover effect**: Color change and underline

The UI automatically reflects the version from the `.version` file without requiring any code changes.

## Viewing Releases

### GitHub Releases Page
Visit: https://github.com/vikrant82/chat-analyzer/releases

### Via Git
```bash
# List all tags/releases
git tag

# View specific release
git show v1.2
```

### Via Docker Hub
```bash
# View all available tags
docker search vikrant82/chat-analyzer

# Or visit: https://hub.docker.com/r/vikrant82/chat-analyzer/tags
```

## Manual Release Creation (Alternative)

If you prefer manual control without the GitHub Actions workflow:

1. **Tag the commit**:
   ```bash
   git tag -a v1.2 -m "Release version 1.2"
   git push origin v1.2
   ```

2. **Create release on GitHub**:
   - Go to https://github.com/vikrant82/chat-analyzer/releases
   - Click "Draft a new release"
   - Select tag `v1.2`
   - Fill in title and description
   - Click "Publish release"

## Versioning Strategy

### Version Format: MAJOR.MINOR

- **MAJOR**: Breaking changes or major feature additions
- **MINOR**: New features, bug fixes, improvements

### Examples

- `1.0` → Initial release
- `1.1` → Version display feature added
- `1.2` → Next feature or bug fix
- `2.0` → Major rewrite or breaking changes

### Manual Version Override

To reset to a specific version:

```bash
echo "2.0" > .version
./build-and-push.sh
# Next build will be 2.1
```

## Troubleshooting

### Release Not Created Automatically

**Check:**
1. Is `.version` file committed to git?
   ```bash
   git ls-files .version
   # Should show: .version
   ```

2. Is GitHub Actions workflow present?
   ```bash
   ls .github/workflows/release.yml
   ```

3. Check GitHub Actions logs:
   - Go to: https://github.com/vikrant82/chat-analyzer/actions
   - Look for "Create Release on Version Change" workflow

### Tag Already Exists Error

If you see "tag already exists", either:
- The release was already created for this version
- Delete the tag and recreate:
  ```bash
  git tag -d v1.2
  git push origin :refs/tags/v1.2
  ```

### Version Not Showing in UI

1. **Check API endpoint**:
   ```bash
   curl http://localhost:8000/api/version
   # Should return: {"version":"1.2"}
   ```

2. **Clear browser cache**: Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)

3. **Check .version file**:
   ```bash
   cat .version
   ```

## Advanced: Customizing Releases

### Add Custom Release Notes

Edit `.github/workflows/release.yml` and modify the `body` section:

```yaml
body: |
  ## Chat Analyzer v${{ steps.version.outputs.version }}
  
  ### 🎉 What's New
  - Feature 1
  - Feature 2
  
  ### 🐛 Bug Fixes
  - Fix 1
  - Fix 2
  
  ### 📦 Installation
  ...
```

### Add Release Assets

To attach files to releases (e.g., compiled binaries, documentation):

```yaml
- name: Upload Release Asset
  uses: actions/upload-release-asset@v1
  with:
    upload_url: ${{ steps.create_release.outputs.upload_url }}
    asset_path: ./build/output.zip
    asset_name: chat-analyzer-${{ steps.version.outputs.version }}.zip
    asset_content_type: application/zip
```

## Best Practices

1. **Always test locally before pushing**:
   ```bash
   ./build-and-push.sh
   # Test the Docker image locally
   docker run -p 8000:8000 vikrant82/chat-analyzer:latest
   ```

2. **Write meaningful commit messages**:
   ```bash
   git commit -m "feat: add user authentication"
   git commit -m "fix: resolve memory leak in cache system"
   git commit -m "chore: bump version to 1.3"
   ```

3. **Tag major releases manually** for important versions:
   ```bash
   git tag -a v2.0 -m "Major release: Complete UI redesign"
   ```

4. **Document breaking changes** in release notes

5. **Keep .version file in sync** with your releases

## Summary

- ✅ **Automated**: Version → Build → Push → Release
- ✅ **Integrated**: One command to build and optionally release
- ✅ **Visible**: Version displayed in UI footer with GitHub link
- ✅ **Tracked**: All versions in GitHub releases and Docker Hub
- ✅ **Documented**: Automatic changelog generation

You now have a fully automated release pipeline! 🚀
