/* ─────────────────────────────────────────────────────────────
   Tradeler — işlem fikirlerinin defteri: yayımlanmış sayıların KENDİSİNDEN.

   Ayrı bir defter dosyası YOK (bulten/fikir.py başlığı): fikir açıldığı
   sayının `fikirler` alanında, yazarın erken kapanış emri kapattığı sayının
   `fikir_kapat` alanında, mekanik kapanış ilk ölçüldüğü sayının
   `fikir_karne`sinde durur. Bu modül o üç alanı SEÇER ve BİRLEŞTİRİR; hiçbir
   sonucu, durumu ya da fiili girişi yeniden hesaplamaz — tanım Python'da tek
   yerde kalır (`fikir.degerle`, `fikir.karne`). İkinci bir hesap bir gün
   bülten sayısıyla sessizce ayrışırdı ve okur iki sayfada iki sonuç görürdü.

   Kurallar `fikir.defter()` ile birebir:
   · TANIM yalnız YAZILMIŞ biçim 3 sayının `fikirler` alanından (yazılmamış
     sayı okura hiç çıkmadı; fikri de açılmamıştır).
   · DURUM ve TAKİP her sayının `fikir_karne.kayitlar`ından — yazılmış ya da
     yazılmamış: ölçü veriden gelir, yayımdan bağımsızdır. Kayıtlar sayı
     tarihine göre dizilir; SON durum en son kayıttır. İLK kapanmış kayıt
     DONAR: sonraki sayılar onu yeniden hesaplamaz, takip orada biter.
   · ERKEN KAPANIŞ yalnız yazılmış sayının `fikir_kapat`ından, fikir o güne
     kadar kapanmamışsa; ilk emir geçerlidir.

   TANIMI OLMAYAN KARNE KAYDI ATLANMAZ, adıyla basılır. Python'un defteri bir
   kaydı yalnız tanımlı fikir için üretir; tanımsız bir kayıt, tanımın taşındığı
   sayının artık okunamadığı (silinmiş ya da biçimi değişmiş) anlamına gelir.
   O kayıt bir sayıda okura basılmış bir SONUÇTUR ve onu gizlemek — özellikle
   bir zararı — defterin kendi sözünü bozar. Kayıt kendi alanlarıyla (başlık,
   yapı, seviyeler, sonuç) basılır, gerekçesi olmadığı ve açıldığı sayının
   bulunamadığı söylenir, bülten kartına bağ kurulmaz (ölü bağ olurdu).
   ───────────────────────────────────────────────────────────── */
import { bultenSayilari } from './yayinlar';
import { FIKIR_KAPANMIS } from './fikir';

export interface TakipSatiri {
  /** Kaydı taşıyan sayının günü (YYYY-MM-DD). */
  tarih: string;
  /** Sayı yazılmışsa okura açık sayfası (fikir bölümüne çapayla); değilse null. */
  href: string | null;
  kayit: any;
}

export interface ErkenEmir {
  tarih: string | null;
  sebep: string | null;
  /** Emrin yazıldığı sayı. */
  sayi: string;
  href: string;
}

export type TradeGrubu = 'acik' | 'kapanan' | 'olculemez';

export interface Trade {
  kimlik: string;
  /** Yazılmış sayının `fikirler` öğesi; tanımsız karne kaydında null. */
  tanim: any | null;
  /** Fikrin açıldığı sayı ve o sayıdaki kartın bağı. */
  acildigi: { tarih: string; href: string } | null;
  /** Karnede göründüğü her sayı, kapanışa kadar (kapanış dahil). */
  takip: TakipSatiri[];
  /** Son kayıt — kapandıysa donmuş kapanış kaydı; karne henüz yoksa null. */
  son: any | null;
  /** Son kaydın sayı günü. */
  sonOlcum: string | null;
  erken: ErkenEmir | null;
  /** Görünüm: tanımın üstüne son kayıt (sayılar kayıttan, metin tanımdan). */
  f: any;
  grup: TradeGrubu;
  /** Kapanmış ama çıkışı henüz gerçekleşmemiş erken kapanış emri. */
  cikisBekleniyor: boolean;
}

export interface Defter {
  tradeler: Trade[];
  /** En son karne taşıyan sayının `fikir_karne.sayim`ı (tanım Python'da). */
  sayim: any | null;
  sayimTarih: string | null;
  /** En son karne kurulamadıysa o sayının günü (durumlar bir önceki ölçümden). */
  karneHataTarih: string | null;
}

const nesne = (x: unknown): x is Record<string, any> => !!x && typeof x === 'object' && !Array.isArray(x);
const surum = (b: any): number => { const n = Number(b?.surum ?? 2); return Number.isFinite(n) ? n : 2; };
const sayiSayfasi = (tarih: string) => `/bulten/${tarih}/`;

