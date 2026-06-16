#!/bin/bash

# Final production deployment - locked and immutable
# This deploys to real market with all configurations locked

set -e

echo "🔒 FINAL PRODUCTION DEPLOYMENT - LOCKED SYSTEM"
echo "=============================================="

# Check if system is already locked
if [ -f "config/market_lock.json" ]; then
    echo "⚠️  System is already locked"
    echo "To unlock and redeploy, you must:"
    echo "1. Have authorized key"
    echo "2. Be in non-production mode"
    echo "3. Contact system administrator"
    exit 1
fi

# Verify environment
if [ "$ENVIRONMENT" != "production" ]; then
    echo "❌ ENVIRONMENT must be set to 'production'"
    exit 1
fi

# Verify production settings
if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    exit 1
fi

# Check for required production variables
if [ -z "$DERIV_API_TOKEN" ]; then
    echo "❌ DERIV_API_TOKEN not set"
    exit 1
fi

echo "✅ Environment verified"
echo "🔒 Locking all market configurations..."

# Generate lock key
LOCK_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Lock the system
python -c "
from config.market_lock import MarketLock
lock = MarketLock()
lock.lock('$LOCK_KEY')
print('System locked successfully')
"

echo "✅ System locked"
echo "🚀 Deploying to REAL market (production)..."

# Build production image
docker build -f deploy/Dockerfile -t smartpip-trader:final .

# Tag for production
docker tag smartpip-trader:final registry.fly.io/smartpip-trader:final

# Push to registry
docker push registry.fly.io/smartpip-trader:final

# Deploy to production
flyctl deploy --image registry.fly.io/smartpip-trader:final --app smartpip-trader --remote-only

# Set production secrets
flyctl secrets set ENVIRONMENT=production --app smartpip-trader
flyctl secrets set LOCK_KEY=$LOCK_KEY --app smartpip-trader

# Verify deployment
echo "🔍 Verifying deployment..."
sleep 15

# Check health
HEALTH_CHECK=$(curl -s https://derivfusion.com/health)
if [ "$HEALTH_CHECK" != '{"status":"healthy"}' ]; then
    echo "❌ Health check failed"
    exit 1
fi

echo "✅ Health check passed"

# Verify lock status
LOCK_STATUS=$(curl -s https://derivfusion.com/api/config/lock-status)
echo "🔒 Lock status: $LOCK_STATUS"

echo ""
echo "=============================================="
echo "✅ FINAL PRODUCTION DEPLOYMENT COMPLETE"
echo "=============================================="
echo ""
echo "🔒 System Status: LOCKED"
echo "🌐 URL: https://derivfusion.com"
echo "📚 Docs: https://derivfusion.com/docs"
echo "💰 Market: REAL (Production)"
echo ""
echo "⚠️  IMPORTANT:"
echo "  - All configurations are locked"
echo "  - No further changes allowed"
echo "  - System is immutable"
echo "  - Real market trading enabled"
echo ""
echo "🔐 Lock Key: $LOCK_KEY"
echo "   (Save this key securely for future reference)"
echo ""
