#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Al Brooks fiyat hareketi dersi — gerçek piyasa verisi önbelleği.

Brooks bar bar okuma öğretir; ders de bunu gerçek barlarla göstermeli. Bu script
gerekli enstrüman/zaman dilimi çiftlerini bir kez indirir ve `_veri/` altına CSV
olarak yazar. Grafik üreticileri SADECE bu önbellekten okur:

  · Deterministiklik: ders metnindeki her sayı (bar sayısı, seviye, ölçülmüş hareket
    hedefi) grafikteki barlara sadık kalır. Her koşuda yeniden indirilseydi metin
    bir hafta sonra grafikle çelişirdi — bu depoda "sessiz bayatlama" sınıfı hata.
  · İçgün veri (5m/15m) yfinance'te yalnız SON 60 GÜN için var; önbellek olmadan
    ders birkaç ay sonra yeniden üretilemez hâle gelirdi. CSV depoda tutulur.

Kullanım:
  python3 brooks_veri.py            # eksikleri indir (var olanlara dokunmaz)
  python3 brooks_veri.py --tazele   # hepsini yeniden indir (pencereler kayar!)
  python3 brooks_veri.py --liste    # önbellekte ne var, göster
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "_veri"
VERI.mkdir(parents=True, exist_ok=True)

# (ticker, aralık, period) — period yfinance'in izin verdiği azami pencere.
# 5m: 60 gün · 15m: 60 gün · 1h: 730 gün · 1d: sınırsız.
# Brooks'un kanonik enstrümanı E-mini S&P (ES); ders ayrıca BIST, USDTRY, altın ve
# BTC ile Türk okura tanıdık örnekler verir. BTC 7/24 işlem gördüğü için "bar dizisi
# kesintisiz" örneklerinde (mikro kanal, barbwire) en temiz malzemedir.
ISTEK = [
    ("ES=F", "5m", "60d"),      # E-mini S&P 500 vadeli — Brooks'un ana grafiği
    ("ES=F", "15m", "60d"),
    ("ES=F", "1h", "730d"),
    ("ES=F", "1d", "10y"),
    ("XU100.IS", "15m", "60d"),  # BIST 100
    ("XU100.IS", "1h", "730d"),
    ("XU100.IS", "1d", "10y"),
    ("USDTRY=X", "1h", "730d"),
    ("USDTRY=X", "1d", "10y"),
    ("GC=F", "5m", "60d"),       # altın vadeli
    ("GC=F", "15m", "60d"),
    ("GC=F", "1d", "10y"),
    ("BTC-USD", "5m", "60d"),
    ("BTC-USD", "15m", "60d"),
    ("EURUSD=X", "1h", "730d"),
    ("^GSPC", "1d", "25y"),      # S&P 500 endeksi — günlük/haftalık bağlam
]


def ad(ticker: str, aralik: str) -> str:
    return f"{ticker.replace('=', '_').replace('^', '')}_{aralik}.csv"


def indir(ticker: str, aralik: str, period: str) -> pd.DataFrame | None:
    try:
        import yfinance as yf
    except ImportError:
        print("  ✗ yfinance kurulu değil:  pip install yfinance")
        return None
    try:
        ham = yf.download(ticker, period=period, interval=aralik,
                          progress=False, auto_adjust=False)
    except Exception as e:                                    # noqa: BLE001
        print(f"  ✗ {ticker} {aralik}: {type(e).__name__} {e}")
        return None
    if ham is None or len(ham) < 100:
        print(f"  ✗ {ticker} {aralik}: yetersiz veri ({0 if ham is None else len(ham)} bar)")
        return None
    if isinstance(ham.columns, pd.MultiIndex):
        ham.columns = [c[0] for c in ham.columns]
    df = pd.DataFrame({"o": ham["Open"].values, "h": ham["High"].values,
                       "l": ham["Low"].values, "c": ham["Close"].values,
                       "v": ham["Volume"].values if "Volume" in ham else 0})
    ts = pd.to_datetime(ham.index)
    if getattr(ts, "tz", None) is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)     # her şey UTC-naive
    df["ts"] = ts
    return df.dropna(subset=["o", "h", "l", "c"]).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tazele", action="store_true")
    ap.add_argument("--liste", action="store_true")
    a = ap.parse_args()

    if a.liste:
        for t, i, _ in ISTEK:
            y = VERI / ad(t, i)
            if y.exists():
                d = pd.read_csv(y, parse_dates=["ts"])
                print(f"  ✓ {ad(t,i):22s} {len(d):6d} bar  {d.ts.iloc[0]:%Y-%m-%d} → {d.ts.iloc[-1]:%Y-%m-%d}")
            else:
                print(f"  – {ad(t,i):22s} yok")
        return 0

    yeni = atlanan = dusen = 0
    for t, i, p in ISTEK:
        y = VERI / ad(t, i)
        if y.exists() and not a.tazele:
            atlanan += 1
            continue
        print(f"  indiriliyor: {t} {i} ({p})")
        df = indir(t, i, p)
        if df is None:
            dusen += 1
            continue
        df.to_csv(y, index=False)
        print(f"    ✓ {len(df)} bar  {df.ts.iloc[0]:%Y-%m-%d %H:%M} → {df.ts.iloc[-1]:%Y-%m-%d %H:%M}")
        yeni += 1
    print(f"\n  {yeni} yeni · {atlanan} zaten vardı · {dusen} düştü")
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
