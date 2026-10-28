/* ─────────────────────────────────────────────────────────────
   Grafikler bölümü — serileri DERLEME ANINDA kurar.

   İki kaynak var ve ikisi de katalogdan okunur (src/data/grafikler/katalog.json):

   · FİGÜR. Projelerin ölçtüğü seriler, panoların yayımlanmış Plotly
     dosyalarından (`public/projeler/<proje>/<dosya>`) izin ADIYLA okunur.
     Seri yeniden hesaplanmaz: okurun panoda gördüğü sayı burada da aynıdır
     ve hesabı panonun "bu seri nasıl hesaplanıyor" bölümündedir. Pano
     tazelendiği gün bu sayfa da tazelenir — ikinci bir hat yoktur.
     Aynı adlı birden çok iz varsa (aynı figürde kısa ve uzun pencere) EN UZUN
     olanı alınır.

   · DIŞ ve HAT. Hiçbir panonun çekmediği EVDS serileri, piyasa serileri
     (USD/TRY, BIST 100) ve panonun figürü yalnız son yıllarını çizen serilerin
     hattın veri dosyasındaki uzun tarihçesi `Aktarılacak Projeler/Grafikler/cek.py`
     ile `src/data/grafikler/dis/<id>.json` olarak commit edilir.

   ÇÖZÜLEMEYEN SERİ DERLEMEYİ DÜŞÜRMEZ. İz adı değişirse ya da dosya yoksa
   seri `sorun` taşır: kart "şu an gösterilemiyor" der, seri sayfası
   üretilmez ve sayfa sınavı (30) adını UYARI olarak listeler. Bir figür
   izinin adı yüzünden bütün sitenin yayını durmamalı; ama sessizce de
   kaybolmamalı.
   ───────────────────────────────────────────────────────────── */
import fs from 'node:fs';
import path from 'node:path';
import { degerSonu } from './grafikOlcu';
import {
  degisimSerisi, donusumBirimi, sonDegisim, type Frekans, type Seri, type Tur,
} from './grafikDonusum';
import katalog from '../data/grafikler/katalog.json';

const KOK = path.resolve(process.cwd());
const PUBLIC = path.join(KOK, 'public');
const DIS = path.join(KOK, 'src', 'data', 'grafikler', 'dis');

export interface Baslik { kod: string; ad: string; aciklama: string }

export interface FigurKaynak {
  tur: 'figur'; proje: string; dosya: string; iz: string;
  /** Aynı adlı iz birden çok panelde varsa hangisi (Plotly `xaxis`: "x", "x2"…). */
  eksen?: string;
}
export interface DisKaynak { tur: 'evds' | 'yahoo'; kod: string; ad?: string }
/** Hattın depodaki veri dosyasındaki bir sütun: panonun figürü serinin yalnız son yıllarını
 *  çiziyorsa uzun tarihçe buradan gelir (cek.py taşır; derleme o dosyayı göremez). */
export interface HatKaynak {
  tur: 'hat'; proje: string; dosya: string; sutun: string; carpan?: number;
  /** Pay: sütun / payda × çarpan (ör. altının brüt rezervdeki payı); iki sütun hattın aynı satırından. */
  payda?: string;
}
/** Katalogdaki BAŞKA bir seriden türetilen seri (ör. USD/TRY'nin gerçekleşen oynaklığı):
 *  taban serinin dosyası okunur, ikinci bir çekim yapılmaz. Taban kendisi türetilmiş olamaz. */
export interface SeriKaynak { tur: 'seri'; seri: string }

