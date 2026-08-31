#!/usr/bin/env node
/**
 * KaTeX SINAVI — MDX içindeki her formülü DERLEMEDEN ÖNCE ayrıştır.
 *
 * Neden gerekli: rehype-katex bir formülü ayrıştıramadığında derlemeyi
 * DÜŞÜRMEZ; hatayı sayfaya kırmızı ham LaTeX olarak basar ve `npm run build`
 * yeşil biter. 31.08.2026'da tam bu oldu: `\textbf{%3,3}` yazıldı, LaTeX'te
 * `%` YORUM karakteri olduğu için süslü parantez yutuldu, KaTeX
 * "Unexpected end of input" verdi ve dört formül sayfada ham metin olarak
 * yayımlandı. Kusuru derleme değil OKUR gördü.
 *
 * Bu betik aynı soruyu derlemeden önce sorar: her `$...$` ve `$$...$$` bloğunu
 * KaTeX'in kendi ayrıştırıcısına verir, düşen olursa dosya+satır ile bildirir
 * ve ÇIKIŞ KODU 1 döner.
 *
 * Kullanım:  node site/tools/katex_sinavi.mjs [dosya|dizin ...]
 * Argümansız: site/src/content altındaki bütün .mdx dosyaları.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import katex from 'katex';

const KOK = new URL('../..', import.meta.url).pathname;
const VARSAYILAN = join(KOK, 'site/src/content');

function mdxDosyalari(yol) {
  const st = statSync(yol);
  if (st.isFile()) return yol.endsWith('.mdx') ? [yol] : [];
  return readdirSync(yol).flatMap((a) => mdxDosyalari(join(yol, a)));
}

/** Frontmatter'ı at: orada geçen $ işaretleri formül değildir. */
function govde(metin) {
  const m = metin.match(/^---\n[\s\S]*?\n---\n/);
  if (!m) return { govde: metin, kayma: 0 };
  return { govde: metin.slice(m[0].length), kayma: m[0].split('\n').length - 1 };
}

/** Blok ($$…$$) ve satır içi ($…$) formülleri sırayla çıkar. */
function formuller(metin) {
  const bulunan = [];
  const blok = /\$\$([\s\S]+?)\$\$/g;
  let m;
  const maskeli = metin.replace(blok, (t, ic, i) => {
    bulunan.push({ tur: 'blok', ic, indis: i });
    return ' '.repeat(t.length);
  });
  const satir = /(?<![\\$])\$(?!\$)([^\n$]+?)(?<!\\)\$/g;
  while ((m = satir.exec(maskeli)) !== null) {
    bulunan.push({ tur: 'satır içi', ic: m[1], indis: m.index });
  }
  return bulunan;
}

const hedefler = process.argv.slice(2);
const dosyalar = (hedefler.length ? hedefler : [VARSAYILAN]).flatMap(mdxDosyalari);
let toplam = 0;
const bulgular = [];

for (const d of dosyalar) {
  const ham = readFileSync(d, 'utf8');
  const { govde: g, kayma } = govde(ham);
  for (const f of formuller(g)) {
    toplam++;
    try {
      katex.renderToString(f.ic, { throwOnError: true, displayMode: f.tur === 'blok' });
    } catch (e) {
      const satir = kayma + g.slice(0, f.indis).split('\n').length;
      bulgular.push({
        dosya: relative(KOK, d), satir, tur: f.tur,
        formul: f.ic.trim().replace(/\s+/g, ' ').slice(0, 90),
        hata: String(e.message).replace(/^KaTeX parse error:\s*/, '').slice(0, 110),
      });
    }
  }
}

console.log(`KaTeX sınavı — ${dosyalar.length} dosya · ${toplam} formül`);
if (!bulgular.length) {
  console.log('  ✓ hepsi ayrıştırıldı');
  process.exit(0);
}
for (const b of bulgular) {
  console.log(`  ✗ ${b.dosya}:${b.satir} (${b.tur})\n      ${b.formul}\n      → ${b.hata}`);
}
console.log(`\nKATEX SINAVI DÜŞTÜ (${bulgular.length} formül ayrıştırılamadı).`);
process.exit(1);
