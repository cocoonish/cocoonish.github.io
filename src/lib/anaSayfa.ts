/* ─────────────────────────────────────────────────────────────
   Ana sayfanın ölçülen katmanı.

   Ana sayfa bir DİZİN değil, bir MANŞET. Siteye ilk gelen üç soruya
   beş saniyede cevap arar: bu ne, güncel mi, ciddi mi? Rejim panosu
   üçünü birden cevaplar; bir içindekiler listesi hiçbirini cevaplamaz.

   Buradaki her şey ÖLÇÜLEN katmandan gelir — yazı katmanından tek
   cümle alınmaz. Sebebi dayanıklılık: yazı katmanı bir sabah koşmasa
   da (ya da hafta sonu) ana sayfanın manşeti doğru kalır. Yazılmış bir
   tez, yazıldığı günün tezidir; ölçülmüş bir rejim, dosyanın tarihine
   aittir ve o tarih zaten yanında yazar.

   Veri iki yerden okunur, ikisi de derleme anında:
     site/src/data/bulten/<tarih>.json   → rejim, σ sıralaması, künye
     site/public/projeler/<slug>/ozet.json → hatların kendi saatleri
   ───────────────────────────────────────────────────────────── */
import fs from 'node:fs';
import path from 'node:path';
import { sayi, yuzde, olcuYaz, tariheCevir, tarihYaz, gunFarki } from './bicim';
export { sayi, tarihYaz };

const KOK = path.resolve(process.cwd());
const BULTEN_DIZIN = path.join(KOK, 'src', 'data', 'bulten');
const PROJE_DIZIN = path.join(KOK, 'public', 'projeler');

export interface RejimSatiri {
  ad: string;
  deger: number | null;
  birim: string;
  hesap: string;
  etiket: string;
  aciklama: string;
  konum: string;
  /**
   * Bir önceki ölçümdeki değer (aynı ad). Pano yalnız seviye gösterdiği için
   * günün asıl bulgusu olan bir rejim hareketi (risk primi 8,98 → 9,21) ancak
   * düzyazıdan öğreniliyordu. Önceki dosya yoksa ya da satır orada yoksa
   * tanımsız — fark uydurulmaz.
   */
  onceki?: number | null;
  /** Bir önceki ölçümdeki etiket (aynı ad); yoksa tanımsız. */
  etiketOnceki?: string;
}

export interface SigmaSatiri {
  ad: string;
  deger: number;
  birim: string;
  sigma: number;
  oynaklik: number;
}

export interface HatSatiri {
  slug: string;
  baslik: string;
  href: string;
  durum: 'aktif' | 'taslak' | 'arsiv';
  /** Bu hattın MANŞET büyüklüğü — biçimlenmiş sayı, ör. "48,03" */
  deger: string | null;
  /** Sayı ve birim birlikte, biçim sözleşmesiyle: "%30,19", "82,6 endeks". */
  metin: string | null;
  olcu: string;
  birim: string;
  /** Büyüklüğün KENDİ saati (hattın ana saati değil) */
  tarih: string;
  /**
   * Veri tarihinin bugüne uzaklığı, gün. Bilinmiyorsa null.
   * NEGATİF OLABİLİR: piyasa serileri (yfinance) bir sonraki işlem gününün
   * barını verebiliyor ve o gün İstanbul'da henüz başlamamış olur. Böyle bir
   * satıra "bugün" demek yanlış olurdu; yaş etiketi hiç gösterilmez, tarih
   * kendi başına konuşur.
   */
  yas: number | null;
}

export interface AnaSayfaVerisi {
  var: boolean;
  tarih: string;
  trTarih: string;
  gun: string;
  olusturma: string;
  bultenHref: string;
  /** Bağın gittiği yazılmış sayı bugünün ölçümüne mi ait? */
  bultenYazili: boolean;
  bultenHaftalik: boolean;
  bultenTrTarih: string;
  enstruman: number;
  hatSayisi: number;
  rejim: RejimSatiri[];
  sigma: SigmaSatiri[];
  /**
   * σ listesinin kıyas penceresi: 'gunluk' | 'haftalik'. Ana sayfa başlığı ve
   * oynaklık etiketi buna bakar. Sabit "günlük" yazan eski sürüm, pazar
   * haftaya bakış bülteni yayımlandığında ana sayfada haftalık oynaklıkları
   * "20g oynaklık" diye etiketliyordu (30.08.2026).
   */
  sigmaKip: string;
  manset: { metin: string; parcalar: RejimSatiri[] } | null;
  /**
   * "BUGÜN NE VAR" — okurun sabah üç sorusunun üçüncüsü ana sayfada hiç
   * cevaplanmıyordu, oysa takvim bülten verisinde hazır duruyordu. Ölçüm
   * gününün bütün kayıtları (saat sırasıyla) ve sıradaki birinci derece
   * veriler. Liste ölçüm katmanının takviminden gelir, yazıdan değil.
   */
  takvimGunu: TakvimKaydi[];
  siradaki: TakvimKaydi[];
}

