# SmartPip Trader v3.0

**AI-powered sniper bot for Deriv volatility indices** — FastAPI backend, WebSocket real-time feed, ensemble ML, and a dark-themed browser UI.

## What's new in v3.0

| Component | Upgrade |
|-----------|---------|
| **Ensemble ML** | RF + GBM + LR with calibrated probabilities, soft voting weighted by live-trade accuracy |
| **PatternRecognizer** | Chi-squared test, Wald-Wolfowitz runs test, Shannon entropy, mean reversion scoring |
| **Feature Engineering** | 33+ features: entropy, autocorrelation lags 1-3, MACD, Bollinger Band position, run-length encoding |
| **Adaptive weights** | Per-analyzer weights tracked and updated each trade; entropy filter gates trades in random markets |
| **UI: AI Brain panel** | Neural consensus visualization, entropy meter, signal strength bars for all 6 conditions |
| **API** | New endpoints: `/api/signals`, `/api/patterns`, `/api/ml-status`, `/api/entropy`, `/api/analyzer-weights` |

## Stack

- **Backend**: Python 3.11, FastAPI 0.115, Uvicorn, WebSockets
- **ML**: scikit-learn (RF, GBM, LR, CalibratedClassifierCV), XGBoost, SciPy
- **Frontend**: Vanilla JS, Chart.js 4, Tabler Icons
- **Exchange**: Deriv WSS API (`wss://ws.binaryws.com/websockets/v3`)

## Quick start

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Open in browser
open http://localhost:8000
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DERIV_API_TOKEN` | — | Deriv API token (Read + Trade) |
| `DERIV_APP_ID` | 1089 | Deriv application ID |
| `BASE_AMOUNT` | 1.0 | Default stake per trade ($) |
| `MIN_CONFIDENCE` | 70 | Minimum ML confidence to trade |
| `STOP_LOSS` | 50.0 | Daily stop loss ($) |
| `TAKE_PROFIT` | 100.0 | Daily take profit ($) |
| `MAX_CONSECUTIVE_LOSSES` | 3 | Kill-switch after N losses |
| `DAILY_LOSS_LIMIT_PERCENT` | 5.0 | Max daily drawdown (%) |
| `CHI_THRESHOLD` | 7.0 | Chi-sq stat for digit skew |
| `MIN_STREAK` | 6 | Min streak for reversal signal |

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Full system state |
| `/api/health` | GET | Health check |
| `/api/start` | POST | Start auto-trading |
| `/api/stop` | POST | Stop auto-trading |
| `/api/settings` | GET/POST | Read/update settings |
| `/api/market/{m}` | POST | Switch market |
| `/api/signals` | GET | All AI signals + consensus |
| `/api/patterns` | GET | Pattern analysis metrics |
| `/api/ml-status` | GET | Ensemble ML status + feature importance |
| `/api/entropy` | GET | Market entropy & randomness |
| `/api/analyzer-weights` | GET | Adaptive analyzer weights |
| `/api/trade` | POST | Execute manual trade |
| `/api/history` | GET | Trade history |
| `/api/backtest` | POST | Quick backtest on current data |
| `/ws` | WS | Live data + signals stream |

## Architecture

```
main.py
├── core/deriv_api.py          # Deriv WebSocket connection
├── analysis/
│   ├── analysis_manager.py    # 10 analyzers, weighted consensus
│   ├── pattern_recognizer.py  # Chi-sq, runs test, Shannon entropy
│   ├── technical_analyzer.py  # RSI, MACD, BB
│   └── ... (8 more analyzers)
├── ml/
│   ├── ml_predictor.py        # Primary predictor (delegates to ensemble)
│   ├── ensemble_predictor.py  # RF + GBM + LR + ModelTracker
│   └── feature_engineer.py   # 33+ features
├── strategies/
│   ├── unified_strategy.py    # Entropy-gated consensus strategy
│   └── adaptive_strategy_manager.py
├── api/routes.py              # FastAPI routes
└── index.html                 # Sniper UI (dark theme, 3-column)
```

## Sniper UI features

- **Score ring** — weighted 0-100 score; fires only at ≥85
- **6 conditions** — all must align: streak, chi-sq, RSI, momentum, payout, cooldown
- **AI Brain panel** — neural consensus bars, entropy meter, signal strength per analyzer
- **Entropy meter** — Shannon entropy of last 30 digits; green = patterned (edge), amber = random (wait)
- **Kill switch** — auto-stops at daily loss limit
- **Telegram alerts** — shot fired + result notifications
- **Flat stakes** — no martingale, ever

## Risk notice

This software is experimental. Trading binary options carries substantial risk. Never trade more than you can afford to lose. Past performance does not guarantee future results.
