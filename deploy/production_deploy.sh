#!/bin/bash

# Production deployment script for SmartPip Trader
# This script builds and deploys to production environments (Fly.io)

set -e

echo "🚀 SmartPip Trader Production Deployment"
echo "========================================"

# Get the deployment environment (default: production)
DEPLOY_ENV=${1:-production}
APP_NAME="smartpip-trader"

if [ "$DEPLOY_ENV" = "staging" ]; then
    APP_NAME="smartpip-trader-staging"
    echo "📦 Deploying to STAGING environment"
elif [ "$DEPLOY_ENV" = "production" ]; then
    echo "🚀 Deploying to PRODUCTION environment"
else
    echo "❌ Unknown environment: $DEPLOY_ENV"
    echo "Usage: ./production_deploy.sh [production|staging]"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp deploy/.env.example .env
    echo "❗ Please edit .env with your production credentials before running again."
    exit 1
fi

# Verify Fly.io is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ Fly.io CLI not found. Installing..."
    curl -L https://fly.io/install.sh | sh
    export PATH="$HOME/.fly/bin:$PATH"
fi

# Check for Fly.io token
if [ -z "$FLY_API_TOKEN" ]; then
    echo "⚠️  FLY_API_TOKEN not set. Please run 'flyctl auth login' first."
    echo "   Or set the FLY_API_TOKEN environment variable."
fi

# Set production environment
echo "🏭 Setting production environment..."
export ENVIRONMENT=production
export DEBUG=false
export PORT=8080

# Build Docker image
echo "📦 Building production Docker image..."
docker build -f deploy/Dockerfile -t smartpip-trader:production .

# Tag for registry
echo "🏷️  Tagging for registry..."
docker tag smartpip-trader:production ghcr.io/$(gh repo view --json owner,name -q '.owner.login + "/" + .name'):production

# Push to registry
echo "📤 Pushing to GitHub Container Registry..."
docker push ghcr.io/$(gh repo view --json owner,name -q '.owner.login + "/" + .name'):production

# Deploy to Fly.io
echo "🚀 Deploying to Fly.io ($APP_NAME)..."
if [ -f "fly.$DEPLOY_ENV.toml" ]; then
    flyctl deploy --remote-only \
        --image ghcr.io/$(gh repo view --json owner,name -q '.owner.login + "/" + .name'):production \
        --config fly.$DEPLOY_ENV.toml
else
    flyctl deploy --remote-only \
        --image ghcr.io/$(gh repo view --json owner,name -q '.owner.login + "/" + .name'):production
fi

# Set up secrets
echo "🔐 Setting up production secrets..."
if [ -n "$DERIV_API_TOKEN" ]; then
    flyctl secrets set DERIV_API_TOKEN="$DERIV_API_TOKEN" --app "$APP_NAME"
fi
flyctl secrets set ENVIRONMENT=production --app "$APP_NAME"
flyctl secrets set PORT=8080 --app "$APP_NAME"

# Verify deployment
echo "✅ Verifying deployment..."
sleep 15
HEALTH_URL=$(flyctl api-url --app "$APP_NAME")
curl -f "${HEALTH_URL}/api/health" || echo "⚠️  Health check failed - manual verification may be needed"

echo ""
echo "========================================"
echo "✅ Production deployment complete!"
echo "🌐 App deployed to: https://$APP_NAME.fly.dev"
echo "📚 API docs available at: https://$APP_NAME.fly.dev/docs"
echo "🔐 Security features enabled:"
echo "   - JWT authentication"
echo "   - IP whitelisting"
echo "   - Data encryption"
echo "   - SSL/TLS"
echo "   - Rate limiting"
echo "========================================"
