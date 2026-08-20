#!/usr/bin/env python3
"""SMC dersi — DERİNLEŞTİRME ek grafik seti (29 şekil).

Şekil numaraları sayfadaki OKUMA SIRASINA göredir (01–57 aralığına serpiştirilmiş);
dosya adı = şekil numarası. İlk baskının 28 şeklini smc_grafikler.py üretir.

Tek komut:  python3 site/tools/ders_grafik/smc_grafikler_ek.py
Çıktı:      site/public/arastirma/smc-teknik-analiz/29_*.html … 57_*.html

Mevcut `smc_grafikler.py` DEĞİŞTİRİLMEZ; buradaki grafikler onun yardımcı
fonksiyonlarını (palet, Seri, mum_izi, kutu, not_, duzen, kaydet, fib_ciz…)
import ederek aynı görsel dili kullanır ve aynı klasöre, mevcut numaraların
ARDINDAN yazar. Mevcut 01–27 + 16b dosyalarına dokunulmaz.

Sentetik seriler sabit tohumla deterministiktir. Gerçek veri gereken üç
grafikte (39, 40, 57) `_veri/` önbelleği kullanılır; önbellek yoksa yfinance'ten
indirilip önbelleğe yazılır. İndirilemezse o grafik ATLANIR ve raporlanır —
sahte "gerçek veri" üretilmez.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.filterwarnings("ignore")

from smc_grafikler import (  # noqa: E402
    CIKTI, TEAL, BORDO, ALTIN, MAVI, MOR, TURUNCU, GRI, MUREKKEP,
    rgba, Seri, swingler, fvg_bul, mum_izi, kutu, yatay, not_, daire,
    lejant, lejant_cizgi, duzen, kaydet, fib_ciz,
)
import smc_grafikler as sg  # noqa: E402

VERI = Path(__file__).resolve().parent / "_veri"
VERI.mkdir(parents=True, exist_ok=True)
YENILE = "--yenile" in sys.argv

URETILEN: list[str] = []
RAPOR: list[str] = []
OZET: dict = {}

YESIL = "#15803d"
KIRMIZI = "#b91c1c"
LACIVERT = "#1e3a8a"


def _alt_baslik_sar(fig, genislik: int = 138):
    """duzen() alt başlığı <sup> içine koyar; Plotly başlıkları sarmadığı için
    ~800 px iframe'de uzun alt başlıklar kırpılır. Burada kelime sınırından bölünür."""
    t = getattr(fig.layout.title, "text", None)
    if not t or "<sup" not in t:
        return
    bas, _, kalan = t.partition("<sup")
    ac, _, geri = kalan.partition(">")
    ic, _, son = geri.rpartition("</sup>")
    parcalar = []
    for blok in ic.split("<br>"):
        satir = ""
        for kelime in blok.split(" "):
            if satir and len(satir) + 1 + len(kelime) > genislik:
                parcalar.append(satir)
                satir = kelime
            else:
                satir = f"{satir} {kelime}".strip()
        parcalar.append(satir)
    fig.layout.title.text = f"{bas}<sup{ac}>" + "<br>".join(parcalar) + f"</sup>{son}"
    satir = len(parcalar)
    if satir < 2:
        return
    # plotly_stil.py yayında margin.t'yi 92 px'e sabitler; çok satırlı alt başlık
    # make_subplots panel başlıklarıyla çakışmasın diye çizim alanı aşağı kaydırılır.
    # Panel başlıkları paper-referanslıdır → domain ile birlikte onlar da kaydırılır.
    panel = [a for a in fig.layout.annotations
             if getattr(a, "yanchor", None) == "bottom"
             and str(getattr(a, "yref", "")) == "paper"
             and str(getattr(a, "xref", "")) in ("paper", "x domain")
             and getattr(a, "showarrow", True) is False]
    if not panel:
        return
    f = 1.0 - 0.055 * (satir - 1)
    for ax in fig.select_yaxes():
        d = getattr(ax, "domain", None)
        if d:
            ax.domain = (d[0] * f, d[1] * f)
    for a in panel:
        if a.y is not None:
            a.y = a.y * f


def _kaydet(fig, ad: str):
    _alt_baslik_sar(fig)
    kaydet(fig, ad)
    URETILEN.append(ad + ".html")


# ---------------------------------------------------------------- gerçek veri (önbellekli)
def veri_yukle(ticker: str, interval: str, period: str):
    """_veri/ altında CSV önbelleği; yoksa yfinance. Dönüş: (df[o,h,l,c,ts], kaynak) ya da (None, None)."""
    ad = f"{ticker.replace('=', '_').replace('^', '')}_{interval}.csv"
    yol = VERI / ad
    ham = None
    kaynak = None
    if yol.exists() and not YENILE:
        ham = pd.read_csv(yol, index_col=0, parse_dates=True)
        kaynak = f"önbellek ({ad})"
    else:
        try:
            import yfinance as yf
            ham = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
            if isinstance(ham.columns, pd.MultiIndex):
                ham.columns = ham.columns.get_level_values(0)
            ham = ham[["Open", "High", "Low", "Close"]].dropna()
            if len(ham) < 100:
                raise RuntimeError(f"çok az veri ({len(ham)} bar)")
            ham.to_csv(yol)
            kaynak = "yfinance (indirildi)"
        except Exception as e:  # noqa
            RAPOR.append(f"GERÇEK VERİ ATLANDI: {ticker} {interval} — {e}")
            return None, None
    ts = pd.to_datetime(ham.index)
    df = pd.DataFrame(dict(o=ham["Open"].values, h=ham["High"].values,
                           l=ham["Low"].values, c=ham["Close"].values))
    df["ts"] = ts.tz_localize(None) if getattr(ts, "tz", None) is None else ts.tz_convert("UTC").tz_localize(None)
    df["lab"] = ""
    return df.dropna().reset_index(drop=True), kaynak


def zaman_ekseni(fig, df, adet=10, fmt="%d %b", row=None, col=None):
    n = len(df)
    adimlar = list(range(0, n, max(1, n // adet)))
    fig.update_xaxes(tickvals=adimlar, ticktext=[df.ts[i].strftime(fmt) for i in adimlar],
                     tickangle=0, tickfont=dict(size=10), row=row, col=col)


def hover_ts(df, fmt="%Y-%m-%d %H:%M"):
    return [f"{t:{fmt}}" for t in df.ts]


# ---------------------------------------------------------------- diyagram yardımcıları
def d_kutu(fig, x0, x1, y0, y1, metin, renk, a=0.16, boyut=11, kalin=False, row=None, col=None,
           yazi_renk=None, cizgi=1.2, dash=None):
    """Akış şeması / merdiven kutusu: dolgu + kenar + ortalanmış metin."""
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=rgba(renk, a),
                  line=dict(color=renk, width=cizgi, dash=dash), layer="below", row=row, col=col)
    fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=(f"<b>{metin}</b>" if kalin else metin),
                       showarrow=False, font=dict(size=boyut, color=yazi_renk or MUREKKEP),
                       align="center", row=row, col=col)


def d_ok(fig, x0, y0, x1, y1, renk=MUREKKEP, w=1.6, row=None, col=None, dash=None):
    fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowsize=1.0, arrowwidth=w, arrowcolor=renk,
                       text="", row=row, col=col)
    if dash:
        fig.add_shape(type="line", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(color=renk, width=w, dash=dash), row=row, col=col)


def temiz_eksen(fig, row=None, col=None, x=None, y=None):
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, title_text="",
                     range=x, row=row, col=col)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, title_text="",
                     range=y, row=row, col=col)


# =====================================================================================
# 29 — IPDA 20/40/60 lookback kutuları (çoklu ufuklu Donchian)
# =====================================================================================
def g29_ipda():
    s = Seri(29, baslangic=92.0, birim=0.55)
    s.bacak(89.5, 5); s.bacak(88.0, 5, lab="60 günlük kutunun dibi")
    s.bacak(108.0, 16); s.bacak(96.5, 9); s.bacak(110.0, 11, lab="60 günlük kutunun tepesi")
    s.bacak(99.5, 11); s.bacak(103.0, 5); s.bacak(100.5, 8, lab="bugün")
    df = s.df(); n = len(df)
    P = df.c[n - 1]
    kutular = []
    for N, renk, a in ((60, GRI, 0.07), (40, MAVI, 0.07), (20, TEAL, 0.09)):
        seg = df.iloc[n - N:]
        H, L = seg.h.max(), seg.l.min()
        kutular.append(dict(N=N, H=H, L=L, EQ=(H + L) / 2, yuzde=(P - L) / (H - L) * 100, renk=renk, a=a, i0=n - N))
    fig = go.Figure(mum_izi(df, ad="günlük mum"))
    for k in kutular:
        kutu(fig, k["i0"] - 0.5, n + 5.5, k["L"], k["H"], k["renk"], a=k["a"], cizgi=1.4, dash="dash")
        yatay(fig, k["EQ"], k["i0"] - 0.5, n + 5.5, renk=k["renk"], dash="dot", w=1.3)
        not_(fig, k["i0"] - 0.5, k["H"], f"IPDA-{k['N']} high {k['H']:.1f}", renk=k["renk"], ok=False, boyut=10,
             xanchor="left", ay=-10)
        not_(fig, k["i0"] - 0.5, k["EQ"], f"EQ %50 = {k['EQ']:.1f}", renk=k["renk"], ok=False, boyut=9, xanchor="left", ay=-9)
        not_(fig, k["i0"] - 0.5, k["L"], f"IPDA-{k['N']} low {k['L']:.1f}", renk=k["renk"], ok=False, boyut=10,
             xanchor="left", ay=11)
        lejant(fig, f"son {k['N']} işlem günü kutusu", k["renk"], a=k["a"] + 0.18)
    # sağ kenardaki yerleşim şeridi
    xs = n + 8
    for j, k in enumerate(kutular):
        x = xs + j * 3.2
        fig.add_shape(type="rect", x0=x - 1.1, x1=x + 1.1, y0=k["L"], y1=k["H"],
                      fillcolor=rgba(k["renk"], 0.10), line=dict(color=k["renk"], width=1.0))
        fig.add_trace(go.Scatter(x=[x], y=[P], mode="markers", marker=dict(size=13, color=k["renk"],
                      symbol="diamond", line=dict(color="#ffffff", width=1.2)), showlegend=False,
                      hovertext=[f"IPDA-{k['N']} = %{k['yuzde']:.0f}"]))
        not_(fig, x, k["H"], f"IPDA<sub>{k['N']}</sub><br><b>%{k['yuzde']:.0f}</b>", renk=k["renk"], ok=False,
             boyut=10, ay=-16)
    # 20 günlük dilim sınırları
    for b in (n - 20, n - 40, n - 60):
        fig.add_vline(x=b - 0.5, line=dict(color=MUREKKEP, width=1, dash="dot"))
    not_(fig, n - 60 - 0.5, 87.0, "her ~20 işlem gününde<br>'yeni havuz doğar' (ICT iddiası —<br>kanıtsız; kutu tanımı ise triviyal Donchian)",
         renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="top")
    yatay(fig, P, 0, n + 20, renk=MUREKKEP, dash="dash", w=1.2)
    not_(fig, n - 1, P, f"bugünkü kapanış {P:.1f}", renk=MUREKKEP, ax=-70, ay=-42)
    okuma = ("kısa ve orta ufuk discount, uzun ufuk premium → karşı-trend alış: "
             "hedef küçültülür, TP1'de %70 kapatılır (1.7 karar tablosu)")
    not_(fig, 1, 111.5, f"<b>Rejim üçlüsü:</b> IPDA₂₀ = %{kutular[2]['yuzde']:.0f} · IPDA₄₀ = %{kutular[1]['yuzde']:.0f} · "
         f"IPDA₆₀ = %{kutular[0]['yuzde']:.0f}<br>{okuma}", renk=MUREKKEP, ok=False, boyut=10, xanchor="left")
    fig.update_xaxes(range=[-3, n + 16])
    fig.update_yaxes(range=[86.0, 113.5])
    duzen(fig, "Şekil 01 — IPDA 20/40/60 kutuları: aynı fiyatı üç ufukta konumlandırmak (şematik örnek)",
          "Tanım (derste sabitlenen): işlem günü, fitil uçları, EQ = (H+L)/2, IPDA_N = (P−L_N)/(H_N−L_N)×100. "
          "Ölçüt meşru (çoklu ufuklu Donchian); 'algoritma bunu hedefliyor' anlatısı kanıtsızdır",
          y_baslik="fiyat (şematik birim)", x_baslik="işlem günü sırası", h=640)
    _kaydet(fig, "01_ipda_20_40_60")


# =====================================================================================
# 30 — PD Array Matrix merdiveni (saf diyagram)
# =====================================================================================
def g30_pd_matrix():
    prem = [("Old High / eski tepe — BSL", "stop kümelenmesinin fiilî adresi; birincil DOL"),
            ("Bearish Order Block", "displacement'ı doğuran son yükseliş mumu; en dar, en test edilebilir bant"),
            ("Bearish FVG (SIBI)", "tek yönlü işlem görmüş aralık; CE (%50) reaktif nokta"),
            ("Bearish Breaker", "kırılmış destek → direnç; 'iki kez sınanmış' olduğu için OB'den zayıf"),
            ("Mitigation Block", "zarardaki pozisyonun kapatıldığı varsayılan bölge; tanım kaynaklar arası çelişkili"),
            ("Rejection Block", "uzun fitilin gövde–uç aralığı; en öznel"),
            ("Volume Imbalance", "gövdeler arası mikro boşluk; mikro-hedef, giriş için zayıf")]
    disc = [("Old Low / eski dip — SSL", ""), ("Bullish Order Block", ""), ("Bullish FVG (BISI)", ""),
            ("Bullish Breaker", ""), ("Mitigation Block", ""), ("Rejection Block", ""), ("Volume Imbalance", "")]
    fig = go.Figure()
    yuk = 0.78
    for j, (ad, aciklama) in enumerate(prem):        # j=0 en güçlü, en yukarıda
        y = 7.0 - j
        a = 0.42 - 0.045 * j
        d_kutu(fig, 0.6, 6.4, y - yuk / 2, y + yuk / 2, f"{j+1}. {ad}", BORDO, a=a, boyut=11, kalin=(j == 0))
        if aciklama:
            not_(fig, 6.7, y, aciklama, renk=GRI, ok=False, boyut=9, xanchor="left")
    for j, (ad, _) in enumerate(disc):
        y = -7.0 + j
        a = 0.42 - 0.045 * j
        d_kutu(fig, 0.6, 6.4, y - yuk / 2, y + yuk / 2, f"{j+1}. {ad}", TEAL, a=a, boyut=11, kalin=(j == 0))
    # equilibrium
    fig.add_shape(type="line", x0=-0.2, x1=12.5, y0=0, y1=0, line=dict(color=MUREKKEP, width=3))
    not_(fig, 0.6, 0, "<b>EQUILIBRIUM %50</b> — array değil, ayraç", renk=MUREKKEP, ok=False, boyut=12, xanchor="left", ay=0)
    # yön okları
    d_ok(fig, 0.15, 0.6, 0.15, 7.4, renk=BORDO, w=2.2)
    d_ok(fig, 0.15, -0.6, 0.15, -7.4, renk=TEAL, w=2.2)
    not_(fig, -0.55, 4.0, "PREMIUM<br>satış aranır<br>(alış hedefi)", renk=BORDO, ok=False, boyut=11, xanchor="center")
    not_(fig, -0.55, -4.0, "DISCOUNT<br>alış aranır<br>(satış hedefi)", renk=TEAL, ok=False, boyut=11, xanchor="center")
    # güç ölçeği
    for j in range(7):
        fig.add_shape(type="rect", x0=11.6, x1=12.3, y0=6.6 - j, y1=7.4 - j,
                      fillcolor=rgba(MUREKKEP, 0.40 - 0.05 * j), line=dict(color=GRI, width=0.5))
    not_(fig, 11.95, 7.9, "çekim<br>gücü", renk=GRI, ok=False, boyut=9)
    not_(fig, 12.4, 7.0, "güçlü", renk=GRI, ok=False, boyut=9, xanchor="left")
    not_(fig, 12.4, 1.0, "zayıf", renk=GRI, ok=False, boyut=9, xanchor="left")
    # dipnot
    d_kutu(fig, 0.6, 12.3, -9.9, -8.3,
           "Uyarı: bu sıralama <b>ölçülmüş değil, öğretilen</b> bir sıralamadır; kaynaklar arasında değişir. "
           "Ezberlenecek yasa değil,<br><b>çakışma yokken</b> kullanılacak varsayılan sıradır. Çakışma (2+ array üst üste) "
           "her zaman sıralamayı ezer — Unicorn tam olarak budur.",
           GRI, a=0.09, boyut=10)
    temiz_eksen(fig, x=[-1.4, 13.6], y=[-10.6, 8.9])
    duzen(fig, "Şekil 20 — PD Array Matrix merdiveni: hangi dizi hangi sırada (şematik diyagram)",
          "Öncelik kuralı (4.7): 1) HTF önce · 2) çakışma sayısı · 3) premium/discount testi · 4) tazelik · "
          "5) displacement kalitesi · 6) stop bütçesi · 7) ancak berabere kalırsa bu merdiven",
          y_baslik="", x_baslik="", h=760)
    _kaydet(fig, "20_pd_array_matrix_merdiveni")


# =====================================================================================
# 31 — Çakışan array'lerde öncelik: kesişim bandı vs yalnız array
# =====================================================================================
def g31_cakisan_array():
    s = Seri(31, baslangic=18398.0, birim=5.5)
    s.bacak(18372.0, 4, gurultu=0.6)
    s.bacak(18332.0, 5, gurultu=0.6)
    s.bacak(18305.0, 4, gurultu=0.5, lab="H4 FVG'ye giriş")
    s.bacak(18296.0, 3, gurultu=0.5, lab="zayıf aday: VI 18296–18302 burada dolar")
    s.bacak(18276.0, 4, gurultu=0.5)
    s.mum(18276.0, 18280.0, 18262.0, 18272.0, "kesişim bandına dokunuş (18268–18281)")
    s.bacak(18288.0, 3, gurultu=0.5)
    s.bacak(18356.0, 7, lab="TP1 18356 (seans içi EQH)")
    s.bacak(18338.0, 3, gurultu=0.5)
    s.bacak(18412.0, 7, lab="TP2 18412 (H4 FVG üst kenarı / PDH)")
    df = s.df(); n = len(df)

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_g = idx("kesişim"); i_t1 = idx("TP1"); i_t2 = idx("TP2"); i_vi = idx("zayıf")
    fig = go.Figure(mum_izi(df, ad="15 dk mum"))
    kutu(fig, 0, n - 1, 18240, 18310, TEAL, a=0.07, cizgi=1.0, dash="dot")
    kutu(fig, 6, n - 1, 18262, 18288, TEAL, a=0.14, cizgi=1.0)
    kutu(fig, 8, n - 1, 18268, 18281, TEAL, a=0.22, cizgi=1.2)
    kutu(fig, 10, n - 1, 18268, 18281, ALTIN, a=0.30, cizgi=1.8)
    not_(fig, 0.4, 18310, "H4 bullish FVG 18240–18310 (HTF array — LTF adayları yalnız bunun içinde geçerli)",
         renk=TEAL, ok=False, boyut=10, xanchor="left", ay=-10)
    not_(fig, 6.2, 18288, "15m bullish OB 18262–18288 (MT 18275)", renk=TEAL, ok=False, boyut=9, xanchor="left", ay=-9)
    not_(fig, 8.2, 18268, "15m bullish breaker 18268–18281", renk=TEAL, ok=False, boyut=9, xanchor="left", ay=10)
    not_(fig, i_g, 18274.5, "<b>TRIPLE CONFLUENCE 18268–18281</b><br>emir kesişimin ORTASINA: limit 18274",
         renk=ALTIN, ax=100, ay=-72)
    # zayıf aday
    kutu(fig, 3, i_vi + 6, 18296, 18302, GRI, a=0.14, cizgi=1.0, dash="dot")
    not_(fig, 0.4, 18232, "tek array (volume imbalance 18296–18302): HTF array içinde ama en zayıf sırada<br>"
         "→ 'daha yakın, daha çabuk dolar' tuzağı — dolum kolaylığı ile geçerlilik ters orantılıdır",
         renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="bottom")
    giris, sl = 18274.0, 18256.0
    R = giris - sl
    for y, ad, renk, dash in ((giris, f"giriş (limit) {giris:.0f}", MUREKKEP, "dash"),
                              (sl, f"SL {sl:.0f} = kesişimin altı 18262 − 6 puan tampon → 1R = {R:.0f} puan", BORDO, "solid"),
                              (18356.0, f"TP1 18356 → +{(18356-giris)/R:.1f}R", TEAL, "dot"),
                              (18412.0, f"TP2 18412 → +{(18412-giris)/R:.1f}R", TEAL, "dot"),
                              (18505.0, f"TP3 18505 (IPDA-20 üst kenarı) → +{(18505-giris)/R:.1f}R", TEAL, "dot")):
        yatay(fig, y, i_g - 2, n - 1, renk=renk, dash=dash, w=1.6 if dash == "solid" else 1.2)
        not_(fig, n - 1, y, ad, renk=renk, ok=False, boyut=9, xanchor="right", ay=-10)
    kutu(fig, i_g, n - 1, sl, giris, BORDO, a=0.16, cizgi=0)
    # stop bütçesi karşılaştırma çubukları
    for x, y0, y1, renk, ad in ((n + 2, giris, sl, TEAL, "kesişim<br>18 puan"),
                                (n + 5, 18300.0, 18285.0, GRI, "VI adayı<br>15 puan ama<br>önünde OB var")):
        fig.add_shape(type="rect", x0=x - 0.9, x1=x + 0.9, y0=min(y0, y1), y1=max(y0, y1),
                      fillcolor=rgba(renk, 0.30), line=dict(color=renk, width=1.0))
        not_(fig, x, max(y0, y1), ad, renk=renk, ok=False, boyut=9, ay=-18)
    not_(fig, n + 3.5, 18244, "stop bütçesi<br>(karar kuralı 6)", renk=GRI, ok=False, boyut=9)
    lejant(fig, "HTF array (H4 FVG)", TEAL, a=0.10); lejant(fig, "LTF array (OB / breaker)", TEAL, a=0.22)
    lejant(fig, "kesişim bandı — emir buraya", ALTIN, a=0.35); lejant(fig, "tek array, atlanır", GRI, a=0.2)
    fig.update_yaxes(range=[18222, 18545], tickformat=".0f")
    fig.update_xaxes(range=[-1, n + 7])
    duzen(fig, "Şekil 21 — Çakışan PD array'lerde öncelik: kesişim bandı emri, tek array atlanır (şematik örnek)",
          "NQ benzeri puanlama. Sıra: HTF array içi mi → kaç array çakışıyor → doğru tarafta mı → taze mi → "
          "displacement yapı kırdı mı → stop bütçesi. Emir kutunun kenarına değil, kesişimin ortasına",
          y_baslik="fiyat (puan)", x_baslik="mum sırası (15 dk)", h=640)
    _kaydet(fig, "21_cakisan_array_oncelik")