export interface SeriTanim {
  id: string;
  ad: string;
  baslik: string;
  birim: string;
  tur: Tur;
  frekans: Frekans;
  ondalik: number;
  kurum: string;
  kaynak: FigurKaynak | DisKaynak | HatKaynak | SeriKaynak;
  /** Ham seriden türetme: endeksin yıllık ya da aylık % değişimi; günlük kapanıştan
   *  `pencere` iş günlük yıllıklandırılmış gerçekleşen oynaklık; ya da `pencere` iş günlük
   *  ACT/365 yıllıklandırılmış devalüasyon hızı (USD/TRY panosunun tanımı). */
  turet?: 'yillik_yuzde' | 'aylik_yuzde' | 'oynaklik' | 'deval';
  pencere?: number;
  /** Yalnız `deval`: son `ortalama` iş gününde biten pencerelerin ortalaması (panonun
   *  "son hafta ortalaması" — tek günlük kotasyon sıçramasını söndürür). */
  ortalama?: number;
  /** Türetmeden ÖNCE: art arda `toplam` gözlemin toplamı (ör. haftalık harcamanın dört
   *  haftalık, aylık gelirin on iki aylık toplamı). Aradaki boşluk frekansın payını aşarsa
   *  o toplam kurulmaz — eksik bir hafta toplamı küçültüp sahte bir düşüş çizerdi. */
  toplam?: number;
  /** Anketin "cari yıl sonu" / "gelecek yıl sonu" sorusu: hedef yıl her Ocak değişir;
   *  değişim yalnız aynı takvim yılı içinde kurulur, çizgi yıl başında kesilir
   *  (lib/grafikDonusum). */
  hedef_yil?: boolean;
  aciklama: string;
}

export interface KurulmusSeri extends SeriTanim {
  seri: Seri;
  /** Döviz kapanışının saatlik bardan kurulmaya başladığı gün (öncesi düzeltilmiş günlük
   *  bar, Londra gece yarısı); bilinmiyorsa ya da döviz değilse null. */
  gecis: string | null;
  /** Piyasa kodu (Yahoo); türetilmiş seride tabanınki. Kapanış anını (lira kuru
   *  İstanbul, öbürleri New York) ve bülten bağını bu belirler. */
  piyasaKodu: string | null;
  sorun: string | null;
  /** Panosu varsa adresi (figür kaynağı) — "hesabı orada" bağı. */
  pano: string | null;
  sonDeger: number | null;
  sonTarih: string | null;
  yillikDegisim: number | null;
  yillikBirim: string;
}

/** Hazır grafik: aynı birim ve türde birkaç seri tek grafikte (en çok beş — paletin boyu). */
export interface SetTanim { id: string; ad: string; baslik: string; seriler: string[]; aciklama: string }
export interface KurulmusSet extends SetTanim {
  /** Çözülen üyeler, katalogdaki sırasıyla (renk sıradan gelir, sıralamadan değil). */
  uyeler: KurulmusSeri[];
  /** Çözülemeyen üyeler adıyla; iki üye kalmazsa set gösterilmez. */
  eksik: string[];
  sorun: string | null;
  birim: string;
  tur: Tur;
  frekans: Frekans;
  ondalik: number;
}

export const BASLIKLAR = katalog.basliklar as Baslik[];
export const TANIMLAR = katalog.seriler as SeriTanim[];
export const SET_TANIMLAR = ((katalog as { setler?: SetTanim[] }).setler ?? []) as SetTanim[];
export const SET_AZAMI = 5;

// ── Plotly figürünün VERİ argümanı ────────────────────────────

type HamIz = { name?: string; x?: unknown; y?: unknown; xaxis?: string };

/** Plotly'nin ikili dizisi ({dtype, bdata}) ya da düz dizi → sayı dizisi. */
function dizi(v: unknown): unknown[] | null {
  if (Array.isArray(v)) return v;
  if (v && typeof v === 'object' && 'bdata' in v) {
    const { dtype, bdata } = v as { dtype?: string; bdata: string };
    const b = Buffer.from(bdata, 'base64');
    const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
    const tip: Record<string, [number, (o: number) => number]> = {
      f8: [8, (o) => dv.getFloat64(o, true)], f4: [4, (o) => dv.getFloat32(o, true)],
      i4: [4, (o) => dv.getInt32(o, true)], i2: [2, (o) => dv.getInt16(o, true)],
      i1: [1, (o) => dv.getInt8(o)], u1: [1, (o) => dv.getUint8(o)],
      u2: [2, (o) => dv.getUint16(o, true)], u4: [4, (o) => dv.getUint32(o, true)],
    };
    const k = tip[dtype ?? 'f8'];
    if (!k) return null;
    const out: number[] = [];
    for (let o = 0; o + k[0] <= b.byteLength; o += k[0]) out.push(k[1](o));
    return out;
  }
  return null;
}

const figurOnbellek = new Map<string, HamIz[] | null>();

