def get_dashboard_html() -> str:
    """Return the HTML dashboard template"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 ULTIMATE AI TRADING SYSTEM | SmartPip</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0a0e27; color: #e2e8f0; }
        
        /* Header */
        .header { background: linear-gradient(135deg, #0f1235, #1a1f4e); padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3748; position: sticky; top: 0; z-index: 100; }
        .logo { font-size: 22px; font-weight: 800; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .balance-card { background: rgba(16,185,129,0.1); padding: 8px 20px; border-radius: 12px; border: 1px solid rgba(16,185,129,0.3); text-align: center; }
        .balance-value { font-size: 24px; font-weight: bold; color: #10b981; }
        
        /* Main Grid */
        .main-grid { display: grid; grid-template-columns: 380px 1fr 380px; gap: 20px; padding: 20px; max-width: 1600px; margin: 0 auto; }
        
        /* Panels */
        .panel { background: #0f1235; border-radius: 16px; border: 1px solid #2d3748; overflow: hidden; }
        .panel-header { padding: 15px 20px; background: #1a1f4e; font-weight: bold; font-size: 14px; border-bottom: 1px solid #2d3748; }
        .panel-content { padding: 20px; }
        
        /* Market Card */
        .market-card { background: linear-gradient(135deg, #1a1f4e, #0f1235); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; border: 1px solid #2d3748; }
        .market-price { font-size: 36px; font-weight: bold; margin: 10px 0; }
        .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .status-running { background: #10b981; color: white; animation: pulse 2s infinite; }
        .status-stopped { background: #ef4444; color: white; }
        
        /* Prediction Card */
        .prediction-card { background: linear-gradient(135deg, #667eea20, #764ba220); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; border: 1px solid #667eea; }
        .prediction-type { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
        .prediction-value { font-size: 28px; font-weight: bold; margin: 10px 0; color: #667eea; }
        .prediction-confidence { font-size: 20px; font-weight: bold; color: #10b981; }
        
        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .stat-card { background: #1a1f4e; padding: 12px; border-radius: 10px; text-align: center; }
        .stat-label { font-size: 10px; color: #94a3b8; margin-bottom: 5px; text-transform: uppercase; }
        .stat-value { font-size: 18px; font-weight: bold; }
        
        /* Analysis Cards */
        .analysis-card { background: #1a1f4e; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
        .analysis-title { font-size: 13px; font-weight: bold; margin-bottom: 10px; color: #667eea; }
        .analysis-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 12px; border-bottom: 1px solid #2d3748; }
        .prediction-tag { background: #667eea20; padding: 2px 8px; border-radius: 12px; color: #667eea; }
        
        /* Settings Panel */
        .setting-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #2d3748; }
        .setting-label { font-size: 13px; }
        .setting-input { background: #0f1235; border: 1px solid #2d3748; color: white; padding: 6px 12px; border-radius: 6px; width: 100px; }
        .setting-checkbox { width: 20px; height: 20px; cursor: pointer; }
        
        /* Buttons */
        .btn-start { background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 12px 24px; border-radius: 10px; font-weight: bold; cursor: pointer; margin-right: 10px; }
        .btn-stop { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; padding: 12px 24px; border-radius: 10px; font-weight: bold; cursor: pointer; }
        .btn-manual { background: #1a1f4e; border: 1px solid #667eea; color: #667eea; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin: 5px; }
        .btn-save { background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
        
        /* Digits */
        .digits-container { background: #1a1f4e; border-radius: 12px; padding: 15px; margin-bottom: 20px; }
        .digits-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0; justify-content: center; }
        .digit { width: 40px; height: 40px; background: #0f1235; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; border: 1px solid #2d3748; }
        
        /* Trade Log */
        .trade-log { max-height: 300px; overflow-y: auto; }
        .trade-item { background: #1a1f4e; padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid; font-size: 11px; }
        .trade-win { border-left-color: #10b981; }
        .trade-loss { border-left-color: #ef4444; }
        
        /* Market Selector */
        .market-selector { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
        .market-btn { background: #1a1f4e; border: 1px solid #2d3748; color: #94a3b8; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 11px; }
        .market-btn.active { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        
        /* Signal List */
        .signal-item { background: #1a1f4e; padding: 8px; border-radius: 6px; margin-bottom: 5px; font-size: 11px; display: flex; justify-content: space-between; align-items: center; }
        
        /* Performance Panel */
        .perf-card { background: #1a1f4e; padding: 12px; border-radius: 8px; margin-bottom: 8px; }
        .perf-label { font-size: 10px; color: #94a3b8; margin-bottom: 4px; }
        .perf-value { font-size: 14px; font-weight: bold; }
        .perf-bar { height: 4px; background: #2d3748; border-radius: 2px; margin-top: 4px; overflow: hidden; }
        .perf-bar-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); transition: width 0.3s; }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
        
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #1a1f4e; }
        ::-webkit-scrollbar-thumb { background: #667eea; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🧠 ULTIMATE AI TRADING SYSTEM | SmartPip</div>
        <div class="balance-card">
            <div style="font-size:11px;">Balance</div>
            <div class="balance-value" id="balance">$0.00</div>
        </div>
    </div>
    
    <div class="main-grid">
        <!-- LEFT PANEL - TRADING & PREDICTION -->
        <div class="panel">
            <div class="panel-header">🎯 LIVE TRADING</div>
            <div class="panel-content">
                <div class="market-card">
                    <div style="font-size:12px; color:#94a3b8;">Current Market</div>
                    <div class="market-price" id="price">$0.00</div>
                    <div><span class="status-badge" id="status">STOPPED</span></div>
                </div>
                
                <div class="market-selector" id="marketSelector"></div>
                
                <div class="prediction-card">
                    <div class="prediction-type">BEST PREDICTION</div>
                    <div class="prediction-value" id="bestPrediction">-</div>
                    <div class="prediction-confidence" id="bestConfidence">0% confidence</div>
                    <div style="font-size:11px; margin-top:10px;" id="bestReason"></div>
                </div>
                
                <div style="display:flex; gap:10px; margin-bottom:20px;">
                    <button class="btn-start" onclick="startBot()">▶ START ENGINE</button>
                    <button class="btn-stop" onclick="stopBot()">⏹ STOP ENGINE</button>
                </div>
                
                <div style="margin-bottom:20px;">
                    <button class="btn-manual" onclick="manualTrade('CALL')">📈 MANUAL CALL</button>
                    <button class="btn-manual" onclick="manualTrade('PUT')">📉 MANUAL PUT</button>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-label">Win Rate</div><div class="stat-value" id="winRate">0%</div></div>
                    <div class="stat-card"><div class="stat-label">Session P&L</div><div class="stat-value" id="sessionPnl">$0.00</div></div>
                    <div class="stat-card"><div class="stat-label">Total Trades</div><div class="stat-value" id="totalTrades">0</div></div>
                    <div class="stat-card"><div class="stat-label">Active</div><div class="stat-value" id="activeTrades">0</div></div>
                </div>
            </div>
        </div>
        
        <!-- CENTER PANEL - INTELLIGENT ANALYSIS -->
        <div class="panel">
            <div class="panel-header">🧠 INTELLIGENT MARKET ANALYSIS</div>
            <div class="panel-content">
                <div class="digits-container">
                    <div style="font-size:12px; margin-bottom:10px;">📊 LAST 20 DIGITS PATTERN</div>
                    <div class="digits-row" id="digitsRow"></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">🎲 EVEN / ODD ANALYSIS</div>
                    <div class="analysis-row"><span>Even/Odd Count</span><span id="evenOddCount">0E / 0O</span></div>
                    <div class="analysis-row"><span>Prediction</span><span id="evenOddPred" class="prediction-tag">-</span></div>
                    <div class="analysis-row"><span>Confidence</span><span id="evenOddConf">0%</span></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">📈 RISE / FALL ANALYSIS</div>
                    <div class="analysis-row"><span>Rise/Fall Count</span><span id="riseFallCount">0R / 0F</span></div>
                    <div class="analysis-row"><span>Momentum</span><span id="momentum">0.0000</span></div>
                    <div class="analysis-row"><span>Prediction</span><span id="riseFallPred" class="prediction-tag">-</span></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">📊 OVER 3 / UNDER 7 ANALYSIS</div>
                    <div class="analysis-row"><span>Over 3 / Under 7</span><span id="overUnderCount">0O / 0U</span></div>
                    <div class="analysis-row"><span>Prediction</span><span id="overUnderPred" class="prediction-tag">-</span></div>
                    <div class="analysis-row"><span>Confidence</span><span id="overUnderConf">0%</span></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">🔄 MATCH / DIFF ANALYSIS</div>
                    <div class="analysis-row"><span>Match/Diff Count</span><span id="matchDiffCount">0M / 0D</span></div>
                    <div class="analysis-row"><span>Streak</span><span id="streak">0</span></div>
                    <div class="analysis-row"><span>Prediction</span><span id="matchDiffPred" class="prediction-tag">-</span></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">🏆 TOP TRADE SIGNALS</div>
                    <div id="tradeSignalsList"></div>
                </div>
            </div>
        </div>
        
        <!-- RIGHT PANEL - SETTINGS & TRADE LOG -->
        <div class="panel">
            <div class="panel-header">⚙️ SETTINGS & CONTROL</div>
            <div class="panel-content">
                <div class="setting-row">
                    <span class="setting-label">💰 Base Trade Amount</span>
                    <input type="number" id="baseAmount" class="setting-input" value="1" step="0.5">
                </div>
                <div class="setting-row">
                    <span class="setting-label">🎯 Min Confidence (%)</span>
                    <input type="number" id="minConfidence" class="setting-input" value="70" min="50" max="95">
                </div>
                <div class="setting-row">
                    <span class="setting-label">🛑 Stop Loss ($)</span>
                    <input type="number" id="stopLoss" class="setting-input" value="50">
                </div>
                <div class="setting-row">
                    <span class="setting-label">🎯 Take Profit ($)</span>
                    <input type="number" id="takeProfit" class="setting-input" value="100">
                </div>
                <div class="setting-row">
                    <span class="setting-label">📊 Max Consecutive Losses</span>
                    <input type="number" id="maxLosses" class="setting-input" value="3">
                </div>
                <div class="setting-row">
                    <span class="setting-label">🔘 Enable Even/Odd</span>
                    <input type="checkbox" id="enableEvenOdd" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🔘 Enable Rise/Fall</span>
                    <input type="checkbox" id="enableRiseFall" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🔘 Enable Over/Under</span>
                    <input type="checkbox" id="enableOverUnder" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🔘 Enable Match/Diff</span>
                    <input type="checkbox" id="enableMatchDiff" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🛡 Kill Switch Armed</span>
                    <input type="checkbox" id="killSwitch" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🤖 Auto Trading</span>
                    <input type="checkbox" id="autoTrading" class="setting-checkbox">
                </div>
                <div class="setting-row">
                    <button class="btn-save" onclick="saveSettings()">💾 SAVE SETTINGS</button>
                    <button class="btn-save" onclick="resetSession()">🔄 RESET SESSION</button>
                </div>
            </div>
            
            <div class="panel-header" style="margin-top:0;">📋 TRADE LOG</div>
            <div class="panel-content">
                <div class="trade-log" id="tradeLog">
                    <div style="text-align:center; padding:20px;">No trades yet</div>
                </div>
            </div>
            
            <div class="panel-header" style="margin-top:20px;">⚡ PERFORMANCE METRICS</div>
            <div class="panel-content">
                <div class="perf-card">
                    <div class="perf-label">Cache Hit Rate</div>
                    <div class="perf-value" id="cacheHitRate">0%</div>
                    <div class="perf-bar"><div class="perf-bar-fill" id="cacheHitRateBar" style="width: 0%"></div></div>
                </div>
                
                <div class="perf-card">
                    <div class="perf-label">Analysis Time (avg)</div>
                    <div class="perf-value" id="analysisTime">0ms</div>
                </div>
                
                <div class="perf-card">
                    <div class="perf-label">Ticks Processed</div>
                    <div class="perf-value" id="ticksProcessed">0</div>
                </div>
                
                <div class="perf-card">
                    <div class="perf-label">Reconnections</div>
                    <div class="perf-value" id="reconnections">0</div>
                </div>
                
                <div class="perf-card">
                    <div class="perf-label">Cache Size</div>
                    <div class="perf-value" id="cacheSize">0/1000</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        
        function connectWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);
            ws.onmessage = (event) => { const data = JSON.parse(event.data); updateDashboard(data); };
            ws.onclose = () => setTimeout(connectWebSocket, 3000);
        }
        
        function updateDashboard(data) {
            // Balance & Status
            document.getElementById('balance').innerHTML = `${data.currency || '$'}${(data.current_balance || 0).toFixed(2)}`;
            document.getElementById('price').innerHTML = `${data.currency || '$'}${(data.current_price || 0).toFixed(4)}`;
            document.getElementById('status').innerHTML = data.bot_status || 'STOPPED';
            document.getElementById('status').className = `status-badge status-${(data.bot_status || 'stopped').toLowerCase()}`;
            
            // Stats
            document.getElementById('winRate').innerHTML = `${(data.stats?.win_rate || 0).toFixed(0)}%`;
            const sessionPnl = data.stats?.session_pnl || 0;
            document.getElementById('sessionPnl').innerHTML = `${sessionPnl >= 0 ? '+' : ''}${data.currency || '$'}${sessionPnl.toFixed(2)}`;
            document.getElementById('totalTrades').innerHTML = data.stats?.total_trades || 0;
            document.getElementById('activeTrades').innerHTML = data.active_trades || 0;
            
            // Best Prediction
            if (data.best_prediction) {
                document.getElementById('bestPrediction').innerHTML = `${data.best_prediction.type} - ${data.best_prediction.direction}`;
                document.getElementById('bestConfidence').innerHTML = `${data.best_prediction.confidence.toFixed(0)}% confidence`;
                document.getElementById('bestReason').innerHTML = data.best_prediction.reason || '';
            } else {
                document.getElementById('bestPrediction').innerHTML = 'Analyzing...';
                document.getElementById('bestConfidence').innerHTML = '0% confidence';
            }
            
            // Even/Odd
            if (data.even_odd) {
                document.getElementById('evenOddCount').innerHTML = `${data.even_odd.even_count || 0}E / ${data.even_odd.odd_count || 0}O`;
                document.getElementById('evenOddPred').innerHTML = data.even_odd.prediction || '-';
                document.getElementById('evenOddConf').innerHTML = `${(data.even_odd.confidence || 0).toFixed(0)}%`;
            }
            
            // Rise/Fall
            if (data.rise_fall) {
                document.getElementById('riseFallCount').innerHTML = `${data.rise_fall.rise_count || 0}R / ${data.rise_fall.fall_count || 0}F`;
                document.getElementById('momentum').innerHTML = (data.rise_fall.momentum || 0).toFixed(4);
                document.getElementById('riseFallPred').innerHTML = data.rise_fall.prediction || '-';
            }
            
            // Over/Under
            if (data.over_under) {
                document.getElementById('overUnderCount').innerHTML = `${data.over_under.over_3_count || 0}O / ${data.over_under.under_7_count || 0}U`;
                document.getElementById('overUnderPred').innerHTML = data.over_under.prediction || '-';
                document.getElementById('overUnderConf').innerHTML = `${(data.over_under.confidence || 0).toFixed(0)}%`;
            }
            
            // Match/Diff
            if (data.match_diff) {
                document.getElementById('matchDiffCount').innerHTML = `${data.match_diff.match_count || 0}M / ${data.match_diff.diff_count || 0}D`;
                document.getElementById('streak').innerHTML = data.match_diff.match_streak || 0;
                document.getElementById('matchDiffPred').innerHTML = data.match_diff.prediction || '-';
            }
            
            // Digits
            if (data.last_20_digits && data.last_20_digits.length > 0) {
                const digitsRow = document.getElementById('digitsRow');
                digitsRow.innerHTML = data.last_20_digits.map(d => `<div class="digit">${d}</div>`).join('');
            }
            
            // Trade Signals
            if (data.trade_signals && data.trade_signals.length > 0) {
                const signalsList = document.getElementById('tradeSignalsList');
                signalsList.innerHTML = data.trade_signals.slice(0,5).map(s => `
                    <div class="signal-item">
                        <span>${s.type}</span>
                        <span style="color:#667eea;">${s.direction}</span>
                        <span style="color:#10b981;">${s.confidence.toFixed(0)}%</span>
                    </div>
                `).join('');
            }
            
            // Trade Log
            if (data.trade_history && data.trade_history.length > 0) {
                const logContainer = document.getElementById('tradeLog');
                logContainer.innerHTML = data.trade_history.slice().reverse().map(trade => `
                    <div class="trade-item ${trade.profit > 0 ? 'trade-win' : trade.profit < 0 ? 'trade-loss' : ''}">
                        <div>${new Date(trade.entry_time).toLocaleTimeString()} | ${trade.type}</div>
                        <div>${trade.direction} | ${trade.profit > 0 ? '+' : ''}${data.currency || '$'}${(trade.profit || 0).toFixed(2)}</div>
                        <div style="font-size:10px;">Conf: ${trade.confidence}% | ${trade.reason}</div>
                    </div>
                `).join('');
            }
            
            // Market Selector
            if (data.market_scores) {
                const selector = document.getElementById('marketSelector');
                selector.innerHTML = Object.keys(data.market_scores).map(m => 
                    `<button class="market-btn ${m === data.current_market ? 'active' : ''}" onclick="switchMarket('${m}')">${m}<br><small>${data.market_scores[m]}%</small></button>`
                ).join('');
            }
            
            // Settings sync
            document.getElementById('baseAmount').value = data.settings?.base_amount || 1;
            document.getElementById('minConfidence').value = data.settings?.min_confidence || 70;
            document.getElementById('stopLoss').value = data.settings?.stop_loss || 50;
            document.getElementById('takeProfit').value = data.settings?.take_profit || 100;
            document.getElementById('maxLosses').value = data.settings?.max_consecutive_losses || 3;
            document.getElementById('enableEvenOdd').checked = data.settings?.enable_even_odd !== false;
            document.getElementById('enableRiseFall').checked = data.settings?.enable_rise_fall !== false;
            document.getElementById('enableOverUnder').checked = data.settings?.enable_over_under !== false;
            document.getElementById('enableMatchDiff').checked = data.settings?.enable_match_diff !== false;
            document.getElementById('killSwitch').checked = data.kill_switch?.armed || false;
            document.getElementById('autoTrading').checked = data.settings?.auto_trading || false;
            
            // Performance metrics
            if (data.performance) {
                const cache = data.performance.cache || {};
                const metrics = data.performance.metrics || {};
                const connection = data.performance.connection || {};
                
                document.getElementById('cacheHitRate').innerHTML = `${(cache.hit_rate * 100).toFixed(1)}%`;
                document.getElementById('cacheHitRateBar').style.width = `${cache.hit_rate * 100}%`;
                
                const analysisAvg = metrics.timings?.analysis?.average || 0;
                document.getElementById('analysisTime').innerHTML = `${(analysisAvg * 1000).toFixed(2)}ms`;
                
                document.getElementById('ticksProcessed').innerHTML = metrics.counters?.ticks_processed || 0;
                document.getElementById('reconnections').innerHTML = connection.reconnect_attempts || 0;
                document.getElementById('cacheSize').innerHTML = `${cache.size || 0}/${cache.max_size || 1000}`;
            }
        }
        
        function startBot() { fetch('/api/start', { method: 'POST' }); }
        function stopBot() { fetch('/api/stop', { method: 'POST' }); }
        
        function switchMarket(market) { 
            fetch('/api/switch_market', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ market }) });
        }
        
        function saveSettings() {
            const settings = {
                base_amount: parseFloat(document.getElementById('baseAmount').value),
                min_confidence: parseFloat(document.getElementById('minConfidence').value),
                stop_loss: parseFloat(document.getElementById('stopLoss').value),
                take_profit: parseFloat(document.getElementById('takeProfit').value),
                max_consecutive_losses: parseInt(document.getElementById('maxLosses').value),
                enable_even_odd: document.getElementById('enableEvenOdd').checked,
                enable_rise_fall: document.getElementById('enableRiseFall').checked,
                enable_over_under: document.getElementById('enableOverUnder').checked,
                enable_match_diff: document.getElementById('enableMatchDiff').checked,
                auto_trading: document.getElementById('autoTrading').checked
            };
            fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) });
        }
        
        function resetSession() { fetch('/api/reset_session', { method: 'POST' }); }
        
        function manualTrade(direction) {
            const amount = prompt('Enter trade amount:', '1');
            if (amount) {
                fetch('/api/manual_trade', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ direction, amount: parseFloat(amount) }) });
            }
        }
        
        connectWebSocket();
        setInterval(() => { fetch('/api/status').then(res => res.json()).then(data => updateDashboard(data)); }, 2000);
    </script>
</body>
</html>'''