export interface TakvimKaydi {
  olay: string;
  saat: string;
  ulke: string;
  trTarih: string;
  gun: string;
  onem: number;
  kalanGun: number | null;
}

// Sayı ve tarih biçimi lib/bicim.ts'te — burada yalnız yeniden dışa aktarılır.

/**
 * OLAĞANDIŞILIK EŞİĞİ — tek tanım (YAZIM.md'nin 2σ kuralıyla aynı). Bülten
 * tablosunun vurgusu, σ şeridinin eşik çizgisi ve başlık kararı buradan okur.
 * Sıralama eşiksizdir; eşiği aşan hareket yoksa başlık "olağandışı" demez.
 */
export const OLAGANDISI_SIGMA = 2;

/** Hareket listesinin başlığı: eşiği aşan varsa "olağandışı", yoksa "en büyük". */
export function sigmaBasligi(sigmalar: number[], haftalik: boolean): string {
  const asan = sigmalar.some((z) => Math.abs(z) >= OLAGANDISI_SIGMA);
  if (asan) return haftalik ? 'Haftanın olağandışı hareketleri' : 'Günün olağandışı hareketleri';
  return haftalik ? 'Haftanın oynaklığa göre en büyük hareketleri' : 'Oynaklığa göre günün en büyük hareketleri';
}

function oku<T>(yol: string): T | null {
  try {
    return JSON.parse(fs.readFileSync(yol, 'utf-8')) as T;
  } catch {
    return null;
  }
}


// ── Manşet ──────────────────────────────────────────────────
//
// Manşet cümlesi rejim panosunun İKİ satırından kurulur ve tek bir soru
// sorar: politika duruşu ile piyasanın o duruşa verdiği cevap aynı yönde
// mi? Bu, Türkiye makrosunun bugünkü merkezî gerilimi ve tek cümlede
// söylenebilir.
//
// Satırların hangi tarafta durduğu ELLE ilan edilir. Ölçüt "iyi/kötü"
// değil — o bir yargı olurdu: **bu satır 'politika sıkı ve işliyor'
// okumasını destekliyor mu, yoksa altını mı oyuyor?** Eşikler zaten
// bulten/rejim.py içinde açıkça yazılı; burada yalnız yönleri var.
const ETIKET_YON: Record<string, 1 | -1> = {
  sıkı: 1,
  gevşek: -1,
  pozitif: 1,
  negatif: -1,
  'taşıma kârlı': 1,
  'taşıma zararlı': -1,
  'reel daralma': 1,
  'reel genişleme': -1,
  'reel ucuz': 1,
  'reel değerli': -1,
  'normal eğim': 1,
  'ters eğri': -1,
  'güven yerinde': 1,
  'güven zayıf': -1,
  'çerçeve tutuyor': 1,
  'kaçak geniş': -1,
};

/** Manşette kullanılacak kısa adlar — panodaki tam ad cümleye sığmıyor. */
const KISA_AD: Record<string, string> = {
  'Reel politika faizi (ileriye dönük)': 'reel faiz',
  'Reel politika faizi (geriye dönük)': 'geriye dönük reel faiz',
  'TL taşıma makası': 'taşıma makası',
  'Reel kredi büyümesi': 'reel kredi',
  'Reel efektif kur': 'reel efektif kur',
  'DİBS eğri eğimi (2y−9y)': 'eğri eğimi',
  'Enflasyon risk primi (2y)': 'enflasyon risk primi',
  'Makroihtiyati ayrışma': 'makroihtiyati ayrışma',
  'Rezerv kalitesi': 'rezerv kalitesi',
};