# =====================================================================================
# 32 — SD projeksiyonu: manipülasyon bacağından −1 / −2 / −2.5 / −4
# =====================================================================================
def g32_sd_projeksiyon():
    s = Seri(32, baslangic=100.35, birim=0.055)
    s.bacak(100.10, 4, gurultu=0.6)
    s.mum(100.10, 100.13, 99.80, 99.96, "SWEEP: SSL 99.86 fitille alındı (bacak başı = 0)")
    s.mum(99.96, 100.05, 99.94, 100.03, "d1")
    s.mum(100.03, 100.62, 100.02, 100.58, "d2 displacement (FVG 100.05–100.42)")
    s.mum(100.58, 100.90, 100.52, 100.82, "d3 — bacak sonu 100.90 = 1")
    s.bacak(100.55, 3, gurultu=0.4)
    s.mum(100.55, 100.58, 100.18, 100.30, "FVG CE 100.22'ye dönüş → limit doldu")
    s.bacak(100.75, 3); s.bacak(101.20, 4)
    s.bacak(102.05, 5, lab="TP1 = −1.0")
    s.bacak(101.80, 3, gurultu=0.5)
    s.bacak(103.15, 6, lab="TP2 = −2.0")
    s.mum(103.15, 103.68, 103.05, 103.20, "−2.5'te reddedildi (tipik dönüş bölgesi)")
    s.bacak(102.60, 4)
    df = s.df(); n = len(df)

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_sw = idx("SWEEP"); i_top = idx("d3"); i_g = idx("FVG CE"); i_r = idx("−2.5")
    P0, P1 = df.l[i_sw], df.h[i_top]          # bacak başı (0) ve sonu (1)
    L = P1 - P0
    fig = go.Figure(mum_izi(df, ad="15 dk mum"))
    fig.add_shape(type="line", x0=i_sw, x1=i_top, y0=P0, y1=P1,
                  line=dict(color=TURUNCU, width=3.5))
    not_(fig, i_sw, P0, f"0 — bacak başı (sweep dibi) {P0:.2f}", renk=TURUNCU, ok=False, boyut=10, xanchor="left", ay=14)
    not_(fig, i_top, P1, f"1 — bacak sonu (displacement tepesi) {P1:.2f}", renk=TURUNCU, ok=False, boyut=10,
         xanchor="left", ay=-12)
    giris, sl = 100.22, 99.74
    R = giris - sl
    hedefler = []
    for k, renk, w in ((1.0, TEAL, 2.0), (2.0, TEAL, 1.8), (2.5, TEAL, 1.6), (4.0, GRI, 1.4)):
        y = P1 + k * L
        hedefler.append((k, y))
        yatay(fig, y, i_sw, n - 1, renk=renk, dash="dash" if k < 4 else "dot", w=w)
        ek = f" → +{(y-giris)/R:.1f}R" if k < 4 else "  ⟵ max expansion: YENİ İŞLEM YOK, yapı yeniden okunur"
        not_(fig, n - 1, y, f"−{k:g} = {y:.2f}{ek}", renk=renk, ok=False, boyut=10, xanchor="right", ay=-10)
    kutu(fig, i_top - 3, i_g + 3, 100.05, 100.42, MOR, a=0.20)
    y62, y79 = P1 - 0.62 * L, P1 - 0.79 * L
    kutu(fig, i_top, i_g + 3, y79, y62, ALTIN, a=0.16, cizgi=0)
    not_(fig, i_g, giris, f"giriş = FVG CE {giris:.2f} (OTE bandı içinde)", renk=MUREKKEP, ax=-90, ay=48)
    yatay(fig, giris, i_g, n - 1, renk=MUREKKEP, dash="dash")
    yatay(fig, sl, i_g, n - 1, renk=BORDO, w=1.8)
    not_(fig, i_g, sl, f"SL {sl:.2f} = sweep fitili {P0:.2f} − 0.06 tampon → 1R = {R:.2f}", renk=BORDO,
         ok=False, boyut=10, xanchor="left", ay=12)
    kutu(fig, i_g, n - 1, sl, giris, BORDO, a=0.14, cizgi=0)
    not_(fig, i_r, df.h[i_r], "fiyat −2.0'yi geçti, −2.5'te reddedildi", renk=TEAL, ax=-60, ay=-40)
    not_(fig, 1, 104.6, f"<b>Formül:</b> Hedef₋ₖ = P<sub>bacak sonu</sub> + k·(P<sub>bacak sonu</sub> − P<sub>bacak başı</sub>)"
         f"  ·  bacak boyu = {L:.2f}<br>Uyarı: buradaki 'standart sapma' istatistiksel σ DEĞİLDİR — bir referans "
         "bacağın tam katlarıdır (yanlış adlandırma)", renk=GRI, ok=False, boyut=10, xanchor="left")
    lejant(fig, "FVG (BISI)", MOR); lejant(fig, "OTE 0.62–0.79", ALTIN, a=0.2)
    lejant_cizgi(fig, "SD projeksiyon hedefleri", TEAL); lejant_cizgi(fig, "manipülasyon bacağı", TURUNCU, "solid")
    fig.update_yaxes(range=[99.55, 105.6])
    duzen(fig, "Şekil 07 — Standart sapma projeksiyonu: sweep sonrası manipülasyon bacağından hedef üretmek (şematik örnek)",
          "Fib aracı sweep dibinden displacement tepesine; seviyeler −1 / −2 / −2.5 / −4. −2.5 sık dönüş bölgesi, "
          "−4 'max expansion' — orada yeni işlem açılmaz. Statü: öğretilen, ölçülmemiş — kendi verinizle test edilebilir",
          y_baslik="fiyat (şematik birim)", x_baslik="mum sırası (15 dk)", h=660)
    _kaydet(fig, "07_sd_projeksiyonu")


# =====================================================================================
# 33 — CBDR + Asya aralığı + SD bantları + protraction profili
# =====================================================================================
def g33_cbdr_sd():
    s = Seri(33, baslangic=1.08380, birim=0.00011)
    s.yatay(3, 1.08390, genlik=0.7)
    s.mum(s.son, 1.08512, s.son - 0.00012, 1.08500, "CBDR high 1.08500")     # 15:30
    s.bacak(1.08340, 3, gurultu=0.5)
    s.mum(s.son, s.son + 0.00012, 1.08238, 1.08250, "CBDR low 1.08250")      # 18:00
    s.bacak(1.08400, 4, gurultu=0.5, lab="CBDR sonu (20:00)")                # 12 mum: 14:00–20:00
    s.yatay(8, 1.08395, genlik=0.55, lab="Asya sonu (00:00)")                # 20:00–00:00
    s.bacak(1.08300, 4, gurultu=0.5)                                         # 00:00–02:00
    s.mum(1.08300, 1.08310, 1.07950, 1.08040, "Judas dibi (Normal Protraction — Buy)")
    s.bacak(1.08290, 3)
    s.bacak(1.08520, 4, lab="Londra genişlemesi")
    s.bacak(1.08440, 2, gurultu=0.5)
    s.bacak(1.08830, 4)
    s.mum(1.08830, 1.09000, 1.08800, 1.08930, "günün high'ı")
    s.bacak(1.08790, 3)
    df = s.df(); n = len(df)
    zaman = pd.date_range("2025-06-10 14:00", periods=n, freq="30min")

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_cb = idx("CBDR sonu"); i_as = idx("Asya sonu"); i_j = idx("Judas"); i_hi = idx("günün high")
    # ÖLÇÜM GÖVDELERLE (fitil uçları aralığı şişirir — BOS/MSS'teki gövde kuralıyla aynı gerekçe)
    govde = df[["o", "c"]]
    H = govde.max(axis=1)[:i_cb + 1].max(); L = govde.min(axis=1)[:i_cb + 1].min(); R = H - L
    fig = go.Figure(mum_izi(df, x=zaman, ad="30 dk mum"))
    for x0, x1, ad, renk, a in ((0, i_cb, "CBDR 14:00–20:00 NY", MAVI, 0.10),
                                (i_cb, i_as, "Asya aralığı 20:00–00:00", MOR, 0.10),
                                (i_as + 4, i_as + 10, "Londra KZ 02:00–05:00", ALTIN, 0.13)):
        fig.add_vrect(x0=zaman[x0], x1=zaman[min(x1, n - 1)], fillcolor=rgba(renk, a), line_width=0, layer="below",
                      annotation_text=ad, annotation_position="top left", annotation_font=dict(size=9, color=renk))
        lejant(fig, ad, renk, a=a + 0.18)
    for y in (H, L):
        yatay(fig, y, zaman[0], zaman[n - 1], renk=MAVI, w=1.8)
    not_(fig, zaman[1], H, f"CBDR high {H:.5f}", renk=MAVI, ok=False, boyut=10, xanchor="left", ay=-10)
    not_(fig, zaman[1], L, f"CBDR low {L:.5f}  ·  R = {R*10000:.0f} pip ✓ (<40 pip → projeksiyon geçerli)",
         renk=MAVI, ok=False, boyut=10, xanchor="left", ay=12)
    for k in (1, 2):
        for isaret, taban in ((+1, H), (-1, L)):
            y = taban + isaret * k * R
            yatay(fig, y, zaman[i_as], zaman[n - 1], renk=GRI, dash="dash", w=1.0)
            not_(fig, zaman[n - 1], y, f"SD{'+' if isaret > 0 else '−'}{k} = {y:.5f}", renk=GRI, ok=False,
                 boyut=9, xanchor="right", ay=-9)
    sd_j = (L - df.l[i_j]) / R
    sd_h = (df.h[i_hi] - H) / R
    daire(fig, zaman[i_j], df.l[i_j] + 0.00020, r_x=pd.Timedelta(minutes=45), r_y=0.00030)
    not_(fig, zaman[i_j], df.l[i_j], f"Judas: SD−{sd_j:.1f} — 'Normal Protraction — Buy'<br>"
         "(gece aralığının bias'a ters ucu süpürüldü)", renk=ALTIN, ax=105, ay=50)
    not_(fig, zaman[i_hi], df.h[i_hi], f"günün high'ı: SD+{sd_h:.1f}<br>"
         "(ICT iddiası: gerçek ekstrem 2–3 SD bandında)", renk=TEAL, ax=-80, ay=-38)
    tv = list(pd.date_range("2025-06-10 14:00", periods=8, freq="3h"))
    fig.update_xaxes(tickvals=tv, ticktext=[f"{t:%H:%M} NY<br>{(t + pd.Timedelta(hours=7)):%H:%M} TSİ" for t in tv],
                     tickfont=dict(size=10))
    not_(fig, zaman[1], 1.07720, "Geçersizlik: CBDR > 40 pip olsaydı projeksiyon KULLANILMAZDI; ayrıca 2R zaten ADR'yi "
         "aşıyorsa yöntem o gün atlanır.<br>Ölçüm gövdelerle yapılır (tek fitil ölçeği bozmasın) — BOS/MSS'teki "
         "'gövde kapanışı' kuralıyla aynı gerekçe", renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="bottom")
    fig.update_yaxes(tickformat=".5f", range=[1.07700, 1.09080])
    duzen(fig, "Şekil 08 — CBDR + Asya aralığı + SD bantları: gece aralığından günün menzilini projekte etmek (şematik örnek)",
          "SD_n⁺ = H + n·R, SD_n⁻ = L − n·R (R = aralık genişliği). Bu model GİRİŞ vermez, ÇERÇEVE verir: "
          "alıcıysam girişimi SD−1/−2'de arayacağım, hedefim SD+2/+3",
          y_baslik="EUR/USD (şematik)", x_baslik="saat (NY / TSİ, ABD yaz saati)", h=660)
    _kaydet(fig, "08_cbdr_asya_sd_bantlari")


# =====================================================================================
# 34 — ICT makro pencereleri ve altındaki hacim gerçeği
# =====================================================================================
def g34_makro():
    s = Seri(34, baslangic=100.02, birim=0.028)
    s.yatay(10, 100.00, genlik=0.9)                                   # 08:00–08:45
    s.bacak(99.94, 4, gurultu=0.5, lab="makro 1 (08:50–09:10)")       # 08:50–09:05
    s.bacak(99.90, 8, gurultu=0.5)                                    # 09:10–09:45
    s.mum(99.90, 99.92, 99.80, 99.88, "SSL 99.83 süpürüldü (makro 09:50 içinde)")
    s.mum(99.88, 99.96, 99.86, 99.95, "M1")
    s.mum(99.95, 100.32, 99.94, 100.28, "M2 displacement — 5m MSS (FVG 99.96–100.14)")
    s.mum(100.28, 100.45, 100.20, 100.38, "M3")
    s.bacak(100.20, 3, gurultu=0.4)
    s.mum(100.20, 100.22, 100.04, 100.12, "FVG CE 100.05'e dönüş → giriş")
    s.bacak(100.30, 3); s.bacak(100.62, 5, lab="hedef: seans high 100.62")
    s.bacak(100.48, 4, gurultu=0.5)
    s.yatay(14, 100.45, genlik=0.8, lab="öğle makrosu: kaçınılır")
    df = s.df(); n = len(df)
    zaman = pd.date_range("2025-07-16 08:00", periods=n, freq="5min")

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_sw = idx("SSL"); i_m1 = idx("M1"); i_g = idx("FVG CE"); i_t = idx("hedef")
    # sentetik dakikalık hacim: gün içi U profili + saat başı sivrilikleri
    rng = np.random.default_rng(340)
    dk = np.array([(t.hour * 60 + t.minute) for t in zaman], dtype=float)
    u = 1.0 + 1.5 * np.exp(-((dk - 570) / 55.0) ** 2) + 0.55 * np.exp(-((dk - 690) / 90.0) ** 2)
    saat_kenar = np.array([min(abs(m % 60 - 0), abs(m % 60 - 60)) for m in dk])
    spike = 0.85 * np.exp(-(saat_kenar / 9.0) ** 2)
    hacim = (u + spike) * (1 + 0.10 * rng.normal(size=n))
    hacim = np.clip(hacim, 0.25, None)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32],
                        vertical_spacing=0.115,
                        subplot_titles=("(a) 5 dakikalık fiyat — makro pencereleri",
                                        "(b) İşlem hacmi (sentetik): gün içi U profili + saat başı sivrilikleri"))
    fig.add_trace(mum_izi(df, x=zaman, ad="5 dk mum"), row=1, col=1)
    fig.add_trace(go.Bar(x=zaman, y=hacim, marker_color=rgba(GRI, 0.55), name="hacim (göreli)"), row=2, col=1)
    makrolar = [("08:50", "09:10", "NY AM 1 — 08:50–09:10", TURUNCU, 0.16, "yüksek ama gürültülü (08:30 verisinin artığı)"),
                ("09:50", "10:10", "NY AM 2 — 09:50–10:10", TURUNCU, 0.30, "EN YÜKSEK KALİTE"),
                ("10:50", "11:10", "NY AM 3 — 10:50–11:10", TURUNCU, 0.16, "orta (Londra kapanışına doğru)"),
                ("11:50", "12:10", "Öğle — 11:50–12:10", GRI, 0.16, "düşük hacim → KAÇIN")]
    for h0, h1, ad, renk, a, _ in makrolar:
        for r in (1, 2):
            fig.add_vrect(x0=pd.Timestamp(f"2025-07-16 {h0}"), x1=pd.Timestamp(f"2025-07-16 {h1}"),
                          fillcolor=rgba(renk, a), line_width=0, layer="below", row=r, col=1)
        not_(fig, pd.Timestamp(f"2025-07-16 {h0}"), 100.86, ad, renk=renk, ok=False, boyut=9,
             xanchor="left", row=1, col=1)
    for k, (x, y, metin, renk, ax_, ay_) in enumerate((
            (zaman[i_sw], df.l[i_sw], "① eşit dipler (SSL) süpürüldü", ALTIN, -85, 34),
            (zaman[i_m1 + 1], df.c[i_m1 + 1], "② displacement + FVG · ③ 5m MSS", BORDO, 95, 38),
            (zaman[i_g], 100.05, "④ FVG CE'ye geri çekilme → giriş", MUREKKEP, -95, 40),
            (zaman[i_t], df.h[i_t], "⑤ hedef: seans high", TEAL, -70, -18))):
        not_(fig, x, y, metin, renk=renk, ax=ax_, ay=ay_, row=1, col=1)
    f = [z for z in fvg_bul(df) if z["tip"] == "BISI" and z["i"] == i_m1][0]
    kutu(fig, zaman[i_m1], zaman[i_t], f["alt"], f["ust"], MOR, a=0.20, row=1, col=1)
    yatay(fig, 99.83, zaman[0], zaman[i_sw], renk=ALTIN, w=1.5, row=1, col=1)
    tv = list(pd.date_range("2025-07-16 08:00", periods=11, freq="30min"))
    fig.update_xaxes(tickvals=tv, ticktext=[f"{t:%H:%M} NY<br>{(t + pd.Timedelta(hours=7)):%H:%M} TSİ" for t in tv],
                     tickfont=dict(size=10), row=2, col=1)
    fig.update_yaxes(title_text="fiyat (şematik)", row=1, col=1)
    fig.update_yaxes(title_text="göreli hacim", row=2, col=1)
    lejant(fig, "makro penceresi (yüksek kalite)", TURUNCU, a=0.35)
    lejant(fig, "öğle makrosu — kaçınılır", GRI, a=0.3)
    lejant(fig, "FVG (BISI)", MOR)
    fig.update_yaxes(range=[99.60, 100.94], row=1, col=1)
    duzen(fig, "Şekil 24 — Makro pencereleri: mistik saat değil, hacmin yoğunlaştığı dakikalar (şematik örnek)",
          "ICT genellemesi: makro = her saatin son 10 dk + yeni saatin ilk 10 dk. Alt panel asıl mesajı taşır — "
          "displacement olasılığı hacimle birlikte yükselir (VWAP dilim sınırları, benchmark fixing, MOC toplama)",
          x_baslik="saat (NY / TSİ, ABD yaz saati)", h=720)
    fig.update_layout(bargap=0.15)
    fig.update_yaxes(title_text="fiyat (şematik)", row=1, col=1)
    fig.update_yaxes(title_text="göreli hacim", row=2, col=1)
    fig.update_xaxes(title_text="", row=1, col=1)
    _kaydet(fig, "24_makro_pencereleri_hacim")


# =====================================================================================
# 35 — Üç açılış çapası: 00:00 midnight open, 08:30, 09:30
# =====================================================================================
def g35_acilis_capalari():
    s = Seri(35, baslangic=99.98, birim=0.030)
    s.yatay(16, 100.00, genlik=0.9)                       # 20:00–00:00 Asya
    s.bacak(99.92, 8, gurultu=0.6)                        # 00:00–02:00
    s.bacak(99.60, 12, gurultu=0.6, lab="Londra: midnight open'ın altı")   # 02:00–05:00
    s.bacak(99.86, 14, gurultu=0.6)                       # 05:00–08:30
    s.mum(99.86, 99.90, 99.55, 99.72, "08:30 verisi: sert aşağı fitil")
    s.mum(99.72, 100.02, 99.70, 99.98, "08:30 açılışının ÜSTÜNE dönüş → itiş manipülasyondu")
    s.bacak(100.06, 4)                                    # 09:00–09:30
    s.bacak(100.45, 24, gurultu=0.5, lab="gün kapanışı")  # 09:30–16:00
    df = s.df(); n = len(df)
    zaman = pd.date_range("2025-07-15 20:00", periods=n, freq="15min")

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_mo = 16                                             # 00:00 NY
    i_830 = idx("08:30 verisi")
    i_930 = i_830 + 6
    mo, o830, o930 = df.o[i_mo], df.o[i_830], df.o[i_930]
    ADR = 0.90
    fig = go.Figure(mum_izi(df, x=zaman, ad="15 dk mum"))
    for y, ad, renk, dash, w in ((mo, f"00:00 midnight open {mo:.2f}", MUREKKEP, "solid", 2.4),
                                 (o830, f"08:30 open {o830:.2f}", MAVI, "dash", 1.6),
                                 (o930, f"09:30 open {o930:.2f}", GRI, "dot", 1.6)):
        yatay(fig, y, zaman[0], zaman[n - 1], renk=renk, dash=dash, w=w)
        not_(fig, zaman[1], y, ad, renk=renk, ok=False, boyut=10, xanchor="left", ay=-10)
    for i, ad in ((i_mo, "00:00 (07:00 TSİ)"), (i_830, "08:30 (15:30 TSİ)"), (i_930, "09:30 (16:30 TSİ)")):
        fig.add_vline(x=zaman[i], line=dict(color=MUREKKEP, width=1, dash="dot"))
        not_(fig, zaman[i], 100.62, ad, renk=MUREKKEP, ok=False, boyut=9, ay=0)
    i_lo = int(df.l[:i_830].idxmin())
    fig.add_shape(type="rect", x0=zaman[i_mo], x1=zaman[i_830], y0=df.l[:i_830 + 1].min(), y1=mo,
                  fillcolor=rgba(BORDO, 0.08), line_width=0, layer="below")
    not_(fig, zaman[i_lo], df.l[i_lo], f"gece midnight open'ın ALTINDA: Δ = {(df.l[i_lo]-mo)/ADR*100:.0f}% ADR<br>"
         "→ 'bias bearish mi, yoksa bu Judas mı?'", renk=BORDO, ax=95, ay=45)
    not_(fig, zaman[i_830 + 1], df.c[i_830 + 1], "veri itişi 2 mumda geri alındı → <b>manipülasyon</b><br>"
         "(kalıcı olsaydı gerçek yön olurdu)", renk=TEAL, ax=90, ay=-48)
    not_(fig, zaman[n - 1], df.c[n - 1], f"kapanış: midnight open'ın üstü<br>Δ<sub>mo</sub> = +{(df.c[n-1]-mo)/ADR*100:.0f}% ADR",
         renk=TEAL, ax=-70, ay=-40)
    # sağ kenar göstergeleri
    for j, (ad, o, renk) in enumerate((("00:00", mo, MUREKKEP), ("08:30", o830, MAVI), ("09:30", o930, GRI))):
        x = zaman[n - 1] + pd.Timedelta(minutes=45 + j * 45)
        d = (df.c[n - 1] - o) / ADR * 100
        fig.add_shape(type="rect", x0=x - pd.Timedelta(minutes=16), x1=x + pd.Timedelta(minutes=16),
                      y0=100.30, y1=100.30 + d * 0.006, fillcolor=rgba(renk, 0.35), line=dict(color=renk, width=1))
        not_(fig, x, 100.30 + d * 0.006, f"{ad}<br><b>{d:+.0f}%</b>", renk=renk, ok=False, boyut=9, ay=-16)
    not_(fig, zaman[n - 1] + pd.Timedelta(minutes=90), 100.24, "kapanışın her çapaya<br>uzaklığı (ADR %)",
         renk=GRI, ok=False, boyut=9, yanchor="top")
    tv = list(pd.date_range("2025-07-15 20:00", periods=11, freq="2h"))
    fig.update_xaxes(tickvals=tv, ticktext=[f"{t:%H:%M} NY<br>{(t + pd.Timedelta(hours=7)):%H:%M} TSİ" for t in tv],
                     tickfont=dict(size=10), range=[zaman[0], zaman[n - 1] + pd.Timedelta(minutes=200)])
    lejant_cizgi(fig, "00:00 midnight open (günlük bias çapası)", MUREKKEP, "solid")
    lejant_cizgi(fig, "08:30 open (veri çapası)", MAVI); lejant_cizgi(fig, "09:30 open (RTH seans çapası)", GRI, "dot")
    fig.update_yaxes(range=[99.45, 100.72])
    duzen(fig, "Şekil 25 — Üç açılış çapası tek gün üstünde: 00:00 / 08:30 / 09:30 (şematik örnek)",
          "Δ_mo = (P − O₀₀:₀₀)/ADR × 100 — hem bias hem 'günlük menzilin ne kadarı harcandı' bilgisini birlikte verir. "
          "00:00'ın gerekçesi mistik değil: Asya'nın ortası, yani günün en tarafsız fiyatı",
          x_baslik="saat (NY / TSİ, ABD yaz saati)", h=660)
    _kaydet(fig, "25_uc_acilis_capasi")


