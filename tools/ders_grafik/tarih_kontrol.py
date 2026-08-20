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

# ---------------------------------------------------------------------------
# Metin–grafik denetimi: "Şekil N nasıl okunur" notlarındaki sayılar grafiğin
# ürettiği değerlerle uyuşuyor mu? Bu bölüm her izin uç değerlerini ve son
# gözlemini basar; MDX'teki iddialar bu dökümle karşılaştırılır.
#     python3 tarih_kontrol.py --degerler [dosya_parcasi]
# ---------------------------------------------------------------------------
def _dizi(v):
    """Plotly dizisi: düz liste ya da {dtype, bdata} (base64 typed array)."""
    if isinstance(v, dict) and "bdata" in v:
        import base64
        import numpy as np
        return np.frombuffer(base64.b64decode(v["bdata"]),
                             dtype=np.dtype(v.get("dtype", "f8"))).tolist()
    return v


def degerler(filtre: str | None = None) -> None:
    for yol in sorted(DIZIN.glob("*.html")):
        if filtre and filtre not in yol.name:
            continue
        ham = yol.read_text()
        m = re.search(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\]),\s*(\{.*?\}),\s*\{"responsive"',
                      ham, re.S)
        if not m:
            continue
        izler = json.loads(m.group(1))
        yerlesim = json.loads(m.group(2))
        print(f"\n=== {yol.name} ===")
        for k in sorted(yerlesim):
            if re.fullmatch(r"annotations", k):
                for a in yerlesim[k]:
                    t = (a.get("text") or "").strip()
                    if t and not a.get("xref", "").startswith("paper"):
                        print(f"  [anotasyon] {t}")
        for iz in izler:
            y = _dizi(iz.get("y") or iz.get("close"))
            if y is None or not len(y):
                continue
            sy = [v for v in y if isinstance(v, (int, float))]
            if not sy:
                continue
            x = _dizi(iz.get("x") or [])
            imin, imax = sy.index(min(sy)), sy.index(max(sy))

            def et(i):
                try:
                    return str(x[list(y).index(sy[i])])[:10]
                except Exception:
                    return "?"
            print(f"  {iz.get('name','?'):46s} min {min(sy):10.2f} ({et(imin)})  "
                  f"max {max(sy):10.2f} ({et(imax)})  son {sy[-1]:10.2f}")



if "--degerler" in sys.argv:
    _i = sys.argv.index("--degerler")
    degerler(sys.argv[_i + 1] if len(sys.argv) > _i + 1 else None)
    sys.exit(0)


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
