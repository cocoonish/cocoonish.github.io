#!/usr/bin/env python3
"""Türkiye Piyasa Tarihi — vaka dersi · grafik seti üreticisi.

Tek komut:  python3 site/tools/ders_grafik/tarih_grafikler.py
Çıktı:      site/public/arastirma/turkiye-piyasa-tarihi/NN_ad.html

Kurallar (ders standardı):
  · Sentetik seri YOK. Her seri ya EVDS'ten (`tarih_veri.py` önbelleği) ya depodaki
    bir hattın ürettiği CSV'den ya da yfinance önbelleğinden gelir.
  · Paneller ALT ALTA: make_subplots(rows=N, cols=1). Yan yana panel yok.
  · Pencereler PİNLİ (sabit tarih aralıkları) → çıktı deterministik.
  · Her grafikte epizot tarihleri gölgeli bant / dikey çizgi + etiketle işaretli.
  · Başlık altında "Çıpa: <pencere>" ibaresi.
  · Veri bulunamayan gösterge UYDURULMAZ; grafik atlanır ve raporlanır.

Ev stili son rötuşu: python3 site/tools/plotly_stil.py public/arastirma/turkiye-piyasa-tarihi/*.html
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import tarih_veri as tv

warnings.filterwarnings("ignore")

KOK = Path(__file__).resolve().parents[2]           # site/
CIKTI = KOK / "public" / "arastirma" / "turkiye-piyasa-tarihi"
CIKTI.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------- palet
TEAL = "#0f766e"      # kur / ana seri
BORDO = "#7f1d1d"     # faiz / stres
ALTIN = "#b45309"     # enflasyon
MAVI = "#1d4ed8"      # hisse
MOR = "#6d28d9"       # rezerv
TURUNCU = "#ea580c"   # akım / müdahale
YESIL = "#15803d"     # olumlu / normalleşme
GRI = "#6b7280"
MUREKKEP = "#211b12"
BANT = "#9a7327"


def rgba(hex_: str, a: float) -> str:
    h = hex_.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


URETILEN: list[tuple[str, str, str]] = []   # (dosya, başlık, pencere)
ATLANAN: list[str] = []


# ------------------------------------------------------------------- veri
_ONBELLEK: dict[str, pd.DataFrame] = {}


def S(ad: str) -> pd.DataFrame:
    """EVDS serisi, dt indeksli."""
    if ad not in _ONBELLEK:
        d = tv.seri(ad).set_index("dt")
        _ONBELLEK[ad] = d
    return _ONBELLEK[ad]


def Y(sembol: str, bas="2005-01-01", bit="2026-08-21") -> pd.DataFrame | None:
    """yfinance günlük, dt indeksli."""
    k = f"yf::{sembol}"
    if k not in _ONBELLEK:
        d = tv.yf(sembol, bas, bit)
        _ONBELLEK[k] = None if d is None else d.set_index("dt")
    return _ONBELLEK[k]


def D(fn) -> pd.DataFrame:
    k = f"depo::{fn.__name__}"
    if k not in _ONBELLEK:
        _ONBELLEK[k] = fn().set_index("dt")
    return _ONBELLEK[k]


def kur() -> pd.Series:
    return S("kur")["DK.USD.A.YTL"].dropna()


def gecelik() -> pd.Series:
    """Bankalararası para piyasası gecelik ağırlıklı ortalama basit faiz (%)."""
    return S("gecelik")["PY.P06.ON"].dropna()


def aofm() -> pd.Series:
    return S("api")["APIFON4"].dropna()


def tufe_yoy() -> pd.Series:
    """TÜFE yıllık değişim (%), üç endeks eklemlenerek: 1987=100 (1988–2003),
    2003=100 (2004–2005), 2025=100 (2006→). Yıllık değişim ölçekten bağımsız
    olduğu için endeksleri seviyede zincirlemeye gerek yoktur."""
    parcalar = []
    for ad, kol, bas, bit in [("tufe87", "FG.A01", "1988-01-01", "2003-12-31"),
                              ("tufe03", "FG.J0", "2004-01-01", "2005-12-31"),
                              ("tufe25", "TUKFIY2025.GENEL", "2006-01-01", "2026-12-31")]:
        s = S(ad)[kol].dropna()
        parcalar.append((100 * (s / s.shift(12) - 1)).loc[bas:bit])
    return pd.concat(parcalar).sort_index()


def ufe_yoy() -> pd.Series:
    s = S("ufe")["TUFE1YI.T1"].dropna()
    return 100 * (s / s.shift(12) - 1)


def politika() -> pd.Series:
    """TCMB politika faizi, aylık (BIS derlemesi, EVDS TP.BISPOLFAIZ.TUR).
    EVDS'te günlük/karar tarihli bir politika faizi serisi yoktur; karar günleri
    grafiklerde dikey çizgiyle ayrıca işaretlenir."""
    return S("polfaiz")["BISPOLFAIZ.TUR"].dropna()


def mevduat_faizi() -> pd.Series:
    """3 aya kadar vadeli TL mevduat faizi, stok, aylık (%)."""
    return S("mevfaiz")["MT210AGS.TRY.MT02"].dropna()


def dth_payi() -> pd.Series:
    """Döviz tevdiat hesaplarının toplam mevduat içindeki payı (%), aylık."""
    d = S("mevduat")
    kol = ["KM.F01", "KM.F04", "KM.F07", "KM.F13", "KM.F19", "KM.F22"]
    t = d[kol].dropna(how="all")
    return 100 * t["KM.F19"] / t[kol].sum(axis=1)


def kmdh_payi() -> pd.Series:
    d = S("mevduat")
    kol = ["KM.F01", "KM.F04", "KM.F07", "KM.F13", "KM.F19", "KM.F22"]
    t = d[kol].dropna(how="all")
    return 100 * t["KM.F22"] / t[kol].sum(axis=1)


def yabanci_akim() -> pd.DataFrame:
    """Yurt dışı yerleşiklerin haftalık net akımı (mn USD): hisse + DİBS.
    2005–2021 arşiv serisi (TP.PYUK3/4) ile 2020→ yeni seri (ForeignHoldings hattı)
    tarih ekseninde birleştirilir; çakışan haftalarda yeni seri esas alınır."""
    eski = S("yabanci_eski")[["PYUK3", "PYUK4"]].dropna(how="all")
    eski.columns = ["hisse", "dibs"]
    yeni = D(tv.depo_yabanci)[["Hisse", "DIBS"]]
    yeni.columns = ["hisse", "dibs"]
    kes = yeni.index.min()
    return pd.concat([eski.loc[:kes - pd.Timedelta(days=1)], yeni]).sort_index()


# ------------------------------------------------------------------ epizotlar
EPIZOT = [
    ("1994-01-01", "1994-04-30", "1994 krizi"),
    ("2000-11-17", "2000-12-29", "Kasım 2000"),
    ("2001-02-19", "2001-04-30", "Şubat 2001"),
    ("2008-09-15", "2009-03-31", "küresel kriz"),
    ("2013-05-22", "2013-09-18", "taper"),
    ("2013-12-17", "2014-02-28", "Ara 13 – Oca 14"),
    ("2016-07-15", "2016-09-30", "Tem 2016"),
    ("2018-08-01", "2018-09-30", "Ağustos 2018"),
    ("2019-03-20", "2019-04-05", "Mart 2019"),
    ("2020-03-01", "2020-11-20", "2020 erimesi"),
    ("2021-11-18", "2021-12-24", "Aralık 2021"),
    ("2023-06-01", "2023-09-30", "Haz 2023 dönüşü"),
    ("2025-03-19", "2025-04-30", "Mart 2025"),
    ("2026-02-28", "2026-04-30", "Şubat 2026"),
]


def epizot_bantlari(fig, bas=None, bit=None, etiket_satiri=1, satir_sayisi=1,
                    yalnizca=None, renk=BANT, a=0.10):
    """Epizot pencerelerini gölgeli dikey bant olarak çizer. Etiket yalnızca
    `etiket_satiri`ndaki panele yazılır (çok panelli figürde tekrar olmasın diye)."""
    for b, e, ad in EPIZOT:
        if yalnizca and ad not in yalnizca:
            continue
        b_, e_ = pd.Timestamp(b), pd.Timestamp(e)
        if bas is not None and e_ < pd.Timestamp(bas):
            continue
        if bit is not None and b_ > pd.Timestamp(bit):
            continue
        if bas is not None:
            b_ = max(b_, pd.Timestamp(bas))
        if bit is not None:
            e_ = min(e_, pd.Timestamp(bit))
        for r in range(1, satir_sayisi + 1):
            if r == etiket_satiri:
                fig.add_vrect(x0=b_, x1=e_, fillcolor=rgba(renk, a), line_width=0,
                              layer="below", row=r, col=1,
                              annotation_text=ad, annotation_position="top left",
                              annotation=dict(font=dict(size=9, color=GRI), textangle=-90,
                                              xanchor="left", yanchor="top"))
            else:
                fig.add_vrect(x0=b_, x1=e_, fillcolor=rgba(renk, a), line_width=0,
                              layer="below", row=r, col=1)


def dikey(fig, x, etiket="", row=1, renk=BORDO, dash="dash", konum="top left",
          aci=-90, boyut=9.5, satir_sayisi=None, y_konum=1.0):
    """Olay çizgisi. `satir_sayisi` verilirse çizgi bütün panellerde çizilir,
    etiket yalnız `row`da kalır.

    Not: `add_vline(annotation_text=…)` tarih eksenli figürlerde plotly'nin
    açıklama konumlandırıcısını kırıyor (x0 == x1 iken iki Timestamp toplanıyor).
    Bu yüzden çizgi `add_shape`, etiket ayrı bir `add_annotation` ile kuruluyor."""
    x = pd.Timestamp(x)
    satirlar = range(1, satir_sayisi + 1) if satir_sayisi else [row]
    for r in satirlar:
        fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, yref="y domain",
                      line=dict(color=renk, width=1.2, dash=dash), layer="below",
                      row=r, col=1)
    if etiket:
        fig.add_annotation(x=x, y=y_konum, yref="y domain", yanchor="top", xanchor="left",
                           text=" " + etiket, showarrow=False, textangle=aci,
                           font=dict(size=boyut, color=renk), row=row, col=1)


def not_(fig, x, y, metin, row=1, renk=MUREKKEP, ok=True, boyut=10.5,
         ax=0, ay=-34, xanchor="center", kutu=True):
    fig.add_annotation(x=x, y=y, text=metin, showarrow=ok, arrowhead=2, arrowsize=1,
                       arrowwidth=1.1, arrowcolor=renk, ax=ax, ay=ay,
                       font=dict(size=boyut, color=renk), xanchor=xanchor,
                       bgcolor="rgba(255,255,255,0.82)" if kutu else None,
                       bordercolor=rgba(renk, 0.35) if kutu else None,
                       borderwidth=0.8 if kutu else 0, borderpad=3,
                       row=row, col=1)


def isaret(fig, x, y, metin="", row=1, renk=BORDO, boyut=9, sembol="circle-open"):
    fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers", showlegend=False,
                             marker=dict(symbol=sembol, size=boyut + 3, color=renk,
                                         line=dict(width=2, color=renk)),
                             hovertemplate=f"{metin}<extra></extra>"), row=row, col=1)


def sifir_cizgisi(fig, row=1, renk=MUREKKEP):
    fig.add_hline(y=0, line=dict(color=rgba(renk, 0.55), width=1.4), row=row, col=1)


KUR_NOTU = ("TCMB gösterge kuru günde tek değerdir ve seans içi ekstremleri göstermez; "
            "bülten tarihi t, kotasyon t−1 15:30")


def duzen(fig, baslik: str, cipa: str, h: int, alt: str = "", legend_y=-0.06):
    # EVDS gösterge kuru çizilen her figürde kaydırma/tanım uyarısı altyazıya eklenir.
    parcalar = [str(getattr(iz, "name", "") or "") for iz in fig.data]
    parcalar += [str(getattr(a, "text", "") or "") for a in fig.layout.annotations]
    parcalar += [str(getattr(ax.title, "text", "") or "") for ax in fig.select_yaxes()]
    adlar = " ".join(parcalar).lower()
    if any(im in adlar for im in ("usd/try", "gösterge kuru", "resmî kur", "usd baz",
                                 "dolar baz", "usdtry")) and KUR_NOTU not in alt:
        alt = (alt + " · " if alt else "") + KUR_NOTU
    ust = f"{baslik}<br><sup style='color:#6b6355'>Çıpa: {cipa}"
    if alt:
        ust += f" · {alt}"
    ust += "</sup>"
    fig.update_layout(
        title=dict(text=ust, x=0.01, xanchor="left", font=dict(size=15, color=MUREKKEP)),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(family="-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
                  size=12.5, color=MUREKKEP),
        legend=dict(orientation="h", yanchor="top", y=legend_y, xanchor="left", x=0,
                    font=dict(size=11), bgcolor="rgba(255,255,255,0)"),
        margin=dict(l=66, r=76, t=96, b=104), height=h, hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#efe9dc", linecolor="#d8cfba",
                     rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="#efe9dc", linecolor="#d8cfba")


def panel_basliklari(fig, boyut=12):
    ust = {round(tuple(ax.domain)[1], 4) for ax in fig.select_yaxes() if ax.domain is not None}
    for a in fig.layout.annotations:
        if getattr(a, "yanchor", None) == "bottom" and round(getattr(a, "y", 0) or 0, 4) in ust:
            a.font = a.font or {}
            a.font.size = boyut


def kaydet(fig, ad: str, baslik: str, pencere: str):
    panel_basliklari(fig)
    yol = CIKTI / f"{ad}.html"
    fig.write_html(str(yol), include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    URETILEN.append((yol.name, baslik, pencere))
    print(f"  ✓ {yol.name}")


def kes(s: pd.Series | pd.DataFrame, bas, bit):
    return s.loc[pd.Timestamp(bas):pd.Timestamp(bit)]


def endeksle(s: pd.Series, taban_tarih) -> pd.Series:
    """Verilen tarihte (ya da ondan önceki son gözlemde) 100 olacak şekilde ölçekler."""
    t = pd.Timestamp(taban_tarih)
    onceki = s.loc[:t]
    if not len(onceki):
        return s * np.nan
    return 100 * s / onceki.iloc[-1]


def cizgi(fig, s: pd.Series, ad: str, renk: str, row=1, w=1.8, dash=None,
          eksen="y", ikincil=False, sekil=None, doldur=None, goster=True, birim=""):
    fig.add_trace(go.Scatter(x=s.index, y=s.values, name=ad, mode="lines",
                             line=dict(color=renk, width=w, dash=dash, shape=sekil or "linear"),
                             fill=doldur, showlegend=goster,
                             hovertemplate="%{y:.2f}" + birim + "<extra>" + ad + "</extra>"),
                  row=row, col=1, secondary_y=ikincil)


def sutun(fig, s: pd.Series, ad: str, renk: str, row=1, goster=True, birim="",
          renkler=None, genislik=None):
    fig.add_trace(go.Bar(x=s.index, y=s.values, name=ad,
                         marker=dict(color=renkler if renkler is not None else renk,
                                     line=dict(width=0)),
                         width=genislik, showlegend=goster,
                         hovertemplate="%{y:.2f}" + birim + "<extra>" + ad + "</extra>"),
                  row=row, col=1)


# ==========================================================================
#  01 — Dersin haritası
# ==========================================================================
def g01():
    bas, bit = "1990-01-01", "2026-08-21"
    k = kes(kur(), bas, bit)
    g = kes(gecelik(), bas, bit)
    t = kes(tufe_yoy(), bas, bit)
    p = kes(politika(), bas, bit)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.055,
                        subplot_titles=(
                            "USD/TRY — TCMB gösterge kuru, logaritmik ölçek (eşit dikey mesafe = eşit yüzde)",
                            "Bankalararası gecelik faiz — gerçekleşen ağırlıklı ortalama (%), logaritmik",
                            "TÜFE yıllık değişim (%) ve TCMB politika faizi (%)"))
    cizgi(fig, k, "USD/TRY", TEAL, row=1, w=1.5)
    cizgi(fig, g, "gecelik AOF (%)", BORDO, row=2, w=1.2)
    cizgi(fig, t, "TÜFE yıllık (%)", ALTIN, row=3, w=1.8)
    cizgi(fig, p, "politika faizi (%)", MAVI, row=3, w=1.6, sekil="hv")

    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=3)
    not_(fig, pd.Timestamp("1994-04-07"), np.log10(0.0398), "07.04.1994 — 1993 sonuna göre ×2,76",
         row=1, ay=-46, boyut=10)
    not_(fig, pd.Timestamp("2001-02-23"), np.log10(0.9579), "23.02.2001 — bir günde +%39,8",
         row=1, ay=-42, boyut=10)
    not_(fig, pd.Timestamp("2007-12-12"), np.log10(1.1626), "12.12.2007 — dönem dibi 1,1626",
         row=1, ay=44, boyut=10)
    not_(fig, pd.Timestamp("2021-12-20"), np.log10(17.4731), "20.12.2021 — 17,47", row=1, ay=52, boyut=10)
    not_(fig, pd.Timestamp("2001-02-21"), np.log10(4018.58), "21.02.2001 — gecelik %4.018,6",
         row=2, ay=-30, boyut=10)
    not_(fig, pd.Timestamp("2022-10-01"), 85.5, "Eki 2022 — TÜFE %85,5", row=3, ay=-36, boyut=10)

    fig.update_yaxes(type="log", title_text="TL / USD (log)", row=1)
    fig.update_yaxes(type="log", title_text="% (log)", row=2)
    fig.update_yaxes(title_text="%", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Dersin haritası: kur, gecelik faiz ve enflasyon — 36 yıl, on dört epizot",
          "02.01.1990 – 21.08.2026", 1050,
          alt="EVDS TP.DK.USD.A.YTL · TP.PY.P06.ON · TÜFE (1987=100/2003=100/2025=100 eklemli) · TP.BISPOLFAIZ.TUR")
    kaydet(fig, "01_omurga", "Dersin haritası: kur, gecelik faiz ve enflasyon", "1990-01 → 2026-08")


# ==========================================================================
#  02 — Dolarizasyon tarihçesi
# ==========================================================================
def g02():
    bas, bit = "1986-01-01", "2026-06-30"
    dth = kes(dth_payi(), bas, bit)
    kmd = kes(kmdh_payi(), bas, bit)
    k = kes(kur(), bas, bit).resample("MS").last()
    kyoy = 100 * (k / k.shift(12) - 1)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.055,
                        subplot_titles=(
                            "Döviz tevdiat hesaplarının toplam mevduat içindeki payı (%)",
                            "Kıymetli maden depo hesaplarının payı (%) — altına kaçışın mevduat izi",
                            "USD/TRY yıllık değişim (%) — aynı eksende dolarizasyonun tetikleyicisi"))
    cizgi(fig, dth, "DTH payı (%)", TEAL, row=1, w=2.0)
    cizgi(fig, kmd, "KMDH payı (%)", ALTIN, row=2, w=2.0)
    cizgi(fig, kyoy, "USD/TRY yıllık (%)", BORDO, row=3, w=1.6)
    sifir_cizgisi(fig, row=3)

    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=3)
    zirve = dth.idxmax()
    not_(fig, zirve, dth.max(), f"{zirve.strftime('%m.%Y')} — DTH payı zirvesi %{dth.max():.1f}",
         row=1, ay=-38, boyut=10)
    son = dth.dropna().index[-1]
    not_(fig, son, dth.loc[son], f"{son.strftime('%m.%Y')} — %{dth.loc[son]:.1f}",
         row=1, ay=40, boyut=10, xanchor="right")
    kz = kmd.idxmax()
    not_(fig, kz, kmd.max(), f"{kz.strftime('%m.%Y')} — %{kmd.max():.1f}", row=2, ay=-34, boyut=10)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_yaxes(title_text="%", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Dolarizasyon kırk yılda ne yaptı? Mevduatın para birimi kompozisyonu",
          "01.1986 – 06.2026", 950,
          alt="EVDS TP.KM.F01/F04/F07/F13/F19/F22 (mevduat bankaları, türlerine göre) · TP.DK.USD.A.YTL")
    kaydet(fig, "02_dolarizasyon_tarihcesi", "Dolarizasyon tarihçesi: DTH ve kıymetli maden payı",
           "1986-01 → 2026-06")


# ==========================================================================
#  03 — 2000–2001: çıpanın kırılması
# ==========================================================================
def g03():
    bas, bit = "2000-01-03", "2001-06-29"
    k = kes(kur(), bas, bit)
    b = kes(S("bist")["MK.F.BILESIK"].dropna(), bas, bit)
    g = kes(gecelik(), bas, bit)
    bu = (b / k.reindex(b.index).ffill()).dropna()

    # ilan edilmiş çıpa patikası (2000 için yıllık +%20, sepet üzerinden ilan edildi;
    # burada dolar bacağı YAKLAŞIK temsil olarak çizilir — bkz. altyazı)
    t0 = pd.Timestamp("2000-01-03")
    gun = pd.date_range(t0, pd.Timestamp("2000-12-31"), freq="D")
    patika = pd.Series(k.loc[t0] * (1.20 ** ((gun - t0).days / 365.0)), index=gun)

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                        subplot_titles=(
                            "USD/TRY günlük — ilan edilmiş kur patikası (yaklaşık dolar bacağı) kesikli",
                            "İMKB-100 bileşik endeks (kapanış)",
                            "İMKB-100'ün dolar bazlı hâli (endeks ÷ USD/TRY)",
                            "Bankalararası gecelik faiz — gerçekleşen ağırlıklı ortalama (%), logaritmik"))
    cizgi(fig, k, "USD/TRY", TEAL, row=1, w=2.0)
    cizgi(fig, patika, "ilan edilen patika (yaklaşık)", GRI, row=1, w=1.6, dash="dash")
    cizgi(fig, b, "İMKB-100", MAVI, row=2, w=1.8)
    cizgi(fig, bu, "İMKB-100 (USD bazlı)", MOR, row=3, w=1.8)
    cizgi(fig, g, "gecelik AOF (%)", BORDO, row=4, w=1.5)

    for i, (tar, et) in enumerate([("2000-11-17", "17.11.2000 · Kasım krizi başlangıcı"),
                                   ("2000-12-06", "06.12.2000 · Demirbank TMSF'ye"),
                                   ("2001-02-19", "19.02.2001 · siyasi kriz"),
                                   ("2001-02-22", "22.02.2001 · dalgalı kura geçiş")]):
        dikey(fig, tar, et, row=1, satir_sayisi=4, boyut=9,
              y_konum=1.0 if i % 2 == 0 else 0.70)

    not_(fig, pd.Timestamp("2001-02-23"), 0.9579, "23.02.2001 — 0,6854 → 0,9579 (+%39,8)",
         row=1, ay=-40, boyut=10)
    not_(fig, pd.Timestamp("2001-02-21"), np.log10(4018.58), "21.02.2001 — gecelik %4.018,6",
         row=4, ay=-26, boyut=10)
    zb = b.loc["2000-01-01":"2000-03-01"].idxmax()
    not_(fig, zb, b.loc[zb], f"{zb.strftime('%d.%m.%Y')} — İMKB zirvesi {b.loc[zb]:,.0f}".replace(",", "."),
         row=2, ay=-34, boyut=10)

    fig.update_yaxes(title_text="TL / USD", row=1)
    fig.update_yaxes(title_text="endeks", row=2)
    fig.update_yaxes(title_text="endeks / USD", row=3)
    fig.update_yaxes(type="log", title_text="% (log)", row=4)
    fig.update_xaxes(title_text="tarih", row=4)
    duzen(fig, "Çıpa tutuyordu, fiyatlar tutmuyordu: 2000 programının son on beş ayı",
          "03.01.2000 – 29.06.2001", 1300,
          alt="EVDS TP.DK.USD.A.YTL · TP.MK.F.BILESIK (Ocak 1986 = 0,01 tabanlı; geleneksel kotasyonun yüzde biri) · TP.PY.P06.ON · patika: 2000 programının ilan ettiği yıllık +%20 çıpanın yaklaşık dolar bacağı")
    kaydet(fig, "03_2000_2001_cipa", "2000–2001: çıpanın kırılması", "2000-01 → 2001-06")


# ==========================================================================
#  04 — İMKB: aynı şok, iki para birimi (1990–2003)
# ==========================================================================
def g04():
    bas, bit = "1990-01-01", "2003-12-31"
    b = kes(S("bist")["MK.F.BILESIK"].dropna(), bas, bit)
    k = kes(kur(), bas, bit)
    bu = (b / k.reindex(b.index).ffill()).dropna()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.075,
                        subplot_titles=("İMKB-100, TL bazında (logaritmik)",
                                        "İMKB-100, dolar bazında (endeks ÷ USD/TRY, logaritmik)"))
    cizgi(fig, b, "İMKB-100 (TL)", MAVI, row=1, w=1.6)
    cizgi(fig, bu, "İMKB-100 (USD)", MOR, row=2, w=1.6)
    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=2)

    z1 = b.loc["1993-11-01":"1994-02-28"].idxmax()
    d1 = b.loc["1994-02-01":"1994-05-31"].idxmin()
    z2 = b.loc["1999-11-01":"2000-03-31"].idxmax()
    d2 = b.loc["2001-06-01":"2001-12-31"].idxmin()
    for x, y, m, r, ay in [(z1, b.loc[z1], f"{z1.strftime('%d.%m.%Y')} zirve", 1, -34),
                           (d1, b.loc[d1], f"{d1.strftime('%d.%m.%Y')} dip · TL bazında −%{100*(1-b.loc[d1]/b.loc[z1]):.1f}", 1, 40),
                           (z2, b.loc[z2], f"{z2.strftime('%d.%m.%Y')} zirve", 1, -34),
                           (d2, b.loc[d2], f"{d2.strftime('%d.%m.%Y')} dip · TL bazında −%{100*(1-b.loc[d2]/b.loc[z2]):.1f}", 1, 46)]:
        not_(fig, x, np.log10(y), m, row=r, ay=ay, boyut=10)
    zu = bu.loc["1999-11-01":"2000-03-31"].idxmax()
    du = bu.loc["2001-06-01":"2001-12-31"].idxmin()
    not_(fig, du, np.log10(bu.loc[du]),
         f"aynı pencere dolar bazında −%{100*(1-bu.loc[du]/bu.loc[zu]):.1f}", row=2, ay=44, boyut=10)

    fig.update_yaxes(type="log", title_text="endeks (log)", row=1)
    fig.update_yaxes(type="log", title_text="endeks/USD (log)", row=2)
    fig.update_xaxes(title_text="tarih", row=2)
    duzen(fig, "Aynı şok, iki para birimi: yerel parayla ve dolarla bakanın gördüğü iki farklı kriz",
          "01.01.1990 – 31.12.2003", 780,
          alt="EVDS TP.MK.F.BILESIK (Ocak 1986 = 0,01 tabanlı; geleneksel kotasyonun yüzde biri) · TP.DK.USD.A.YTL — dolar bazı, endeksin gösterge kura bölünmesiyle hesaplanmıştır")
    kaydet(fig, "04_imkb_tl_usd", "İMKB-100: TL bazlı ve dolar bazlı, 1990–2003", "1990-01 → 2003-12")


# ==========================================================================
#  05 — Carry'nin gövdesi ve kuyruğu
# ==========================================================================
def g05():
    k = kes(kur(), "1990-01-01", "2026-08-21")
    yil_son = k.resample("YE").last()
    degisim = (100 * (yil_son / yil_son.shift(1) - 1)).dropna()
    degisim.index = degisim.index.year
    # yıl içi gerçekleşen oynaklık: günlük log getirilerin yıllıklandırılmış std'si
    lg = np.log(k).diff().dropna()
    vol = lg.groupby(lg.index.year).std() * np.sqrt(252) * 100
    vol = vol.loc[degisim.index]

    renkler = [BORDO if v > 50 else (TURUNCU if v > 0 else YESIL) for v in degisim.values]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09,
                        subplot_titles=(
                            "USD/TRY yıllık yüzde değişim — yeşil: TL değer kazandı · turuncu: kaybetti · bordo: %50 üzeri kayıp",
                            "Yıl içi gerçekleşen kur oynaklığı (%, yıllıklandırılmış günlük log getiri std'si)"))
    sutun(fig, degisim, "yıllık % değişim", TURUNCU, row=1, renkler=renkler, birim="%")
    sutun(fig, vol, "gerçekleşen oynaklık (%)", MAVI, row=2, birim="%")
    sifir_cizgisi(fig, row=1)
    for y in degisim.index:
        if degisim.loc[y] > 50:
            not_(fig, y, degisim.loc[y], f"{y}: +%{degisim.loc[y]:.0f}", row=1, ay=-26, boyut=9.5)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_xaxes(title_text="yıl", row=2, dtick=2)
    duzen(fig, "Carry'nin gövdesi ve kuyruğu: sessiz yılların sayısı çok, kuyruk yıllarının büyüklüğü çok",
          "1991 – 2026 (2026 yılbaşından 21.08.2026'ya)", 780,
          alt="EVDS TP.DK.USD.A.YTL yıl sonu kapanışları · oynaklık günlük log getirilerden hesaplandı")
    kaydet(fig, "05_yillik_kur_degisimi", "USD/TRY yıllık değişim ve yıl içi oynaklık", "1991 → 2026")


# ==========================================================================
#  06 — Rejim değişikliği: 2003–2013
# ==========================================================================
def g06():
    bas, bit = "2003-01-01", "2013-12-31"
    t = kes(tufe_yoy(), bas, bit)
    k = kes(kur(), bas, bit)
    h = D(tv.depo_haftalik_rezerv)
    hb = kes(h["brut_rezerv_usd"].dropna(), bas, bit)
    hn = kes(h["net_rezerv_usd"].dropna(), bas, bit)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.055,
                        subplot_titles=("TÜFE yıllık değişim (%) — %5 referans çizgisiyle",
                                        "USD/TRY günlük",
                                        "TCMB brüt ve net uluslararası rezerv (mlr USD, haftalık)"))
    cizgi(fig, t, "TÜFE yıllık (%)", ALTIN, row=1, w=2.0)
    fig.add_hline(y=5, line=dict(color=rgba(GRI, 0.8), width=1.2, dash="dot"), row=1, col=1,
                  annotation_text="%5", annotation_position="right",
                  annotation=dict(font=dict(size=10, color=GRI)))
    cizgi(fig, k, "USD/TRY", TEAL, row=2, w=1.8)
    cizgi(fig, hb, "brüt rezerv", MOR, row=3, w=1.8)
    cizgi(fig, hn, "net rezerv", BORDO, row=3, w=1.8)

    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=3)
    dip = k.loc["2007-01-01":"2008-06-30"].idxmin()
    not_(fig, dip, k.loc[dip], f"{dip.strftime('%d.%m.%Y')} — {k.loc[dip]:.4f}".replace(".", ","),
         row=2, ay=44, boyut=10)
    not_(fig, pd.Timestamp("2013-05-22"), k.loc[pd.Timestamp("2013-05-22")],
         "22.05.2013 — 1,8475", row=2, ay=-36, boyut=10)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="TL / USD", row=2)
    fig.update_yaxes(title_text="mlr USD", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Rejim değişikliği ve kırılganlığın yer değiştirmesi: bolluk dönemi",
          "01.01.2003 – 31.12.2013", 1000,
          alt="EVDS TÜFE · TP.DK.USD.A.YTL · depo hattı TCMBNetRezerv/haftalik_rezerv.csv")
    kaydet(fig, "06_rejim_degisikligi", "Rejim değişikliği: enflasyon, kur, rezerv (2003–2013)",
           "2003-01 → 2013-12")


def koridor(fig, bas, bit, row):
    """TCMB gecelik borç alma/verme kotasyonları — faiz koridoru gölgeli bant."""
    d = S("gecelik")
    alt = kes(d["PY.P01.ON"].dropna(), bas, bit)
    ust = kes(d["PY.P02.ON"].dropna(), bas, bit)
    ort = alt.index.intersection(ust.index)
    if not len(ort):
        return
    fig.add_trace(go.Scatter(x=ust.loc[ort].index, y=ust.loc[ort].values, mode="lines",
                             line=dict(width=0), showlegend=False, hoverinfo="skip"),
                  row=row, col=1)
    fig.add_trace(go.Scatter(x=alt.loc[ort].index, y=alt.loc[ort].values, mode="lines",
                             line=dict(width=0), fill="tonexty", fillcolor=rgba(GRI, 0.16),
                             name="faiz koridoru (TCMB gecelik borç alma–verme)",
                             hovertemplate="%{y:.2f}%<extra>koridor</extra>"),
                  row=row, col=1)


# TCMB PPK karar günleri ve o kararla belirlenen bir hafta vadeli repo faizi (%).
# EVDS'te karar tarihli bir politika faizi serisi yoktur; aylık BIS derlemesi (TP.BISPOLFAIZ.TUR)
# AY SONU değerini verir. Aşağıdaki tablo yalnızca derste açıkça anılan kararları içerir ve
# basamağı ay sonundan gerçek karar gününe taşır. Kaynak: TCMB PPK karar duyuruları.
PPK_KARAR = {
    "2014-01-28": 10.00,
    "2018-09-13": 24.00,
    "2020-11-19": 15.00,
    "2021-09-23": 18.00, "2021-10-21": 16.00, "2021-11-18": 15.00, "2021-12-16": 14.00,
    "2023-06-22": 15.00, "2023-07-20": 17.50, "2023-08-24": 25.00,
    "2024-03-21": 50.00,
    "2025-04-17": 46.00,
}


def politika_gunluk(bas, bit) -> pd.Series:
    """Politika faizinin günlük basamak hâli.

    Aylık seri ay SONU değeridir; bu yüzden basamak ay sonuna çıpalanır (asla erken
    görünmez). Derste anılan kararlar için basamak PPK_KARAR tablosuyla gerçek karar
    gününe kaydırılır."""
    p = politika()
    pe = p.copy()
    pe.index = pe.index + pd.offsets.MonthEnd(0)
    idx = pd.date_range(pd.Timestamp(bas), pd.Timestamp(bit), freq="D")
    s = pe.reindex(pe.index.union(idx)).ffill().reindex(idx)
    for tarih, oran in PPK_KARAR.items():
        t = pd.Timestamp(tarih)
        if t < idx[0] or t > idx[-1]:
            continue
        ay_sonu = t + pd.offsets.MonthEnd(0)
        s.loc[t:min(ay_sonu, idx[-1])] = oran
    return s


# ==========================================================================
#  07 — 2013 taper
# ==========================================================================
def g07():
    bas, bit = "2013-01-01", "2013-12-31"
    tnx = Y("^TNX", "2010-01-01")
    xu = Y("XU100.IS")
    eem = Y("EEM")
    if tnx is None or xu is None or eem is None:
        ATLANAN.append("07 — 2013 taper: yfinance serilerinden biri çekilemedi (^TNX / XU100.IS / EEM)")
        return
    t0 = "2013-05-22"
    tn = kes(tnx["Close"].dropna(), bas, bit)
    x = endeksle(kes(xu["Close"].dropna(), bas, bit), t0)
    e = endeksle(kes(eem["Close"].dropna(), bas, bit), t0)
    k = kes(kur(), bas, bit)
    a = kes(aofm(), bas, bit)

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                        subplot_titles=(
                            "ABD 10 yıllık tahvil getirisi (%) — küresel fonlama maliyeti şoku",
                            "BIST-100 ve EM hisse sepeti (EEM), 22.05.2013 = 100 — aradaki fark yerel primdir",
                            "USD/TRY — TCMB gösterge kuru",
                            "TCMB ağırlıklı ortalama fonlama maliyeti (%) ve faiz koridoru; politika faizi kesikli"))
    cizgi(fig, tn, "ABD 10Y (%)", MUREKKEP, row=1, w=1.8)
    cizgi(fig, x, "BIST-100 (endeksli)", MAVI, row=2, w=1.9)
    cizgi(fig, e, "EEM (endeksli)", GRI, row=2, w=1.7)
    cizgi(fig, k, "USD/TRY", TEAL, row=3, w=1.9)
    koridor(fig, bas, bit, row=4)
    cizgi(fig, a, "AOFM (%)", BORDO, row=4, w=1.9)
    cizgi(fig, politika_gunluk(bas, bit), "politika faizi (%, ay sonu · PPK günü düzeltmeli)", MAVI, row=4, w=1.5,
          dash="dash", sekil="hv")

    for tar, et in [("2013-05-22", "22.05.2013 · Bernanke tanıklığı"),
                    ("2013-07-24", "24.07.2013 · koridor üst bandı %6,50 → %7,25"),
                    ("2013-08-21", "21.08.2013 · koridor üst bandı %7,25 → %7,75"),
                    ("2013-09-18", "18.09.2013 · Fed taper'ı erteledi")]:
        dikey(fig, tar, et, row=1, satir_sayisi=4, boyut=9)
    zt = tn.loc["2013-08-15":"2013-09-15"].idxmax()
    not_(fig, zt, tn.loc[zt], f"{zt.strftime('%d.%m.%Y')} — %{tn.loc[zt]:.3f}", row=1, ay=-30, boyut=10)
    dx = x.loc["2013-06-01":"2013-09-30"].idxmin()
    not_(fig, dx, x.loc[dx], f"{dx.strftime('%d.%m.%Y')} — BIST {x.loc[dx]:.1f} · EEM {e.reindex([dx]).ffill().iloc[0]:.1f}",
         row=2, ay=42, boyut=10)
    za = a.loc["2013-08-01":"2013-09-15"].idxmax()
    not_(fig, za, a.loc[za], f"{za.strftime('%d.%m.%Y')} — AOFM %{a.loc[za]:.2f} (politika faizi %4,50 sabit)",
         row=4, ay=-32, boyut=10)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="endeks (22.05 = 100)", row=2)
    fig.update_yaxes(title_text="TL / USD", row=3)
    fig.update_yaxes(title_text="%", row=4)
    fig.update_xaxes(title_text="tarih", row=4)
    duzen(fig, "Küresel fitil, yerel yangın: 2013 taper şokunun aktarım sırası",
          "01.01.2013 – 31.12.2013", 1250,
          alt="yfinance ^TNX/XU100.IS/EEM · EVDS TP.DK.USD.A.YTL · TP.APIFON4 · TP.PY.P01.ON/P02.ON")
    kaydet(fig, "07_taper_2013", "2013 taper şokunun aktarım sırası", "2013-01 → 2013-12")


# ==========================================================================
#  08 — Aralık 2013 – Ocak 2014
# ==========================================================================
def g08():
    bas, bit = "2013-12-01", "2014-03-31"
    k = kes(kur(), bas, bit)
    a = kes(aofm(), bas, bit)
    f = kes(S("api")["APIFON1.TOP"].dropna(), bas, bit) / 1000.0   # mn TL → mlr TL
    xu = Y("XU100.IS")
    x = kes(xu["Close"].dropna(), bas, bit) if xu is not None else None

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                        subplot_titles=(
                            "USD/TRY — TCMB gösterge kuru",
                            "AOFM (%), faiz koridoru ve politika faizi (aylık, basamak)",
                            "TCMB toplam fonlaması (mlr TL) — miktar kanalı",
                            "BIST-100 (kapanış)"))
    cizgi(fig, k, "USD/TRY", TEAL, row=1, w=2.2)
    koridor(fig, bas, bit, row=2)
    cizgi(fig, a, "AOFM (%)", BORDO, row=2, w=2.2)
    cizgi(fig, politika_gunluk(bas, bit), "politika faizi (%, ay sonu · PPK günü düzeltmeli)", MAVI, row=2, w=1.7,
          dash="dash", sekil="hv")
    cizgi(fig, f, "toplam fonlama (mlr TL)", MOR, row=3, w=1.9)
    if x is not None:
        cizgi(fig, x, "BIST-100", MAVI, row=4, w=2.0)

    for i, (tar, et) in enumerate([("2013-12-17", "17.12.2013 · yerel şok"),
                                   ("2013-12-18", "18.12.2013 · FOMC taper ilanı"),
                                   ("2014-01-23", "23.01.2014 · doğrudan döviz müdahalesi"),
                                   ("2014-01-28", "28.01.2014 · olağanüstü PPK → %10")]):
        dikey(fig, tar, et, row=1, satir_sayisi=4, boyut=9,
              y_konum=1.0 if i % 2 == 0 else 0.72)
    zk = k.loc["2014-01-20":"2014-02-05"].idxmax()
    not_(fig, zk, k.loc[zk], f"{zk.strftime('%d.%m.%Y')} — zirve {k.loc[zk]:.4f}".replace(".", ","),
         row=1, ay=-34, boyut=10)
    a1 = a.loc[pd.Timestamp("2014-01-28")] if pd.Timestamp("2014-01-28") in a.index else np.nan
    a2 = a.loc[pd.Timestamp("2014-01-29")] if pd.Timestamp("2014-01-29") in a.index else np.nan
    if np.isfinite(a1) and np.isfinite(a2):
        not_(fig, pd.Timestamp("2014-01-29"), a2,
             f"AOFM %{a1:.2f} → %{a2:.2f} (bir günde +{100*(a2-a1):.0f} bp)".replace(".", ","),
             row=2, ay=-34, boyut=10)
    if x is not None:
        dx = x.loc["2014-02-01":"2014-03-15"].idxmin()
        not_(fig, dx, x.loc[dx],
             f"{dx.strftime('%d.%m.%Y')} — endeks dibi {x.loc[dx]:,.0f}; faiz kararı kuru durdurdu, hisseyi durdurmadı".replace(",", "."),
             row=4, ay=44, boyut=10)

    fig.update_yaxes(title_text="TL / USD", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_yaxes(title_text="mlr TL", row=3)
    fig.update_yaxes(title_text="endeks", row=4)
    fig.update_xaxes(title_text="tarih", row=4)
    duzen(fig, "550 baz puanın iz düşümü: faiz şoku hangi göstergede ne zaman göründü?",
          "01.12.2013 – 31.03.2014", 1250,
          alt="EVDS TP.DK.USD.A.YTL · TP.APIFON4 · TP.APIFON1.TOP · TP.PY.P01.ON/P02.ON · yfinance XU100.IS")
    kaydet(fig, "08_ocak2014_soku", "Ocak 2014 faiz şokunun iz düşümü", "2013-12 → 2014-03")


# ==========================================================================
#  09 — Politika faizi ile fonlama maliyetinin ayrışması
# ==========================================================================
def g09():
    bas, bit = "2011-01-03", "2026-08-20"
    a = kes(aofm(), bas, bit)
    p = politika_gunluk(bas, bit).reindex(a.index).ffill()
    fark = ((a - p) * 100).dropna()
    f = kes(S("api")["APIFON1.TOP"].dropna(), bas, bit) / 1000.0   # mn TL → mlr TL

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.055,
                        subplot_titles=(
                            "AOFM (%), faiz koridoru (gölgeli) ve politika faizi (aylık, basamak)",
                            "AOFM − politika faizi (baz puan) — sıfırın üstü fiili sıkılaştırma, altı fiili gevşeme",
                            "TCMB toplam fonlaması (mlr TL, logaritmik) — miktar kanalı"))
    koridor(fig, bas, bit, row=1)
    cizgi(fig, a, "AOFM (%)", BORDO, row=1, w=1.6)
    cizgi(fig, politika_gunluk(bas, bit), "politika faizi (%, ay sonu · PPK günü düzeltmeli)", MAVI, row=1, w=1.5,
          dash="dash", sekil="hv")
    renkler = [rgba(BORDO, 0.85) if v > 0 else rgba(YESIL, 0.85) for v in fark.values]
    sutun(fig, fark, "AOFM − politika (bp)", BORDO, row=2, renkler=renkler, birim=" bp")
    sifir_cizgisi(fig, row=2)
    cizgi(fig, f, "toplam fonlama (mlr TL)", MOR, row=3, w=1.4)

    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=3)
    for tar, et in [("2013-08-23", "Ağu 2013"), ("2014-01-29", "Oca 2014"),
                    ("2018-08-17", "Ağu 2018"), ("2019-03-25", "Mar 2019"),
                    ("2020-11-19", "Kas 2020"), ("2025-03-24", "Mar 2025")]:
        t = pd.Timestamp(tar)
        if t in fark.index:
            not_(fig, t, fark.loc[t], f"{et}: {fark.loc[t]:+.0f} bp", row=2,
                 ay=-30 if fark.loc[t] > 0 else 34, boyut=9.5)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="baz puan", row=2)
    fig.update_yaxes(type="log", title_text="mlr TL (log)", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Duruşun ölçüsü ilan edilen faiz değil, gerçekleşen fonlama maliyetidir",
          "03.01.2011 – 20.08.2026", 1000,
          alt="EVDS TP.APIFON4 · TP.APIFON1.TOP · TP.PY.P01.ON/P02.ON · TP.BISPOLFAIZ.TUR (aylık)")
    kaydet(fig, "09_aofm_politika_ayrismasi", "AOFM ile politika faizinin ayrışması",
           "2011-01 → 2026-08")


# ==========================================================================
#  10 — 2015: tek şok değil, şok dizisi
# ==========================================================================
def g10():
    bas, bit = "2015-01-01", "2015-12-31"
    t0 = "2015-01-02"
    k = endeksle(kes(kur(), bas, bit), t0)
    xu, eem = Y("XU100.IS"), Y("EEM")
    if xu is None or eem is None:
        ATLANAN.append("10 — 2015: XU100.IS / EEM çekilemedi")
        return
    x = endeksle(kes(xu["Close"].dropna(), bas, bit), t0)
    e = endeksle(kes(eem["Close"].dropna(), bas, bit), t0)
    a = kes(aofm(), bas, bit)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=(
                            "USD/TRY ve BIST-100, 02.01.2015 = 100 — yukarı hareket TL'nin zayıflaması",
                            "BIST-100 ve EM hisse sepeti (EEM), 02.01.2015 = 100 — neredeyse üst üste",
                            "AOFM (%), faiz koridoru (gölgeli) ve politika faizi — dar bantta gezinen fonlama"))
    cizgi(fig, k, "USD/TRY (endeksli)", TEAL, row=1, w=2.0)
    cizgi(fig, x, "BIST-100 (endeksli)", MAVI, row=1, w=2.0)
    cizgi(fig, x, "BIST-100 (endeksli)", MAVI, row=2, w=2.0, goster=False)
    cizgi(fig, e, "EEM (endeksli)", GRI, row=2, w=1.8)
    koridor(fig, bas, bit, row=3)
    cizgi(fig, a, "AOFM (%)", BORDO, row=3, w=2.0)
    cizgi(fig, politika_gunluk(bas, bit), "politika faizi (%, ay sonu · PPK günü düzeltmeli)", MAVI, row=3, w=1.5,
          dash="dash", sekil="hv")

    for i, (tar, et) in enumerate([("2015-06-07", "07.06 · genel seçim"),
                                   ("2015-08-18", "18.08 · politika yol haritası"),
                                   ("2015-11-01", "01.11 · tekrar seçim"),
                                   ("2015-11-24", "24.11 · jeopolitik olay"),
                                   ("2015-12-16", "16.12 · Fed ilk artış")]):
        dikey(fig, tar, et, row=1, satir_sayisi=3, boyut=9,
              y_konum=1.0 if i % 2 == 0 else 0.74)
    sonk, sonx = k.dropna().iloc[-1], x.dropna().iloc[-1]
    not_(fig, k.dropna().index[-1], sonk, f"yıl sonu: kur {sonk-100:+.1f}%, BIST {sonx-100:+.1f}%",
         row=1, ay=-30, boyut=10, xanchor="right")

    fig.update_yaxes(title_text="endeks (=100)", row=1)
    fig.update_yaxes(title_text="endeks (=100)", row=2)
    fig.update_yaxes(title_text="%", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Tek şok değil, şok dizisi: belirsizliğin kronikleştiği bir yılın imzası",
          "01.01.2015 – 31.12.2015", 1000,
          alt="EVDS TP.DK.USD.A.YTL · TP.APIFON4 · TP.PY.P01.ON/P02.ON · yfinance XU100.IS / EEM")
    kaydet(fig, "10_2015_sok_dizisi", "2015: şok dizisinin varlık sınıfı imzası", "2015-01 → 2015-12")


# ==========================================================================
#  11 — Üç şok, t = 0 hizalı
# ==========================================================================
def g11():
    xu = Y("XU100.IS")
    if xu is None:
        ATLANAN.append("11 — üç şok hizalı: XU100.IS çekilemedi")
        return
    x = xu["Close"].dropna()
    k = kur()
    a = aofm()
    soklar = [("2013-05-22", "22.05.2013 · taper", MAVI),
              ("2013-12-17", "17.12.2013 · yerel şok", BORDO),
              ("2016-07-15", "15.07.2016 · darbe girişimi", TURUNCU)]

    def hizala(s: pd.Series, t0: str, once=10, sonra=40, oran=True):
        t0 = pd.Timestamp(t0)
        idx = s.index
        konum = idx.searchsorted(t0)
        if konum >= len(idx):
            return None
        bas_i, bit_i = max(0, konum - once), min(len(idx), konum + sonra + 1)
        parca = s.iloc[bas_i:bit_i]
        taban = s.iloc[konum]
        y = 100 * parca / taban if oran else (parca - taban) * 100
        return pd.Series(y.values, index=np.arange(bas_i, bit_i) - konum)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=(
                            "BIST-100, şok günü = 100",
                            "USD/TRY, şok günü = 100 (yukarı = TL zayıflıyor)",
                            "AOFM, şok gününe göre değişim (baz puan)"))
    for t0, ad, renk in soklar:
        for satir, seri_, oran in [(1, x, True), (2, k, True), (3, a, False)]:
            h = hizala(seri_, t0, oran=oran)
            if h is None or not len(h.dropna()):
                continue
            fig.add_trace(go.Scatter(x=h.index, y=h.values, name=ad, mode="lines",
                                     line=dict(color=renk, width=2.0),
                                     showlegend=(satir == 1),
                                     hovertemplate="t%{x:+d}: %{y:.1f}<extra>" + ad + "</extra>"),
                          row=satir, col=1)
    for r in (1, 2, 3):
        fig.add_vline(x=0, line=dict(color=rgba(MUREKKEP, 0.5), width=1.4, dash="dash"),
                      row=r, col=1)
    fig.add_hline(y=100, line=dict(color=rgba(GRI, 0.6), width=1), row=1, col=1)
    fig.add_hline(y=100, line=dict(color=rgba(GRI, 0.6), width=1), row=2, col=1)
    sifir_cizgisi(fig, row=3)
    not_(fig, 20, 0, "darbe girişiminde fonlama maliyeti YÜKSELMEDİ, düştü — araç faiz değil likiditeydi",
         row=3, ay=-40, boyut=10, ok=False)

    fig.update_yaxes(title_text="endeks (t=0 → 100)", row=1)
    fig.update_yaxes(title_text="endeks (t=0 → 100)", row=2)
    fig.update_yaxes(title_text="baz puan", row=3)
    fig.update_xaxes(title_text="şok gününden itibaren işlem günü", row=3, dtick=5)
    duzen(fig, "Aynı ülke, üç şok, üç farklı imza: hangi göstergede ne büyüklükte tepki?",
          "t = −10 … +40 işlem günü; t₀ = 22.05.2013 · 17.12.2013 · 15.07.2016", 1000,
          alt="yfinance XU100.IS · EVDS TP.DK.USD.A.YTL · TP.APIFON4")
    kaydet(fig, "11_uc_sok_hizalanmis", "Üç şokun t=0 hizalı karşılaştırması",
           "2013-05 / 2013-12 / 2016-07")


# ==========================================================================
#  12 — Reel efektif döviz kuru tarihçesi
# ==========================================================================
def g12():
    r = D(tv.depo_reer)
    bas, bit = "1994-01-01", "2026-07-31"
    cpi = kes(r["CPI_REER"].dropna(), bas, bit)
    ppi = kes(r["PPI_REER"].dropna(), bas, bit)
    sapma = kes(r["CPI_Deviation_10Y_Pct"].dropna(), bas, bit)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=(
                            "Reel efektif döviz kuru (2003 = 100): TÜFE ve Yİ-ÜFE bazlı — düşüş = TL reel olarak ucuzluyor",
                            "TÜFE bazlı REDK'nin 10 yıllık ortalamasından sapması (%)"))
    cizgi(fig, cpi, "TÜFE bazlı REDK", TEAL, row=1, w=1.9)
    cizgi(fig, ppi, "Yİ-ÜFE bazlı REDK", ALTIN, row=1, w=1.7)
    fig.add_hline(y=100, line=dict(color=rgba(GRI, 0.8), width=1.2, dash="dot"), row=1, col=1)
    renkler = [rgba(BORDO, 0.85) if v > 0 else rgba(TEAL, 0.85) for v in sapma.values]
    sutun(fig, sapma, "10y ortalamadan sapma (%)", TEAL, row=2, renkler=renkler, birim="%")
    sifir_cizgisi(fig, row=2)

    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=2)
    z = cpi.idxmax()
    d = cpi.idxmin()
    not_(fig, z, cpi.loc[z], f"{z.strftime('%m.%Y')} — zirve {cpi.loc[z]:.1f}".replace(".", ","),
         row=1, ay=-34, boyut=10)
    not_(fig, d, cpi.loc[d], f"{d.strftime('%m.%Y')} — dip {cpi.loc[d]:.1f}".replace(".", ","),
         row=1, ay=42, boyut=10)
    son = cpi.dropna().index[-1]
    not_(fig, son, cpi.loc[son], f"{son.strftime('%m.%Y')} — {cpi.loc[son]:.1f}".replace(".", ","),
         row=1, ay=-34, boyut=10, xanchor="right")

    fig.update_yaxes(title_text="endeks (2003 = 100)", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_xaxes(title_text="tarih", row=2)
    duzen(fig, "Reel kur: nominal kur hikâyesinin arkasındaki rekabetçilik hikâyesi",
          "01.1994 – 07.2026", 800,
          alt="depo hattı TRYREER/reer_analysis_data.csv (EVDS TP.RK.T1.Y ve TP.RK.U1.Y kaynaklı)")
    kaydet(fig, "12_redk_tarihce", "Reel efektif döviz kuru tarihçesi", "1994-01 → 2026-07")


# ==========================================================================
#  13 — Ağustos 2018, gün gün
# ==========================================================================
def g13():
    bas, bit = "2018-07-15", "2018-09-30"
    yu = Y("USDTRY=X")
    if yu is None:
        ATLANAN.append("13 — Ağustos 2018: USDTRY=X çekilemedi")
        return
    o = kes(yu, bas, bit).dropna(subset=["Open", "High", "Low", "Close"])
    k = kes(kur(), bas, bit)
    menzil = 100 * (o["High"] - o["Low"]) / o["Low"]
    a = kes(aofm(), bas, bit)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=(
                            "USD/TRY günlük mum (piyasa, yfinance) + TCMB gösterge kuru (çizgi) — iki katmanın farkı",
                            "Gün içi menzil (%): (yüksek − düşük) ÷ düşük",
                            "AOFM (%), faiz koridoru (gölgeli) ve politika faizi (aylık, basamak)"))
    fig.add_trace(go.Candlestick(x=o.index, open=o["Open"], high=o["High"], low=o["Low"],
                                 close=o["Close"], name="USD/TRY (piyasa)",
                                 increasing_line_color=BORDO, decreasing_line_color=TEAL,
                                 increasing_fillcolor=rgba(BORDO, 0.55),
                                 decreasing_fillcolor=rgba(TEAL, 0.55)),
                  row=1, col=1)
    cizgi(fig, k, "TCMB gösterge kuru", MUREKKEP, row=1, w=1.3, dash="dot")
    renkler = [rgba(BORDO, 0.9) if v > 8 else rgba(MAVI, 0.75) for v in menzil.values]
    sutun(fig, menzil, "gün içi menzil (%)", MAVI, row=2, renkler=renkler, birim="%")
    koridor(fig, bas, bit, row=3)
    cizgi(fig, a, "AOFM (%)", BORDO, row=3, w=2.0)
    cizgi(fig, politika_gunluk(bas, bit), "politika faizi (%, ay sonu · PPK günü düzeltmeli)", MAVI, row=3, w=1.6,
          dash="dash", sekil="hv")

    for i, (tar, et) in enumerate([("2018-07-24", "24.07 · PPK faizi sabit bıraktı"),
                                   ("2018-08-10", "10.08 · dış ticaret tarifesi duyurusu"),
                                   ("2018-08-13", "13.08 · swap sınırı %50"),
                                   ("2018-08-15", "15.08 · swap sınırı %25"),
                                   ("2018-09-13", "13.09 · PPK +625 bp → %24")]):
        dikey(fig, tar, et, row=1, satir_sayisi=3, boyut=9,
              y_konum=1.0 if i % 2 == 0 else 0.74)
    zm = menzil.idxmax()
    not_(fig, zm, menzil.loc[zm],
         f"{zm.strftime('%d.%m.%Y')} — gün içi menzil %{menzil.loc[zm]:.1f} (yüksek {o['High'].loc[zm]:.4f})".replace(".", ","),
         row=2, ay=-34, boyut=10)
    t913 = pd.Timestamp("2018-09-13")
    if t913 in o.index:
        not_(fig, t913, o["Low"].loc[t913],
             f"13.09 gün içi {o['High'].loc[t913]:.4f} → {o['Low'].loc[t913]:.4f} (−%{100*(1-o['Low'].loc[t913]/o['High'].loc[t913]):.1f})".replace(".", ","),
             row=1, ay=48, boyut=10)

    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="TL / USD", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_yaxes(title_text="%", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Ağustos 2018, gün gün: resmî kur ile piyasa fiyatının ayrıldığı pencere",
          "15.07.2018 – 30.09.2018", 1000,
          alt="yfinance USDTRY=X (gün içi) · EVDS TP.DK.USD.A.YTL (resmî kayıt) · TP.APIFON4 · TP.PY.P01.ON/P02.ON")
    kaydet(fig, "13_agustos2018", "Ağustos 2018 krizi, gün gün", "2018-07 → 2018-09")


# ==========================================================================
#  14 — Rezervin üç tanımı
# ==========================================================================
def g14():
    bas, bit = "2010-01-01", "2026-08-07"
    h = D(tv.depo_haftalik_rezerv)
    brut = kes(h["brut_rezerv_usd"].dropna(), bas, bit)
    net = kes(h["net_rezerv_usd"].dropna(), bas, bit)
    swapsiz = kes(h["swap_haric_net_rezerv_usd"].dropna(), bas, bit)
    swap = kes(h["swap_duzeltme_usd"].dropna(), bas, bit)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.055,
                        subplot_titles=(
                            "Brüt uluslararası rezerv (mlr USD, haftalık)",
                            "Net rezerv ve swap hariç net rezerv (mlr USD) — aradaki mesafe swap stokudur",
                            "Swap düzeltmesi (mlr USD): net rezervden düşülen bankalarla yapılmış swap yükümlülüğü"))
    cizgi(fig, brut, "brüt rezerv", MOR, row=1, w=1.9)
    ort = net.index.intersection(swapsiz.index)
    fig.add_trace(go.Scatter(x=net.loc[ort].index, y=net.loc[ort].values, mode="lines",
                             line=dict(color=BORDO, width=1.9), name="net rezerv",
                             hovertemplate="%{y:.1f} mlr $<extra>net rezerv</extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=swapsiz.loc[ort].index, y=swapsiz.loc[ort].values, mode="lines",
                             line=dict(color=TEAL, width=1.9), fill="tonexty",
                             fillcolor=rgba(ALTIN, 0.22), name="swap hariç net rezerv",
                             hovertemplate="%{y:.1f} mlr $<extra>swap hariç net</extra>"), row=2, col=1)
    sifir_cizgisi(fig, row=2)
    sutun(fig, swap, "swap düzeltmesi (mlr USD)", ALTIN, row=3, birim=" mlr $")
    sifir_cizgisi(fig, row=3)

    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=3)
    d = swapsiz.idxmin()
    not_(fig, d, swapsiz.loc[d],
         f"{d.strftime('%d.%m.%Y')} — swap hariç net {swapsiz.loc[d]:.1f} mlr $".replace(".", ","),
         row=2, ay=44, boyut=10)
    z = brut.idxmax()
    not_(fig, z, brut.loc[z], f"{z.strftime('%d.%m.%Y')} — brüt zirve {brut.loc[z]:.0f} mlr $",
         row=1, ay=-32, boyut=10)
    ilk_negatif = swapsiz[swapsiz < 0]
    if len(ilk_negatif):
        t = ilk_negatif.index[0]
        not_(fig, t, swapsiz.loc[t], f"{t.strftime('%d.%m.%Y')} — swap hariç net ilk kez negatif",
             row=2, ay=-40, boyut=10)

    fig.update_yaxes(title_text="mlr USD", row=1)
    fig.update_yaxes(title_text="mlr USD", row=2)
    fig.update_yaxes(title_text="mlr USD", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Rezervin üç tanımı: hangi satıra baktığınız neyi göreceğinizi belirler",
          "01.01.2010 – 07.08.2026", 1000,
          alt="depo hattı TCMBNetRezerv/haftalik_rezerv.csv (TCMB analitik bilanço + IRFCL swap stoku)")
    kaydet(fig, "14_rezervin_uc_tanimi", "Rezervin üç tanımı (brüt / net / swap hariç net)",
           "2010-01 → 2026-08")


# ==========================================================================
#  15 — Mart 2019 sıkışması
# ==========================================================================
def g15():
    bas, bit = "2019-01-01", "2019-05-31"
    h = D(tv.depo_haftalik_rezerv)
    sw = kes(h["swap_haric_net_rezerv_usd"].dropna(), bas, bit)
    a = kes(aofm(), bas, bit)
    g = kes(gecelik(), bas, bit)
    k = kes(kur(), bas, bit)

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                        subplot_titles=(
                            "Swap hariç net rezerv (mlr USD, haftalık) — savunmanın bilançodaki bedeli",
                            "AOFM (%) — 22.03'te haftalık repo ihalelerinin durdurulmasıyla oluşan basamak",
                            "Bankalararası gecelik faiz, gerçekleşen ağırlıklı ortalama (%)",
                            "USD/TRY — TCMB gösterge kuru"))
    fig.add_trace(go.Scatter(x=sw.index, y=sw.values, mode="lines+markers", name="swap hariç net rezerv",
                             line=dict(color=MOR, width=2.0), marker=dict(size=6),
                             hovertemplate="%{y:.1f} mlr $<extra>swap hariç net</extra>"), row=1, col=1)
    cizgi(fig, a, "AOFM (%)", BORDO, row=2, w=2.2)
    cizgi(fig, g, "gecelik AOF (%)", TURUNCU, row=3, w=2.0)
    cizgi(fig, k, "USD/TRY", TEAL, row=4, w=2.2)

    for tar, et in [("2019-03-22", "22.03 · haftalık repo ihaleleri durduruldu"),
                    ("2019-03-27", "26–27.03 · yurt dışı TL likiditesi kilitlendi"),
                    ("2019-03-31", "31.03 · yerel seçim")]:
        dikey(fig, tar, et, row=1, satir_sayisi=4, boyut=9)
    z = sw.loc["2019-02-15":"2019-04-15"]
    if len(z):
        not_(fig, z.idxmax(), z.max(), f"{z.idxmax().strftime('%d.%m.%Y')} — {z.max():.1f} mlr $".replace(".", ","),
             row=1, ay=-32, boyut=10)
        not_(fig, z.idxmin(), z.min(), f"{z.idxmin().strftime('%d.%m.%Y')} — {z.min():.1f} mlr $".replace(".", ","),
             row=1, ay=42, boyut=10)
    for t in [pd.Timestamp("2019-03-21"), pd.Timestamp("2019-03-25")]:
        if t in a.index:
            not_(fig, t, a.loc[t], f"{t.strftime('%d.%m')} · AOFM %{a.loc[t]:.2f}".replace(".", ","),
                 row=2, ay=-28 if t.day == 25 else 34, boyut=9.5)
    not_(fig, pd.Timestamp("2019-03-27"), g.loc["2019-03-20":"2019-04-05"].max(),
         "Yurt dışı (offshore) gecelik TL swap faizi için atıflanabilir bir zaman serisi yok; "
         "burada yurt içi gecelik faiz gösterilmektedir.", row=3, ay=-46, boyut=9.5, ok=False)

    fig.update_yaxes(title_text="mlr USD", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_yaxes(title_text="%", row=3)
    fig.update_yaxes(title_text="TL / USD", row=4)
    fig.update_xaxes(title_text="tarih", row=4)
    duzen(fig, "Mart 2019: yurt dışı TL likiditesinin kesilmesi ve rezervde görünen bedel",
          "01.01.2019 – 31.05.2019", 1200,
          alt="depo hattı TCMBNetRezerv/haftalik_rezerv.csv · EVDS TP.APIFON4 · TP.PY.P06.ON · TP.DK.USD.A.YTL")
    kaydet(fig, "15_mart2019_sikisma", "Mart 2019 offshore sıkışması", "2019-01 → 2019-05")


# ==========================================================================
#  16 — 2020: rezerv erimesi ve kredi patlaması
# ==========================================================================
def g16():
    bas, bit = "2019-01-01", "2021-06-30"
    h = D(tv.depo_haftalik_rezerv)
    sw = kes(h["swap_haric_net_rezerv_usd"].dropna(), bas, bit)
    kr = S("krediler")["KREDI.L001"].dropna()
    buyume = (100 * (kr / kr.shift(13)) ** 4 - 100).dropna()   # 13 haftalık, yıllıklandırılmış
    buyume = kes(buyume, bas, bit)
    a = kes(aofm(), bas, bit)
    k = kes(kur(), bas, bit)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=(
                            "Swap hariç net rezerv (mlr USD, haftalık)",
                            "Toplam kredi hacmi — 13 haftalık büyümenin yıllıklandırılmış hâli (%)",
                            "AOFM (%), faiz koridoru (gölgeli) ve politika faizi (aylık, basamak)"))
    cizgi(fig, sw, "swap hariç net rezerv", MOR, row=1, w=2.0)
    sifir_cizgisi(fig, row=1)
    renkler = [rgba(BORDO, 0.85) if v > 50 else rgba(MAVI, 0.8) for v in buyume.values]
    sutun(fig, buyume, "kredi büyümesi (%, yıllıklandırılmış)", MAVI, row=2, renkler=renkler, birim="%")
    sifir_cizgisi(fig, row=2)
    koridor(fig, bas, bit, row=3)
    cizgi(fig, a, "AOFM (%)", BORDO, row=3, w=2.0)
    cizgi(fig, politika_gunluk(bas, bit), "politika faizi (%, ay sonu · PPK günü düzeltmeli)", MAVI, row=3, w=1.6,
          dash="dash", sekil="hv")

    for tar, et in [("2020-03-17", "17.03 · salgın tedbir paketi"),
                    ("2020-04-18", "18.04 · aktif rasyosu yürürlükte"),
                    ("2020-08-06", "06.08 · yurt dışı TL sıkışması"),
                    ("2020-11-19", "19.11 · PPK +475 bp, sadeleşme")]:
        dikey(fig, tar, et, row=1, satir_sayisi=3, boyut=9)
    d = sw.idxmin()
    not_(fig, d, sw.loc[d], f"{d.strftime('%d.%m.%Y')} — dip {sw.loc[d]:.1f} mlr $".replace(".", ","),
         row=1, ay=44, boyut=10)
    z = buyume.loc["2020-04-01":"2020-09-30"]
    if len(z):
        not_(fig, z.idxmax(), z.max(),
             f"{z.idxmax().strftime('%d.%m.%Y')} — %{z.max():.0f} yıllıklandırılmış kredi büyümesi",
             row=2, ay=-32, boyut=10)

    fig.update_yaxes(title_text="mlr USD", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_yaxes(title_text="%", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "2020: kredi genişlemesinin faturası rezervde kesildi",
          "01.01.2019 – 30.06.2021", 1000,
          alt="depo hattı TCMBNetRezerv/haftalik_rezerv.csv · EVDS TP.KREDI.L001 (haftalık, arşiv) · TP.APIFON4 · TP.PY.P01.ON/P02.ON")
    kaydet(fig, "16_2020_rezerv_kredi", "2020: rezerv erimesi ve kredi genişlemesi", "2019-01 → 2021-06")


# ==========================================================================
#  17 — Bilanço krizi: endeksler
# ==========================================================================
def g17():
    bas, bit = "2018-01-02", "2021-01-29"
    xu, xb = Y("XU100.IS"), Y("XBANK.IS")
    if xu is None or xb is None:
        ATLANAN.append("17 — bilanço krizi: XU100.IS / XBANK.IS çekilemedi")
        return
    t0 = "2018-01-02"
    x = kes(xu["Close"].dropna(), bas, bit)
    b = kes(xb["Close"].dropna(), bas, bit)
    k = kur().reindex(x.index.union(b.index)).ffill()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=("BIST-100 ve BIST Banka, TL bazında, 02.01.2018 = 100",
                                        "Aynı iki endeks dolar bazında (TCMB gösterge kuruyla deflate), 02.01.2018 = 100"))
    cizgi(fig, endeksle(x, t0), "BIST-100 (TL)", MAVI, row=1, w=1.9)
    cizgi(fig, endeksle(b, t0), "BIST Banka (TL)", BORDO, row=1, w=1.9)
    cizgi(fig, endeksle((x / k.reindex(x.index)).dropna(), t0), "BIST-100 (USD)", MAVI, row=2, w=1.9)
    cizgi(fig, endeksle((b / k.reindex(b.index)).dropna(), t0), "BIST Banka (USD)", BORDO, row=2, w=1.9)
    for r in (1, 2):
        fig.add_hline(y=100, line=dict(color=rgba(GRI, 0.6), width=1), row=r, col=1)
    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=2)

    bu = endeksle((b / k.reindex(b.index)).dropna(), t0)
    d1 = bu.loc["2018-08-01":"2018-10-01"].idxmin()
    d2 = bu.loc["2020-06-01":"2020-12-31"].idxmin()
    not_(fig, d1, bu.loc[d1], f"{d1.strftime('%d.%m.%Y')} — banka endeksi dolar bazında {bu.loc[d1]:.0f}",
         row=2, ay=44, boyut=10)
    not_(fig, d2, bu.loc[d2], f"{d2.strftime('%d.%m.%Y')} — {bu.loc[d2]:.0f}", row=2, ay=42, boyut=10)

    fig.update_yaxes(title_text="endeks (=100)", row=1)
    fig.update_yaxes(title_text="endeks (=100)", row=2)
    fig.update_xaxes(title_text="tarih", row=2)
    duzen(fig, "Bilanço krizinin fiyattaki karşılığı: TL bazında yatay, dolar bazında yarı yarıya",
          "02.01.2018 – 29.01.2021", 800,
          alt="yfinance XU100.IS / XBANK.IS · EVDS TP.DK.USD.A.YTL")
    kaydet(fig, "17_bilanco_krizi_endeksler", "BIST-100 ve BIST Banka: TL ve dolar bazında",
           "2018-01 → 2021-01")


# ==========================================================================
#  18 — 2021 spirali
# ==========================================================================
def g18():
    bas, bit = "2021-06-01", "2022-03-31"
    k = kes(kur(), bas, bit)
    t = kes(tufe_yoy(), "2021-01-01", "2022-06-30")
    p = kes(politika(), "2021-01-01", "2022-06-30")
    reel = (p.reindex(t.index).ffill() - t).dropna()
    tl = kes(S("tlref")["BISTTLREF.ORAN"].dropna(), "2021-11-01", "2022-01-31")
    a = kes(aofm(), "2021-11-01", "2022-01-31")
    ort = tl.index.intersection(a.index)
    spread = ((tl.loc[ort] - a.loc[ort]) * 100)
    h = D(tv.depo_haftalik_rezerv)
    hb = kes(h["brut_rezerv_usd"].dropna(), "2021-09-01", "2022-03-31")
    hn = kes(h["net_rezerv_usd"].dropna(), "2021-09-01", "2022-03-31")
    hs = kes(h["swap_haric_net_rezerv_usd"].dropna(), "2021-09-01", "2022-03-31")

    fig = make_subplots(rows=4, cols=1, shared_xaxes=False, vertical_spacing=0.075,
                        subplot_titles=(
                            "USD/TRY — TCMB gösterge kuru; dikey çizgiler faiz indirimi kararları",
                            "Politika faizi (basamak), TÜFE yıllık ve reel politika faizi (dolgu) — aylık",
                            "TLREF − AOFM farkı (baz puan) — gecelik piyasa faizinin fonlama maliyetinden sapması",
                            "Haftalık rezerv: brüt, net ve swap hariç net (mlr USD)"))
    cizgi(fig, k, "USD/TRY", TEAL, row=1, w=2.2)
    cizgi(fig, p, "politika faizi (%, ay sonu)", MAVI, row=2, w=2.0, sekil="hv")
    cizgi(fig, t, "TÜFE yıllık (%)", ALTIN, row=2, w=2.0)
    fig.add_trace(go.Scatter(x=reel.index, y=reel.values, name="reel politika faizi (%)",
                             mode="lines", line=dict(color=BORDO, width=2.0),
                             fill="tozeroy", fillcolor=rgba(BORDO, 0.18),
                             hovertemplate="%{y:.2f}%<extra>reel politika faizi</extra>"), row=2, col=1)
    sifir_cizgisi(fig, row=2)
    renkler = [rgba(TURUNCU, 0.95) if abs(v) > 100 else rgba(MOR, 0.8) for v in spread.values]
    sutun(fig, spread, "TLREF − AOFM (bp)", MOR, row=3, renkler=renkler, birim=" bp")
    sifir_cizgisi(fig, row=3)
    cizgi(fig, hb, "brüt rezerv", MOR, row=4, w=1.8)
    cizgi(fig, hn, "net rezerv", BORDO, row=4, w=1.8)
    cizgi(fig, hs, "swap hariç net rezerv", TEAL, row=4, w=1.8)
    sifir_cizgisi(fig, row=4)

    for i, (tar, et) in enumerate([("2021-09-23", "23.09 · −100 bp → %18"),
                                   ("2021-10-21", "21.10 · −200 bp → %16"),
                                   ("2021-11-18", "18.11 · −100 bp → %15"),
                                   ("2021-12-16", "16.12 · −100 bp → %14")]):
        dikey(fig, tar, et, row=1, boyut=9, y_konum=1.0 if i % 2 == 0 else 0.74)
    fig.add_vrect(x0=pd.Timestamp("2021-12-01"), x1=pd.Timestamp("2021-12-17"),
                  fillcolor=rgba(TURUNCU, 0.14), line_width=0, layer="below", row=1, col=1,
                  annotation_text="doğrudan döviz satım penceresi", annotation_position="top left",
                  annotation=dict(font=dict(size=9, color=TURUNCU)))
    z = k.loc["2021-12-15":"2021-12-25"]
    if len(z):
        onceki = z.idxmax() - pd.Timedelta(days=1)
        not_(fig, z.idxmax(), z.max(),
             f"{z.idxmax().strftime('%d.%m.%Y')} bülteni ({onceki.strftime('%d.%m')} 15:30 kotasyonu) — "
             f"{z.max():.4f}".replace(".", ","), row=1, ay=-34, boyut=10)
    dr = reel.loc["2021-06-01":"2022-03-31"]
    if len(dr):
        not_(fig, dr.idxmin(), dr.min(), f"{dr.idxmin().strftime('%m.%Y')} — reel politika faizi {dr.min():.1f} puan".replace(".", ","),
             row=2, ay=44, boyut=10)

    fig.update_yaxes(title_text="TL / USD", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_yaxes(title_text="baz puan", row=3)
    fig.update_yaxes(title_text="mlr USD", row=4)
    fig.update_xaxes(title_text="tarih", row=4)
    duzen(fig, "2021 spirali: reel faiz sıfırın çok altındayken yapılan indirimlerin fiyattaki karşılığı",
          "panel 1: 01.06.2021–31.03.2022 · panel 2: 01.2021–06.2022 · panel 3: 01.11.2021–31.01.2022 · panel 4: 01.09.2021–31.03.2022",
          1400, alt="EVDS TP.DK.USD.A.YTL · TP.BISPOLFAIZ.TUR · TÜFE · TP.BISTTLREF.ORAN · TP.APIFON4 · depo hattı haftalik_rezerv.csv")
    kaydet(fig, "18_2021_spirali", "2021 faiz indirimi spirali", "2021-06 → 2022-03")


# ==========================================================================
#  19 — KKM'nin hayat döngüsü
# ==========================================================================
def g19():
    k = kes(kur(), "2021-12-01", "2022-02-28")
    kk = S("kkm")
    dd = kk["KKM.K1"].dropna()
    tlk = kk["KKM.K4"].dropna()
    mev = mevduat_faizi()
    t = tufe_yoy()
    reel_mev = (mev - t.reindex(mev.index)).dropna().loc["2021-12-01":]

    fig = make_subplots(rows=3, cols=1, shared_xaxes=False, vertical_spacing=0.085,
                        specs=[[{"secondary_y": False}], [{"secondary_y": True}], [{"secondary_y": False}]],
                        subplot_titles=(
                            "USD/TRY — TCMB gösterge kuru, ilan penceresi",
                            "KKM stoku: dövizden dönüşümlü (mlr USD, sütun) ve TL kaynaklı (mlr TL, çizgi, sağ eksen)",
                            "Reel 3 aylık TL mevduat faizi (%, mevduat faizi − TÜFE yıllık) — ürünün ömrünü belirleyen değişken"))
    cizgi(fig, k, "USD/TRY", TEAL, row=1, w=2.4)
    sutun(fig, dd, "DDKKM (mlr USD)", TEAL, row=2, birim=" mlr $")
    fig.add_trace(go.Scatter(x=tlk.index, y=tlk.values, name="TL KKM (mlr TL)", mode="lines",
                             line=dict(color=ALTIN, width=2.2),
                             hovertemplate="%{y:,.0f} mlr TL<extra>TL KKM</extra>"),
                  row=2, col=1, secondary_y=True)
    renkler = [rgba(BORDO, 0.85) if v < 0 else rgba(YESIL, 0.85) for v in reel_mev.values]
    sutun(fig, reel_mev, "reel mevduat faizi (%)", YESIL, row=3, renkler=renkler, birim="%")
    sifir_cizgisi(fig, row=3)

    for i, (tar, et) in enumerate([("2021-12-20", "20.12 bülteni · dönem zirvesi"),
                                   ("2021-12-21", "21.12 · KKM ilanı")]):
        dikey(fig, tar, et, row=1, boyut=9, y_konum=1.0 if i == 0 else 0.62)
    z = dd.idxmax()
    not_(fig, z, dd.max(), f"{z.strftime('%m.%Y')} — DDKKM zirvesi {dd.max():.1f} mlr $".replace(".", ","),
         row=2, ay=-34, boyut=10)
    not_(fig, dd.index[0], dd.iloc[0], "ilan ayı: 0,7 mlr $ — asıl akım duyurudan aylar sonra geldi",
         row=2, ax=96, ay=-52, boyut=10, xanchor="left")
    ilk_pozitif = reel_mev[reel_mev > 0]
    if len(ilk_pozitif):
        kalici = None
        for i in range(len(reel_mev) - 5):
            if (reel_mev.iloc[i:i + 6] > 0).all():
                kalici = reel_mev.index[i]
                break
        if kalici is not None:
            not_(fig, kalici, reel_mev.loc[kalici],
                 f"{kalici.strftime('%m.%Y')} — reel mevduat faizi kalıcı olarak pozitif",
                 row=3, ay=-40, boyut=10)

    fig.update_yaxes(title_text="TL / USD", row=1)
    fig.update_yaxes(title_text="mlr USD", row=2, secondary_y=False)
    fig.update_yaxes(title_text="mlr TL", row=2, secondary_y=True, showgrid=False)
    fig.update_yaxes(title_text="%", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "KKM'nin hayat döngüsü: bir gecede kuru düşüren ürün, pozitif reel faiz dönünce eridi",
          "panel 1: 01.12.2021–28.02.2022 · panel 2–3: 12.2021–06.2026", 1150,
          alt="EVDS TP.KKM.K1/K4 · TP.MT210AGS.TRY.MT02 · TÜFE · TP.DK.USD.A.YTL")
    kaydet(fig, "19_kkm_hayat_dongusu", "KKM'nin hayat döngüsü", "2021-12 → 2026-06")


# ==========================================================================
#  20 — 2022 labirenti
# ==========================================================================
def g20():
    t = kes(tufe_yoy(), "2021-01-01", "2026-07-31")
    p = kes(politika(), "2021-01-01", "2026-07-31")
    mev = kes(mevduat_faizi(), "2021-01-01", "2026-07-31")
    reel_p = (p.reindex(t.index).ffill() - t).dropna()
    reel_m = (mev - t.reindex(mev.index)).dropna()
    xu = Y("XU100.IS")
    ya = yabanci_akim()
    dort = kes(ya[["hisse", "dibs"]].rolling(4).sum().dropna(), "2021-01-01", "2026-08-14")

    fig = make_subplots(rows=4, cols=1, shared_xaxes=False, vertical_spacing=0.07,
                        subplot_titles=(
                            "TÜFE yıllık (%) ve politika faizi (%, basamak) — aylık",
                            "Reel politika faizi ve reel 3 aylık mevduat faizi (%) — negatif alan taralı",
                            "BIST-100, TL ve dolar bazında, 31.12.2021 = 100 (günlük)",
                            "Yurt dışı yerleşiklerin net akımı, 4 haftalık toplam (mn USD): hisse ve DİBS"))
    cizgi(fig, t, "TÜFE yıllık (%)", ALTIN, row=1, w=2.0)
    cizgi(fig, p, "politika faizi (%, ay sonu)", MAVI, row=1, w=2.0, sekil="hv")
    fig.add_trace(go.Scatter(x=reel_p.index, y=reel_p.values, name="reel politika faizi (%)",
                             mode="lines", line=dict(color=BORDO, width=2.0),
                             fill="tozeroy", fillcolor=rgba(BORDO, 0.16),
                             hovertemplate="%{y:.2f}%<extra>reel politika faizi</extra>"), row=2, col=1)
    cizgi(fig, reel_m, "reel 3 aylık mevduat faizi (%)", TEAL, row=2, w=2.0)
    sifir_cizgisi(fig, row=2)
    if xu is not None:
        x = kes(xu["Close"].dropna(), "2021-12-31", "2026-08-20")
        k = kur().reindex(x.index).ffill()
        cizgi(fig, endeksle(x, "2021-12-31"), "BIST-100 (TL)", MAVI, row=3, w=1.9)
        cizgi(fig, endeksle((x / k).dropna(), "2021-12-31"), "BIST-100 (USD)", MOR, row=3, w=1.9)
        fig.add_hline(y=100, line=dict(color=rgba(GRI, 0.6), width=1), row=3, col=1)
    sutun(fig, dort["hisse"], "hisse (4 haftalık, mn USD)", MAVI, row=4, birim=" mn $")
    sutun(fig, dort["dibs"], "DİBS (4 haftalık, mn USD)", ALTIN, row=4, birim=" mn $")
    sifir_cizgisi(fig, row=4)
    fig.update_layout(barmode="relative")

    z = t.idxmax()
    not_(fig, z, t.max(), f"{z.strftime('%m.%Y')} — TÜFE zirvesi %{t.max():.2f}".replace(".", ","),
         row=1, ay=-32, boyut=10)
    dip = p.loc["2022-06-01":"2023-06-30"]
    if len(dip):
        not_(fig, dip.idxmin(), dip.min(), f"politika faizi dibi %{dip.min():.2f}".replace(".", ","),
             row=1, ay=40, boyut=10)
    dr = reel_p.loc["2021-06-01":"2023-12-31"]
    if len(dr):
        not_(fig, dr.idxmin(), dr.min(), f"{dr.idxmin().strftime('%m.%Y')} — {dr.min():.1f} puan".replace(".", ","),
             row=2, ay=42, boyut=10)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_yaxes(title_text="endeks (=100)", row=3)
    fig.update_yaxes(title_text="mn USD", row=4)
    fig.update_xaxes(title_text="tarih", row=4)
    duzen(fig, "2022 labirenti: enflasyon zirvesi, negatif reel faiz ve yabancı tabanının çekilmesi",
          "01.2021 – 08.2026", 1400,
          alt="EVDS TÜFE · TP.BISPOLFAIZ.TUR · TP.MT210AGS.TRY.MT02 · yfinance XU100.IS · TP.PYUK3/PYUK4 ve ForeignHoldings hattı")
    kaydet(fig, "20_2022_labirenti", "2022 labirenti: enflasyon, reel faiz, yabancı akımı",
           "2021-01 → 2026-08")


# ==========================================================================
#  21 — Tahvil piyasası: ihale ihale
# ==========================================================================
def g21():
    d = D(tv.depo_ihale)
    d = d.loc["2021-06-01":"2026-08-21"]
    d = d[d["Senet Tanımı"].astype(str).str.contains("Sabit Kuponlu|Hazine Bonosu", na=False)]
    d = d.copy()
    d["oran"] = pd.to_numeric(d["Ortalama Yıllık Bileşik(Gerçekleşme)"], errors="coerce")
    d["vade"] = pd.to_numeric(d["Vade (Yıl)"], errors="coerce")
    d["hacim"] = pd.to_numeric(d["Toplam(Gerçekleşme)"], errors="coerce")
    d["teklif"] = pd.to_numeric(d["Toplam(Teklif)"], errors="coerce")
    d = d.dropna(subset=["oran", "vade"])
    if not len(d):
        ATLANAN.append("21 — Hazine ihaleleri: filtrelenen pencerede ihale bulunamadı")
        return
    kisa = d[d["vade"] <= 2.5]
    uzun = d[d["vade"] >= 4.0]
    t = tufe_yoy().loc["2021-06-01":"2026-08-21"]
    karsilama = (100 * d["hacim"] / d["teklif"]).dropna()

    # ihale bazında eğim: aynı ay içindeki kısa ve uzun ihalelerin ortalama farkı
    ay_k = kisa.groupby(kisa.index.to_period("M"))["oran"].mean()
    ay_u = uzun.groupby(uzun.index.to_period("M"))["oran"].mean()
    ort_ay = ay_k.index.intersection(ay_u.index)
    egim = ((ay_k.loc[ort_ay] - ay_u.loc[ort_ay]) * 100)
    egim.index = egim.index.to_timestamp()

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=(
                            "Hazine ihalelerinde gerçekleşen ortalama yıllık bileşik faiz (%) — vade grubuna göre; arkada TÜFE yıllık",
                            "İhale bazında toplam gerçekleşme (mn TL)",
                            "Eğim: aylık ortalama kısa − uzun ihale faizi (baz puan); POZİTİF = ters eğim (kısa uç uzun ucun üstünde)"))
    cizgi(fig, t, "TÜFE yıllık (%)", ALTIN, row=1, w=1.4, dash="dot")
    fig.add_trace(go.Scatter(x=kisa.index, y=kisa["oran"], name="kısa vade (≤ 2,5 yıl)",
                             mode="lines+markers", line=dict(color=BORDO, width=1.5),
                             marker=dict(size=6),
                             hovertemplate="%{y:.2f}%<extra>kısa vade</extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=uzun.index, y=uzun["oran"], name="uzun vade (≥ 4 yıl)",
                             mode="lines+markers", line=dict(color=TEAL, width=1.5),
                             marker=dict(size=6),
                             hovertemplate="%{y:.2f}%<extra>uzun vade</extra>"), row=1, col=1)
    sutun(fig, d["hacim"].dropna(), "gerçekleşme (mn TL)", MAVI, row=2, birim=" mn TL")
    renkler = [rgba(BORDO, 0.85) if v < 0 else rgba(TEAL, 0.85) for v in egim.values]
    sutun(fig, egim, "kısa − uzun (bp)", TEAL, row=3, renkler=renkler, birim=" bp")
    sifir_cizgisi(fig, row=3)

    for tar, et in [("2022-08-20", "20.08.2022 · menkul kıymet tesisi yürürlükte"),
                    ("2023-06-22", "22.06.2023 · politika dönüşü"),
                    ("2025-03-19", "19.03.2025 · şok")]:
        dikey(fig, tar, et, row=1, satir_sayisi=3, boyut=9)
    dk = kisa["oran"].loc["2022-08-01":"2023-06-30"]
    if len(dk):
        not_(fig, dk.idxmin(), dk.min(),
             f"{dk.idxmin().strftime('%d.%m.%Y')} — kısa vade %{dk.min():.2f}, aynı ay TÜFE %{t.reindex([dk.idxmin()], method='ffill').iloc[0]:.0f}".replace(".", ","),
             row=1, ax=-30, ay=-64, boyut=10)
    if len(egim):
        not_(fig, egim.idxmax(), egim.max(),
             f"{egim.idxmax().strftime('%m.%Y')} — kısa uç uzun ucun {egim.max():,.0f} bp üstünde".replace(",", "."),
             row=3, ay=-34, boyut=10)
        not_(fig, egim.idxmin(), egim.min(),
             f"{egim.idxmin().strftime('%m.%Y')} — {egim.min():,.0f} bp (normal eğim)".replace(",", "."),
             row=3, ay=38, boyut=10)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="mn TL", row=2)
    fig.update_yaxes(title_text="baz puan", row=3)
    fig.update_xaxes(title_text="ihale tarihi", row=3)
    duzen(fig, "Tahvil piyasasının bozulması ve toparlanması: ihale ihale kayıt",
          "01.06.2021 – 21.08.2026", 1100,
          alt="depo hattı hazineihrac/hazine_ihale_verileri.csv (Hazine ihale sonuçları) · EVDS TÜFE")
    kaydet(fig, "21_tahvil_ihale", "Hazine ihalelerinde faiz, hacim ve eğim", "2021-06 → 2026-08")


# ==========================================================================
#  22 — 2023 dönüşü
# ==========================================================================
def g22():
    bas, bit = "2023-01-01", "2024-12-31"
    p = politika_gunluk(bas, bit)
    a = kes(aofm(), bas, bit)
    tl = kes(S("tlref")["BISTTLREF.ORAN"].dropna(), bas, bit)
    k = kes(kur(), bas, bit)
    t = kes(tufe_yoy(), bas, bit)
    h = D(tv.depo_haftalik_rezerv)
    hn = kes(h["net_rezerv_usd"].dropna(), bas, bit)
    hs = kes(h["swap_haric_net_rezerv_usd"].dropna(), bas, bit)
    ya = yabanci_akim()
    dort = kes(ya[["hisse", "dibs"]].rolling(4).sum().dropna(), bas, bit)

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        specs=[[{"secondary_y": False}], [{"secondary_y": True}],
                               [{"secondary_y": False}], [{"secondary_y": False}]],
                        subplot_titles=(
                            "Politika faizi (aylık, basamak), AOFM ve TLREF (%) — ilan ile gerçekleşen arasındaki gecikme",
                            "USD/TRY (sol) ve TÜFE yıllık (%, sağ eksen)",
                            "Haftalık rezerv: net ve swap hariç net (mlr USD)",
                            "Yurt dışı yerleşiklerin net akımı, 4 haftalık toplam (mn USD)"))
    cizgi(fig, p, "politika faizi (%, ay sonu · PPK günü düzeltmeli)", MAVI, row=1, w=2.0, sekil="hv")
    cizgi(fig, a, "AOFM (%)", BORDO, row=1, w=2.0)
    cizgi(fig, tl, "TLREF (%)", TURUNCU, row=1, w=1.4)
    fig.add_trace(go.Scatter(x=k.index, y=k.values, name="USD/TRY", mode="lines",
                             line=dict(color=TEAL, width=2.0),
                             hovertemplate="%{y:.4f}<extra>USD/TRY</extra>"),
                  row=2, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=t.index, y=t.values, name="TÜFE yıllık (%)", mode="lines",
                             line=dict(color=ALTIN, width=2.0, dash="dot"),
                             hovertemplate="%{y:.2f}%<extra>TÜFE yıllık</extra>"),
                  row=2, col=1, secondary_y=True)
    cizgi(fig, hn, "net rezerv", BORDO, row=3, w=1.9)
    cizgi(fig, hs, "swap hariç net rezerv", TEAL, row=3, w=1.9)
    sifir_cizgisi(fig, row=3)
    sutun(fig, dort["hisse"], "hisse (4 haftalık)", MAVI, row=4, birim=" mn $")
    sutun(fig, dort["dibs"], "DİBS (4 haftalık)", ALTIN, row=4, birim=" mn $")
    sifir_cizgisi(fig, row=4)
    fig.update_layout(barmode="relative")

    for tar, et in [("2023-06-22", "22.06.2023 · politika dönüşü (+650 bp)"),
                    ("2023-08-24", "24.08.2023 · +750 bp"),
                    ("2024-03-21", "21.03.2024 · +500 bp"),
                    ("2024-03-31", "31.03.2024 · yerel seçim")]:
        dikey(fig, tar, et, row=1, satir_sayisi=4, boyut=9)
    for t_ in [pd.Timestamp("2023-06-22"), pd.Timestamp("2023-07-06")]:
        if t_ in a.index:
            not_(fig, t_, a.loc[t_], f"{t_.strftime('%d.%m')} · AOFM %{a.loc[t_]:.2f}".replace(".", ","),
                 row=1, ay=40, boyut=9.5)
    d = hs.idxmin()
    not_(fig, d, hs.loc[d], f"{d.strftime('%d.%m.%Y')} — swap hariç net {hs.loc[d]:.1f} mlr $".replace(".", ","),
         row=3, ay=44, boyut=10)
    son = hs.dropna().index[-1]
    not_(fig, son, hs.loc[son], f"{son.strftime('%d.%m.%Y')} — {hs.loc[son]:.1f} mlr $".replace(".", ","),
         row=3, ay=-32, boyut=10, xanchor="right")

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="TL / USD", row=2, secondary_y=False)
    fig.update_yaxes(title_text="%", row=2, secondary_y=True, showgrid=False)
    fig.update_yaxes(title_text="mlr USD", row=3)
    fig.update_yaxes(title_text="mn USD", row=4)
    fig.update_xaxes(title_text="tarih", row=4)
    duzen(fig, "2023 dönüşü: ilan edilen faiz ile gerçekleşen fonlama maliyeti arasındaki geçiş penceresi",
          "01.01.2023 – 31.12.2024", 1400,
          alt="EVDS TP.BISPOLFAIZ.TUR · TP.APIFON4 · TP.BISTTLREF.ORAN · TP.DK.USD.A.YTL · TÜFE · depo hatları")
    kaydet(fig, "22_2023_donusu", "2023 politika dönüşü", "2023-01 → 2024-12")


# ==========================================================================
#  23 — 19 Mart 2025
# ==========================================================================
def g23():
    bas, bit = "2025-03-03", "2025-04-30"
    k = kes(kur(), bas, bit)
    yu = Y("USDTRY=X")
    xu, xb = Y("XU100.IS"), Y("XBANK.IS")
    fon = kes(S("api")["APIFON3"].dropna(), bas, bit) / 1000.0   # mn TL → mlr TL
    g = D(tv.depo_gunluk_rezerv)
    sw = kes(g["swap_haric_net_rezerv_usd"].dropna(), bas, bit)

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                        subplot_titles=(
                            "USD/TRY: TCMB resmî alış kuru (çizgi) ve piyasa gün içi en yükseği (nokta)",
                            "BIST-100 ve BIST Banka, 18.03.2025 = 100",
                            "TCMB net fonlaması (mlr TL) — negatif = sistem fazlası, pozitif = TCMB fonluyor",
                            "Swap hariç net rezerv (mlr USD, günlük)"))
    cizgi(fig, k, "TCMB resmî kur", TEAL, row=1, w=2.4)
    if yu is not None:
        hi = kes(yu["High"].dropna(), bas, bit)
        fig.add_trace(go.Scatter(x=hi.index, y=hi.values, name="piyasa gün içi en yükseği",
                                 mode="markers", marker=dict(color=BORDO, size=6, symbol="triangle-up"),
                                 hovertemplate="%{y:.4f}<extra>gün içi yüksek</extra>"), row=1, col=1)
        t19 = pd.Timestamp("2025-03-19")
        if t19 in hi.index:
            not_(fig, t19, hi.loc[t19],
                 f"19.03.2025 gün içi {hi.loc[t19]:.3f} — aynı gün resmî kur {k.reindex([t19]).ffill().iloc[0]:.3f}".replace(".", ","),
                 row=1, ay=-38, boyut=10)
    if xu is not None and xb is not None:
        x = endeksle(kes(xu["Close"].dropna(), bas, bit), "2025-03-18")
        b = endeksle(kes(xb["Close"].dropna(), bas, bit), "2025-03-18")
        cizgi(fig, x, "BIST-100", MAVI, row=2, w=2.2)
        cizgi(fig, b, "BIST Banka", BORDO, row=2, w=2.2)
        fig.add_hline(y=100, line=dict(color=rgba(GRI, 0.6), width=1), row=2, col=1)
        db = b.loc["2025-03-19":"2025-03-31"]
        if len(db):
            not_(fig, db.idxmin(), db.min(),
                 f"{db.idxmin().strftime('%d.%m')} — banka endeksi {db.min()-100:+.1f}%", row=2, ay=42, boyut=10)
    renkler = [rgba(BORDO, 0.85) if v > 0 else rgba(TEAL, 0.85) for v in fon.values]
    sutun(fig, fon, "net fonlama (mlr TL)", MOR, row=3, renkler=renkler, birim=" mlr TL")
    sifir_cizgisi(fig, row=3)
    cizgi(fig, sw, "swap hariç net rezerv", MOR, row=4, w=2.2)

    for tar, et in [("2025-03-19", "19.03 · beklenmedik iç şok"),
                    ("2025-03-20", "20.03 · ara PPK: gecelik borç verme %46"),
                    ("2025-04-17", "17.04 · PPK +350 bp")]:
        dikey(fig, tar, et, row=1, satir_sayisi=4, boyut=9)
    if len(sw):
        not_(fig, sw.index[0], sw.iloc[0], f"{sw.index[0].strftime('%d.%m')} — {sw.iloc[0]:.1f} mlr $".replace(".", ","),
             row=4, ay=-30, boyut=10)
        not_(fig, sw.idxmin(), sw.min(), f"{sw.idxmin().strftime('%d.%m')} — dip {sw.min():.1f} mlr $".replace(".", ","),
             row=4, ay=44, boyut=10)

    fig.update_yaxes(title_text="TL / USD", row=1)
    fig.update_yaxes(title_text="endeks (18.03 = 100)", row=2)
    fig.update_yaxes(title_text="mlr TL", row=3)
    fig.update_yaxes(title_text="mlr USD", row=4)
    fig.update_xaxes(title_text="tarih", row=4)
    duzen(fig, "19 Mart 2025: resmî kur ilk gün bilgi taşımadı — gün içi fiyat, banka hissesi ve bilanço konuştu",
          "03.03.2025 – 30.04.2025", 1150,
          alt="EVDS TP.DK.USD.A.YTL · TP.APIFON3 · yfinance USDTRY=X / XU100.IS / XBANK.IS · depo hattı TCMBNetRezerv/gunluk.csv")
    kaydet(fig, "23_mart2025", "19 Mart 2025 şokunun anatomisi", "2025-03 → 2025-04")


# ==========================================================================
#  24 — Program panosu
# ==========================================================================
def g24():
    bas, bit = "2024-01-01", "2026-08-21"
    p = politika_gunluk(bas, bit)
    a = kes(aofm(), bas, bit)
    t = kes(tufe_yoy(), bas, bit)
    bek = kes(S("beklenti")["ENFBEK.PKA12ENF"].dropna(), bas, bit)
    r = D(tv.depo_reer)
    cpi = kes(r["CPI_REER"].dropna(), bas, bit)
    ma = kes(r["CPI_MA_10Y"].dropna(), bas, bit)
    g = D(tv.depo_gunluk_rezerv)
    sw = kes(g["swap_haric_net_rezerv_usd"].dropna(), bas, bit)
    brut = kes(g["brut_usd"].dropna(), bas, bit)

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=(
                            "Politika faizi (aylık, basamak) ve AOFM (%)",
                            "TÜFE yıllık (%) ve piyasa katılımcılarının 12 ay sonrası enflasyon beklentisi (%)",
                            "TÜFE bazlı reel efektif döviz kuru ve 10 yıllık ortalaması",
                            "Swap hariç net rezerv ve brüt rezerv (mlr USD, günlük)"))
    cizgi(fig, p, "politika faizi (%, ay sonu · PPK günü düzeltmeli)", MAVI, row=1, w=2.0, sekil="hv")
    cizgi(fig, a, "AOFM (%)", BORDO, row=1, w=2.0)
    cizgi(fig, t, "TÜFE yıllık (%)", ALTIN, row=2, w=2.2)
    cizgi(fig, bek, "12 ay sonrası beklenti (%)", TEAL, row=2, w=2.0, dash="dash")
    cizgi(fig, cpi, "TÜFE bazlı REDK", TEAL, row=3, w=2.2)
    cizgi(fig, ma, "10 yıllık ortalama", GRI, row=3, w=1.6, dash="dash")
    cizgi(fig, brut, "brüt rezerv", GRI, row=4, w=1.6)
    cizgi(fig, sw, "swap hariç net rezerv", MOR, row=4, w=2.2)
    sifir_cizgisi(fig, row=4)

    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=4)
    for tar, et in [("2024-03-31", "31.03.2024 · yerel seçim"),
                    ("2025-03-19", "19.03.2025 · iç şok"),
                    ("2026-02-28", "28.02.2026 · dış şok")]:
        dikey(fig, tar, et, row=1, satir_sayisi=4, boyut=9, renk=MUREKKEP)
    son_t = t.dropna().index[-1]
    not_(fig, son_t, t.loc[son_t], f"{son_t.strftime('%m.%Y')} — TÜFE %{t.loc[son_t]:.1f}".replace(".", ","),
         row=2, ay=-32, boyut=10, xanchor="right")
    d = sw.idxmin()
    not_(fig, d, sw.loc[d], f"{d.strftime('%d.%m.%Y')} — dip {sw.loc[d]:.1f} mlr $".replace(".", ","),
         row=4, ay=44, boyut=10)
    z = sw.idxmax()
    not_(fig, z, sw.loc[z], f"{z.strftime('%d.%m.%Y')} — zirve {sw.loc[z]:.1f} mlr $".replace(".", ","),
         row=4, ay=-30, boyut=10)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_yaxes(title_text="endeks (2003 = 100)", row=3)
    fig.update_yaxes(title_text="mlr USD", row=4)
    fig.update_xaxes(title_text="tarih", row=4)
    duzen(fig, "Dezenflasyon programının panosu: faiz, enflasyon, reel kur ve rezerv aynı ekranda",
          "01.01.2024 – 21.08.2026", 1400,
          alt="EVDS TP.BISPOLFAIZ.TUR · TP.APIFON4 · TÜFE · TP.ENFBEK.PKA12ENF · depo hatları TRYREER ve TCMBNetRezerv/gunluk.csv")
    kaydet(fig, "24_program_panosu", "Dezenflasyon programı panosu", "2024-01 → 2026-08")


# ==========================================================================
#  25 — Reel faiz örüntüsü
# ==========================================================================
def g25():
    g = gecelik().resample("MS").mean()
    t = tufe_yoy()
    ort = g.index.intersection(t.index)
    reel = (g.loc[ort] - t.loc[ort]).dropna()
    reel = reel.loc["1989-01-01":]
    k = kur().resample("MS").last()
    ileri = (100 * (k.shift(-12) / k - 1)).dropna()
    ortak = reel.index.intersection(ileri.index)
    x = reel.loc[ortak]
    y = ileri.loc[ortak]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.11,
                        subplot_titles=(
                            "Ex-post reel gecelik faiz (%): aylık ortalama gecelik faiz − TÜFE yıllık; negatif bölge taralı",
                            "Örüntü: reel gecelik faiz (yatay) ile sonraki 12 aydaki USD/TRY değişimi (dikey) — her nokta bir ay"))
    fig.add_trace(go.Scatter(x=reel.index, y=reel.values, name="reel gecelik faiz (%)",
                             mode="lines", line=dict(color=BORDO, width=1.8),
                             fill="tozeroy", fillcolor=rgba(BORDO, 0.16),
                             hovertemplate="%{y:.1f}%<extra>reel gecelik faiz</extra>"), row=1, col=1)
    sifir_cizgisi(fig, row=1)
    epizot_bantlari(fig, "1989-01-01", "2026-08-21", etiket_satiri=1, satir_sayisi=1)
    # Kriz aylarındaki gecelik faiz sıçramaları ekseni ezdiği için üst sınır kırpılır;
    # kırpılan gözlemler metinle açıkça anılır (veri silinmez, yalnızca eksen kısaltılır).
    Y_UST, Y_ALT = 90, -70
    tasan = reel[reel > Y_UST]
    fig.update_yaxes(range=[Y_ALT, Y_UST], row=1)
    if len(tasan):
        ilk_iki = tasan.sort_values(ascending=False).head(2)
        metin = " · ".join(f"{d.strftime('%m.%Y')}: +%{v:,.0f}".replace(",", ".")
                           for d, v in ilk_iki.items())
        fig.add_annotation(x=pd.Timestamp("2003-06-01"), y=72, row=1, col=1, showarrow=False,
                           yanchor="top", xanchor="left",
                           text=f"eksen okunabilirlik için %{Y_UST}'de kırpıldı — kriz aylarındaki zirveler: {metin} "
                                f"(toplam {len(tasan)} ay eksenin üstünde)",
                           font=dict(size=10, color=MUREKKEP), bgcolor="rgba(255,255,255,0.85)",
                           bordercolor=rgba(MUREKKEP, 0.3), borderwidth=0.8, borderpad=3)

    # Saçılımda da kriz ayları eksenleri eziyor: pencere kırpılır, kırpılan gözlem sayısı yazılır.
    XA, XU_, YA, YU = -70, 60, -40, 180
    icinde = (x >= XA) & (x <= XU_) & (y >= YA) & (y <= YU)
    on_yil = x.index.year // 10 * 10
    renk_harita = {1980: GRI, 1990: BORDO, 2000: MAVI, 2010: TEAL, 2020: TURUNCU}
    for dk in sorted(set(on_yil)):
        m = (on_yil == dk) & icinde.values
        if not m.any():
            continue
        fig.add_trace(go.Scatter(x=x[m].values, y=y[m].values, mode="markers",
                                 name=f"{dk}'lar", marker=dict(size=6, opacity=0.72,
                                                               color=renk_harita.get(dk, GRI)),
                                 customdata=[d.strftime("%m.%Y") for d in x[m].index],
                                 hovertemplate="%{customdata}<br>reel faiz %{x:.1f}% · sonraki 12 ay kur %{y:.1f}%<extra></extra>"),
                      row=2, col=1)
    # Uyum doğrusu görünen (kırpılmış) örneklem üzerinde; sıra korelasyonu ise TÜM örneklem
    # üzerinde raporlanır — sıra korelasyonu uç gözlemlerden etkilenmez.
    if icinde.sum() > 24:
        xi, yi = x[icinde.values], y[icinde.values]
        egim, kesim = np.polyfit(xi.values, yi.values, 1)
        xs = np.linspace(XA, XU_, 50)
        rho = float(pd.Series(x.values).rank().corr(pd.Series(y.values).rank()))
        fig.add_trace(go.Scatter(x=xs, y=egim * xs + kesim, mode="lines",
                                 name="doğrusal uyum (görünen örneklem)",
                                 line=dict(color=MUREKKEP, width=1.8, dash="dash"),
                                 hoverinfo="skip"), row=2, col=1)
        fig.add_annotation(x=XU_, y=YU, row=2, col=1, showarrow=False, xanchor="right", yanchor="top",
                           text=(f"eğim {egim:.2f} (görünen örneklem, n = {int(icinde.sum())}) · "
                                 f"Spearman sıra korelasyonu {rho:.2f} (tüm örneklem, n = {len(x)}) · "
                                 f"eksen dışında {len(x) - int(icinde.sum())} kriz ayı").replace(".", ","),
                           font=dict(size=10, color=MUREKKEP),
                           bgcolor="rgba(255,255,255,0.85)", bordercolor=rgba(MUREKKEP, 0.35),
                           borderwidth=0.8, borderpad=3)
    fig.update_xaxes(range=[XA, XU_], row=2)
    fig.update_yaxes(range=[YA, YU], row=2)
    fig.add_vline(x=0, line=dict(color=rgba(MUREKKEP, 0.5), width=1.2, dash="dot"), row=2, col=1)
    fig.add_hline(y=0, line=dict(color=rgba(MUREKKEP, 0.5), width=1.2, dash="dot"), row=2, col=1)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(title_text="sonraki 12 ayda USD/TRY değişimi (%)", row=2)
    fig.update_xaxes(title_text="tarih", row=1)
    fig.update_xaxes(title_text="reel gecelik faiz (%)", row=2)
    duzen(fig, "Reel faiz ile sonraki yılın kur değişimi: otuz yedi yılın saçılımı",
          "01.1989 – 08.2026 (saçılımda sonraki 12 ay gözlemi olan aylar: 01.1989 – 08.2025)", 950,
          alt="EVDS TP.PY.P06.ON (aylık ortalama) · TÜFE · TP.DK.USD.A.YTL — ilişki ölçümdür, nedensellik iddiası değildir")
    kaydet(fig, "25_reel_faiz_oruntusu", "Reel faiz ve sonraki 12 ay kur değişimi", "1989-01 → 2026-08")


# ==========================================================================
#  26 — EM karşılaştırması
# ==========================================================================
def g26():
    bas, bit = "2013-01-01", "2026-08-20"
    pariteler = [("USDTRY=X", "kur · TRY", BORDO), ("ZAR=X", "kur · ZAR", MAVI),
                 ("MXN=X", "kur · MXN", TEAL), ("BRL=X", "kur · BRL", ALTIN),
                 ("INR=X", "kur · INR", MOR)]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.10,
                        subplot_titles=(
                            "Dolar karşısında seçilmiş gelişmekte olan piyasa paraları, 02.01.2013 = 100, logaritmik — yukarı = yerel para değer kaybı",
                            "Aynı ülkelerin politika faizi (%, aylık) — BIS derlemesi"))
    var = False
    for sem, ad, renk in pariteler:
        d = Y(sem, "2010-01-01")
        if d is None:
            ATLANAN.append(f"26 — EM karşılaştırma: {sem} çekilemedi, o para birimi çizilmedi")
            continue
        s = endeksle(kes(d["Close"].dropna(), bas, bit), "2013-01-02")
        cizgi(fig, s, ad, renk, row=1, w=2.1 if "TRY" in ad else 1.4)
        var = True
    if not var:
        ATLANAN.append("26 — EM karşılaştırma: hiçbir parite çekilemedi, grafik üretilmedi")
        return
    fig.add_hline(y=100, line=dict(color=rgba(GRI, 0.6), width=1), row=1, col=1)

    pf = S("polfaiz")
    for kod, ad, renk in [("BISPOLFAIZ.TUR", "politika faizi · Türkiye", BORDO),
                          ("BISPOLFAIZ.ZAF", "politika faizi · G. Afrika", MAVI),
                          ("BISPOLFAIZ.MEX", "politika faizi · Meksika", TEAL),
                          ("BISPOLFAIZ.BRA", "politika faizi · Brezilya", ALTIN),
                          ("BISPOLFAIZ.IND", "politika faizi · Hindistan", MOR)]:
        if kod in pf.columns:
            cizgi(fig, kes(pf[kod].dropna(), bas, bit), ad, renk, row=2,
                  w=2.0 if "TUR" in kod else 1.4)

    epizot_bantlari(fig, bas, bit, etiket_satiri=1, satir_sayisi=1)
    d = Y("USDTRY=X", "2010-01-01")
    if d is not None:
        s = endeksle(kes(d["Close"].dropna(), bas, bit), "2013-01-02")
        son = s.dropna().index[-1]
        not_(fig, son, np.log10(s.loc[son]), f"TRY {s.loc[son]:,.0f}".replace(",", "."),
             row=1, ay=-28, boyut=10, xanchor="right")

    fig.update_yaxes(type="log", title_text="endeks (log, 2013 = 100)", row=1)
    fig.update_yaxes(title_text="%", row=2)
    fig.update_xaxes(title_text="tarih", row=1)
    fig.update_xaxes(title_text="tarih", row=2)
    duzen(fig, "Şok yerel mi küresel mi? Aynı pencerede bir gelişmekte olan piyasa sepeti",
          "02.01.2013 – 20.08.2026", 950,
          alt="yfinance USDTRY=X / ZAR=X / MXN=X / BRL=X / INR=X · EVDS TP.BISPOLFAIZ.* (BIS derlemesi)")
    kaydet(fig, "26_em_karsilastirma", "TRY ve EM paraları, politika faizleri", "2013-01 → 2026-08")


# ==========================================================================
FIGURLER = [g01, g02, g03, g04, g05, g06, g07, g08, g09, g10, g11, g12, g13,
            g14, g15, g16, g17, g18, g19, g20, g21, g22, g23, g24, g25, g26]


def main():
    print(f"Çıktı: {CIKTI}")
    for f in FIGURLER:
        try:
            f()
        except Exception as e:                      # bir figür patlarsa diğerleri üretilsin
            import traceback
            ATLANAN.append(f"{f.__name__} — HATA: {e}")
            traceback.print_exc()
    print(f"\n{len(URETILEN)} grafik üretildi.")
    for ad, baslik, pencere in URETILEN:
        print(f"  {ad:34s} {baslik}  [{pencere}]")
    if ATLANAN:
        print("\nAtlananlar / uyarılar:")
        for s in ATLANAN:
            print("  ·", s)


if __name__ == "__main__":
    main()