# =====================================================================================
# 36 — NWOG: anatomi (üst panel) ve NWOG yığını (alt panel)
# =====================================================================================
def g36_nwog():
    # --- üst panel: Cuma 14:00 → Pazartesi 12:00, 1 saatlik
    s = Seri(36, baslangic=99.86, birim=0.045)
    s.bacak(100.00, 3, gurultu=0.5, lab="Cuma 16:59 kapanış")
    s.mum(100.42, 100.52, 100.40, 100.48, "Pazar 18:00 açılış")     # boşluk
    s.bacak(100.60, 3, gurultu=0.5)
    s.bacak(100.46, 4, gurultu=0.5)
    s.mum(100.46, 100.48, 100.19, 100.28, "CE 100.21'e iniş → tepki (giriş)")
    s.bacak(100.55, 3); s.bacak(100.82, 4); s.bacak(101.08, 4, lab="TP: önceki hafta high 101.05")
    a = s.df(); na = len(a)
    i_fri = int(a.index[a.lab.str.startswith("Cuma")][0])
    i_sun = int(a.index[a.lab.str.startswith("Pazar")][0])
    i_ce = int(a.index[a.lab.str.startswith("CE")][0])
    i_tp = int(a.index[a.lab.str.startswith("TP")][0])
    g_alt, g_ust = a.c[i_fri], a.o[i_sun]
    ce = (g_alt + g_ust) / 2

    # --- sağ: günlük seri + son 5 NWOG şeridi
    s2 = Seri(361, baslangic=98.4, birim=0.30)
    s2.bacak(99.3, 6); s2.bacak(98.7, 5); s2.bacak(100.4, 7); s2.bacak(99.6, 5)
    s2.bacak(101.2, 6); s2.bacak(100.3, 5); s2.bacak(101.9, 6)
    b = s2.df(); nb = len(b)
    nwoglar = [(4, 98.72, 98.92), (9, 99.15, 99.34), (14, 99.98, 100.16), (19, 99.70, 99.88), (24, 100.55, 100.78)]

    # Paneller ALT ALTA: makale sütununda her panel tam genişlik alır.
    # İki panel farklı seri/zaman kurgusu → shared_xaxes YOK, her panel kendi x ekseniyle.
    fig = make_subplots(rows=2, cols=1, row_heights=[0.5, 0.5], vertical_spacing=0.10,
                        subplot_titles=("(a) NWOG anatomisi: Cuma 16:59 kapanış → Pazar 18:00 açılış",
                                        "(b) NWOG yığını: son 5 hafta sonu boşluğu ve CE'leri"))
    fig.add_trace(mum_izi(a, ad="1 saatlik mum"), row=1, col=1)
    fig.add_trace(mum_izi(b, ad="günlük mum", gorunur=False), row=2, col=1)
    # (a)
    fig.add_vrect(x0=i_fri + 0.5, x1=i_sun - 0.5, fillcolor=rgba(GRI, 0.16), line_width=0, layer="below", row=1, col=1)
    not_(fig, (i_fri + i_sun) / 2, 101.15, "hafta sonu:<br>işlem YOK", renk=GRI, ok=False, boyut=9, row=1, col=1)
    kutu(fig, i_fri, na - 1, g_alt, g_ust, GRI, a=0.22, cizgi=1.2, row=1, col=1)
    yatay(fig, ce, i_fri, na - 1, renk=MUREKKEP, dash="dash", w=2.0, row=1, col=1)
    not_(fig, i_fri, g_ust, f"NWOG üst = Pazar açılışı {g_ust:.2f}", renk=GRI, ok=False, boyut=9, xanchor="left", ay=-9, row=1, col=1)
    not_(fig, i_fri, g_alt, f"NWOG alt = Cuma kapanışı {g_alt:.2f}", renk=GRI, ok=False, boyut=9, xanchor="left", ay=11, row=1, col=1)
    not_(fig, i_ce + 1, ce, f"<b>CE %50 = {ce:.2f}</b>", renk=MUREKKEP, ok=False, boyut=10, xanchor="left", ay=-10, row=1, col=1)
    daire(fig, i_ce, a.l[i_ce] + 0.05, r_x=0.7, r_y=0.10, row=1, col=1)
    giris, sl, tp = ce, g_alt - 0.08, 101.05
    R = giris - sl
    yatay(fig, sl, i_ce, na - 1, renk=BORDO, w=1.6, row=1, col=1)
    yatay(fig, tp, i_ce, na - 1, renk=TEAL, dash="dot", row=1, col=1)
    kutu(fig, i_ce, na - 1, sl, giris, BORDO, a=0.14, cizgi=0, row=1, col=1)
    kutu(fig, i_ce, na - 1, giris, tp, TEAL, a=0.12, cizgi=0, row=1, col=1)
    not_(fig, i_ce, a.l[i_ce], f"giriş = CE {giris:.2f}<br>(teyitli: 1m/5m CISD sonrası)", renk=MUREKKEP, ax=-70, ay=48, row=1, col=1)
    not_(fig, i_ce, sl, f"SL {sl:.2f} = boşluğun karşı ucu + tampon (1R = {R:.2f})", renk=BORDO, ok=False,
         boyut=9, xanchor="left", ay=11, row=1, col=1)
    not_(fig, i_tp, tp, f"TP = önceki hafta high {tp:.2f} → +{(tp-giris)/R:.1f}R", renk=TEAL, ok=False, boyut=9,
         xanchor="right", ay=-10, row=1, col=1)
    tikler = [0, i_fri, i_sun, i_ce, na - 1]
    fig.update_xaxes(tickvals=tikler, ticktext=["Cuma 14:00", "Cuma 16:59", "Pazar 18:00", "Pzt 03:00", "Pzt 12:00"],
                     tickfont=dict(size=9), row=1, col=1)
    fig.update_yaxes(range=[99.70, 101.30], row=1, col=1)
    # (b)
    for j, (i0, lo, hi) in enumerate(nwoglar):
        a_ = 0.10 + 0.045 * j
        kutu(fig, i0, nb - 1, lo, hi, GRI, a=a_, cizgi=0.8, row=2, col=1)
        yatay(fig, (lo + hi) / 2, i0, nb - 1, renk=MUREKKEP, dash="dot", w=1.0, row=2, col=1)
    for i0, lo, hi in nwoglar[-3:]:
        pass
    for i, y in ((17, 100.07), (23, 99.79), (33, 100.66)):
        daire(fig, i, y, r_x=0.9, r_y=0.20, row=2, col=1)
    not_(fig, 17, 100.07, "CE'ye dönüş → tepki", renk=ALTIN, ax=-55, ay=-40, row=2, col=1)
    not_(fig, 23, 99.79, "içinden geçti (tepkisiz)", renk=ALTIN, ax=60, ay=42, row=2, col=1)
    not_(fig, 33, 100.66, "kenarda konsolidasyon", renk=ALTIN, ax=-70, ay=-38, row=2, col=1)
    not_(fig, nb - 1, 100.78, "en yakın ALINMAMIŞ CE<br>= birincil DOL", renk=MUREKKEP, ok=False, boyut=9,
         xanchor="right", ay=-24, row=2, col=1)
    not_(fig, 1, 97.42, "Her boşluk çalışmaz. Doldurma oranı için ICT<br>kaynaklarında sayı YOKTUR; edgeful "
         "ölçümünde<br>bullish FVG'lerin %60,7'si aynı seansta gövdeyle<br>dolmuyor — açılış boşlukları FVG'nin özel "
         "hâlidir.", renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="bottom", row=2, col=1)
    fig.update_yaxes(range=[97.3, 102.5], row=2, col=1)
    lejant(fig, "NWOG bandı (işlem görmemiş fiyat)", GRI, a=0.3)
    lejant_cizgi(fig, "CE %50 — en tepkili nokta", MUREKKEP, "dash")
    duzen(fig, "Şekil 22 — New Week Opening Gap (NWOG): anatomi ve yığın (şematik örnek)",
          "NWOG = Cuma 16:59 NY kapanışı ile Pazar 18:00 NY açılışı arası. En az 4, uygulamada 8–10 eski boşluk saklanır. "
          "SMC'nin en az öznel aracı: saat ve fiyat sabit, iki trader aynı kutuyu çizer",
          y_baslik="fiyat (şematik birim)", x_baslik="", h=860)
    fig.update_xaxes(title_text="gün", row=2, col=1)
    _kaydet(fig, "22_nwog_anatomi_yigin")


# =====================================================================================
# 37 — NDOG (17:00–18:00) ve üç günlük yığın: üç farklı davranış
# =====================================================================================
def g37_ndog():
    s = Seri(37, baslangic=100.12, birim=0.040)
    # gün 1: 18:00 → 17:00
    s.bacak(100.30, 6, gurultu=0.6); s.bacak(99.95, 7, gurultu=0.6); s.bacak(100.24, 6, gurultu=0.6)
    s.bacak(100.00, 4, gurultu=0.5, lab="G1 17:00 kapanış")
    # NDOG-1 (100.00 → 100.20)
    s.mum(100.20, 100.28, 100.18, 100.25, "G2 18:00 açılış")
    s.bacak(100.05, 5, gurultu=0.5)
    s.mum(100.05, 100.07, 100.06, 100.12, "NDOG-1 CE 100.10: tepki → dönüş")
    s.bacak(100.48, 7); s.bacak(100.30, 5, gurultu=0.5)
    s.bacak(100.62, 5, gurultu=0.5, lab="G2 17:00 kapanış")
    # NDOG-2 (100.62 → 100.44) — aşağı boşluk
    s.mum(100.44, 100.48, 100.40, 100.46, "G3 18:00 açılış")
    s.bacak(100.66, 6, gurultu=0.5, lab="NDOG-2'nin içinden tepkisiz geçiş")
    s.bacak(100.40, 6, gurultu=0.5)
    s.yatay(6, 100.30, genlik=0.7, lab="NDOG-3 kenarında konsolidasyon")
    s.bacak(100.18, 5, gurultu=0.5)
    df = s.df(); n = len(df)

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_k1 = idx("G1 17:00"); i_o2 = idx("G2 18:00"); i_ce1 = idx("NDOG-1 CE")
    i_k2 = idx("G2 17:00"); i_o3 = idx("G3 18:00"); i_gec = idx("NDOG-2"); i_kons = idx("NDOG-3")
    fig = go.Figure(mum_izi(df, ad="1 saatlik mum"))
    ndoglar = [(i_k1, df.c[i_k1], df.o[i_o2], "NDOG-1"), (i_k2, df.o[i_o3], df.c[i_k2], "NDOG-2"),
               (i_kons - 4, 100.24, 100.36, "NDOG-3 (önceki günden kalan)")]
    for i0, lo, hi, ad in ndoglar:
        lo, hi = min(lo, hi), max(lo, hi)
        kutu(fig, i0, n - 1, lo, hi, GRI, a=0.22, cizgi=1.0)
        yatay(fig, (lo + hi) / 2, i0, n - 1, renk=MUREKKEP, dash="dash", w=1.4)
        not_(fig, i0, hi, f"{ad}  (CE {((lo+hi)/2):.2f})", renk=GRI, ok=False, boyut=9, xanchor="left", ay=-9)
    for i0 in (i_k1, i_k2):
        fig.add_vrect(x0=i0 + 0.5, x1=i0 + 0.5 + 0.98, fillcolor=rgba(MUREKKEP, 0.13), line_width=0, layer="below")
    not_(fig, i_k1 + 1, 100.80, "17:00–18:00 NY:<br>vadeli piyasa KAPALI<br>(tanım gereği bir FVG)",
         renk=MUREKKEP, ok=False, boyut=9)
    daire(fig, i_ce1, df.l[i_ce1] + 0.02, r_x=1.0, r_y=0.045)
    not_(fig, i_ce1, df.l[i_ce1], "① CE'ye dönüş → tepki, dönüş", renk=ALTIN, ax=-30, ay=52)
    not_(fig, i_gec, df.c[i_gec], "② içinden tepkisiz geçiş", renk=ALTIN, ax=70, ay=-42)
    not_(fig, i_kons, df.c[i_kons], "③ kenarında konsolidasyon", renk=ALTIN, ax=-40, ay=-46)
    tik = [0, i_k1, i_o2, i_k2, i_o3, n - 1]
    fig.update_xaxes(tickvals=tik, ticktext=["G1 18:00", "G1 17:00", "G2 18:00", "G2 17:00", "G3 18:00", "G3 17:00"],
                     tickfont=dict(size=9))
    not_(fig, 1, 99.78, "Aynı grafikte üç farklı davranış: <b>her boşluk çalışmaz.</b> Boşluk doldurulduktan sonra da "
         "günlerce referans olmaya devam edebilir; silinmez.<br>NDOG için en az 5 (bir hafta), bazı uygulayıcılar 10 tutar. "
         "NDOG midnight open ile AYNI ŞEY DEĞİLDİR — sık karıştırılır.", renk=GRI, ok=False, boyut=9, xanchor="left")
    lejant(fig, "NDOG bandı", GRI, a=0.3); lejant_cizgi(fig, "CE %50", MUREKKEP, "dash")
    lejant(fig, "17:00–18:00 kapalı saat", MUREKKEP, a=0.2)
    fig.update_yaxes(range=[99.70, 100.92])
    duzen(fig, "Şekil 23 — NDOG (New Day Opening Gap): 17:00 kapanış → 18:00 açılış ve üç günlük yığın (şematik örnek)",
          "Fib 0 / 0.5 / 1 boşluğun dibinden tepesine; 0.5 = consequent encroachment (CE). "
          "Bullish bias + fiyat üstünde kapandı → destek; bearish + altında → direnç; uzaktaysa → DOL (mıknatıs)",
          y_baslik="fiyat (şematik birim)", x_baslik="saat (NY)", h=640)
    _kaydet(fig, "23_ndog_gunluk_yigin")


# =====================================================================================
# 38 — SMT divergence (şematik): iki korele enstrüman, biri süpürüyor diğeri süpürmüyor
# =====================================================================================
def g38_smt_sematik():
    def kur(seed, bas, birim, d1, tepe, d2, disp, geri, son):
        s = Seri(seed, baslangic=bas, birim=birim)
        s.bacak(bas - (bas - d1) * 0.35, 5, gurultu=0.7)
        s.mum(s.son, s.son + birim, d1, d1 + 2 * birim, "dip 1")
        s.bacak(tepe, 6, gurultu=0.6)
        s.bacak(d2 + 4 * birim, 4, gurultu=0.6)
        s.mum(s.son, s.son + birim, d2, d2 + 3 * birim, "dip 2")
        s.bacak(disp, 3, lab="displacement + MSS")
        s.bacak(geri, 3, gurultu=0.5, lab="geri çekilme (giriş)")
        s.bacak(son, 8, lab="hedef")
        return s.df()

    E = kur(38, 1.08400, 0.00030, 1.08120, 1.08380, 1.08060, 1.08520, 1.08280, 1.08900)
    G = kur(381, 1.27000, 0.00035, 1.26640, 1.26960, 1.26710, 1.27180, 1.26900, 1.27600)
    n = min(len(E), len(G))
    E, G = E.iloc[:n].reset_index(drop=True), G.iloc[:n].reset_index(drop=True)

    def idx(df, p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_d1, i_d2 = idx(E, "dip 1"), idx(E, "dip 2")
    i_ms, i_gi, i_hd = idx(G, "displacement"), idx(G, "geri"), idx(G, "hedef")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09,
                        subplot_titles=("EUR/USD — yeni dip YAPIYOR (LL): eski dip süpürüldü",
                                        "GBP/USD — yeni dip YAPMIYOR (HL): dip korundu → göreli güç burada"))
    fig.add_trace(mum_izi(E, ad="EURUSD (15 dk, şematik)"), row=1, col=1)
    fig.add_trace(mum_izi(G, ad="GBPUSD (15 dk, şematik)", gorunur=True), row=2, col=1)
    for r, df, renk in ((1, E, BORDO), (2, G, TEAL)):
        yatay(fig, df.l[i_d1], 0, n - 1, renk=ALTIN, w=1.6, row=r, col=1)
        not_(fig, 0.5, df.l[i_d1], f"dip 1 = {df.l[i_d1]:.4f}", renk=ALTIN, ok=False, boyut=9, xanchor="left",
             ay=12, row=r, col=1)
        daire(fig, i_d2, df.l[i_d2] + (df.h.max() - df.l.min()) * 0.03,
              r_x=0.8, r_y=(df.h.max() - df.l.min()) * 0.05, renk=renk, row=r, col=1)
    not_(fig, i_d2, E.l[i_d2], f"<b>LL</b> {E.l[i_d2]:.4f} < {E.l[i_d1]:.4f}<br>(sweep: likidite burada alındı)",
         renk=BORDO, ax=-60, ay=52, row=1, col=1)
    not_(fig, i_d2, G.l[i_d2], f"<b>HL</b> {G.l[i_d2]:.4f} > {G.l[i_d1]:.4f}<br>(dip korundu)",
         renk=TEAL, ax=-60, ay=52, row=2, col=1)
    for r in (1, 2):
        fig.add_vline(x=i_d2, line=dict(color=MUREKKEP, width=1.2, dash="dash"), row=r, col=1)
    not_(fig, i_d2, E.h.max(), "<b>BULLISH SMT</b><br>aynı an, aynı TF, eşleşen swing", renk=MUREKKEP,
         ok=False, boyut=12, ay=-12, row=1, col=1)
    # GBPUSD tarafında giriş
    r_ = G.h[i_ms] - G.l[i_d2]
    giris, sl = G.c[i_gi], G.l[i_d2] - 0.00025
    R = giris - sl
    tp1, tp2 = G.h[i_ms], G.h[i_ms] + 0.62 * r_
    kutu(fig, i_gi - 1, n - 1, sl, giris, BORDO, a=0.14, cizgi=0, row=2, col=1)
    kutu(fig, i_gi - 1, n - 1, giris, tp2, TEAL, a=0.12, cizgi=0, row=2, col=1)
    yatay(fig, giris, i_gi - 1, n - 1, renk=MUREKKEP, dash="dash", row=2, col=1)
    yatay(fig, sl, i_gi - 1, n - 1, renk=BORDO, w=1.6, row=2, col=1)
    for y, ad in ((tp1, f"TP1 {tp1:.4f} → +{(tp1-giris)/R:.1f}R"), (tp2, f"TP2 {tp2:.4f} → +{(tp2-giris)/R:.1f}R")):
        yatay(fig, y, i_gi - 1, n - 1, renk=TEAL, dash="dot", row=2, col=1)
        not_(fig, n - 1, y, ad, renk=TEAL, ok=False, boyut=9, xanchor="right", ay=-9, row=2, col=1)
    not_(fig, i_gi, giris, f"giriş: <b>zayıf değil GÜÇLÜ tarafta</b> (dip yapmayan enstrüman) — {giris:.4f}",
         renk=MUREKKEP, ax=-40, ay=-46, row=2, col=1)
    not_(fig, i_gi, sl, f"SL {sl:.4f} (dip 2 altı + tampon) → 1R = {R*10000:.0f} pip", renk=BORDO, ok=False,
         boyut=9, xanchor="left", ay=12, row=2, col=1)
    not_(fig, i_ms, G.c[i_ms], "MSS: SMT tek başına giriş DEĞİL — sweep teyididir.<br>"
         "Doğru dizi: havuz süpürüldü → SMT görüldü → MSS geldi → FVG/OTE'ye giriş", renk=TEAL, ax=110, ay=-40, row=2, col=1)
    fig.update_yaxes(title_text="EUR/USD", tickformat=".4f", row=1, col=1)
    fig.update_yaxes(title_text="GBP/USD", tickformat=".4f", row=2, col=1)
    duzen(fig, "Şekil 13 — SMT divergence: iki korele enstrüman, iki farklı dip (şematik örnek)",
          "Ön koşul: korelasyon SIKI olmalı (öneri: 60 günlük getiri |ρ| > 0,80) ve karşılaştırılan swing'ler AYNI olmalı. "
          "Gevşek korelasyon sürekli sahte divergence üretir", x_baslik="mum sırası (15 dk)", h=760)
    fig.update_yaxes(title_text="EUR/USD", row=1, col=1)
    fig.update_yaxes(title_text="GBP/USD", row=2, col=1)
    fig.update_xaxes(title_text="", row=1, col=1)
    _kaydet(fig, "13_smt_divergence_sematik")


