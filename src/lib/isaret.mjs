// İşaretli yüzde satır sonunda bölünmez — tek tanım.
//
// Unicode satır kırma kuralı önek sayı işareti (eksi U+2212, artı) ile yüzde
// işareti arasında kırmayı yasaklamaz. Dar ekranda satır "−" ile biter, sonraki
// satır "%15,1" ile başlar ve alt satıra bakan okur değeri artı okur — yön
// yanlış okunur. Sayı tablolarının değer hücreleri zaten kırılmaz (global.css,
// `.sayi-tablo`); bu eklenti aynı kuralı MDX gövdesinin düzyazısına ve
// yönetici özetine taşır: işaretli her yüzde `.isaret-koru` kabına girer
// (global.css: `white-space: nowrap`). Eksi ile rakam arasında kırma zaten
// yasak ("−4,8" bölünmez), sarılan yalnız işaret + yüzde + sayı dizisidir.
// Bağlam sorulmaz: kısa bir diziyi kırılmaz yapmak her yerde zararsızdır.
//
// Kapsam: yalnız Markdown/MDX gövdesi (astro.config → rehypePlugins). Bülten
// metni bileşenlerden `set:html` ile basılır ve bu yoldan geçmez.

/** İşaretli yüzde: "−%4,8", "+%19,4", "−%1.234,5". */
export const ISARETLI_YUZDE = /[−+]%\d+(?:[.,]\d+)*/g;

const ATLA = new Set(['code', 'pre', 'script', 'style', 'svg', 'math', 'kbd', 'samp']);

function atlanir(dugum) {
  if (dugum.type !== 'element') return false;
  if (ATLA.has(dugum.tagName)) return true;
  const c = dugum.properties?.className;
  const s = Array.isArray(c) ? c : typeof c === 'string' ? c.split(/\s+/) : [];
  return s.includes('katex') || s.includes('katex-display') || s.includes('isaret-koru');
}

/** Metni düz metin ve sarılmış işaretli yüzde parçalarına böler (eşleşme yoksa null). */
export function isaretParcala(metin) {
  const s = String(metin ?? '');
  const out = [];
  let i = 0;
  for (const m of s.matchAll(ISARETLI_YUZDE)) {
    if (m.index > i) out.push({ type: 'text', value: s.slice(i, m.index) });
    out.push({ type: 'element', tagName: 'span', properties: { className: ['isaret-koru'] },
               children: [{ type: 'text', value: m[0] }] });
    i = m.index + m[0].length;
  }
  if (!out.length) return null;
  if (i < s.length) out.push({ type: 'text', value: s.slice(i) });
  return out;
}

/** rehype eklentisi — KaTeX çıktısı, kod ve ön biçimli bloklar atlanır. */
export function rehypeIsaretKoru() {
  return (agac) => {
    const gez = (dugum) => {
      if (!dugum.children || atlanir(dugum)) return;
      const yeni = [];
      for (const c of dugum.children) {
        if (c.type === 'text' && c.value) {
          const p = isaretParcala(c.value);
          if (p) { yeni.push(...p); continue; }
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
