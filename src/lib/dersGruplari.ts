/* ─────────────────────────────────────────────────────────────
   Araştırma derslerinin konu grupları.
   Amaç: listede "nerede ne var" sorusunun tek bakışta yanıtlanması.
   Bir ders ya açıkça slug listesinde geçer, ya da etiketlerinden
   eşleşir; hiçbiri tutmazsa "Diğer notlar"a düşer (kaybolmaz).
   ───────────────────────────────────────────────────────────── */

export interface DersGrubu {
  id: string;
  no: string;
  baslik: string;
  aciklama: string;
  /** Grup içi okuma sırası. Listede olmayanlar tarihe göre sona eklenir. */
  slugSirasi?: string[];
  /** slugSirasi tutmazsa etiketlerden eşleşme. */
  etiketler?: string[];
  /** Grup baştan sona bir hat mı, yoksa bağımsız notlar mı? */
  hat?: boolean;
}

export const GRUPLAR: DersGrubu[] = [
  {
    id: 'faiz-masasi',
    no: '01',
    baslik: 'Faiz masası — eğriden pozisyona',
    aciklama:
      'TL faiz masasının dört derslik ana hattı. Sırayla okunmak üzere yazıldı: ' +
      'her ders bir öncekinin çıktısını girdi olarak alır — konvansiyon ve eğri ' +
      'inşasıyla başlar, enstrüman fiyatlamasıyla sürer, riski ölçüp hedge eder ' +
      've son derste görüşü pozisyona çevirir.',
    hat: true,
    slugSirasi: [
      'faiz-egrisi-ve-konvansiyonlar',
      'enstruman-fiyatlama',
      'risk-ve-hedge',
      'trade-pratigi',
    ],
    etiketler: ['faiz', 'egri', 'bootstrap', 'tlref', 'swap', 'dv01', 'asw', 'ois', 'tahvil'],
  },
  {
    id: 'fx-opsiyon',
    no: '02',
    baslik: 'FX & opsiyon kitabı',
    aciklama:
      'Bir FX opsiyon kitabının uçtan uca yönetimi: fiyatlama ve Greekler, ' +
      'gamma–theta ekonomisi, vol yüzeyi, tenor×delta bucket mimarisi, P&L ayrıştırması ' +
      've terste kalan kitabın toparlanma protokolü.',
    slugSirasi: ['opsiyon-book-yonetimi'],
    etiketler: ['fx', 'opsiyon', 'vol'],
  },
  {
    id: 'teknik-analiz',
    no: '03',
    baslik: 'Teknik analiz & fiyat aksiyonu',
    aciklama:
      'Doğrudan grafik üstünde çalışan çerçeveler: piyasa yapısı ve likidite (SMC), ' +
      'Fibonacci geometrisi ve XABCD katalogları (harmonik). Kural ve katalog metinleri ' +
      'takvimden bağımsızdır; tarihli sayı yalnız gerçek-veri vakalarında ve çıpa ' +
      'ibaresiyle geçer. Her ikisi de kanıt tartışmasıyla kapanır.',
    slugSirasi: ['smc-teknik-analiz', 'harmonik-patternler'],
    etiketler: ['teknik-analiz', 'smc', 'ict', 'harmonik', 'fibonacci', 'fiyat-aksiyonu'],
  },
  {
    id: 'olcum-rv',
    no: '04',
    baslik: 'Ölçüm & göreli değer',
    aciklama:
      'İki seri arasındaki ilişkiyi sayıya çevirmenin dersi: regresyon ve korelasyon, ' +
      "R²'nin hedge diline çevrilmesi, rich/cheap sinyali ve istatistiğin dürüst sınırları " +
      '(büyük N tuzağı, kointegrasyon ve HAC eksikleri).',
    slugSirasi: ['bloomberg-hra-korelasyon'],
    etiketler: ['korelasyon', 'regresyon', 'rv', 'bloomberg'],
  },
  {
    id: 'makro-tarih',
    no: '05',
    baslik: 'Makro & piyasa tarihi',
    aciklama:
      'Türkiye piyasalarının otuz yedi yılı, epizot epizot: kırılganlığın nerede ' +
      'biriktiği, şokun hangi sırayla dolaştığı ve politikanın hangi kolu çektiği — ' +
      'gerçek veriyle. Kural cümleleri göreli dille, epizot ölçümleri çıpalı tarihle.',
    slugSirasi: ['turkiye-piyasa-tarihi'],
    etiketler: ['makro', 'kriz', 'tcmb', 'tarih', 'türkiye', 'rezerv', 'enflasyon'],
  },
];

export const DIGER_GRUP: DersGrubu = {
  id: 'diger',
  no: '06',
  baslik: 'Diğer notlar',
  aciklama: 'Henüz bir hatta bağlanmamış tekil araştırma notları.',
};

/** Bir dersin hangi gruba düştüğünü çözer. */
export function grupBul(slug: string, etiketler: string[] = []): DersGrubu {
  const acik = GRUPLAR.find((g) => g.slugSirasi?.includes(slug));
  if (acik) return acik;
  const etiketli = GRUPLAR.find((g) => g.etiketler?.some((e) => etiketler.includes(e)));
  return etiketli ?? DIGER_GRUP;
}

/** Grup içi sıra: açık listedekiler listedeki sırayla, gerisi sona. */
export function grupIciSira(grup: DersGrubu, slug: string): number {
  const i = grup.slugSirasi?.indexOf(slug) ?? -1;
  return i === -1 ? 999 : i;
}

export const SEVIYE_ETIKET: Record<string, string> = {
  giris: 'Giriş',
  orta: 'Orta',
  ileri: 'İleri',
};
