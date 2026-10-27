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
   ───────────────────────────────────────────────────────────── */

export type Tur = 'oran' | 'seviye' | 'fark';
export type Frekans = 'gunluk' | 'haftalik' | 'aylik' | 'ceyreklik';
export type Donusum = 'duzey' | 'yillik' | 'aylik';

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
export function donusumler(tur: Tur, frekans: Frekans): { kod: Donusum; ad: string }[] {
  const liste: { kod: Donusum; ad: string }[] = [{ kod: 'duzey', ad: 'Düzey' }];
  if (tur === 'seviye') liste.push({ kod: 'yillik', ad: 'Yıllık % değişim' });
  else liste.push({ kod: 'yillik', ad: 'Yıllık fark' });
  // Çeyreklik seride "aylık" bir kıyas noktası yoktur.
  if (frekans !== 'ceyreklik') {
    liste.push({ kod: 'aylik', ad: tur === 'seviye' ? 'Aylık % değişim' : 'Aylık fark' });
  }
  return liste;
}

/** Dönüşümün birimi: seviyede yüzde değişim, oranda puan, farkla okunan seride serinin
 *  birimi (endeksin farkı puandır). */
export function donusumBirimi(tur: Tur, birim: string, d: Donusum): string {
  if (d === 'duzey') return birim;
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
export function degisimSerisi(s: Seri, tur: Tur, frekans: Frekans, ay: number): Seri {
  const ms = s.t.map(gun);
  const pay = PAY_GUN[frekans] * GUN;
  const t: string[] = [];
  const v: number[] = [];
  let j = 0;
  for (let i = 0; i < s.t.length; i++) {
    const hedef = ayGeri(s.t[i], ay);
    while (j + 1 < i && ms[j + 1] <= hedef) j++;
    if (ms[j] > hedef || hedef - ms[j] > pay) continue;
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

export function donustur(s: Seri, tur: Tur, frekans: Frekans, d: Donusum): Seri {
  if (d === 'duzey') return s;
  return degisimSerisi(s, tur, frekans, d === 'yillik' ? 12 : 1);
}

/** Son gözlemin `ay` ay önceye göre değişimi; ölçülemiyorsa null. */
export function sonDegisim(s: Seri, tur: Tur, frekans: Frekans, ay = 12): number | null {
  if (!s.t.length) return null;
  const r = degisimSerisi(s, tur, frekans, ay);
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
