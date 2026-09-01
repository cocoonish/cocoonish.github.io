/* ─────────────────────────────────────────────────────────────
   Yayın kayıtları — bülten ve teknik sayılarının TEK okuma noktası.

   Dört sayfa (bülten dizini, bülten günü, arşiv, ana sayfa) ve iki besleme
   aynı JSON dosyalarını kendi başlarına açıp kendi kurallarıyla süzüyordu.
   Yayın kapısı (yalnız YAZILMIŞ sayı yayımlanır) dört yerde tekrar
   yazılmıştı; biri değişse diğerleri sessizce ayrışırdı. Kapı burada,
   bir kez.

   Sayı numarası da buradan gelir: yazılmış sayılar tarihe göre dizilir ve
   ilkinden itibaren sayılır. Elle yazılmaz, dosyadan türetilir — yani
   bayatlayamaz.
   ───────────────────────────────────────────────────────────── */
import { duzMetin, ozetle, istanbulSaat, damgaTarihi } from './bicim';

export interface BultenKaydi {
  tarih: string;         // YYYY-MM-DD (dosya adı)
  trTarih: string;       // "1 Eylül 2026"
  gun: string;           // "Salı"
  haftalik: boolean;
  sayiNo: number;        // yazılmış sayılar arasında kronolojik sıra (1'den)
  href: string;
  /** Bağlantı önizlemesi / RSS için düz metin özet. */
  aciklama: string;
  /** Ölçümün kurulduğu an, İstanbul saati ("07:30"). */
  olcumSaati: string;
  /** Ölçüm damgası. */
  olcumZamani: Date | null;
  /** Okura giden sayının yayın anı: yazı damgası, yoksa ölçüm anı (RSS pubDate). */
  yayinZamani: Date | null;
  yaziTarihi: string;    // yorum_zamani (YYYY-MM-DD) — yazı katmanının günü
  enstruman: number;
  haber: number;
  b: any;
}

export interface TeknikKaydi {
  tarih: string;
  trTarih: string;
  sayiNo: number;
  href: string;
  aciklama: string;
  olcumZamani: Date | null;
  olcumSaati: string;
  /** Yorumun yazıldığı an (RSS ve künye) — yoksa ölçüm anı. */
  yayinZamani: Date | null;
  veriUcu: string;
  enstruman: number;
  t: any;
}

const bultenDosyalari = import.meta.glob('../data/bulten/*.json', { eager: true });
const teknikDosyalari = import.meta.glob('../data/teknik/*.json', { eager: true });

function tarihten(yol: string): string {
  return yol.split('/').pop()!.replace('.json', '');
}

/** YAYIN KAPISI — yalnız yazılmış bülten. Kural tabanlı çekirdek her koşuda bir
 *  iskelet üretir; yazı katmanı çalışana kadar o dosya bir bülten DEĞİL. */
export const bultenYazilmis = (b: any): boolean => b?.gundem_kaynagi === 'yazili';
export const teknikYazilmis = (t: any): boolean => !!t?.yazili;

/** Bültenin okura giden tek cümlelik özeti: önce "ne oldu", yoksa yorumun ilk cümlesi. */
export function bultenAciklama(b: any): string {
  const kaynak = b?.ozet?.ne_oldu || b?.yorum || '';
  const m = ozetle(kaynak, 220);
  if (m) return m;
  return b?.haftalik
    ? `${b.tr_tarih ?? b.tarih} haftaya bakış: geçen hafta ne değişti, önümüzdeki hafta ne bekleniyor.`
    : `${b?.tr_tarih ?? b?.tarih} günlük makro bülteni: ölçülen değişimler, takvim ve günün okuması.`;
}

let _bultenler: BultenKaydi[] | null = null;

/** Yazılmış bültenler, EN YENİSİ başta. */
export function bultenler(): BultenKaydi[] {
  if (_bultenler) return _bultenler;
  const ham = Object.entries(bultenDosyalari)
    .map(([yol, m]: [string, any]) => ({ tarih: tarihten(yol), b: (m as any).default ?? m }))
    .filter((x) => bultenYazilmis(x.b))
    .sort((a, b) => (a.tarih < b.tarih ? -1 : 1));   // eskiden yeniye → numara
  _bultenler = ham
    .map((x, i) => {
      const b = x.b;
      const olcum = damgaTarihi(b.olusturma);
      return {
        tarih: x.tarih,
        trTarih: b.tr_tarih ?? x.tarih,
        gun: b.gun ?? '',
        haftalik: !!b.haftalik,
        sayiNo: i + 1,
        href: `/bulten/${x.tarih}/`,
        aciklama: bultenAciklama(b),
        olcumSaati: istanbulSaat(b.olusturma),
        olcumZamani: olcum,
        yayinZamani: damgaTarihi(b.yazi_zamani) ?? olcum,
        yaziTarihi: b.yorum_zamani ?? '',
        enstruman: (b?.piyasa?.gruplar ?? []).reduce((n: number, g: any) => n + (g?.satirlar?.length ?? 0), 0),
        haber: b?.haberler?.haber?.length ?? 0,
        b,
      } as BultenKaydi;
    })
    .reverse();
  return _bultenler;
}

let _teknikler: TeknikKaydi[] | null = null;

/** Yazılmış teknik sayılar, EN YENİSİ başta. */
export function teknikler(): TeknikKaydi[] {
  if (_teknikler) return _teknikler;
  const ham = Object.entries(teknikDosyalari)
    .map(([yol, m]: [string, any]) => ({ tarih: tarihten(yol), t: (m as any).default ?? m }))
    .filter((x) => teknikYazilmis(x.t))
    .sort((a, b) => (a.tarih < b.tarih ? -1 : 1));
  _teknikler = ham
    .map((x, i) => {
      const t = x.t;
      return {
        tarih: x.tarih,
        trTarih: t.tr_tarih ?? x.tarih,
        sayiNo: i + 1,
        href: `/teknik/${x.tarih}/`,
        aciklama: ozetle(t.giris || '', 220)
          || `${t.tr_tarih ?? x.tarih} haftalık teknik analiz: ABD 2Y/10Y, DXY, EUR/USD, USD/CHF ve BIST 100.`,
        olcumZamani: damgaTarihi(t.olcum_zamani),
        olcumSaati: istanbulSaat(t.olcum_zamani),
        yayinZamani: damgaTarihi(t.yorum_zamani) ?? damgaTarihi(t.olcum_zamani),
        veriUcu: t.veri_ucu ?? '',
        enstruman: (t.enstrumanlar ?? []).length,
        t,
      } as TeknikKaydi;
    })
    .reverse();
  return _teknikler;
}

/** Sayfa <title> için: "Sayı 12 · 1 Eylül 2026". */
export function sayiEtiketi(k: { sayiNo: number; trTarih: string }): string {
  return `Sayı ${k.sayiNo} · ${k.trTarih}`;
}

/** Düz metin uzunluğu (kelime) — künye için. */
export function kelime(html: string | null | undefined): number {
  const m = duzMetin(html);
  return m ? m.split(/\s+/).length : 0;
}
