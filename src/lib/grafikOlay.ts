/* ─────────────────────────────────────────────────────────────
   Grafikler bölümü — olay işaretleri. TEK tanım.

   Olay dosyası (`src/data/grafikler/olaylar.json`) çekme betiğinin
   (`Aktarılacak Projeler/Grafikler/cek.py → ppk_olaylari`) depodaki PPK
   duyuru arşivinden yazdığı TCMB politika faizi DEĞİŞİKLİKLERİDİR; sabit
   bırakılan kararlar işaretlenmez (hepsi çizilseydi grafik okunmazdı). Liste
   Haziran 2018'de başlar: ondan önce fonlama koridor ve geç likidite
   penceresiyle yönlendiriliyordu ve tek bir "politika faizi değişikliği"
   yazılamaz.

   İKİNCİ OLAY TÜRÜ bir veri olayıdır, piyasa olayı değil: döviz kurunun
   kapanış tanımının değiştiği gün (öncesi günlük bar, Londra gece yarısı;
   sonrası saatlik bar, İstanbul 18:00 ya da New York 17:00). Düzeyde fark
   küçüktür ama gerçekleşen oynaklıkta yapısaldır — gece saatlerinin sığ
   kotasyonu günlük getiriye girer — ve okur o günü görmeden bir oynaklık
   düşüşünü piyasaya yorardı.

   İşaret, kararın kendisiyle aynı düzlemdeki serilere konur: para politikası
   ve fonlama, piyasa (DİBS eğrisi, borsa), kredi ve mevduat faizleri, kur.
   Enflasyon, dış denge, kamu maliyesi ve büyüme serileri aylık ve çeyreklik
   yayımlanır; her gözlemi zaten bir yayımdır ve karar çizgisi orada bir
   nedensellik çağrışımı yapardı. Dünya ve küresel piyasa serilerinde TCMB
   kararı bağlam değildir.
   ───────────────────────────────────────────────────────────── */
import olayDosyasi from '../data/grafikler/olaylar.json';
import { yuzde } from './bicim';

export interface Olay {
  /** ISO gün. */
  t: string;
  /** İpucunda basılan tek satır. */
  etiket: string;
  /** +1 artırım, −1 indirim. */
  yon: number;
}

export const OLAY_BASLIKLARI = ['para', 'piyasa', 'kredi', 'kur'];

interface PpkKaydi { t: string; onceki: number; yeni: number; no: string | null }

export function ppkOlaylari(): Olay[] {
  const ppk = ((olayDosyasi as { ppk?: PpkKaydi[] }).ppk ?? []);
  return ppk.map((k) => {
    const bp = Math.round((k.yeni - k.onceki) * 100);
    return {
      t: k.t,
      yon: Math.sign(bp),
      etiket: `PPK: politika faizi ${yuzde(k.onceki, 2)} → ${yuzde(k.yeni, 2)} (${bp > 0 ? '+' : '−'}${Math.abs(bp)} bp)`,
    };
  });
}

/** Bu başlıktaki seriye (ya da hazır grafiğe) PPK işaretleri konur mu. */
export function olayUygun(baslik: string): boolean {
  return OLAY_BASLIKLARI.includes(baslik);
}

export const OLAY_BASLANGIC: string = (olayDosyasi as { baslangic?: string }).baslangic ?? '2018-06-01';

/** Kapanış tanımı geçişi (`yon` 0, ◆ ile çizilir). */
export function gecisOlayi(gecis: string, kesim: string): Olay {
  return {
    t: gecis,
    yon: 0,
    etiket: `Kapanış tanımı: bu günden önce günlük bar (Londra gece yarısı), bu günden itibaren saatlik bar (${kesim})`,
  };
}

/** Bir sayfanın olayları ve denetim etiketi; olay yoksa null. */
export function sayfaOlaylari(baslik: string, gecis: string | null, kesim: string): { olaylar: Olay[]; ad: string } | null {
  const ppk = olayUygun(baslik) ? ppkOlaylari() : [];
  const g = gecis ? [gecisOlayi(gecis, kesim)] : [];
  const olaylar = [...ppk, ...g].sort((a, b) => (a.t < b.t ? -1 : 1));
  if (!olaylar.length) return null;
  const ad = ppk.length && g.length ? 'PPK kararları ve kapanış geçişi' : ppk.length ? 'PPK faiz kararları' : 'Kapanış tanımı geçişi';
  return { olaylar, ad };
}

/** Döviz kodunun kapanış anı (ortak/fx_kapanis.KESIM_ADI ile aynı kural: lira kurları İstanbul). */
export function kesimAdi(kod: string | undefined): string {
  return kod && kod.toUpperCase().includes('TRY') ? 'İstanbul 18:00' : 'New York 17:00';
}
