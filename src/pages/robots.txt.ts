import type { APIRoute } from 'astro';

// robots.txt yayın adresini astro.config.mjs `site` alanından kurar; sabit
// adres taşımaz (adres değişince unutulan bir kopya eski adresi anlatırdı).
export const GET: APIRoute = ({ site }) => {
  if (!site) throw new Error('astro.config.mjs: `site` tanımsız — robots.txt kurulamaz');
  const govde = `User-agent: *\nAllow: /\n\nSitemap: ${new URL('sitemap-index.xml', site)}\n`;
  return new Response(govde, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
