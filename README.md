# SmartPip Sniper — smartpip.site

**Hit and run. Fire only when all 6 conditions align. Then go dark.**

---

## Quick start (3 steps)

1. Open `index.html` in Chrome, Edge, or Firefox
2. Get your token → [app.deriv.com/account/api-token](https://app.deriv.com/account/api-token)  
   *(Needs Read + Trade permissions)*
3. Paste token, select account, click **Launch Sniper**

---

## The 6 sniper conditions

All 6 must pass simultaneously. If even one fails — no shot.

| # | Condition | Edge it exploits |
|---|-----------|-----------------|
| 1 | **Streak exhaustion** | 6+ consecutive EVEN/ODD creates statistical reversal pressure |
| 2 | **Chi-square deviation** | Digit frequency deviates beyond normal random distribution |
| 3 | **RSI extreme** | RSI ≤25 (oversold→RISE) or ≥75 (overbought→FALL) |
| 4 | **Momentum aligned** | MACD + price direction confirms signal |
| 5 | **High payout only** | Rise/Fall 95% — only contract type ever traded |
| 6 | **Cooldown clear** | Mandatory 15-tick rest between shots |

---

## Guerrilla rules (non-negotiable)

- **Flat stake only** — no martingale, ever
- **Max 5 shots per session** — then log off
- **Kill switch** auto-stops at daily loss limit
- **Only Rise/Fall** — 95% payout, best math
- **No chasing** — if 3 misses in a row, stop manually

---

## Accounts

| | Account ID | Type |
|--|------------|------|
| Real | CR9553087 | Live USD |
| Demo | VRTC14297314 | Virtual USD (test here first) |

---

## Deploy to smartpip.site

### Option 1 — Netlify (free, 30 seconds)
1. Go to [netlify.com](https://netlify.com)
2. Add new site → Deploy manually
3. Drag this folder onto the page
4. Site is live instantly
5. Domain settings → Add custom domain → `smartpip.site`

### Option 2 — cPanel / any host
1. Log into your host's File Manager
2. Upload `index.html` to `public_html/`
3. Done

### Option 3 — GitHub Pages
1. Push this folder to a GitHub repo
2. Settings → Pages → Deploy from main branch
3. Add custom domain: `smartpip.site`

---

## Security

- Tokens stored in browser `localStorage` only
- Never transmitted to any external server
- Only connects directly to `wss://ws.binaryws.com` (Deriv official endpoint)

---

## Honest edge assessment

Deriv synthetic indices are RNG-based. No system beats pure randomness consistently.
What SmartPip Sniper does:
- **Waits for statistical clusters** (streak exhaustion + chi-square skew) where probability briefly shifts
- **Only fires when multiple independent signals agree** — reducing noise trades
- **Strict loss protection** — the kill switch and session limits prevent ruin
- **High payout selection** — Rise/Fall at 95% means you only need ~53% win rate to profit

This is not a guaranteed win system. It is a disciplined, low-frequency, high-selectivity approach.

---

SmartPip Sniper v5.0  
smartpip.site · Not affiliated with Deriv Ltd