/**
 * Karşı taraf aranırken bakılacak sıra. Başta duruşun en doğrudan
 * karşılığı olan iki satır var: piyasa politikanın SONUCUNA inanıyor mu
 * (risk primi), ve sıkılık toplamda mı yoksa yalnız düzenlenen kalemlerde
 * mi (ayrışma). Sonrakiler daha dolaylı.
 */
const KARSI_SIRA = [
  'Enflasyon risk primi (2y)',
  'Makroihtiyati ayrışma',
  'DİBS eğri eğimi (2y−9y)',
  'TL taşıma makası',
  'Reel kredi büyümesi',
  'Reel efektif kur',
];

/** Rejim satırının ekrandaki hanesi — pano, manşet ve fark aynı haneyi kullanır. */
export function rejimHane(s: Pick<RejimSatiri, 'ad' | 'birim'>): number {
  return s.birim === 'puan' && s.ad.includes('eğim') ? 2 : 1;
}

/**
 * Önceki ölçüme göre fark — EKRANDAKİ iki değerin farkı; ölçülemiyorsa null.
 * Yuvarlama sayi()nin kuralıyla aynı olmalı: Math.round yarımı +∞'a
 * yuvarlıyor (−4,85 → −4,8), ekran ise sıfırdan uzağa ("−4,9"), ve eksi
 * satırlarda fark ekranda görünen hareketle çelişebiliyordu ("−20,0 → −20,0
 * puan"). Fark bu yüzden ekranın KENDİ biçimleyicisinden (sayi) geçen iki
 * değerden okunur — toFixed ile Intl aynı kural DEĞİLDİR (aşağıda).
 */
export function rejimFark(s: RejimSatiri): number | null {
  if (s.deger === null || typeof s.onceki !== 'number') return null;
  const n = rejimHane(s);
  // Fark EKRANDA basılan iki değerden okunur: toFixed ikili tam değeri
  // yuvarlar (8,95 → "8,9"), Intl en kısa ondalık gösterimi (8,95 → "9,0");
  // 200 bin rastgele değerde 766'sı ayrıştı ve manşet "+9,2 → +9,0" yazarken
  // şerit "−0,3 puan" basıyordu (01.10.2026 incelemesi).
  const ekran = (v: number) => Number(sayi(v, n).replace(/\./g, '').replace(',', '.').replace('−', '-'));
  const f = Number((ekran(s.deger) - ekran(s.onceki)).toFixed(n));
  return f === 0 ? 0 : f;
}

/** Farkın birimi: bir oranın ve bir endeksin farkı PUANDIR. */
export const REJIM_FARK_BIRIMI: Record<string, string> = { '%': 'puan', puan: 'puan', endeks: 'puan' };

/** Değer + birim: "+13,3 puan", "%29,5", "104,6 endeks". */
function birimYaz(s: RejimSatiri): string {
  if (s.deger === null) return '';
  const n = rejimHane(s);
  if (s.birim === '%') return yuzde(s.deger, n);
  if (s.birim === 'puan') return `${sayi(s.deger, n, true)} puan`;
  return `${sayi(s.deger, n)} ${s.birim}`;
}

/**
 * MANŞET HAREKETİ TAŞIR. Cümle iki satırın SEVİYESİNDEN kuruluyordu; iki satır
 * iki hafta boyunca aynı etiketi taşıyınca manşet kelimesi kelimesine donmuştu
 * ve geri dönen okur siteyi güncellenmemiş sanıyordu. Karşı satır önceki
 * ölçümden bu yana hareket ettiyse cümle hareketi yazar ("+9,0 → +9,2 puan");
 * ok gösterimi Türkçe ekin sayıya göre değişmesi sorununu da taşımaz.
 */
function hareketliYaz(s: RejimSatiri): string {
  const f = rejimFark(s);
  if (f === null || f === 0 || typeof s.onceki !== 'number') return birimYaz(s);
  const n = rejimHane(s);
  const eski = s.birim === '%' ? yuzde(s.onceki, n) : sayi(s.onceki, n, s.birim === 'puan');
  return `${eski} → ${birimYaz(s)}`;
}


