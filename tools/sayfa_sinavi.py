#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sayfa ↔ hat sözleşmesi sınavı (CI'da koşturulabilir).

Bu sınav, "hat koştu ama sayfa yalan söylüyor" sınıfı hataları yakalar. Beş
bölüm var; her biri düzenin bir kuralına karşılık gelir:

  (1) <Deger> anahtarları — MDX'te çağrılan her anahtar ozet.json'da var mı?
      Yoksa sayfada STATİK yedek görünür ve veri tazelendikçe donar.
  (2) ÇIPLAK OYNAK SAYI — ozet.json'daki oynak bir değerin Türkçe biçimi,
      MDX'te <Deger> ile sarılmadan düz metin olarak geçiyor mu? (CLAUDE.md
      kural 5'in ihlali: bir sonraki tazelemede o cümle donar.)
  (3) Şekil yüksekliği — MDX'teki yukseklik={} değeri, üretimin
      cikti/yukseklikler.json'daki gerçek script height'i ile aynı mı?
  (4) Dosya kümesi — üretimdeki figürler siteye birebir kopyalanmış mı ve
      hepsinde ev stili bloğu var mı?
  (5) Panel düzeni — paneller ALT ALTA mı? (yan yana panel yasak)

Koşum:  python3 site/tools/sayfa_sinavi.py
Çıkış:  0 = geçti · 1 = en az bir sınav düştü
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).resolve().parents[2]

# (sayfa slug'ı, proje klasörü)
HATLAR = [
    ("kredi-parasal", "Aktarılacak Projeler/Kredi"),
    ("fonlama-likidite", "Aktarılacak Projeler/Fonlama"),
    ("enflasyon", "Aktarılacak Projeler/Enflasyon"),
    ("odemeler-dengesi", "Aktarılacak Projeler/OdemelerDengesi"),
    ("butce-borc", "Aktarılacak Projeler/Butce"),
    ("dibs-verim-egrisi", "Aktarılacak Projeler/DIBS"),
]

# (2) için: yalnız GERÇEKTEN oynak sayılar taranır. Tarih/oran metinleri, tek
# haneli sayımlar ve yöntemsel sabitler taramaya girmez — yoksa "13 haftalık"
# gibi metodolojik ifadeler yanlış alarm üretir.
TARAMA_ALT_SINIR = 2.0        # |v| bu değerin altındaysa taranmaz
TARAMA_ONDALIK = (1, 2)       # kaç ondalıkla yazılmış olabileceği


def tr(v: float, ondalik: int) -> str:
    m = f"{v:,.{ondalik}f}"
    return (m.replace(",", " ").replace(".", ",").replace(" ", ".")
             .replace("-", "−"))


def deger_disi(mdx: str) -> str:
    """MDX'ten <Deger …>…</Deger> bloklarını, kod bloklarını ve satır içi
    kodu çıkar — geriye kalan, gerçekten çıplak duran metindir."""
    s = re.sub(r"<Deger\b[\s\S]*?</Deger>", " ", mdx)
    s = re.sub(r"```[\s\S]*?```", " ", s)
    s = re.sub(r"`[^`]*`", " ", s)
    s = re.sub(r"\$\$[\s\S]*?\$\$", " ", s)      # KaTeX blokları
    s = re.sub(r"\$[^$\n]*\$", " ", s)           # satır içi KaTeX
    return s


# Bir sayı gerçekten TARİHSEL SABİT olabilir (başka bir kurumun yayımladığı,
# değişmeyecek bir alıntı). O zaman muafiyet, sayının yanına MDX'in kendi
# içinde yazılır ki gerekçe sayıdan ayrı düşmesin:
#     {/* sinav-muaf: agirlik_kayma_09 — TCMB Blog alıntısı, tarihsel sabit */}
MUAF_KALIP = re.compile(r"\{/\*\s*sinav-muaf:\s*([A-Za-z0-9_]+)")


