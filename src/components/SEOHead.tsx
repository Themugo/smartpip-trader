import { useEffect } from 'react';

interface SEOHeadProps {
  title?: string;
  description?: string;
  keywords?: string[];
  ogImage?: string;
  ogType?: 'website' | 'article';
  canonicalUrl?: string;
  noIndex?: boolean;
}

export function SEOHead({
  title = 'SmartPip Trader - AI-Powered Trading Platform',
  description = 'Automate your Deriv trading with advanced AI algorithms, real-time market analysis, and institutional-grade risk management. No coding required.',
  keywords = ['AI trading', 'automated trading', 'Deriv', 'Volatility Indices', 'trading bot', 'quantitative trading'],
  ogImage = '/og-image.png',
  ogType = 'website',
  canonicalUrl,
  noIndex = false,
}: SEOHeadProps) {
  const siteUrl = 'https://smartpip.trade';
  const fullUrl = canonicalUrl || siteUrl;
  const fullTitle = title.includes('SmartPip') ? title : `${title} | SmartPip Trader`;

  useEffect(() => {
    // Update document title
    document.title = fullTitle;

    // Update meta tags
    const updateMeta = (name: string, content: string, property?: boolean) => {
      const selector = property ? `meta[property="${name}"]` : `meta[name="${name}"]`;
      let meta = document.querySelector(selector) as HTMLMetaElement;
      
      if (!meta) {
        meta = document.createElement('meta');
        if (property) {
          meta.setAttribute('property', name);
        } else {
          meta.setAttribute('name', name);
        }
        document.head.appendChild(meta);
      }
      meta.content = content;
    };

    // Basic meta
    updateMeta('description', description);
    updateMeta('keywords', keywords.join(', '));
    if (noIndex) {
      updateMeta('robots', 'noindex, nofollow');
    }

    // Open Graph
    updateMeta('og:title', fullTitle, true);
    updateMeta('og:description', description, true);
    updateMeta('og:type', ogType, true);
    updateMeta('og:url', fullUrl, true);
    updateMeta('og:image', `${siteUrl}${ogImage}`, true);
    updateMeta('og:site_name', 'SmartPip Trader', true);
    updateMeta('og:locale', 'en_US', true);

    // Twitter
    updateMeta('twitter:card', 'summary_large_image');
    updateMeta('twitter:title', fullTitle);
    updateMeta('twitter:description', description);
    updateMeta('twitter:image', `${siteUrl}${ogImage}`);
    updateMeta('twitter:site', '@smartpip');

    // Canonical link
    let canonical = document.querySelector('link[rel="canonical"]') as HTMLLinkElement;
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.rel = 'canonical';
      document.head.appendChild(canonical);
    }
    canonical.href = fullUrl;

    // Structured Data (JSON-LD)
    const structuredData = {
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: 'SmartPip Trader',
      applicationCategory: 'FinanceApplication',
      operatingSystem: 'Web',
      description: description,
      url: siteUrl,
      offers: {
        '@type': 'AggregateOffer',
        priceCurrency: 'USD',
        lowPrice: '0',
        highPrice: '199',
        offerCount: '4'
      },
      aggregateRating: {
        '@type': 'AggregateRating',
        ratingValue: '4.8',
        ratingCount: '1250'
      }
    };

    let script = document.querySelector('script[type="application/ld+json"]') as HTMLScriptElement;
    if (!script) {
      script = document.createElement('script');
      script.type = 'application/ld+json';
      document.head.appendChild(script);
    }
    script.textContent = JSON.stringify(structuredData);

  }, [title, description, keywords, ogImage, ogType, canonicalUrl, fullUrl, fullTitle, noIndex]);

  return null;
}

// Generate sitemap data for dynamic routes
export function generateSitemap(routes: { url: string; priority: number; changefreq: string }[]): string {
  const siteUrl = 'https://smartpip.trade';
  
  const urls = routes.map(route => `
  <url>
    <loc>${siteUrl}${route.url}</loc>
    <changefreq>${route.changefreq}</changefreq>
    <priority>${route.priority}</priority>
  </url>`).join('');

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>`;
}