function mansetKur(rejim: RejimSatiri[]): AnaSayfaVerisi['manset'] {
  const bul = (ad: string) => rejim.find((r) => r.ad === ad && r.deger !== null && r.etiket);
  const durus = bul('Reel politika faizi (ileriye dönük)') ?? bul('Reel politika faizi (geriye dönük)');
  if (!durus) return null;
  const durusYon = ETIKET_YON[durus.etiket];

  // ÖNCE DEĞİŞEN. Etiketi bir önceki ölçüme göre değişen satır günün asıl
  // haberidir ve manşete o çıkar; duruş satırı cümlenin ikinci yarısına iner.
  // Değişen yoksa aşağıdaki gerilim cümlesi kurulur (karşı satır hareket
  // ettiyse hareketiyle).
  const donen = [durus, ...KARSI_SIRA.map(bul)].find(
    (r) => r && r.etiketOnceki && r.etiketOnceki !== r.etiket,
  );
  if (donen) {
    const ad = KISA_AD[donen.ad] ?? donen.ad;
    const bas = `${ad[0].toUpperCase()}${ad.slice(1)} ${hareketliYaz(donen)} (${donen.etiketOnceki} → ${donen.etiket})`;
    const metin = donen === durus
      ? `${bas}.`
      : `${bas}; ${KISA_AD[durus.ad] ?? durus.ad} ${birimYaz(durus)} (${durus.etiket}).`;
    return { metin, parcalar: donen === durus ? [durus] : [donen, durus] };
  }

  // Önce duruşla ÇELİŞEN ilk satır aranır: manşetin değeri gerilimde.
  let karsi = KARSI_SIRA.map(bul).find(
    (r) => r && ETIKET_YON[r.etiket] !== undefined && ETIKET_YON[r.etiket] !== durusYon,
  );
  const celisiyor = Boolean(karsi);
  // Çelişen yoksa aynı yöndeki ilk satırla "ve" kurulur — gerilim yok,
  // bunu da açıkça söylemek bir bulgudur.
  if (!karsi) karsi = KARSI_SIRA.map(bul).find((r) => r && r.ad !== durus.ad);
  if (!karsi) return null;

  // Etiket PARANTEZ içinde durur, cümlenin içine karışmaz. Sebebi
  // dilbilgisel: etiketler tek biçimde değil — kimi sıfat ("sıkı",
  // "ters eğri"), kimi tam cümle ("güven zayıf", "kaçak geniş"). Cümlenin
  // gövdesine yerleştirilince ikinci grup bozuluyor ("8,3 puanla güven
  // zayıf"). Parantez ikisini de bozmadan taşır.
  const a = `${KISA_AD[durus.ad] ?? durus.ad} ${birimYaz(durus)} (${durus.etiket})`;
  const b = `${KISA_AD[karsi.ad] ?? karsi.ad} ${hareketliYaz(karsi)} (${karsi.etiket})`;
  const metin = celisiyor
    ? `${a[0].toUpperCase()}${a.slice(1)}, ama ${b}.`
    : `${a[0].toUpperCase()}${a.slice(1)}, ${b}.`;
  return { metin, parcalar: [durus, karsi] };
}

// ── Hat manşetleri ──────────────────────────────────────────
//
// Her hattın tabloda görünen TEK büyüklüğü. Anahtar seçimi keyfî değil:
// hattın kendi sayfasının "güncel okuma" bölümünde ilk sırada duran
// büyüklük alındı. Tarih alanı boş bırakılırsa anahtar başına saat
// geleneği işler: <anahtar>_tarih → _tarih.
const HAT_MANSET: Record<
  string,
  { anahtar: string; olcu: string; birim: string; ondalik: number; isaret?: boolean; tarihAlani?: string }
