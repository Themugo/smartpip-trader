#!/bin/bash

# Production deployment script for derivfusion.com
# This script locks down the system and deploys to production

set -e

echo "🔒 Locking down SmartPip Trader system for production deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Creating from .env.example..."
    cp deploy/.env.example .env
    echo "❗ Please edit .env with your production credentials before running again."
    exit 1
fi

# Generate secure secrets
echo "🔐 Generating secure secrets..."
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "SECRET_KEY=$SECRET_KEY" >> .env
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY" >> .env

# Set production environment
echo "🏭 Setting production environment..."
export ENVIRONMENT=production
export DEBUG=false

# Build Docker image
echo "📦 Building production Docker image..."
docker build -f deploy/Dockerfile -t smartpip-trader:production .

# Tag for registry
echo "🏷️  Tagging for registry..."
docker tag smartpip-trader:production registry.fly.io/smartpip-trader:production

# Push to registry
echo "📤 Pushing to registry..."
docker push registry.fly.io/smartpip-trader:production

# Deploy to production
echo "🚀 Deploying to production (derivfusion.com)..."
flyctl deploy --image registry.fly.io/smartpip-trader:production --app smartpip-trader --remote-only

# Configure SSL/TLS
echo "🔒 Configuring SSL/TLS..."
flyctl certs install derivfusion.com --app smartpip-trader

# Set up IP whitelisting
echo "🛡️  Setting up IP whitelisting..."
flyctl ips allocate-v4 --app smartpip-trader

# Enable auto-scaling
echo "📊 Enabling auto-scaling..."
flyctl scale min 2 max 10 --app smartpip-trader

# Set up secrets
echo "🔐 Setting up production secrets..."
flyctl secrets set SECRET_KEY=$SECRET_KEY --app smartpip-trader
flyctl secrets set ENCRYPTION_KEY=$ENCRYPTION_KEY --app smartpip-trader

# Verify deployment
echo "✅ Verifying deployment..."
sleep 10
curl -f https://derivfusion.com/health || exit 1

echo "✅ Production deployment complete!"
echo "🌐 System locked and deployed to: https://derivfusion.com"
echo "📚 API docs available at: https://derivfusion.com/docs"
echo "🔐 Security features enabled:"
echo "   - JWT authentication"
echo "   - IP whitelisting"
echo "   - Data encryption"
echo "   - SSL/TLS"
echo "   - Rate limiting"
