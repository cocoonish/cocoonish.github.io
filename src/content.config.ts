import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const ortakSema = z.object({
  title: z.string(),
  description: z.string(),
  pubDate: z.coerce.date(),
  updatedDate: z.coerce.date().optional(),
  tags: z.array(z.string()).default([]),
  // taslak → sitede "hazırlanıyor" rozetiyle görünür; arsiv → listede sona düşer
  durum: z.enum(['aktif', 'taslak', 'arsiv']).default('taslak'),
  kaynak: z.string().optional(), // veri kaynağı, ör. "TCMB EVDS + IRFCL"
  guncelleme: z.string().optional(), // güncelleme sıklığı, ör. "haftalık (Cuma)"

  // ── Liste kartları için (hesaplanamayan, yazarın koyduğu bilgiler) ──
  // Kelime/grafik/pratik sayıları ELLE YAZILMAZ; src/lib/ders.ts gövdeden sayar.
  // Aşağıdakiler metinden çıkarılamadığı için frontmatter'da durur.
  /** Kartta görünen tek cümlelik "bu ders ne öğretir" özeti. */
  ozet: z.string().optional(),
  /** Zorluk: hattın giriş dersi mi, ortası mı, ileri halkası mı? */
  seviye: z.enum(['giris', 'orta', 'ileri']).optional(),
  /** Ön koşul dersler (slug listesi) — kartta bağlantı olarak gösterilir. */
  onkosul: z.array(z.string()).default([]),
});

const projeler = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/projeler' }),
  // Pano bir ölçüm yüzeyidir: künyesi kaynağını ve yayım ritmini yazar
  // (projeler/YAZIM.md). İkisi burada ZORUNLU — rehberin "zorunlu" dediği
  // şey şemada isteğe bağlıydı ve hiçbir kapı yokluğunu görmüyordu.
  schema: ortakSema.extend({ kaynak: z.string().min(1), guncelleme: z.string().min(1) }),
});

// İndikatörler: bir dersin öğrettiği yöntemin çalışan karşılığı. Ders değil,
// araç — ama kaynağı DERSTİR: her eşik hangi bölümden geldiğini yazar.
const indikatorler = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/indikatorler' }),
  schema: ortakSema.extend({
    /** Hangi dersten türetildi (slug) — kaynağı gizlenmez. */
    kaynakDers: z.string().min(1),
    /**
     * İndikatörün PARÇALARI. Bir indikatör birden çok panele dağılabilir ve
     * o zaman birden çok Pine dosyası taşır; ikisi TEK sistem olarak
     * kullanılıyorsa tek sayfada durur. Sıra, sayfadaki okuma sırasıdır.
     */
    parcalar: z
      .array(
        z.object({
          /** TradingView panel yerleşimi. */
          panel: z.enum(['fiyat', 'alt']),
          /** İndirilebilir Pine dosyasının site köküne göreli yolu. */
          dosya: z.string().min(1),
          /** Parçanın TradingView'de görünen adı. */
          ad: z.string().min(1),
        }),
      )
      .min(1),
    /** Pine Script sürümü. */
    pine: z.string().default('v6'),
  }),
});

const arastirma = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/arastirma' }),
  schema: ortakSema,
});

// Analiz: tek bir piyasa gelişmesini derinlemesine inceleyen yazılar. Bültenden
// farkı kapsam değil DERİNLİK: bülten günün tamamını özetler, analiz tek bir
// olayı mekanizmasına, tarihsel emsaline ve fiyat etkisine kadar açar.
const analiz = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/analiz' }),
  schema: ortakSema.extend({
    /** VERİ ÇIPASI: yazının hangi güne kadar veri kullandığı (künyede 'Veri' hücresi).
     *  Yayın günüyle aynı olmak zorunda değil; ödemeler dengesi 6–8 hafta gecikir. */
    veriTarihi: z.coerce.date().optional(),
    /** Yayımlanmış bir sayının düzeltme kaydı — bültenle aynı sözleşme; /duzeltmeler/ toplar. */
    duzeltmeler: z
      .array(z.object({
        tarih: z.string(),
        alan: z.string(),
        eski: z.string(),
        yeni: z.string(),
        sebep: z.string().optional(),
      }))
      .default([]),
  }),
});

export const collections = { projeler, arastirma, analiz, indikatorler };
