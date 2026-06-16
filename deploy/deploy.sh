#!/bin/bash

# Deployment script for SmartPip Trader

echo "🚀 Deploying SmartPip Trader..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp deploy/.env.example .env
    echo "❗ Please edit .env with your actual configuration before running again."
    exit 1
fi

# Build Docker image
echo "📦 Building Docker image..."
docker-compose -f deploy/docker-compose.yml build

# Start container
echo "🏁 Starting container..."
docker-compose -f deploy/docker-compose.yml up -d

echo "✅ Deployment complete!"
echo "🌐 Dashboard available at: http://localhost:8000"
echo "📚 API docs available at: http://localhost:8000/docs"
