/* ─────────────────────────────────────────────────────────────
   Gömülü grafiğin KENDİ ilan ettiği yüksekliği derleme anında okur.

   Neden gerekiyor: GrafikEmbed sabit yükseklikli bir iframe kuruyordu
   (öntanımlı 540px) ve Python tarafı figüre kendi yüksekliğini yazıyor.
   İki sayı birbirinden habersiz olunca grafik alttan KIRPILIYOR — sayfada
   "yarım çıkmış" bir şekil kalıyor ve bunu kimse ölçmüyor. 26.08'de on bir
   gömme böyleydi (en kötüsü 200 piksel kırpılmış).

   Doğrusu yüksekliği tek bir yerden okumak: figürün kendisinden. MDX'te
   `yukseklik` verilirse o KAZANIR (yazarın bilinçli tercihi), verilmezse
   figürün ilan ettiği yükseklik, o da yoksa öntanımlı.
   ───────────────────────────────────────────────────────────── */
import fs from 'node:fs';
import path from 'node:path';

const PUBLIC = path.join(path.resolve(process.cwd()), 'public');
const ONTANIMLI = 540;
/** Aşırı uçlara karşı emniyet: bozuk bir figür sayfayı ele geçirmesin. */
const EN_AZ = 260;
const EN_COK = 1600;

const onbellek = new Map<string, number | null>();

/** Figürün layout'unda ilan edilen yükseklik (px). Yoksa null. */
export function ilanEdilenYukseklik(src: string): number | null {
  if (onbellek.has(src)) return onbellek.get(src)!;
  let sonuc: number | null = null;
  try {
    const t = fs.readFileSync(path.join(PUBLIC, src.replace(/^\//, '')), 'utf-8');
    // Plotly figürü layout'u JSON olarak gömer: ..."height":700,...
    const m = t.match(/"height"\s*:\s*(\d{2,4})\b/);
    if (m) {
      const h = Number(m[1]);
      if (h >= EN_AZ && h <= EN_COK) sonuc = h;
    }
  } catch {
    /* dosya yoksa öntanımlıya düşülür — sayfa yine kurulur */
  }
  onbellek.set(src, sonuc);
  return sonuc;
}

/** iframe yüksekliği: açık tercih → figürün ilanı → öntanımlı. */
export function cerceveYuksekligi(src: string, acik?: number): number {
  return acik ?? ilanEdilenYukseklik(src) ?? ONTANIMLI;
}
