/* ─────────────────────────────────────────────────────────────
   İşlem fikirleri — okura basılan sözlük, yazım ve sabit metin: TEK yer.

   Aynı fikir iki yerde basılır: açıldığı bülten sayısının "İşlem fikirleri"
   bölümünde (BultenGovde) ve Tradeler sayfasında (pages/tradeler). Durum
   etiketi, birim yazımı, uyarı ve yöntem metni iki yerde yazılsaydı bir gün
   sessizce ayrışırdı: bülten "stopta kapandı" derken defter başka bir şey
   derdi ya da uyarının bir cümlesi yalnız bir sayfada kalırdı.

   Veri sözleşmesi bulten/fikir.py'dedir (birim, sonuç birimi, durumlar,
   fiili giriş, donan kapanış). Bu modül YALNIZ YAZAR: hiçbir sonucu,
   durumu ya da girişi hesaplamaz — sayılar ölçülen katmandan gelir.
   Makine değerleri (kimlik, seri kodu, tür, yön, sınıf kodu) okura basılmaz;
   okura bu sözlüklerin Türkçe karşılığı gider.
   ───────────────────────────────────────────────────────────── */
import { sayi, yuzde, degisim } from './bicim';

export const FIKIR_SINIF: Record<string, string> = {
  faiz: 'Faiz', fx: 'Döviz', hisse: 'Hisse', emtia: 'Emtia', kredi: 'Kredi',
};

export const FIKIR_TUR: Record<string, string> = {
  yalin: 'Tek bacak', egri: 'Eğri', kelebek: 'Kelebek', goreli: 'Göreli', opsiyon: 'Opsiyon',
  olculemez: 'Karnesi tutulmuyor',
};

/** Karnenin durumları (bulten/fikir.degerle) → okura giden etiket. */
export const FIKIR_DURUM: Record<string, string> = {
  acik: 'açık', olculemez: 'karnesi tutulmuyor', hedef: 'hedefte kapandı', stop: 'stopta kapandı',
  sure: 'ufuk doldu', geri_cekildi: 'erken kapandı', vade: 'vadesinde', olculemedi: 'ölçülemedi',
  sure_olculemez: 'ufku doldu', giriste_gecersiz: 'girişte geçersiz',
};

/** Kapanmış durumlar — bulten/fikir.KAPANMIS ile BİREBİR (duman_sinav kaynak
 *  metninden kıyaslar). Bir kapanış bir sayıya yazıldıktan sonra donar. */
export const FIKIR_KAPANMIS = new Set([
  'hedef', 'stop', 'sure', 'geri_cekildi', 'vade', 'olculemedi', 'sure_olculemez', 'giriste_gecersiz',
]);

/** Açık sayılan durumlar (karnesi tutulmayan fikir de ufku dolana kadar açıktır). */
export const FIKIR_ACIK = new Set(['acik', 'olculemez']);

/** Mekanik kapanışın okura giden açıklaması. Yazarın erken kapanışında
 *  (geri_cekildi) açıklama yazarın kendi sebebidir, burada durmaz. */
export const FIKIR_KAPANIS_NEDEN: Record<string, string> = {
  hedef: 'Hedef seviyesi bir kapanışta aşıldı; fikir o kapanışla kapandı.',
  stop: 'Stop seviyesi bir kapanışta aşıldı; fikir o kapanışla kapandı.',
  sure: 'Ufuk doldu; fikir ufuk içindeki son kapanışla kapandı.',
  vade: 'Vade doldu; sonuç vade sonu ödemesidir.',
  giriste_gecersiz: 'Giriş kapanışı seviyelerden birinin ötesindeydi; yapı kurulamadan geçersiz kaldı.',
  olculemedi: 'Ufuk dolana kadar yayımdan sonra kapanış gelmedi; sonuç ölçülemedi.',
  sure_olculemez: 'Ufku doldu; karnesi tutulmadığı için sonucu yok.',
};

export const FIKIR_UYARI = 'Bu bölümdeki işlem fikirleri bültenin piyasa okumasını bir işlem yapısına çevirir. '
  + 'Kişiye özel değildir; yatırım danışmanlığı kapsamında değildir. Yatırım danışmanlığı hizmeti, '
  + 'yetkili kuruluşlarla imzalanacak sözleşme çerçevesinde kişinin risk ve getiri tercihleri dikkate '
  + 'alınarak sunulur. Referans seviyeler bültenin ölçüm anındaki kapanışlardır; karne kapanış bazında '
  + 'tutulur ve gün içi dokunuşu ölçmez. Geçmiş sonuçlar gelecekteki sonuçların göstergesi değildir.';

