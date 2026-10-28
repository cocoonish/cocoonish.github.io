/* ─────────────────────────────────────────────────────────────
   Grafikler bölümü — seri dönüşümleri ve tarih etiketi. TEK tanım.

   Derleme anı (kartın "1 yılda" değişimi, kıvılcım çizgisi) ile tarayıcı
   (seri sayfasının dönüşüm düğmeleri, ipucu, CSV) aynı fonksiyonları çağırır;
   iki ayrı kopya bir gün aynı seriye iki ayrı değişim yazardı. Bu dosya
   `node:fs` içe aktarmaz — tarayıcıya da paketlenir.

   DÖNÜŞÜMÜN BİRİMİ SERİNİN TÜRÜNDEN GELİR. Bir oranın (faiz, enflasyon,
   pay) farkı PUANDIR, yüzde değişimi değil: %43'ten %30'a inen bir oranın
   değişimi 13 puandır (CLAUDE.md — "bir FARKIN birimi SEVİYENİN birimi
   değildir"). Seviye (endeks, stok, kur) yüzde değişimle okunur; işaret
   değiştiren büyüklük (cari denge, net fonlama, swap hariç net rezerv) ile
   100 çevresinde dolaşan güven endeksi kendi biriminde FARKLA okunur:
   eksiden artıya geçen bir büyüklüğün yüzde değişimi anlamsızdır.

   KIYAS NOKTASI TAKVİMDEN SEÇİLİR, GÖZLEM SAYISINDAN DEĞİL. "Bir yıl önce"
   t − 1 yıl gününde ya da ondan önceki SON gözlemdir; o gözlem frekansın
   payından eskiyse (seri orada boşsa) değişim ölçülemez ve boş kalır.
   Gözlem sayısıyla geri gitmek (günlük seride 252) tatil ve kesinti
   günlerinde başka bir güne düşerdi.

   100'E ENDEKSLEME YALNIZ SEVİYEDE ve dönemin kendisine bağlıdır: taban,
   görünen dönemde BÜTÜN serilerin ölçüldüğü ilk gündür ve her seri o gün
   (ya da ondan sonraki ilk gözlemi) 100 olacak biçimde ölçeklenir. Farklı
   birimdeki seviyeler (BIST puan, Brent dolar/varil) ancak böyle tek eksende
   kıyaslanır — iki eksen kullanılmaz. Oranın ve işaret değiştiren büyüklüğün
   endeksi anlamsızdır (%2'den %4'e çıkan faiz "200" olmaz); düğme yalnız
   seviyede çıkar.

   HEDEF YILI OCAKTA DEĞİŞEN SERİ (`hedef_yil`: anketin "cari yıl sonu" ya da
   "gelecek yıl sonu" sorusu) iki ayrı yılın beklentisini art arda dizer: Aralık
   2025'te %38,21 olan "yıl sonu politika faizi" 2025 sonunun, Ocak 2026'daki %28,02
   2026 sonunun beklentisidir. Aradaki 10 puan bir beklenti değişimi değildir.
   Böyle seride değişim yalnız AYNI takvim yılının iki gözlemi arasında kurulur
   (yıllık fark hiç kurulamaz, düğmesi çıkmaz; Ocak'ın aylık farkı ölçülmez) ve
   çizgi her yıl başında kesilir (lib/grafikCizim).
   ───────────────────────────────────────────────────────────── */

export type Tur = 'oran' | 'seviye' | 'fark';
export type Frekans = 'gunluk' | 'haftalik' | 'aylik' | 'ceyreklik';
export type Donusum = 'duzey' | 'yillik' | 'aylik' | 'endeks';

export interface Seri {
  /** ISO gün ("2026-10-26"); aylık seri ayın ilk günü, çeyreklik çeyreğin son günü. */
  t: string[];
  v: number[];
}

/** Kıyas noktasının en çok ne kadar eski olabileceği (gün). */
const PAY_GUN: Record<Frekans, number> = { gunluk: 10, haftalik: 12, aylik: 20, ceyreklik: 50 };

const GUN = 86_400_000;

function gun(t: string): number {
  return Date.UTC(+t.slice(0, 4), +t.slice(5, 7) - 1, +t.slice(8, 10));
}

/** t'den `ay` ay geri giden takvim günü (ayın son gününe sıkıştırılır). */
function ayGeri(t: string, ay: number): number {
  const y = +t.slice(0, 4);
  const m = +t.slice(5, 7) - 1 - ay;
  const d = +t.slice(8, 10);
  const son = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
  return Date.UTC(y, m, Math.min(d, son));
}

/** Hangi dönüşümler bu türde anlamlı, okura nasıl adlandırılır. */
export function donusumler(tur: Tur, frekans: Frekans, hedefYil = false): { kod: Donusum; ad: string }[] {
  const liste: { kod: Donusum; ad: string }[] = [{ kod: 'duzey', ad: 'Düzey' }];
  if (hedefYil) {
    // Bir yıl önceki gözlem başka bir yılın beklentisidir: yıllık kıyas yok.
  } else if (tur === 'seviye') liste.push({ kod: 'yillik', ad: 'Yıllık % değişim' });
  else liste.push({ kod: 'yillik', ad: 'Yıllık fark' });
  // Çeyreklik seride "aylık" bir kıyas noktası yoktur.
  if (frekans !== 'ceyreklik') {
    liste.push({ kod: 'aylik', ad: tur === 'seviye' ? 'Aylık % değişim' : 'Aylık fark' });
  }
  if (tur === 'seviye') liste.push({ kod: 'endeks', ad: "100'e endeksli" });
  return liste;
}

