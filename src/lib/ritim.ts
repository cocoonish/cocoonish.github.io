/* ─────────────────────────────────────────────────────────────
   Panonun yayım ritmi — ana saatinin (`_tarih`) ne sıklıkla ilerlediği.

   Kodlar burada TEK yerde durur: içerik şeması (content.config.ts) panonun
   ön bilgisindeki `ritim` alanını bu listeyle sınar, Projeler sayfası
   grupları bu sırayla kurar, sayfa sınavı (28) derlenmiş dizini bu sırayla
   okur. Bu dosya hiçbir şey içe aktarmaz; şema onu derleme öncesinde yükler.

   Ritim ELLE beyan edilir ama ölçüye bağlıdır: sınav her panonun beyanını
   bülten ölçüm katmanının ritim eşiğiyle (bulten/ayar.py → RITIM) kıyaslar
   ve ayrışmayı adıyla uyarır. Eşikler ölçülmüş üç kümede duruyor (4–6 gün ·
   11 gün · 32–75 gün) ve 05.10.2026'da gözlem defterindeki tarihçeyle
   sınandı: günlük kümede ana saatin ilerlemeleri arası medyan 1,0–1,6 gün,
   haftalıkta 7,0, aylıkta 14–21 gün (yayımlar ay içinde farklı günlere
   düşüyor).
   ───────────────────────────────────────────────────────────── */

export const RITIMLER = ['gunluk', 'haftalik', 'aylik', 'ceyreklik'] as const;
export type Ritim = (typeof RITIMLER)[number];

/** Okura giden ad ve tek cümlelik açıklama — gruplar bu sırayla basılır. */
export const RITIM_GRUBU: Record<Ritim, { ad: string; aciklama: string }> = {
  gunluk: {
    ad: 'Her iş günü',
    aciklama:
      'Piyasa kapanışları, haber akışı ve TCMB’nin günlük yayımlarıyla her iş günü ilerler.',
  },
  haftalik: {
    ad: 'Haftalık',
    aciklama:
      'TCMB’nin perşembe günü yayımladığı haftalık para, banka ve menkul kıymet istatistikleriyle ilerler; veri bir önceki cuma haftasını kapsar.',
  },
  aylik: {
    ad: 'Aylık',
    aciklama:
      'Ayda bir yayımlanan resmî istatistiklerle ya da ay içindeki ihale takvimiyle ilerler. Yayım gecikmesi seriden seriye değişir: TÜFE ay kapandıktan birkaç gün sonra, ödemeler dengesi altı-sekiz hafta sonra gelir.',
  },
  ceyreklik: {
    ad: 'Üç aylık',
    aciklama: 'Çeyreklik yayımlarla ilerler.',
  },
};

/** Arşivdeki pano ritminden bağımsız olarak en sondaki grupta durur. */
export const ARSIV_GRUBU = {
  ad: 'Arşiv',
  aciklama: 'Artık tazelenmeyen panolar; son verileriyle duruyor.',
};
