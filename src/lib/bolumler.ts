/* ─────────────────────────────────────────────────────────────
   Site bölümleri — TEK kaynak.

   Başlıktaki gezinme "01 Bülten · 02 Analiz · 03 Projeler …" derken liste
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
  /** Yayını sona ermiş bölüm: sayfaları kendi adreslerinde durur; gezinmede,
   *  alt bilginin yayın kolonunda ve besleme listesinde görünmez. */
  arsiv?: boolean;
}

export const BOLUMLER: Bolum[] = [
  {
    no: '01', ad: 'Bülten', href: '/bulten/', gezinme: true, rss: '/bulten/rss.xml',
    aciklama: 'Hafta içi her sabah günlük, pazar akşamı haftaya bakış: ölçülen piyasa, takvim ve günün okuması.',
  },
  // İşlem fikirlerinin defteri bültenden doğar, o yüzden hemen ardında
  // (04.10.2026). Numaralar yalnız bu listede yazılı; başlık, alt bilgi, 404,
  // hakkında ve kicker'lar buradan okur — kaydırma başka hiçbir dosyaya dokunmaz.
  {
    no: '02', ad: 'Tradeler', href: '/tradeler/', gezinme: true,
    aciklama: 'Bültenin okumasından türeyen işlem fikirlerinin defteri: neden açıldı, ne durumda, nasıl kapandı, kârla mı zararla mı — karne ölçülen katmandan, kapanış bazında.',
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
    no: '06', ad: 'İndikatörler', href: '/indikatorler/', gezinme: true,
    aciklama: 'Derslerde öğretilen yöntemlerin TradingView karşılığı: kaynağı açık, eşiği dersten gelen Pine Script indikatörleri.',
  },
  {
    no: '07', ad: 'Hakkında', href: '/hakkinda/', gezinme: true,
    aciklama: 'Sitenin amacı, yayın ilkeleri, yayın takvimi ve düzeltme politikası.',
  },
  {
    no: '08', ad: 'Arama', href: '/arama/', gezinme: true,
    aciklama: 'Başlık, etiket ve metinlerde tam metin arama.',
  },
  // Haftalık teknik analiz 27.09.2026 sayısıyla sona erdi (01.10.2026, kullanıcı
  // kararı). Beş sayı kendi adreslerinde arşivde duruyor; bölüm gezinmeden ve
  // besleme listesinden çıktı, numarası sona alındı ki gezinmede boşluk kalmasın.
  {
    no: '09', ad: 'Teknik arşivi', href: '/teknik/', gezinme: false, rss: '/teknik/rss.xml', arsiv: true,
    aciklama: 'Haftalık teknik analizin 30 Ağustos–27 Eylül 2026 arasında yayımlanan beş sayısı; yayın 27 Eylül 2026 sayısıyla sona erdi.',
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
  ...BOLUMLER.filter((b) => b.rss && !b.arsiv).map((b) => ({ ad: `TTO Trading — ${b.ad}`, href: b.rss! })),
];