/** Dönüşümün birimi: seviyede yüzde değişim, oranda puan, farkla okunan seride serinin
 *  birimi (endeksin farkı puandır). */
export function donusumBirimi(tur: Tur, birim: string, d: Donusum): string {
  if (d === 'duzey') return birim;
  if (d === 'endeks') return '';
  if (tur === 'seviye') return '%';
  if (tur === 'oran' || birim === 'endeks') return 'puan';
  return birim;
}

/** Değişimin hanesi: yüzde değişim tek hane (kurun dört haneli seviyesi "+%18,6424"
 *  basmasın), fark serinin hanesi ama en çok iki. */
export function degisimOndalik(tur: Tur, ondalik: number): number {
  return tur === 'seviye' ? 1 : Math.min(ondalik, 2);
}

/** Her gözlem için `ay` ay önceki kıyas noktasına göre değişim; ölçülemeyen gözlem düşer. */
export function degisimSerisi(s: Seri, tur: Tur, frekans: Frekans, ay: number, hedefYil = false): Seri {
  const ms = s.t.map(gun);
  const pay = PAY_GUN[frekans] * GUN;
  const t: string[] = [];
  const v: number[] = [];
  let j = 0;
  for (let i = 0; i < s.t.length; i++) {
    const hedef = ayGeri(s.t[i], ay);
    while (j + 1 < i && ms[j + 1] <= hedef) j++;
    if (ms[j] > hedef || hedef - ms[j] > pay) continue;
    if (hedefYil && s.t[j].slice(0, 4) !== s.t[i].slice(0, 4)) continue;
    const once = s.v[j];
    const simdi = s.v[i];
    let d: number;
    if (tur === 'seviye') {
      if (!(once > 0)) continue;           // sıfır ya da eksi tabana yüzde kurulmaz
      d = (simdi / once - 1) * 100;
    } else {
      d = simdi - once;
    }
    t.push(s.t[i]);
    v.push(d);
  }
  return { t, v };
}

export function donustur(s: Seri, tur: Tur, frekans: Frekans, d: Donusum, hedefYil = false): Seri {
  // Endeks dönemin tabanına bağlıdır; seriler kesildikten SONRA `endeksle` ile kurulur.
  if (d === 'duzey' || d === 'endeks') return s;
  return degisimSerisi(s, tur, frekans, d === 'yillik' ? 12 : 1, hedefYil);
}

/** Son gözlemin `ay` ay önceye göre değişimi; ölçülemiyorsa null. */
export function sonDegisim(s: Seri, tur: Tur, frekans: Frekans, ay = 12, hedefYil = false): number | null {
  if (!s.t.length) return null;
  const r = degisimSerisi(s, tur, frekans, ay, hedefYil);
  return r.t.length && r.t[r.t.length - 1] === s.t[s.t.length - 1] ? r.v[r.v.length - 1] : null;
}

/** Serinin [bas, son] gün aralığındaki parçası. */
export function kes(s: Seri, basGun: string | null): Seri {
  if (!basGun) return s;
  let i = 0;
  while (i < s.t.length && s.t[i] < basGun) i++;
  return { t: s.t.slice(i), v: s.v.slice(i) };
}

/** Son gözlemden `yil` yıl (kesirli olabilir) geriye giden başlangıç günü. */
export function donemBasi(s: Seri, ay: number | null): string | null {
  if (ay === null || !s.t.length) return null;
  return new Date(ayGeri(s.t[s.t.length - 1], ay)).toISOString().slice(0, 10);
}

/** Frekansa göre okur etiketi: gün "26.10.2026", ay "09.2026", çeyrek "2026Ç2". */
export function tarihEtiketi(t: string, frekans: Frekans): string {
  const y = t.slice(0, 4);
  const m = t.slice(5, 7);
  if (frekans === 'aylik') return `${m}.${y}`;
  if (frekans === 'ceyreklik') return `${y}Ç${Math.ceil(+m / 3)}`;
  return `${t.slice(8, 10)}.${m}.${y}`;
}

/** Eşit aralıklı seyreltme: kıvılcım çizgisi için en çok `n` nokta, son nokta korunur. */
export function seyrelt(s: Seri, n: number): Seri {
  if (s.t.length <= n) return s;
  const adim = (s.t.length - 1) / (n - 1);
  const t: string[] = [];
  const v: number[] = [];
  for (let k = 0; k < n; k++) {
    const i = Math.round(k * adim);
    t.push(s.t[i]);
    v.push(s.v[i]);
  }
  return { t, v };
}

/** Serileri ortak bir tabanda 100'e endeksler: taban, bütün dolu serilerin ölçüldüğü
 *  ilk gündür (ilk gözlemlerin en geç olanı). Taban günü ya da sonrasında pozitif bir
 *  gözlemi olmayan seri boş döner — sıfır ya da eksi tabana endeks kurulmaz. */
export function endeksle(seriler: Seri[]): { seriler: Seri[]; taban: string | null } {
  const dolu = seriler.filter((s) => s.t.length);
  if (!dolu.length) return { seriler: seriler.map(() => ({ t: [], v: [] })), taban: null };
  const taban = dolu.reduce((m, s) => (s.t[0] > m ? s.t[0] : m), dolu[0].t[0]);
  return {
    taban,
    seriler: seriler.map((s) => {
      let i = 0;
      while (i < s.t.length && s.t[i] < taban) i++;
      const b = s.v[i];
      if (!(b > 0)) return { t: [], v: [] };
      return { t: s.t.slice(i), v: s.v.slice(i).map((x) => (x / b) * 100) };
    }),
  };
}