let _defter: Defter | null = null;

export function defter(): Defter {
  if (_defter) return _defter;
  const sayilar = bultenSayilari();   // eskiden yeniye

  // 1) TANIMLAR — yazılmış biçim 3 sayılar (fikir.defter: aynı kimlik sonradan
  //    yeniden yazılırsa sonuncusu geçerlidir).
  const tanim = new Map<string, { f: any; tarih: string }>();
  for (const s of sayilar) {
    if (!s.yazili || surum(s.b) < 3 || !Array.isArray(s.b?.fikirler)) continue;
    for (const f of s.b.fikirler) {
      if (nesne(f) && f.kimlik) tanim.set(String(f.kimlik), { f, tarih: s.tarih });
    }
  }

  // 2) KARNE ve ERKEN KAPANIŞ — sayı sayı, fikir.defter'in sırasıyla: önce o
  //    sayının karnesi (kapanış donar), sonra yazılmışsa kapanış emirleri.
  const takip = new Map<string, TakipSatiri[]>();
  const kapandi = new Set<string>();
  const erken = new Map<string, ErkenEmir>();
  let sayim: any = null;
  let sayimTarih: string | null = null;
  let karneHataTarih: string | null = null;
  for (const s of sayilar) {
    const karne = s.b?.fikir_karne;
    if (nesne(karne)) {
      if (karne.hata) {
        karneHataTarih = s.tarih;
      } else {
        karneHataTarih = null;
        if (nesne(karne.sayim) && Object.keys(karne.sayim).length > 0) {
          sayim = karne.sayim;
          sayimTarih = s.tarih;
        }
      }
      const href = s.yazili && surum(s.b) >= 3 ? `${sayiSayfasi(s.tarih)}#fikirler` : null;
      for (const x of Array.isArray(karne.kayitlar) ? karne.kayitlar : []) {
        if (!nesne(x) || !x.kimlik) continue;
        const k = String(x.kimlik);
        if (kapandi.has(k)) continue;              // donmuş kapanışın kopyaları takibe girmez
        if (!takip.has(k)) takip.set(k, []);
        takip.get(k)!.push({ tarih: s.tarih, href, kayit: x });
        if (FIKIR_KAPANMIS.has(String(x.durum))) kapandi.add(k);
      }
    }
    if (!s.yazili) continue;
    for (const x of Array.isArray(s.b?.fikir_kapat) ? s.b.fikir_kapat : []) {
      if (!nesne(x) || !x.kimlik) continue;
      const k = String(x.kimlik);
      if (!tanim.has(k) || kapandi.has(k) || erken.has(k)) continue;
      erken.set(k, {
        tarih: x.tarih ? String(x.tarih) : null,
        sebep: x.sebep ? String(x.sebep) : null,
        sayi: s.tarih,
        href: sayiSayfasi(s.tarih),
      });
    }
  }

  // 3) BİRLEŞTİRME — tanımlı her fikir ve tanımsız her karne kaydı.
  const kimlikler = new Set<string>([...tanim.keys(), ...takip.keys()]);
  const tradeler: Trade[] = [];
  for (const k of kimlikler) {
    const t = tanim.get(k) ?? null;
    const satirlar = takip.get(k) ?? [];
    const sonSatir = satirlar.length ? satirlar[satirlar.length - 1] : null;
    const son = sonSatir?.kayit ?? null;
    const f = { ...(t?.f ?? {}), ...(son ?? {}) };
    const durum = String(son?.durum ?? '');
    const grup: TradeGrubu = f.tur === 'olculemez' ? 'olculemez'
      : FIKIR_KAPANMIS.has(durum) ? 'kapanan' : 'acik';
    const e = erken.get(k) ?? null;
    tradeler.push({
      kimlik: k,
      tanim: t?.f ?? null,
      acildigi: t ? { tarih: t.tarih, href: `${sayiSayfasi(t.tarih)}#fikir-${k}` } : null,
      takip: satirlar,
      son,
      sonOlcum: sonSatir?.tarih ?? null,
      erken: e,
      f,
      grup,
      cikisBekleniyor: grup === 'acik' && (!!e || son?.cikis_bekleniyor === true),
    });
  }
  _defter = { tradeler, sayim, sayimTarih, karneHataTarih };
  return _defter;
}

/** Açıldığı sayının kartına bağ (`/bulten/<gün>/#fikir-<kimlik>`), yalnız kart
 *  orada gerçekten basılıyorsa: yazılmış biçim 3 sayının fikir listesinde.
 *  Bülten gövdesinin karne tablosu ile Tradeler aynı haritayı okur. */
export function fikirKartBaglari(): Map<string, string> {
  const m = new Map<string, string>();
  for (const t of defter().tradeler) if (t.acildigi) m.set(t.kimlik, t.acildigi.href);
  return m;
}