> = {
  'usdtry-deval': { anahtar: 'kur', olcu: 'USD/TRY', birim: '', ondalik: 2 },
  'tcmb-net-rezerv': { anahtar: 'g_net', olcu: 'Net rezerv (günlük tahmin)', birim: 'mlr USD', ondalik: 1, tarihAlani: 'g_tarih' },
  'fonlama-likidite': { anahtar: 'politika', olcu: 'Politika faizi', birim: '%', ondalik: 2 },
  'dibs-verim-egrisi': { anahtar: 'spot_2y', olcu: '2 yıllık spot getiri', birim: '%', ondalik: 2 },
  enflasyon: { anahtar: 'tufe_12a', olcu: 'TÜFE (yıllık)', birim: '%', ondalik: 2 },
  'kredi-parasal': { anahtar: 'g_ar_13y', olcu: 'Kredi büyümesi (13h yıl., kur arınd.)', birim: '%', ondalik: 1 },
  'try-reer': { anahtar: 'redk', olcu: 'Reel efektif kur', birim: 'endeks', ondalik: 1 },
  'hazine-ihrac': { anahtar: 'maliyet_son', olcu: 'Son ihale maliyeti', birim: '%', ondalik: 2 },
  'yabanci-pozisyon': { anahtar: 'toplam_4h', olcu: 'Yabancı 4 haftalık net akım', birim: 'mn USD', ondalik: 0, isaret: true },
  // Aylık akım milyon dolarla yazılır: milyar ve tek hanede 36 mn $'lık bir
  // fazla "0,0 mlr $" görünüyor, okur veriyi eksik sanıyordu.
  'odemeler-dengesi': { anahtar: 'cari_ay_mn', olcu: 'Aylık cari denge', birim: 'mn USD', ondalik: 0, isaret: true },
  // Oran birimi '%' ve GSYH ölçü adında: '% GSYH' birimi yüzdeyi sayının
  // ARKASINA düşürüyordu ("−2,41 % GSYH"); yüzde önde yazılır ("−%2,41").
  'butce-borc': { anahtar: 'denge_gsyh', olcu: 'Bütçe dengesi / GSYH', birim: '%', ondalik: 2, isaret: true },
  makroihtiyati: { anahtar: 'ayrisma', olcu: 'Makroihtiyati ayrışma', birim: 'puan', ondalik: 1, isaret: true },
  'tl-tasima': { anahtar: 'endeks', olcu: 'TL taşıma endeksi', birim: '', ondalik: 1 },
  'tufex-basabas': { anahtar: 'basabas_2y', olcu: '2 yıllık başabaş enflasyon', birim: '%', ondalik: 2 },
  'reel-sektor-fx': { anahtar: 'net_pozisyon', olcu: 'Net döviz pozisyonu', birim: 'mlr USD', ondalik: 1, isaret: true },
  // Sayfanın kendisi üç haneyle yazıyor; iki hane +0,0033'ü "+0,00" gösteriyordu.
  // Birim yazımı bülten şeridiyle aynı: "mlr USD", "mn USD" ("mlr $" değil).
  'fx-haber-endeksi': { anahtar: 'spread', olcu: 'Haber tonu: güvenli liman − risk sepeti', birim: '', ondalik: 3, isaret: true },
  'yiyecek-hizmetleri-marj': { anahtar: 'oran_ev_yemekleri', olcu: 'Ev yemekleri / gıda oranı', birim: '×', ondalik: 2 },
  // Manşet, hattın SORUSUNUN öznesidir: yurt içi yerleşiklerin yabancı para
  // mevduatı. Kaynağın GENİŞ toplamı (271,1 mlr $) yurt dışı yerleşik bankaları
  // da içerir ve bu hattın konusu değildir; onu ana sayfa tablosuna basmak,
  // kapsam karışıklığını sitenin en görünür yerine taşırdı. Akım manşeti de
  // seçilmedi: haftadan haftaya işaret değiştiren tek haftalık bir sayı, tablo
  // satırında bağlamsız okunur. tarihAlani AÇIKÇA veriliyor, çünkü ayrıştırma
  // tablosu stok tablolarından 539 hafta daha eskiye gidiyor: bacaklar bir gün
  // ayrışırsa şerit manşetin KENDİ gününü basmalı.
  'yp-mevduat': {
    anahtar: 'stok_toplam_mia',
    olcu: 'Yurt içi yerleşiklerin YP mevduatı',
    birim: 'mlr USD',
    ondalik: 1,
    tarihAlani: 'stok_toplam_mia_tarih',
  },
};

/** Manşet tanımı (anahtar, hane, işaret, tarih alanı) — istemci tazelemesi aynı kuralı uygular. */
export function hatMansetTanimi(slug: string) {
  return HAT_MANSET[slug] ?? null;
}

