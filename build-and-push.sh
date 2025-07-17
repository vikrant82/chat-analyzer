#!/bin/bash

# Exit on any error
set -e

# Get the version from the user
read -p "Enter the version (e.g., 1.3): " VERSION

# Build and push the multi-arch image directly
docker buildx build --platform linux/arm64,linux/amd64 --no-cache -t vikrant82/chat-analyzer:latest -t vikrant82/chat-analyzer:$VERSION --push .

echo "Successfully built and pushed version $VERSION"