def main() -> int:
    hata: list[str] = []
    for slug, klasor in HATLAR:
        proje = KOK / klasor
        mp = KOK / "site/src/content/projeler" / f"{slug}.mdx"
        oj = proje / "ozet.json"
        if not mp.exists() or not oj.exists():
            print(f"  – {slug}: sayfa ya da ozet.json yok, atlandı")
            continue
        mdx = mp.read_text(encoding="utf-8")
        o = json.loads(oj.read_text(encoding="utf-8"))
        print(f"\n▶ {slug}")

        # (1) anahtar varlığı
        kul = re.findall(r'<Deger\s+proje="([^"]+)"\s+anahtar="([^"]+)"', mdx)
        eksik = sorted({a for p, a in kul if p == slug and a not in o})
        yanlis = sorted({p for p, _ in kul if p != slug})
        if eksik:
            hata.append(f"{slug}: ozet.json'da olmayan anahtar: {eksik}")
        if yanlis:
            hata.append(f"{slug}: yanlış proje niteliği: {yanlis}")
        print(f"  (1) <Deger>: {len(kul)} kullanım · eksik {len(eksik)} · "
              f"yanlış proje {len(yanlis)}")

        # (2) çıplak oynak sayı
        disi = deger_disi(mdx)
        muaf = set(MUAF_KALIP.findall(mdx))
        ciplak = []
        for k, v in o.items():
            if k in muaf:
                continue
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            if abs(v) < TARAMA_ALT_SINIR:
                continue
            for d in TARAMA_ONDALIK:
                metin = tr(float(v), d)
                if len(metin.replace(".", "").replace(",", "")) < 3:
                    continue          # iki haneli sayılar çok yaygın, taranmaz
                if re.search(r"(?<![\d.,])" + re.escape(metin) + r"(?![\d.,])", disi):
                    ciplak.append(f"{k}={metin}")
                    break
        if ciplak:
            hata.append(f"{slug}: ÇIPLAK OYNAK SAYI (kural 5): "
                        + ", ".join(sorted(set(ciplak))))
        print(f"  (2) çıplak oynak sayı: {len(set(ciplak))}"
              + (f" · muaf: {sorted(muaf)}" if muaf else ""))

        # (2b) statik yedek ↔ canlı değer — BİLGİ (düşürmez)
        # Yedek metin JSON yüklenene kadar (ve JS kapalıyken) görünen sayıdır.
        # Veri her tazelendiğinde doğal olarak kayar, o yüzden hattı DURDURMAZ;
        # ama sapma sayısı büyürse sayfanın "ilk bakış" hâli eskimiş demektir.
        sapan_yedek = []
        for m in re.finditer(r'<Deger\s+proje="' + re.escape(slug)
                             + r'"\s+anahtar="([^"]+)"([^>]*)>([^<]*)</Deger>', mdx):
            a, nit, yedek = m.group(1), m.group(2), m.group(3).strip()
            v = o.get(a)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            dm = re.search(r"ondalik=\{(\d+)\}", nit)
            bek = tr(float(v), int(dm.group(1)) if dm else 1)
            if "isaret=" in nit and v > 0:
                bek = "+" + bek
            if yedek != bek:
                sapan_yedek.append(f"{a}: '{yedek}' ≠ '{bek}'")
        print(f"  (2b) statik yedek sapması (bilgi): {len(set(sapan_yedek))}"
              + ("" if not sapan_yedek else "  → " + ", ".join(sorted(set(sapan_yedek))[:6])))

        # (3) şekil yüksekliği
        yj = proje / "cikti/yukseklikler.json"
        if yj.exists():
            y = json.loads(yj.read_text(encoding="utf-8"))
            sapan = []
            for dosya, h in y.items():
                m = re.search(r'src="/projeler/' + re.escape(slug) + "/"
                              + re.escape(dosya) + r'"[\s\S]{0,400}?yukseklik=\{(\d+)\}', mdx)
                if not m:
                    sapan.append(f"{dosya}: MDX'te bulunamadı")
                elif int(m.group(1)) != h:
                    sapan.append(f"{dosya}: MDX {m.group(1)} ≠ üretim {h}")
            if sapan:
                hata.append(f"{slug}: yükseklik sapması → " + " · ".join(sapan))
            print(f"  (3) yükseklik: {len(y)} figür · sapma {len(sapan)}")

        # (4) dosya kümesi + ev stili
        uret = {p.name for p in (proje / "cikti").glob("*.html")}
        site = {p.name for p in (KOK / "site/public/projeler" / slug).glob("*.html")}
        if uret != site:
            hata.append(f"{slug}: üretim ile site dosya kümesi farklı: "
                        f"{sorted(uret ^ site)}")
        stilsiz = [n for n in sorted(site)
                   if "tto-ev-stili" not in (KOK / "site/public/projeler" / slug / n)
                   .read_text(encoding="utf-8", errors="ignore")]
        if stilsiz:
            hata.append(f"{slug}: ev stili bloğu YOK: {stilsiz}")
        print(f"  (4) dosya kümesi: üretim {len(uret)} · site {len(site)} · "
              f"ev stilsiz {len(stilsiz)}")

        # (5) panel düzeni — yan yana panel YASAK
        yanyana = []
        for n in sorted(site):
            t = (KOK / "site/public/projeler" / slug / n).read_text(
                encoding="utf-8", errors="ignore")
            sol = {round(float(a), 4) for a, _ in re.findall(
                r'"xaxis\d*":\s*\{[^{}]*?"domain":\s*\[([\d.]+),\s*([\d.]+)\]', t)}
            if len(sol) > 1:
                yanyana.append(f"{n} (sol uçlar {sorted(sol)})")
        if yanyana:
            hata.append(f"{slug}: YAN YANA PANEL: " + ", ".join(yanyana))
        print(f"  (5) panel düzeni: yan yana {len(yanyana)}")

    print()
    if hata:
        for h in hata:
            print("  ✗ " + h)
        print(f"\nSAYFA SINAVI DÜŞTÜ ({len(hata)} bulgu).")
        return 1
    print("SAYFA SINAVI GEÇTİ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
