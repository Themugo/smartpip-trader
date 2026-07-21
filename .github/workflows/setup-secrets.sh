#!/bin/bash
# Setup script for GitHub Actions secrets
# Run this once to configure secrets for deployment

set -e

REPO="Themugo/smartpip-trader"

echo "🔐 GitHub Secrets Setup for SmartPip Trader"
echo "============================================"
echo ""
echo "📍 Deployment: Vercel (smartpip-sniper project)"
echo ""

# Check for Vercel token
if [ -z "$VERCEL_TOKEN" ]; then
    echo ""
    echo "⚠️  VERCEL_TOKEN not set"
    echo ""
    echo "To get your Vercel token:"
    echo "1. Go to https://vercel.com/account/tokens"
    echo "2. Click 'Create Token'"
    echo "3. Name it 'smartpip-trader-deploy'"
    echo "4. Copy the token and set it"
    echo ""
fi

# Check for Vercel Org ID
if [ -z "$VERCEL_ORG_ID" ]; then
    echo ""
    echo "⚠️  VERCEL_ORG_ID not set"
    echo ""
    echo "To get your Vercel Org ID:"
    echo "1. Go to https://vercel.com/account/teams"
    echo "2. Find your team slug"
    echo ""
fi

# Check for Vercel Project ID
if [ -z "$VERCEL_PROJECT_ID" ]; then
    echo ""
    echo "⚠️  VERCEL_PROJECT_ID not set"
    echo ""
    echo "To get your Vercel Project ID:"
    echo "1. Go to https://vercel.com/dashboard"
    echo "2. Select the smartpip-sniper project"
    echo "3. Go to Settings > General"
    echo "4. Copy the Project ID"
    echo ""
fi

echo ""
echo "GitHub Secrets to configure:"
echo "------------------------------"
echo "1. Go to: https://github.com/$REPO/settings/secrets/actions"
echo "2. Add these secrets:"
echo ""
echo "   Name: VERCEL_TOKEN"
echo "   Name: VERCEL_ORG_ID"
echo "   Name: VERCEL_PROJECT_ID"
echo "   Name: DERIV_API_TOKEN"
echo ""
echo "After adding secrets, deployments will go to:"
echo "   Production: https://smartpip-sniper.vercel.app"
echo "   Preview: https://smartpip-sniper-git-{branch}.vercel.app"
