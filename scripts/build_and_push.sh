#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "🔍 Extracting region from infrastructure/terraform/gpu.auto.tfvars..."

# Extract the region variable from the tfvars file
REGION=$(grep -E '^region\s*=' infrastructure/terraform/gpu.auto.tfvars | cut -d'"' -f2)

if [ -z "$REGION" ]; then
    echo "❌ Error: Could not extract the region from infrastructure/terraform/gpu.auto.tfvars"
    exit 1
fi

echo "✅ Found Region: ${REGION}"

# Hardcoded project variables (you can also extract these if they become dynamic)
PROJECT_ID="ml-ops-classifier-app"
REGISTRY_NAME="machine-learning-artifacts-registry"
IMAGE_NAME="gradio-app:v3"

# Construct the Artifact Registry domain and full image path
REGISTRY_DOMAIN="${REGION}-docker.pkg.dev"
FULL_IMAGE_PATH="${REGISTRY_DOMAIN}/${PROJECT_ID}/${REGISTRY_NAME}/${IMAGE_NAME}"

echo "🔐 Configuring Docker authentication for ${REGISTRY_DOMAIN}..."
gcloud auth configure-docker ${REGISTRY_DOMAIN} --quiet

echo "🚀 Building and pushing the Docker image..."
echo "📦 Image Path: ${FULL_IMAGE_PATH}"

# Build and push the image using the context of the 'app' directory
docker buildx build --platform linux/amd64 -f app/docker/Dockerfile -t ${FULL_IMAGE_PATH} --push app/

echo "🎉 Successfully built and pushed the image!"
