/* ─────────────────────────────────────────────────────────────
   Ders ölçümü — kart ve rozet verileri MDX gövdesinden
   DERLEME ANINDA hesaplanır. Kelime sayısı, grafik sayısı,
   pratik bloğu / alıştırma sayısı hiçbir yerde ELLE yazılmaz;
   MDX değişince rakam kendiliğinden tazelenir.
   (Sessiz bayatlama denetimi: elle yazılan sayı bayatlar, sayılan sayı bayatlamaz.)
   ───────────────────────────────────────────────────────────── */

export interface DersOlcum {
  kelime: number; // gövdedeki gerçek sözcük sayısı (kod/formül/etiket hariç)
  dakika: number; // tahmini okuma süresi
  sure: string; // "1 sa 45 dk" biçiminde
  grafik: number; // <GrafikEmbed …> sayısı
  arac: number; // sayfaya gömülü interaktif hesap aracı sayısı
  bolum: number; // "## " başlık sayısı
  pratik: number; // <div class="pratik"> bloğu sayısı
  alistirma: number; // <details> içindeki çözümlü alıştırma sayısı
  tablo: number; // markdown tablo satırı değil, tablo sayısı
}

/** Okuma hızı: teknik Türkçe metin, formül ve tablo aralarıyla. */
const KELIME_DK = 200;

/** Gövdeden okunabilir düz metni çıkarır (kod, formül, etiket, import atılır). */
function duzMetin(govde: string): string {
  return govde
    .replace(/^import\s[^\n]*$/gm, ' ') // MDX import satırları
    .replace(/```[\s\S]*?```/g, ' ') // kod blokları
    .replace(/`[^`\n]*`/g, ' ') // satır içi kod
    .replace(/\$\$[\s\S]*?\$\$/g, ' ') // blok KaTeX
    .replace(/\$[^$\n]+\$/g, ' ') // satır içi KaTeX
    .replace(/<[^>]*>/g, ' ') // HTML/JSX etiketleri
    .replace(/\{[^{}]*\}/g, ' ') // JSX ifadeleri
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1') // bağlantı/görsel → yalnız metni
    .replace(/^[#>\-*+\s|]+/gm, ' ') // liste/başlık/tablo işaretleri
    .replace(/[*_~`|]/g, ' ');
}

/** İçinde en az bir harf ya da rakam olan belirteçleri sayar. */
function kelimeSay(metin: string): number {
  const parcalar = metin.split(/\s+/);
  let n = 0;
  for (const p of parcalar) if (/[\p{L}\p{N}]/u.test(p)) n++;
  return n;
}

function say(govde: string, kalip: RegExp): number {
  return (govde.match(kalip) || []).length;
}

/**
 * Markdown tablolarını sayar: ayraç satırı (|---|---|) = bir tablo.
 * En az İKİ tire yeter — `|:--|` biçimindeki kısa ayraçlar da sayılsın diye
 * (üç tire şartı, geçerli bir tabloyu sessizce görmezden geliyordu).
 */
function tabloSay(govde: string): number {
  return say(govde, /^\s*\|?[\s:|-]*-{2,}[\s:|-]*\|[\s:|-]*$/gm);
}

/**
 * Hesap araçları: components/ altından içeri alınan, grafik/veri yardımcıları
 * dışındaki bileşenler. Ders içine gömülü interaktif araç sayısını verir.
 */
const ARAC_DISI = new Set([
  'GrafikEmbed',
  'Deger',
  'VeriTablosu',
  'KayitKarti',
  'ZamanSozlugu',
]);

function aracSay(govde: string): number {
  const bulunan = new Set<string>();
  const kalip = /^import\s+(\w+)\s+from\s+['"][^'"]*components\/[^'"]+['"]/gm;
  let m: RegExpExecArray | null;
  while ((m = kalip.exec(govde))) {
    if (!ARAC_DISI.has(m[1])) bulunan.add(m[1]);
  }
  // İmport edilmiş ama gövdede kullanılmayan bileşen sayılmaz: bir araç metinden
  // çıkarılıp import'u unutulursa kart sessizce fazla saymasın (sessiz bayatlama).
  let n = 0;
  for (const ad of bulunan) {
    if (new RegExp(`<${ad}[\\s/>]`).test(govde)) n++;
  }
  return n;
}

export function sureYaz(dakika: number): string {
  if (dakika < 60) return `${dakika} dk`;
  const sa = Math.floor(dakika / 60);
  const dk = dakika % 60;
  return dk === 0 ? `${sa} sa` : `${sa} sa ${dk} dk`;
}

/**
 * Bölüm sayısı. Ders "## Bölüm N — …" kalıbını kullanıyorsa YALNIZ o başlıklar
 * sayılır; "## Özet tablo" / "## Sözlük" gibi ek h2'ler bölüm değildir ve künye
 * şeridini şişirirdi. Kalıbı kullanmayan derslerde eski davranış (tüm h2) sürer.
 */
function bolumSay(govde: string): number {
  const numarali = say(govde, /^## Bölüm\s+\d+/gm);
  return numarali > 0 ? numarali : say(govde, /^## /gm);
}

export function olc(govde: string | undefined): DersOlcum {
  const g = govde ?? '';
  const kelime = kelimeSay(duzMetin(g));
  const dakika = Math.max(1, Math.round(kelime / KELIME_DK));
  return {
    kelime,
    dakika,
    sure: sureYaz(dakika),
    grafik: say(g, /<GrafikEmbed\b/g),
    arac: aracSay(g),
    bolum: bolumSay(g),
    pratik: say(g, /<div class="pratik"/g),
    alistirma: say(g, /<details\b/g),
    tablo: tabloSay(g),
  };
}

/** Kelime sayısını "34 bin kelime" gibi okunur biçime çevirir. */
export function kelimeYaz(kelime: number): string {
  if (kelime < 1000) return `${kelime} kelime`;
  const bin = kelime / 1000;
  const yuvarlak = bin < 10 ? Math.round(bin * 10) / 10 : Math.round(bin);
  return `${String(yuvarlak).replace('.', ',')} bin kelime`;
}

/** Kart ve liste satırlarında kullanılan tek satırlık ölçüm özeti. */
export function olcumSatiri(o: DersOlcum, secenek: { tablo?: boolean } = {}): string[] {
  const parcalar = [`${o.sure} okuma`, `${o.bolum} bölüm`];
  if (o.grafik > 0) parcalar.push(`${o.grafik} grafik`);
  if (o.arac > 0) parcalar.push(`${o.arac} hesap aracı`);
  if (o.pratik > 0) parcalar.push(`${o.pratik} pratik · ${o.alistirma} alıştırma`);
  if (secenek.tablo && o.tablo > 0) parcalar.push(`${o.tablo} tablo`);
  return parcalar;
}
