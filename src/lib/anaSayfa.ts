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
import { sayi, yuzde, tariheCevir, tarihYaz, gunFarki } from './bicim';
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
  /** Bu hattın MANŞET büyüklüğü — biçimlenmiş metin, ör. "48,03" */
  deger: string | null;
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
}

// Sayı ve tarih biçimi lib/bicim.ts'te — burada yalnız yeniden dışa aktarılır.

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

/** Değer + birim: "+13,3 puan", "%29,5", "104,6 endeks". */
function birimYaz(s: RejimSatiri): string {
  if (s.deger === null) return '';
  if (s.birim === '%') return yuzde(s.deger, 1);
  if (s.birim === 'puan') return `${sayi(s.deger, s.ad.includes('eğim') ? 2 : 1, true)} puan`;
  return `${sayi(s.deger, 1)} ${s.birim}`;
}


function mansetKur(rejim: RejimSatiri[]): AnaSayfaVerisi['manset'] {
  const bul = (ad: string) => rejim.find((r) => r.ad === ad && r.deger !== null && r.etiket);
  const durus = bul('Reel politika faizi (ileriye dönük)') ?? bul('Reel politika faizi (geriye dönük)');
  if (!durus) return null;
  const durusYon = ETIKET_YON[durus.etiket];

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
  const b = `${KISA_AD[karsi.ad] ?? karsi.ad} ${birimYaz(karsi)} (${karsi.etiket})`;
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
  'tcmb-net-rezerv': { anahtar: 'g_net', olcu: 'Net rezerv (günlük tahmin)', birim: 'mlr $', ondalik: 1, tarihAlani: 'g_tarih' },
  'fonlama-likidite': { anahtar: 'politika', olcu: 'Politika faizi', birim: '%', ondalik: 2 },
  'dibs-verim-egrisi': { anahtar: 'spot_2y', olcu: '2 yıllık spot getiri', birim: '%', ondalik: 2 },
  enflasyon: { anahtar: 'tufe_12a', olcu: 'TÜFE (yıllık)', birim: '%', ondalik: 2 },
  'kredi-parasal': { anahtar: 'g_ar_13y', olcu: 'Kredi büyümesi (13h yıl., kur arınd.)', birim: '%', ondalik: 1 },
  'try-reer': { anahtar: 'redk', olcu: 'Reel efektif kur', birim: 'endeks', ondalik: 1 },
  'hazine-ihrac': { anahtar: 'maliyet_son', olcu: 'Son ihale maliyeti', birim: '%', ondalik: 2 },
  'yabanci-pozisyon': { anahtar: 'toplam_4h', olcu: 'Yabancı 4 haftalık net akım', birim: 'mn $', ondalik: 0, isaret: true },
  'odemeler-dengesi': { anahtar: 'cari_ay_mia', olcu: 'Aylık cari denge', birim: 'mlr $', ondalik: 1, isaret: true },
  'butce-borc': { anahtar: 'denge_gsyh', olcu: 'Bütçe dengesi', birim: '% GSYH', ondalik: 2, isaret: true },
  makroihtiyati: { anahtar: 'ayrisma', olcu: 'Makroihtiyati ayrışma', birim: 'puan', ondalik: 1 },
  'tl-tasima': { anahtar: 'endeks', olcu: 'TL taşıma endeksi', birim: '', ondalik: 1 },
  'tufex-basabas': { anahtar: 'basabas_2y', olcu: '2 yıllık başabaş enflasyon', birim: '%', ondalik: 2 },
  'reel-sektor-fx': { anahtar: 'net_pozisyon', olcu: 'Net döviz pozisyonu', birim: 'mlr $', ondalik: 1, isaret: true },
  'fx-haber-endeksi': { anahtar: 'spread', olcu: "Sepet spread'i", birim: '', ondalik: 2, isaret: true },
  'yiyecek-hizmetleri-marj': { anahtar: 'oran_ev_yemekleri', olcu: 'Ev yemekleri / gıda oranı', birim: '×', ondalik: 2 },
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
export function hatManseti(slug: string): Pick<HatSatiri, 'deger' | 'olcu' | 'birim' | 'tarih' | 'yas'> {
  const bos = { deger: null, olcu: '', birim: '', tarih: '', yas: null };
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
  return { deger: sayi(v, t.ondalik, t.isaret ?? false), olcu: t.olcu, birim: t.birim, tarih: tarihYaz(tarih), yas };
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

  const rejim: RejimSatiri[] = Array.isArray(b.rejim) ? b.rejim : [];
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
  };
}