# =====================================================================================
# 39 — GERÇEK VERİ: EURUSD ↔ GBPUSD SMT örneği + iki yıllık ölçüm
# =====================================================================================
def g39_gercek_smt():
    eu, k1 = veri_yukle("EURUSD=X", "1h", "730d")
    gb, k2 = veri_yukle("GBPUSD=X", "1h", "730d")
    if eu is None or gb is None:
        RAPOR.append("Şekil 39 atlandı: EURUSD/GBPUSD 1h verisi yok")
        return
    m = pd.merge(eu, gb, on="ts", suffixes=("_e", "_g")).reset_index(drop=True)
    E = m.rename(columns={"o_e": "o", "h_e": "h", "l_e": "l", "c_e": "c"})[["o", "h", "l", "c"]].copy()
    G = m.rename(columns={"o_g": "o", "h_g": "h", "l_g": "l", "c_g": "c"})[["o", "h", "l", "c"]].copy()
    E["lab"] = ""; G["lab"] = ""
    sle = swingler(E, 5)[1]; slg = swingler(G, 5)[1]

    def yakin(lst, i, tol=4):
        c = sorted([j for j in lst if abs(j - i) <= tol], key=lambda j: abs(j - i))
        return c[0] if c else None

    H = 24
    smt, teyit, net = [], [], []
    for a, b in zip(sle[:-1], sle[1:]):
        if not (E.l[b] < E.l[a] and (b - a) <= 72):
            continue
        ga, gb_ = yakin(slg, a), yakin(slg, b)
        if ga is None or gb_ is None or b + H >= len(m):
            continue
        mfe = (E.h[b:b + H].max() - E.l[b]) * 1e4
        mfeg = (G.h[gb_:gb_ + H].max() - G.l[gb_]) * 1e4
        if G.l[gb_] > G.l[ga]:
            smt.append((b, mfe, mfeg))
            if (E.l[a] - E.l[b]) * 1e4 >= 5 and (G.l[gb_] - G.l[ga]) * 1e4 >= 5:
                net.append((b, mfe, mfeg))
        else:
            teyit.append((b, mfe, mfeg))
    # korelasyon
    gunluk = m.set_index("ts")[["c_e", "c_g"]].resample("1D").last().dropna().pct_change().dropna()
    rho60 = float(gunluk.tail(60).corr().iloc[0, 1]); rho250 = float(gunluk.tail(250).corr().iloc[0, 1])
    # temsilî örnek
    b0 = 8945 if 8945 < len(m) and abs(float(m.ts[8945].value) - float(pd.Timestamp("2025-04-15 16:00").value)) < 1 else None
    if b0 is None:
        hedef = pd.Timestamp("2025-04-15 16:00")
        b0 = int((m.ts - hedef).abs().idxmin())
    a0 = [x for x in sle if x < b0][-1]
    ga0, gb0 = yakin(slg, a0), yakin(slg, b0)
    i0, i1 = max(0, b0 - 45), min(len(m) - 1, b0 + 60)
    dE = m.iloc[i0:i1].reset_index(drop=True); nE = len(dE)
    Ex = dE.rename(columns={"o_e": "o", "h_e": "h", "l_e": "l", "c_e": "c"})[["o", "h", "l", "c"]].copy()
    Gx = dE.rename(columns={"o_g": "o", "h_g": "h", "l_g": "l", "c_g": "c"})[["o", "h", "l", "c"]].copy()
    Ex["lab"] = ""; Gx["lab"] = ""
    ja, jb = a0 - i0, b0 - i0
    jga, jgb = ga0 - i0, gb0 - i0

    # 2×2 ızgara ALT ALTA açıldı; satırlar anlam öbeğine göre sıralanır:
    # üst blok = tek örnek (1 EUR/USD · 2 GBP/USD, aynı zaman ekseninde bitişik),
    # alt blok = tüm örneklemin ölçümü (3 MFE çubukları · 4 örneklem kutusu).
    fig = make_subplots(rows=4, cols=1, row_heights=[0.29, 0.29, 0.21, 0.21], vertical_spacing=0.06,
                        subplot_titles=(f"EUR/USD 1 saatlik — {dE.ts[0]:%d %b %Y} – {dE.ts[nE-1]:%d %b %Y}",
                                        "GBP/USD 1 saatlik — aynı zaman ekseni",
                                        "24 saatlik ileri hareket (medyan, pip)",
                                        "Örneklem (2 yıl, 1 saatlik)"))
    fig.add_trace(mum_izi(Ex, ad="EURUSD 1h", hover_ek=[f"{t:%Y-%m-%d %H:%M}" for t in dE.ts]), row=1, col=1)
    fig.add_trace(mum_izi(Gx, ad="GBPUSD 1h", hover_ek=[f"{t:%Y-%m-%d %H:%M}" for t in dE.ts]), row=2, col=1)
    for r, df, ja_, jb_, renk, et in ((1, Ex, ja, jb, BORDO, "LL — yeni dip YAPTI"),
                                      (2, Gx, jga, jgb, TEAL, "HL — yeni dip YAPMADI")):
        yatay(fig, df.l[ja_], 0, nE - 1, renk=ALTIN, w=1.5, row=r, col=1)
        yatay(fig, df.l[jb_], jb_ - 6, nE - 1, renk=renk, dash="dot", w=1.2, row=r, col=1)
        rr = df.h.max() - df.l.min()
        daire(fig, jb_, df.l[jb_] + rr * 0.02, r_x=1.4, r_y=rr * 0.035, renk=renk, row=r, col=1)
        not_(fig, 0.5, df.l[ja_], f"önceki dip {df.l[ja_]:.5f}  ({dE.ts[ja_]:%d %b %H:%M})", renk=ALTIN,
             ok=False, boyut=9, xanchor="left", ay=12, row=r, col=1)
        fark = abs(df.l[jb_] - df.l[ja_]) * 1e4
        not_(fig, jb_, df.l[jb_], f"<b>{et}</b><br>{df.l[jb_]:.5f} ({fark:.1f} pip)", renk=renk, ax=-70, ay=52, row=r, col=1)
        fig.add_vline(x=jb_, line=dict(color=MUREKKEP, width=1.1, dash="dash"), row=r, col=1)
    tik = list(range(0, nE, max(1, nE // 6)))
    # iki mum paneli artık bitişik ve GERÇEKTEN aynı zaman ekseninde (aynı dE
    # indeksi); matches ile bağlanır, ama her biri kendi tarih etiketlerini taşır.
    fig.update_xaxes(tickvals=tik, ticktext=[dE.ts[i].strftime("%d %b %H:%M") for i in tik],
                     tickfont=dict(size=9), row=1, col=1)
    fig.update_xaxes(tickvals=tik, ticktext=[dE.ts[i].strftime("%d %b %H:%M") for i in tik],
                     tickfont=dict(size=9), matches="x", row=2, col=1)
    fig.update_yaxes(tickformat=".4f", title_text="EUR/USD", row=1, col=1)
    fig.update_yaxes(tickformat=".4f", title_text="GBP/USD", row=2, col=1)
    not_(fig, nE - 1, Ex.h.max(), f"<b>BULLISH SMT</b> — {dE.ts[jb]:%d %b %Y %H:%M} (UTC)",
         renk=MUREKKEP, ok=False, boyut=11, xanchor="right", ay=-4, row=1, col=1)
    # row 3: medyan MFE karşılaştırması
    med = lambda v: float(np.median(v)) if len(v) else float("nan")
    gruplar = [("SMT\n(GBP dibi korudu)", [x[1] for x in smt], TEAL),
               ("teyit\n(ikisi de LL)", [x[1] for x in teyit], GRI),
               ("net SMT\n(≥5 pip marj)", [x[1] for x in net], ALTIN)]
    fig.add_trace(go.Bar(x=[g[0].replace("\n", "<br>") for g in gruplar], y=[med(g[1]) for g in gruplar],
                         marker_color=[rgba(g[2], 0.55) for g in gruplar],
                         marker_line=dict(color=[g[2] for g in gruplar], width=1.2),
                         text=[f"{med(g[1]):.0f} pip" for g in gruplar], textposition="outside",
                         showlegend=False), row=3, col=1)
    # dikey dizilimde panel alçaldı; "outside" çubuk etiketleri üstteki panel
    # başlığına girmesin diye tepeye pay bırakılır
    fig.update_yaxes(title_text="medyan MFE, 24 saat (pip)",
                     range=[0, max(med(g[1]) for g in gruplar) * 1.22], row=3, col=1)
    fig.update_xaxes(tickfont=dict(size=9), row=3, col=1)
    # row 4: örneklem ve korelasyon kutusu
    metin = (f"Ortak bar: <b>{len(m):,}</b> (1 saatlik)<br>"
             f"Dönem: {m.ts.iloc[0]:%d %b %Y} – {m.ts.iloc[-1]:%d %b %Y}<br><br>"
             f"EURUSD'de LL yapan swing dibi: <b>{len(smt)+len(teyit)}</b><br>"
             f"  · bunlarda SMT (GBP dibi korudu): <b>{len(smt)}</b><br>"
             f"  · GBP de LL yaptı (teyit): <b>{len(teyit)}</b><br>"
             f"  · her iki tarafta ≥5 pip marjlı 'net SMT': <b>{len(net)}</b><br><br>"
             f"Günlük getiri korelasyonu ρ<sub>60g</sub> = <b>{rho60:.2f}</b> · ρ<sub>250g</sub> = <b>{rho250:.2f}</b> "
             f"(eşik 0,80 ✓)<br><br>"
             f"<b>Bulgu:</b> bu örneklemde SMT'li dipler ({med([x[1] for x in smt]):.0f} pip),<br>"
             f"SMT'siz teyitli diplerden ({med([x[1] for x in teyit]):.0f} pip) <b>daha iyi değil</b>.<br>"
             f"'Güçlü tarafta giriş' kuralı da ayrışmıyor: net SMT'de<br>EURUSD medyanı "
             f"{med([x[1] for x in net]):.0f} pip,<br>GBPUSD medyanı {med([x[2] for x in net]):.0f} pip.<br><br>"
             f"<i>n = {len(net)} çok küçük bir örneklem; bu bir çürütme<br>değil, "
             f"'ölçmeden kullanma' ilkesinin somut hâlidir.</i>".replace(",", "."))
    temiz_eksen(fig, row=4, col=1, x=[0, 1], y=[0, 1])
    # tam genişlikte panelde kutu ortalanır (metin içi sola dayalı kalır)
    fig.add_annotation(x=0.5, y=0.98, xanchor="center", yanchor="top",
                       text=metin, showarrow=False, align="left", font=dict(size=10, color=MUREKKEP),
                       bgcolor="rgba(255,255,255,0.9)", bordercolor=GRI, borderwidth=0.8, borderpad=6,
                       row=4, col=1)
    duzen(fig, "Şekil 14 — Gerçek veri: EUR/USD ↔ GBP/USD SMT divergence ve iki yıllık ölçümü",
          "Kural: 11-mum (k=5) fraktal swing dipleri; EURUSD önceki dibini kırıp GBPUSD kırmıyorsa SMT. "
          "EUR/USD ve GBP/USD panellerinde tek bir örnek, diğer iki panelde aynı kuralın tüm örneklem üzerindeki ölçümü — "
          "yalnız mekanik, bağlam (bias, kill zone) yok",
          x_baslik="", h=1380)
    fig.update_layout(margin=dict(t=118, b=120), legend=dict(y=-0.07))
    fig.update_xaxes(title_text="tarih (UTC; hover'da saat)", row=1, col=1)
    fig.update_xaxes(title_text="tarih (UTC; hover'da saat)", row=2, col=1)
    fig.update_yaxes(title_text="EUR/USD", row=1, col=1)
    fig.update_yaxes(title_text="GBP/USD", row=2, col=1)
    fig.update_yaxes(title_text="medyan MFE, 24 saat (pip)", row=3, col=1)
    # duzen() tüm eksenlere ızgara açar; metin kutusu paneli yeniden temizlenir
    # (tam genişlikte panelde ızgara çizgileri kutunun arkasında görünür oluyordu)
    fig.update_yaxes(title_text="", showticklabels=False, showgrid=False, zeroline=False, row=4, col=1)
    fig.update_xaxes(title_text="", row=3, col=1)
    fig.update_xaxes(title_text="", showticklabels=False, showgrid=False, zeroline=False, row=4, col=1)
    OZET.update(smt_bar=len(m), smt_donem=f"{m.ts.iloc[0]:%d %b %Y} – {m.ts.iloc[-1]:%d %b %Y}",
                smt_ll_olay=len(smt) + len(teyit), smt_n=len(smt), smt_teyit_n=len(teyit), smt_net_n=len(net),
                smt_med_mfe=round(med([x[1] for x in smt]), 1), smt_teyit_med_mfe=round(med([x[1] for x in teyit]), 1),
                smt_net_med_eur=round(med([x[1] for x in net]), 1), smt_net_med_gbp=round(med([x[2] for x in net]), 1),
                smt_rho60=round(rho60, 3), smt_rho250=round(rho250, 3),
                smt_ornek=f"{dE.ts[jb]:%Y-%m-%d %H:%M} UTC",
                smt_ornek_eur=f"{Ex.l[ja]:.5f} → {Ex.l[jb]:.5f}", smt_ornek_gbp=f"{Gx.l[jga]:.5f} → {Gx.l[jgb]:.5f}")
    RAPOR.append(f"Şekil 39 (gerçek): EURUSD/GBPUSD 1h, {len(m)} ortak bar, {m.ts.iloc[0]:%Y-%m-%d}–{m.ts.iloc[-1]:%Y-%m-%d}; "
                 f"LL olayı {len(smt)+len(teyit)}, SMT {len(smt)}, teyit {len(teyit)}, net SMT {len(net)}; "
                 f"medyan 24s MFE: SMT {med([x[1] for x in smt]):.1f} pip / teyit {med([x[1] for x in teyit]):.1f} pip; "
                 f"rho60={rho60:.3f}, rho250={rho250:.3f}; örnek {dE.ts[jb]:%Y-%m-%d %H:%M} "
                 f"EUR {Ex.l[ja]:.5f}→{Ex.l[jb]:.5f}, GBP {Gx.l[jga]:.5f}→{Gx.l[jgb]:.5f}")
    _kaydet(fig, "14_gercek_smt_eurusd_gbpusd")


# =====================================================================================
# 40 — GERÇEK VERİ: haftalık high/low haftanın hangi gününde oluşuyor?
# =====================================================================================
def g40_haftanin_gunu():
    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    enst = [("EURUSD=X", "EUR/USD", TEAL), ("GC=F", "Altın (GC=F)", ALTIN),
            ("XU100.IS", "BIST 100", MAVI), ("BTC-USD", "BTC/USD (Pzt–Cum barları)", MOR)]
    sonuc = []
    for tk, ad, renk in enst:
        df, kay = veri_yukle(tk, "1d", "730d")
        if df is None:
            continue
        d = df.copy()
        d["gun"] = d.ts.dt.dayofweek
        d = d[d.gun < 5].copy()
        iso = d.ts.dt.isocalendar()
        d["hafta"] = iso.year.astype(str) + "-" + iso.week.astype(str)
        hi, lo = [], []
        for _, s in d.groupby("hafta"):
            if len(s) < 5:
                continue
            hi.append(int(s.gun.iloc[int(np.argmax(s.h.values))]))
            lo.append(int(s.gun.iloc[int(np.argmin(s.l.values))]))
        if len(hi) < 30:
            continue
        n = len(hi)
        sonuc.append(dict(ad=ad, renk=renk, n=n, kaynak=kay,
                          d0=df.ts.iloc[0].date(), d1=df.ts.iloc[-1].date(),
                          hi=[100 * np.mean([x == j for x in hi]) for j in range(5)],
                          lo=[100 * np.mean([x == j for x in lo]) for j in range(5)]))
    if not sonuc:
        RAPOR.append("Şekil 40 atlandı: günlük veri yok")
        return
    n_ort = int(np.mean([s["n"] for s in sonuc]))
    se = 100 * np.sqrt(0.2 * 0.8 / n_ort)
    # Paneller ALT ALTA (aynı gün kategorileri, ama iki ayrı ölçüm → shared_xaxes YOK,
    # her panel kendi gün etiketlerini taşır).
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.10,
                        subplot_titles=("(a) Haftalık HIGH hangi gün oluştu? (tam haftaların %'si)",
                                        "(b) Haftalık LOW hangi gün oluştu? (tam haftaların %'si)"))
    for r, anahtar in ((1, "hi"), (2, "lo")):
        for s in sonuc:
            fig.add_trace(go.Bar(x=gunler, y=s[anahtar], name=f"{s['ad']} (n={s['n']})",
                                 marker_color=rgba(s["renk"], 0.55),
                                 marker_line=dict(color=s["renk"], width=1.0),
                                 legendgroup=s["ad"], showlegend=(r == 1)), row=r, col=1)
        fig.add_hline(y=20, line=dict(color=MUREKKEP, width=1.4, dash="dash"), row=r, col=1)
        fig.add_hrect(y0=20 - 1.96 * se, y1=20 + 1.96 * se, fillcolor=rgba(GRI, 0.16), line_width=0,
                      layer="below", row=r, col=1)
        fig.update_yaxes(title_text="tam haftaların %'si", range=[0, 60], row=r, col=1)
        fig.update_xaxes(tickfont=dict(size=10), row=r, col=1)
    not_(fig, 2.0, 20 + 1.96 * se, f"şans beklentisi %20 · gri bant = %95 güven aralığı (n≈{n_ort})",
         renk=GRI, ok=False, boyut=9, ay=-11, row=1, col=1)
    not_(fig, 2.0, 56, "<b>ICT'nin 'Classic Tuesday Low' şablonu bu örneklemde YOK:</b><br>"
         "haftalık dip Salı'da en az görülen günlerden biri.<br>Ekstremler <b>Pazartesi</b> ve <b>Cuma</b>'da kümeleniyor.",
         renk=BORDO, ok=False, boyut=10, row=2, col=1)
    d0 = min(s["d0"] for s in sonuc); d1 = max(s["d1"] for s in sonuc)
    duzen(fig, "Şekil 29 — Gerçek veri: haftalık ekstremler haftanın hangi gününde oluşuyor?",
          f"Günlük mumlar, {d0} – {d1}; yalnız Pzt–Cum barları ve 5 barlık tam haftalar. "
          "Haftalık high = o haftanın en yüksek fitili hangi güne düştü; low simetrik. "
          "Şablon 'tanıma aracı'dır, olasılık dağılımı değil — sayılar kendi enstrümanınızda yeniden ölçülmelidir",
          y_baslik="", x_baslik="", h=700)
    for r in (1, 2):
        fig.update_yaxes(title_text="tam haftaların %'si", row=r, col=1)
    for s in sonuc:
        OZET[f"hafta_gun_{s['ad'].split()[0].replace('/', '')}"] = dict(
            n=s["n"], high=[round(x, 1) for x in s["hi"]], low=[round(x, 1) for x in s["lo"]])
        RAPOR.append(f"Şekil 40 (gerçek): {s['ad']} — {s['kaynak']}, {s['d0']}–{s['d1']}, n={s['n']} tam hafta; "
                     f"high% {['%.0f' % x for x in s['hi']]}, low% {['%.0f' % x for x in s['lo']]} (Pzt→Cum)")
    _kaydet(fig, "29_gercek_haftanin_gunu_profili")


# =====================================================================================
# 41 — Metaorder gerçeği vs "order block" anlatısı
# =====================================================================================
def g41_metaorder():
    s = Seri(41, baslangic=100.00, birim=0.035)
    s.bacak(99.86, 6, gurultu=0.6)
    s.yatay(6, 99.88, genlik=0.8)
    s.mum(99.88, 99.92, 99.80, 99.84, "OB mumu (SMC okuması)")
    s.bacak(100.35, 8)
    s.bacak(100.22, 4, gurultu=0.5)
    s.bacak(100.70, 8)
    df = s.df(); n = len(df)
    i_ob = int(df.index[df.lab.str.startswith("OB")][0])
    # Üç panel ALT ALTA: üçü de farklı x ekseni (mum sırası / Q/V oranı / saat)
    # → shared_xaxes YOK, her panel kendi eksen başlığını korur.
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.08, row_heights=[0.40, 0.30, 0.30],
                        subplot_titles=("(a) Aynı seri, iki okuma", "(b) Kare-kök yasası",
                                        "(c) Hacim eğrisi + makrolar"))
    # (a)
    fig.add_trace(mum_izi(df, ad="5 dk mum"), row=1, col=1)
    kutu(fig, i_ob - 0.5, n - 1, df.l[i_ob], df.h[i_ob], MAVI, a=0.22, cizgi=1.2, row=1, col=1)
    not_(fig, i_ob, df.h[i_ob], "SMC okuması: <b>'kurum burada aldı'</b> → OB", renk=MAVI, ax=95, ay=-42, row=1, col=1)
    # çocuk emirleri: 4 saate (48 bar) yayılmış icra
    rng = np.random.default_rng(410)
    taban = 99.72
    olcek = 0.10
    agir = np.exp(-((np.arange(n) - (i_ob + 6)) / 9.0) ** 2) * 0.55 + 0.35
    q = agir * (0.7 + 0.6 * rng.random(n))
    for i in range(n):
        fig.add_shape(type="line", x0=i, x1=i, y0=taban, y1=taban + q[i] * olcek,
                      line=dict(color=rgba(TURUNCU, 0.75), width=2.0), row=1, col=1)
    ic = q[i_ob] / q.sum() * 100
    fig.add_shape(type="rect", x0=-0.5, x1=n - 1, y0=taban - 0.10, y1=taban - 0.03,
                  fillcolor=rgba(GRI, 0.35), line=dict(color=GRI, width=0.8), row=1, col=1)
    not_(fig, n / 2, taban - 0.065, "grafikte hiç görünmeyen kısım: dark pool / OTC", renk=MUREKKEP,
         ok=False, boyut=9, row=1, col=1)
    not_(fig, i_ob + 6, taban + 0.62 * olcek, f"gerçek: tek bir metaorder onlarca çocuk emre bölünür,<br>"
         f"saatlere yayılır — toplam icranın yalnız ≈%{ic:.0f}'si o mumun içinde kalır", renk=TURUNCU, ax=110, ay=-70, row=1, col=1)
    fig.update_yaxes(range=[99.58, 100.85], title_text="fiyat (şematik)", row=1, col=1)
    fig.update_xaxes(title_text="mum sırası", row=1, col=1)
    # (b) kare-kök yasası
    x = np.linspace(0, 0.10, 200)
    Y = 0.9 * 0.55 * np.sqrt(x / 0.01)          # I = Y·σ·sqrt(Q/V), ölçek normalize
    dogru = Y[-1] / 0.10 * x
    fig.add_trace(go.Scatter(x=x, y=Y, mode="lines", line=dict(color=LACIVERT, width=3),
                             name="ölçülen: I ∝ √(Q/V)"), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=dogru, mode="lines", line=dict(color=GRI, width=2, dash="dash"),
                             name="'büyük emir orantılı hareket ettirir' beklentisi"), row=2, col=1)
    fig.add_trace(go.Scatter(x=np.r_[x, x[::-1]], y=np.r_[Y, dogru[::-1]], fill="toself",
                             fillcolor=rgba(TURUNCU, 0.13), line=dict(width=0), showlegend=False,
                             hoverinfo="skip"), row=2, col=1)
    not_(fig, 0.062, (Y[124] + dogru[124]) / 2, "büyük emir <b>orantısız</b><br>hareket ETMEZ<br>(içbükey etki)",
         renk=TURUNCU, ok=False, boyut=10, row=2, col=1)
    fig.update_xaxes(title_text="emir büyüklüğü Q / günlük hacim V", row=2, col=1, tickformat=".0%")
    fig.update_yaxes(title_text="fiyat etkisi (göreli)", row=2, col=1)
    # (c) VWAP hacim eğrisi + makrolar
    dk = np.arange(9.5 * 60, 16 * 60 + 1, 5.0)
    u = 1.0 + 2.2 * np.exp(-((dk - 585) / 32.0) ** 2) + 1.7 * np.exp(-((dk - 955) / 34.0) ** 2) \
        + 0.5 * np.exp(-((dk - 780) / 120.0) ** 2)
    kenar = np.array([min(m % 60, 60 - m % 60) for m in dk])
    u = u + 0.45 * np.exp(-(kenar / 8.0) ** 2)
    saat = dk / 60.0
    fig.add_trace(go.Scatter(x=saat, y=u, mode="lines", line=dict(color=LACIVERT, width=2.4),
                             fill="tozeroy", fillcolor=rgba(LACIVERT, 0.12), name="gün içi hacim eğrisi (U)"),
                  row=3, col=1)
    for h0, h1 in ((9.833, 10.167), (10.833, 11.167), (11.833, 12.167), (13.167, 13.667), (15.25, 15.75)):
        fig.add_vrect(x0=h0, x1=h1, fillcolor=rgba(TURUNCU, 0.22), line_width=0, layer="below", row=3, col=1)
    not_(fig, 12.9, u.max() * 0.74, "turuncu şeritler =<br>ICT makro pencereleri<br>"
         "<b>aynı saatler —<br>farklı açıklama</b><br>(VWAP dilim sınırı,<br>fixing, MOC toplama)",
         renk=TURUNCU, ok=False, boyut=9, row=3, col=1)
    fig.update_xaxes(title_text="saat (NY)", tickvals=[10, 11, 12, 13, 14, 15, 16],
                     ticktext=["10", "11", "12", "13", "14", "15", "16"], row=3, col=1)
    fig.update_yaxes(title_text="göreli hacim", row=3, col=1)
    duzen(fig, "Şekil 51 — Order flow gerçeği: metaorder vs 'order block' anlatısı",
          "Ne destekliyor: stop kümelenmesi, kare-kök etki yasası, saatlik hacim yoğunlaşması. "
          "Ne çürütüyor: 'tek mum bir kurumsal emir bloğudur' ve 'merkezî bir algoritma retail'i avlar'. "
          "(b) ve (c) şematik eğrilerdir; ölçülmüş olgunun biçimini gösterir, veri değildir",
          y_baslik="", x_baslik="", h=1040)
    fig.update_yaxes(title_text="fiyat (şematik)", row=1, col=1)
    fig.update_yaxes(title_text="fiyat etkisi (göreli)", row=2, col=1)
    fig.update_yaxes(title_text="göreli hacim", row=3, col=1)
    fig.update_xaxes(title_text="mum sırası", row=1, col=1)
    fig.update_xaxes(title_text="Q / V (emir / günlük hacim)", tickformat=".0%", row=2, col=1)
    fig.update_xaxes(title_text="saat (NY)", row=3, col=1)
    _kaydet(fig, "51_metaorder_vs_order_block")


# =====================================================================================
# 42 — Turtle Soup: adım adım dört aşama (aynı seri, dört panel)
# =====================================================================================
def _turtle_seri():
    s = Seri(42, baslangic=100.95, birim=0.05)
    s.bacak(101.10, 3, gurultu=0.6)
    s.mum(101.10, 101.18, 101.02, 101.06, "PDH'ye ilk dokunuş (seviye iki seans tuttu)")
    s.bacak(100.85, 3, gurultu=0.6)
    s.bacak(101.04, 3, gurultu=0.6)
    s.bacak(100.58, 4, gurultu=0.5, lab="son 5m swing low 100.58 = MSS referansı")
    s.bacak(100.95, 2, gurultu=0.5)
    s.mum(100.95, 101.24, 100.88, 100.84, "SWEEP: fitil 101.24 > PDH 101.20; gövde 100.84 İÇERİDE kapandı")
    s.mum(100.84, 100.90, 100.72, 100.75, "M1")
    s.mum(100.75, 100.78, 100.40, 100.44, "M2 displacement — 100.58 altında kapanış = MSS")
    s.mum(100.44, 100.50, 100.30, 100.36, "M3 (FVG: 100.50–100.72, CE 100.61)")
    s.bacak(100.52, 2, gurultu=0.4)
    s.mum(100.52, 100.66, 100.48, 100.58, "FVG CE 100.61'e dönüş → Tetik B limiti doldu")
    s.bacak(100.22, 3)
    s.bacak(99.96, 3, lab="TP1 99.96 (seans içi EQL)")
    s.bacak(100.14, 2, gurultu=0.5)
    s.bacak(99.31, 4, lab="TP2 99.31 (seans low / SSL)")
    s.bacak(99.58, 2, gurultu=0.5)
    s.bacak(98.66, 4, lab="TP3 98.66 (PDL)")
    return s.df()


def g42_turtle_adim_adim():
    df = _turtle_seri(); n = len(df)

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_pdh = idx("PDH"); i_ref = idx("son 5m"); i_sw = idx("SWEEP"); i_m1 = idx("M1")
    i_m2 = idx("M2"); i_m3 = idx("M3"); i_g = idx("FVG CE"); i_t1 = idx("TP1"); i_t2 = idx("TP2"); i_t3 = idx("TP3")
    PDH, ref = 101.20, 100.58
    fvg_alt, fvg_ust = 100.50, 100.72
    ce = (fvg_alt + fvg_ust) / 2
    girisB, SL = 100.61, 101.26
    RB = SL - girisB
    girisA, RA = 100.90, SL - 100.90
    kes = [i_sw, i_m1, i_m3 + 1, n - 1]
    baslik = ("① Adım 1 — HARİTA (sweep'ten ÖNCE):<br>en az iki seans tutmuş PDH işaretlenir",
              "② Adım 2 — SWEEP:<br>fitil ötede, GÖVDE içeride kapandı",
              "③ Adım 3 — MSS +<br>displacement FVG (5 dk)",
              "④ Adım 4 — Giriş / SL / TP:<br>iki tetik, iki farklı R")
    # Dört aşama ALT ALTA: aynı seri, aynı x aralığı → shared_xaxes=True (tek eksen etiketi altta)
    fig = make_subplots(rows=4, cols=1, subplot_titles=baslik, vertical_spacing=0.06, shared_xaxes=True)
    for k, kesim in enumerate(kes):
        r, c = k + 1, 1
        d = df.iloc[:kesim + 1].reset_index(drop=True)
        fig.add_trace(mum_izi(d, ad="5 dk mum", gorunur=(k == 0)), row=r, col=c)
        yatay(fig, PDH, 0, n - 1, renk=ALTIN, w=1.8, row=r, col=c)
        not_(fig, 0.3, PDH, "PDH 101.20 (BSL)", renk=ALTIN, ok=False, boyut=9, xanchor="left", ay=-10, row=r, col=c)
        fig.update_xaxes(range=[-1, n], row=r, col=c)
        fig.update_yaxes(range=[98.35, 101.60], row=r, col=c)
    # panel 1
    yatay(fig, 99.96, 0, n - 1, renk=GRI, dash="dot", row=1, col=1)
    not_(fig, n - 1, 99.96, "iç likidite: seans içi EQL 99.96", renk=GRI, ok=False, boyut=9, xanchor="right", ay=11, row=1, col=1)
    yatay(fig, 98.66, 0, n - 1, renk=GRI, dash="dot", row=1, col=1)
    not_(fig, n - 1, 98.66, "PDL 98.66 (DOL)", renk=GRI, ok=False, boyut=9, xanchor="right", ay=11, row=1, col=1)
    not_(fig, i_pdh, df.h[i_pdh], "seviye iki seans tuttu ✓<br>günlük bias AŞAĞI ✓", renk=MUREKKEP, ax=95, ay=55, row=1, col=1)
    # panel 2
    daire(fig, i_sw, df.h[i_sw] - 0.10, r_x=1.2, r_y=0.10, row=2, col=1)
    not_(fig, i_sw, df.c[i_sw], "fitil 101.24 > 101.20, gövde 100.84 < 101.20<br>"
         "→ sweep. Gövde ÖTEDE kapansaydı: kırılım, işlem yok", renk=ALTIN, ax=-115, ay=55, row=2, col=1)
    # panel 3
    yatay(fig, ref, i_ref, i_m3 + 1, renk=BORDO, dash="dash", w=1.4, row=3, col=1)
    not_(fig, i_ref, ref, "MSS referansı 100.58", renk=BORDO, ok=False, boyut=9, xanchor="left", ay=12, row=3, col=1)
    kutu(fig, i_m1, i_m3 + 1, fvg_alt, fvg_ust, MOR, a=0.22, row=3, col=1)
    yatay(fig, ce, i_m1, i_m3 + 1, renk=MOR, dash="dash", row=3, col=1)
    not_(fig, i_m2, df.c[i_m2], "M2 displacement 100.58 ALTINDA kapandı → MSS<br>"
         "FVG 100.50–100.72, CE = 100.61", renk=BORDO, ax=95, ay=48, row=3, col=1)
    # panel 4
    r, c = 4, 1
    kutu(fig, i_m1, n - 1, fvg_alt, fvg_ust, MOR, a=0.18, row=r, col=c)
    for y, ad, renk, dash in ((SL, f"SL 101.26 = sweep fitilinin (101.24) 2 tik ÜSTÜ", BORDO, "solid"),
                              (girisA, "Tetik A: geri almada stop-emir 100.90 (1R = 0,36)", TURUNCU, "dash"),
                              (girisB, "Tetik B: FVG CE limiti 100.61 (1R = 0,65)", MUREKKEP, "dash"),
                              (99.96, "TP1 99.96", TEAL, "dot"), (99.31, "TP2 99.31", TEAL, "dot"),
                              (98.66, "TP3 98.66", TEAL, "dot")):
        yatay(fig, y, i_sw, n - 1, renk=renk, dash=dash, w=1.6 if dash == "solid" else 1.2, row=r, col=c)
    kutu(fig, i_g, n - 1, girisB, SL, BORDO, a=0.13, cizgi=0, row=r, col=c)
    not_(fig, i_sw + 1, SL, "SL 101,26", renk=BORDO, ok=False, boyut=9, xanchor="left", ay=-10, row=r, col=c)
    not_(fig, i_sw + 1, girisA, "Tetik A 100,90", renk=TURUNCU, ok=False, boyut=9, xanchor="left", ay=-10, row=r, col=c)
    not_(fig, i_g, girisB, "Tetik B 100,61 (FVG CE)", renk=MUREKKEP, ok=False, boyut=9, xanchor="left", ay=-10, row=r, col=c)
    for y, i in ((99.96, i_t1), (99.31, i_t2), (98.66, i_t3)):
        not_(fig, n - 1, y, f"A: +{(girisA-y)/RA:.1f}R  ·  B: +{(girisB-y)/RB:.1f}R", renk=TEAL, ok=False,
             boyut=9, xanchor="right", ay=-10, row=r, col=c)
    not_(fig, 1, 98.75, "<b>Denge:</b> Tetik A yüksek R verir, ama geri alma<br>olmadan devam ederse işlem hiç olmaz. "
         "Tetik B güvenli,<br>ama FVG'ye dönülmezse dolum yok.<br><i>Dolum kesinliği ↔ R:R</i>",
         renk=GRI, ok=False, boyut=9, xanchor="left", row=r, col=c)
    lejant(fig, "FVG (SIBI)", MOR); lejant_cizgi(fig, "PDH / likidite", ALTIN, "solid")
    lejant_cizgi(fig, "Tetik A (erken, geniş stop)", TURUNCU); lejant_cizgi(fig, "Tetik B (2022 modeli, dar stop)", MUREKKEP)
    duzen(fig, "Şekil 33 — Turtle Soup adım adım: haritadan girişe dört aşama (şematik örnek, bearish)",
          "Tarihsel çıpa: Connors & Raschke, Street Smarts (1995) — kırılımı fade etme; ICT versiyonu aynı fikri "
          "intraday ve likidite haritasıyla yeniden yazar. Geçerlilik: seviye ≥2 seans · gövde içeride · "
          "süpürme bias'ın tersine · kill zone içinde · 5m MSS",
          y_baslik="fiyat (şematik birim)", x_baslik="mum sırası (5 dk)", h=1540)
    for r in (1, 2, 3):
        fig.update_xaxes(title_text="", row=r, col=1)
    _kaydet(fig, "33_adim_adim_turtle_soup")


