import type { APIContext } from 'astro';
import { getCollection } from 'astro:content';
import { rssBelgesi, RSS_BASLIK } from '../../lib/rss';

export async function GET({ site }: APIContext) {
  const yazilar = (await getCollection('analiz')).sort(
    (a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf(),
  );
  return new Response(
    rssBelgesi(site, {
      baslik: 'TTO Trading — Analiz',
      aciklama: 'Tek bir piyasa gelişmesini mekanizmasına, tarihsel emsaline ve fiyat etkisine kadar açan uzun yazılar.',
      yol: '/analiz/rss.xml',
      ogeler: yazilar.map((a) => ({
        baslik: a.data.title, href: `/analiz/${a.id}/`,
        aciklama: a.data.ozet ?? a.data.description, tarih: a.data.pubDate,
        kategori: a.data.tags?.[0],
      })),
    }),
    { headers: RSS_BASLIK },
  );
}
