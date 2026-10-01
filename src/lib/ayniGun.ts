/**
 * Bir bülten sayısıyla AYNI GÜN yayımlananlar (analiz yazıları, haftalık teknik).
 *
 * Tek tanım: sayının tarihli sayfası ile /bulten/ güncel sayı sayfası aynı
 * sayıyı basıyor ve biri bu bağı veriyor, öbürü vermiyordu — aynı sayı iki
 * adreste farklı içerikle.
 */
import { getCollection } from 'astro:content';
import { teknikler } from './yayinlar';
import { isoGun } from './bicim';

export interface AyniGunKaydi { tur: string; ad: string; href: string }

export async function ayniGunYayimlar(tarih: string): Promise<AyniGunKaydi[]> {
  return [
    ...(await getCollection('analiz'))
      .filter((y) => isoGun(y.data.pubDate) === tarih && y.data.durum !== 'taslak')
      .map((y) => ({ tur: 'Analiz', ad: y.data.title, href: `/analiz/${y.id}/` })),
    ...teknikler()
      .filter((t) => t.tarih === tarih)
      .map((t) => ({ tur: 'Haftalık teknik analiz', ad: `Sayı ${t.sayiNo}`, href: t.href })),
  ];
}