# =====================================================================================
# 43 — Turtle Soup geçerlilik matrisi: dört durum, EVET/HAYIR
# =====================================================================================
def g43_turtle_matris():
    SEV = 101.20

    def seri(seed, tip):
        s = Seri(seed, baslangic=100.86, birim=0.05)
        s.bacak(101.02, 4, gurultu=0.6)
        s.bacak(100.90, 3, gurultu=0.5)
        s.bacak(101.06, 3, gurultu=0.5)
        if tip == "gecerli":
            s.mum(101.06, 101.30, 101.00, 100.86, "sweep")
            s.bacak(100.45, 4); s.bacak(100.00, 4)
        elif tip == "kirilim":
            s.mum(101.06, 101.34, 101.02, 101.29, "gövde ÖTEDE kapandı")
            s.bacak(101.60, 4); s.bacak(101.95, 4)
        elif tip == "zayif":
            s.mum(101.06, 101.26, 101.00, 100.94, "sweep ama seviye tek seanslık")
            s.bacak(101.10, 4, gurultu=0.6); s.bacak(101.40, 4)
        else:  # bias yönünde
            s.mum(101.06, 101.30, 101.00, 100.92, "sweep — ama bias YUKARI")
            s.bacak(101.15, 4, gurultu=0.5); s.bacak(101.70, 4)
        return s.df()

    kurgu = [("(1) Geçerli sweep", "gecerli", "EVET — işlem", TEAL,
              "Fitil 101,30 ötede, gövde 100,86 içeride;<br>seviye iki seans tuttu; bias aşağı"),
             ("(2) Gövde ötede kapandı", "kirilim", "HAYIR — kırılım", BORDO,
              "Bu bir sweep değil, gerçek kırılımdır.<br>Ters yönde işlem intihar"),
             ("(3) Seviye tek seanslık", "zayif", "HAYIR — zayıf", BORDO,
              "Tek seanslık seviyede stop kümesi zayıf;<br>süpürülecek bir şey yok"),
             ("(4) Sweep bias YÖNÜNDE", "bias", "HAYIR — dağıtım", BORDO,
              "Bias yönünde süpürme manipülasyon değil<br>dağıtımdır — trend devam eder")]
    # Dört durum ALT ALTA: her panel AYRI bir kurgu (farklı seri) → shared_xaxes YOK
    fig = make_subplots(rows=4, cols=1, subplot_titles=[k[0] for k in kurgu],
                        vertical_spacing=0.06)
    for j, (ad, tip, rozet, renk, aciklama) in enumerate(kurgu):
        r, c = j + 1, 1
        d = seri(430 + j, tip); nn = len(d)
        fig.add_trace(mum_izi(d, ad="5 dk mum", gorunur=(j == 0)), row=r, col=c)
        yatay(fig, SEV, 0, nn - 1, renk=ALTIN, w=1.8, row=r, col=c)
        i_s = int(d.index[d.lab.str.startswith("sweep") | d.lab.str.startswith("gövde")][0])
        daire(fig, i_s, d.h[i_s] - 0.06, r_x=1.0, r_y=0.09, renk=renk, row=r, col=c)
        fig.add_shape(type="rect", x0=nn - 7.0, x1=nn - 0.4, y0=100.02, y1=100.30,
                      fillcolor=rgba(renk, 0.20), line=dict(color=renk, width=1.2), row=r, col=c)
        not_(fig, (nn - 3.7), 100.16, f"<b>{rozet}</b>", renk=renk, ok=False, boyut=11, row=r, col=c)
        not_(fig, 0.3, 100.02, aciklama, renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="bottom", row=r, col=c)
        not_(fig, 0.3, SEV, "referans seviye 101,20", renk=ALTIN, ok=False, boyut=9, xanchor="left", ay=-10, row=r, col=c)
        fig.update_yaxes(range=[99.80, 102.10], row=r, col=c)
        fig.update_xaxes(range=[-1, nn], row=r, col=c)
    duzen(fig, "Şekil 34 — Turtle Soup geçerlilik matrisi: aynı seviye, dört farklı sonuç (şematik örnek)",
          "Kontrol listesinden bir madde bile 'HAYIR' ise işlem yoktur. Sık hata: her fitili sweep saymak — "
          "iki şart birden gerekir: seviye en az iki seans tutmuş olmalı VE gövde içeride kapanmalı",
          y_baslik="fiyat (şematik birim)", x_baslik="mum sırası (5 dk)", h=1540)
    for r in (1, 2, 3):
        fig.update_xaxes(title_text="", row=r, col=1)
    _kaydet(fig, "34_turtle_soup_gecerlilik_matrisi")


# =====================================================================================
# 44 — ICT 2022 mentorship modeli: adım adım dört aşama
# =====================================================================================
def g44_ict2022():
    s = Seri(44, baslangic=100.14, birim=0.035)
    s.yatay(12, 100.15, genlik=1.0, lab="00:00–03:00 aralığı kapandı")      # 00:00–03:00
    s.bacak(100.02, 2, gurultu=0.5)
    s.mum(100.02, 100.05, 99.88, 99.94, "SWEEP: aralık low 100.00 altına Londra süpürmesi")
    s.mum(99.94, 100.02, 99.92, 100.00, "M1")
    s.mum(100.00, 100.26, 99.99, 100.24, "M2 displacement — aralık içi swing high 100.18 üstü kapanış = MSS")
    s.mum(100.24, 100.30, 100.12, 100.18, "M3 (FVG 100.02–100.12, CE 100.07)")
    s.bacak(100.20, 2, gurultu=0.4)
    s.mum(100.20, 100.22, 100.04, 100.10, "FVG CE 100.07'ye dönüş → giriş")
    s.bacak(100.28, 3); s.bacak(100.46, 4)
    s.bacak(100.38, 2, gurultu=0.4)
    s.bacak(100.78, 5, lab="TP: PDH 100.75 (1:3 eşiği sağlandı)")
    df = s.df(); n = len(df)

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_ar = idx("00:00"); i_sw = idx("SWEEP"); i_m1 = idx("M1"); i_m2 = idx("M2"); i_m3 = idx("M3")
    i_g = idx("FVG CE"); i_tp = idx("TP")
    ar_h, ar_l = df.h[:i_ar + 1].max(), df.l[:i_ar + 1].min()
    giris, sl, tp = 100.07, 99.85, 100.75
    R = giris - sl
    kes = [i_ar, i_sw, i_m3, n - 1]
    bas = ("① 00:00–03:00 aralığı ölçülür<br><b>emir YOK</b> (saat kuralı serttir)",
           "② 03:00 sonrası Londra süpürmesi:<br>aralığın bias'a ters ucu alındı",
           "③ Displacement <b>FVG bırakmalı</b><br>+ MSS (5/3/1 dk)",
           "④ Giriş / SL / TP ve<br><b>minimum 1:3</b> kontrolü")
    # Dört aşama ALT ALTA: aynı seri, aynı x aralığı → shared_xaxes=True
    fig = make_subplots(rows=4, cols=1, subplot_titles=bas, vertical_spacing=0.06, shared_xaxes=True)
    for k, kesim in enumerate(kes):
        r, c = k + 1, 1
        d = df.iloc[:kesim + 1].reset_index(drop=True)
        fig.add_trace(mum_izi(d, ad="15 dk mum", gorunur=(k == 0)), row=r, col=c)
        kutu(fig, -0.5, i_ar, ar_l, ar_h, MAVI, a=0.10, cizgi=1.0, dash="dot", row=r, col=c)
        yatay(fig, ar_l, 0, n - 1, renk=ALTIN, w=1.5, row=r, col=c)
        yatay(fig, ar_h, 0, n - 1, renk=ALTIN, w=1.2, dash="dot", row=r, col=c)
        fig.add_vline(x=i_ar + 0.5, line=dict(color=MUREKKEP, width=1.2, dash="dot"), row=r, col=c)
        fig.update_xaxes(range=[-1, n], row=r, col=c)
        fig.update_yaxes(range=[99.66, 101.00], row=r, col=c)
    not_(fig, i_ar + 0.5, 100.90, "03:00 NY (10:00 TSİ)", renk=MUREKKEP, ok=False, boyut=9, row=1, col=1)
    not_(fig, 1, ar_h, f"aralık {ar_l:.2f} – {ar_h:.2f}", renk=MAVI, ok=False, boyut=9, xanchor="left", ay=-10, row=1, col=1)
    not_(fig, 1, 99.70, "En sık atlanan şart: aralık KAPANMADAN ölçüm yanlıştır.<br>02:40'ta 'olgun' görünmesi kural değiştirmez.",
         renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="bottom", row=1, col=1)
    daire(fig, i_sw, df.l[i_sw] + 0.03, r_x=0.9, r_y=0.035, row=2, col=1)
    not_(fig, i_sw, df.l[i_sw], "aralık low'u süpürüldü", renk=ALTIN, ax=70, ay=45, row=2, col=1)
    not_(fig, 1, 99.70, "Geçersizleşme: aralığın HER İKİ ucu da süpürülürse<br>gün 2022 modeliyle okunamaz — ORG/PO3'e geçilir.",
         renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="bottom", row=2, col=1)
    kutu(fig, i_m1, i_m3, 100.02, 100.12, MOR, a=0.22, row=3, col=1)
    yatay(fig, 100.18, i_ar - 6, i_m3, renk=BORDO, dash="dash", w=1.4, row=3, col=1)
    not_(fig, i_m2, df.c[i_m2], "MSS: 100,18 üstünde kapanış<br>FVG 100,02–100,12 · CE 100,07", renk=TEAL, ax=-110, ay=-46, row=3, col=1)
    not_(fig, 1, 99.70, "FVG yoksa MODEL YOK. Güçlü mum var ama boşluk yoksa,<br>OB'ye düşmek AYRI bir modeldir.",
         renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="bottom", row=3, col=1)
    kutu(fig, i_m1, n - 1, 100.02, 100.12, MOR, a=0.16, row=4, col=1)
    kutu(fig, i_g, n - 1, sl, giris, BORDO, a=0.14, cizgi=0, row=4, col=1)
    kutu(fig, i_g, n - 1, giris, tp, TEAL, a=0.11, cizgi=0, row=4, col=1)
    for y, ad, renk, dash in ((giris, f"giriş {giris:.2f} (FVG CE)", MUREKKEP, "dash"),
                              (sl, f"SL {sl:.2f} (sweep {df.l[i_sw]:.2f} − tampon) → 1R = {R:.2f}", BORDO, "solid"),
                              (tp, f"TP {tp:.2f} (PDH) → +{(tp-giris)/R:.1f}R ✓ ≥ 1:3", TEAL, "dot")):
        yatay(fig, y, i_g - 2, n - 1, renk=renk, dash=dash, w=1.6 if dash == "solid" else 1.2, row=4, col=1)
        not_(fig, i_g - 2, y, ad, renk=renk, ok=False, boyut=9, xanchor="left", ay=-10, row=4, col=1)
    not_(fig, 1, 99.80, "<b>1:3 aritmetiği:</b> p* = 1/(1+R) = 1/4 = <b>%25</b> başabaş isabet.<br>"
         "%40 isabetle E = 0,40·3 − 0,60 = <b>+0,60R</b>; maliyet 0,05R ise net +0,55R.<br>"
         "Aynı model 1:1'e razı olunca 0,40 − 0,60 = <b>−0,20R</b>:<br>hedef düşürmek modeli zarar makinesine çevirir.",
         renk=MUREKKEP, ok=False, boyut=9, xanchor="left", yanchor="bottom", row=4, col=1)
    lejant(fig, "00:00–03:00 aralığı", MAVI, a=0.2); lejant(fig, "FVG", MOR)
    lejant_cizgi(fig, "aralık uçları (likidite)", ALTIN, "solid")
    duzen(fig, "Şekil 35 — ICT 2022 mentorship modeli adım adım: aralık → süpürme → MSS/FVG → 1:3 (şematik örnek)",
          "Takvim (NY / TSİ yaz): 00:00–03:00 ölçüm (07:00–10:00) · 03:00–05:00 Londra KZ (10:00–12:00) · "
          "09:30–11:00 NY AM (16:30–18:00) · 11:00–13:00 öğle: yeni işlem yok",
          y_baslik="fiyat (şematik birim)", x_baslik="mum sırası (15 dk)", h=1540)
    for r in (1, 2, 3):
        fig.update_xaxes(title_text="", row=r, col=1)
    _kaydet(fig, "35_adim_adim_ict2022")


# =====================================================================================
# 45 — Silver Bullet'ın üç penceresi aynı günde
# =====================================================================================
def g45_silver_bullet_uc():
    s = Seri(45, baslangic=100.06, birim=0.045)
    s.bacak(100.00, 4, gurultu=0.6)                                   # 02:00–03:00
    s.mum(100.00, 100.04, 99.84, 99.92, "Londra SB: Asya low 99.90 süpürüldü")
    s.bacak(100.12, 1); s.bacak(100.34, 2, lab="Londra hedefi (orta)")   # 03:15–04:00
    s.bacak(100.20, 6, gurultu=0.6)                                   # 04:00–05:30
    s.bacak(100.36, 6, gurultu=0.6)                                   # 05:30–07:00
    s.bacak(100.10, 4, gurultu=0.6, lab="sabah seansı low 100.10")    # 07:00–08:00
    s.bacak(100.30, 4, gurultu=0.6)                                   # 08:00–09:00
    s.bacak(100.14, 4, gurultu=0.5)                                   # 09:00–10:00
    s.mum(100.14, 100.16, 99.98, 100.08, "NY AM SB: sabah low 100.10 süpürüldü")
    s.bacak(100.42, 1); s.bacak(100.88, 2, lab="NY AM hedefi (en büyük)")  # 10:30–11:00
    s.bacak(100.66, 8, gurultu=0.6)                                   # 11:00–13:00
    s.bacak(100.74, 4, gurultu=0.5)                                   # 13:00–14:00
    s.mum(100.74, 100.78, 100.58, 100.66, "NY PM SB: gün içi EQL 100.60 süpürüldü")
    s.bacak(100.80, 1); s.bacak(100.98, 2, lab="NY PM hedefi (en küçük)")
    s.bacak(100.90, 3, gurultu=0.5)
    df = s.df(); n = len(df)
    zaman = pd.date_range("2025-07-16 02:00", periods=n, freq="15min")

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    fig = go.Figure(mum_izi(df, x=zaman, ad="15 dk mum"))
    pencere = [("03:00", "04:00", "Londra SB 03–04 (TSİ 10–11)", "Asya seansı H/L", ALTIN),
               ("10:00", "11:00", "NY AM SB 10–11 (TSİ 17–18)", "sabah seansı H/L, PDH/PDL, 09:30 ekstremi", TEAL),
               ("14:00", "15:00", "NY PM SB 14–15 (TSİ 21–22)", "AM seansının ucu, gün içi EQH/EQL", MOR)]
    for h0, h1, ad, havuz, renk in pencere:
        fig.add_vrect(x0=pd.Timestamp(f"2025-07-16 {h0}"), x1=pd.Timestamp(f"2025-07-16 {h1}"),
                      fillcolor=rgba(renk, 0.20), line_width=0, layer="below",
                      annotation_text=ad, annotation_position="top left", annotation_font=dict(size=9, color=renk))
        not_(fig, pd.Timestamp(f"2025-07-16 {h0}"), 99.80, f"süpürülen havuz:<br>{havuz}", renk=renk,
             ok=False, boyut=9, xanchor="left", yanchor="top")
        lejant(fig, ad, renk, a=0.35)
    for sw_lab, hd_lab, renk, et in (("Londra SB", "Londra hedefi", ALTIN, "orta"),
                                     ("NY AM SB", "NY AM hedefi", TEAL, "EN BÜYÜK"),
                                     ("NY PM SB", "NY PM hedefi", MOR, "en küçük")):
        i_s, i_h = idx(sw_lab), idx(hd_lab)
        daire(fig, zaman[i_s], df.l[i_s] + 0.03, r_x=pd.Timedelta(minutes=22), r_y=0.035, renk=renk)
        fig.add_annotation(x=zaman[i_h], y=df.h[i_h], ax=zaman[i_s], ay=df.l[i_s], xref="x", yref="y",
                           axref="x", ayref="y", showarrow=True, arrowhead=3, arrowwidth=2.6, arrowcolor=renk, text="")
        boy = (df.h[i_h] - df.l[i_s]) * 100
        not_(fig, zaman[i_h], df.h[i_h], f"hedef büyüklüğü: {boy:.0f} birim ({et})", renk=renk, ax=-10, ay=-34)
    for y, ad in ((99.90, "Asya low (99.90)"), (100.10, "sabah seansı low (100.10)"), (100.60, "gün içi EQL (100.60)")):
        yatay(fig, y, zaman[0], zaman[n - 1], renk=GRI, dash="dot", w=1.0)
        not_(fig, zaman[n - 1], y, ad, renk=GRI, ok=False, boyut=9, xanchor="right", ay=-9)
    tv = list(pd.date_range("2025-07-16 02:00", periods=8, freq="2h"))
    fig.update_xaxes(tickvals=tv, ticktext=[f"{t:%H:%M} NY<br>{(t + pd.Timedelta(hours=7)):%H:%M} TSİ" for t in tv],
                     tickfont=dict(size=10))
    fig.update_yaxes(range=[99.62, 101.20])
    duzen(fig, "Şekil 37 — Silver Bullet'ın üç penceresi aynı günde: farklı havuz, farklı hedef büyüklüğü (şematik örnek)",
          "Ortak, ihlal edilemez liste: harita pencereden ÖNCE çizilir · süpürme pencere İÇİNDE · FVG pencere İÇİNDE oluşur · "
          "geri çekilme pencerenin son 15 dakikasından önce başlar · hedefte gerçek havuz (≥1:2). "
          "Öğrenmeye NY AM ile başlanır; PM en zor penceredir",
          y_baslik="fiyat (şematik birim)", x_baslik="saat (NY / TSİ, ABD yaz saati)", h=680)
    _kaydet(fig, "37_silver_bullet_uc_pencere")


# =====================================================================================
# 46 — OTE tek başına bir model: giriş seviyesi ↔ R:R değiş tokuşu
# =====================================================================================
def g46_ote_rr():
    s = Seri(46, baslangic=100.58, birim=0.045)
    s.bacak(100.22, 4, gurultu=0.6)
    s.mum(100.22, 100.26, 100.00, 100.12, "sweep dibi 100.00 = fib 1.0 (SL referansı)")
    s.bacak(100.48, 2)
    s.bacak(101.00, 4, lab="displacement + MSS tepesi 101.00 = fib 0")
    s.bacak(100.62, 3, gurultu=0.4)
    s.mum(100.62, 100.64, 100.36, 100.40, "0.62 dokunuldu")
    s.mum(100.40, 100.42, 100.28, 100.31, "0.705 dokunuldu")
    s.mum(100.31, 100.33, 100.19, 100.26, "0.79 dokunuldu (derin çekilme)")
    s.bacak(100.62, 3)
    s.bacak(101.02, 4, lab="TP1 101.00")
    s.bacak(100.86, 2, gurultu=0.4)
    s.bacak(101.64, 4, lab="TP2 101.62 (−0.62)")
    df = s.df(); n = len(df)

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_lo, i_hi = idx("sweep dibi"), idx("displacement")
    LOW, HIGH = 100.00, 101.00
    SL = 99.90
    girisler = [(0.62, TEAL), (0.705, ALTIN), (0.79, MOR)]
    TP1, TP2 = 101.00, 101.62
    # İki panel ALT ALTA: (a) mum serisi, (b) kategori çubukları → shared_xaxes YOK
    fig = make_subplots(rows=2, cols=1, row_heights=[0.62, 0.38], vertical_spacing=0.10,
                        subplot_titles=("(a) Aynı bacak, üç giriş seviyesi ve üç ayrı risk kutusu",
                                        "(b) Aynı hedeflerin R karşılığı"))
    fig.add_trace(mum_izi(df, ad="5 dk mum"), row=1, col=1)
    fib_ciz(fig, LOW, HIGH, i_lo, n - 1, yon="bull",
            seviyeler=(0, 0.5, 0.62, 0.705, 0.79, 1.0, -0.62), etiket_x=n - 1, row=1, col=1, kisa=True)
    yatay(fig, SL, i_lo, n - 1, renk=BORDO, w=1.8, row=1, col=1)
    not_(fig, i_lo, SL, f"SL {SL:.2f} = 1.0'ın (sweep ekstremi) ötesi + tampon — <b>0.79'un değil</b>",
         renk=BORDO, ok=False, boyut=9, xanchor="left", ay=11, row=1, col=1)
    satir = []
    for j, (sv, renk) in enumerate(girisler):
        p = HIGH - sv * (HIGH - LOW)
        R = p - SL
        satir.append((sv, p, R, (TP1 - p) / R, (TP2 - p) / R, renk))
        fig.add_shape(type="rect", x0=n - 9 + j * 0.9, x1=n - 8.4 + j * 0.9, y0=SL, y1=p,
                      fillcolor=rgba(renk, 0.28), line=dict(color=renk, width=1.0), row=1, col=1)
        not_(fig, i_hi + 1, p, f"{sv:g} → {p:.3f} (1R = {R:.3f})", renk=renk, ok=False, boyut=9,
             xanchor="left", ay=-9, row=1, col=1)
    not_(fig, n - 7.6, SL, "risk kutuları", renk=GRI, ok=False, boyut=9, xanchor="left", ay=12, row=1, col=1)
    kar = 0.5 * (HIGH - 0.62 * (HIGH - LOW)) + 0.5 * (HIGH - 0.705 * (HIGH - LOW))
    Rk = kar - SL
    not_(fig, 1, 101.80, f"<b>Kademeli limit:</b> yarısı 0.62'de, yarısı 0.705'te → ortalama giriş {kar:.4f}, "
         f"1R = {Rk:.4f}, TP1 = <b>{(TP1-kar)/Rk:.2f}R</b><br>doldurulmama riskini yarıya indirir "
         "(mevcut §7.6 ekleme kurallarıyla uyumlu)", renk=MUREKKEP, ok=False, boyut=9, xanchor="left", row=1, col=1)
    fig.update_yaxes(range=[99.80, 101.95], row=1, col=1)
    fig.update_xaxes(title_text="mum sırası (5 dk)", row=1, col=1)
    # (b)
    ad = [f"{x[0]:g}" for x in satir]
    fig.add_trace(go.Bar(x=ad, y=[x[3] for x in satir], name="TP1 = 101,00 (fib 0)",
                         marker_color=rgba(TEAL, 0.55), marker_line=dict(color=TEAL, width=1.0),
                         text=[f"{x[3]:.2f}R" for x in satir], textposition="outside"), row=2, col=1)
    fig.add_trace(go.Bar(x=ad, y=[x[4] for x in satir], name="TP2 = 101,62 (fib −0.62)",
                         marker_color=rgba(MOR, 0.45), marker_line=dict(color=MOR, width=1.0),
                         text=[f"{x[4]:.2f}R" for x in satir], textposition="outside"), row=2, col=1)
    fig.update_yaxes(title_text="R çarpanı", range=[0, 5.6], row=2, col=1)
    fig.update_xaxes(title_text="giriş seviyesi (fib)", row=2, col=1)
    orn = satir[2][3] / satir[0][3]
    not_(fig, 1.0, 5.15, f"0.62 → 0.79 girişte TP1 R'si <b>{orn:.1f}×</b> artıyor —<br>"
         "ama fiyatın oraya inmeme riski de artıyor.<br>Denge: dolum olasılığı ↔ R:R",
         renk=MUREKKEP, ok=False, boyut=9, row=2, col=1)
    duzen(fig, "Şekil 41 — OTE tek başına bir model: giriş seviyesi seçimi ve R:R değiş tokuşu (şematik örnek)",
          "Fib FİTİL uçlarından çekilir (gövde değil): 1.0 = sweep fitilinin dibi, 0 = displacement tepesi. "
          "OTE bir FİYAT ARALIĞIDIR, bir SEBEP değil — günlük bias, tamamlanmış süpürme, gerçek displacement+MSS "
          "ve kill zone olmadan 0.705 sadece bir sayıdır",
          y_baslik="fiyat (şematik birim)", x_baslik="", h=780)
    fig.update_yaxes(title_text="fiyat (şematik birim)", row=1, col=1)
    fig.update_yaxes(title_text="R çarpanı", row=2, col=1)
    fig.update_xaxes(title_text="mum sırası (5 dk)", row=1, col=1)
    fig.update_xaxes(title_text="giriş seviyesi (fib)", row=2, col=1)
    _kaydet(fig, "41_ote_giris_secimi_rr")
    RAPOR.append("Şekil 46: OTE R tablosu (hesaplandı) — " + " · ".join(
        f"{x[0]:g}: giriş {x[1]:.4f}, 1R {x[2]:.4f}, TP1 {x[3]:.2f}R, TP2 {x[4]:.2f}R" for x in satir)
        + f" · kademeli (0.62+0.705): giriş {kar:.4f}, TP1 {(TP1-kar)/Rk:.2f}R")
    OZET["ote_tablo"] = [dict(sev=x[0], giris=round(x[1], 4), R=round(x[2], 4),
                              tp1=round(x[3], 2), tp2=round(x[4], 2)) for x in satir]


