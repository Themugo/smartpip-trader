#!/bin/bash

# Deployment script for derivfusion.com

echo "🚀 Deploying SmartPip Trader to derivfusion.com..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp deploy/.env.example .env
    echo "❗ Please edit .env with your actual configuration before running again."
    exit 1
fi

# Build and push to Docker registry
echo "📦 Building Docker image..."
docker build -t smartpip-trader:latest -f deploy/Dockerfile .

# Tag for deployment
docker tag smartpip-trader:latest registry.fly.io/smartpip-trader:latest

# Push to registry
echo "📤 Pushing to registry..."
docker push registry.fly.io/smartpip-trader:latest

# Deploy to production
echo "🌐 Deploying to derivfusion.com..."
flyctl deploy --image registry.fly.io/smartpip-trader:latest --app smartpip-trader

echo "✅ Deployment complete!"
echo "🌐 Dashboard available at: https://derivfusion.com"
echo "📚 API docs available at: https://derivfusion.com/docs"
