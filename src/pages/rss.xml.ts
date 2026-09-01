import type { APIContext } from 'astro';
import { getCollection } from 'astro:content';
import { bultenler, teknikler } from '../lib/yayinlar';
import { rssBelgesi, RSS_BASLIK, type BeslemeOgesi } from '../lib/rss';

/** Tüm yayınlar tek beslemede: bülten, teknik analiz, analiz yazıları. */
export async function GET({ site }: APIContext) {
  const ogeler: BeslemeOgesi[] = [];
  for (const k of bultenler())
    ogeler.push({
      baslik: `${k.haftalik ? 'Haftaya bakış' : 'Günlük bülten'} — ${k.trTarih}`,
      href: k.href, aciklama: k.aciklama, tarih: k.yayinZamani ?? k.olcumZamani, kategori: 'Bülten',
    });
  for (const k of teknikler())
    ogeler.push({
      baslik: `Haftalık teknik analiz — ${k.trTarih}`,
      href: k.href, aciklama: k.aciklama, tarih: k.yayinZamani ?? k.olcumZamani, kategori: 'Teknik',
    });
  for (const a of await getCollection('analiz'))
    ogeler.push({
      baslik: a.data.title, href: `/analiz/${a.id}/`,
      aciklama: a.data.ozet ?? a.data.description, tarih: a.data.pubDate, kategori: 'Analiz',
    });
  ogeler.sort((x, y) => (y.tarih?.getTime() ?? 0) - (x.tarih?.getTime() ?? 0));
  return new Response(
    rssBelgesi(site, {
      baslik: 'TTO Trading — tüm yayınlar',
      aciklama: 'Türkiye makro ve piyasa araştırmaları: günlük bülten, haftalık teknik analiz ve analiz yazıları.',
      yol: '/rss.xml',
      ogeler: ogeler.slice(0, 60),
    }),
    { headers: RSS_BASLIK },
  );
}
