// SmartPip Trading Site - Main Application JavaScript

class SmartPipApp {
    constructor() {
        this.apiBase = window.location.origin + '/api';
        this.ws = null;
        this.connected = false;
        this.currentMarket = 'R_10';
        this.priceHistory = [];
        this.updateInterval = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadInitialData();
        this.initCharts();
    }
    
    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateTo(link.getAttribute('href'));
            });
        });
        
        // Connection
        document.getElementById('connectBtn').addEventListener('click', () => this.connect());
        document.getElementById('authBtn').addEventListener('click', () => this.showAuthModal());
        
        // Bot controls
        document.getElementById('startBot').addEventListener('click', () => this.startBot());
        document.getElementById('stopBot').addEventListener('click', () => this.stopBot());
        document.getElementById('resetSession').addEventListener('click', () => this.resetSession());
        
        // Market switching
        document.getElementById('switchMarket').addEventListener('click', () => this.showMarketModal());
        document.querySelectorAll('.select-market').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const market = e.target.closest('.market-item').dataset.market;
                this.switchMarket(market);
            });
        });
        
        // Market analysis
        document.getElementById('analyzeMarkets').addEventListener('click', () => this.analyzeMarkets());
        
        // Manual trading
        document.getElementById('callBtn').addEventListener('click', () => this.executeManualTrade('CALL'));
        document.getElementById('putBtn').addEventListener('click', () => this.executeManualTrade('PUT'));
        document.getElementById('executeTrade').addEventListener('click', () => this.executeTrade());
        
        // Confidence slider
        document.getElementById('confidenceSlider').addEventListener('input', (e) => {
            document.getElementById('confidenceValue').textContent = e.target.value + '%';
        });
        
        // Settings
        document.getElementById('saveSettings').addEventListener('click', () => this.saveSettings());
        
        // Export
        document.getElementById('exportHistory').addEventListener('click', () => this.exportHistory());
    }
    
    navigateTo(section) {
        // Update active nav link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === section) {
                link.classList.add('active');
            }
        });
        
        // Scroll to section
        const element = document.querySelector(section);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
    }
    
    async connect() {
        this.showLoading(true);
        try {
            const response = await fetch(`${this.apiBase}/status`);
            const data = await response.json();
            
            if (data.connected) {
                this.connected = true;
                this.updateConnectionStatus(true);
                this.showToast('Connected successfully', 'success');
            } else {
                this.showToast('Not connected to Deriv API', 'error');
            }
        } catch (error) {
            this.showToast('Connection failed', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            // Only log in development
            if (process.env.NODE_ENV === 'development') {
                console.log('WebSocket connected');
            }
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.ws.onerror = (error) => {
            // Only log errors in development
            if (process.env.NODE_ENV === 'development') {
                console.error('WebSocket error:', error);
            }
        };
        
        this.ws.onclose = () => {
            // Only log in development
            if (process.env.NODE_ENV === 'development') {
                console.log('WebSocket closed');
            }
            // Attempt to reconnect after 5 seconds
            setTimeout(() => this.connectWebSocket(), 5000);
        };
    }
    
    handleWebSocketMessage(data) {
        // Update connection status
        if (data.connected !== undefined) {
            this.updateConnectionStatus(data.connected);
        }
        
        // Update market data
        if (data.current_price !== undefined) {
            this.updatePrice(data.current_price, data.current_market);
        }
        
        // Update prediction
        if (data.best_prediction) {
            this.updatePrediction(data.best_prediction);
        }
        
        // Update risk metrics
        if (data.zero_loss_risk) {
            this.updateRiskMetrics(data.zero_loss_risk);
        }
        
        // Update performance metrics
        if (data.performance) {
            this.updatePerformanceMetrics(data.performance);
        }
        
        // Update active trades
        if (data.active_trades !== undefined) {
            this.updateActiveTrades(data.active_trades);
        }
        
        // Update trade history
        if (data.trade_history) {
            this.updateTradeHistory(data.trade_history);
        }
        
        // Update market analysis
        if (data.market_analysis) {
            this.updateMarketAnalysis(data.market_analysis);
        }
        
        // Update market ranking
        if (data.market_ranking) {
            this.updateMarketRanking(data.market_ranking);
        }
    }
    
    updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('connectionStatus');
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');
        
        if (connected) {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.remove('connected');
            statusText.textContent = 'Disconnected';
        }
    }
    
    updatePrice(price, market) {
        document.getElementById('currentPrice').textContent = price.toFixed(4);
        document.getElementById('marketName').textContent = market;
        
        // Add to price history
        this.priceHistory.push(price);
        if (this.priceHistory.length > 100) {
            this.priceHistory.shift();
        }
        
        // Update price chart
        this.updatePriceChart();
        
        // Calculate price change
        if (this.priceHistory.length > 1) {
            const change = ((price - this.priceHistory[0]) / this.priceHistory[0]) * 100;
            const changeElement = document.getElementById('priceChange');
            changeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
            changeElement.className = `market-change ${change >= 0 ? '' : 'negative'}`;
        }
    }
    
    updatePrediction(prediction) {
        document.getElementById('predictionType').textContent = prediction.type;
        document.getElementById('predictionDirection').textContent = prediction.direction;
        document.getElementById('predictionDirection').className = `prediction-direction ${prediction.direction}`;
        document.getElementById('predictionConfidence').textContent = `${prediction.confidence}%`;
        document.getElementById('predictionReason').textContent = prediction.reason;
        document.getElementById('confidenceFill').style.width = `${prediction.confidence}%`;
    }
    
    updateRiskMetrics(metrics) {
        document.getElementById('dailyPnL').textContent = `${metrics.daily_pnl >= 0 ? '+' : ''}${metrics.daily_pnl.toFixed(2)}`;
        document.getElementById('dailyPnL').className = `risk-value ${metrics.daily_pnl >= 0 ? 'positive' : 'negative'}`;
        document.getElementById('consecutiveLosses').textContent = metrics.consecutive_losses;
        document.getElementById('killSwitch').textContent = metrics.kill_switch ? 'Active' : 'Inactive';
        document.getElementById('killSwitch').className = `risk-value ${metrics.kill_switch ? 'negative' : 'positive'}`;
        document.getElementById('currentWinRate').textContent = `${(metrics.win_rate * 100).toFixed(1)}%`;
    }
    
    updatePerformanceMetrics(performance) {
        if (performance.hft_metrics) {
            document.getElementById('avgLatency').textContent = `${performance.hft_metrics.average_latency.toFixed(2)}ms`;
            document.getElementById('p95Latency').textContent = `${performance.hft_metrics.latency_p95.toFixed(2)}ms`;
        }
        
        if (performance.cache) {
            const hitRate = performance.cache.hits / (performance.cache.hits + performance.cache.misses) * 100;
            document.getElementById('cacheHitRate').textContent = `${hitRate.toFixed(1)}%`;
        }
    }
    
    updateActiveTrades(count) {
        document.getElementById('activeTradesCount').textContent = count;
    }
    
    updateTradeHistory(history) {
        const tbody = document.getElementById('tradeHistory');
        
        if (history.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>No trade history</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = history.map(trade => `
            <tr>
                <td>${new Date(trade.timestamp).toLocaleString()}</td>
                <td>${trade.market}</td>
                <td>${trade.type}</td>
                <td class="${trade.direction === 'CALL' ? 'text-success' : 'text-danger'}">${trade.direction}</td>
                <td>${trade.amount}</td>
                <td>${trade.confidence}%</td>
                <td class="${trade.profit >= 0 ? 'text-success' : 'text-danger'}">${trade.profit >= 0 ? '+' : ''}${trade.profit}</td>
                <td>${trade.status}</td>
            </tr>
        `).join('');
        
        // Update history stats
        this.updateHistoryStats(history);
    }
    
    updateHistoryStats(history) {
        const totalTrades = history.length;
        const winningTrades = history.filter(t => t.profit > 0).length;
        const losingTrades = history.filter(t => t.profit < 0).length;
        const totalProfit = history.reduce((sum, t) => sum + t.profit, 0);
        
        document.getElementById('totalTradesHistory').textContent = totalTrades;
        document.getElementById('winningTrades').textContent = winningTrades;
        document.getElementById('losingTrades').textContent = losingTrades;
        document.getElementById('totalProfitHistory').textContent = `${totalProfit >= 0 ? '+' : ''}${totalProfit.toFixed(2)}`;
        document.getElementById('totalProfitHistory').className = `stat-value ${totalProfit >= 0 ? '' : 'negative'}`;
    }
    
    updateMarketAnalysis(analysis) {
        if (analysis.best_market) {
            document.getElementById('marketName').textContent = analysis.best_market;
        }
    }
    
    updateMarketRanking(ranking) {
        const rankingList = document.getElementById('marketRanking');
        
        rankingList.innerHTML = ranking.map((item, index) => `
            <div class="ranking-item">
                <span class="rank-position">${index + 1}</span>
                <span class="rank-market">${item[0]}</span>
                <span class="rank-score">${item[1].toFixed(1)}</span>
            </div>
        `).join('');
    }
    
    async startBot() {
        this.showLoading(true);
        try {
            const response = await fetch(`${this.apiBase}/start`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Bot started successfully', 'success');
            } else {
                this.showToast('Failed to start bot', 'error');
            }
        } catch (error) {
            this.showToast('Failed to start bot', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async stopBot() {
        this.showLoading(true);
        try {
            const response = await fetch(`${this.apiBase}/stop`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Bot stopped successfully', 'success');
            } else {
                this.showToast('Failed to stop bot', 'error');
            }
        } catch (error) {
            this.showToast('Failed to stop bot', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async resetSession() {
        this.showLoading(true);
        try {
            const response = await fetch(`${this.apiBase}/reset_session`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Session reset successfully', 'success');
            } else {
                this.showToast('Failed to reset session', 'error');
            }
        } catch (error) {
            this.showToast('Failed to reset session', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async switchMarket(market) {
        this.showLoading(true);
        try {
            const response = await fetch(`${this.apiBase}/switch_market`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ market })
            });
            const data = await response.json();
            
            if (data.success) {
                this.currentMarket = market;
                this.showToast(`Switched to ${market}`, 'success');
            } else {
                this.showToast('Failed to switch market', 'error');
            }
        } catch (error) {
            this.showToast('Failed to switch market', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async analyzeMarkets() {
        this.showLoading(true);
        try {
            const response = await fetch(`${this.apiBase}/markets/analyze`);
            const data = await response.json();
            
            // Update market cards
            document.querySelectorAll('.market-item').forEach(item => {
                const market = item.dataset.market;
                const marketData = data.all_scores[market];
                
                if (marketData) {
                    item.querySelector('.market-score').textContent = marketData.toFixed(1);
                    item.querySelector('.market-volatility').textContent = `Volatility: ${marketData.toFixed(2)}`;
                }
            });
            
            this.showToast('Market analysis completed', 'success');
        } catch (error) {
            this.showToast('Failed to analyze markets', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async executeManualTrade(direction) {
        const amount = document.getElementById('tradeAmount').value;
        const market = document.getElementById('tradeMarket').value;
        
        this.showLoading(true);
        try {
            const response = await fetch(`${this.apiBase}/manual_trade`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    direction,
                    amount,
                    market
                })
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast(`${direction} trade executed`, 'success');
            } else {
                this.showToast('Failed to execute trade', 'error');
            }
        } catch (error) {
            this.showToast('Failed to execute trade', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async executeTrade() {
        const direction = document.getElementById('callBtn').classList.contains('active') ? 'CALL' : 'PUT';
        await this.executeManualTrade(direction);
    }
    
    async saveSettings() {
        const settings = {
            base_amount: parseFloat(document.getElementById('baseAmount').value),
            min_confidence: parseInt(document.getElementById('minConfidence').value),
            max_trades_per_hour: parseInt(document.getElementById('maxTradesPerHour').value),
            max_consecutive_losses: parseInt(document.getElementById('maxConsecutiveLosses').value),
            enable_even_odd: document.getElementById('enableEvenOdd').checked,
            enable_rise_fall: document.getElementById('enableRiseFall').checked,
            enable_over_under: document.getElementById('enableOverUnder').checked,
            enable_match_diff: document.getElementById('enableMatchDiff').checked
        };
        
        this.showLoading(true);
        try {
            const response = await fetch(`${this.apiBase}/settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Settings saved successfully', 'success');
            } else {
                this.showToast('Failed to save settings', 'error');
            }
        } catch (error) {
            this.showToast('Failed to save settings', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    exportHistory() {
        const history = document.getElementById('tradeHistory');
        const rows = history.querySelectorAll('tr');
        
        let csv = 'Time,Market,Type,Direction,Amount,Confidence,Profit,Status\n';
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length === 8) {
                const rowData = Array.from(cells).map(cell => cell.textContent);
                csv += rowData.join(',') + '\n';
            }
        });
        
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `trade_history_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        
        this.showToast('History exported successfully', 'success');
    }
    
    async loadInitialData() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            const data = await response.json();
            
            // Update account info
            if (data.active_account) {
                document.getElementById('accountType').textContent = data.active_account;
            }
            if (data.current_balance) {
                document.getElementById('balance').textContent = data.current_balance.toFixed(2);
            }
            if (data.currency) {
                document.getElementById('currency').textContent = data.currency;
            }
            
            // Update settings
            if (data.settings) {
                document.getElementById('baseAmount').value = data.settings.base_amount;
                document.getElementById('minConfidence').value = data.settings.min_confidence;
                document.getElementById('maxTradesPerHour').value = data.settings.max_trades_per_hour;
                document.getElementById('maxConsecutiveLosses').value = data.settings.max_consecutive_losses;
            }
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }
    
    initCharts() {
        // Price chart
        const priceCtx = document.getElementById('priceChart').getContext('2d');
        this.priceChart = new Chart(priceCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Price',
                    data: [],
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        display: true
                    }
                }
            }
        });
        
        // Performance chart
        const perfCtx = document.getElementById('performanceChart').getContext('2d');
        this.performanceChart = new Chart(perfCtx, {
            type: 'bar',
            data: {
                labels: ['Win Rate', 'Profit Factor', 'Avg Win', 'Avg Loss'],
                datasets: [{
                    label: 'Metrics',
                    data: [85, 2.5, 150, -75],
                    backgroundColor: [
                        '#10b981',
                        '#2563eb',
                        '#10b981',
                        '#ef4444'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    updatePriceChart() {
        const labels = this.priceHistory.map((_, i) => i);
        this.priceChart.data.labels = labels;
        this.priceChart.data.datasets[0].data = this.priceHistory;
        this.priceChart.update('none');
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    showAuthModal() {
        // TODO: Implement authentication modal
        this.showToast('Authentication coming soon', 'info');
    }
    
    showMarketModal() {
        // TODO: Implement market selection modal
        this.navigateTo('#markets');
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SmartPipApp();
});
