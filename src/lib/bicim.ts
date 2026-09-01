/* ─────────────────────────────────────────────────────────────
   Biçim yardımcıları — TEK yer.

   Sayı, yüzde ve tarih yazımı sitede beş ayrı dosyada birbirinden habersiz
   kopyalanmıştı (ana sayfa, bülten gövdesi, teknik gövde, kart, canlı
   değer). Aynı sayı bir sayfada "−1,88", diğerinde "-1.88" çıkabiliyordu.
   Kural buradan okunur; başka yerde sayı biçimlenmez.

   Türkçe yazım kararları:
   · Ondalık ayracı virgül, binlik ayracı nokta (tr-TR).
   · Eksi işareti U+2212 (−), ASCII tire değil — tabloda hizalama bozulmaz.
   · Yüzde işareti sayıdan ÖNCE gelir, işaret onun da önünde: "−%1,88", "+%0,4".
   · Baz puan bir birimdir, sayıdan sonra yazılır: "−6,5 bp".
   ───────────────────────────────────────────────────────────── */

export const AYLAR_TR = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];
export const GUNLER_TR = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'];

/**
 * Yaş etiketi — TEK kural. null ya da NEGATİF (ileri valörlü tarih: yarının
 * gösterge kuru) → boş: böyle bir satıra "bugün" demek yanlış olurdu.
 */
export function yasMetni(gun: number | null | undefined): string {
  if (gun === null || gun === undefined || !Number.isFinite(gun) || gun < 0) return '';
  if (gun === 0) return 'bugün';
  if (gun === 1) return '1 gün önce';
  return `${gun} gün önce`;
}

/** Kaynağın kendi hane sayısı (en çok 4): ondalık verilmeyen yerde kullanılır. */
export function ondalikSay(v: number): number {
  const s = String(v);
  const i = s.indexOf('.');
  return i < 0 ? 0 : Math.min(4, s.length - i - 1);
}

/** Okurun bugünü, İstanbul saatiyle: "1 Eylül 2026 Salı". */
export function bugunUzun(d: Date = new Date()): string {
  return new Intl.DateTimeFormat('tr-TR', {
    day: 'numeric', month: 'long', year: 'numeric', weekday: 'long', timeZone: 'Europe/Istanbul',
  }).format(d);
}

/** 1234.5 → "1.234,5"; isaret=true ise pozitife "+" konur; eksi U+2212. */
export function sayi(v: number, ondalik = 1, isaret = false): string {
  const m = v
    .toLocaleString('tr-TR', { minimumFractionDigits: ondalik, maximumFractionDigits: ondalik })
    .replace('-', '−');
  return isaret && v > 0 ? `+${m}` : m;
}

/** Yüzde: işaret önde, % sayının önünde. yuzde(-1.884, 2) → "−%1,88". */
export function yuzde(v: number, ondalik = 1, isaret = false): string {
  const govde = sayi(Math.abs(v), ondalik);
  if (v < 0) return `−%${govde}`;
  return `${isaret && v > 0 ? '+' : ''}%${govde}`;
}

/** Birimli değişim: birim "%" ise yuzde(), değilse "sayı birim" ("−6,5 bp"). */
export function degisim(v: number, birim: string, ondalik = 2): string {
  const b = (birim || '').trim();
  if (b === '%') return yuzde(v, ondalik, true);
  return `${sayi(v, ondalik, true)}${b ? ` ${b}` : ''}`;
}

/**
 * Hatların tarih yazımı üç biçimde geliyor: "GG.AA.YYYY", "AA.YYYY" (aylık
 * seri) ve ISO ("YYYY-MM-DD", "YYYY-MM-DD HH:MM UTC", "YYYY-MM-DDTHH:MM:SS").
 * Ayrıştırılamayan biçim null döner — uydurulmuş bir tarih, çirkin bir
 * tarihten kötüdür. Aylık seri ayın SON gününe demirlenir: bir "07.2026"
 * verisi Temmuz'un tamamını anlatır, 1 Temmuz'u değil.
 */
export function tariheCevir(t: unknown): Date | null {
  if (t instanceof Date) return isNaN(t.valueOf()) ? null : t;
  if (typeof t !== 'string') return null;
  const s = t.trim();
  // Takvim günleri UTC gece yarısına demirlenir: ön bilgideki `pubDate`
  // ('2026-08-31' → 2026-08-31T00:00Z) ile aynı eksende dururlar ve derleyen
  // makinenin saat dilimi tarihi bir gün kaydıramaz.
  let m = s.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if (m) return new Date(Date.UTC(+m[3], +m[2] - 1, +m[1]));
  m = s.match(/^(\d{2})\.(\d{4})$/);
  if (m) return new Date(Date.UTC(+m[2], +m[1], 0));
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return null;
}

