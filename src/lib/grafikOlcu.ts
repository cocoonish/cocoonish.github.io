/* ─────────────────────────────────────────────────────────────
   Gömülü grafiğin KENDİ ilan ettiği yüksekliği derleme anında okur.

   Neden gerekiyor: GrafikEmbed sabit yükseklikli bir iframe kuruyordu
   (öntanımlı 540px) ve Python tarafı figüre kendi yüksekliğini yazıyor.
   İki sayı birbirinden habersiz olunca grafik alttan KIRPILIYOR — sayfada
   "yarım çıkmış" bir şekil kalıyor ve bunu kimse ölçmüyor. 26.08'de on bir
   gömme böyleydi (en kötüsü 200 piksel kırpılmış).

   KURAL: MDX'te `yukseklik` verilirse bir ALT SINIRDIR; figürün ilan ettiği
   yükseklik onu aşarsa figürünki geçer. Verilmezse figürün ilanı, o da yoksa
   öntanımlı. Önceki kural "MDX KAZANIR"dı ve aynı kusuru başka yoldan geri
   getirdi (25.09.2026): hatlar figür yüksekliğini alt yazının satır
   sayısından hesaplıyor, satır sayısı veriye bağlı, MDX ise o sayının elle
   yazılmış İKİNCİ bir kopyası — iki kopya veri değiştikçe ayrışıyor. 483
   gömmenin ikisi canlı sitede kırpılıyordu (FX haber endeksi Şekil 10 · 430
   piksel, YP mevduat Şekil 05 · 26 piksel) ve fonlama figürleri bir satır
   kısaldığında yayın kapısı düşüp siteyi donduruyordu. Artık figür yüksekliğini
   ilan ettiği sürece kırpılma yapısal olarak imkânsızdır; figür küçülürse
   aradaki fark yalnız boşluktur. Python eşi: ortak/figur_olcu.py (yayın
   kapısı ve hat koşusu aynı soruyu oradan sorar — biri değişirse öbürü de).

   Ayrıştırma figürün DÜZENİNDEN (Plotly.newPlot'un üçüncü argümanı) yapılır:
   dosyadaki ilk "height" bir tablo izinin hücre yüksekliği olabilir (bütçe
   Şekil 09'da ilk eşleşme 24 piksel, düzeninki 1227).
   ───────────────────────────────────────────────────────────── */
import fs from 'node:fs';
import path from 'node:path';

const PUBLIC = path.join(path.resolve(process.cwd()), 'public');
const ONTANIMLI = 540;
/** Aşırı uçlara karşı emniyet: bozuk bir figür sayfayı ele geçirmesin.
 *  Sitedeki en uzun meşru figür 2.300 piksel (REDK 10 yıllık analiz). */
const EN_AZ = 260;
const EN_COK = 2600;

const onbellek = new Map<string, number | null>();

/** t[k]'dan (boşluk atlanarak) başlayan JSON değerinin bittiği konum; -1 bozuk. */
function degerSonu(t: string, k: number): number {
  const n = t.length;
  while (k < n && ' \t\r\n'.includes(t[k])) k++;
  if (k >= n) return -1;
  const c = t[k];
  if (c === '"') {
    k++;
    while (k < n) {
      if (t[k] === '\\') { k += 2; continue; }
      if (t[k] === '"') return k + 1;
      k++;
    }
    return -1;
  }
  if (c === '[' || c === '{') {
    let derin = 0;
    while (k < n) {
      const ch = t[k];
      if (ch === '"') {
        k++;
        while (k < n && t[k] !== '"') k += t[k] === '\\' ? 2 : 1;
      } else if (ch === '[' || ch === '{') {
        derin++;
      } else if (ch === ']' || ch === '}') {
        derin--;
        if (derin === 0) return k + 1;
      }
      k++;
    }
    return -1;
  }
  while (k < n && !',)]}'.includes(t[k])) k++;
  return k;
}

/** Plotly.newPlot("kimlik", [veri], {düzen}, {ayar}) çağrısının düzen nesnesi. */
function duzen(t: string): Record<string, unknown> | null {
  const i = t.indexOf('Plotly.newPlot(');
  if (i < 0) return null;
  let k = i + 'Plotly.newPlot('.length;
  for (let a = 0; a < 2; a++) {            // kimlik, veri
    k = degerSonu(t, k);
    if (k < 0) return null;
    while (k < t.length && ' \t\r\n'.includes(t[k])) k++;
    if (t[k] !== ',') return null;
    k++;
  }
  while (k < t.length && ' \t\r\n'.includes(t[k])) k++;
  const son = degerSonu(t, k);
  if (son < 0 || t[k] !== '{') return null;
  try {
    const d = JSON.parse(t.slice(k, son));
    return d && typeof d === 'object' ? d : null;
  } catch {
    return null;
  }
}

/** Figürün düzeninde ilan edilen yükseklik (px). Yoksa null. */
export function ilanEdilenYukseklik(src: string): number | null {
  if (onbellek.has(src)) return onbellek.get(src)!;
  let sonuc: number | null = null;
  try {
    const t = fs.readFileSync(path.join(PUBLIC, src.replace(/^\//, '')), 'utf-8');
    let h: unknown = null;
    if (t.includes('Plotly.newPlot(')) {
      h = duzen(t)?.height ?? null;
    } else {
      // Plotly dışı bir gömme: tek ipucu düz metindeki ilk yükseklik.
      const m = t.match(/"height"\s*:\s*(\d{2,4})\b/);
      h = m ? Number(m[1]) : null;
    }
    if (typeof h === 'number' && h >= EN_AZ && h <= EN_COK) sonuc = Math.trunc(h);
  } catch {
    /* dosya yoksa öntanımlıya düşülür — sayfa yine kurulur */
  }
  onbellek.set(src, sonuc);
  return sonuc;
}

/** iframe yüksekliği: elle yazılan ALT SINIR, figürün ilanı onu aşarsa ilan. */
export function cerceveYuksekligi(src: string, acik?: number): number {
  const ilan = ilanEdilenYukseklik(src);
  if (acik != null && ilan != null) return Math.max(acik, ilan);
  return acik ?? ilan ?? ONTANIMLI;
}
