// Büyük harf dönüşümünden korunan metin — tek tanım.
//
// Sitenin etiket, künye ve tablo başlıkları `text-transform: uppercase` taşır ve
// sayfa `lang="tr"`dir. Tarayıcı bu ikisini birlikte uygulayınca iki kusur doğar
// ve ikisi de HTML'de görünmez (HTML'de "σ" ve "TradingView" durur, çizimde
// "Σ" ve "TRADİNGVİEW" çıkar):
//
//   1. Küçük Yunan harfi büyüğüne döner: σ (standart sapma) → Σ (toplam),
//      β → Β, τ → Τ. Nicel okur için bu başka bir büyüklüğün adıdır.
//   2. İngilizce özel ad ve kısaltma Türkçe kuralla büyür: i → İ
//      ("TRADİNGVİEW", "PİNE SCRİPT", "OİS").
//
// Koruma iki biçimde: Yunan harfi `.harf-koru` kabına girer (global.css:
// `text-transform: none`), yabancı ad `lang="en"` taşır (tarayıcı büyük harfi
// İngilizce kuralla kurar). Ödünç TERİMLER (fixing, receive, swaption) listede
// YOK ve bu bilerek: Türkçe metnin sözcüğüdürler ve Türkçe kuralla büyürler;
// kaynağın yazımını koruyan yalnız özel ad ve kısaltmadır.
//
// Liste sayfa sınavının 27. ölçütüyle (site/tools/buyuk_harf_baglam.py →
// YABANCI) aynıdır; duman sınaması ikisini kaynak metninden kıyaslar.

/** Büyük harf bağlamında kaynağın yazımını koruyan ad ve kısaltmalar (küçük harfle). */
export const YABANCI = [
  'tradingview', 'trading', 'pine', 'script', 'bitcoin', 'nikkei',
  'bachelier', 'fibonacci', 'fib', 'ict', 'ois',
];

const YUNAN = /[α-ωϑϕϵ]+/g;
const YABANCI_KALIP = new RegExp(`(?<![A-Za-z])(${[...YABANCI].sort((a, b) => b.length - a.length).join('|')})(?![A-Za-z])`, 'gi');

/**
 * Metni korunacak parçalarına böler: [{ t, tur: 'yunan' | 'yabanci' | null }].
 * Astro bileşenleri etiket basarken bunu kullanır; MDX gövdesi aşağıdaki
 * rehype eklentisinden geçer.
 */
export function harfParcala(metin) {
  const s = String(metin ?? '');
  const isaret = [];
  for (const m of s.matchAll(YUNAN)) isaret.push([m.index, m.index + m[0].length, 'yunan']);
  // Yalnız küçük 'i' taşıyan eşleşme: "OIS" dönüşümden sağ çıkar, sarılmaz.
  for (const m of s.matchAll(YABANCI_KALIP)) if (m[0].includes('i')) isaret.push([m.index, m.index + m[0].length, 'yabanci']);
  isaret.sort((a, b) => a[0] - b[0]);
  const out = [];
  let i = 0;
  for (const [b, e, tur] of isaret) {
    if (b < i) continue;
    if (b > i) out.push({ t: s.slice(i, b), tur: null });
    out.push({ t: s.slice(b, e), tur });
    i = e;
  }
  if (i < s.length) out.push({ t: s.slice(i), tur: null });
  return out;
}

/** Bir etiketin tamamı yabancı bir ad mı ("pine script", "tradingview")? */
export function yabanciMi(metin) {
  const p = harfParcala(metin).filter((x) => x.t.trim());
  return p.length > 0 && p.every((x) => x.tur === 'yabanci');
}

const ATLA = new Set(['code', 'pre', 'script', 'style', 'svg', 'math', 'kbd', 'samp']);

function sinifVar(dugum, ad) {
  const c = dugum.properties?.className;
  return Array.isArray(c) ? c.includes(ad) : typeof c === 'string' && c.split(/\s+/).includes(ad);
}

function atlanir(dugum) {
  if (dugum.type === 'element') {
    if (ATLA.has(dugum.tagName)) return true;
    if (sinifVar(dugum, 'katex') || sinifVar(dugum, 'katex-display') || sinifVar(dugum, 'harf-koru')) return true;
    if (dugum.properties?.lang) return true;
  }
  if ((dugum.type === 'mdxJsxFlowElement' || dugum.type === 'mdxJsxTextElement')) {
    const n = dugum.attributes ?? [];
    if (n.some((a) => a.name === 'lang')) return true;
    if (n.some((a) => a.name === 'class' && typeof a.value === 'string' && /\b(harf-koru|katex)\b/.test(a.value))) return true;
    // Bileşen çağrısı (büyük harfle başlayan ad) — metni bileşen basar,
    // çocuk metni prop değildir ama bileşen onu başka bir yere taşıyabilir;
    // yine de kap içinde kalır, o yüzden işlenir.
  }
  return false;
}

function sar(parca) {
  if (parca.tur === 'yunan') {
    return { type: 'element', tagName: 'span', properties: { className: ['harf-koru'] }, children: [{ type: 'text', value: parca.t }] };
  }
  if (parca.tur === 'yabanci') {
    return { type: 'element', tagName: 'span', properties: { lang: 'en' }, children: [{ type: 'text', value: parca.t }] };
  }
  return { type: 'text', value: parca.t };
}

/**
 * rehype eklentisi — rehype-katex'ten SONRA koşar. KaTeX çıktısı, kod ve ön
 * biçimli bloklar atlanır; kalan her metin düğümündeki küçük Yunan harfi
 * `.harf-koru`ya, listedeki yabancı ad `lang="en"`e sarılır. Bağlam
 * sorulmaz (hangi öğenin büyük harfle çizileceğini CSS bilir, eklenti bilmez):
 * sarmak her yerde zararsızdır, sarmamak yalnız büyük harf bağlamında kusurdur.
 */
export function rehypeHarfKoru() {
  return (agac) => {
    const gez = (dugum) => {
      if (!dugum.children || atlanir(dugum)) return;
      const yeni = [];
      for (const c of dugum.children) {
        if (c.type === 'text' && c.value) {
          const p = harfParcala(c.value);
          if (p.some((x) => x.tur)) { yeni.push(...p.map(sar)); continue; }
          yeni.push(c);
        } else {
          gez(c);
          yeni.push(c);
        }
      }
      dugum.children = yeni;
    };
    gez(agac);
  };
}
