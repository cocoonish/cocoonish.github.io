#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sayfa ↔ hat sözleşmesi sınavı (CI'da koşturulabilir).

Bu sınav, "hat koştu ama sayfa yalan söylüyor" sınıfı hataları yakalar. Dokuz
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
  (6) KaTeX — her formül ayrıştırılabiliyor mu? (rehype-katex düşmez, ham basar)
  (7) <Deger> anahtarları TÜM koleksiyonlarda — analiz ve araştırma
      sayfaları da aynı sözleşmeyi kullanıyor; kural 1 onları görmüyordu.
  (8) DERLENMİŞ ÇIKTI — dist/ içinde KaTeX hatası, ham <Deger> etiketi ya
      da çözülmemiş MDX yorumu var mı? Kaynağı sınayan ölçütlerin
      göremediği tek şey: okurun gerçekte gördüğü sayfa.

Koşum:  python3 site/tools/sayfa_sinavi.py
Çıkış:  0 = geçti · 1 = en az bir sınav düştü
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parents[2]

# (sayfa slug'ı, proje klasörü)
# HAT LİSTESİ ELLE TUTULMAZ, guncelle.py'nin kendi kütüğünden TÜRETİLİR.
# Elle tutulan liste altı hat taşıyordu ve sınav geri kalanını hiç görmüyordu:
# hazine-ihrac sayfasında <Deger> ile çağrılan on altı anahtar ozet.json'da
# YOKTU, yani noktalı çizgiyle "canlı" görünen o sayılar aylardır statik
# yedeklerinde donmuştu — ve sınav bunu bulmak için yazılmış olmasına rağmen
# o sayfaya hiç bakmıyordu. Yeni bir hat eklendiğinde de aynı boşluk
# tekrarlanırdı. Kaynak tek: hattın kendisi.
def _hatlar() -> list[tuple[str, str]]:
    # Modül sys.path'ten NORMAL import edilir. spec_from_file_location ile
    # yüklemek dataclass çözümlemesini kırıyor: dataclasses tip adlarını
    # sys.modules[cls.__module__] üzerinden arıyor ve sentetik adla yüklenen
    # modül orada olmadığı için AttributeError veriyor.
    import sys
    if str(KOK) not in sys.path:
        sys.path.insert(0, str(KOK))
    import guncelle
    return [(h.slug, h.klasor) for h in guncelle.HATLAR]


HATLAR = _hatlar()

