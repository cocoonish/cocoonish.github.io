# TTO Trading — site

Türkiye makro & piyasa araştırmaları. Yayın: **https://cocoonish.github.io/**

Bu depo yalnız **sitenin kaynağıdır** (Astro + MDX). Veri hatları (Python), ham
araştırma dosyaları ve çalışma araçları ayrı bir **private** depoda durur; grafikler
orada üretilip `public/` altına kopyalanır.

```
src/content/projeler/     proje sayfaları   ·  src/content/arastirma/  ders sayfaları
public/projeler/<slug>/   üretilmiş grafikler + ozet.json (sayfa metnindeki güncel sayılar)
public/arastirma/<slug>/  ders grafikleri
src/components/           GrafikEmbed, VeriTablosu, Deger ve hesap araçları
```

Yerelde:

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # dist/
```

`main`'e her push GitHub Actions ile derlenip yayınlanır
(`.github/workflows/deploy.yml`).

---

İçerik bilgilendirme amaçlıdır; yatırım tavsiyesi değildir.