function figurIzleri(yol: string): HamIz[] | null {
  if (figurOnbellek.has(yol)) return figurOnbellek.get(yol)!;
  let sonuc: HamIz[] | null = null;
  try {
    const t = fs.readFileSync(yol, 'utf-8');
    const i = t.indexOf('Plotly.newPlot(');
    if (i >= 0) {
      let k = degerSonu(t, i + 'Plotly.newPlot('.length);      // kimlik
      while (k > 0 && k < t.length && t[k] !== ',') k++;
      const bas = k + 1;
      const son = degerSonu(t, bas);
      if (son > 0) {
        const d = JSON.parse(t.slice(bas, son));
        if (Array.isArray(d)) sonuc = d as HamIz[];
      }
    }
  } catch {
    sonuc = null;
  }
  figurOnbellek.set(yol, sonuc);
  return sonuc;
}

/** "2026-10-26", "2026-09-01 00:00:00", "1950-01" → ISO gün; tanınmayan → null. */
function isoGunu(x: unknown): string | null {
  if (typeof x !== 'string') return null;
  const m = x.match(/^(\d{4})-(\d{2})(?:-(\d{2}))?/);
  if (!m) return null;
  return `${m[1]}-${m[2]}-${m[3] ?? '01'}`;
}

function figurSerisi(k: FigurKaynak): { seri: Seri | null; sorun: string | null } {
  const izler = figurIzleri(path.join(PUBLIC, 'projeler', k.proje, k.dosya));
  if (!izler) return { seri: null, sorun: `figür okunamadı: ${k.proje}/${k.dosya}` };
  let en: Seri | null = null;
  for (const iz of izler) {
    if (iz.name !== k.iz) continue;
    if (k.eksen && (iz.xaxis ?? 'x') !== k.eksen) continue;
    const xs = dizi(iz.x);
    const ys = dizi(iz.y);
    if (!xs || !ys) continue;
    const t: string[] = [];
    const v: number[] = [];
    for (let i = 0; i < Math.min(xs.length, ys.length); i++) {
      const g = isoGunu(xs[i]);
      const y = ys[i];
      if (!g || typeof y !== 'number' || !Number.isFinite(y)) continue;
      t.push(g);
      v.push(y);
    }
    if (!en || t.length > en.t.length) en = { t, v };
  }
  if (!en || en.t.length < 2) return { seri: null, sorun: `iz bulunamadı: ${k.proje}/${k.dosya} › ${k.iz}` };
  return { seri: sirala(en), sorun: null };
}

/** Tarihe göre sıralı, aynı gün tekrarı son değerle (figürde kesik izler olabilir). */
function sirala(s: Seri): Seri {
  const m = new Map<string, number>();
  s.t.forEach((t, i) => m.set(t, s.v[i]));
  const t = [...m.keys()].sort();
  return { t, v: t.map((g) => m.get(g)!) };
}

function disSerisi(id: string): { seri: Seri | null; sorun: string | null; gecis?: string | null } {
  try {
    const d = JSON.parse(fs.readFileSync(path.join(DIS, `${id}.json`), 'utf-8')) as Seri & { gecis?: string };
    if (!Array.isArray(d.t) || !Array.isArray(d.v) || d.t.length < 2) {
      return { seri: null, sorun: `dış seri boş: ${id}` };
    }
    return { seri: sirala({ t: d.t, v: d.v }), sorun: null, gecis: typeof d.gecis === 'string' ? d.gecis : null };
  } catch {
    return { seri: null, sorun: `dış seri henüz çekilmedi: ${id}` };
  }
}

/** Endeksin yıllık yüzde değişimi: ay ve çeyrekte bir yıl önceki AYNI dönemle, gün ve
 *  haftada takvimde bir yıl önceki son gözlemle (grafikDonusum'un kuralı). */
function yillikYuzde(s: Seri, frekans: Frekans): Seri {
  if (frekans === 'gunluk' || frekans === 'haftalik') return degisimSerisi(s, 'seviye', frekans, 12);
  const m = new Map(s.t.map((t, i) => [t.slice(0, 7), s.v[i]]));
  const t: string[] = [];
  const v: number[] = [];
  s.t.forEach((g, i) => {
    const once = m.get(`${+g.slice(0, 4) - 1}${g.slice(4, 7)}`);
    if (once && once > 0) {
      t.push(g);
      v.push((s.v[i] / once - 1) * 100);
    }
  });
  return { t, v };
}

