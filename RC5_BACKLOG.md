# SmartPip RC5 – Technical Debt & Improvement Backlog

**Date:** July 18, 2026  
**Version:** RC5  
**Status:** Technical Debt Documented

---

## 1. Executive Summary

This document catalogs all technical debt identified during the RC5 architecture audit and provides a prioritized backlog for resolution.

**Total Issues Identified:** 47  
**Critical:** 5  
**High Priority:** 12  
**Medium:** 18  
**Low:** 12

---

## 2. Critical Technical Debt (P0)

### Issue #1: Supabase RLS Not Enabled

| Field | Value |
|-------|-------|
| Category | Security |
| Estimated Effort | 1 day |
| Risk if Unaddressed | Critical data breach |
| Dependencies | None |

**Action Required:**
```sql
-- Enable RLS on all tables
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_statistics ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_insights ENABLE ROW LEVEL SECURITY;

-- Create policies for each table
CREATE POLICY "Users can only see own trades" ON trades
  FOR ALL USING (auth.uid() = user_id);
-- Repeat for other tables
```

### Issue #2: Broker Tokens in Frontend

| Field | Value |
|-------|-------|
| Category | Security |
| Estimated Effort | 3 days |
| Risk if Unaddressed | Credential exposure |
| Dependencies | None |

**Action Required:**
- Move broker tokens to Supabase with encryption
- Create API endpoints for token retrieval
- Implement server-side token injection
- Remove localStorage token storage

### Issue #3: WebSocket No Authentication

| Field | Value |
|-------|-------|
| Category | Security |
| Estimated Effort | 2 days |
| Risk if Unaddressed | Unauthorized access |
| Dependencies | None |

**Action Required:**
- Add JWT validation to WebSocket handshake
- Implement token refresh on disconnect
- Add connection authorization
- Log all connections

### Issue #4: Type Safety Gaps

| Field | Value |
|-------|-------|
| Category | Code Quality |
| Estimated Effort | 2 days |
| Risk if Unaddressed | Runtime errors |
| Dependencies | None |

**Action Required:**
- Fix remaining type mismatches
- Add strict null checks
- Enable noUnusedLocals/noUnusedParameters
- Add comprehensive type coverage

### Issue #5: Test Coverage

| Field | Value |
|-------|-------|
| Category | Testing |
| Estimated Effort | 5 days |
| Risk if Unaddressed | Confidence in changes |
| Dependencies | None |

**Action Required:**
- Write unit tests for all hooks
- Write integration tests for API
- Add E2E tests for critical flows
- Set up CI/CD test pipeline

---

## 3. High Priority Debt (P1)

### Issue #6: Mobile Responsive Issues

| Field | Value |
|-------|-------|
| Category | UX |
| Estimated Effort | 3 days |
| Impact | User experience |
| Dependencies | None |

**Action Required:**
- Fix navigation hamburger menu
- Improve chart sizing
- Fix button spacing
- Test on multiple devices

### Issue #7: API v2 Orphan Code

| Field | Value |
|-------|-------|
| Category | Code Quality |
| Estimated Effort | 0.5 days |
| Impact | Maintenance burden |
| Dependencies | None |

**Action Required:**
- Delete src/lib/api_v2.ts
- Update all imports to use api.ts
- Verify all endpoints work

### Issue #8: WorkspaceContainer Unused

| Field | Value |
|-------|-------|
| Category | Code Quality |
| Estimated Effort | 1 day |
| Impact | Code complexity |
| Dependencies | None |

**Action Required:**
- Either integrate or remove WorkspaceContainer
- Document navigation architecture
- Remove dead code

### Issue #9: AI Command Center Mock Data

| Field | Value |
|-------|-------|
| Category | Functionality |
| Estimated Effort | 5 days |
| Impact | Core feature quality |
| Dependencies | AI service |

**Action Required:**
- Connect to real AI service
- Replace mock responses
- Add streaming support
- Implement error handling

### Issue #10: Subscription Mock Data

| Field | Value |
|-------|-------|
| Category | Billing |
| Estimated Effort | 5 days |
| Impact | Revenue generation |
| Dependencies | Stripe account |

**Action Required:**
- Connect to Stripe
- Implement subscription CRUD
- Add webhook handlers
- Test payment flows

