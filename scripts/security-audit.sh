#!/bin/bash

# Security Audit Script for SmartPip Trading System
# Runs comprehensive security checks on dependencies and code

set -e

echo "=========================================="
echo "SmartPip Trading System - Security Audit"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Python Dependency Audit
echo "1. Running pip-audit for Python dependencies..."
if command -v pip-audit &> /dev/null; then
    pip-audit --desc --strict || print_warning "pip-audit found vulnerabilities"
    print_status $? "Python dependency audit completed"
else
    print_warning "pip-audit not installed (install with: pip install pip-audit)"
fi
echo ""

# 2. Safety Check
echo "2. Running safety check for known security issues..."
if command -v safety &> /dev/null; then
    safety check --json || print_warning "safety found potential issues"
    print_status $? "Safety check completed"
else
    print_warning "safety not installed (install with: pip install safety)"
fi
echo ""

# 3. Bandit Security Linter
echo "3. Running bandit security linter..."
if command -v bandit &> /dev/null; then
    bandit -r . -f json -o bandit-report.json || print_warning "bandit found potential security issues"
    print_status $? "Bandit security linter completed"
else
    print_warning "bandit not installed (install with: pip install bandit)"
fi
echo ""

# 4. Check for hardcoded secrets
echo "4. Checking for hardcoded secrets..."
if command -v trufflehog &> /dev/null; then
    trufflehog --json . > trufflehog-report.json || print_warning "trufflehog found potential secrets"
    print_status $? "Secret scan completed"
else
    print_warning "trufflehog not installed (install with: go install github.com/trufflesecurity/trufflehog/v3/cmd/trufflehog@latest)"
fi
echo ""

# 5. Check for outdated dependencies
echo "5. Checking for outdated dependencies..."
pip list --outdated --format=json > outdated-deps.json || true
print_status $? "Outdated dependencies check completed"
echo ""

# 6. Docker Security Scan
echo "6. Running Docker security scan..."
if command -v trivy &> /dev/null; then
    trivy image smartpip-trader:latest --json --output trivy-report.json || print_warning "trivy found vulnerabilities"
    print_status $? "Docker security scan completed"
else
    print_warning "trivy not installed (install with: brew install trivy or apt-get install trivy)"
fi
echo ""

# 7. Check file permissions
echo "7. Checking file permissions..."
find . -type f -perm -o+w -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./venv/*" > world-writable-files.txt || true
if [ -s world-writable-files.txt ]; then
    print_warning "Found world-writable files:"
    cat world-writable-files.txt
else
    print_status 0 "No world-writable files found"
fi
echo ""

# 8. Check for exposed .env files
echo "8. Checking for exposed .env files..."
if [ -f ".env" ] && [ -f ".gitignore" ]; then
    if grep -q ".env" .gitignore; then
        print_status 0 ".env file is in .gitignore"
    else
        print_warning ".env file exists but not in .gitignore"
    fi
else
    print_warning ".env file or .gitignore not found"
fi
echo ""

# 9. Check for SSH keys
echo "9. Checking for exposed SSH keys..."
find . -type f -name "*.pem" -o -name "*.key" -o -name "id_rsa*" -o -name "id_dsa*" | grep -v ".git" > ssh-keys.txt || true
if [ -s ssh-keys.txt ]; then
    print_warning "Found potential SSH keys:"
    cat ssh-keys.txt
else
    print_status 0 "No exposed SSH keys found"
fi
echo ""

# 10. Generate summary report
echo "=========================================="
echo "Security Audit Summary"
echo "=========================================="
echo ""
echo "Reports generated:"
echo "- bandit-report.json (Python security issues)"
echo "- trufflehog-report.json (Secret scan)"
echo "- outdated-deps.json (Outdated dependencies)"
echo "- trivy-report.json (Docker vulnerabilities)"
echo "- world-writable-files.txt (File permissions)"
echo "- ssh-keys.txt (SSH key scan)"
echo ""
echo "Review these files for detailed findings."
echo ""
print_status 0 "Security audit completed"