/** Hattın en son koştuğu/ilerlediği an: kosum_tarihi → _tarih (meta veri saati). */
export function projeSaati(slug: string): Date | null {
  const d = oku<Record<string, unknown>>(path.join(PROJE_DIZIN, slug, 'ozet.json'));
  if (!d) return null;
  for (const k of ['kosum_tarihi', '_tarih']) {
    const t = tariheCevir(d[k]);
    if (t) return t;
  }
  return null;
}

/** Bir hattın manşet büyüklüğünü ve o büyüklüğün KENDİ tarihini okur. */
export function hatManseti(slug: string): Pick<HatSatiri, 'deger' | 'metin' | 'olcu' | 'birim' | 'tarih' | 'yas'> {
  const bos = { deger: null, metin: null, olcu: '', birim: '', tarih: '', yas: null };
  const t = HAT_MANSET[slug];
  if (!t) return bos;
  const d = oku<Record<string, unknown>>(path.join(PROJE_DIZIN, slug, 'ozet.json'));
  if (!d) return bos;
  const v = d[t.anahtar];
  if (typeof v !== 'number' || !Number.isFinite(v)) {
    // Hat henüz koşmamış olabilir; tarihi yine de göster ki satır "veri yok"
    // demek yerine NE ZAMANDIR veri olmadığını söylesin.
    const t0 = typeof d._tarih === 'string' ? d._tarih : '';
    return { ...bos, olcu: t.olcu, birim: t.birim, tarih: tarihYaz(t0) };
  }
  const tarih =
    (t.tarihAlani && typeof d[t.tarihAlani] === 'string' ? (d[t.tarihAlani] as string) : '') ||
    (typeof d[`${t.anahtar}_tarih`] === 'string' ? (d[`${t.anahtar}_tarih`] as string) : '') ||
    (typeof d._tarih === 'string' ? d._tarih : '');
  const g = tariheCevir(tarih);
  const yas = g ? gunFarki(g) : null;
  return {
    deger: sayi(v, t.ondalik, t.isaret ?? false),
    metin: olcuYaz(v, t.birim, t.ondalik, t.isaret ?? false),
    olcu: t.olcu, birim: t.birim, tarih: tarihYaz(tarih), yas,
  };
}

// ── Bülten ──────────────────────────────────────────────────
export function sonBulten(): AnaSayfaVerisi {
  const bos: AnaSayfaVerisi = {
    var: false,
    tarih: '',
    trTarih: '',
    gun: '',
    olusturma: '',
    bultenHref: '/bulten/',
    bultenYazili: false,
    bultenHaftalik: false,
    bultenTrTarih: '',
    enstruman: 0,
    hatSayisi: 0,
    rejim: [],
    sigma: [],
    sigmaKip: 'gunluk',
    manset: null,
    takvimGunu: [],
    siradaki: [],
  };
  let dosyalar: string[] = [];
  try {
    dosyalar = fs
      .readdirSync(BULTEN_DIZIN)
      .filter((f) => f.endsWith('.json'))
      .sort();
  } catch {
    return bos;
  }
  if (!dosyalar.length) return bos;
  const b = oku<Record<string, any>>(path.join(BULTEN_DIZIN, dosyalar[dosyalar.length - 1]));
  if (!b) return bos;
  // YAYIN KAPISI ana sayfada da geçerli: ölçülen katman en yeni dosyadan gelir
  // (yazı olmasa da doğru), ama "Günün bülteni →" bağı yalnız YAZILMIŞ bir sayıya
  // gider — aksi hâlde henüz üretilmemiş bir sayfaya bağ verilirdi.
  let yazili: Record<string, any> | null = null;
  for (let i = dosyalar.length - 1; i >= 0; i--) {
    const aday = oku<Record<string, any>>(path.join(BULTEN_DIZIN, dosyalar[i]));
    if (aday?.gundem_kaynagi === 'yazili') { yazili = aday; break; }
  }

  // Önceki ölçüm: bir önceki bülten dosyası. Aynı ad taşıyan satırın değeri
  // `onceki` olur; dosya ya da satır yoksa fark hiç yazılmaz.
  const onceki = dosyalar.length > 1
    ? oku<Record<string, any>>(path.join(BULTEN_DIZIN, dosyalar[dosyalar.length - 2]))
    : null;
  const oncekiDeger = new Map<string, number>(
    (Array.isArray(onceki?.rejim) ? (onceki!.rejim as any[]) : [])
      .filter((r: any) => r && typeof r.deger === 'number')
      .map((r: any) => [String(r.ad), r.deger as number] as [string, number]),
  );
  const oncekiEtiket = new Map<string, string>(
    (Array.isArray(onceki?.rejim) ? (onceki!.rejim as any[]) : [])
      .filter((r: any) => r && typeof r.etiket === 'string' && r.etiket)
      .map((r: any) => [String(r.ad), String(r.etiket)] as [string, string]),
  );
  const rejim: RejimSatiri[] = (Array.isArray(b.rejim) ? b.rejim : []).map((r: any) => ({
    ...r,
    onceki: oncekiDeger.has(String(r.ad)) ? oncekiDeger.get(String(r.ad)) : undefined,
    etiketOnceki: oncekiEtiket.get(String(r.ad)),
  }));
  const sigma: SigmaSatiri[] = b?.piyasa?.en_cok_hareket?.sigma ?? [];
  const enstruman = (b?.piyasa?.gruplar ?? []).reduce(
    (n: number, g: any) => n + (g?.satirlar?.length ?? 0),
    0,
  );

  return {
    var: true,
    tarih: b.tarih ?? '',
    trTarih: b.tr_tarih ?? '',
    gun: b.gun ?? '',
    olusturma: b.olusturma ?? '',
    bultenHref: yazili?.tarih ? `/bulten/${yazili.tarih}/` : '/bulten/',
    bultenYazili: !!(yazili && yazili.tarih === b.tarih),
    bultenHaftalik: !!yazili?.haftalik,
    bultenTrTarih: yazili?.tr_tarih ?? '',
    enstruman,
    hatSayisi: Object.keys(HAT_MANSET).length,
    rejim,
    sigma,
    sigmaKip: b?.piyasa?.en_cok_hareket?.sigma_kip ?? 'gunluk',
    manset: mansetKur(rejim),
    ...takvimOzeti(b),
  };
}

