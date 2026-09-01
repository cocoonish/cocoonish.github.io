/* RSS 2.0 belgesi — kütüphanesiz. Dört besleme aynı kalıbı kullanır. */
import { rfc822, xmlKacis } from './bicim';

export interface BeslemeOgesi {
  baslik: string;
  href: string;          // site köküne göreli ("/bulten/2026-09-01/")
  aciklama: string;      // düz metin
  tarih: Date | null;
  kategori?: string;
}

export interface Besleme {
  baslik: string;
  aciklama: string;
  yol: string;           // beslemenin kendi yolu ("/bulten/rss.xml")
  ogeler: BeslemeOgesi[];
}

export function rssBelgesi(site: URL | undefined, f: Besleme): string {
  if (!site) throw new Error('astro.config.mjs: `site` tanımsız — RSS mutlak adres kuramaz');
  const kok = site.toString().replace(/\/$/, '');
  const mutlak = (y: string) => `${kok}${y.startsWith('/') ? '' : '/'}${y}`;
  const en_yeni = f.ogeler.map((o) => o.tarih).filter(Boolean) as Date[];
  const son = en_yeni.length ? new Date(Math.max(...en_yeni.map((d) => d.getTime()))) : new Date(0);
  const ogeler = f.ogeler
    .map((o) => {
      const link = mutlak(o.href);
      return [
        '    <item>',
        `      <title>${xmlKacis(o.baslik)}</title>`,
        `      <link>${xmlKacis(link)}</link>`,
        `      <guid isPermaLink="true">${xmlKacis(link)}</guid>`,
        o.tarih ? `      <pubDate>${rfc822(o.tarih)}</pubDate>` : '',
        o.kategori ? `      <category>${xmlKacis(o.kategori)}</category>` : '',
        `      <description>${xmlKacis(o.aciklama)}</description>`,
        '    </item>',
      ].filter(Boolean).join('\n');
    })
    .join('\n');
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
    '  <channel>',
    `    <title>${xmlKacis(f.baslik)}</title>`,
    `    <link>${xmlKacis(kok + '/')}</link>`,
    `    <description>${xmlKacis(f.aciklama)}</description>`,
    '    <language>tr</language>',
    `    <lastBuildDate>${rfc822(son.getTime() ? son : new Date())}</lastBuildDate>`,
    `    <atom:link href="${xmlKacis(mutlak(f.yol))}" rel="self" type="application/rss+xml" />`,
    ogeler,
    '  </channel>',
    '</rss>',
    '',
  ].join('\n');
}

export const RSS_BASLIK = { 'Content-Type': 'application/rss+xml; charset=utf-8' };
