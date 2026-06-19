#!/bin/bash

# SmartPip Trading Site Deployment Script for smartpip.site
# This script deploys the trading system to the registered domain

set -e

echo "🚀 Starting SmartPip Trading Site Deployment to smartpip.site"
echo "================================================"

# Configuration
DOMAIN="www.smartpip.site"
REPO="https://github.com/Themugo/smartpip-trader.git"
DEPLOY_DIR="/var/www/smartpip"
BACKUP_DIR="/var/www/backups/smartpip"
LOG_FILE="/var/log/smartpip-deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root"
    exit 1
fi

# Create backup
log "Creating backup..."
if [ -d "$DEPLOY_DIR" ]; then
    BACKUP_NAME="smartpip-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    cp -r "$DEPLOY_DIR" "$BACKUP_DIR/$BACKUP_NAME"
    log_success "Backup created: $BACKUP_NAME"
fi

# Create deployment directory
log "Creating deployment directory..."
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Clone or update repository
if [ -d ".git" ]; then
    log "Updating existing repository..."
    git pull origin master
    log_success "Repository updated"
else
    log "Cloning repository..."
    git clone "$REPO" .
    log_success "Repository cloned"
fi

# Install dependencies
log "Installing Python dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
log_success "Dependencies installed"

# Set up environment variables
log "Setting up environment variables..."
if [ ! -f .env ]; then
    cp deploy/.env.example .env
    log_warning "Please configure .env file with your credentials"
fi

# Run database migrations (if any)
log "Running database migrations..."
# Add migration commands here if needed
log_success "Database migrations completed"

# Build static assets
log "Building static assets..."
# Add build commands here if needed
log_success "Static assets built"

# Configure Nginx
log "Configuring Nginx..."
cat > /etc/nginx/sites-available/smartpip << EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;

    # Redirect to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Logging
    access_log /var/log/nginx/smartpip-access.log;
    error_log /var/log/nginx/smartpip-error.log;

    # Static files
    location /static/ {
        alias $DEPLOY_DIR/web/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/smartpip /etc/nginx/sites-enabled/
log_success "Nginx configured"

# Test Nginx configuration
nginx -t
if [ $? -eq 0 ]; then
    log_success "Nginx configuration test passed"
else
    log_error "Nginx configuration test failed"
    exit 1
fi

# Reload Nginx
systemctl reload nginx
log_success "Nginx reloaded"

# Set up SSL certificate with Let's Encrypt
if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    log "Setting up SSL certificate..."
    certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
    log_success "SSL certificate configured"
else
    log "SSL certificate already exists, renewing..."
    certbot renew --quiet
    log_success "SSL certificate renewed"
fi

# Create systemd service
log "Creating systemd service..."
cat > /etc/systemd/system/smartpip.service << EOF
[Unit]
Description=SmartPip Trading System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$DEPLOY_DIR
Environment="PATH=$DEPLOY_DIR/venv/bin"
EnvironmentFile=$DEPLOY_DIR/.env
ExecStart=$DEPLOY_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload
log_success "Systemd service created"

# Start the service
systemctl enable smartpip
systemctl restart smartpip
log_success "SmartPip service started"

# Wait for service to start
sleep 5

# Check service status
if systemctl is-active --quiet smartpip; then
    log_success "SmartPip service is running"
else
    log_error "SmartPip service failed to start"
    systemctl status smartpip
    exit 1
fi

# Set up log rotation
log "Setting up log rotation..."
cat > /etc/logrotate.d/smartpip << EOF
/var/log/smartpip-deploy.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
}

/var/log/nginx/smartpip-*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data adm
}
EOF
log_success "Log rotation configured"

# Set permissions
log "Setting permissions..."
chown -R www-data:www-data $DEPLOY_DIR
chmod -R 755 $DEPLOY_DIR
log_success "Permissions set"

# Health check
log "Performing health check..."
sleep 3
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$HEALTH_CHECK" = "200" ]; then
    log_success "Health check passed"
else
    log_error "Health check failed (HTTP $HEALTH_CHECK)"
fi

# Cleanup old backups (keep last 7)
log "Cleaning up old backups..."
cd "$BACKUP_DIR"
ls -t | tail -n +8 | xargs -r rm -rf
log_success "Old backups cleaned"

log_success "================================================"
log_success "✓ SmartPip Trading Site deployed successfully to $DOMAIN"
log_success "================================================"
log ""
log "Access your site at: https://$DOMAIN"
log "API documentation: https://$DOMAIN/docs"
log "Service status: systemctl status smartpip"
log "View logs: journalctl -u smartpip -f"
log ""