# =====================================================================================
# 47 — Unicorn varyasyonları (2×2)
# =====================================================================================
def g47_unicorn():
    def seri(seed):
        s = Seri(seed, baslangic=100.30, birim=0.045)
        s.bacak(100.02, 4, gurultu=0.6, lab="L")
        s.bacak(100.44, 4, gurultu=0.5, lab="H")
        s.bacak(100.10, 3, gurultu=0.5)
        s.mum(100.10, 100.12, 99.90, 99.98, "LL (sweep)")
        s.mum(99.98, 100.06, 99.96, 100.04, "n1")
        s.mum(100.04, 100.52, 100.02, 100.50, "n2 displacement → HH (kırılım)")
        s.mum(100.50, 100.58, 100.36, 100.42, "n3")
        s.bacak(100.28, 3, gurultu=0.4, lab="banda dönüş")
        s.bacak(100.70, 5); s.bacak(100.96, 4, lab="hedef")
        return s.df()

    kurgu = [("(1) Klasik Unicorn:<br>breaker ∩ displacement FVG", (100.20, 100.34), (100.24, 100.38), TEAL, True,
              "İki bağımsız kanıt aynı bantta → en yüksek güç"),
             ("(2) BPR + breaker", (100.18, 100.32), (100.22, 100.36), MAVI, True,
              "BPR = karşıt iki FVG'nin örtüşmesi; breaker ile çakışıyor"),
             ("(3) IFVG + breaker", (100.16, 100.30), (100.20, 100.34), MOR, True,
              "Ters çevrilmiş FVG breaker bandına düşüyor → orta-yüksek"),
             ("(4) SAHTE Unicorn:<br>örtüşme YOK", (100.06, 100.18), (100.30, 100.42), GRI, False,
              "3 tik uzaklık örtüşme değildir. Tek başına breaker VEYA tek başına FVG model değildir")]
    # Dört varyasyon ALT ALTA: her panel AYRI seri → shared_xaxes YOK
    fig = make_subplots(rows=4, cols=1, subplot_titles=[k[0] for k in kurgu],
                        vertical_spacing=0.06)
    for j, (ad, kutu1, kutu2, renk, gecerli, aciklama) in enumerate(kurgu):
        r, c = j + 1, 1
        d = seri(470 + j); nn = len(d)
        fig.add_trace(mum_izi(d, ad="15 dk mum", gorunur=(j == 0)), row=r, col=c)
        i_b = int(d.index[d.lab.str.startswith("banda")][0])
        kutu(fig, 6, nn - 1, kutu1[0], kutu1[1], MAVI, a=0.20, row=r, col=c)
        kutu(fig, 8, nn - 1, kutu2[0], kutu2[1], MOR, a=0.20, row=r, col=c)
        not_(fig, 6.2, kutu1[1], "breaker", renk=MAVI, ok=False, boyut=9, xanchor="left", ay=-9, row=r, col=c)
        not_(fig, nn - 1, kutu2[0], "FVG / BPR / IFVG", renk=MOR, ok=False, boyut=9, xanchor="right", ay=11, row=r, col=c)
        if gecerli:
            lo = max(kutu1[0], kutu2[0]); hi = min(kutu1[1], kutu2[1])
            kutu(fig, 9, nn - 1, lo, hi, ALTIN, a=0.42, cizgi=1.6, row=r, col=c)
            not_(fig, i_b, (lo + hi) / 2, f"<b>ÖRTÜŞME {lo:.2f}–{hi:.2f}</b><br>limit buraya",
                 renk=ALTIN, ax=-58, ay=-58, row=r, col=c)
            sl = 99.90 - 0.04
            yatay(fig, sl, 9, nn - 1, renk=BORDO, w=1.4, row=r, col=c)
            not_(fig, nn - 1, sl, "SL: FVG'yi yaratan mumun ucu − tampon<br>(muhafazakâr: breaker'ın tamamının altı)",
                 renk=BORDO, ok=False, boyut=8.5, xanchor="right", ay=-14, row=r, col=c)
        else:
            fig.add_shape(type="line", x0=8, x1=nn - 2, y0=kutu1[0], y1=kutu2[1],
                          line=dict(color=KIRMIZI, width=3), row=r, col=c)
            fig.add_shape(type="line", x0=8, x1=nn - 2, y0=kutu2[1], y1=kutu1[0],
                          line=dict(color=KIRMIZI, width=3), row=r, col=c)
            not_(fig, (nn) / 2, 100.72, "<b>MODEL DEĞİL</b>", renk=KIRMIZI, ok=False, boyut=12, row=r, col=c)
        not_(fig, 0.3, 99.56, aciklama, renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="bottom", row=r, col=c)
        fig.update_yaxes(range=[99.50, 101.30], row=r, col=c)
        fig.update_xaxes(range=[-1, nn], row=r, col=c)
    lejant(fig, "breaker", MAVI); lejant(fig, "FVG / BPR / IFVG", MOR); lejant(fig, "örtüşme bandı — emir", ALTIN, a=0.5)
    duzen(fig, "Şekil 38 — Unicorn varyasyonları: örtüşme varsa model, yoksa yok (şematik örnek)",
          "Tarama sırası: 15m'de L→H→LL→HH dizisi bul · kırılan swing'i yaratan OB'yi breaker olarak işaretle · "
          "kırılımı yapan bacakta FVG var mı · <b>fiyat olarak örtüşüyorlar mı</b> · 5m/3m'de örtüşme bandına limit. "
          "Geçersizleşme yalnız GÖVDEYLE karşı tarafa kapanıştır; fitil geçişi değil",
          y_baslik="fiyat (şematik birim)", x_baslik="mum sırası (15 dk)", h=1540)
    for r in (1, 2, 3):
        fig.update_xaxes(title_text="", row=r, col=1)
    _kaydet(fig, "38_unicorn_varyasyonlari")


# =====================================================================================
# 48 — Power of 3: günlük mumun içi ve günlük işlem planı
# =====================================================================================
def g48_po3():
    s = Seri(48, baslangic=99.98, birim=0.030)
    s.yatay(16, 100.00, genlik=0.9, lab="accumulation sonu (02:00)")      # 20:00–02:00 (dün 20:00 başlangıç)
    s.bacak(99.78, 8, gurultu=0.6)                                        # 02:00–04:00
    s.mum(99.78, 99.80, 99.60, 99.66, "Judas dibi 99.60 — havuz alındı (manipulation)")
    s.bacak(99.86, 6, gurultu=0.5)                                        # 04:45–06:15
    s.bacak(99.80, 4, gurultu=0.5)
    s.mum(99.80, 99.84, 99.78, 99.83, "p1")
    s.mum(99.83, 100.06, 99.82, 100.04, "p2 displacement + MSS (FVG 99.84–99.94)")
    s.mum(100.04, 100.10, 99.96, 100.02, "p3")
    s.bacak(99.92, 2, gurultu=0.4, lab="FVG CE 99.89'a dönüş → giriş")
    s.bacak(100.30, 8)                                                    # distribution
    s.bacak(100.20, 4, gurultu=0.5)
    s.bacak(100.90, 10, lab="günün high'ı 100.90 (PDH)")
    s.bacak(100.75, 6, lab="kapanış 100.75 — gün ekstremine yakın")
    df = s.df(); n = len(df)
    zaman = pd.date_range("2025-07-15 20:00", periods=n, freq="15min")

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_j = idx("Judas"); i_g = idx("FVG CE"); i_hi = idx("günün high"); i_k = idx("kapanış")
    O, L, H, C = 100.00, df.l.min(), df.h.max(), df.c[n - 1]
    gunluk = pd.DataFrame(dict(o=[O], h=[H], l=[L], c=[C], lab=["bugünün günlük mumu"]))
    # İki panel ALT ALTA: (a) tek günlük mum, (b) aynı günün 15 dk açılımı.
    # x eksenleri farklı türde (indeks / zaman damgası) → shared_xaxes YOK.
    fig = make_subplots(rows=2, cols=1, row_heights=[0.38, 0.62], vertical_spacing=0.09,
                        subplot_titles=("(a) Günlük mum", "(b) Aynı günün 15 dakikalık açılımı: accumulation → manipulation → distribution"))
    fig.add_trace(mum_izi(gunluk, ad="günlük mum", gorunur=False), row=1, col=1)
    for y, ad, renk in ((O, f"O açılış {O:.2f} (00:00 NY)", MUREKKEP), (L, f"L düşük {L:.2f}", TEAL),
                        (H, f"H yüksek {H:.2f}", BORDO), (C, f"C kapanış {C:.2f}", MUREKKEP)):
        yatay(fig, y, -0.6, 0.6, renk=renk, dash="dot", w=1.2, row=1, col=1)
        not_(fig, 0.62, y, ad, renk=renk, ok=False, boyut=9, xanchor="left", row=1, col=1)
    not_(fig, 0, L - 0.10, "Sıra: <b>O → L → H → C</b><br>(boğa günü)", renk=MUREKKEP, ok=False, boyut=10,
         yanchor="top", row=1, col=1)
    fig.update_xaxes(range=[-1.0, 2.4], showticklabels=False, row=1, col=1)
    fig.update_yaxes(range=[99.20, 101.15], row=1, col=1)
    # (b)
    fig.add_trace(mum_izi(df, x=zaman, ad="15 dk mum"), row=2, col=1)
    fazlar = [("2025-07-15 20:00", "2025-07-16 02:00", "ACCUMULATION 20:00–02:00 — emir YOK", GRI, 0.10),
              ("2025-07-16 02:00", "2025-07-16 05:00", "MANIPULATION (Judas) 02:00–05:00", ALTIN, 0.16),
              ("2025-07-16 08:00", "2025-07-16 11:00", "DISTRIBUTION 08:00–11:00 — giriş burada", TEAL, 0.14),
              ("2025-07-16 13:30", "2025-07-16 16:00", "uzatma 13:30–16:00", MOR, 0.10)]
    for j, (t0, t1, ad, renk, a) in enumerate(fazlar):
        fig.add_vrect(x0=pd.Timestamp(t0), x1=pd.Timestamp(t1), fillcolor=rgba(renk, a), line_width=0,
                      layer="below", row=2, col=1)
        not_(fig, pd.Timestamp(t0), 101.02 - 0.055 * (j % 2), ad.replace(" — ", "<br>"), renk=renk, ok=False,
             boyut=9, xanchor="left", yanchor="top", row=2, col=1)
        lejant(fig, ad.split("—")[0].strip(), renk, a=a + 0.18)
    yatay(fig, O, zaman[0], zaman[n - 1], renk=MUREKKEP, dash="dash", w=2.0, row=2, col=1)
    not_(fig, zaman[2], O, "00:00 NY açılışı = PO3'ün 'O'su · fiyat altındayken discount", renk=MUREKKEP,
         ok=False, boyut=9, xanchor="left", ay=-10, row=2, col=1)
    fig.add_vline(x=pd.Timestamp("2025-07-16 00:00"), line=dict(color=MUREKKEP, width=1.2, dash="dot"), row=2, col=1)
    daire(fig, zaman[i_j], df.l[i_j] + 0.03, r_x=pd.Timedelta(minutes=40), r_y=0.03, row=2, col=1)
    not_(fig, zaman[i_j], df.l[i_j], "Judas: açılışın ALTINA sarkma, havuz alındı<br>"
         "(bias yukarıysa giriş burada ARANIR — dizi tamamlanınca)", renk=ALTIN, ax=125, ay=-58, row=2, col=1)
    kutu(fig, zaman[idx("p1")], zaman[i_hi], 99.84, 99.94, MOR, a=0.20, row=2, col=1)
    giris, sl = 99.89, df.l[i_j] - 0.05
    R = giris - sl
    for y, ad, renk, dash in ((giris, f"giriş {giris:.2f} (FVG CE)", MUREKKEP, "dash"),
                              (sl, f"SL {sl:.2f} → 1R = {R:.2f}", BORDO, "solid"),
                              (100.90, f"TP = günün beklenen ekstremi / PDH 100,90 → +{(100.90-giris)/R:.1f}R", TEAL, "dot")):
        yatay(fig, y, zaman[i_g], zaman[n - 1], renk=renk, dash=dash, w=1.6 if dash == "solid" else 1.2, row=2, col=1)
        not_(fig, zaman[i_g], y, ad, renk=renk, ok=False, boyut=9, xanchor="left", ay=-10, row=2, col=1)
    not_(fig, zaman[i_k], df.c[i_k], "gün ekstremine yakın kapanış → dağıtım tamamlandı", renk=TEAL, ax=-90, ay=40, row=2, col=1)
    tv = list(pd.date_range("2025-07-15 20:00", periods=11, freq="2h"))
    fig.update_xaxes(tickvals=tv, ticktext=[f"{t:%H:%M} NY<br>{(t + pd.Timedelta(hours=7)):%H:%M} TSİ" for t in tv],
                     tickfont=dict(size=9), row=2, col=1)
    fig.update_yaxes(range=[99.20, 101.15], row=2, col=1)
    not_(fig, zaman[2], 99.30, "Geçersizleşme: manipülasyon fazı HER İKİ ucu da süpürürse gün 'range günü'dür — PO3 "
         "okunmaz.<br>11:00'e kadar distribution başlamadıysa gün genelde konsolidasyondur, model kapatılır.",
         renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="bottom", row=2, col=1)
    lejant(fig, "FVG (BISI)", MOR)
    duzen(fig, "Şekil 39 — Power of 3'ü günlük işlem planına çevirmek: günlük mumun içi (şematik örnek, boğa günü)",
          "Boğa günü geçerlilik listesi: bias yukarı mı · fiyat 00:00 açılışının ALTINA sarktı mı (Judas) · "
          "sarkma bir havuz aldı mı · sonrasında displacement+MSS geldi mi · fiyat hâlâ discount'ta mı. "
          "Beşincisi HAYIR ise giriş 'premium'da alım' olur → boyut yarıya ya da atla",
          y_baslik="fiyat (şematik birim)", x_baslik="", h=900)
    fig.update_xaxes(title_text="saat (NY / TSİ, ABD yaz saati)", row=2, col=1)
    fig.update_yaxes(title_text="", row=2, col=1)
    _kaydet(fig, "39_po3_gunluk_plan")


# =====================================================================================
# 49 — Market Maker Buy Model: beş aşama ve hedef zinciri
# =====================================================================================
def g49_mmbm():
    s = Seri(49, baslangic=105.90, birim=0.20)
    s.yatay(10, 106.10, genlik=1.0, lab="1) orijinal konsolidasyon (nihai hedef)")
    s.bacak(103.60, 6)
    s.yatay(4, 103.30, genlik=0.8, lab="K3 konsolidasyonu (103,10)")
    s.bacak(101.60, 6)
    s.yatay(4, 101.30, genlik=0.8, lab="K2 konsolidasyonu (101,10)")
    s.bacak(100.10, 5)
    s.yatay(4, 99.80, genlik=0.8, lab="K1 konsolidasyonu (99,60)")
    s.bacak(98.40, 5)
    s.mum(98.40, 98.50, 97.35, 97.70, "3) smart money reversal: HTF FVG'de sweep + MSS")
    s.bacak(98.70, 3, lab="giriş 98,10 (retest)")
    s.bacak(99.75, 5, lab="→ K1 hedefi"); s.bacak(99.20, 3, gurultu=0.5)
    s.bacak(101.20, 6, lab="→ K2 hedefi"); s.bacak(100.70, 3, gurultu=0.5)
    s.bacak(103.20, 7, lab="→ K3 hedefi"); s.bacak(102.60, 3, gurultu=0.5)
    s.bacak(106.20, 9, lab="5) completion: orijinal konsolidasyona varış")
    df = s.df(); n = len(df)

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_ok = idx("1)"); i_k3 = idx("K3 kon"); i_k2 = idx("K2 kon"); i_k1 = idx("K1 kon")
    i_rev = idx("3)"); i_g = idx("giriş")
    giris, sl = 98.10, 97.10
    R = giris - sl
    hedef = [(99.60, "K1", 0.30), (101.10, "K2", 0.30), (103.10, "K3", 0.20), (106.10, "OK", 0.20)]
    fig = go.Figure(mum_izi(df, ad="1 saatlik mum"))
    kutu(fig, 0, i_ok + 1, 105.55, 106.65, MAVI, a=0.16, cizgi=1.2)
    not_(fig, 0.5, 106.65, "① orijinal konsolidasyon — modelin NİHAİ HEDEFİ", renk=MAVI, ok=False,
         boyut=10, xanchor="left", ay=-10)
    for i0, y0, y1, ad in ((i_k3 - 4, 103.00, 103.60, "K3"), (i_k2 - 4, 101.00, 101.60, "K2"), (i_k1 - 4, 99.50, 100.10, "K1")):
        kutu(fig, i0, i0 + 5, y0, y1, GRI, a=0.18, cizgi=1.0)
        not_(fig, i0, y1, ad, renk=GRI, ok=False, boyut=9, xanchor="left", ay=-9)
    fig.add_annotation(x=i_rev, y=98.2, ax=i_ok + 2, ay=105.7, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowwidth=2.4, arrowcolor=BORDO, text="")
    not_(fig, (i_ok + i_rev) / 2, 102.9, "② low resistance liquidity run<br>(geri çekilmeler sığ, FVG'ler dolmamış)",
         renk=BORDO, ok=False, boyut=10, xanchor="right")
    kutu(fig, i_rev - 3, i_g + 3, 97.30, 98.60, TEAL, a=0.18, cizgi=1.2)
    daire(fig, i_rev, df.l[i_rev] + 0.25, r_x=1.3, r_y=0.35)
    not_(fig, i_rev, df.l[i_rev], "③ smart money reversal: HTF PD array'de sweep + MSS — <b>ANA GİRİŞ</b>",
         renk=TEAL, ax=110, ay=52)
    fig.add_annotation(x=n - 2, y=106.0, ax=i_g, ay=98.4, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowwidth=2.4, arrowcolor=TEAL, text="")
    not_(fig, (i_g + n) / 2 + 4, 100.4, "④ high resistance liquidity run:<br>eski konsolidasyonlar AYNA gibi yeniden ziyaret",
         renk=TEAL, ok=False, boyut=10, xanchor="left")
    yatay(fig, giris, i_g, n - 1, renk=MUREKKEP, dash="dash")
    yatay(fig, sl, i_g, n - 1, renk=BORDO, w=1.8)
    not_(fig, i_g, sl, f"SL {sl:.2f} → 1R = {R:.2f}", renk=BORDO, ok=False, boyut=9, xanchor="left", ay=12)
    not_(fig, i_g, giris, f"giriş {giris:.2f}", renk=MUREKKEP, ok=False, boyut=9, xanchor="left", ay=-10)
    kum = 0.0
    satirlar = []
    for y, ad, pay in hedef:
        yatay(fig, y, i_g, n - 1, renk=TEAL, dash="dot", w=1.2)
        rr = (y - giris) / R
        kum += pay * rr
        satirlar.append(f"{ad} {y:.2f} → {rr:.1f}R · %{pay*100:.0f} kapat · kümülatif {kum:.2f}R")
        not_(fig, n - 1, y, f"{ad}  {rr:.1f}R", renk=TEAL, ok=False, boyut=9, xanchor="right", ay=-9)
    not_(fig, 1, 97.35, "<b>Hedef zinciri (%30/%30/%20/%20):</b><br>" +
         "<br>".join(f"· {x}" for x in satirlar) +
         f"<br>Aynı işlem tek hedefle (K1'de tamamı) yalnız {(hedef[0][0]-giris)/R:.1f}R verirdi. Zincirli hedef "
         "MMXM'in varlık sebebidir;<br>ama bu tablo işlemin SONUNA kadar gittiği senaryodur.",
         renk=MUREKKEP, ok=False, boyut=9, xanchor="left", yanchor="top")
    lejant(fig, "orijinal konsolidasyon (hedef)", MAVI); lejant(fig, "koşu bacağındaki konsolidasyonlar", GRI, a=0.25)
    lejant(fig, "HTF PD array (dönüş bölgesi)", TEAL)
    fig.update_yaxes(range=[95.9, 107.4])
    duzen(fig, "Şekil 40 — Market Maker Buy Model: beş aşama tek grafikte ve hedef merdiveni (şematik örnek)",
          "Neden 'low' ve 'high resistance': fiyat boşluk bırakarak koştuğu bölgeden dönerken kendi bıraktığı "
          "arz/talep engelleriyle karşılaşır. Geçersizleşme: dönüş bacağı K1'i gövdeyle geçemez ve altında kapanırsa "
          "model iptal. En sık hata: MMXM'i GERİYE DÖNÜK görmek — aşama 1 ve 2 canlıda işaretlenmiş olmalıdır",
          y_baslik="fiyat (şematik birim)", x_baslik="mum sırası (1 saat)", h=720)
    _kaydet(fig, "40_mmbm_bes_asama")


