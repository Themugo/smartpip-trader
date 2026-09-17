// Generate sitemap data for dynamic routes.
// Currently unused at runtime (public/sitemap.xml is served statically),
// kept as a utility for generating that file when routes change.
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
