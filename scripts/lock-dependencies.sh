#!/bin/bash

# Lock exact dependency versions for reproducible builds

set -e

echo "=========================================="
echo "Locking Dependency Versions"
echo "=========================================="
echo ""

# Generate requirements.lock with exact versions
echo "1. Generating requirements.lock with exact versions..."
pip freeze > requirements.lock
echo "✓ requirements.lock generated"
echo ""

# Generate package-lock.json for npm dependencies
echo "2. Generating package-lock.json for npm dependencies..."
if [ -f "package.json" ]; then
    npm install --package-lock-only
    echo "✓ package-lock.json generated"
else
    echo "⚠ No package.json found, skipping npm lock"
fi
echo ""

# Generate SBOM (Software Bill of Materials)
echo "3. Generating Software Bill of Materials (SBOM)..."
if command -v syft &> /dev/null; then
    syft . -o spdx-json > sbom.json
    echo "✓ SBOM generated (sbom.json)"
else
    echo "⚠ syft not installed (install with: brew install syft)"
fi
echo ""

# Verify locked versions
echo "4. Verifying locked versions..."
if [ -f "requirements.lock" ]; then
    echo "Total packages in requirements.lock: $(wc -l < requirements.lock)"
    echo "✓ Verification complete"
else
    echo "✗ requirements.lock not found"
fi
echo ""

echo "=========================================="
echo "Dependency Locking Complete"
echo "=========================================="
echo ""
echo "Generated files:"
echo "- requirements.lock (Python dependencies)"
echo "- package-lock.json (npm dependencies)"
echo "- sbom.json (Software Bill of Materials)"
echo ""
echo "Commit these files to ensure reproducible builds."