# =====================================================================================
# 50 — Opening Range Gap (ORG) + ilk sunulan FVG (FPFVG)
# =====================================================================================
def g42_org_fpfvg():
    s = Seri(50, baslangic=20055.0, birim=3.0)
    s.yatay(6, 20052.0, genlik=1.0, lab="gece seansı (ETH) sonu")            # 09:00–09:29 (5 dk)
    s.mum(20060.0, 20074.0, 20058.0, 20070.0, "09:30 RTH açılışı 20 060 (bu mum FPFVG sayılmaz)")
    s.mum(20070.0, 20072.0, 20054.0, 20056.0, "f1")
    s.mum(20056.0, 20058.0, 20036.0, 20038.0, "f2 displacement (FPFVG 20 036–20 054)")
    s.mum(20038.0, 20044.0, 20030.0, 20034.0, "f3")
    s.bacak(20050.0, 2, gurultu=0.5)
    s.mum(20050.0, 20052.0, 20040.0, 20043.0, "ORG CE 20 030 ∩ FPFVG CE 20 045 bölgesine dönüş → giriş")
    s.bacak(20026.0, 3)
    s.bacak(20000.0, 4, lab="TP1: gap tam kapanışı 20 000")
    s.bacak(20012.0, 2, gurultu=0.5)
    s.bacak(19940.0, 6, lab="TP2: gece seansı düşüğü 19 940")
    s.bacak(19962.0, 3, gurultu=0.5)
    df = s.df(); n = len(df)
    zaman = pd.date_range("2025-07-16 09:00", periods=n, freq="5min")

    def idx(p):
        return int(df.index[df.lab.str.startswith(p)][0])

    i_op = idx("09:30"); i_f1 = idx("f1"); i_g = idx("ORG CE"); i_t1 = idx("TP1"); i_t2 = idx("TP2")
    settle, acilis = 20000.0, 20060.0
    ce_org = (settle + acilis) / 2
    fpf_alt, fpf_ust = 20036.0, 20054.0
    ce_fpf = (fpf_alt + fpf_ust) / 2
    giris, sl = ce_org, acilis + 6
    R = sl - giris
    fig = go.Figure(mum_izi(df, x=zaman, ad="5 dk mum (endeks vadelisi)"))
    fig.add_vrect(x0=pd.Timestamp("2025-07-16 09:30"), x1=pd.Timestamp("2025-07-16 10:00"),
                  fillcolor=rgba(ALTIN, 0.13), line_width=0, layer="below",
                  annotation_text="09:30–10:00 penceresi (TSİ 16:30–17:00)", annotation_position="top left",
                  annotation_font=dict(size=10, color=ALTIN))
    kutu(fig, zaman[0], zaman[n - 1], settle, acilis, GRI, a=0.16, cizgi=1.0)
    yatay(fig, settle, zaman[0], zaman[n - 1], renk=GRI, w=1.6)
    yatay(fig, acilis, zaman[0], zaman[n - 1], renk=GRI, w=1.6)
    yatay(fig, ce_org, zaman[0], zaman[n - 1], renk=MUREKKEP, dash="dash", w=2.0)
    not_(fig, zaman[1], acilis, "bugünkü RTH açılışı 20 060 (premium açılış)", renk=GRI, ok=False, boyut=9,
         xanchor="left", ay=-10)
    not_(fig, zaman[1], settle, "dünkü settlement (16:00/16:15 NY) 20 000", renk=GRI, ok=False, boyut=9,
         xanchor="left", ay=12)
    not_(fig, zaman[1], ce_org, f"ORG CE %50 = {ce_org:.0f}", renk=MUREKKEP, ok=False, boyut=10, xanchor="left", ay=-10)
    kutu(fig, zaman[i_f1], zaman[n - 1], fpf_alt, fpf_ust, MOR, a=0.22)
    yatay(fig, ce_fpf, zaman[i_f1], zaman[n - 1], renk=MOR, dash="dash")
    not_(fig, zaman[i_f1], fpf_ust, f"FPFVG (09:31 sonrası ilk FVG) {fpf_alt:.0f}–{fpf_ust:.0f} · CE {ce_fpf:.0f}",
         renk=MOR, ok=False, boyut=9, xanchor="left", ay=-9)
    not_(fig, zaman[i_op], df.h[i_op], "09:30 mumunun KENDİSİ FPFVG sayılmaz", renk=BORDO, ax=95, ay=-40)
    yatay(fig, sl, zaman[i_g], zaman[n - 1], renk=BORDO, w=1.8)
    kutu(fig, zaman[i_g], zaman[n - 1], giris, sl, BORDO, a=0.14, cizgi=0)
    kutu(fig, zaman[i_g], zaman[n - 1], 19940.0, giris, TEAL, a=0.10, cizgi=0)
    for y, ad, renk in ((giris, f"giriş (short) {giris:.0f}", MUREKKEP),
                        (sl, f"SL {sl:.0f} = açılış + 6 puan → 1R = {R:.0f} puan", BORDO),
                        (20000.0, f"TP1 gap kapanışı 20 000 → +{(giris-20000)/R:.2f}R  ⚠ 1R'nin ALTINDA", TEAL),
                        (19940.0, f"TP2 gece seansı düşüğü 19 940 → +{(giris-19940)/R:.1f}R", TEAL)):
        if renk is TEAL:
            yatay(fig, y, zaman[i_g], zaman[n - 1], renk=renk, dash="dot")
        not_(fig, zaman[i_g], y, ad, renk=renk, ok=False, boyut=9, xanchor="left", ay=-10)
    tv = list(pd.date_range("2025-07-16 09:00", periods=8, freq="15min"))
    fig.update_xaxes(tickvals=tv, ticktext=[f"{t:%H:%M} NY<br>{(t + pd.Timedelta(hours=7)):%H:%M} TSİ" for t in tv],
                     tickfont=dict(size=10))
    not_(fig, zaman[1], 19918.0, "Kaynak iddiası [doğrulanmamış]: 'fiyat ORG'nin en az %50'sini ilk 30 dakikada geri alır, ~%70'. "
         "Bağımsız doğrulaması yok.<br>Model yalnız <b>endeks vadelilerinde</b> (ES/NQ/YM) vardır — forex'te RTH yoktur, "
         "dolayısıyla ORG de yoktur. Sadece gap kapanışını hedefleyen bir ORG işlemi matematiksel olarak zayıftır.",
         renk=GRI, ok=False, boyut=9, xanchor="left")
    lejant(fig, "ORG (settlement → açılış)", GRI, a=0.3); lejant(fig, "FPFVG", MOR)
    lejant_cizgi(fig, "ORG CE %50", MUREKKEP, "dash")
    fig.update_yaxes(range=[19900, 20105], tickformat=".0f")
    duzen(fig, "Şekil 42 — Opening Range Gap ve ilk sunulan FVG (FPFVG): iki katmanlı giriş (şematik örnek)",
          "Geçerlilik: enstrüman endeks vadelisi mi · gap tik gürültüsünden büyük mü · 09:31+ bir 1 dk FVG oluştu mu · "
          "gap yönü günlük bias ile uyumlu mu. Geçersizleşme: 10:00'a kadar CE'ye dönülmediyse emir iptal",
          y_baslik="endeks puanı", x_baslik="saat (NY / TSİ, ABD yaz saati)", h=680)
    _kaydet(fig, "42_org_fpfvg")


# =====================================================================================
# 51 — Emir tipi karar ağacı
# =====================================================================================
def g51_emir_karar_agaci():
    fig = go.Figure()
    d_kutu(fig, 3.4, 6.6, 9.2, 10.0, "Kurulum geçerli — emir tipi seçilecek", MUREKKEP, a=0.10, kalin=True, boyut=12)
    d_kutu(fig, 2.6, 7.4, 7.7, 8.6, "Fiyat bölgeye DÖNEREK mi girecek,<br>yoksa bölgeyi KIRARAK mı?", MAVI, a=0.12, boyut=11)
    d_ok(fig, 5.0, 9.2, 5.0, 8.6)
    # sol dal: dönüş
    d_kutu(fig, 0.3, 4.4, 6.0, 6.9, "DÖNÜŞ (FVG / OB / CE / OTE'ye geri çekilme)", TEAL, a=0.12, boyut=10)
    d_ok(fig, 4.0, 7.7, 2.4, 6.9, renk=TEAL)
    d_kutu(fig, 0.3, 4.4, 4.3, 5.2, "Spread normal mi? (ortalamanın ≤1,5 katı)", GRI, a=0.10, boyut=10)
    d_ok(fig, 2.35, 6.0, 2.35, 5.2, renk=TEAL)
    d_kutu(fig, -0.5, 1.9, 2.4, 3.5, "EVET →<br><b>LİMİT</b> emir<br>(kesişimin ortası / CE / MT)", TEAL, a=0.20, boyut=10)
    d_kutu(fig, 2.4, 4.9, 2.4, 3.5, "HAYIR →<br><b>teyitli MARKET</b><br>(1m tepki mumu + mini-MSS)", ALTIN, a=0.18, boyut=10)
    d_ok(fig, 1.7, 4.3, 0.7, 3.5, renk=TEAL); d_ok(fig, 3.0, 4.3, 3.65, 3.5, renk=ALTIN)
    # sağ dal: kırılım
    d_kutu(fig, 5.6, 9.7, 6.0, 6.9, "KIRILIM (seviyenin geri alınması, Tetik A)", BORDO, a=0.12, boyut=10)
    d_ok(fig, 6.0, 7.7, 7.65, 6.9, renk=BORDO)
    d_kutu(fig, 5.6, 9.7, 4.3, 5.2, "Slipaj bütçesi SL'in %10'undan küçük mü?", GRI, a=0.10, boyut=10)
    d_ok(fig, 7.65, 6.0, 7.65, 5.2, renk=BORDO)
    d_kutu(fig, 5.1, 7.5, 2.4, 3.5, "EVET →<br><b>STOP</b> emir<br>(seviye + tampon)", BORDO, a=0.20, boyut=10)
    d_kutu(fig, 7.7, 10.2, 2.4, 3.5, "HAYIR →<br><b>atla</b><br>(maliyet R'yi yer)", GRI, a=0.18, boyut=10)
    d_ok(fig, 7.0, 4.3, 6.3, 3.5, renk=BORDO); d_ok(fig, 8.3, 4.3, 8.95, 3.5, renk=GRI)
    # çıkış tarafı
    d_kutu(fig, 1.4, 8.4, 0.7, 1.7, "ÇIKIŞ TARAFI HER ZAMAN AYNI: <b>stop-market</b>.<br>"
           "Stop-limit ile korunmaz — boşlukta doldurulmaz ve pozisyon açık kalır.", MUREKKEP, a=0.10, boyut=11)
    for x0 in (0.7, 3.65, 6.3, 8.95):
        d_ok(fig, x0, 2.4, x0 if x0 < 5 else x0, 1.75, renk=GRI, w=1.2)
    # yan not
    d_kutu(fig, 10.6, 15.4, 2.4, 10.0,
           "<b>Maliyet aritmetiği</b><br><br>"
           "c = spread + komisyon + kayma<br><br>"
           "R cinsinden maliyet = c / SL mesafesi<br><br>"
           "Örnek: SL = 15 pip, c = 1,2 pip<br>→ <b>0,08R</b> her işlemde<br><br>"
           "Aynı c, SL = 4 pip'lik bir scalp'te<br>→ <b>0,30R</b>: aynı model, farklı sonuç<br><br>"
           "<i>Bu yüzden emir tipi seçimi bir<br>'tercih' değil, R hesabının parçasıdır.</i>",
           GRI, a=0.09, boyut=10)
    temiz_eksen(fig, x=[-1.2, 16.0], y=[0.2, 10.6])
    duzen(fig, "Şekil 52 — Emir tipi karar ağacı: limit mi, stop mu, teyitli market mi (akış şeması)",
          "Kural: dolum kesinliği ile R:R ters orantılıdır. Limit en iyi fiyatı verir ama doldurulmayabilir; "
          "stop emir doldurulur ama kayma taşır; teyitli market ikisinin ortasıdır ve stopu daraltır",
          y_baslik="", x_baslik="", h=680)
    _kaydet(fig, "52_emir_tipi_karar_agaci")


# =====================================================================================
# 52 — Pozisyon sonrası senaryo ağacı: aynı giriş, üç farklı sonuç
# =====================================================================================
def g52_senaryo_agaci():
    GIRIS, SL0 = 100.00, 99.60
    R = GIRIS - SL0
    T1, T2 = GIRIS + R, GIRIS + 2 * R
    FVG = (99.86, 100.06)

    def ortak(seed):
        s = Seri(seed, baslangic=100.32, birim=0.030)
        s.bacak(100.12, 3, gurultu=0.5)
        s.mum(100.12, 100.14, 99.94, 100.00, "giriş doldu (FVG CE 100.00)")
        return s

    def a():   # hedefe gitti
        s = ortak(520)
        s.bacak(100.16, 2); s.bacak(100.06, 2, gurultu=0.4)
        s.bacak(100.42, 4, lab="TP1 100.40 → %50 kapat + SL BE'ye")
        s.bacak(100.30, 3, gurultu=0.4, lab="HL1")
        s.bacak(100.84, 5, lab="TP2 100.80 → %25 daha kapat")
        s.bacak(100.70, 2, gurultu=0.4, lab="HL2")
        s.bacak(101.22, 5); s.mum(101.22, 101.24, 100.62, 100.66, "runner trailing'de çıktı (HL2 altı)")
        return s.df()

    def b():   # BE'ye döndü
        s = ortak(521)
        s.bacak(100.18, 2); s.bacak(100.08, 2, gurultu=0.4)
        s.bacak(100.42, 4, lab="TP1 100.40 → %50 kapat + SL BE'ye")
        s.bacak(100.24, 3, gurultu=0.4)
        s.bacak(100.34, 3, gurultu=0.4)
        s.mum(100.20, 100.22, 99.96, 99.98, "BE'de kapandı → kalan %50 sıfır")
        s.bacak(99.80, 4)
        return s.df()

    def c():   # geçersizleşti
        s = ortak(522)
        s.bacak(100.10, 2, gurultu=0.4)
        s.bacak(100.04, 3, gurultu=0.4)
        s.mum(100.02, 100.04, 99.80, 99.84, "gövde FVG'nin ALTINDA kapandı → yapı bozuldu")
        s.bacak(99.88, 2, gurultu=0.4, lab="erken çıkış ≈ −0,4R (SL beklenmedi)")
        s.bacak(99.58, 3); s.bacak(99.30, 4)
        return s.df()

    seriler = [("(a) Hedefe gitti", a(), TEAL), ("(b) TP1 sonrası BE'ye döndü", b(), ALTIN),
               ("(c) Geçersizleşti — erken çıkış", c(), BORDO)]
    # Üç senaryo ALT ALTA: her panel AYRI seri → shared_xaxes YOK
    fig = make_subplots(rows=3, cols=1, subplot_titles=[x[0] for x in seriler], vertical_spacing=0.07)
    for j, (ad, d, renk) in enumerate(seriler):
        r_ = j + 1
        nn = len(d)
        fig.add_trace(mum_izi(d, ad="5 dk mum", gorunur=(j == 0)), row=r_, col=1)
        kutu(fig, 0, nn - 1, FVG[0], FVG[1], MOR, a=0.18, row=r_, col=1)
        for y, rk, dash in ((GIRIS, MUREKKEP, "dash"), (SL0, BORDO, "solid"), (T1, TEAL, "dot"), (T2, TEAL, "dot")):
            yatay(fig, y, 0, nn - 1, renk=rk, dash=dash, w=1.6 if dash == "solid" else 1.1, row=r_, col=1)
        if j == 0:
            for y, t in ((GIRIS, "giriş 100,00"), (SL0, "SL₀ 99,60 (1R = 0,40)"), (T1, "TP1 100,40 (1R)"), (T2, "TP2 100,80 (2R)")):
                not_(fig, 0.3, y, t, renk=MUREKKEP if y in (GIRIS,) else (BORDO if y == SL0 else TEAL),
                     ok=False, boyut=9, xanchor="left", ay=-10, row=r_, col=1)
        fig.update_yaxes(range=[99.20, 101.42], row=r_, col=1)
        fig.update_xaxes(range=[-1, nn], row=r_, col=1)
    # (a) anotasyonlar
    da = seriler[0][1]; na = len(da)
    i = lambda d, p: int(d.index[d.lab.str.startswith(p)][0])
    not_(fig, i(da, "TP1"), T1, "①  TP1 → %50 kapat, SL <b>BE'ye</b><br>(BE T1'den ÖNCE değil)", renk=TEAL,
         ax=75, ay=-42, row=1, col=1)
    not_(fig, i(da, "TP2"), T2, "②  TP2 → %25 daha; kalan %25 runner", renk=TEAL, ax=-72, ay=-30, row=1, col=1)
    not_(fig, i(da, "runner"), da.l[i(da, "runner")], "③  runner: her onaylı yeni HL'nin altına trailing", renk=BORDO,
         ax=-60, ay=52, row=1, col=1)
    top = 0.5 * 1.0 + 0.25 * 2.0 + 0.25 * ((100.66 - GIRIS) / R)
    not_(fig, 1, 99.32, f"sonuç ≈ <b>+{top:.2f}R</b>", renk=TEAL, ok=False, boyut=11, xanchor="left", row=1, col=1)
    # (b)
    db = seriler[1][1]
    not_(fig, i(db, "TP1"), T1, "TP1 alındı: %50 kilitlendi (+0,50R)", renk=ALTIN, ax=-60, ay=-40, row=2, col=1)
    not_(fig, i(db, "BE'de"), GIRIS, "momentum öldü; kalan %50 BE'de kapandı<br>"
         "→ 'kazanan' değil ama <b>kayıp da değil</b>", renk=ALTIN, ax=-40, ay=48, row=2, col=1)
    not_(fig, 1, 99.32, "sonuç = <b>+0,50R</b>", renk=ALTIN, ok=False, boyut=11, xanchor="left", row=2, col=1)
    # (c)
    dc = seriler[2][1]
    not_(fig, i(dc, "gövde"), dc.c[i(dc, "gövde")], "FVG gövdeyle karşı tarafa<br>kapatıldı → <b>yapı bozuldu</b>",
         renk=BORDO, ax=-40, ay=-48, row=3, col=1)
    not_(fig, i(dc, "erken"), dc.c[i(dc, "erken")], "erken çık: SL'i BEKLEME<br>(−0,4R, −1,0R değil)", renk=BORDO,
         ax=-52, ay=48, row=3, col=1)
    not_(fig, 1, 99.32, "sonuç ≈ <b>−0,40R</b> (SL beklenseydi −1,00R)", renk=BORDO, ok=False, boyut=11,
         xanchor="left", row=3, col=1)
    lejant(fig, "FVG (giriş bölgesi)", MOR); lejant_cizgi(fig, "hedefler", TEAL, "dot")
    lejant_cizgi(fig, "SL / giriş", BORDO, "solid")
    duzen(fig, "Şekil 45 — Pozisyon sonrası senaryo ağacı: aynı giriş, üç farklı sonuç (şematik örnek)",
          "Karar kuralları aynı, sonuçlar farklı. Okunacak şey: giriş sonrası mumların GÖVDESİ nerede kapanıyor. "
          "İki ardışık gövde bölgenin dışında kapanırsa erken çık; TP1'den önce BE'ye çekme; "
          "trailing yalnız onaylı yeni HL/LH sonrası",
          y_baslik="fiyat (şematik birim)", x_baslik="mum sırası (5 dk)", h=1200)
    _kaydet(fig, "45_pozisyon_senaryo_agaci")


# =====================================================================================
# 53 — MAE / MFE ile SL ve TP kalibrasyonu
# =====================================================================================
def g53_mae_mfe():
    rng = np.random.default_rng(53)
    # MAE bantları (kurgu, C.2.4 tablosu): kazanan / kaybeden sayıları
    bant = [(0.00, 0.20, 14, 3), (0.20, 0.40, 15, 6), (0.40, 0.60, 9, 7), (0.60, 0.80, 3, 9), (0.80, 1.00, 1, 33)]
    kaz_mae, kaz_r, kay_mae, kay_r = [], [], [], []
    for a, b, nk, nl in bant:
        for _ in range(nk):
            kaz_mae.append(rng.uniform(a, b))
            kaz_r.append(max(0.35, rng.gamma(2.2, 1.05)))
        for _ in range(nl):
            kay_mae.append(rng.uniform(a, b))
            kay_r.append(-1.0 if b > 0.95 else -rng.uniform(0.25, 0.9))
    kaz_r = np.array(kaz_r) * (2.40 / np.mean(kaz_r))
    kay_r = np.array(kay_r) * (0.96 / abs(np.mean(kay_r)))
    kay_r = np.clip(kay_r, -1.0, -0.10)
    E = len(kaz_r) / 100 * np.mean(kaz_r) + len(kay_r) / 100 * np.mean(kay_r)
    M90 = float(np.percentile(kaz_mae, 90))
    T = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
    p = [0.78, 0.61, 0.47, 0.38, 0.24, 0.11]
    bek = [pp * tt - (1 - pp) for pp, tt in zip(p, T)]

    # İki panel ALT ALTA: (a) MAE saçılımı, (b) MFE merdiveni (çift y eksenli)
    fig = make_subplots(rows=2, cols=1, row_heights=[0.55, 0.45], vertical_spacing=0.12,
                        subplot_titles=("(a) MAE dağılımı: kazananlar nereye kadar aleyhe gitti?",
                                        "(b) MFE merdiveni: hangi hedef ne kadar ödüyor?"),
                        specs=[[{}], [{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=kaz_mae, y=kaz_r, mode="markers", name="kazanan işlem",
                             marker=dict(size=8, color=rgba(TEAL, 0.65), line=dict(color=TEAL, width=0.8))),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=kay_mae, y=kay_r, mode="markers", name="kaybeden işlem",
                             marker=dict(size=8, color=rgba(BORDO, 0.55), symbol="x", line=dict(color=BORDO, width=0.8))),
                  row=1, col=1)
    fig.add_vline(x=1.0, line=dict(color=BORDO, width=2), row=1, col=1)
    fig.add_vline(x=M90, line=dict(color=MAVI, width=2, dash="dash"), row=1, col=1)
    fig.add_vrect(x0=M90, x1=1.0, fillcolor=rgba(BORDO, 0.10), line_width=0, layer="below", row=1, col=1)
    fig.add_hline(y=0, line=dict(color=GRI, width=1), row=1, col=1)
    not_(fig, 1.0, 6.4, "mevcut SL = 1,00R", renk=BORDO, ok=False, boyut=10, ay=-8, row=1, col=1)
    not_(fig, M90, 5.5, f"M₉₀ = {M90:.2f}R<br>(kazananların %90'ı burada kaldı)", renk=MAVI, ok=False, boyut=10,
         ay=-8, row=1, col=1)
    not_(fig, (M90 + 1.0) / 2, 3.4, "stopun son bölümü:<br>kazananların yalnız<br>%9,5'ini kurtarır,<br>"
         "her kaybedende<br>TAM ödenir", renk=BORDO, ok=False, boyut=9, row=1, col=1)
    fig.update_xaxes(title_text="MAE — aleyhe azami sapma (R)", range=[-0.02, 1.12], row=1, col=1)
    fig.update_yaxes(title_text="işlem sonucu (R)", row=1, col=1)
    # (b)
    fig.add_trace(go.Bar(x=[f"{t:g}R" for t in T], y=[100 * x for x in p], name="p(MFE ≥ T)",
                         marker_color=rgba(MAVI, 0.45), marker_line=dict(color=MAVI, width=1.0),
                         text=[f"%{100*x:.0f}" for x in p], textposition="outside"), row=2, col=1)
    fig.add_trace(go.Scatter(x=[f"{t:g}R" for t in T], y=bek, name="'T'de tam kapat' beklentisi (R)",
                             mode="lines+markers", line=dict(color=TURUNCU, width=2.6),
                             marker=dict(size=9, color=TURUNCU)), row=2, col=1, secondary_y=True)
    fig.add_trace(go.Scatter(x=[f"{t:g}R" for t in T], y=[0.34] * len(T), name="50/25/25 ölçekli çıkış: +0,34R",
                             mode="lines", line=dict(color=TEAL, width=2.2, dash="dash")), row=2, col=1, secondary_y=True)
    fig.add_hline(y=0, line=dict(color=GRI, width=1), row=2, col=1, secondary_y=True)
    fig.update_yaxes(title_text="p(MFE ≥ T)  (%)", range=[0, 100], row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="işlem başına beklenti (R)", range=[-0.62, 0.62], row=2, col=1, secondary_y=True)
    fig.update_xaxes(title_text="hedef eşiği T", row=2, col=1)
    not_(fig, "2R", 88, "çıplak 3R hedefi <b>negatif</b> (−0,04R) · tek hedefin<br>en iyisi 1,0R (+0,22R) · "
         "ölçekli çıkış ikisini de yener (+0,34R)", renk=MUREKKEP, ok=False, boyut=9, row=2, col=1,
         xanchor="center")
    duzen(fig, "Şekil 55 — MAE/MFE ile SL ve TP kalibrasyonu (kurgu örnek, n = 100 — kendi verinizle yeniden hesaplanır)",
          f"Bu kurgu örneklemde E[R] = +{E:.2f}R. MAE kalibrasyonunun doğru kullanımı stopu keyfî daraltmak DEĞİL, "
          "GİRİŞ yerini iyileştirmektir; kalibrasyon aynı örneklemde uygulanıp 'iyileşti' denemez (OOS %30 şart)",
          y_baslik="", x_baslik="", h=700)
    fig.update_yaxes(title_text="işlem sonucu (R)", row=1, col=1)
    fig.update_yaxes(title_text="p(MFE ≥ T)  (%)", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="işlem başına beklenti (R)", row=2, col=1, secondary_y=True)
    fig.update_xaxes(title_text="MAE — aleyhe azami sapma (R)", row=1, col=1)
    fig.update_xaxes(title_text="hedef eşiği T", row=2, col=1)
    _kaydet(fig, "55_mae_mfe_kalibrasyon")
    OZET.update(mae_M90=round(M90, 2), mae_E=round(float(E), 3))


# =====================================================================================
# 54 — 100 işlemin R dağılımı, kümülatif R eğrisi ve bootstrap belirsizlik konisi
# =====================================================================================
def g54_r_dagilimi():
    rng = np.random.default_rng(54)
    nk, nl = 42, 58
    kaz = rng.gamma(1.9, 1.0, nk) + 0.30
    kaz = kaz * (2.40 / kaz.mean())
    kay = np.where(rng.random(nl) < 0.83, -1.0, -rng.uniform(0.20, 0.85, nl))
    kay = kay * (0.96 / abs(kay.mean()))
    kay = np.clip(kay, -1.05, -0.15)
    R = np.concatenate([kaz, kay])
    rng.shuffle(R)
    kum = np.cumsum(R)
    ER = R.mean(); sR = R.std(ddof=1); t = ER * np.sqrt(len(R)) / sR
    # bootstrap
    B = 10000
    ornek = rng.choice(R, size=(B, len(R)), replace=True)
    kum_b = np.cumsum(ornek, axis=1)
    alt = np.percentile(kum_b, 5, axis=0); ust = np.percentile(kum_b, 95, axis=0)
    ortanca = np.percentile(kum_b, 50, axis=0)
    tepe = np.maximum.accumulate(kum)
    dd = kum - tepe
    x = np.arange(1, len(R) + 1)

    fig = make_subplots(rows=3, cols=1, row_heights=[0.28, 0.46, 0.26], vertical_spacing=0.105,
                        subplot_titles=("(a) R dağılımı (x = işlem sonucu, R) — −1R'de yığılma, sağ kuyruk",
                                        "(b) Kümülatif R eğrisi ve 10.000 bootstrap örneğinin %5–%95 konisi",
                                        "(c) Çekilme (drawdown), R cinsinden"))
    kenar = np.arange(-1.1, 7.4, 0.25)
    fig.add_trace(go.Histogram(x=R, xbins=dict(start=-1.1, end=7.4, size=0.25),
                               marker_color=rgba(LACIVERT, 0.55), marker_line=dict(color=LACIVERT, width=0.6),
                               name="işlem sonuçları (R)"), row=1, col=1)
    fig.add_vline(x=0, line=dict(color=GRI, width=1), row=1, col=1)
    fig.add_vline(x=ER, line=dict(color=TURUNCU, width=2, dash="dash"), row=1, col=1)
    not_(fig, ER, 26, f"ortalama E[R] = +{ER:.2f}R", renk=TURUNCU, ok=False, boyut=10, ay=-8, row=1, col=1)
    fig.update_xaxes(title_text="işlem sonucu (R)", row=1, col=1)
    fig.update_yaxes(title_text="işlem sayısı", row=1, col=1)
    fig.add_trace(go.Scatter(x=np.r_[x, x[::-1]], y=np.r_[ust, alt[::-1]], fill="toself",
                             fillcolor=rgba(GRI, 0.22), line=dict(width=0), name="bootstrap %5–%95 konisi",
                             hoverinfo="skip"), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=ortanca, mode="lines", line=dict(color=GRI, width=1.6, dash="dot"),
                             name="bootstrap medyanı"), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=kum, mode="lines", line=dict(color=LACIVERT, width=2.8),
                             name="gerçekleşen kümülatif R"), row=2, col=1)
    fig.add_hline(y=0, line=dict(color=GRI, width=1), row=2, col=1)
    not_(fig, 62, alt[61], f"aynı sistem, aynı dağılım — <b>bu kadar farklı eğriler</b><br>"
         f"100 işlem sonunda %5–%95 aralığı: {alt[-1]:+.1f}R … {ust[-1]:+.1f}R", renk=MUREKKEP,
         ok=False, boyut=10, yanchor="top", row=2, col=1)
    fig.update_yaxes(title_text="kümülatif R", row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=dd, mode="lines", line=dict(color=BORDO, width=1.8), fill="tozeroy",
                             fillcolor=rgba(BORDO, 0.16), name="çekilme (R)"), row=3, col=1)
    not_(fig, int(np.argmin(dd)) + 1, dd.min(), f"azami çekilme {dd.min():.2f}R", renk=BORDO, ax=60, ay=-28, row=3, col=1)
    fig.update_yaxes(title_text="çekilme (R)", row=3, col=1)
    fig.update_xaxes(title_text="işlem sırası", row=3, col=1)
    duzen(fig, "Şekil 54 — 100 işlemin R dağılımı, kümülatif eğrisi ve bootstrap belirsizliği (kurgu örnek)",
          f"Bu örneklemde isabet %{100*np.mean(R > 0):.0f}, E[R] = +{ER:.2f}R, s_R = {sR:.2f}, "
          f"t = R̄·√n/s_R = <b>{t:.2f}</b> (Van Tharp SQN mantığı: t > 2,0 kalite eşiği). "
          "Dersin en önemli görsellerinden: 100 işlem, edge'i GÖRMEK için çoğu zaman yetmez — "
          "0,15R'lik bir edge için %95 anlamlılıkta ≈656, %80 güçte ≈1339 işlem gerekir",
          y_baslik="", x_baslik="", h=880)
    fig.update_layout(bargap=0.06)
    fig.update_yaxes(title_text="işlem sayısı", row=1, col=1)
    fig.update_yaxes(title_text="kümülatif R", row=2, col=1)
    fig.update_yaxes(title_text="çekilme (R)", row=3, col=1)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    fig.update_xaxes(title_text="işlem sırası", row=3, col=1)
    _kaydet(fig, "54_R_dagilimi_kumulatif_bootstrap")
    OZET.update(r_isabet=round(float(np.mean(R > 0)) * 100, 1), r_ER=round(float(ER), 3), r_sR=round(float(sR), 2),
                r_t=round(float(t), 2), r_koni=[round(float(alt[-1]), 1), round(float(ust[-1]), 1)],
                r_maxdd=round(float(dd.min()), 2))
    RAPOR.append(f"Şekil 54 (kurgu, seed 54): isabet %{100*np.mean(R>0):.0f}, E[R]={ER:.3f}R, s_R={sR:.2f}, "
                 f"t={t:.2f}, 100 işlem sonu bootstrap %5–%95 = {alt[-1]:+.1f}R…{ust[-1]:+.1f}R, "
                 f"azami çekilme {dd.min():.2f}R")


