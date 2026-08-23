#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brooks_ortak.py birim testleri —  python3 brooks_ortak_test.py

Altı ayrı grafik dosyası bu katmanı paylaşıyor; biri yardımcıyı "düzeltirken"
diğerlerinin figürünü sessizce bozmasın diye kurallar burada sabitlenir.
Özellikle bar sayımı (H1/H2…) kaynaktaki tanıma göre çivilenmiştir.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brooks_ortak as B                                        # noqa: E402

hata = 0


def kontrol(ad, kosul, ek=""):
    global hata
    print(("  ✓ " if kosul else "  ✗ ") + ad + (f"  {ek}" if ek and not kosul else ""))
    hata += 0 if kosul else 1


print("bar sayımı (Brooks: yükselemeyen bar geri çekilmeyi başlatır; önceki barın")
print("yükseğini aşan bar H1'dir; bacak yeni tepe yapınca sayaç sıfırlanır)")
boga = [(100, 101.0, 99.8, 100.9), (100.9, 102.1, 100.7, 102.0), (102.0, 103.5, 101.9, 103.4),
        (103.4, 103.40, 102.6, 102.7), (102.7, 103.20, 102.5, 103.1), (103.1, 103.30, 103.0, 103.25),
        (103.2, 103.25, 102.4, 102.5), (102.5, 103.00, 102.3, 102.9), (102.9, 103.40, 102.8, 103.35),
        (103.35, 104.2, 103.3, 104.1), (104.1, 104.15, 103.6, 103.7), (103.7, 104.30, 103.6, 104.2)]
d = B.df_yap(boga)
kontrol("boğa: H1(5) → H2(8) → yeni tepe → H1(11)",
        B.bar_say(d, "bull") == [(5, "H1"), (8, "H2"), (11, "H1")], str(B.bar_say(d, "bull")))

ayi = [(100, 100.2, 99.0, 99.1), (99.1, 99.2, 98.0, 98.1), (98.1, 98.2, 97.0, 97.1),
       (97.1, 97.9, 97.00, 97.8), (97.8, 98.0, 97.20, 97.3), (97.3, 97.5, 97.10, 97.2),
       (97.2, 97.9, 97.15, 97.8), (97.8, 97.9, 97.30, 97.4), (97.4, 97.5, 97.05, 97.1),
       (97.1, 97.2, 96.50, 96.6)]
kontrol("ayı: L1 → L2 sırası", [e for _, e in B.bar_say(B.df_yap(ayi), "bear")][:2] == ["L1", "L2"])

print("bar kurma")
try:
    B.df_yap([(100, 99, 98, 101)])          # yüksek, gövdenin altında → geçersiz
    kontrol("geçersiz bar yakalanıyor", False, "hata vermedi")
except ValueError:
    kontrol("geçersiz bar yakalanıyor", True)
b = B.bar(100, 103, ust=0.5, alt=0.3)
kontrol("bar(): gövde+kuyruk geometrisi", b == (100, 103.5, 99.7, 103), str(b))

print("ölçülmüş hareket ve işlem kümesi")
import plotly.graph_objects as go                               # noqa: E402
d2 = B.df_yap(B.yol_uret(60, 100, 0.05, 0.4, tohum=7))
f = go.Figure(B.mumlar(d2))
hedef = B.olculmus_hareket(f, 5, float(d2.l[5]), 25, float(d2.h[25]), 55)
beklenen = float(d2.h[25]) + (float(d2.h[25]) - float(d2.l[5]))
kontrol("ölçülmüş hareket = bacak boyu kadar ileri", abs(hedef - beklenen) < 1e-9)
r = B.islem(f, d2, sinyal=30, yon="bull", hedefler=(float(d2.h[30]) + 5,))
kontrol("risk = giriş − stop > 0", r["risk"] > 0)
kontrol("R katı doğru", abs(r["r"][0] - abs(float(d2.h[30]) + 5 - r["giris"]) / r["risk"]) < 1e-9)

print("yol_uret determinizmi")
kontrol("aynı tohum → aynı barlar", B.yol_uret(20, 100, 0.1, 0.5, 3) == B.yol_uret(20, 100, 0.1, 0.5, 3))

print("gerçek veri önbelleği")
for t, a in (("ES=F", "5m"), ("ES=F", "1d"), ("XU100.IS", "1h"), ("BTC-USD", "5m")):
    df = B.yukle(t, a)
    kontrol(f"{t} {a} okunuyor", df is not None and len(df) > 500,
            f"{0 if df is None else len(df)} bar")

print(f"\n{'TÜM TESTLER GEÇTİ' if not hata else str(hata) + ' TEST DÜŞTÜ'}")
sys.exit(1 if hata else 0)