# KURAL 1 (anahtar varlığı) HER hatta koşar: ölçütü tek ve kesin — sayfada
# çağrılan anahtar ozet.json'da ya vardır ya yoktur, yorum payı sıfırdır.
#
# Kural 2–5 yalnız aşağıdaki hatlarda DÜŞÜRÜR. Sebebi dürüstçe şu: bu ölçütler
# o altı hattın çıktı düzenine göre yazıldı ve liste genişletilince altı hatta
# birden YANLIŞ ALARM verdiler (ör. dosya kümesi ölçütü, çıktısını farklı adla
# kopyalayan hatlarda hepsini "farklı" sayıyor). Yanlış alarmla düşen bir
# denetim, kapatılan bir denetimdir. Ölçütler o hatlar için de düzeltilene
# kadar orada BİLGİ olarak basılır, kapı olmaz.
TAM_SINAV = {"kredi-parasal", "fonlama-likidite", "enflasyon",
             "odemeler-dengesi", "butce-borc", "dibs-verim-egrisi"}

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

    def bulgu(slug: str, mesaj: str) -> None:
        """Kural 2–5 bulgusu: TAM_SINAV'daki hatta kapı, diğerlerinde bilgi."""
        if slug in TAM_SINAV:
            hata.append(mesaj)
        else:
            print(f"  (bilgi, kapı değil) {mesaj}")
    TUM_MDX = sorted((KOK / "site/src/content").rglob("*.mdx"))
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
            bulgu(slug, f"{slug}: ÇIPLAK OYNAK SAYI (kural 5): "
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
        # BİR HATTIN FİGÜRÜ PROJE SAYFASINDA DURMAK ZORUNDA DEĞİL. İTO kanadının
        # üç figürü Enflasyon hattı tarafından üretiliyor ama analiz yazısında
        # gömülü; ölçüt yalnız projeler/<slug>.mdx'e baktığı için üçünü birden
        # "MDX'te bulunamadı" diye düşürüyordu. Aranan şey figürün hangi
        # dosyada olduğu değil, SİTEDE gömülü olduğu yerdeki yüksekliğin
        # üretimdekiyle aynı olması. Arama bu yüzden bütün içerik ağacında.
        yj = proje / "cikti/yukseklikler.json"
        if yj.exists():
            y = json.loads(yj.read_text(encoding="utf-8"))
            sapan = []
            for dosya, h in y.items():
                kalip = re.compile(r'src="/projeler/' + re.escape(slug) + "/"
                                   + re.escape(dosya)
                                   + r'"[\s\S]{0,400}?yukseklik=\{(\d+)\}')
                m = kalip.search(mdx)
                nerede = f"projeler/{slug}"
                if not m:
                    for baska in TUM_MDX:
                        m = kalip.search(baska.read_text(encoding="utf-8"))
                        if m:
                            nerede = f"{baska.parent.name}/{baska.stem}"
                            break
                if not m:
                    sapan.append(f"{dosya}: hiçbir sayfada gömülü değil")
                elif int(m.group(1)) != h:
                    sapan.append(f"{dosya}: {nerede}'de {m.group(1)} ≠ üretim {h}")
            if sapan:
                bulgu(slug, f"{slug}: yükseklik sapması → " + " · ".join(sapan))
            print(f"  (3) yükseklik: {len(y)} figür · sapma {len(sapan)}")

        # (4) dosya kümesi + ev stili
        uret = {p.name for p in (proje / "cikti").glob("*.html")}
        site = {p.name for p in (KOK / "site/public/projeler" / slug).glob("*.html")}
        if uret != site:
            bulgu(slug, f"{slug}: üretim ile site dosya kümesi farklı: "
                        f"{sorted(uret ^ site)}")
        stilsiz = [n for n in sorted(site)
                   if "tto-ev-stili" not in (KOK / "site/public/projeler" / slug / n)
                   .read_text(encoding="utf-8", errors="ignore")]
        if stilsiz:
            bulgu(slug, f"{slug}: ev stili bloğu YOK: {stilsiz}")
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
            bulgu(slug, f"{slug}: YAN YANA PANEL: " + ", ".join(yanyana))
        print(f"  (5) panel düzeni: yan yana {len(yanyana)}")

    # (6) KaTeX — FORMÜLLER AYRIŞTIRILIYOR MU?
    # rehype-katex bir formülü ayrıştıramadığında derlemeyi DÜŞÜRMEZ; hatayı
    # sayfaya kırmızı ham LaTeX olarak basar ve `npm run build` yeşil biter.
    # 31.08.2026'da `\textbf{%3,3}` yazıldı — LaTeX'te % yorum karakteri olduğu
    # için süslü parantez yutuldu ve dört formül sayfada ham metin olarak
    # yayımlandı. Kusuru derleme değil OKUR gördü. Denetim buraya kondu ki
    # sınavı koşturan herkes aynı soruyu sorsun.
    # (7) <Deger> ANAHTARLARI — YALNIZ PROJE SAYFALARINDA DEĞİL, HER SAYFADA.
    # Kural 1 yalnız site/src/content/projeler/<slug>.mdx'e bakıyordu. Ama
    # <Deger> sözleşmesi koleksiyondan bağımsız: bileşen ozet.json'u
    # /projeler/<proje>/ genel yolundan çekiyor ve analiz/araştırma sayfaları
    # da onu kullanıyor. Büyüme yazısı projeler'den analiz'e taşındığı gün
    # sınavın görüş alanından da çıkmıştı; borçlanma ve İTO yazıları hiç
    # girmemişti. Donan bir sayının hangi klasörde durduğu okur için bir şey
    # ifade etmiyor — denetim de ayırmamalı.
    print("\n▶ Tüm sayfalarda <Deger> anahtarları")
    # Tarayıcı /projeler/<slug>/ozet.json'u çeker; sınavın bakması gereken
    # dosya da odur. Bazı hatların çalışma klasöründeki ozet.json .gitignore'da
    # (Büyüme, El Niño) — proje klasörüne bakmak onları "bilinmeyen proje"
    # sanıyordu. Önce SİTEDEKİ kopya, yoksa proje klasörü.
    ozetler: dict[str, dict] = {}
    ozet_yok: list[str] = []
    for slug, klasor in HATLAR:
        for oj in (KOK / "site/public/projeler" / slug / "ozet.json",
                   KOK / klasor / "ozet.json"):
            if oj.exists():
                try:
                    ozetler[slug] = json.loads(oj.read_text(encoding="utf-8"))
                except Exception as ex:
                    hata.append(f"{slug}: ozet.json okunamadı ({type(ex).__name__})")
                break
        else:
            ozet_yok.append(slug)
    if ozet_yok:
        print(f"  (ozet.json bulunamayan hat: {', '.join(ozet_yok)})")
    icerik = KOK / "site/src/content"
    n_sayfa = n_kul = 0
    for mdx_yol in sorted(icerik.rglob("*.mdx")):
        # projeler/ zaten kural 1'de tam kapsamla sınandı; burada geri kalanlar.
        if mdx_yol.parent.name == "projeler":
            continue
        metin = mdx_yol.read_text(encoding="utf-8")
        kul = re.findall(r'<Deger\s+proje="([^"]+)"\s+anahtar="([^"]+)"', metin)
        if not kul:
            continue
        n_sayfa += 1
        n_kul += len(kul)
        ad = f"{mdx_yol.parent.name}/{mdx_yol.stem}"
        bilinmez = sorted({pr for pr, _ in kul if pr not in ozetler})
        if [x for x in bilinmez if x not in ozet_yok]:
            hata.append(f"{ad}: bilinmeyen proje niteliği: "
                        f"{[x for x in bilinmez if x not in ozet_yok]}")
        eksik = sorted({f"{pr}.{an}" for pr, an in kul
                        if pr in ozetler and an not in ozetler[pr]})
        if eksik:
            hata.append(f"{ad}: ozet.json'da olmayan anahtar: {eksik}")
        print(f"  {ad}: {len(kul)} kullanım · eksik {len(eksik)}"
              + (f" · bilinmeyen proje {bilinmez}" if bilinmez else ""))
    print(f"  toplam {n_sayfa} sayfa · {n_kul} <Deger> kullanımı")

    print("\n▶ KaTeX")
    kt = KOK / "site/tools/katex_sinavi.mjs"
    if not kt.exists():
        print("  – katex_sinavi.mjs yok, atlandı")
    else:
        r = subprocess.run(["node", str(kt)], cwd=str(KOK / "site"),
                           capture_output=True, text=True)
        cikti = [x for x in r.stdout.splitlines() if x.strip()]
        for satir in cikti[:14]:
            print("  " + satir)
        if r.returncode != 0:
            hata.append("KaTeX: formül ayrıştırılamadı (ayrıntı yukarıda)")
        elif r.returncode != 0 or not cikti:
            print("  – node/katex yok, atlandı")

    # (8) DERLENMİŞ ÇIKTIYA BAK — OKURUN GÖRDÜĞÜ ŞEY BUDUR.
    # 6. ve 7. ölçütler kaynağı sınıyor ve ikisi de yeşil bitiyordu; sayfada
    # ise üç formül bloğu ve ARDINDAKİ 108 <Deger> etiketi ham metin olarak
    # duruyordu. Çünkü kusur ne KaTeX'te ne anahtar listesindeydi: MDX iki
    # satıra yayılan bir `$$` bloğunun delimiter'ını yanlış eşliyor ve açılan
    # span belgenin sonuna kadar uzuyor. Kaynağı ne kadar iyi sınarsak
    # sınayalım, ÇIKTIYA bakmayan bir denetim bu sınıfı göremez.
    #
    # Bu ölçüt dist/ varsa koşar (npm run build sonrası). Yoksa atlanır ve
    # bunu SÖYLER — sessizce geçmek, koşmayan bir denetimi geçmiş saymaktır.
    print("\n▶ Derlenmiş çıktı (dist/)")
    dist = KOK / "site/dist"
    if not dist.exists():
        print("  – dist/ yok (önce `npm run build`), ÖLÇÜT KOŞMADI")
    else:
        sayfa = sorted(dist.rglob("index.html"))
        kirik = []
        for h in sayfa:
            metin = h.read_text(encoding="utf-8", errors="replace")
            n_kt = metin.count("katex-error")
            # Ham <Deger> etiketi: MDX bileşeni çözememiş, metne kaçmış.
            n_dg = metin.count("&lt;Deger") + metin.count("&#x3C;Deger")
            # Çözülmemiş MDX yorumu: aynı sınıf kusurun ikinci izi.
            n_yr = metin.count("sinav-muaf")
            if n_kt or n_dg or n_yr:
                kirik.append((h.relative_to(dist).parent.as_posix() or ".",
                              n_kt, n_dg, n_yr))
        for yol, a, b, c in kirik:
            hata.append(f"dist/{yol}: KaTeX hatası {a} · ham <Deger> {b} · "
                        f"çözülmemiş MDX yorumu {c} — sayfa ham metin basıyor")
        print(f"  {len(sayfa)} sayfa tarandı · kırık {len(kirik)}")

    # ---------------------------------------------------------------- (9)
    # YAPIM GÜNLÜĞÜ DİLİ. Sayfa okura yazılır, kendi yapımına değil.
    # "Bu yazının ilk sürümünde şu hata vardı", "önceki sürümde şöyle
    # yazıyordu", "kodda şu düzeltildi" gibi cümleler okurun kararını
    # değiştirmiyor; bulguyu taşıyan cümle kalır, süreç anlatısı gitmelidir.
    # Aynı sınıfa dosya/anahtar adları da girer: ozet.json, metrik.py,
    # itp_* anahtarı — okurun elinde olmayan şeylerdir.
    # ÖLÇÜT NEDEN GEREKLİ: bu dil bir kez temizlendi ve temizlik yalnız
    # hatırlandığı sürece sürer. Kural araca konmazsa bir sonraki yazıda
    # geri gelir.
    print("\n▶ Okur dili (okura değil kendine anlatan cümleler)")
    # KALIP LİSTESİ BURADA DEĞİL. Aynı kural bülten ve tweet katmanlarında da
    # uygulanıyor; üç ayrı liste bir gün sessizce ayrışırdı ve hangisinin neyi
    # gördüğü kimsenin aklında kalmazdı. Tek tanım: ortak/okur_dili.py.
    sys.path.insert(0, str(KOK / "ortak"))
    import okur_dili
    icerik = sorted((KOK / "site/src/content").rglob("*.mdx"))
    bulgu = 0
    for yol in icerik:
        for aile, esl, sat in okur_dili.tara(yol.read_text(encoding="utf-8")):
            hata.append(f"{aile} — {yol.relative_to(KOK / 'site/src/content')}"
                        f":{sat}: {esl!r}")
            bulgu += 1
    print(f"  {len(icerik)} sayfa tarandı · bulgu {bulgu}")

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