/** Ölçüm gününün takvimi ve sıradaki birinci derece veriler (bülten verisinden). */
function takvimOzeti(b: Record<string, any>): Pick<AnaSayfaVerisi, 'takvimGunu' | 'siradaki'> {
  const gun = String(b?.tarih ?? '');
  const kayit = (k: any): TakvimKaydi => ({
    olay: String(k?.olay ?? ''),
    saat: String(k?.saat ?? ''),
    ulke: String(k?.ulke ?? ''),
    trTarih: String(k?.tr_tarih ?? ''),
    gun: String(k?.gun ?? ''),
    onem: typeof k?.onem === 'number' ? k.onem : 9,
    kalanGun: typeof k?.kalan_gun === 'number' ? k.kalan_gun : null,
  });
  const anahtar = (k: any) => `${k?.olay}|${k?.tarih}|${k?.saat ?? ''}|${k?.not_ ?? ''}`;
  const gorulen = new Set<string>();
  const takvimGunu: TakvimKaydi[] = [];
  const tum = [
    ...(Array.isArray(b?.kritik_takvim) ? b.kritik_takvim : []),
    ...(Array.isArray(b?.takvim) ? b.takvim.flatMap((t: any) => t?.kayitlar ?? []) : []),
  ];
  for (const k of tum) {
    if (String(k?.tarih ?? '') !== gun) continue;
    const a = anahtar(k);
    if (gorulen.has(a)) continue;
    gorulen.add(a);
    takvimGunu.push(kayit(k));
  }
  takvimGunu.sort((x, y) => (x.saat || '99:99').localeCompare(y.saat || '99:99') || x.onem - y.onem);
  // Aynı başlığı taşıyan kayıtlar tek satırda kalır (bütçe dengesinin iki
  // ayrı tablosu aynı gün aynı saatte yayımlanır; ana sayfada ayrım gerekmez).
  const siradaki: TakvimKaydi[] = [];
  const adlar = new Set<string>();
  for (const k of Array.isArray(b?.kritik_takvim) ? b.kritik_takvim : []) {
    if (String(k?.tarih ?? '') <= gun) continue;
    const a = `${k?.olay}|${k?.tarih}`;
    if (adlar.has(a)) continue;
    adlar.add(a);
    siradaki.push(kayit(k));
    if (siradaki.length >= 4) break;
  }
  return { takvimGunu, siradaki };
}