/** Endeksin aylık yüzde değişimi: bir önceki AY (gözlem değil; ay boşsa ölçülmez). */
function aylikYuzde(s: Seri): Seri {
  const m = new Map(s.t.map((t, i) => [t.slice(0, 7), s.v[i]]));
  const t: string[] = [];
  const v: number[] = [];
  s.t.forEach((g, i) => {
    const y = +g.slice(0, 4);
    const a = +g.slice(5, 7);
    const once = m.get(a === 1 ? `${y - 1}-12` : `${y}-${String(a - 1).padStart(2, '0')}`);
    if (once && once > 0) {
      t.push(g);
      v.push((s.v[i] / once - 1) * 100);
    }
  });
  return { t, v };
}

/** GERÇEKLEŞEN OYNAKLIK: son `n` gözlemin günlük log getirilerinin örneklem standart
 *  sapması × √252, yüzde. Getiri ardışık İKİ GÖZLEM arasındadır (tatil ve hafta sonu
 *  tek getiri sayılır — kapanıştan kapanışa fiyatta hafta sonu seansı yoktur, CLAUDE.md
 *  "üç takvim günü" ölçümü). İki gözlem arasında 10 takvim gününden uzun boşluk varsa
 *  o getiri ölçülemez ve onu içeren pencere boş kalır: veri kesintisi oynaklık sayılmaz. */
function oynaklik(s: Seri, n: number): Seri {
  const GUN = 864e5;
  const ms = (t: string) => Date.UTC(+t.slice(0, 4), +t.slice(5, 7) - 1, +t.slice(8, 10));
  const r: (number | null)[] = s.v.map((x, i) => {
    if (i === 0) return null;
    const a = s.v[i - 1];
    if (!(a > 0) || !(x > 0) || ms(s.t[i]) - ms(s.t[i - 1]) > 10 * GUN) return null;
    return Math.log(x / a);
  });
  const t: string[] = [];
  const v: number[] = [];
  for (let i = n; i < s.v.length; i++) {
    const p = r.slice(i - n + 1, i + 1);
    if (p.some((x) => x === null)) continue;
    const q = p as number[];
    const ort = q.reduce((a, b) => a + b, 0) / n;
    const var_ = q.reduce((a, b) => a + (b - ort) ** 2, 0) / (n - 1);
    t.push(s.t[i]);
    v.push(Math.sqrt(var_ * 252) * 100);
  }
  return { t, v };
}

const GUN_MS = 864e5;
const gunMs = (t: string) => Date.UTC(+t.slice(0, 4), +t.slice(5, 7) - 1, +t.slice(8, 10));
const msGun = (ms: number) => new Date(ms).toISOString().slice(0, 10);

/** DEVALÜASYON HIZI — USD/TRY panosunun tanımı (Aktarılacak Projeler/USDTRYDeval,
 *  `deval_act365` ve `ozet_uret.deval`): kapanışlar takvim gününe zaman ağırlıklı
 *  doğrusal ara değerle yayılır, yalnız hafta içi günler kalır (tatil bir ara değer
 *  taşır — ham gözlem üzerinden n adım gitmek resmî tatilde pencereyi kaydırırdı), ve
 *      hız(t) = (P_t / P_{t−n})^(365 / Δd) − 1      (Δd: iki günün takvim farkı)
 *  `ortalama` verilirse son `ortalama` hafta içi günde biten pencerelerin ortalaması.
 *  Sonuç yalnız GERÇEK gözlem günlerinde yazılır: ara değerli tatil günü bir gözlem değildir. */
