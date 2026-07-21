#!/bin/bash

# Deployment script for SmartPip Trader - Local Development

set -e

echo "🚀 Deploying SmartPip Trader..."
echo "================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp deploy/.env.example .env
    echo "❗ Please edit .env with your actual configuration before running again."
    exit 1
fi

# Set environment
export ENVIRONMENT=${ENVIRONMENT:-development}
export PORT=8080

# Build Docker image
echo "📦 Building Docker image..."
docker-compose -f deploy/docker-compose.yml build

# Start container
echo "🏁 Starting container..."
docker-compose -f deploy/docker-compose.yml up -d

echo ""
echo "================================"
echo "✅ Deployment complete!"
echo "🌐 Dashboard available at: http://localhost:8080"
echo "📚 API docs available at: http://localhost:8080/docs"
echo "🔧 Health check: http://localhost:8080/api/v1/system/health"
echo "================================"
