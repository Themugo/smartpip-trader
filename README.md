# SmartPip AI Trading System 🤖

Advanced AI-powered trading bot for Deriv Volatility Indices.

## Features
- Real-time WebSocket connection to Deriv
- AI-powered trading signals
- Auto-execution and auto-closure
- Beautiful dashboard
- Trade history tracking

## Deployment on Render
1. Push this repo to GitHub
2. Connect to Render
3. Add DERIV_API_TOKEN environment variable
4. Deploy!

## Local Development
```bash
pip install -r requirements.txt
export DERIV_API_TOKEN="your_token"
uvicorn main:app --reload