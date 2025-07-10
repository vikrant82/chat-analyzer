#!/bin/bash

# Exit on any error
set -e

# Get the version from the user
read -p "Enter the version (e.g., 1.3): " VERSION

# Build for amd64
docker buildx build --platform linux/amd64 -t vikrant82/chat-analyzer:latest-amd64 --load .

# Build for arm64
docker buildx build --platform linux/arm64 -t vikrant82/chat-analyzer:latest-arm64 --load .

# Push the images
docker push vikrant82/chat-analyzer:latest-arm64
docker push vikrant82/chat-analyzer:latest-amd64

# Build and push the multi-arch manifest
docker buildx build --platform linux/arm64,linux/amd64 -t vikrant82/chat-analyzer:latest -t vikrant82/chat-analyzer:$VERSION --push .

echo "Successfully built and pushed version $VERSION"