### Issue #11: Missing Error Recovery UI

| Field | Value |
|-------|-------|
| Category | UX |
| Estimated Effort | 2 days |
| Impact | User experience |
| Dependencies | None |

**Action Required:**
- Add recovery steps to errors
- Add retry buttons
- Add help links
- Improve error messages

### Issue #12: No Onboarding Workspace Creation

| Field | Value |
|-------|-------|
| Category | UX |
| Estimated Effort | 3 days |
| Impact | User activation |
| Dependencies | None |

**Action Required:**
- Add workspace creation step
- Add workspace selection
- Add workspace settings
- Persist workspace choice

### Issue #13: Missing ARIA Labels

| Field | Value |
|-------|-------|
| Category | Accessibility |
| Estimated Effort | 2 days |
| Impact | Screen reader users |
| Dependencies | None |

**Action Required:**
- Add labels to icon buttons
- Add labels to form inputs
- Add labels to charts
- Test with screen reader

### Issue #14: Missing Input Validation

| Field | Value |
|-------|-------|
| Category | Security |
| Estimated Effort | 2 days |
| Impact | Data integrity |
| Dependencies | None |

**Action Required:**
- Add broker token format validation
- Add workspace name validation
- Add strategy name validation
- Add length limits

### Issue #15: Missing 2FA

| Field | Value |
|-------|-------|
| Category | Security |
| Estimated Effort | 2 days |
| Impact | Account security |
| Dependencies | None |

**Action Required:**
- Enable Supabase 2FA
- Add 2FA setup flow
- Require 2FA for live trading
- Add 2FA recovery codes

### Issue #16: No Audit Log Alerting

| Field | Value |
|-------|-------|
| Category | Operations |
| Estimated Effort | 3 days |
| Impact | Security monitoring |
| Dependencies | Monitoring tool |

**Action Required:**
- Set up alerting service
- Define alert rules
- Add Slack/email notifications
- Document alert response

### Issue #17: Missing Documentation

| Field | Value |
|-------|-------|
| Category | Documentation |
| Estimated Effort | 3 days |
| Impact | Developer experience |
| Dependencies | None |

**Action Required:**
- Document architecture
- Document API endpoints
- Document deployment process
- Create troubleshooting guide

---

## 4. Medium Priority Debt (P2)

### Issue #18: Skeleton vs Spinner Inconsistency
- **Effort:** 1 day
- **Action:** Standardize all loading states

### Issue #19: Missing Breadcrumb Navigation
- **Effort:** 1 day
- **Action:** Add breadcrumb component

### Issue #20: Missing Skip Links
- **Effort:** 0.5 days
- **Action:** Add skip navigation links

### Issue #21: No Confirmation Dialogs
- **Effort:** 2 days
- **Action:** Add for critical actions

### Issue #22: Missing HSTS Header
- **Effort:** 0.5 days
- **Action:** Add HSTS configuration

### Issue #23: WebSocket Rate Limiting
- **Effort:** 1 day
- **Action:** Add rate limit to WebSocket

### Issue #24: No Password Policy
- **Effort:** 0.5 days
- **Action:** Configure in Supabase

### Issue #25: Session Timeout Not Implemented
- **Effort:** 1 day
- **Action:** Add 30-minute timeout

### Issue #26: No Field-Level Encryption
- **Effort:** 3 days
- **Action:** Add for sensitive data

### Issue #27: Missing Log Retention
- **Effort:** 0.5 days
- **Action:** Set 90-day retention

### Issue #28: Analytics Dashboard Placeholder
- **Effort:** 2 days
- **Action:** Connect to real data

### Issue #29: No Load Testing
- **Effort:** 2 days
- **Action:** Add k6 load tests

### Issue #30: Missing Performance Monitoring
- **Effort:** 2 days
- **Action:** Add Datadog/Sentry

### Issue #31: Responsive Table Issues
- **Effort:** 2 days
- **Action:** Add horizontal scroll

### Issue #32: Missing Mobile Navigation
- **Effort:** 2 days
- **Action:** Add hamburger menu

### Issue #33: No Multi-language Support
- **Effort:** 5 days
- **Action:** Add i18n system

