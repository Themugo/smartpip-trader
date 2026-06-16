#!/bin/bash

# Docker Image Signing with Cosign
# Provides deployment integrity and provenance

set -e

echo "=========================================="
echo "Docker Image Signing with Cosign"
echo "=========================================="
echo ""

# Configuration
IMAGE_NAME="${IMAGE_NAME:-smartpip-trader}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
COSIGN_KEY="${COSIGN_KEY:-cosign.key}"
COSIGN_PASSWORD="${COSIGN_PASSWORD:-}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if cosign is installed
echo "1. Checking for Cosign installation..."
if command -v cosign &> /dev/null; then
    print_status 0 "Cosign is installed"
    COSIGN_VERSION=$(cosign version)
    echo "   Version: $COSIGN_VERSION"
else
    print_status 1 "Cosign not installed"
    echo "   Install with: go install github.com/sigstore/cosign/cmd/cosign@latest"
    exit 1
fi
echo ""

# Generate signing key if not exists
echo "2. Checking for signing key..."
if [ ! -f "$COSIGN_KEY" ]; then
    print_warning "Signing key not found, generating new key..."
    cosign generate-key-pair
    print_status 0 "Generated new signing key pair"
    print_warning "IMPORTANT: Store cosign.pub securely in your repository"
    print_warning "IMPORTANT: Store cosign.key securely in your secrets manager"
else
    print_status 0 "Signing key found"
fi
echo ""

# Build Docker image
echo "3. Building Docker image..."
docker build -t $FULL_IMAGE -f deploy/Dockerfile .
print_status $? "Docker image built"
echo ""

# Sign the image
echo "4. Signing Docker image with Cosign..."
if [ -n "$COSIGN_PASSWORD" ]; then
    echo $COSIGN_PASSWORD | cosign sign --key $COSIGN_KEY $FULL_IMAGE
else
    cosign sign --key $COSIGN_KEY $FULL_IMAGE
fi
print_status $? "Image signed successfully"
echo ""

# Verify the signature
echo "5. Verifying signature..."
cosign verify --key cosign.pub $FULL_IMAGE
print_status $? "Signature verified"
echo ""

# Generate SBOM
echo "6. Generating SBOM..."
if command -v syft &> /dev/null; then
    syft $FULL_IMAGE -o spdx-json > sbom-${IMAGE_TAG}.json
    print_status 0 "SBOM generated (sbom-${IMAGE_TAG}.json)"
else
    print_warning "syft not installed, skipping SBOM generation"
fi
echo ""

# Attach SBOM to image
echo "7. Attaching SBOM to image..."
if [ -f "sbom-${IMAGE_TAG}.json" ] && command -v cosign &> /dev/null; then
    cosign attach sbom --sbom sbom-${IMAGE_TAG}.json $FULL_IMAGE
    print_status 0 "SBOM attached to image"
else
    print_warning "SBOM attachment skipped"
fi
echo ""

# Generate provenance
echo "8. Generating provenance attestation..."
cosign attest --key $COSIGN_KEY --type slsaprovenance $FULL_IMAGE
print_status $? "Provenance attestation generated"
echo ""

# Display summary
echo "=========================================="
echo "Docker Image Signing Summary"
echo "=========================================="
echo ""
echo "Image: $FULL_IMAGE"
echo "Signed: Yes"
echo "Verified: Yes"
echo "SBOM: sbom-${IMAGE_TAG}.json"
echo "Provenance: Attached"
echo ""
echo "To verify the image later:"
echo "  cosign verify --key cosign.pub $FULL_IMAGE"
echo ""
echo "To view the SBOM:"
echo "  cosign sbom $FULL_IMAGE"
echo ""
echo "To view the provenance:"
echo "  cosign attest --key cosign.pub $FULL_IMAGE"
echo ""
print_status 0 "Docker image signing completed"
