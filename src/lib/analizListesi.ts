/* ─────────────────────────────────────────────────────────────
   Analiz listesi yardımcıları — ana sayfa ve /analiz/ aynı yerden okur.

   Seri: slug'ın tarihsiz kökü (buyume-2026-08-31 → buyume). Kart numarası
   KRONOLOJİK ve kalıcıdır: en eski yazı 01. Her yeni yazı numaraları
   kaydırmaz — bülten sayı numarasıyla aynı ilke.
   ───────────────────────────────────────────────────────────── */
import type { CollectionEntry } from 'astro:content';
import { olc } from './ders';

export type Analiz = CollectionEntry<'analiz'>;

export const seriKoku = (id: string) => id.replace(/-\d{4}-\d{2}-\d{2}$/, '');

/** Eskiden yeniye, aynı günde slug'a göre — deterministik. */
export function kronolojik(yazilar: Analiz[]): Analiz[] {
  return [...yazilar].sort((a, b) =>
    a.data.pubDate.valueOf() - b.data.pubDate.valueOf() || (a.id < b.id ? -1 : 1));
}

export interface AnalizKarti {
  yazi: Analiz;
  /** Kalıcı kronolojik numara (en eski = 1). */
  no: number;
  /** "serinin 2. yazısı" — seri tek yazıysa null. */
  seri: string | null;
  ekBilgi: string[];
}

export function kartlar(yazilar: Analiz[]): AnalizKarti[] {
  const sirali = kronolojik(yazilar);
  const seriSayisi = new Map<string, number>();
  for (const y of sirali) seriSayisi.set(seriKoku(y.id), (seriSayisi.get(seriKoku(y.id)) ?? 0) + 1);
  return sirali.map((y, i) => {
    const kok = seriKoku(y.id);
    let seri: string | null = null;
    if ((seriSayisi.get(kok) ?? 0) > 1) {
      const sira = sirali.filter((x) => seriKoku(x.id) === kok && x.data.pubDate <= y.data.pubDate).length;
      seri = `serinin ${sira}. yazısı`;
    }
    const o = olc(y.body);
    const ekBilgi = [`${o.sure} okuma`];
    if (o.grafik) ekBilgi.push(`${o.grafik} grafik`);
    if ((y.data as any).veriTarihi) ekBilgi.push(`veri ${new Date((y.data as any).veriTarihi).toISOString().slice(0, 10).split('-').reverse().join('.')}`);
    if (seri) ekBilgi.push(seri);
    return { yazi: y, no: i + 1, seri, ekBilgi };
  });
}
