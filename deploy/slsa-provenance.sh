#!/bin/bash

# SLSA Provenance Generation
# Provides supply chain security and build reproducibility

set -e

echo "=========================================="
echo "SLSA Provenance Generation"
echo "=========================================="
echo ""

# Configuration
IMAGE_NAME="${IMAGE_NAME:-smartpip-trader}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
BUILD_ID="${BUILD_ID:-$(date +%s)}"
GITHUB_RUN_ID="${GITHUB_RUN_ID:-local}"

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

# Check for required tools
echo "1. Checking for required tools..."
REQUIRED_TOOLS=("cosign" "jq")
MISSING_TOOLS=()

for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v $tool &> /dev/null; then
        MISSING_TOOLS+=($tool)
    fi
done

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    print_status 1 "Missing required tools: ${MISSING_TOOLS[*]}"
    exit 1
else
    print_status 0 "All required tools installed"
fi
echo ""

# Generate build metadata
echo "2. Generating build metadata..."
BUILD_METADATA=$(cat <<EOF
{
  "buildType": "https://slsa.dev/provenance/v0.2",
  "buildId": "build-${BUILD_ID}",
  "builder": {
    "id": "https://github.com/Themugo/smartpip-trader/.github/workflows/build.yml"
  },
  "invocation": {
    "configSource": {
      "uri": "github.com/Themugo/smartpip-trader/.github/workflows/build.yml@main"
    },
    "parameters": {
      "IMAGE_NAME": "${IMAGE_NAME}",
      "IMAGE_TAG": "${IMAGE_TAG}"
    }
  },
  "buildConfig": {
    "uri": "github.com/Themugo/smartpip-trader/.github/workflows/build.yml@main"
  }
}
EOF
)
echo "$BUILD_METADATA" > build-metadata.json
print_status 0 "Build metadata generated"
echo ""

# Generate materials (source code hash)
echo "3. Generating materials (source code hash)..."
if command -v git &> /dev/null; then
    SOURCE_HASH=$(git rev-parse HEAD)
    SOURCE_URI=$(git config --get remote.origin.url)
    
    MATERIALS=$(cat <<EOF
{
  "materials": [
    {
      "uri": "${SOURCE_URI}",
      "digest": {
        "sha1": "${SOURCE_HASH}"
      }
    }
  ]
}
EOF
)
else
    print_warning "Git not available, using placeholder materials"
    MATERIALS='{"materials": []}'
fi
echo "$MATERIALS" > materials.json
print_status 0 "Materials generated"
echo ""

# Generate subject (image digest)
echo "4. Generating subject (image digest)..."
IMAGE_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' $FULL_IMAGE 2>/dev/null || echo "")
if [ -z "$IMAGE_DIGEST" ]; then
    print_warning "Could not get image digest, using placeholder"
    SUBJECT='{"subject": []}'
else
    SUBJECT=$(cat <<EOF
{
  "subject": [
    {
      "name": "${FULL_IMAGE}",
      "digest": {
        "sha256": "${IMAGE_DIGEST#*:}"
      }
    }
  ]
}
EOF
)
fi
echo "$SUBJECT" > subject.json
print_status 0 "Subject generated"
echo ""

# Combine into provenance statement
echo "5. Creating provenance statement..."
PROVENANCE=$(jq -s '.[0] + .[1] + .[2]' build-metadata.json materials.json subject.json)
echo "$PROVENANCE" > provenance.json
print_status 0 "Provenance statement created"
echo ""

# Sign provenance with Cosign
echo "6. Signing provenance statement..."
if [ -f "cosign.key" ]; then
    cosign sign-blob --key cosign.key --output provenance.sig provenance.json
    print_status 0 "Provenance signed"
else
    print_warning "cosign.key not found, skipping signature"
fi
echo ""

# Attach provenance to image
echo "7. Attaching provenance to image..."
if [ -f "provenance.sig" ]; then
    cosign attach attestation --type slsaprovenance --signature provenance.sig $FULL_IMAGE
    print_status 0 "Provenance attached to image"
else
    print_warning "Provenance attachment skipped (no signature)"
fi
echo ""

# Generate SLSA Level 1 summary
echo "8. Generating SLSA Level 1 summary..."
SLSA_SUMMARY=$(cat <<EOF
{
  "slsa_level": "1",
  "build_id": "build-${BUILD_ID}",
  "source_hash": "${SOURCE_HASH:-unknown}",
  "image_digest": "${IMAGE_DIGEST:-unknown}",
  "builder": "https://github.com/Themugo/smartpip-trader/.github/workflows/build.yml",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "verified": $([ -f "provenance.sig" ] && echo "true" || echo "false")
}
EOF
)
echo "$SLSA_SUMMARY" > slsa-summary.json
print_status 0 "SLSA summary generated"
echo ""

# Display summary
echo "=========================================="
echo "SLSA Provenance Summary"
echo "=========================================="
echo ""
echo "Build ID: build-${BUILD_ID}"
echo "Source Hash: ${SOURCE_HASH:-unknown}"
echo "Image Digest: ${IMAGE_DIGEST:-unknown}"
echo "SLSA Level: 1"
echo "Verified: $([ -f "provenance.sig" ] && echo "Yes" || echo "No")"
echo ""
echo "Generated files:"
echo "- build-metadata.json"
echo "- materials.json"
echo "- subject.json"
echo "- provenance.json"
echo "- provenance.sig"
echo "- slsa-summary.json"
echo ""
echo "To verify the provenance:"
echo "  cosign verify-attestation --type slsaprovenance $FULL_IMAGE"
echo ""
print_status 0 "SLSA provenance generation completed"
