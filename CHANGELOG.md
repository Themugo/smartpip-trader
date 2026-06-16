# Changelog

## v5.0 — June 2026 (Current) — Sniper Edition

Complete rebuild. Removed all noise. Focused purely on hit-and-run trading.

### What was removed
- Bot Manager (replaced by single smart sniper engine)
- Market Board (irrelevant to sniper model)
- Auto-Optimizer tab (settings are manually tuned once)
- Backtest tab (simplified — focus on live)
- 6-bot system (replaced by single arbiter logic)
- Martingale (removed — flat stake only)
- Busy multi-tab interface (replaced by clean 3-column layout)

### What was built
- **Sniper score ring** (0–100 live score with weighted conditions)
- **6-condition checker** with real-time pass/fail per condition
- **Chi-square deviation** engine — detects digit distribution skew
- **Streak exhaustion** detector — 6+ same type triggers reversal signal
- **RSI extreme** filter — only fires at genuine oversold/overbought
- **Momentum alignment** — MACD + price direction must confirm
- **Cooldown bar** — visual 15-tick mandatory rest timer
- **Why fire / why wait** panel — plain English explanation every tick
- **Shot log** — pending → hit/miss with full context
- **Digit frequency** bars with hot digit detection
- **Session equity curve** with peak tracker
- **Kill switch** — auto-stops at daily loss limit
- **Telegram alerts** — shot fired, hit/miss, kill switch trigger
- **Dual account** login (real CR9553087 + demo VRTC14297314)
- **Capital protection** — flat stake, no martingale, session limits

## v4.0 — May 2026
Full platform with 6 bots, market board, backtest, optimizer

## v3.0 — April 2026
Bot Manager, Telegram, martingale

## v1–2 — March 2026
Initial Deriv WebSocket connection, basic analysis
