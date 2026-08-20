#!/usr/bin/env python3
"""Türkiye Piyasa Tarihi grafik seti — çıktı denetimi.

Her HTML için: boyut > 15 KB · ev stili enjekte edilmiş · TEK SÜTUN (yan yana panel yok)
· panel sayısı · figür yüksekliği · iz sayısı · boş iz var mı · tarih aralığı.
"""
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
DIZIN = KOK / "public" / "arastirma" / "turkiye-piyasa-tarihi"

hata = 0
print(f"{'dosya':34s} {'KB':>6s} {'sütun':>5s} {'panel':>5s} {'yük.':>5s} {'iz':>4s}  durum")
for yol in sorted(DIZIN.glob("*.html")):
    ham = yol.read_text()
    kb = yol.stat().st_size / 1024
    m = re.search(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\]),\s*(\{.*?\}),\s*\{"responsive"', ham, re.S)
    if not m:
        print(f"{yol.name:34s} {kb:6.0f}  — figür JSON okunamadı"); hata += 1; continue
    izler = json.loads(m.group(1))
    yerlesim = json.loads(m.group(2))
    sol = {round(v["domain"][0], 3) for k, v in yerlesim.items()
           if re.fullmatch(r"xaxis\d*", k) and "domain" in v}
    panel = len([k for k in yerlesim if re.fullmatch(r"yaxis\d*", k)
                 and "domain" in yerlesim[k]])
    sutun = max(1, len(sol))
    yuk = yerlesim.get("height", 0)
    bos = [iz.get("name", "?") for iz in izler
           if not (iz.get("y") or iz.get("close") or iz.get("x"))]
    sorun = []
    if kb < 15:
        sorun.append("BOYUT<15KB")
    if sutun != 1:
        sorun.append(f"ÇOK SÜTUN({sutun})")
    if "tto-ev-stili" not in ham:
        sorun.append("EV STİLİ YOK")
    if bos:
        sorun.append("BOŞ İZ: " + ", ".join(bos[:3]))
    if sorun:
        hata += 1
    print(f"{yol.name:34s} {kb:6.0f} {sutun:5d} {panel:5d} {yuk:5d} {len(izler):4d}  "
          + ("· ".join(sorun) if sorun else "tamam"))

print(f"\n{'HATA VAR' if hata else 'hepsi tamam'} — {hata} dosyada sorun")
sys.exit(1 if hata else 0)
