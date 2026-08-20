// @ts-check
import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

// https://astro.build/config
export default defineConfig({
  // TODO: kendi domainini aldığında burayı güncelle
  site: 'https://cocoonish.github.io',
  integrations: [mdx(), sitemap()],
  markdown: {
    remarkPlugins: [remarkMath],
    // strict: false — KaTeX, \text{} içindeki Türkçe aksanlı harfleri
    // ("gövde", "bütçe", "çıkış") varsayılan 'warn' kipinde şikâyet eder ama
    // doğru render eder. Türkçe bir sitede bu uyarı her derlemede onlarca satır
    // gürültü üretip GERÇEK KaTeX hatalarını görünmez kılıyordu.
    rehypePlugins: [[rehypeKatex, { strict: false }]],
  },
});