export const FIKIR_YONTEM = 'Referans seviye yazarın değil ölçümün: fiyat bacağı piyasa fotoğrafının o '
  + 'sayıdaki kapanışından, TL faiz bacağı DİBS eğrisinin ölçüm anındaki düğümünden okunur. Karne '
  + 'referanstan değil, yayımdan sonraki ilk kapanıştan (fiili giriş) başlar: referans bir önceki seansın '
  + 'kapanışıdır ve gece boyunca olan hareketi fikre yazmak, okurun yakalayamayacağı bir kazancı saymak '
  + 'olurdu. Giriş kapanışı seviyelerden birinin ötesindeyse fikir girişte geçersiz sayılır. Girişten '
  + 'sonraki her kapanışta yapının değeri yeniden kurulur; hedef ya da stop bir kapanışta aşılırsa fikir '
  + 'o gün kapanır, ufuk dolarsa son kapanışla kapanır; yazarın erken kapanışı da kapatan sayının '
  + 'yayımından sonraki ilk kapanışta gerçekleşir; emir girişle aynı kapanışa düşerse yapı hiç taşınmamıştır '
  + 've sonucu yoktur. Bir kapanış bir sayıya yazıldıktan sonra değişmez. '
  + 'Faiz yapılarında sonuç baz puan, fiyat yapılarında yüzdedir; R, sonucun fiili girişten stopa olan mesafeye '
  + 'oranıdır ve farklı birimdeki yapıları aynı ölçüde toplar. Dolar/TL fikrinin sonucu spot hareketi ile '
  + 'TL ve ABD doları kısa faizleri arasındaki farktan gelen taşımanın toplamıdır (TLREF ve ABD 3 aylık hazine '
  + 'bonosu faizi, takvim günüyle); hedef ve stop spot kapanışında sorulur, bu yüzden stopta kapanan bir fikir '
  + 'taşıma sayesinde kârla kapanabilir. Taşıma ölçülemediği gün sonuç yalnız spottur ve kazanç oranına girmez. '
  + 'Öbür fikirlerde sonuç işlem maliyetini, alış-satış makasını, fonlama ve taşıma maliyetini, vadeli devir '
  + 'maliyetini ve temettüyü içermez. Vadeli bacaklar devir günlerinde giriş '
  + 'kontratı cinsinden izlenir. Opsiyon fikrinde prim ölçülmez (örtük oynaklık verisi yok): karne vade '
  + 'sonu ödemesini dayanağın kapanışından yazar ve kazanç oranına katmaz. TRY OIS, çapraz kur swap bazı '
  + 've tek hisse gibi elimizde fiyatı olmayan enstrümanlar ya ölçülebilir bir vekille izlenir ya da '
  + 'karneye sonuçla girmez.';

export const sayiMi = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

/** Seviye yapının kendi biriminde (bulten/fikir.birim): tek getiri yüzde önde,
 *  getiri bileşimi baz puan arkada, fiyat kendi hanesiyle, oran dört haneyle. */
export const fkSeviye = (v: unknown, f: any): string => {
  if (!sayiMi(v)) return '—';
  const br = String(f?.birim ?? '');
  const n = sayiMi(f?.ondalik) ? f.ondalik : null;
  if (br === '%') return yuzde(v, 2);
  if (br === 'bp') return `${sayi(v, n ?? 1)} bp`;
  if (br === 'oran') return sayi(v, 4);
  return sayi(v, n ?? 2);
};

/** Sonucun birimi: faiz yapılarında baz puan, fiyat yapılarında yüzde. */
export const fkSonucBirim = (f: any): string =>
  f?.sonuc_birim ?? (['bp', '%'].includes(String(f?.birim ?? '')) ? 'bp' : '%');

/** Sonuç (+ kazanç): "+43,0 bp" ya da "−%7,68". */
export const fkSonuc = (v: unknown, f: any): string =>
  !sayiMi(v) ? '—' : fkSonucBirim(f) === 'bp' ? degisim(v, 'bp', 1) : degisim(v, '%', 2);

/** Yön sınıfı (renk): artı kazanç, eksi kayıp. */
export const fkYon = (v: unknown) => (sayiMi(v) ? { arti: v > 0, eksi: v < 0 } : {});

export const kalanYaz = (n: unknown): string =>
  !sayiMi(n) ? '—' : n < 0 ? `${-n} gün geçti` : n === 0 ? 'bugün' : `${n} gün`;

/** Kullanım fiyatları parça parça: her fiyat satırda bölünmez, satır ayraçta kırılır. */
export const fkKullanimParca = (f: any): { parca: string[]; ayrac: string } => {
  const o = f?.opsiyon ?? {};
  const k = (Array.isArray(o.kullanim) ? o.kullanim : []).filter(sayiMi);
  // Kullanım fiyatı yazarın yazdığı hanede (en az iki, en çok dört): dayanağın
  // kotasyon hanesi (dolar/TL dört) 51,25'i "51,2500" diye basıyordu.
  const hane = (x: number) => (String(x).split('.')[1] ?? '').length;
  const n = Math.min(4, Math.max(2, ...k.map(hane)));
  if (o.tip === 'risk_reversal' && k.length === 2) return { parca: [`satım ${sayi(k[0], n)}`, `alım ${sayi(k[1], n)}`], ayrac: ' · ' };
  return { parca: k.length ? k.map((x: number) => sayi(x, n)) : ['—'], ayrac: ' – ' };
};

