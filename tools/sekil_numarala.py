#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ders sayfasındaki şekil numaralarını BELGE SIRASINA göre yeniden numaralar.

Sorun: SMC dersi derinleştirilirken yeni grafikler mevcut numaraların ardından
(29…57) üretildi ama yeni alt bölümler mevcut bölümlerin İÇİNE eklendi. Sonuç:
okur sayfayı yukarıdan aşağı okurken "Şekil 29"u "Şekil 01"den önce görüyor.

Bu araç: (1) MDX'teki GrafikEmbed'leri belge sırasıyla okur, (2) 01..N yeniden
numaralar, (3) HTML dosyalarını yeni numarayla adlandırır (slug korunur),
(4) MDX'teki src/no ve metindeki "Şekil NN" atıflarını (aralık ve listeler dahil)
günceller, (5) grafik scriptlerindeki dosya adlarını günceller.

Kullanım:
  python3 sekil_numarala.py --slug smc-teknik-analiz --kok "<repo>" [--uygula]
Varsayılan KURU KOŞU: hiçbir dosyaya dokunmaz, ne yapacağını basar.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

GRAFIK_RE = re.compile(
    r'<GrafikEmbed\s+[^>]*?src="(?P<src>/arastirma/(?P<slug>[^/"]+)/(?P<dosya>[^"]+))"[^>]*?>',
    re.S)
NO_RE = re.compile(r'(no=")(?P<no>[0-9]+b?)(")')
# "Şekil 12", "Şekil 01–05", "Şekil 06 ve 07", "Şekil 12/13", "Şekil 16b"
ATIF_RE = re.compile(
    r'(Şekil|ŞEKİL|şekil)(\s+)(\d{1,2}b?)((?:\s*(?:–|—|-|/|,|·|\s+ve\s+|\s+ile\s+)\s*\d{1,2}b?)*)')
SAYI_RE = re.compile(r'\d{1,2}b?')


def dosya_slug(ad: str) -> str:
    """'29_ipda_20_40_60.html' → 'ipda_20_40_60.html' (numara öneki atılır)."""
    m = re.match(r'^\d{1,2}b?_(.*)$', ad)
    return m.group(1) if m else ad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--kok", required=True)
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--script", nargs="*", default=[],
                    help="dosya adı içeren grafik scriptleri (kökten göreli)")
    a = ap.parse_args()

    kok = Path(a.kok)
    mdx = kok / "site/src/content/arastirma" / f"{a.slug}.mdx"
    kls = kok / "site/public/arastirma" / a.slug
    metin = mdx.read_text(encoding="utf-8")

    # 1) Belge sırasıyla grafikler
    kayitlar = []
    for m in GRAFIK_RE.finditer(metin):
        blok = m.group(0)
        nm = NO_RE.search(blok)
        kayitlar.append({"dosya": m.group("dosya"),
                         "eski_no": nm.group("no") if nm else None,
                         "bas": m.start(), "son": m.end()})
    if not kayitlar:
        print("GrafikEmbed bulunamadı"); return 1

    harita: dict[str, str] = {}          # eski_no → yeni_no
    dosya_harita: dict[str, str] = {}    # eski dosya adı → yeni dosya adı
    for i, k in enumerate(kayitlar, 1):
        yeni = f"{i:02d}"
        k["yeni_no"] = yeni
        if k["eski_no"]:
            if k["eski_no"] in harita and harita[k["eski_no"]] != yeni:
                print(f"UYARI: {k['eski_no']} iki kez geçiyor"); return 1
            harita[k["eski_no"]] = yeni
        k["yeni_dosya"] = f"{yeni}_{dosya_slug(k['dosya'])}"
        dosya_harita[k["dosya"]] = k["yeni_dosya"]

    degisen = [k for k in kayitlar if k["eski_no"] != k["yeni_no"]]
    print(f"{len(kayitlar)} grafik · {len(degisen)} numara değişiyor")
    for k in degisen[:80]:
        print(f"  {k['eski_no']:>3s} → {k['yeni_no']}   {k['dosya']} → {k['yeni_dosya']}")

    # 2) MDX: src ve no güncelle (bloklar tersten, indeksler kaymasın)
    yeni_metin = metin
    for k in sorted(kayitlar, key=lambda x: -x["bas"]):
        blok = yeni_metin[k["bas"]:k["son"]]
        b2 = blok.replace(f'/arastirma/{a.slug}/{k["dosya"]}',
                          f'/arastirma/{a.slug}/{k["yeni_dosya"]}')
        b2 = NO_RE.sub(lambda mm: mm.group(1) + k["yeni_no"] + mm.group(3), b2)
        yeni_metin = yeni_metin[:k["bas"]] + b2 + yeni_metin[k["son"]:]

    # 3) Metindeki "Şekil NN" atıfları — GrafikEmbed blokları hariç
    bloklar = [(m.start(), m.end()) for m in GRAFIK_RE.finditer(yeni_metin)]

    def blok_icinde(i):
        return any(b <= i < s for b, s in bloklar)

    def atif_cevir(m):
        if blok_icinde(m.start()):
            return m.group(0)
        bas = harita.get(m.group(3), m.group(3))
        kuyruk = SAYI_RE.sub(lambda s: harita.get(s.group(0), s.group(0)), m.group(4) or "")
        return f"{m.group(1)}{m.group(2)}{bas}{kuyruk}"

    yeni_metin, n_atif = ATIF_RE.subn(atif_cevir, yeni_metin)
    print(f"metin içi 'Şekil …' atıfı işlendi: {n_atif}")

    # 4) Denetimler
    for k in kayitlar:
        if not (kls / k["dosya"]).exists():
            print(f"HATA: kaynak dosya yok: {k['dosya']}"); return 1
    diskte = {p.name for p in kls.glob("*.html")}
    gomulu = {k["dosya"] for k in kayitlar}
    if diskte - gomulu:
        print(f"UYARI: gömülmemiş HTML: {sorted(diskte - gomulu)}")

    if not a.uygula:
        print("\n(kuru koşu — --uygula ile yazılır)")
        return 0

    # 5) Dosyaları geçici adla iki aşamada taşı (çakışma olmasın)
    gecici = {}
    for eski, yeni in dosya_harita.items():
        if eski == yeni:
            continue
        gp = kls / f"__gecici__{yeni}"
        shutil.move(str(kls / eski), str(gp))
        gecici[gp] = kls / yeni
    for gp, hedef in gecici.items():
        shutil.move(str(gp), str(hedef))
    print(f"{len(gecici)} dosya yeniden adlandırıldı")

    mdx.write_text(yeni_metin, encoding="utf-8")
    print(f"yazıldı: {mdx}")

    # 6) Grafik scriptlerindeki dosya adları
    for s in a.script:
        sp = kok / s
        if not sp.exists():
            print(f"UYARI: script yok: {s}"); continue
        t = sp.read_text(encoding="utf-8")
        n = 0
        for eski, yeni in dosya_harita.items():
            e, y = eski[:-5], yeni[:-5]          # .html'siz gövde
            if e in t:
                t = t.replace(e, y); n += 1
        sp.write_text(t, encoding="utf-8")
        print(f"{s}: {n} dosya adı güncellendi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
