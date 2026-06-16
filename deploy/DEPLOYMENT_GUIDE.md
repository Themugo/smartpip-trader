# Deployment Guide for SmartPip Trading System

## Deployment Scripts Overview

### Active Scripts
- **deploy.sh** - Basic local development deployment
- **production_deploy.sh** - Production deployment with security hardening
- **docker-signing.sh** - Docker image signing with Cosign
- **slsa-provenance.sh** - SLSA provenance generation

### Deprecated Scripts (Archived)
- **deploy_derivfusion.sh** - Use production_deploy.sh instead
- **final_production_deploy.sh** - Use production_deploy.sh instead
- **smartpip_deploy.sh** - Use production_deploy.sh instead

## Deployment Methods

### 1. Local Development Deployment
```bash
cd deploy
./deploy.sh
```

### 2. Production Deployment
```bash
cd deploy
./production_deploy.sh
```

### 3. Docker Deployment
```bash
docker build -f deploy/Dockerfile -t smartpip-trader .
docker run -p 8000:8000 --env-file .env smartpip-trader
```

### 4. Docker Compose Deployment
```bash
docker-compose -f deploy/docker-compose.yml up -d
```

### 5. Security-Hardened Deployment
```bash
docker-compose -f deploy/docker-compose.security.yml up -d
```

## Deployment Checklist

### Pre-Deployment
- [ ] Copy .env.example to .env
- [ ] Fill in all required environment variables
- [ ] Generate secure secrets (JWT_SECRET_KEY, ENCRYPTION_KEY)
- [ ] Configure KMS provider (if using)
- [ ] Set up Redis (if using rate limiting)
- [ ] Configure notification channels
- [ ] Set up M-Pesa (if using Kenyan market)

### Security Hardening
- [ ] Run security audit: `bash scripts/security-audit.sh`
- [ ] Sign Docker image: `bash deploy/docker-signing.sh`
- [ ] Generate SLSA provenance: `bash deploy/slsa-provenance.sh`
- [ ] Verify image signature
- [ ] Run chaos engineering tests

### Post-Deployment
- [ ] Verify health check: `curl http://localhost:8000/health`
- [ ] Check API docs: `http://localhost:8000/docs`
- [ ] Test WebSocket connection
- [ ] Verify monitoring dashboards
- [ ] Check anomaly detection
- [ ] Test kill switch
- [ ] Verify rate limiting

## Environment Variables

See `.env.example` for all required environment variables.

### Required Variables
- `DERIV_API_TOKEN` - Deriv API token
- `JWT_SECRET_KEY` - JWT signing key
- `SANITIZATION_SECRET_KEY` - Payload signature secret
- `DB_ENCRYPTION_KEY` - Database encryption key

### Optional Variables
- `REDIS_URL` - Redis connection URL
- `KMS_PROVIDER` - KMS provider (aws, azure, hashicorp)
- Notification configuration variables
- M-Pesa configuration variables

## Security Considerations

### Container Security
- Non-root user execution
- Read-only filesystem
- seccomp security profile
- Resource limits
- Health checks

### Application Security
- JWT authentication
- Rate limiting
- Input sanitization
- Payload signature validation
- Replay attack prevention
- IP whitelisting

### Supply Chain Security
- Docker image signing
- SLSA provenance
- SBOM generation
- Dependency vulnerability scanning

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Metrics
- Prometheus metrics available at `/metrics`
- Grafana dashboard configuration in `monitoring/grafana-dashboard.json`

### Logs
- Structured logging with OpenTelemetry
- Log aggregation configured in `monitoring/opentelemetry_config.py`

## Troubleshooting

### Container won't start
- Check environment variables in .env
- Verify Docker image build
- Check container logs: `docker logs smartpip-trader`

### Connection issues
- Verify DERIV_API_TOKEN
- Check network connectivity
- Verify WebSocket connection

### Performance issues
- Check cache hit rate
- Monitor API latency
- Review performance metrics

### Security issues
- Check rate limiting logs
- Review security alerts
- Verify IP whitelisting

## Rollback Procedure

### Docker Rollback
```bash
docker stop smartpip-trader
docker rm smartpip-trader
docker run -p 8000:8000 --env-file .env smartpip-trader:previous-version
```

### Git Rollback
```bash
git revert <commit-hash>
git push origin main
```

## Support

For deployment issues, refer to:
- COMPREHENSIVE_AUDIT_REPORT.md - Full system audit
- docs/RUNTIME_PATH.md - Runtime architecture
- compliance/SOC2_READINESS.md - Compliance documentation
