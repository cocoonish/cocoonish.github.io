import type { APIContext } from 'astro';
import { bultenler } from '../../lib/yayinlar';
import { rssBelgesi, RSS_BASLIK } from '../../lib/rss';

export async function GET({ site }: APIContext) {
  return new Response(
    rssBelgesi(site, {
      baslik: 'TTO Trading — Bülten',
      aciklama: 'Hafta içi her sabah günlük makro bülteni, pazar akşamı haftaya bakış.',
      yol: '/bulten/rss.xml',
      ogeler: bultenler().slice(0, 40).map((k) => ({
        baslik: `${k.haftalik ? 'Haftaya bakış' : 'Günlük bülten'} — ${k.trTarih}`,
        href: k.href, aciklama: k.aciklama, tarih: k.yayinZamani ?? k.olcumZamani,
        kategori: k.haftalik ? 'Haftaya bakış' : 'Günlük',
      })),
    }),
    { headers: RSS_BASLIK },
  );
}
