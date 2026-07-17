# SmartPip Trader - Production Deployment Checklist

## Pre-Deployment Checklist

### Code Quality
- [ ] All tests passing (`npm run test`)
- [ ] No TypeScript errors (`npm run type-check`)
- [ ] No linting errors (`npm run lint`)
- [ ] Build completes successfully (`npm run build`)
- [ ] Bundle size optimized (< 500KB gzipped)

### Security
- [ ] Environment variables configured
- [ ] API keys secured (not in code)
- [ ] CORS configured for production domain
- [ ] Security headers enabled
- [ ] Rate limiting configured
- [ ] Input validation in place
- [ ] No debug mode in production

### Environment Variables
- [ ] `VITE_SUPABASE_URL` set
- [ ] `VITE_SUPABASE_ANON_KEY` set
- [ ] `VITE_API_URL` set
- [ ] Database migrations run
- [ ] Redis configured

### Features
- [ ] Authentication working
- [ ] Broker connections functional
- [ ] Subscription system tested
- [ ] All UI components render
- [ ] Mobile responsiveness verified
- [ ] Dark/light themes work

## Deployment Steps

### 1. Vercel Deployment
```bash
# Connect repository to Vercel
vercel --prod

# Or use GitHub integration
# Settings → Git → Connect GitHub → Enable Auto-Deploy
```

### 2. Environment Configuration
1. Go to Vercel Dashboard → Project → Settings → Environment Variables
2. Add all `VITE_*` variables:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_API_URL`
3. Redeploy after adding variables

### 3. Database Setup (Supabase)
1. Create production project in Supabase
2. Run migrations: `supabase db push`
3. Enable Row Level Security (RLS)
4. Configure authentication settings
5. Set up email templates

### 4. Domain Configuration
1. Add custom domain in Vercel
2. Configure DNS records
3. Enable SSL certificate
4. Set up redirects (www → non-www)

## Post-Deployment Verification

### Functional Tests
- [ ] Landing page loads
- [ ] Sign up flow works
- [ ] Email verification works
- [ ] Login/logout works
- [ ] Dashboard loads
- [ ] Settings pages accessible
- [ ] Broker connection UI present
- [ ] Subscription page loads

### Performance
- [ ] First Contentful Paint < 2s
- [ ] Largest Contentful Paint < 4s
- [ ] Time to Interactive < 5s
- [ ] Cumulative Layout Shift < 0.1

### Monitoring
- [ ] Error tracking enabled (Sentry)
- [ ] Analytics configured
- [ ] Uptime monitoring set up
- [ ] Log aggregation working
- [ ] Alerts configured

## Rollback Procedure

If issues occur:
1. Vercel Dashboard → Deployments → Previous deployment → "Promote to Production"
2. Or: `vercel --prod --force` with previous version

## Emergency Contacts

| Role | Contact |
|------|---------|
| DevOps Lead | TBD |
| Backend Lead | TBD |
| Frontend Lead | TBD |
| Supabase Support | support@supabase.io |
| Vercel Support | support@vercel.com |
