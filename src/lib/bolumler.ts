/* ─────────────────────────────────────────────────────────────
   Site bölümleri — TEK kaynak.

   Başlıktaki gezinme "01 Bülten · 02 Teknik · 03 Analiz …" derken liste
   sayfalarının kicker'ları başka numaralar yazıyordu: Analiz "02 — Bölüm",
   Projeler "03 — Bölüm", Dersler ve Arama "04 — Bölüm", Hakkında "03 —
   Bölüm". Üç yer elle tutulduğu için sessizce ayrışmıştı. Numara, ad, adres
   ve tek cümlelik açıklama buradan okunur; başlık, alt bilgi, kicker ve
   site haritası aynı listeyi kullanır.
   ───────────────────────────────────────────────────────────── */

export interface Bolum {
  no: string;
  ad: string;
  href: string;
  /** Alt bilgide ve 404 sayfasında görünen tek cümle. */
  aciklama: string;
  /** Başlık gezinmesinde görünsün mü (Arama gibi yardımcı sayfalar da görünür). */
  gezinme: boolean;
  /** RSS beslemesi varsa yolu. */
  rss?: string;
}

export const BOLUMLER: Bolum[] = [
  {
    no: '01', ad: 'Bülten', href: '/bulten/', gezinme: true, rss: '/bulten/rss.xml',
    aciklama: 'Hafta içi her sabah günlük, pazar akşamı haftaya bakış: ölçülen piyasa, takvim ve günün okuması.',
  },
  {
    no: '02', ad: 'Teknik', href: '/teknik/', gezinme: true, rss: '/teknik/rss.xml',
    aciklama: 'Haftalık teknik analiz: altı enstrüman, üç zaman dilimi, ölçüme dayalı senaryolar.',
  },
  {
    no: '03', ad: 'Analiz', href: '/analiz/', gezinme: true, rss: '/analiz/rss.xml',
    aciklama: 'Tek bir piyasa gelişmesini mekanizmasına, emsaline ve fiyat etkisine kadar açan uzun yazılar.',
  },
  {
    no: '04', ad: 'Projeler', href: '/projeler/', gezinme: true,
    aciklama: 'Kendi kaynağından beslenen, kendi ritminde tazelenen veri panoları; her sayı kendi tarihini taşır.',
  },
  {
    no: '05', ad: 'Dersler', href: '/arastirma/', gezinme: true,
    aciklama: 'Faiz, kur, opsiyon ve teknik analiz üzerine ders formatında uzun notlar.',
  },
  {
    no: '06', ad: 'Hakkında', href: '/hakkinda/', gezinme: true,
    aciklama: 'Sitenin amacı, yayın ilkeleri, yayın takvimi ve düzeltme politikası.',
  },
  {
    no: '07', ad: 'Arama', href: '/arama/', gezinme: true,
    aciklama: 'Başlık, etiket ve metinlerde tam metin arama.',
  },
];

/** Sayfanın ait olduğu bölüm (yol önekine göre). */
export function bolumBul(yol: string): Bolum | undefined {
  return BOLUMLER.find((b) => yol.startsWith(b.href));
}

/** Liste sayfalarının kicker metni: "03 — Bölüm". */
export function kicker(href: string): string {
  const b = BOLUMLER.find((x) => x.href === href);
  return b ? `${b.no} — Bölüm` : 'Bölüm';
}

/** Beslemesi olan bölümler (Base.astro <link rel="alternate"> için). */
export const BESLEMELER = [
  { ad: 'TTO Trading — tüm yayınlar', href: '/rss.xml' },
  ...BOLUMLER.filter((b) => b.rss).map((b) => ({ ad: `TTO Trading — ${b.ad}`, href: b.rss! })),
];