function deval(s: Seri, n: number, ort = 1): Seri {
  if (s.t.length < 2) return { t: [], v: [] };
  const ms = s.t.map(gunMs);
  const gt: number[] = [];
  const gv: number[] = [];
  let j = 0;
  for (let d = ms[0]; d <= ms[ms.length - 1]; d += GUN_MS) {
    while (j < ms.length - 1 && ms[j + 1] < d) j++;
    const hg = new Date(d).getUTCDay();
    if (hg === 0 || hg === 6) continue;
    let v: number;
    if (d === ms[j]) v = s.v[j];
    else if (j < ms.length - 1 && d === ms[j + 1]) v = s.v[j + 1];
    else v = s.v[j] + (s.v[j + 1] - s.v[j]) * ((d - ms[j]) / (ms[j + 1] - ms[j]));
    gt.push(d);
    gv.push(v);
  }
  const hiz: (number | null)[] = gv.map((p1, i) => {
    if (i < n || !(gv[i - n] > 0) || !(p1 > 0)) return null;
    const gun = (gt[i] - gt[i - n]) / GUN_MS;
    return ((p1 / gv[i - n]) ** (365 / gun) - 1) * 100;
  });
  const gercek = new Set(ms);
  const t: string[] = [];
  const v: number[] = [];
  for (let i = 0; i < gt.length; i++) {
    if (!gercek.has(gt[i])) continue;
    const p = hiz.slice(Math.max(0, i - ort + 1), i + 1);
    if (p.length < ort || p.some((x) => x === null)) continue;
    t.push(msGun(gt[i]));
    v.push((p as number[]).reduce((a, b) => a + b, 0) / ort);
  }
  return { t, v };
}

/** Art arda `n` gözlemin toplamı; ardışık iki gözlem arasındaki boşluk frekansın
 *  payını aşan pencere kurulmaz. */
const TOPLAM_BOSLUK_GUN: Record<Frekans, number> = { gunluk: 10, haftalik: 10, aylik: 35, ceyreklik: 100 };
function toplamSerisi(s: Seri, n: number, frekans: Frekans): Seri {
  const ms = s.t.map(gunMs);
  const t: string[] = [];
  const v: number[] = [];
  for (let i = n - 1; i < s.t.length; i++) {
    let tamam = true;
    for (let k = i - n + 2; k <= i; k++) if (ms[k] - ms[k - 1] > TOPLAM_BOSLUK_GUN[frekans] * GUN_MS) tamam = false;
    if (!tamam) continue;
    t.push(s.t[i]);
    v.push(s.v.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0));
  }
  return { t, v };
}

// ── Katalog ───────────────────────────────────────────────────

let kurulmus: KurulmusSeri[] | null = null;

export function seriler(): KurulmusSeri[] {
  if (kurulmus) return kurulmus;
  const ham = (d: SeriTanim): { seri: Seri | null; sorun: string | null; gecis?: string | null } => {
    if (d.kaynak.tur === 'figur') return figurSerisi(d.kaynak);
    if (d.kaynak.tur === 'seri') {
      const tabanId = d.kaynak.seri;
      const taban = TANIMLAR.find((x) => x.id === tabanId);
      if (!taban || taban.kaynak.tur === 'seri') return { seri: null, sorun: `taban seri tanımsız: ${tabanId}` };
      return ham(taban);
    }
    return disSerisi(d.id);
  };
  const piyasaKodu = (d: SeriTanim): string | null => {
    if (d.kaynak.tur === 'yahoo') return d.kaynak.kod;
    if (d.kaynak.tur === 'seri') {
      const tabanId = d.kaynak.seri;
      const t = TANIMLAR.find((x) => x.id === tabanId);
      return t && t.kaynak.tur === 'yahoo' ? t.kaynak.kod : null;
    }
    return null;
  };
  kurulmus = TANIMLAR.map((d) => {
    const r = ham(d);
    let seri = r.seri ?? { t: [], v: [] };
    const taban = r.seri && d.toplam ? toplamSerisi(r.seri, d.toplam, d.frekans) : r.seri;
    if (taban) seri = taban;
    if (taban && d.turet === 'yillik_yuzde') seri = yillikYuzde(taban, d.frekans);
    if (taban && d.turet === 'aylik_yuzde') seri = aylikYuzde(taban);
    if (taban && d.turet === 'oynaklik') seri = oynaklik(taban, d.pencere ?? 20);
    if (taban && d.turet === 'deval') seri = deval(taban, d.pencere ?? 21, d.ortalama ?? 1);
    const n = seri.t.length;
    return {
      ...d,
      seri,
      gecis: r.gecis ?? null,
      piyasaKodu: piyasaKodu(d),
      sorun: r.sorun ?? (n < 2 ? `türetilen seri boş: ${d.id}` : null),
      pano: d.kaynak.tur === 'figur' || d.kaynak.tur === 'hat' ? `/projeler/${d.kaynak.proje}/` : null,
      sonDeger: n ? seri.v[n - 1] : null,
      sonTarih: n ? seri.t[n - 1] : null,
      yillikDegisim: n ? sonDegisim(seri, d.tur, d.frekans, 12, !!d.hedef_yil) : null,
      yillikBirim: donusumBirimi(d.tur, d.birim, 'yillik'),
    };
  });
  return kurulmus;
}