/** Tabloda tek biçim: ISO → "GG.AA.YYYY"; zaten GG.AA.YYYY / AA.YYYY ise dokunmaz. */
export function tarihYaz(t: string): string {
  if (!t) return '';
  if (/^\d{2}\.\d{2}\.\d{4}$/.test(t) || /^\d{2}\.\d{4}$/.test(t)) return t;
  const m = t.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[3]}.${m[2]}.${m[1]}`;
  return t;
}

/** "1 Eylül 2026" */
export function tarihUzun(d: Date | string | null | undefined): string {
  const t = tariheCevir(d);
  if (!t) return typeof d === 'string' ? d : '';
  return `${t.getUTCDate()} ${AYLAR_TR[t.getUTCMonth()]} ${t.getUTCFullYear()}`;
}

/** "01 Eyl 2026" — künye hücreleri için. */
export function tarihKisa(d: Date | string | null | undefined): string {
  const t = tariheCevir(d);
  if (!t) return typeof d === 'string' ? d : '';
  return new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(t);
}

/** "Ağustos 2026" — ay gruplama başlıkları. */
export function ayAdi(d: Date | string | null | undefined): string {
  const t = tariheCevir(d);
  return t ? `${AYLAR_TR[t.getUTCMonth()]} ${t.getUTCFullYear()}` : '';
}

/** ISO gün: "2026-08-31" (UTC). */
export function isoGun(d: Date | string | null | undefined): string {
  const t = tariheCevir(d);
  return t ? t.toISOString().slice(0, 10) : '';
}

export function gunAdi(d: Date | string): string {
  const t = tariheCevir(d);
  return t ? GUNLER_TR[(t.getUTCDay() + 6) % 7] : '';
}

/** İki tarih arası tam gün (b − a). */
/** b anının İSTANBUL takvim günü, UTC gece yarısına demirli (veri tarihleriyle aynı eksen). */
export function istanbulGunu(b: Date = new Date()): Date {
  const p = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(b);
  const [y, m, d] = p.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

/**
 * Takvim günü farkı: `a` verisi İstanbul takvimine göre bugünden kaç gün
 * geride. Saat farkını yuvarlamak ("22 saat → 1 gün", "−13 saat → 0 gün")
 * ileri valörlü yarının kurunu öğleden sonra "bugün" yapıyordu; takvim
 * günü sayılır. Negatif = ileri valör (yasMetni boş bırakır).
 */
export function gunFarki(a: Date, b: Date = new Date()): number {
  return Math.round((istanbulGunu(b).getTime() - a.getTime()) / 86400000);
}

/**
 * Bir zaman damgasını İSTANBUL saatiyle yazar.
 *
 * Ölçüm koşuları bulut koşucusunda UTC ile damgalanıyor ve bülten JSON'undaki
 * `olusturma` alanı saat dilimi TAŞIMIYOR ("2026-09-01T04:30:26"). Sayfa bu
 * saati olduğu gibi basıyordu — okur 07:30'da kurulan ölçümü "04:30" diye
 * okuyordu. Kural: dilimsiz damga UTC sayılır; Türkiye yaz saati uygulamadığı
 * için dönüşüm sabit +03:00'tır ama yine de Intl'e bırakılır.
 */
export function istanbulSaat(iso: string | null | undefined, biçim: 'saat' | 'tam' = 'saat'): string {
  if (!iso) return '';
  const s = iso.trim();
  const dilimli = /(Z|[+-]\d{2}:\d{2})$/.test(s);
  const d = new Date(dilimli ? s : `${s}Z`);
  if (isNaN(d.valueOf())) return '';
  const saat = new Intl.DateTimeFormat('tr-TR', {
    hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Europe/Istanbul',
  }).format(d);
  if (biçim === 'saat') return saat;
  const gun = new Intl.DateTimeFormat('tr-TR', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/Istanbul',
  }).format(d);
  return `${gun} ${saat}`;
}

/** Dilimsiz ISO damgayı UTC sayıp Date'e çevirir (RSS pubDate için). */
export function damgaTarihi(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const s = iso.trim();
  const dilimli = /(Z|[+-]\d{2}:\d{2})$/.test(s);
  const d = new Date(dilimli ? s : `${s}Z`);
  return isNaN(d.valueOf()) ? null : d;
}

/** HTML → düz metin: etiketleri söker, temel varlıkları çözer, boşluğu toplar. */
export function duzMetin(html: string | null | undefined): string {
  return (html || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Bağlantı önizlemesi için özet: ilk cümle(ler), en çok `en` karakter.
 * Cümle sınırında keser; sığmazsa kelime sınırında ve "…" ile.
 * Nokta tek başına cümle sınırı değildir: "12. ay" ve "48,2469" gibi
 * yazımlarda noktadan sonra büyük harf beklenir.
 */
export function ozetle(metin: string, en = 200): string {
  const m = duzMetin(metin);
  if (m.length <= en) return m;
  const cumleler = m.split(/(?<![0-9])(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ"«(])/);
  let out = '';
  for (const c of cumleler) {
    if ((out + ' ' + c).trim().length > en) break;
    out = (out + ' ' + c).trim();
  }
  if (out.length >= en * 0.5) return out;
  const kes = m.lastIndexOf(' ', en - 1);
  return m.slice(0, kes > 0 ? kes : en - 1).replace(/[\s,;:·]+$/, '') + '…';
}

/** RSS pubDate (RFC 822). */
export function rfc822(d: Date): string {
  return d.toUTCString();
}

/** XML metin kaçışı. */
export function xmlKacis(s: string): string {
  return (s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
