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
  schema: ortakSema,
});

const arastirma = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/arastirma' }),
  schema: ortakSema,
});

export const collections = { projeler, arastirma };