### Issue #34: Missing Tooltip Help System
- **Effort:** 2 days
- **Action:** Add tooltip component

### Issue #35: No Tutorial Overlays
- **Effort:** 3 days
- **Action:** Add onboarding tour

---

## 5. Low Priority Debt (P3)

### Issue #36: Inconsistent Naming (PnLChart)
- **Effort:** 0.5 days
- **Action:** Rename to PnlChart

### Issue #37: No Console.log Cleanup
- **Effort:** 1 day
- **Action:** Replace with proper logging

### Issue #38: Missing TODO Comments
- **Effort:** 0.5 days
- **Action:** Add JSDoc or create issues

### Issue #39: No Bundle Analysis
- **Effort:** 0.5 days
- **Action:** Add bundle analyzer

### Issue #40: No Source Maps in Production
- **Effort:** 0.5 days
- **Action:** Configure source maps

### Issue #41: Missing Error Boundaries
- **Effort:** 1 day
- **Action:** Add React error boundaries

### Issue #42: No Request Cancellation
- **Effort:** 1 day
- **Action:** Add AbortController

### Issue #43: No Request Retries
- **Effort:** 1 day
- **Action:** Add retry logic

### Issue #44: Missing Loading States
- **Effort:** 1 day
- **Action:** Add to AI queries

### Issue #45: No Pagination
- **Effort:** 2 days
- **Action:** Add to trade history

### Issue #46: Missing Virtualization
- **Effort:** 2 days
- **Action:** Add for long lists

### Issue #47: No Offline Support
- **Effort:** 5 days
- **Action:** Add PWA offline mode

---

## 6. Prioritized Backlog

### 6.1 Sprint 1 (Week 1) - Security Hardening

| Issue | Priority | Points | Owner |
|-------|----------|--------|-------|
| #1 RLS Enabled | P0 | 8 | Security |
| #2 Broker Tokens | P0 | 13 | Backend |
| #3 WebSocket Auth | P0 | 8 | Backend |
| #15 2FA | P1 | 5 | Backend |
| #14 Input Validation | P1 | 5 | Backend |

### 6.2 Sprint 2 (Week 2) - Code Quality

| Issue | Priority | Points | Owner |
|-------|----------|--------|-------|
| #4 Type Safety | P0 | 8 | Frontend |
| #7 API v2 Orphan | P1 | 2 | Frontend |
| #8 Workspace Unused | P1 | 3 | Frontend |
| #18 Loading Consistency | P2 | 3 | Frontend |
| #37 Console Cleanup | P3 | 2 | Frontend |

### 6.3 Sprint 3 (Week 3) - UX Improvements

| Issue | Priority | Points | Owner |
|-------|----------|--------|-------|
| #6 Mobile Responsive | P1 | 8 | Frontend |
| #11 Error Recovery | P1 | 5 | Frontend |
| #13 ARIA Labels | P1 | 5 | Frontend |
| #21 Confirmation Dialogs | P2 | 5 | Frontend |
| #32 Mobile Nav | P2 | 5 | Frontend |

### 6.4 Sprint 4 (Week 4) - Features

| Issue | Priority | Points | Owner |
|-------|----------|--------|-------|
| #9 AI Command Center | P1 | 13 | AI Team |
| #10 Subscriptions | P1 | 13 | Backend |
| #12 Onboarding | P1 | 8 | Frontend |
| #5 Test Coverage | P0 | 13 | QA |
| #16 Audit Alerting | P1 | 8 | DevOps |

---

## 7. Definition of Done

Each issue must have:
- [ ] Code changes committed
- [ ] TypeScript passes
- [ ] Build succeeds
- [ ] Tests written (if applicable)
- [ ] Reviewed by peer
- [ ] Documentation updated

---

## 8. Metrics

| Metric | Baseline | Target | Current |
|--------|----------|--------|---------|
| TypeScript Errors | 148 | 0 | 0 |
| Test Coverage | 40% | 80% | TBD |
| Security Score | 82% | 95% | TBD |
| Mobile UX | 60% | 85% | TBD |
| API Response Time | 150ms | 100ms | TBD |

---

**Technical Debt Backlog Completed:** July 18, 2026  
**Last Updated:** July 18, 2026  
**Next Review:** Weekly in sprint planning
