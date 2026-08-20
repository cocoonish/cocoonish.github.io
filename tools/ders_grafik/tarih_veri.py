#!/usr/bin/env python3
"""Türkiye Piyasa Tarihi dersi — veri katmanı (EVDS + depo hatları + yfinance önbelleği).

Her seri diske CSV olarak yazılır (site/tools/ders_grafik/_tarih/). Bir kez çekilen
seri tekrar çekilmez; grafik üretimi böylece deterministik ve tekrarlanabilir olur.
Yeniden çekmek için ilgili CSV silinir ya da `python3 tarih_veri.py --tazele` koşulur.
"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

BURASI = Path(__file__).resolve().parent
ONBELLEK = BURASI / "_tarih"
ONBELLEK.mkdir(parents=True, exist_ok=True)
KOK = BURASI.parents[2]                       # depo kökü (TTO Trading/)
DEPO = KOK / "Aktarılacak Projeler"
YF_ONBELLEK = BURASI / "_veri"

EVDS_BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
_ANAHTAR_YOLLARI = [
    KOK / ".evds_key",
    DEPO / "TCMBNetRezerv" / ".evds_key",
]


def _anahtar() -> str:
    import os
    if os.environ.get("TTO_EVDS_KEY"):
        return os.environ["TTO_EVDS_KEY"].strip()
    for y in _ANAHTAR_YOLLARI:
        if y.exists():
            return y.read_text().strip()
    raise RuntimeError("EVDS anahtarı bulunamadı (TTO_EVDS_KEY ya da .evds_key)")


def _evds_parca(seriler: list[str], bas: str, bit: str) -> pd.DataFrame | None:
    """Tek çağrı. bas/bit: 'dd-mm-YYYY'. EVDS bir çağrıda ~1000 gözlem döndürür."""
    url = f"{EVDS_BASE}/series={'-'.join(seriler)}&startDate={bas}&endDate={bit}&type=csv"
    for deneme in range(4):
        try:
            r = requests.get(url, headers={"key": _anahtar()}, timeout=180)
            r.raise_for_status()
            return pd.read_csv(io.StringIO(r.text))
        except Exception as e:  # ağ hatası / geçici 5xx
            if deneme == 3:
                print(f"    ! EVDS hata ({seriler[0]} {bas}-{bit}): {e}")
                return None
            time.sleep(2 + 2 * deneme)
    return None


def evds(ad: str, seriler: list[str], bas: str, bit: str, adim_yil: int = 3) -> pd.DataFrame:
    """Önbellekli EVDS çekimi. `bas`/`bit`: 'YYYY-MM-DD'. Uzun pencereler parçalanır."""
    yol = ONBELLEK / f"{ad}.csv"
    if yol.exists():
        d = pd.read_csv(yol)
        d["dt"] = pd.to_datetime(d["dt"])
        return d
    s, e = pd.Timestamp(bas), pd.Timestamp(bit)
    parcalar = []
    cur = s
    while cur <= e:
        nxt = min(cur + pd.DateOffset(years=adim_yil) - pd.Timedelta(days=1), e)
        p = _evds_parca(seriler, cur.strftime("%d-%m-%Y"), nxt.strftime("%d-%m-%Y"))
        if p is not None and len(p):
            parcalar.append(p)
        cur = nxt + pd.Timedelta(days=1)
    if not parcalar:
        raise RuntimeError(f"EVDS boş döndü: {ad} {seriler}")
    d = pd.concat(parcalar, ignore_index=True)
    d.columns = [c.strip() for c in d.columns]
    d = d.drop_duplicates(subset=["Tarih"]).reset_index(drop=True)
    d["dt"] = _tarih_coz(d["Tarih"])
    kolon = {c: c.replace("TP_", "").replace("_", ".") for c in d.columns
             if c.startswith("TP_")}
    d = d.rename(columns=kolon)
    d = d.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)
    tut = ["dt"] + [c for c in d.columns if c not in ("dt", "Tarih", "UNIXTIME", "YEARWEEK")]
    d = d[tut]
    for c in d.columns:
        if c != "dt":
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d.to_csv(yol, index=False)
    print(f"  ✓ {ad}: {len(d)} gözlem  {d.dt.min().date()} → {d.dt.max().date()}")
    return d


def _tarih_coz(s: pd.Series) -> pd.Series:
    t = s.astype(str).str.strip()
    # EVDS biçimleri: 'dd-mm-YYYY' (günlük), 'YYYY-M' (aylık), 'YYYY-Ç' (çeyrek)
    if t.str.match(r"^\d{2}-\d{2}-\d{4}$").all():
        return pd.to_datetime(t, format="%d-%m-%Y")
    if t.str.match(r"^\d{4}-\d{1,2}$").all():
        return pd.to_datetime(t + "-01", format="%Y-%m-%d", errors="coerce")
    return pd.to_datetime(t, dayfirst=True, errors="coerce")


# --------------------------------------------------------------------- seriler
BUGUN = "2026-08-21"

TARIF = {
    # günlük / iş günü
    "kur":        (["TP.DK.USD.A.YTL"], "1990-01-01", BUGUN, 2),   # takvim günlük: 2 yıl < 1000 gözlem sınırı
    "bist":       (["TP.MK.F.BILESIK", "TP.MK.F.MALI"], "1990-01-01", BUGUN, 3),
    "gecelik":    (["TP.PY.P06.ON", "TP.PY.P04.ON", "TP.PY.P05.ON",
                    "TP.PY.P01.ON", "TP.PY.P02.ON", "TP.PY.P03.ON"], "1990-01-01", BUGUN, 3),
    "glp":        (["TP.PY.P01.LON", "TP.PY.P02.LON"], "2002-07-01", BUGUN, 5),
    "api":        (["TP.APIFON4", "TP.APIFON3", "TP.APIFON1.TOP"], "2011-01-03", BUGUN, 3),
    "tlref":      (["TP.BISTTLREF.ORAN"], "2018-12-28", BUGUN, 3),
    # aylık
    "tufe03":     (["TP.FG.J0"], "2003-01-01", BUGUN, 20),
    "tufe25":     (["TP.TUKFIY2025.GENEL"], "2005-01-01", BUGUN, 30),
    "tufe94":     (["TP.FG.T01"], "1994-01-01", "2004-12-31", 20),
    "tufe87":     (["TP.FG.A01"], "1987-01-01", "2004-12-31", 20),
    "ufe":        (["TP.TUFE1YI.T1"], "1990-01-01", BUGUN, 40),
    "polfaiz":    (["TP.BISPOLFAIZ.TUR", "TP.BISPOLFAIZ.ARG", "TP.BISPOLFAIZ.BRA",
                    "TP.BISPOLFAIZ.RUS", "TP.BISPOLFAIZ.MEX", "TP.BISPOLFAIZ.ZAF",
                    "TP.BISPOLFAIZ.IND", "TP.BISPOLFAIZ.IDN"], "1990-01-01", BUGUN, 40),
    "mevfaiz":    (["TP.MT210AGS.TRY.MT02", "TP.MT210AGS.TRY.MT06"], "2000-06-01", BUGUN, 30),
    # akım (yeni açılan mevduata uygulanan) ağırlıklı ortalama faiz — haftalık.
    # Ders metnindeki mevduat faizi okumaları bu serinin AY ORTALAMASIDIR.
    "mevfaiz_akim": (["TP.TRY.MT02", "TP.TRY.MT06"], "2000-06-01", BUGUN, 12),
    "mevduat":    (["TP.KM.F01", "TP.KM.F04", "TP.KM.F07", "TP.KM.F13",
                    "TP.KM.F19", "TP.KM.F22"], "1986-01-01", BUGUN, 40),
    "kkm":        (["TP.KKM.K1", "TP.KKM.K2", "TP.KKM.K3", "TP.KKM.K4"], "2021-12-01", BUGUN, 10),
    "krediler":   (["TP.KREDI.L001"], "2007-10-01", BUGUN, 20),
    "beklenti":   (["TP.ENFBEK.PKA12ENF", "TP.BEK.S01.D.M"], "2013-01-01", BUGUN, 15),
    # haftalık
    # Stand-By Cari 2A Net Uluslararası Rezervler (bin TL) — Bölüm 4'ün rezerv
    # ölçümleri bu seriden, aynı tarihli USD alış kuruyla çevrilerek üretilir.
    "sb_nir":     (["TP.AB.N06"], "2010-01-01", BUGUN, 5),
    "yabanci_eski": (["TP.PYUK1", "TP.PYUK2", "TP.PYUK3", "TP.PYUK4"], "2005-01-01", "2021-08-06", 8),
}


def seri(ad: str) -> pd.DataFrame:
    s, b, e, a = TARIF[ad]
    return evds(ad, s, b, e, a)


# ------------------------------------------------------------------ depo hattı
def depo_haftalik_rezerv() -> pd.DataFrame:
    d = pd.read_csv(DEPO / "TCMBNetRezerv" / "haftalik_rezerv.csv")
    d["dt"] = pd.to_datetime(d["Tarih"])
    return d.sort_values("dt").reset_index(drop=True)


def depo_gunluk_rezerv() -> pd.DataFrame:
    d = pd.read_csv(DEPO / "TCMBNetRezerv" / "gunluk.csv")
    d["dt"] = pd.to_datetime(d["Tarih"])
    return d.sort_values("dt").reset_index(drop=True)


def depo_yabanci() -> pd.DataFrame:
    d = pd.read_csv(DEPO / "ForeignHoldings" / "foreign_holdings_data.csv")
    d["dt"] = pd.to_datetime(d["Tarih"])
    return d.sort_values("dt").reset_index(drop=True)


def depo_reer() -> pd.DataFrame:
    d = pd.read_csv(DEPO / "TRYREER" / "reer_analysis_data.csv")
    d["dt"] = pd.to_datetime(d["Dönem"])
    return d.sort_values("dt").reset_index(drop=True)


def depo_ihale() -> pd.DataFrame:
    d = pd.read_csv(DEPO / "hazineihrac" / "hazine_ihale_verileri.csv")
    d.columns = [c.replace("﻿", "").strip() for c in d.columns]
    d["dt"] = pd.to_datetime(d["İhale Tarihi"], format="%d.%m.%Y", errors="coerce")
    return d.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)


# -------------------------------------------------------------------- yfinance
def _yf_tarih(s: pd.Series) -> pd.Series:
    """yfinance indeksi borsa saat diliminde tz-aware gelir; UTC'ye çevirmek tarihi
    bir gün geri kaydırır (00:00 İstanbul = önceki gün 21:00 UTC). Yerel duvar saatini
    koruyup güne yuvarlıyoruz."""
    t = pd.to_datetime(s, errors="coerce")
    try:
        if getattr(t.dt, "tz", None) is not None:
            t = t.dt.tz_localize(None)
    except (TypeError, AttributeError):
        t = pd.to_datetime(s, utc=True).dt.tz_convert("Europe/Istanbul").dt.tz_localize(None)
    return t.dt.normalize()


def yf(sembol: str, bas: str, bit: str) -> pd.DataFrame | None:
    """Önbellekli günlük OHLC. Önce _veri/ (mevcut ders önbelleği), sonra _tarih/."""
    guv = sembol.replace("=", "_").replace("^", "").replace(".", "_")
    eski = YF_ONBELLEK / f"{guv}_1d.csv"
    yeni = ONBELLEK / f"yf_{guv}.csv"
    if yeni.exists():
        d = pd.read_csv(yeni)
        d["dt"] = pd.to_datetime(d["dt"])
        return d
    ham = None
    if eski.exists():
        d = pd.read_csv(eski)
        sut = "Date" if "Date" in d.columns else d.columns[0]
        d["dt"] = _yf_tarih(d[sut])
        if d["dt"].min() <= pd.Timestamp(bas) + pd.Timedelta(days=7):
            ham = d
    if ham is None:
        try:
            import yfinance as yfin
            h = yfin.Ticker(sembol).history(start=bas, end=bit, interval="1d",
                                            auto_adjust=False)
            if h is None or not len(h):
                print(f"    ! yfinance boş: {sembol}")
                return None
            h = h.reset_index()
            h["dt"] = _yf_tarih(h["Date"])
            ham = h
        except Exception as e:
            print(f"    ! yfinance hata {sembol}: {e}")
            return None
    tut = ["dt"] + [c for c in ("Open", "High", "Low", "Close", "Adj Close", "Volume")
                    if c in ham.columns]
    out = ham[tut].dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)
    out.to_csv(yeni, index=False)
    print(f"  ✓ yf {sembol}: {len(out)} gün  {out.dt.min().date()} → {out.dt.max().date()}")
    return out


if __name__ == "__main__":
    if "--tazele" in sys.argv:
        for p in ONBELLEK.glob("*.csv"):
            p.unlink()
    for ad in TARIF:
        try:
            d = seri(ad)
            print(f"{ad:16s} {len(d):6d}  {d.dt.min().date()} → {d.dt.max().date()}  "
                  f"{[c for c in d.columns if c != 'dt']}")
        except Exception as e:
            print(f"{ad:16s} HATA: {e}")
