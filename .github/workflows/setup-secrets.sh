#!/bin/bash
# Setup script for GitHub Actions secrets
# Run this once to configure secrets for deployment

set -e

REPO="Themugo/smartpip-trader"

echo "🔐 GitHub Secrets Setup for SmartPip Trader"
echo "============================================"

# Check for Fly.io token
if [ -z "$FLY_API_TOKEN" ]; then
    echo ""
    echo "⚠️  FLY_API_TOKEN not set"
    echo ""
    echo "To get your Fly.io token:"
    echo "1. Go to https://fly.io/user/token"
    echo "2. Click 'Create access token'"
    echo "3. Copy the token and set it:"
    echo "   export FLY_API_TOKEN='your-token-here'"
    echo ""
fi

# Check for DERIV_API_TOKEN
if [ -z "$DERIV_API_TOKEN" ]; then
    echo ""
    echo "⚠️  DERIV_API_TOKEN not set"
    echo ""
    echo "To get your Deriv API token:"
    echo "1. Go to https://app.deriv.com/account/api"
    echo "2. Create a new API token"
    echo "3. Copy and set it:"
    echo "   export DERIV_API_TOKEN='pat_xxx'"
    echo ""
fi

echo ""
echo "GitHub Secrets to configure:"
echo "------------------------------"
echo "1. Go to: https://github.com/$REPO/settings/secrets/actions"
echo "2. Add these secrets:"
echo ""
echo "   Name: FLY_API_TOKEN"
echo "   Value: $([ -n "$FLY_API_TOKEN" ] && echo "$FLY_API_TOKEN" || echo 'your-fly.io-token')"
echo ""
echo "   Name: DERIV_API_TOKEN" 
echo "   Value: $([ -n "$DERIV_API_TOKEN" ] && echo "$DERIV_API_TOKEN" || echo 'your-deriv-api-token')"
echo ""

if [ -n "$FLY_API_TOKEN" ] && [ -n "$DERIV_API_TOKEN" ]; then
    echo "✅ All tokens available. Use 'gh secret set' or GitHub UI to add them."
fi
