#!/bin/bash
set -e  # Stop bei Fehler

# Konfiguration
REGISTRY="ghcr.io"
USERNAME="weltraumlama"
REPO_NAME="dualis-api-grade-watcher"
REPO_URL="https://github.com/${USERNAME}/${REPO_NAME}" 

# Automatische Versionierung aus Git
COMMIT=$(git rev-parse --short HEAD)

COMMIT_COUNT=$(git rev-list --count HEAD)
VERSION="v1.0.${COMMIT_COUNT}"


echo "============================================"
echo "📦 Version:    ${VERSION}"
echo "🔖 Commit:     ${COMMIT}"
echo "============================================"
echo ""

# Container-Definitionen (Name:Dockerfile-Pfad)
CONTAINERS=(
  "dualis-api-service:dualis_api_service/Dockerfile"
  "refresh-service:refresh_service/Dockerfile"
  "notification-service:notification_service/Dockerfile"
)

# Build und Push für alle Container
for ENTRY in "${CONTAINERS[@]}"; do
  CONTAINER_NAME="${ENTRY%%:*}"
  DOCKERFILE="${ENTRY#*:}"
  
  BUILD_CONTEXT="$(dirname "${DOCKERFILE}")"

  echo "🔨 Building ${CONTAINER_NAME}..."
  
  docker build \
    -f "${DOCKERFILE}" \
    --label "org.opencontainers.image.source=${REPO_URL}" \
    --label "org.opencontainers.image.description=EdgeFire ${CONTAINER_NAME} container" \
    --label "org.opencontainers.image.version=${VERSION}" \
    --label "org.opencontainers.image.revision=${COMMIT}" \
    -t "${REGISTRY}/${USERNAME}/${REPO_NAME}/${CONTAINER_NAME}:${COMMIT}" \
    -t "${REGISTRY}/${USERNAME}/${REPO_NAME}/${CONTAINER_NAME}:${VERSION}" \
    -t "${REGISTRY}/${USERNAME}/${REPO_NAME}/${CONTAINER_NAME}:latest" \
    "${BUILD_CONTEXT}"
  
  echo "📤 Pushing ${CONTAINER_NAME}..."
  
  docker push "${REGISTRY}/${USERNAME}/${REPO_NAME}/${CONTAINER_NAME}:${COMMIT}"
  docker push "${REGISTRY}/${USERNAME}/${REPO_NAME}/${CONTAINER_NAME}:${VERSION}"
  docker push "${REGISTRY}/${USERNAME}/${REPO_NAME}/${CONTAINER_NAME}:latest"
  
  echo "✅ ${CONTAINER_NAME} done!"
  echo ""
done

echo "🎉 All containers built and pushed!"
echo ""
echo "📋 Summary:"
echo "   Version: ${VERSION}"
echo "   Commit:  ${COMMIT}"
echo ""
echo "📋 Packages should appear here:"
echo "   https://github.com/${USERNAME}/${REPO_NAME}/packages"
echo ""
echo "Pull on HPC with:"
echo "   docker pull ${REGISTRY}/${USERNAME}/${REPO_NAME}/edgefire-training:${VERSION}"
echo "   docker pull ${REGISTRY}/${USERNAME}/${REPO_NAME}/edgefire-training:latest"