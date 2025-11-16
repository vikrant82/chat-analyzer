#!/bin/bash
#
# Docker Build and Push Script with Auto-Versioning
# 
# This script automatically increments the minor version number on each build.
# Version is stored in .version file (git ignored) in format: MAJOR.MINOR
# 
# Usage:
#   ./build-and-push.sh              - Auto-increment and build
#   
# Manual version override:
#   echo "2.0" > .version             - Reset to version 2.0
#   ./build-and-push.sh               - Build with version 2.0, next will be 2.1
#
# The script:
# 1. Reads current version from .version file
# 2. Increments minor version (e.g., 1.3 -> 1.4)
# 3. Builds multi-arch Docker image (arm64, amd64)
# 4. Tags with both :latest and :version
# 5. Pushes to vikrant82/chat-analyzer
# 6. Updates .version file for next build

# Exit on any error
set -e

# Version file (git ignored)
VERSION_FILE=".version"

# Initialize version file if it doesn't exist
if [ ! -f "$VERSION_FILE" ]; then
    echo "1.0" > "$VERSION_FILE"
    echo "Created $VERSION_FILE with initial version 1.0"
fi

# Read current version
CURRENT_VERSION=$(cat "$VERSION_FILE")
echo "Current version: $CURRENT_VERSION"

# Parse major and minor version
IFS='.' read -r MAJOR MINOR <<< "$CURRENT_VERSION"

# Increment minor version
MINOR=$((MINOR + 1))
NEW_VERSION="$MAJOR.$MINOR"

# Save new version
echo "$NEW_VERSION" > "$VERSION_FILE"
echo "Building version: $NEW_VERSION"

# Build and push the multi-arch image directly
docker buildx build --platform linux/arm64,linux/amd64 --no-cache -t vikrant82/chat-analyzer:latest -t vikrant82/chat-analyzer:$NEW_VERSION --push .

echo "Successfully built and pushed version $NEW_VERSION"
echo "Version file updated to $NEW_VERSION"

# Optional: Commit version file and push to trigger GitHub release
read -p "Commit version file and push to GitHub to create release? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add .version
    git commit -m "chore: bump version to $NEW_VERSION"
    git push origin main
    echo "Version committed and pushed. GitHub Actions will create release v$NEW_VERSION"
    echo "View releases at: https://github.com/vikrant82/chat-analyzer/releases"
else
    echo "Skipped git commit. Run manually: git add .version && git commit -m 'chore: bump version to $NEW_VERSION' && git push"
fi