# =====================================================================================
# 55 — Aynı an, iki feed: birinde sweep var, diğerinde yok
# =====================================================================================
def g55_broker_feed():
    PDL = 1.08500

    def seri(seed, dip):
        s = Seri(seed, baslangic=1.08536, birim=0.000030)
        s.bacak(1.08518, 4, gurultu=0.5)
        s.bacak(1.08507, 3, gurultu=0.4)
        s.mum(1.08507, 1.08509, dip, 1.08506, "kritik mum")
        s.mum(1.08506, 1.08523, 1.08505, 1.08521, "tepki")
        s.bacak(1.08535, 3)
        s.bacak(1.08556, 4, lab="hedef")
        return s.df()

    A = seri(551, 1.08496)     # PDL'nin 0,4 pip altı → sweep var
    B = seri(552, 1.08502)     # PDL'ye 0,2 pip kala durdu → sweep yok
    # İki feed ALT ALTA: iki AYRI veri sağlayıcısının serisi → shared_xaxes YOK
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.10,
                        subplot_titles=("(a) Broker A feed'i:<br>fitil PDL'nin <b>0,4 pip altına</b> indi",
                                        "(b) Broker B feed'i:<br>fitil PDL'ye <b>0,2 pip kala</b> durdu"))
    for j, (d, renk, hkm, aciklama) in enumerate(
            ((A, TEAL, "SWEEP VAR → setup geçerli", "MSS bekle, FVG'ye limit — işlem açılır"),
             (B, BORDO, "SWEEP YOK → setup yok", "Aynı an, aynı enstrüman, farklı sağlayıcı — işlem açılmaz"))):
        r = j + 1
        nn = len(d)
        fig.add_trace(mum_izi(d, ad="1 dk mum", gorunur=(j == 0)), row=r, col=1)
        yatay(fig, PDL, 0, nn - 1, renk=ALTIN, w=1.8, row=r, col=1)
        not_(fig, 0.3, PDL, f"PDL {PDL:.5f}", renk=ALTIN, ok=False, boyut=9, xanchor="left", ay=12, row=r, col=1)
        i_k = int(d.index[d.lab == "kritik mum"][0])
        daire(fig, i_k, d.l[i_k] + 0.00002, r_x=0.9, r_y=0.000030, renk=renk, row=r, col=1)
        not_(fig, i_k, d.l[i_k], f"fitil dibi {d.l[i_k]:.5f}<br>({(d.l[i_k]-PDL)*1e4:+.1f} pip)", renk=renk,
             ax=-58, ay=52, row=r, col=1)
        fig.add_shape(type="rect", x0=nn - 7.6, x1=nn - 0.4, y0=1.085495, y1=1.085595,
                      fillcolor=rgba(renk, 0.20), line=dict(color=renk, width=1.2), row=r, col=1)
        not_(fig, nn - 4.0, 1.085545, f"<b>{hkm}</b>", renk=renk, ok=False, boyut=10, row=r, col=1)
        not_(fig, nn - 0.4, 1.085485, aciklama, renk=GRI, ok=False, boyut=9, xanchor="right", yanchor="top",
             row=r, col=1)
        fig.update_yaxes(range=[1.08462, 1.08572], tickformat=".5f", row=r, col=1)
        fig.update_xaxes(range=[-1, nn], row=r, col=1)
    not_(fig, 0.3, 1.084655,
         "<b>Kural — minimum aşım eşiği:</b> bir aşımın 'sweep' sayılması için <b>≥ 1 pip</b> ya da "
         "<b>≥ 0,3 × ATR(1 dk)</b> olmalıdır.<br>Bu eşik olmadan setup'ınız broker seçiminize bağlı olur; "
         "ve backtest'iniz canlı hesabınızla asla eşleşmez.<br>FX tezgâh üstüdür — tek bir 'gerçek fiyat' yoktur.",
         renk=MUREKKEP, ok=False, boyut=9.5, xanchor="left", yanchor="bottom", row=1, col=1)
    duzen(fig, "Şekil 53 — Aynı an, iki farklı feed: birinde sweep var, diğerinde yok (şematik örnek)",
          "Aynı senaryo iki farklı fitil uzunluğuyla. FX'te fitil uçları sağlayıcıya göre değişir; "
          "'seviyenin 0,2 pip altı/üstü' bir teknik olgu değil, bir veri kaynağı farkıdır",
          y_baslik="", x_baslik="", h=860)
    for r in (1, 2):
        fig.update_yaxes(title_text="fiyat" if r == 1 else "", row=r, col=1)
        fig.update_xaxes(title_text="mum sırası (1 dk)", row=r, col=1)
    _kaydet(fig, "53_broker_feed_farki")


# =====================================================================================
# 56 — Türkiye saatiyle işlem günü: kill zone'lar, BIST, VIOP (zaman şeridi)
# =====================================================================================
def g56_turkiye_zaman():
    # (ad, başlangıç, bitiş, renk, yaz→kış kayması saat)
    seritler = [
        ("Asya seansı (ICT)", 3.0, 7.0, GRI, 1),
        ("Londra kill zone", 9.0, 12.0, ALTIN, 1),
        ("Londra Silver Bullet", 10.0, 11.0, ALTIN, 1),
        ("NY açılışı (09:30 NY)", 16.5, 16.75, TEAL, 1),
        ("NY AM Silver Bullet", 17.0, 18.0, TEAL, 1),
        ("NY PM Silver Bullet", 21.0, 22.0, MOR, 1),
        ("ABD makro verisi (08:30 NY)", 15.5, 15.75, BORDO, 1),
        ("BIST Pay — sürekli işlem", 10.0, 18.0, MAVI, 0),
        ("VIOP — normal seans (emir toplama 09:15)", 9.5, 18.25, LACIVERT, 0),
        ("VIOP — akşam seansı", 19.0, 23.0, LACIVERT, 0),
        ("TCMB gösterge kur anı (~15:30)", 15.5, 15.6, TURUNCU, 0),
    ]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
                        subplot_titles=("(a) ABD yaz saati dönemi — TSİ = NY + 7 (mart ortası – kasım başı)",
                                        "(b) ABD kış saati dönemi — TSİ = NY + 8 (kasım başı – mart ortası)"))
    for r, kay in ((1, 0), (2, 1)):
        for j, (ad, t0, t1, renk, kayar) in enumerate(seritler):
            y = len(seritler) - j
            a0, a1 = t0 + kay * kayar, t1 + kay * kayar
            if a1 - a0 < 0.4:                       # anlık olay: dikey işaret
                fig.add_shape(type="line", x0=a0, x1=a0, y0=y - 0.42, y1=y + 0.42,
                              line=dict(color=renk, width=3.5), row=r, col=1)
            else:
                fig.add_shape(type="rect", x0=a0, x1=a1, y0=y - 0.34, y1=y + 0.34,
                              fillcolor=rgba(renk, 0.42), line=dict(color=renk, width=1.0), row=r, col=1)
            not_(fig, 24.25, y, ad, renk=renk, ok=False, boyut=9.5, xanchor="left", row=r, col=1)
            sa = f"{int(a0):02d}:{int(round((a0 % 1) * 60)):02d}"
            sb = f"{int(a1):02d}:{int(round((a1 % 1) * 60)):02d}"
            not_(fig, a0 - 0.15, y, sa if a1 - a0 < 0.4 else f"{sa}–{sb}", renk=renk, ok=False, boyut=8.5,
                 xanchor="right", row=r, col=1)
        for vy, t in ((len(seritler) + 0.9, None),):
            pass
        fig.update_yaxes(range=[-4.0 if r == 2 else 0.2, len(seritler) + 1.6], showticklabels=False,
                         showgrid=False, zeroline=False, title_text="", row=r, col=1)
        fig.update_xaxes(range=[-2.6, 30.5], tickvals=list(range(0, 25, 2)),
                         ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)], showgrid=True, row=r, col=1)
        for h in (10.0 + kay, 16.5 + kay):
            fig.add_vline(x=h, line=dict(color=MUREKKEP, width=1, dash="dot"), row=r, col=1)
    not_(fig, 10.5, len(seritler) + 0.90, "① en verimli pencere:<br>Londra KZ + BIST/VIOP açılışı",
         renk=ALTIN, ok=False, boyut=9.5, xanchor="center", row=1, col=1)
    not_(fig, 18.6, len(seritler) + 0.90, "② ikinci verimli pencere:<br>NY açılışı + NY AM SB + BIST kapanış müzayedesi",
         renk=TEAL, ok=False, boyut=9.5, xanchor="center", row=1, col=1)
    not_(fig, 0.0, -1.2, xanchor="left", yanchor="top", renk=MUREKKEP, ok=False, boyut=10, row=2, col=1,
         align="left", metin="<b>DST tuzağı:</b> Türkiye 2016'dan beri yaz saati uygulamaz (yıl boyu UTC+3); ABD ve AB uygular ve "
         "geçiş tarihleri aynı gün DEĞİLDİR.<br>Yılda iki kez, 2–3 haftalık pencerelerde Londra–NY farkı bir saat "
         "sapar. <b>Kural:</b> grafik saat dilimini <b>New York</b> olarak sabitleyin, kill zone'ları NY saatiyle "
         "düşünün;<br>TSİ dönüşümünü yalnız takviminize yazarken yapın — böylece yılda iki kez bozulan tek şey "
         "alarm saatiniz olur, analiz mantığınız değil.")
    duzen(fig, "Şekil 56 — Türkiye saatiyle bir işlem günü: kill zone'lar, BIST ve VIOP yan yana",
          "Türkiye'de tam zamanlı bir işi olan için en gerçekçi kurgu: NY AM penceresi (TSİ 16:30–18:00) ve "
          "VIOP akşam seansı (19:00–23:00). Londra penceresi mesaiyle çakışır. "
          "Kural defterine yazılacak cümle: izleyemediğiniz pencerede işlem yoktur",
          y_baslik="", x_baslik="saat (TSİ)", h=800)
    fig.update_layout(margin=dict(r=40))
    fig.update_xaxes(title_text="", row=1, col=1)
    _kaydet(fig, "56_turkiye_zaman_haritasi")


# =====================================================================================
# 57 — GERÇEK VERİ: TSİ saatlerine göre gün içi oynaklık profili (USDTRY ve BIST 100)
# =====================================================================================
def g57_gercek_tsi_profil():
    veri = []
    for tk, ad, renk in (("USDTRY=X", "USD/TRY (spot, 1 saatlik)", TEAL),
                         ("XU100.IS", "BIST 100 endeksi (1 saatlik)", MAVI)):
        df, kay = veri_yukle(tk, "1h", "730d")
        if df is None:
            continue
        d = df.copy()
        d = d[d.ts.dt.dayofweek < 5].copy()
        d["tsi"] = (d.ts + pd.Timedelta(hours=3)).dt.hour
        # BIST barları 09:30, 10:30 … damgalıdır; kova etiketleri bu ofsetle yazılır
        dk = int(d.ts.dt.minute.mode().iloc[0])
        d["bp"] = (d.h - d.l) / d.c * 1e4
        g = d.groupby("tsi")["bp"].agg(["mean", "count"]).reset_index()
        g = g[g["count"] >= 100]
        # tam bar sayısının %70'inden az bar içeren kova = kısmi (ör. BIST 17:30–18:00)
        tam = float(g["count"].median())
        g["kismi"] = g["count"] < 0.7 * tam
        veri.append(dict(tk=tk, ad=ad, renk=renk, kay=kay, g=g, dk=dk, d0=d.ts.iloc[0].date(),
                         d1=d.ts.iloc[-1].date(), n=len(d)))
    if not veri:
        RAPOR.append("Şekil 57 atlandı: saatlik veri yok")
        return
    fig = make_subplots(rows=len(veri), cols=1, shared_xaxes=True, vertical_spacing=0.13,
                        subplot_titles=[f"({chr(97+j)}) {v['ad']} — saatlik mum menzili, baz puan (H−L)/C" for j, v in enumerate(veri)])
    bantlar = [(9, 12, "Londra KZ (TSİ 09–12, yaz)", ALTIN, 0.14),
               (15.5, 15.75, "ABD 15:30 verisi", BORDO, 0.22),
               (16.5, 18, "NY açılışı + NY AM SB (16:30–18:00)", TEAL, 0.14),
               (21, 22, "NY PM SB", MOR, 0.12)]
    for j, v in enumerate(veri):
        r = j + 1
        g = v["g"]
        ort = float(g["mean"].mean())
        fig.add_trace(go.Bar(x=g["tsi"], y=g["mean"], name=v["ad"],
                             marker_color=rgba(v["renk"], 0.55), marker_line=dict(color=v["renk"], width=1.0),
                             text=[f"{x:.0f}*" if k else f"{x:.0f}" for x, k in zip(g["mean"], g["kismi"])],
                             textposition="outside",
                             textfont=dict(size=9)), row=r, col=1)
        fig.add_hline(y=ort, line=dict(color=MUREKKEP, width=1.4, dash="dash"), row=r, col=1)
        not_(fig, float(g["tsi"].min()), ort, f"gün ortalaması {ort:.0f} bp", renk=MUREKKEP, ok=False,
             boyut=9, xanchor="left", ay=-9, row=r, col=1)
        for t0, t1, ad, renk, a in bantlar:
            if t1 < g["tsi"].min() - 0.5 or t0 > g["tsi"].max() + 0.5:
                continue
            fig.add_vrect(x0=t0 - 0.5, x1=t1 - 0.5, fillcolor=rgba(renk, a), line_width=0, layer="below", row=r, col=1)
        fig.update_yaxes(title_text="ortalama menzil (bp)", row=r, col=1)
        i_max = int(g["mean"].idxmax()); i_min = int(g["mean"].idxmin())
        not_(fig, int(g.loc[i_max, "tsi"]), float(g.loc[i_max, "mean"]),
             f"en oynak saat: {int(g.loc[i_max,'tsi']):02d}:{v['dk']:02d} TSİ", renk=v["renk"], ax=78, ay=-22, row=r, col=1)
        not_(fig, int(g.loc[i_min, "tsi"]), float(g.loc[i_min, "mean"]),
             f"en sakin saat: {int(g.loc[i_min,'tsi']):02d}:{v['dk']:02d} TSİ", renk=GRI, ax=58, ay=-30, row=r, col=1)
        RAPOR.append(f"Şekil 57 (gerçek): {v['ad']} — {v['kay']}, {v['d0']}–{v['d1']}, {v['n']} saatlik bar (Pzt–Cum); "
                     + "; ".join(f"{int(t):02d}:{v['dk']:02d}={m:.1f}bp" + ("*kısmi" if k else "")
                                  for t, m, k in zip(g['tsi'], g['mean'], g['kismi'])))
        OZET[f"tsi_profil_{v['tk'].replace('=', '_').replace('.', '_')}"] = dict(
            d0=str(v["d0"]), d1=str(v["d1"]), bar=int(v["n"]), bar_dakika=v["dk"],
            saat={f"{int(t):02d}:{v['dk']:02d}": round(float(m), 1) for t, m in zip(g["tsi"], g["mean"])},
            kismi_kova=[f"{int(t):02d}:{v['dk']:02d}" for t, k in zip(g["tsi"], g["kismi"]) if k])
    for r, v in enumerate(veri, start=1):
        etk = ":%02d" % v["dk"] if v["dk"] else ""
        fig.update_xaxes(tickvals=list(range(0, 24)), ticktext=[f"{h:02d}{etk}" for h in range(24)],
                         tickfont=dict(size=9), row=r, col=1)
    fig.update_xaxes(title_text="saat (TSİ) — barın başlangıç saati", row=len(veri), col=1)
    for t0, t1, ad, renk, a in bantlar:
        lejant(fig, ad, renk, a=a + 0.2)
    duzen(fig, "Şekil 57 — Gerçek veri: TSİ saatlerine göre gün içi oynaklık profili (USD/TRY ve BIST 100)",
          "Ölçüm: her saatlik mumun (H−L)/C menzili baz puan cinsinden, Pzt–Cum, saat TSİ'ye çevrilmiş. "
          "BIST'in profili ICT kill zone'larından değil, kendi seans yapısından gelir (açılış müzayedesi → öğle "
          "durgunluğu → kapanışa doğru toparlanma). USD/TRY'de yerli banka akışının açıldığı saat ile "
          "ABD seansı iki ayrı tepe üretir. BIST barları 09:30 damgalı olduğu için o panelin kovaları "
          "09:30–10:30, 10:30–11:30 … biçimindedir; 17:30 kovası yalnız 17:30–18:00'i kapsayan KISMİ bardır "
          "(*) ve tam saatlik kovalarla doğrudan kıyaslanmaz",
          y_baslik="", x_baslik="", h=760)
    fig.update_layout(bargap=0.25)
    for r in range(1, len(veri) + 1):
        fig.update_yaxes(title_text="ortalama menzil (bp)",
                         range=[0, float(veri[r - 1]["g"]["mean"].max()) * 1.18], row=r, col=1)
        fig.update_xaxes(title_text="", row=r, col=1)
    fig.update_xaxes(title_text="saat (TSİ) — barın başlangıç saati", row=len(veri), col=1)
    _kaydet(fig, "57_gercek_tsi_seans_profili")


# =====================================================================================
def main():
    print("SMC EK grafik seti (29 şekil, numaralar okuma sırasına göre) →", CIKTI)
    sentetik = [g29_ipda, g30_pd_matrix, g31_cakisan_array, g32_sd_projeksiyon, g33_cbdr_sd, g34_makro,
                g35_acilis_capalari, g36_nwog, g37_ndog, g38_smt_sematik, g41_metaorder,
                g42_turtle_adim_adim, g43_turtle_matris, g44_ict2022, g45_silver_bullet_uc, g46_ote_rr,
                g47_unicorn, g48_po3, g49_mmbm, g42_org_fpfvg, g51_emir_karar_agaci, g52_senaryo_agaci,
                g53_mae_mfe, g54_r_dagilimi, g55_broker_feed, g56_turkiye_zaman]
    gercek = [g39_gercek_smt, g40_haftanin_gunu, g57_gercek_tsi_profil]
    for f in sentetik:
        f()
    if "--sentetik" not in sys.argv:
        for f in gercek:
            try:
                f()
            except Exception as exc:  # noqa
                RAPOR.append(f"{f.__name__} başarısız: {exc!r}")
    if OZET:
        # Yayına girmez: yalnız doğrulama artefaktıdır (public/ altında işlevi yok)
        (VERI / "ozet_ek.json").write_text(json.dumps(OZET, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  ✓ _veri/ozet_ek.json (gerçek/kurgu veri sayıları — MDX metniyle karşılaştırın)")
    print("\nÜretilen dosyalar (%d):" % len(URETILEN))
    for u in URETILEN:
        print("  ", u)
    if RAPOR:
        print("\nRapor / veri notları:")
        for r in RAPOR:
            print(" -", r)


if __name__ == "__main__":
    main()
