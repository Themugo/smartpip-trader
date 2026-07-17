# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** create a public GitHub issue
2. Email security findings to the project maintainers
3. Allow time for vulnerability assessment and patching
4. We will credit you in the security release notes (with your permission)

## Security Measures

### Authentication
- Supabase Auth with JWT tokens
- Email verification required for new accounts
- Password minimum 6 characters
- Session timeout after inactivity

### Data Protection
- All API tokens encrypted at rest
- HTTPS enforced for all connections
- No sensitive data in frontend state
- Secure cookie settings (httpOnly, secure, sameSite)

### API Security
- Rate limiting on all endpoints
- Input validation and sanitization
- CORS configured for allowed origins only
- Request size limits

### Frontend Security
- Content Security Policy headers
- XSS protection enabled
- Frame busting (X-Frame-Options: DENY)
- Strict MIME type checking

## Environment Variables

### Frontend (VITE_*)
These are PUBLIC and safe to expose:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL`

### Backend (Server-only)
These are SECRET and must never be exposed:
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `ENCRYPTION_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DERIV_API_TOKEN`

## Compliance

### Kenyan Market Regulations
- CMA license compliance
- CBK approved payment processing
- Tax calculation (20% VAT where applicable)
- Business hours enforcement

### Data Privacy
- User data encrypted
- Right to deletion (GDPR compliant)
- Data retention policies
- Audit logging

## Incident Response

If a security incident occurs:

1. Immediately notify the security team
2. Isolate affected systems
3. Assess and document the breach
4. Notify affected users (within 72 hours)
5. Implement fixes
6. Post-mortem and prevention measures