export const noktali = (s: unknown) => { const t = String(s ?? '').trim(); return /[.!?…]$/.test(t) ? t : `${t}.`; };

/** Sonucu OLMAYAN kapanış durumları: fiili giriş hiç gelmedi, karnesi
 *  tutulmuyor ya da yapı girişte kurulamadı. */
export const FIKIR_SONUCSUZ = new Set(['olculemedi', 'sure_olculemez', 'giriste_gecersiz']);

/** Fiili giriş henüz yoksa okura giden not: kısa adı ve neyin beklendiği (dar
 *  tablo hücresinde iki satır, şeritte tek satır). */
export const GIRIS_BEKLENIYOR_KISA = 'giriş bekleniyor';
export const GIRIS_BEKLENIYOR_NE = 'yayımdan sonraki ilk kapanış';
export const GIRIS_BEKLENIYOR = `${GIRIS_BEKLENIYOR_KISA} (${GIRIS_BEKLENIYOR_NE})`;

/** Sonucun stop mesafesine oranı (ölçülen katmanın `sonuc_r`): "+0,8 R". */
export const fkR = (v: unknown): string => (sayiMi(v) ? `${sayi(v, 1, true)} R` : '');

/** Opsiyon sonucunun ne olduğu — prim ölçülmediği için sonuç bir kazanç değil,
 *  bir ödemedir. Vadede ödeme; erken kapanışta (ya da açıkken) içsel değer, ki
 *  zaman değerini de taşımaz. */
export const opsiyonSonucNotu = (k: any): string =>
  k?.sonuc_turu === 'odeme' ? 'vade sonu ödemesi, prim hariç'
    : k?.sonuc_turu === 'ic_deger' ? 'erken kapanış: içsel değer, prim ve zaman değeri hariç'
      : 'içsel değer, prim ve zaman değeri hariç';

/** Taşıma ayrışımı (USD/TRY yalın fikirlerinde ölçülen katmanın iki alanı:
 *  `spot_sonuc` spot hareketi, `tasima` taşıma payı; toplamları sonucun
 *  kendisidir). Site HESAPLAMAZ, yalnız basar: iki parça ölçülen katmanda
 *  ayrı ayrı yuvarlanır ve farkla kurulan bir parça okura ondan ayrışan bir
 *  sayı yazardı. */
/** Taşıması ölçülemeyen dolar/TL kaydının notu (açıkta ve kapanmışta). */
export const tasimaOlculemediNotu = (kapanmis: boolean): string =>
  `Taşıma payı ölçülemedi; sonuç yalnız spot hareketidir${kapanmis ? ' ve kazanç oranına girmez' : ''}.`;

/** Ufuk günü kapanışı seriye henüz girmemiş fikrin notu. */
export const UFUK_BEKLENIYOR = 'ufuk kapanışı bekleniyor';
export const UFUK_BEKLENIYOR_NOT = 'Ufuk günü kapanışı henüz seriye girmedi; fikir o kapanışla kapanacak.';

export const tasimaAyrisimi = (k: any): { spot: string; tasima: string } | null =>
  sayiMi(k?.tasima) && sayiMi(k?.spot_sonuc)
    ? { spot: fkSonuc(k.spot_sonuc, k), tasima: fkSonuc(k.tasima, k) }
    : null;

/** Kapanmış bir fikrin hükmü: kâr, zarar ya da başabaş — YALNIZ sonucu ölçülen,
 *  primi olmayan fikirde. Opsiyonun ödemesi primsizdir ("kazandı" sayılmaz),
 *  ölçülemeyen ve girişte geçersiz kalan fikrin sonucu yoktur: ikisinde de null. */
export const sonucHukmu = (k: any): { etiket: string; sinif: 'kar' | 'zarar' | 'basabas' } | null => {
  if (!k || k.tur === 'opsiyon' || k.tur === 'olculemez' || !sayiMi(k.sonuc)) return null;
  // Taşıması ölçülemeyen dolar/TL sonucu yalnız spottur: kâr/zarar hükmü kurulmaz
  // (Python sayımı da onu kazanç oranına katmaz).
  if (k.tasima_olculemedi) return null;
  if (k.sonuc > 0) return { etiket: 'Kâr', sinif: 'kar' };
  if (k.sonuc < 0) return { etiket: 'Zarar', sinif: 'zarar' };
  return { etiket: 'Başabaş', sinif: 'basabas' };
};
