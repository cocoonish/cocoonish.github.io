import type { APIContext } from 'astro';
import { teknikler } from '../../lib/yayinlar';
import { rssBelgesi, RSS_BASLIK } from '../../lib/rss';

export async function GET({ site }: APIContext) {
  return new Response(
    rssBelgesi(site, {
      baslik: 'TTO Trading — Haftalık Teknik Analiz',
      aciklama: 'ABD 2Y/10Y, DXY, EUR/USD, USD/CHF ve BIST 100 için ölçüme dayalı haftalık teknik analiz.',
      yol: '/teknik/rss.xml',
      ogeler: teknikler().slice(0, 40).map((k) => ({
        baslik: `Haftalık teknik analiz — ${k.trTarih}`,
        href: k.href, aciklama: k.aciklama, tarih: k.yayinZamani ?? k.olcumZamani,
      })),
    }),
    { headers: RSS_BASLIK },
  );
}
