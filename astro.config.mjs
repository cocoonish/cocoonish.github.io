// @ts-check
import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

// https://astro.build/config
export default defineConfig({
  // Yayın adresi. Kanonik bağlantı, site haritası, RSS ve bağlantı önizleme
  // kartları bu kökten kurulur; kendi alan adı alınırsa yalnız burası değişir.
  site: 'https://cocoonish.github.io',
  integrations: [
    mdx(),
    sitemap({
      // Tarihli sayı sayfalarında lastmod = adresteki gün; dizinler günlük/haftalık değişir.
      serialize(item) {
        const m = item.url.match(/\/(bulten|teknik)\/(\d{4}-\d{2}-\d{2})\/$/);
        if (m) return { ...item, lastmod: `${m[2]}T00:00:00Z`, changefreq: 'never' };
        if (/\/(bulten|teknik)\/$|\/$/.test(item.url) && !/\/(analiz|projeler|arastirma)\//.test(item.url))
          return { ...item, changefreq: item.url.endsWith('/teknik/') ? 'weekly' : 'daily' };
        return item;
      },
    }),
  ],
  markdown: {
    remarkPlugins: [remarkMath],
    // strict: false — KaTeX, \text{} içindeki Türkçe aksanlı harfleri
    // ("gövde", "bütçe", "çıkış") varsayılan 'warn' kipinde şikâyet eder ama
    // doğru render eder. Türkçe bir sitede bu uyarı her derlemede onlarca satır
    // gürültü üretip GERÇEK KaTeX hatalarını görünmez kılıyordu.
    rehypePlugins: [[rehypeKatex, { strict: false }]],
  },
});
