# Deployment Guide — www.smartpip.site

## DNS Settings

### For Netlify:
```
Type    Name    Value
A       @       75.2.60.5
CNAME   www     smartpip-trader.netlify.app
```

### For GitHub Pages:
```
Type    Name    Value
A       @       185.199.108.153
A       @       185.199.109.153
A       @       185.199.110.153
A       @       185.199.111.153
CNAME   www     yourusername.github.io
```

## App ID

Default App ID `1089` is Deriv's own. For production, register your own:
→ [api.deriv.com/app-registration](https://api.deriv.com/app-registration)

## Updating

Just replace `index.html`. No build process. No dependencies. No backend.

## SSL

All hosts above provide free SSL via Let's Encrypt.
Enable it in your host dashboard after DNS propagates (up to 24h).