export function seriBul(id: string): KurulmusSeri | undefined {
  return seriler().find((s) => s.id === id);
}

/** Piyasa sembolünün (Yahoo kodu, bültenin enstrüman tablosundaki `kod`) Grafikler
 *  sayfası; seri katalogda yoksa ya da şu an gösterilemiyorsa null — bağ kurulmaz. */
let kodHaritasi: Map<string, string> | null = null;
export function koddanGrafik(kod: string | null | undefined): string | null {
  if (!kod) return null;
  if (!kodHaritasi) {
    kodHaritasi = new Map();
    for (const x of seriler()) {
      if (!x.sorun && x.kaynak.tur === 'yahoo' && !kodHaritasi.has(x.kaynak.kod)) kodHaritasi.set(x.kaynak.kod, `/grafikler/${x.id}/`);
    }
  }
  return kodHaritasi.get(kod) ?? null;
}

let kurulmusSet: KurulmusSet[] | null = null;

/** Hazır grafikler. Üyeler aynı birim ve türde olmalı (tek eksen); katalogdaki bir
 *  uyumsuzluk sayfa sınavında ENGEL'dir, burada yalnız seti gösterilemez kılar. */
export function setler(): KurulmusSet[] {
  if (kurulmusSet) return kurulmusSet;
  const harita = new Map(seriler().map((s) => [s.id, s]));
  kurulmusSet = SET_TANIMLAR.map((h) => {
    const tanimli = h.seriler.map((id) => harita.get(id)).filter((x): x is KurulmusSeri => !!x);
    const uyeler = tanimli.filter((x) => !x.sorun);
    const eksik = h.seriler.filter((id) => !uyeler.some((u) => u.id === id));
    const ilk = tanimli[0];
    let sorun: string | null = null;
    if (!ilk) sorun = `${h.id}: üye yok`;
    else if (tanimli.some((x) => x.birim !== ilk.birim || x.tur !== ilk.tur)) sorun = `${h.id}: üyelerin birimi ya da türü farklı`;
    else if (h.seriler.length > SET_AZAMI) sorun = `${h.id}: ${SET_AZAMI} seriden fazla`;
    else if (uyeler.length < 2) sorun = `${h.id}: gösterilebilen üye ikiden az`;
    return {
      ...h, uyeler, eksik, sorun,
      // Karma frekansta tarih etiketi ve dönüşüm listesi EN SIK üyeden: günlük bir üyenin
      // tarihi ay etiketiyle yazılmasın.
      birim: ilk?.birim ?? '', tur: ilk?.tur ?? 'oran',
      frekans: (['gunluk', 'haftalik', 'aylik', 'ceyreklik'] as Frekans[]).find((f) => tanimli.some((x) => x.frekans === f)) ?? 'aylik',
      ondalik: Math.max(...tanimli.map((x) => x.ondalik), 0),
    };
  });
  return kurulmusSet;
}

/** Hazır grafikte üye adlarının ORTAK öneki ("Politika faizi — ") ve ortak parantez soneki
 *  ("(mevsimsellikten arındırılmış)") başlığın zaten söylediği şeydir; kartta ve lejantta
 *  yalnız ayırt eden kısım yazılır. Kırpma bir adı boşaltacaksa yapılmaz. */
export function kisaAdlar(adlar: string[]): string[] {
  if (adlar.length < 2) return adlar;
  let out = adlar;
  const onek = /^(.+? (?:—|·) )/.exec(out[0])?.[1];
  if (onek && out.every((a) => a.startsWith(onek) && a.length > onek.length)) out = out.map((a) => a.slice(onek.length));
  const sonek = / \([^()]+\)$/.exec(out[0])?.[0];
  if (sonek && out.every((a) => a.endsWith(sonek) && a.length > sonek.length)) out = out.map((a) => a.slice(0, -sonek.length));
  return out.map((a) => a.charAt(0).toLocaleUpperCase('tr-TR') + a.slice(1));
}
