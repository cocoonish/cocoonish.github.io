/* ─────────────────────────────────────────────────────────────
   Projeler dizini — panolar yayım ritmine göre gruplanır, grup içinde
   verisi en yeni olan en üstte durur.

   Sıranın anahtarı kartta okura basılan tarihin KENDİSİDİR: panonun manşet
   büyüklüğünün kendi saati (lib/anaSayfa → hatManseti). Kartın yazdığı tarih
   ile sıranın dayandığı tarih ayrı kaynaktan gelseydi okur "veri 02.10" yazan
   bir kartı "veri 05.10" yazanın üstünde görebilirdi. Hattın son KOŞUSU sıra
   anahtarı olamaz: türev hatlar her koşuda çalışır ve veri ilerlemese de
   "bugün" görünürdü — koşu yeşil, damga taze, sayfa bayat.

   Ana sayfanın hat tablosu da aynı karşılaştırıcıyla dizilir (gruplamadan):
   eşit tarihlerde iki yer ayrı sıra basmasın.
   ───────────────────────────────────────────────────────────── */
import { hatManseti } from './anaSayfa';
import { isoGun, tariheCevir, yasMetni } from './bicim';
import { RITIMLER, RITIM_GRUBU, ARSIV_GRUBU, type Ritim } from './ritim';

/** Tazelik sırası: tarihli kart tarihsizden önce, yeni tarih önce, eşitlikte başlık (Türkçe sıra). */
export function tazelikSirasi(
  a: { gun: Date | null; baslik: string },
  b: { gun: Date | null; baslik: string },
): number {
  if (a.gun && b.gun && a.gun.getTime() !== b.gun.getTime()) return b.gun.getTime() - a.gun.getTime();
  if (a.gun && !b.gun) return -1;
  if (!a.gun && b.gun) return 1;
  return a.baslik.localeCompare(b.baslik, 'tr');
}

interface ProjeGirdisi {
  id: string;
  data: { title: string; durum: 'aktif' | 'taslak' | 'arsiv'; ritim: Ritim };
}

export interface DizinKarti<T> {
  proje: T;
  /** Kartta basılan veri tarihi ("05.10.2026", "09.2026"); yoksa boş. */
  tarih: string;
  gun: Date | null;
  /** Kartın tarih alanı (KayitKarti `veri`). Pano kartında HER ZAMAN vardır:
   *  tarih boşsa kart "veri yok" basar ve yayım tarihine geri DÜŞMEZ — köşe
   *  sayfanın tanımında veri tarihidir, yayım günü orada yanıltır. */
  veri: { tarih: string; iso: string; yas: string };
}

export interface DizinGrubu<T> {
  kod: Ritim | 'arsiv';
  ad: string;
  aciklama: string;
  kartlar: DizinKarti<T>[];
}

export function projeDizini<T extends ProjeGirdisi>(projeler: T[]): DizinGrubu<T>[] {
  const gruplar: DizinGrubu<T>[] = [
    ...RITIMLER.map((kod) => ({ kod, ...RITIM_GRUBU[kod], kartlar: [] as DizinKarti<T>[] })),
    { kod: 'arsiv' as const, ...ARSIV_GRUBU, kartlar: [] as DizinKarti<T>[] },
  ];
  for (const p of projeler) {
    const h = hatManseti(p.id);
    const gun = tariheCevir(h.tarih);
    // Aylık damga (AA.YYYY) bir GÜN değildir: ayın son gününe demirlenir ve
    // "5 gün önce" okura o günün ölçümü gibi görünürdü. Yaş yalnız gün damgasında.
    const ay = /^\d{2}\.\d{4}$/.test(h.tarih);
    const kod = p.data.durum === 'arsiv' ? 'arsiv' : p.data.ritim;
    gruplar.find((g) => g.kod === kod)!.kartlar.push({
      proje: p,
      tarih: h.tarih,
      gun,
      veri: {
        tarih: h.tarih,
        iso: gun ? (ay ? isoGun(gun).slice(0, 7) : isoGun(gun)) : '',
        yas: h.tarih && !ay ? yasMetni(h.yas) : '',
      },
    });
  }
  for (const g of gruplar) {
    g.kartlar.sort((a, b) =>
      tazelikSirasi({ gun: a.gun, baslik: a.proje.data.title }, { gun: b.gun, baslik: b.proje.data.title }),
    );
  }
  return gruplar.filter((g) => g.kartlar.length > 0);
}
