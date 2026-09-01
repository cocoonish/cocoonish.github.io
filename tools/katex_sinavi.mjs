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
 * İKİNCİ ÖLÇÜT — DELİMİTER DÜZENİ (01.09.2026'da ölçüldü). Yukarıdaki ölçüt
 * doğruydu, koşuyordu, 4063 formülde yeşil bitiyordu — ve sayfada üç formül
 * bloğu ile ARDINDAKİ 108 <Deger> etiketi ham metin olarak yayımlandı. Sebep
 * KaTeX değil MDX'ti: bir `$$…$$` bloğu iki satıra yayıldığında remark-math
 * delimiter'ları yanlış eşliyor, açılan span belgenin sonuna kadar uzuyor ve
 * o bölge komple metne dönüyor. Bu betiğin regex'i `[\s\S]` ile satır
 * atladığı için formülü DOĞRU çıkarıyor, KaTeX de onu sorunsuz ayrıştırıyordu;
 * yani sınav, MDX'in formülü BULABİLDİĞİNİ hiç sormuyordu.
 *
 * Ölçütün kapsamı ölçütün parçasıdır: artık `$$` delimiter'larının aynı
 * satırda olup olmadığı da sınanıyor. Kural, MDX'in kabul ettiği iki düzeni
 * bırakır — ya `$$…$$` tek satırda, ya da `$$` kendi satırında (üç satırlık
 * blok) — ve arada kalan her şeyi düşürür.
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

/** `$$` delimiter düzeni: MDX'in güvenle ayrıştırdığı iki biçim dışını yakala.
 *  Kabul: (a) `$$…$$` aynı satırda, (b) `$$` tek başına kendi satırında.
 *  Ret:   `$$` ile başlayıp satır sonunda kapanmayan blok. */
function delimiterDuzeni(metin, kayma) {
  const kotu = [];
  const satirlar = metin.split('\n');
  satirlar.forEach((s, i) => {
    const n = (s.match(/\$\$/g) || []).length;
    if (n % 2 === 1 && s.trim() !== '$$') {
      kotu.push({ satir: kayma + i + 1, metin: s.trim().slice(0, 90) });
    }
  });
  return kotu;
}

/** ÜÇÜNCÜ ÖLÇÜT — FORMÜLÜN İÇİNDE JSX OLMAZ.
 *  `$$…<Deger …>…$$` yazmak her hâlükârda yanlıştır: math bloğunun içi METİN
 *  olarak işlenir, bileşen ÇÖZÜLMEZ ve okur ham etiketi görür. Bugün bu kusur
 *  yalnız TESADÜFEN yakalandı — `itp_b_sapma` içindeki alt çizgiler KaTeX'e
 *  "double subscript" dedirtti. Alt çizgisiz bir anahtar olsaydı formül
 *  sorunsuz ayrıştırılır, sayfada çöp basılır ve sınav yeşil biterdi.
 *  Bir kusuru tesadüfen yakalayan ölçüt, o kusuru ölçmüyor demektir. */
function jsxIcinde(formuller_) {
  // KALIP DAR TUTULUR. İlk sürüm `/<\s*[A-Z]\w*[\s/>]/` idi ve matematikteki
  // `0 < DF < 1` ifadesini JSX sandı. Yanlış alarm veren bir kapı, kapatılan
  // kapıdır. Aranan şey bir BİLEŞEN KULLANIMIDIR: `<` hemen ardından büyük
  // harfle başlayan ad (boşluk YOK) ve en az bir öznitelik. Depodaki her
  // gerçek kullanım (<Deger proje="…" …>) bu kalıba uyuyor; `a < B` uymuyor.
  return formuller_.filter((f) =>
    /<[A-Z][A-Za-z0-9]*\s+[a-zA-Z-]+\s*=/.test(f.ic));
}

const hedefler = process.argv.slice(2);
const dosyalar = (hedefler.length ? hedefler : [VARSAYILAN]).flatMap(mdxDosyalari);
let toplam = 0;
const bulgular = [];
const duzenBulgu = [];
const jsxBulgu = [];

for (const d of dosyalar) {
  const ham = readFileSync(d, 'utf8');
  const { govde: g, kayma } = govde(ham);
  for (const k of delimiterDuzeni(g, kayma)) {
    duzenBulgu.push({ dosya: relative(KOK, d), ...k });
  }
  const fs_ = formuller(g);
  for (const f of jsxIcinde(fs_)) {
    const satir = kayma + g.slice(0, f.indis).split('\n').length;
    jsxBulgu.push({
      dosya: relative(KOK, d), satir,
      formul: f.ic.trim().replace(/\s+/g, ' ').slice(0, 90),
    });
  }
  for (const f of fs_) {
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
if (!bulgular.length && !duzenBulgu.length && !jsxBulgu.length) {
  console.log('  ✓ hepsi ayrıştırıldı · $$ delimiter düzeni temiz · formül içinde JSX yok');
  process.exit(0);
}
for (const b of bulgular) {
  console.log(`  ✗ ${b.dosya}:${b.satir} (${b.tur})\n      ${b.formul}\n      → ${b.hata}`);
}
for (const b of duzenBulgu) {
  console.log(`  ✗ ${b.dosya}:${b.satir} (delimiter düzeni)\n      ${b.metin}\n` +
    `      → \`$$\` bu satırda açılıp kapanmıyor. MDX bunu yanlış eşliyor ve\n` +
    `        AÇILAN span belgenin sonuna kadar uzayarak o bölgeyi ham metne\n` +
    `        çeviriyor. Bloğu TEK SATIRA indirin ya da \`$$\` işaretlerini\n` +
    `        kendi satırlarına alın.`);
}
for (const b of jsxBulgu) {
  console.log(`  ✗ ${b.dosya}:${b.satir} (formül içinde JSX)\n      ${b.formul}\n` +
    `      → Math bloğunun içi METİN olarak işlenir; bileşen çözülmez ve okur\n` +
    `        ham etiketi görür. Formülü SEMBOLİK yazın, canlı sayıyı hemen\n` +
    `        altındaki düz metne alın.`);
}
const n = bulgular.length + duzenBulgu.length + jsxBulgu.length;
console.log(`\nKATEX SINAVI DÜŞTÜ (${bulgular.length} formül ayrıştırılamadı, ` +
  `${duzenBulgu.length} delimiter düzeni bozuk, ${jsxBulgu.length} formülde JSX).`);
process.exit(1);
