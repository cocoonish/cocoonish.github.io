#!/usr/bin/env python3
"""Harmonik Patternler dersi — EK grafik seti (Şekil 33+).

Mevcut `harmonik_grafikler.py` DEĞİŞTİRİLMEZ; yardımcıları (palet, mum üretimi,
layout, kaydet, XABCD kurgu, tarayıcı) buradan import edilir → aynı görsel dil.

Kullanım:
    python3 site/tools/ders_grafik/harmonik_grafikler_ek.py
    python3 site/tools/ders_grafik/harmonik_grafikler_ek.py --yenile   # gerçek veriyi tazele

Çıktı: site/public/arastirma/harmonik-patternler/33_*.html ... (mevcut 01–32 EZİLMEZ)

Veri: şematik seriler sabit seed ile deterministik. Gerçek veri yfinance önbelleğinden
(_veri/*.csv) okunur — pencere pinlidir. Önbellek yoksa ve indirme başarısızsa o grafik
ATLANIR ve raporlanır; sahte "gerçek veri" üretilmez.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import harmonik_grafikler as H  # noqa: E402

R = H.R
rgba = H.rgba
lvl = H.lvl
kaydet = H.kaydet
temel_layout = H.temel_layout
mum_iz = H.mum_iz
yatay = H.yatay
kutu = H.kutu
ok = H.ok
not_kutusu = H.not_kutusu
zigzag_iz = H.zigzag_iz
bacak_etiketi = H.bacak_etiketi
prz_cizgileri = H.prz_cizgileri
mumlar = H.mumlar
rsi = H.rsi
atr = H.atr
xabcd_kur = H.xabcd_kur
_prz_hesapla = H._prz_hesapla
PATTERNLER = H.PATTERNLER

RAPOR = H.RAPOR


# ------------------------------------------------------------------ ek yardımcılar
def macd(close, f=12, s=26, sig=9):
    ef = pd.Series(close).ewm(span=f, adjust=False).mean()
    es = pd.Series(close).ewm(span=s, adjust=False).mean()
    line = ef - es
    signal = line.ewm(span=sig, adjust=False).mean()
    return line.values, signal.values, (line - signal).values


def hacim_uret(df, seed=7, tbar=None, carpan=1.9):
    """Deterministik şematik hacim: bar aralığıyla orantılı + gürültü; tbar'da sıçrama."""
    rng = np.random.default_rng(seed)
    r = (df.High - df.Low).values
    v = 100 * r / (r.mean() + 1e-9) * rng.uniform(0.75, 1.25, len(df))
    if tbar is not None and 0 <= tbar < len(v):
        v[tbar] *= carpan
    return v


def sema_layout(fig, baslik, yukseklik=600, alt_baslik=None):
    """Eksensiz şematik (akış şeması / karar ağacı) için."""
    temel_layout(fig, baslik, yukseklik, alt_baslik)
    fig.update_xaxes(visible=False, showgrid=False)
    fig.update_yaxes(visible=False, showgrid=False)
    return fig


def blok(fig, x, y, w, h, metin, renk=None, alfa=0.10, font=11, kalin=1.3, row=None, col=None,
         metin_renk=None, dash=None):
    """Ortalanmış metinli kutu (akış şeması bloğu). x,y = merkez."""
    renk = renk or R["ink"]
    kw = dict(row=row, col=col) if row else {}
    fig.add_shape(type="rect", x0=x - w / 2, x1=x + w / 2, y0=y - h / 2, y1=y + h / 2,
                  fillcolor=rgba(renk, alfa), line=dict(color=renk, width=kalin, dash=dash),
                  layer="below", **kw)
    fig.add_annotation(x=x, y=y, text=metin, showarrow=False, xanchor="center", yanchor="middle",
                       align="center", font=dict(size=font, color=metin_renk or renk), **kw)


def akis_ok(fig, x0, y0, x1, y1, metin=None, renk=None, font=10, dash=None, row=None, col=None,
            ysh=0, xsh=0):
    renk = renk or R["gri"]
    kw = dict(row=row, col=col) if row else {}
    fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.4, arrowcolor=renk,
                       text="", **kw)
    if metin:
        fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=metin, showarrow=False,
                           font=dict(size=font, color=renk), bgcolor="rgba(255,255,255,0.9)",
                           xshift=xsh, yshift=ysh, **kw)


# ================================================================ 33 — oluşum aşamaları (6 panel)
def _bat_seri():
    P = PATTERNLER["Bat"]
    df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=331, nXA=18, nAB=11, nBC=9, nCD=14,
                      sonrasi=[(2, -0.05), (5, 0.12), (9, 0.06), (16, 0.38), (21, 0.30),
                               (30, 0.62), (36, 0.52), (48, 1.00)])
    return df, p


def g33_asamalar():
    df, p = _bat_seri()
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    n = len(df) - 1
    prz = _prz_hesapla(p, dict(xa=0.886, bc=2.618, abcd=1.272))
    lo, hi = min(prz.values()), max(prz.values())
    a14 = float(atr(df)[D[0]])
    giris = hi + 0.15 * a14
    stop = X[1] - 0.75 * a14
    Rr = giris - stop
    T1 = D[1] + 0.382 * (A[1] - D[1]); T2 = D[1] + 0.618 * (A[1] - D[1]); T3 = A[1]

    baslik = ("① X–A: yalnız fib çizilir", "② B = 0.50 XA: aday D bantları",
              "③ C oluştu: PRZ fiyat gelmeden hazır", "④ PRZ'ye dokunuş: kontrol listesi",
              "⑤ Tetik ve emir: giriş / SL / T1-T2-T3", "⑥ Yönetim: kısmi → BE → trailing")
    # alt alta: altı aşama okuma sırasıyla tek sütunda — her panel tam genişlik
    fig = make_subplots(rows=6, cols=1, shared_xaxes=True,
                        vertical_spacing=0.026, subplot_titles=baslik)
    kesim = [A[0] + 3, B[0] + 4, C[0] + 3, D[0] + 3, D[0] + 12, n]
    for k, kes in enumerate(kesim):
        row, col = 1 + k, 1
        d_ = df.iloc[:kes + 1]
        fig.add_trace(mum_iz(d_, etiketler={p[q][0]: q for q in "XABCD" if p[q][0] <= kes}),
                      row=row, col=col)
        pts = [p[q] for q in "XABCD" if p[q][0] <= kes]
        zigzag_iz(pts, harfler=list("XABCD")[:len(pts)], fig=fig, row=row, col=col,
                  showlegend=False)
        yatay(fig, X[1], X[0], n, "X", renk=R["gri"], dash="solid", row=row, col=col, font=9)
        if k == 0:
            for r_ in (0.382, 0.5, 0.618, 0.786, 0.886):
                yatay(fig, lvl(A[1], X[1], r_), X[0], n, f"{r_:.3f}", renk=R["fib"], w=1,
                      row=row, col=col, font=9)
            for r_ in (1.13, 1.272, 1.618):
                yatay(fig, lvl(A[1], X[1], r_), X[0], n, f"{r_:.3f}", renk=R["dn"], w=1,
                      row=row, col=col, font=9)
            not_kutusu(fig, "Karar: <b>işlem yok</b>.<br>Yapılan tek iş: XA'ya fib çekmek ve<br>"
                            "0.382–0.886 bandına alarm koymak.<br>Süre: ~10 saniye.",
                       x=0.03, y=0.04, xanchor="left", yanchor="bottom", row=row, col=col, font=9.5)
        elif k == 1:
            yatay(fig, B[1], A[0], n, "B = 0.50 XA ✓", renk=R["mavi"], w=1.6, row=row, col=col, font=9)
            for r_, t, renk in [(0.886, "Bat 0.886", R["prz"]), (1.13, "Alt Bat 1.13", R["mavi"]),
                                (1.618, "Crab 1.618", R["dn"])]:
                y = lvl(A[1], X[1], r_)
                kutu(fig, B[0], n, y - 0.22, y + 0.22, renk, alfa=0.25, metin=t, konum="top",
                     row=row, col=col, font=9)
            not_kutusu(fig, "B 0.382–0.50 → <b>aday üç</b>: Bat, Alt Bat, Crab.<br>"
                            "Elenen: Gartley (B≠0.618), Butterfly (B≠0.786).<br>"
                            "Ayrımı C değil <b>BC projeksiyonu</b> yapacak.",
                       x=0.03, y=0.04, xanchor="left", yanchor="bottom", row=row, col=col, font=9.5)
        elif k == 2:
            kutu(fig, C[0], n, lo, hi, R["prz"], metin="PRZ hazır", konum="top", row=row, col=col, font=9)
            prz_cizgileri(fig, prz, C[0], n, row=row, col=col, font=9)
            yatay(fig, hi + a14, C[0], n, "alarm: PRZ + 1 ATR", renk=R["lik"], dash="dashdot",
                  row=row, col=col, font=9)
            not_kutusu(fig, f"BC = 2.618 → <b>Bat</b> onaylandı.<br>PRZ genişliği "
                            f"{100*(hi-lo)/abs(A[1]-X[1]):.1f}% XA (≤%3 ✓).<br>"
                            "Alarm çalınca LTF'ye inilir — önce değil.",
                       x=0.03, y=0.04, xanchor="left", yanchor="bottom", row=row, col=col, font=9.5)
        elif k == 3:
            kutu(fig, C[0], n, lo, hi, R["prz"], metin="PRZ", konum="top", row=row, col=col, font=9)
            ok(fig, D[0], D[1], "D: PRZ içinde kapanış<br>+ alt fitil = T-bar adayı",
               ax=-58, ay=52, renk=R["prz"], row=row, col=col, font=9.5)
            not_kutusu(fig, "Kontrol listesi (EVET/HAYIR):<br>"
                            "<b>Yapı (sert kapı):</b> B 0.382–0.50 ✓ · BC ≥1.618 ✓ · C, A'yı aşmadı ✓<br>"
                            "→ biri HAYIR ise <b>pattern değildir</b>, alarm silinir.<br>"
                            "<b>Kalite (yumuşak):</b> PRZ ≤%3 XA ✓ · τ₂ bandda ✓<br>"
                            "→ HAYIR ise pattern durur, <b>skor ve pozisyon boyu düşer</b>.",
                       x=0.03, y=0.04, xanchor="left", yanchor="bottom", row=row, col=col, font=9.5)
        elif k == 4:
            kutu(fig, C[0], n, lo, hi, R["prz"], metin="PRZ", konum="top", row=row, col=col, font=9)
            yatay(fig, giris, D[0], n, f"giriş {giris:.2f}", renk=R["ink"], dash="solid", w=1.6,
                  row=row, col=col, font=9)
            yatay(fig, stop, X[0], n, f"SL {stop:.2f}  (1R = {Rr:.2f})", renk=R["kirmizi"], w=1.6,
                  row=row, col=col, font=9)
            for t_, ad, mult in ((T1, "T1 0.382 AD", (T1 - giris) / Rr), (T2, "T2 0.618 AD", (T2 - giris) / Rr),
                                 (T3, "T3 = A", (T3 - giris) / Rr)):
                yatay(fig, t_, D[0], n, f"{ad} {t_:.2f} → {mult:.1f}R", renk=R["yesil"],
                      row=row, col=col, font=9)
            not_kutusu(fig, "Tetik: PRZ içinde <b>kapanışlı</b> dönüş mumu.<br>"
                            "Emir: %60 teyitte, %40 Type II retestte.<br>"
                            "Boyut: risk %0.5–1 / 1R mesafesi.",
                       x=0.03, y=0.04, xanchor="left", yanchor="bottom", row=row, col=col, font=9.5)
        else:
            kutu(fig, C[0], n, lo, hi, R["prz"], metin="PRZ", konum="top", row=row, col=col, font=9)
            yatay(fig, giris, D[0], n, "giriş", renk=R["ink"], w=1.4, row=row, col=col, font=9)
            yatay(fig, stop, X[0], D[0] + 18, "ilk SL", renk=R["kirmizi"], w=1.2, row=row, col=col, font=9)
            yatay(fig, giris, D[0] + 18, n, "SL → BE", renk=R["kirmizi"], dash="dot", w=1.2,
                  row=row, col=col, font=9)
            for t_, ad in ((T1, "T1"), (T2, "T2"), (T3, "T3 = A")):
                yatay(fig, t_, D[0], n, ad, renk=R["yesil"], row=row, col=col, font=9)
            i1 = D[0] + 16; i2 = D[0] + 30; i3 = D[0] + 48
            ok(fig, i1, T1, "T1: %50 kapat<br>SL → BE", ax=-10, ay=-38, renk=R["yesil"], row=row, col=col, font=9)
            ok(fig, i2, T2, "T2: %25 kapat<br>SL → T1 altı", ax=-6, ay=-34, renk=R["yesil"], row=row, col=col, font=9)
            ok(fig, i3, T3, "T3 = A: kalan %25<br>ya da trailing", ax=-30, ay=-30, renk=R["yesil"], row=row, col=col, font=9)
            not_kutusu(fig, "Senaryo ağacı: T1'e <b>1.5× pattern süresi</b> içinde<br>"
                            "ulaşılmadıysa zaman stopu (yatay fiyat = tez yanlış).<br>"
                            "PRZ altına kapanış → çık, BE'yi bekleme.",
                       x=0.03, y=0.04, xanchor="left", yanchor="bottom", row=row, col=col, font=9.5)
        fig.update_xaxes(range=[0, n * 1.30], row=row, col=col)
    # yatay dizilişte y ekseni paylaşılıyordu; dikeyde her panele aynı ölçek verilir
    for r_ in range(1, 7):
        fig.update_yaxes(title="fiyat", range=[stop - 1.2, A[1] + 2.2], row=r_, col=1)
    temel_layout(fig, "Şekil 33 — Bir pattern'in altı aşaması: X-A → B → C → PRZ → tetik → yönetim (bullish Bat, şematik örnek)", 2230,
                 "Aynı seri altı kez; her panelde o an ekranda olan bilgi ve o bilgiyle alınan karar. "
                 "Sayılar XA = 20 birimlik kurgudan hesaplanmıştır, oranlar gerçektir.")
    kaydet(fig, "33_asamalar_alti_panel")
    RAPOR.append(f"33: Bat kurgusu X={X[1]:.2f} A={A[1]:.2f} B={B[1]:.2f} C={C[1]:.2f} D={D[1]:.2f}; "
                 f"PRZ {lo:.2f}-{hi:.2f} ({100*(hi-lo)/abs(A[1]-X[1]):.1f}% XA); giriş {giris:.2f}, SL {stop:.2f}, "
                 f"1R={Rr:.2f}; T1 {T1:.2f} ({(T1-giris)/Rr:.1f}R), T2 {T2:.2f} ({(T2-giris)/Rr:.1f}R), T3 {T3:.2f} ({(T3-giris)/Rr:.1f}R)")


# ================================================================ 34 — emir planı ızgarası
IZGARA = [
    # ad, giriş, SL, T1, T2, T3, not
    ("Gartley<br>(SL = X)", 121.4, 98.5, 151.4, 170.0, 200.0, "geniş stop"),
    ("Gartley<br>(SL = 0.886 altı)", 121.4, 109.9, 151.4, 170.0, 200.0, "dar stop"),
    ("Bat", 112.0, 98.5, 145.2, 166.2, 200.0, "stop tam geçersizlikte — yapıya yapışık"),
    ("Alternate Bat", 87.0, 71.3, 130.2, 156.8, 200.0, "X ihlali, stop 1.272"),
    ("Butterfly", 72.8, 36.7, 121.4, 151.4, 200.0, "geçersizlik 1.618 → çok uzak"),
    ("Crab /<br>Deep Crab", 38.2, -1.5, 100.0, 138.2, 200.0, "yapısal stop 2.0 XA = taban → fiilen konulamaz"),
    ("Cypher<br>(taban XC)", 127.2, 98.5, 165.4, 189.0, 227.2, "hedefler C'ye göre"),
    ("AB=CD<br>(CD = 1.0 AB)", 125.0, 109.9, 153.7, 171.4, 200.0, "X yok, stop D ötesi"),
]


def g34_emir_izgarasi():
    # alt alta: seviye haritası üstte, R:R ızgarası altta
    fig = make_subplots(rows=2, cols=1, row_heights=[0.53, 0.47], vertical_spacing=0.07,
                        subplot_titles=("Normalize seviye haritası (X = 100, A = 200, ATR = 2, tampon 0.75 ATR = 1.5)",
                                        "Aynı kurgunun R:R'si — T1 ve T2 hedefinde"))
    adlar = [r[0] for r in IZGARA]
    xs = list(range(len(IZGARA)))
    for i, (ad, g, sl, t1, t2, t3, nt) in enumerate(IZGARA):
        fig.add_trace(go.Scatter(x=[i, i], y=[sl, t3], mode="lines", line=dict(color=R["gri"], width=1),
                                 hoverinfo="skip", showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=[i - 0.28, i + 0.28], y=[sl, sl], mode="lines",
                                 line=dict(color=R["kirmizi"], width=3), hoverinfo="skip",
                                 showlegend=(i == 0), name="SL"), row=1, col=1)
        fig.add_trace(go.Scatter(x=[i - 0.32, i + 0.32], y=[g, g], mode="lines",
                                 line=dict(color=R["ink"], width=3.4), hoverinfo="skip",
                                 showlegend=(i == 0), name="giriş"), row=1, col=1)
        for t_, w_, dsh in ((t1, 2.6, None), (t2, 1.8, "dot"), (t3, 1.4, "dot")):
            fig.add_trace(go.Scatter(x=[i - 0.26, i + 0.26], y=[t_, t_], mode="lines",
                                     line=dict(color=R["yesil"], width=w_, dash=dsh), hoverinfo="skip",
                                     showlegend=False), row=1, col=1)
        et_sl = f"{sl:.1f}" + (" · yapısal, fiilen konulamaz" if ad.startswith("Crab") else "")
        fig.add_annotation(x=i, y=sl, text=et_sl, showarrow=False, yshift=-11,
                           font=dict(size=9, color=R["kirmizi"]), row=1, col=1)
        fig.add_annotation(x=i, y=g, text=f"<b>{g:.1f}</b>", showarrow=False, xshift=0, yshift=10,
                           font=dict(size=9.5, color=R["ink"]), row=1, col=1)
        fig.add_annotation(x=i, y=t1, text=f"{t1:.1f}", showarrow=False, yshift=10,
                           font=dict(size=9, color=R["yesil"]), row=1, col=1)
    for y_, t_, c_ in ((100, "X = 100", R["lik"]), (200, "A = 200", R["mavi"])):
        fig.add_hline(y=y_, line=dict(color=c_, width=1.2, dash="dash"), row=1, col=1)
        fig.add_annotation(x=-0.55, y=y_, text=t_, showarrow=False, xanchor="left", yshift=9,
                           font=dict(size=10, color=c_), row=1, col=1)
    fig.update_xaxes(tickvals=xs, ticktext=adlar, tickfont=dict(size=9.5), range=[-0.6, len(IZGARA) - 0.4],
                     row=1, col=1)
    fig.update_yaxes(title="normalize fiyat (XA = 100 birim)", range=[-14, 238], row=1, col=1)

    rr1 = [(r[3] - r[1]) / (r[1] - r[2]) for r in IZGARA]
    rr2 = [(r[4] - r[1]) / (r[1] - r[2]) for r in IZGARA]
    fig.add_trace(go.Bar(y=adlar, x=rr1, orientation="h", name="T1'de R:R",
                         marker=dict(color=R["up"]), text=[f"{v:.2f}" for v in rr1],
                         textposition="outside", textfont=dict(size=10)), row=2, col=1)
    fig.add_trace(go.Bar(y=adlar, x=rr2, orientation="h", name="T2'de R:R",
                         marker=dict(color=rgba(R["up"], 0.42)), text=[f"{v:.2f}" for v in rr2],
                         textposition="outside", textfont=dict(size=10)), row=2, col=1)
    fig.add_vline(x=2.0, line=dict(color=R["kirmizi"], width=1.4, dash="dash"), row=2, col=1)
    fig.add_annotation(xref="x2", yref="y2 domain", x=2.0, y=1.02, text="2R eşiği", showarrow=False,
                       xanchor="left", font=dict(size=10, color=R["kirmizi"]))
    fig.update_xaxes(title="R:R (kâr / risk)", range=[0, 8.6], row=2, col=1)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=9.5), row=2, col=1)

    not_kutusu(fig, "Okuma: aynı ATR ve aynı tampon kuralıyla <b>tek değişen stop mantığı</b>. Gartley'nin iki satırı aynı işlemdir — "
                    "yalnız stop yeri farklı, R:R iki katına çıkıyor. Butterfly ve Crab'de yapısal geçersizlik o kadar uzaktır ki "
                    "R:R 2'nin altına düşer; Crab'de 2.0 XA normalize kurguda fiyat tabanına iner — <b>yapısal stop kullanılamaz</b>, "
                    "para stopu T-bar ucuna konur (geçersizlik ≠ para stopu).<br>"
                    "<b>Uyarı:</b> R:R tek başına beklenen değer değildir. Dar stop R:R'yi yükseltir ve stop yeme olasılığını da yükseltir; "
                    "iki sayı birlikte okunmadan karşılaştırma yapılamaz. Bu ızgara emir <i>planı</i> karşılaştırmasıdır, kârlılık iddiası değil.",
               x=0.5, y=-0.13, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 34 — Emir planı ızgarası: sekiz kurgu, tek normalize ölçek (XA = 100 birim)", 940,
                 "Giriş = ideal D (Bat'te 112 kabul girişi), hedefler T1 = 0.382 AD, T2 = 0.618 AD, T3 = A; "
                 "Cypher'da taban XA değil XC, hedefler C'ye göre", lejant=True)
    fig.update_layout(margin=dict(b=175), barmode="group", bargap=0.28)
    kaydet(fig, "34_emir_plani_izgarasi")
    RAPOR.append("34: normalize ızgara R:R(T1) — " + " · ".join(
        f"{r[0].replace('<br>',' ')}: {v:.2f}" for r, v in zip(IZGARA, rr1)))


# ================================================================ 35 — ölçekli giriş (3 dilim)
def g35_olcekli_giris():
    prz_lo, prz_hi = 101.8, 103.2
    D_, A_, X_ = 102.28, 120.0, 100.0
    anchors = [(0, 112.0), (6, 108.2), (12, 104.6), (16, 103.0), (20, 101.6), (24, 104.6),
               (30, 102.9), (36, 105.8), (44, 109.4), (52, 113.6)]
    df = mumlar(anchors, seed=351, gurultu=0.09, fitil=0.45)
    n = len(df) - 1
    dilimler = [  # (bar, giriş, stop, ağırlık, ad, gerekçe)
        (16, 103.00, 101.50, 0.30, "Dilim 1 — %30", "LTF pattern'in D'si PRZ <b>üst</b> kenarında tamamlandı<br>stop: LTF yapının altı (çok dar)"),
        (24, 104.20, 101.00, 0.40, "Dilim 2 — %40", "LTF <b>CHoCH</b>: son LH kapanışla kırıldı<br>stop: HTF PRZ'nin altı"),
        (30, 103.10, 102.30, 0.30, "Dilim 3 — %30", "<b>Type II retest</b>: higher low<br>stop: retest dibinin altı"),
    ]
    ort = sum(g * w for _, g, _, w, _, _ in dilimler)
    risk = sum((g - s) * w for _, g, s, w, _, _ in dilimler)
    esd_stop = ort - risk
    T1 = D_ + 0.382 * (A_ - D_); T2 = D_ + 0.618 * (A_ - D_)

    fig = go.Figure(mum_iz(df))
    kutu(fig, 0, n, prz_lo, prz_hi, R["prz"], alfa=0.16,
         metin=f"HTF PRZ {prz_lo:.2f}–{prz_hi:.2f} (genişlik %{100*(prz_hi-prz_lo)/20:.0f} XA — ölçekli giriş eşiğinin (&gt;%5) üstünde, tek emirle girilmez)",
         konum="bottom", font=10)
    yatay(fig, X_, 0, n, "X (geçersizlik)", renk=R["kirmizi"], dash="dash", w=1.2, font=10)
    renkler = [R["mavi"], R["ob"], R["fvg"]]
    for k, (bar, g, s, w, ad, ger) in enumerate(dilimler):
        g = float(np.clip(g, df.Low.iloc[bar], df.High.iloc[bar]))
        fig.add_trace(go.Scatter(x=[bar], y=[g], mode="markers",
                                 marker=dict(symbol="triangle-up", size=15, color=renkler[k],
                                             line=dict(color="white", width=1)),
                                 name=ad, hovertemplate=f"{ad}: {g:.2f}<extra></extra>"))
        fig.add_shape(type="line", x0=bar - 1.4, x1=bar + 5.5, y0=s, y1=s,
                      line=dict(color=R["kirmizi"], width=2.4))
        fig.add_annotation(x=bar + 5.5, y=s, text=f"SL{k+1} {s:.2f}", showarrow=False, xanchor="left",
                           font=dict(size=9.5, color=R["kirmizi"]), xshift=3, yshift=-2 + 9 * k)
        ok(fig, bar, g, f"<b>{ad}</b> @ {g:.2f}<br>{ger}", ax=[-92, 6, 96][k], ay=[-92, -108, 78][k],
           renk=renkler[k], font=9.5)
    yatay(fig, ort, dilimler[0][0], n, f"ortalama giriş {ort:.2f}", renk=R["ink"], dash="dashdot", w=1.8, font=10.5)
    yatay(fig, esd_stop, dilimler[0][0], n, f"ağırlıklı stop eşdeğeri {esd_stop:.2f}", renk=R["kirmizi"],
          dash="dot", w=1.4, font=10)
    yatay(fig, T1, dilimler[0][0], n, f"T1 0.382 AD → {T1:.2f}   ({(T1-ort)/risk:.1f}R)", renk=R["yesil"], font=10)
    yatay(fig, T2, dilimler[0][0], n, f"T2 0.618 AD → {T2:.2f}   ({(T2-ort)/risk:.1f}R)", renk=R["yesil"], dash="dot", font=10)
    ok(fig, 20, df.Low.iloc[20], "PRZ dibine sarkma: Dilim 1'in stopu <b>tehlikede</b> ama<br>"
       "Dilim 2 açılmadan Dilim 1'in stopu <b>gevşetilmez</b> —<br>aksi hâlde ölçekleme değil, kaybedene ekleme olur",
       ax=-40, ay=92, renk=R["kirmizi"], font=9.5)
    not_kutusu(fig,
               "<b>Ağırlıklı hesap</b> (birim = XA'nın %1'i)<br>"
               f"ort. giriş = 0.30·{dilimler[0][1]:.2f} + 0.40·{dilimler[1][1]:.2f} + 0.30·{dilimler[2][1]:.2f} = <b>{ort:.2f}</b><br>"
               f"ağırlıklı risk = 0.30·{dilimler[0][1]-dilimler[0][2]:.2f} + 0.40·{dilimler[1][1]-dilimler[1][2]:.2f} "
               f"+ 0.30·{dilimler[2][1]-dilimler[2][2]:.2f} = <b>{risk:.2f}</b><br>"
               f"tek emirle girseydi: giriş {prz_hi:.2f}, stop {X_-0.5:.2f} → risk {prz_hi-(X_-0.5):.2f} (<b>{(prz_hi-(X_-0.5))/risk:.1f}×</b> daha büyük)<br>"
               f"T1'de R:R → ölçekli <b>{(T1-ort)/risk:.2f}</b>   ·   tek emirle <b>{(T1-prz_hi)/(prz_hi-(X_-0.5)):.2f}</b>",
               x=0.985, y=0.97, font=10)
    not_kutusu(fig, "<b>Kural:</b> toplam risk baştan sabittir (hesabın %0.5–1'i); dilimler o riski <i>bölüştürür</i>, çoğaltmaz. "
                    "Her dilim kendi stopunu taşır ve kendi başına kapanabilir. Dilim 2 açılmadan Dilim 1'in stopu aşağı çekilmez.<br>"
                    "<b>Bedeli:</b> ölçekli giriş, tek emirli girişten daha çok kez <i>kısmen</i> stop olur; kazandığında ortalama maliyeti daha iyidir. "
                    "Geniş PRZ'de (≥%5 XA) tercih edilir; dar PRZ'de (≤%2) tek emir daha basit ve komisyon açısından ucuzdur.",
               x=0.5, y=-0.10, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 35 — Ölçekli giriş: geniş bir PRZ'ye üç dilimde girmek (şematik örnek)", 640,
                 "%30 LTF pattern D'sinde · %40 CHoCH'ta · %30 Type II retest'te; üç ayrı stop, tek ortalama maliyet", lejant=True)
    fig.update_yaxes(title="fiyat", range=[99.2, 115.4]); fig.update_xaxes(range=[0, n * 1.30])
    fig.update_layout(margin=dict(b=140))
    kaydet(fig, "35_olcekli_giris_uc_dilim")
    RAPOR.append(f"35: dilimler %30@103.00(SL101.50) %40@104.20(SL101.00) %30@103.10(SL102.30) → ort. giriş {ort:.2f}, "
                 f"ağırlıklı risk {risk:.2f}, eşdeğer stop {esd_stop:.2f}; T1 {T1:.2f} = {(T1-ort)/risk:.2f}R, T2 {T2:.2f} = {(T2-ort)/risk:.2f}R; "
                 f"tek emirle R:R {(T1-prz_hi)/(prz_hi-(X_-0.5)):.2f}")


# ================================================================ 36 — kaybeden senaryo + karar ağacı
def g36_kaybeden_senaryo():
    prz_lo, prz_hi = 101.9, 103.1
    X_, A_ = 100.0, 120.0
    giris, D_ = 102.9, 102.28
    T1 = D_ + 0.382 * (A_ - D_)
    stop = X_ - 1.5
    anchors = [(0, 111.5), (7, 107.4), (13, 104.2), (17, 102.4), (20, 104.3), (25, 103.0),
               (31, 104.1), (38, 102.6), (44, 101.4), (50, 99.2), (56, 97.4), (62, 95.0)]
    df = mumlar(anchors, seed=361, gurultu=0.085, fitil=0.5)
    n = len(df) - 1
    # alt alta: fiyat paneli üstte, karar ağacı altta
    fig = make_subplots(rows=2, cols=1, row_heights=[0.46, 0.54], vertical_spacing=0.07,
                        subplot_titles=("Kaybeden Bat: PRZ tuttu, sonra delindi — dört çıkış noktası",
                                        "Senaryo ağacı: PRZ'de ne oldu → ne yapılır"))
    fig.add_trace(mum_iz(df), row=1, col=1)
    kutu(fig, 0, n, prz_lo, prz_hi, R["prz"], alfa=0.15, metin="PRZ (Bat 0.886)", konum="top", font=10, row=1, col=1)
    yatay(fig, X_, 0, n, "X = geçersizlik (1.0 XA)", renk=R["kirmizi"], dash="dash", w=1.3, row=1, col=1, font=10)
    yatay(fig, stop, 0, n, f"para stopu {stop:.1f} (X − 0.75 ATR)", renk=R["kirmizi"], w=1.8, row=1, col=1, font=10)
    yatay(fig, giris, 17, n, f"giriş {giris:.1f}", renk=R["ink"], w=1.5, row=1, col=1, font=10)
    yatay(fig, T1, 17, n, f"T1 {T1:.1f} — hiç görülmedi", renk=R["yesil"], dash="dot", row=1, col=1, font=10)
    olaylar = [
        (17, 102.4, "① <b>Giriş.</b> PRZ içinde kapanışlı<br>dönüş mumu — kural işledi,<br>hata burada <b>değil</b>", -75, 78, R["ink"]),
        (25, 103.0, "② <b>1. uyarı:</b> tepki T1'in<br>%50'sine bile gitmedi, yapı<br>yatay → zaman stopu sayacı<br>çalışmaya başlar", 22, -84, R["lik"]),
        (38, 102.6, "③ <b>2. uyarı:</b> ikinci deneme<br>daha zayıf (lower high),<br>PRZ üstünde <b>tutunamıyor</b><br>→ %50 kısmi çıkış", 78, -66, R["lik"]),
        (44, 101.4, "④ <b>Erken çıkış:</b> PRZ alt kenarının<br>altında <b>kapanış</b> → tez yanlış.<br>Kalanı burada kapat.<br>Stopu beklemek 3× pahalı", 96, 58, R["kirmizi"]),
        (50, 99.2, "⑤ <b>Yapı öldü:</b> X kapanışla<br>aşıldı → Bat yok.<br>Buradan sonrası Alt Bat (1.13)<br>işidir ve <b>yeni</b> karar ister", 74, 66, R["kirmizi"]),
    ]
    for x_, y_, t_, ax_, ay_, c_ in olaylar:
        ok(fig, x_, y_, t_, ax=ax_, ay=ay_, renk=c_, font=9.5, row=1, col=1)
    kutu(fig, 44, n, stop, prz_lo, R["kirmizi"], alfa=0.09, row=1, col=1)
    fig.update_yaxes(title="fiyat", range=[93.6, 113.6], row=1, col=1)
    fig.update_xaxes(range=[0, n * 1.16], row=1, col=1)

    # --- karar ağacı
    blok(fig, 5, 9.4, 9.0, 1.0, "<b>Fiyat PRZ'ye girdi</b>", R["prz"], 0.14, font=11.5, row=2, col=1)
    blok(fig, 5, 7.9, 9.4, 1.1, "PRZ içinde <b>kapanışlı</b> dönüş mumu var mı?", R["ink"], 0.05, font=10.5, row=2, col=1)
    blok(fig, 11.2, 7.9, 4.4, 0.9, "hayır →<br><b>işlem yok</b>", R["gri"], 0.10, font=9.5, row=2, col=1)
    akis_ok(fig, 5, 8.85, 5, 8.5, row=2, col=1)
    akis_ok(fig, 9.75, 7.9, 8.95, 7.9, row=2, col=1)
    blok(fig, 5, 6.3, 9.4, 1.1, "Giriş. <b>İlk 3 mum</b>: PRZ üstünde kapanıyor mu?", R["ink"], 0.05, font=10.5, row=2, col=1)
    akis_ok(fig, 5, 7.32, 5, 6.88, row=2, col=1)
    blok(fig, 11.2, 6.3, 4.4, 0.9, "hayır →<br><b>tam çık</b> (−0.3R)", R["kirmizi"], 0.10, font=9.5, row=2, col=1)
    akis_ok(fig, 9.75, 6.3, 8.95, 6.3, row=2, col=1)
    blok(fig, 5, 4.7, 9.4, 1.1, "<b>1.0× pattern süresi</b> içinde T1'in %50'sine ulaştı mı?", R["ink"], 0.05, font=10.5, row=2, col=1)
    akis_ok(fig, 5, 5.72, 5, 5.28, row=2, col=1)
    blok(fig, 11.2, 4.7, 4.4, 0.9, "hayır →<br><b>zaman stopu</b>", R["lik"], 0.12, font=9.5, row=2, col=1)
    akis_ok(fig, 9.75, 4.7, 8.95, 4.7, row=2, col=1)
    blok(fig, 5, 3.1, 9.4, 1.1, "PRZ alt kenarı altında <b>kapanış</b> oldu mu?", R["ink"], 0.05, font=10.5, row=2, col=1)
    akis_ok(fig, 5, 4.12, 5, 3.68, row=2, col=1)
    blok(fig, 11.2, 3.1, 4.4, 0.9, "evet →<br><b>erken çıkış</b>", R["kirmizi"], 0.12, font=9.5, row=2, col=1)
    akis_ok(fig, 9.75, 3.1, 8.95, 3.1, row=2, col=1)
    blok(fig, 5, 1.5, 9.4, 1.1, "T1 → %50 kapat, SL → BE<br>T2 → %25 kapat, SL → T1 altı", R["yesil"], 0.12, font=10.5, row=2, col=1)
    akis_ok(fig, 5, 2.52, 5, 2.08, "hepsi <b>evet</b>", renk=R["yesil"], row=2, col=1, xsh=-52)
    Rr = giris - stop
    kismi, erken = 102.60, 101.50
    planA = 0.5 * (kismi - giris) / Rr + 0.5 * (erken - giris) / Rr
    planB = 0.5 * (kismi - giris) / Rr + 0.5 * (stop - giris) / Rr
    planC = -1.0
    fig.add_annotation(xref="x2", yref="y2", x=5, y=0.42, xshift=10,
                       text="<b>Ders:</b> hata ①'de değil — kural işledi, işlem yine de kaybetti. Hata, ② ve ③'teki uyarıları<br>"
                            "görmezden gelip stopu beklemektir. Aynı fiyat serisi, üç farklı yönetim "
                            f"(1R = {Rr:.2f} birim):<br>"
                            f"③'te %50 @ {kismi:.1f} + ④'te kalan %50 @ {erken:.1f} → <b>{planA:+.2f}R</b>   ·   "
                            f"③'te %50, kalan stopta → <b>{planB:+.2f}R</b>   ·   hiçbir şey yapmayıp stop → <b>{planC:+.2f}R</b>",
                       showarrow=False, font=dict(size=10, color=R["ink"]), align="center",
                       bgcolor="rgba(255,255,255,0.94)", bordercolor="#d8cfba", borderwidth=1, borderpad=5)
    fig.update_xaxes(visible=False, range=[0, 14.2], row=2, col=1)
    fig.update_yaxes(visible=False, range=[-0.4, 10.2], row=2, col=1)

    not_kutusu(fig, "<b>Sık üç hata (bu kurguda):</b> (1) ②'deki yatay seyri 'sabır' sanmak — yatay fiyat, tezin <i>yanlışlanmasıdır</i>, teyidi değil. "
                    "(2) ③'te stopu aşağı çekip 'biraz daha yer vermek'. (3) ⑤'ten sonra aynı XA üzerinde üçüncü kez denemek: "
                    "kural, aynı XA'da en fazla iki deneme (Bat + Alt Bat).",
               x=0.5, y=-0.075, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 36 — Kaybeden senaryo: geçerli bir Bat neden ve nasıl kaybeder (şematik örnek)", 990,
                 "Üstte: fiyat davranışı ve beş karar anı · Altta: aynı kararların ağaç hâli — her 'hayır' bir çıkış kapısıdır")
    fig.update_layout(margin=dict(b=110))
    kaydet(fig, "36_kaybeden_senaryo_agac")
    RAPOR.append(f"36: kaybeden Bat — giriş {giris:.1f}, para stopu {stop:.1f} (1R = {Rr:.2f}), T1 {T1:.1f} hiç görülmedi; "
                 f"yönetim: %50@{kismi:.1f}+%50@{erken:.1f} = {planA:+.2f}R · %50 kısmi + stop = {planB:+.2f}R · sadece stop = {planC:+.2f}R")


# ================================================================ 37/38 — RSI BAMM
BAMM_ANC = [(0, 138), (5, 144), (11, 133), (17, 142), (21, 136), (26, 122), (31, 106), (38, 119), (45, 100),
            (58, 120), (67, 107.64), (75, 115.28), (83, 105), (88, 110.5), (96, 99), (101, 104),
            (110, 93), (115, 97), (124, 89.5), (129, 92), (138, 87.64), (154, 103)]
BAMM_IDX = dict(L1=31, X=45, A=58, B=67, C=75, D=138)


def _rsi_paneli(fig, r, n, row=2):
    fig.add_trace(go.Scatter(x=list(range(len(r))), y=r, mode="lines", name="RSI(14)",
                             line=dict(color=R["fvg"], width=1.8)), row=row, col=1)
    for y_, t_, c_, w_ in ((70, "70", R["gri"], 1), (50, "50", R["ink"], 1.6), (30, "30", R["gri"], 1)):
        yatay(fig, y_, 0, n, t_, renk=c_, dash="dot" if y_ != 50 else "dash", w=w_, row=row, col=1, font=10)
    fig.update_yaxes(title="RSI(14)", range=[0, 100], row=row, col=1)


def _dip(r, i, w=3):
    j = int(np.argmin(r[max(0, i - w):i + w + 1])) + max(0, i - w)
    return j, float(r[j])


def g37_rsi_bamm():
    df = mumlar(BAMM_ANC, seed=373, gurultu=0.075, fitil=0.45)
    r = rsi(df.Close.values)
    n = len(df) - 1
    I = BAMM_IDX
    X_, A_ = 100.0, 120.0
    B_, C_, D_ = 107.64, 115.28, 87.64
    prz_c = lvl(A_, X_, 1.618)
    bc_lvl = C_ - 3.618 * (C_ - B_)
    tetik = next(i for i in range(I["A"] - 8, I["A"] + 12) if r[i - 1] < 50 <= r[i])
    j1, v1 = _dip(r, I["L1"]); j2, v2 = _dip(r, I["X"]); j5, v5 = _dip(r, I["D"])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.64, 0.36],
                        vertical_spacing=0.055,
                        subplot_titles=("Fiyat: bullish Crab — D = 1.618 XA",
                                        "RSI(14): BAMM'ın beş aşaması"))
    fig.add_trace(mum_iz(df), row=1, col=1)
    pts = [(I["X"], X_), (I["A"], A_), (I["B"], B_), (I["C"], C_), (I["D"], D_)]
    zigzag_iz(pts, harfler=list("XABCD"), fig=fig, row=1, col=1, showlegend=False)
    kutu(fig, I["C"], n, prz_c - 0.45, prz_c + 0.45, R["prz"], alfa=0.22,
         metin=f"PRZ = {prz_c:.2f}", konum="bottom", row=1, col=1, font=10)
    yatay(fig, prz_c, I["C"], n, f"1.618 XA = {prz_c:.2f}", renk=R["prz"], dash="dot", row=1, col=1, font=10, ysh=9)
    yatay(fig, bc_lvl, I["C"], n, f"3.618 BC = {bc_lvl:.2f}", renk=R["prz"], dash="dot", row=1, col=1, font=10, ysh=-9)
    yatay(fig, lvl(A_, X_, 2.0), 0, n, "geçersizlik 2.0 XA", renk=R["kirmizi"], dash="dash", row=1, col=1, font=10)
    yatay(fig, X_, 0, n, "X", renk=R["gri"], row=1, col=1, font=10)
    fig.add_vline(x=tetik, line=dict(color=R["mavi"], width=1.6, dash="dashdot"), row=1, col=1)
    fig.add_vline(x=tetik, line=dict(color=R["mavi"], width=1.6, dash="dashdot"), row=2, col=1)
    ok(fig, tetik, float(df.Close.iloc[tetik]), "③ <b>RSI trigger bar</b><br>RSI 50'yi yukarı kesti",
       ax=-6, ay=-56, renk=R["mavi"], row=1, col=1, font=10)
    ok(fig, I["D"], D_, "⑤ fiyat <b>yeni dip</b> (X'in altında)<br>ama RSI daha yüksek dip → uyumsuzluk<br>"
                        "<b>ve</b> aynı bant Crab'in PRZ'si → A sınıfı",
       ax=64, ay=64, renk=R["prz"], row=1, col=1, font=10)
    ok(fig, I["B"], B_, "④ trigger bar sonrası <b>tepki</b>,<br>ardından son bacak = CD",
       ax=52, ay=-52, renk=R["ink"], row=1, col=1, font=10)
    fig.add_trace(go.Scatter(x=[I["X"], I["D"]], y=[X_, D_], mode="lines", name="fiyat: lower low",
                             line=dict(color=R["kirmizi"], width=1.6, dash="dash"), hoverinfo="skip"), row=1, col=1)
    fig.update_yaxes(title="fiyat", range=[82, 150], row=1, col=1)

    _rsi_paneli(fig, r, n)
    kutu(fig, j1 - 3, j2 + 4, 4, 32, R["mavi"], alfa=0.10, row=2, col=1)
    fig.add_annotation(x=(j1 + j2) / 2, y=6, text="② <b>kompleks RSI yapısı</b>: aşırı bölgede çift dip (W)",
                       showarrow=False, font=dict(size=10, color=R["mavi"]), row=2, col=1,
                       bgcolor="rgba(255,255,255,0.9)")
    for j, v, t in ((j1, v1, f"① ilk aşırı test<br>RSI {v1:.1f} (&lt;30)"), (j2, v2, f"② ikinci dip<br>RSI {v2:.1f} — <b>daha yüksek</b>")):
        ok(fig, j, v, t, ax=[-40, 40][j == j2], ay=44, renk=R["mavi"], row=2, col=1, font=9.5)
    fig.add_trace(go.Scatter(x=[j2, j5], y=[v2, v5], mode="lines", name="RSI: higher low",
                             line=dict(color=R["yesil"], width=1.8, dash="dash"), hoverinfo="skip"), row=2, col=1)
    ok(fig, j5, v5, f"⑤ RSI {v5:.1f} &gt; {v2:.1f}<br><b>uyumsuzluk</b>", ax=-52, ay=-46, renk=R["yesil"],
       row=2, col=1, font=9.5)

    not_kutusu(fig, "<b>Aşamalar Carney'nin bölüm başlıklarıyla</b> (Harmonic Trading Vol. 2, Bl. 6): aşırı limit testi → kompleks RSI yapısı → "
                    "RSI trigger bar → fiyat/RSI tepkisi → uyumsuzluk ve onay noktası. <b>Eşikler (30/50/70) ikincil kaynak ve uygulamacı "
                    "konvansiyonudur</b>; birincil metnin kesin parametreleri bu derste doğrulanamadı — bu belirsizlik saklanmıyor.<br>"
                    f"<b>Bu kurguda çakışma aritmetiktir, tesadüf değil:</b> BAMM onay noktası tetik bar yapısının (X→A) 1.618 uzantısı = {prz_c:.2f}; "
                    f"Crab'in D'si de 1.618 XA = {prz_c:.2f}; B = 0.618 ve C = 0.618 seçildiğinde 3.618 BC projeksiyonu da aynı sayıyı verir ({bc_lvl:.2f}). "
                    "Üç bağımsız görünen hesap <b>tek</b> geometriden çıkar — konfluens sayarken bu yüzden 'bağımsızlık' şartı vardır.",
               x=0.5, y=-0.085, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 37 — RSI BAMM'ın beş aşaması ve harmonik PRZ ile çakışması (şematik örnek)", 800,
                 "Üst panel fiyat, alt panel RSI(14); rozetler ①–⑤ aşamaları, dikey çizgi trigger bar'ı işaretler", lejant=True)
    fig.update_xaxes(range=[0, n * 1.16], row=2, col=1)
    fig.update_layout(margin=dict(b=150))
    kaydet(fig, "37_rsi_bamm_bes_asama")
    RAPOR.append(f"37: RSI ① {v1:.1f} (bar {j1}) · ② {v2:.1f} (bar {j2}) · trigger bar {tetik} (RSI 50 kesişimi) · "
                 f"⑤ {v5:.1f} (bar {j5}); fiyat X {X_:.2f} → D {D_:.2f} (LL), RSI {v2:.1f} → {v5:.1f} (HL) = klasik uyumsuzluk. "
                 f"BAMM 1.618 uzantısı = Crab D = 3.618 BC = {prz_c:.2f} (aritmetik özdeşlik)")


def g38_rsi_bamm_cakisma_yok():
    anc = [(0, 138), (5, 144), (11, 133), (17, 142), (21, 136), (26, 122), (31, 106), (38, 119), (45, 100),
           (58, 120), (67, 111), (75, 115.5), (83, 107), (88, 110), (96, 102.28),
           (104, 106.5), (112, 102.9), (120, 107.2), (128, 103.4), (138, 106.8), (148, 103.0)]
    df = mumlar(anc, seed=382, gurultu=0.075, fitil=0.45)
    r = rsi(df.Close.values); n = len(df) - 1
    X_, A_, B_, C_, D_ = 100.0, 120.0, 111.0, 115.5, 102.28
    prz_hi = C_ - 2.618 * (C_ - B_)
    bamm = lvl(A_, X_, 1.618)
    tetik = next(i for i in range(50, 64) if r[i - 1] < 50 <= r[i])
    j1, v1 = _dip(r, 31); j2, v2 = _dip(r, 45); j3, v3 = _dip(r, 96)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.64, 0.36], vertical_spacing=0.055,
                        subplot_titles=("Fiyat: bullish Bat — D = 0.886 XA; BAMM onay noktası çok aşağıda",
                                        "RSI(14): ① ② ③ oluştu, ⑤ (uyumsuzluk) <b>oluşmadı</b>"))
    fig.add_trace(mum_iz(df), row=1, col=1)
    zigzag_iz([(45, X_), (58, A_), (67, B_), (75, C_), (96, D_)], harfler=list("XABCD"),
              fig=fig, row=1, col=1, showlegend=False)
    kutu(fig, 75, n, min(D_, prz_hi), max(D_, prz_hi), R["prz"], alfa=0.20,
         metin=f"Harmonik PRZ {min(D_,prz_hi):.2f}–{max(D_,prz_hi):.2f} (0.886 XA + 2.618 BC)", konum="top",
         row=1, col=1, font=10)
    yatay(fig, X_, 0, n, "X — <b>süpürülmedi</b>", renk=R["gri"], row=1, col=1, font=10)
    yatay(fig, bamm, 58, n, f"RSI BAMM onay noktası (1.618 uzantısı) = {bamm:.2f}", renk=R["fvg"],
          dash="dashdot", w=2, row=1, col=1, font=10.5)
    kutu(fig, 58, n, bamm - 0.6, bamm + 0.6, R["fvg"], alfa=0.14, row=1, col=1)
    fig.add_annotation(x=n * 0.60, y=(D_ + bamm) / 2, text=f"<b>{D_ - bamm:.2f} birim = XA'nın %{100*(D_-bamm)/20:.0f}'i fark</b><br>iki sistem aynı yeri göstermiyor",
                       showarrow=False, font=dict(size=11, color=R["kirmizi"]), row=1, col=1,
                       bgcolor="rgba(255,255,255,0.92)", bordercolor=R["kirmizi"], borderwidth=1, borderpad=4)
    fig.add_annotation(xref="x domain", yref="y domain", x=0.50, y=0.50, text="<b>İŞLEM YOK</b>",
                       showarrow=False, font=dict(size=44, color="rgba(185,28,28,0.30)"), row=1, col=1)
    fig.add_vline(x=tetik, line=dict(color=R["mavi"], width=1.4, dash="dashdot"), row=1, col=1)
    fig.add_vline(x=tetik, line=dict(color=R["mavi"], width=1.4, dash="dashdot"), row=2, col=1)
    ok(fig, 96, D_, "D, X'in <b>üstünde</b> kaldı → BAMM'ın son bacağı<br>(yeni uç + uyumsuzluk) hiç oluşmadı",
       ax=70, ay=64, renk=R["kirmizi"], row=1, col=1, font=10)
    fig.update_yaxes(title="fiyat", range=[85, 150], row=1, col=1)

    _rsi_paneli(fig, r, n)
    kutu(fig, j1 - 3, j2 + 4, 4, 32, R["mavi"], alfa=0.10, row=2, col=1)
    for j, v, t in ((j1, v1, f"① {v1:.1f}"), (j2, v2, f"② {v2:.1f} — kompleks yapı ✓")):
        ok(fig, j, v, t, ax=[-34, 46][j == j2], ay=42, renk=R["mavi"], row=2, col=1, font=9.5)
    ok(fig, tetik, float(r[tetik]), "③ trigger bar ✓", ax=44, ay=-38, renk=R["mavi"], row=2, col=1, font=9.5)
    ok(fig, j3, v3, f"⑤ <b>yok</b>: fiyat yeni dip yapmadı,<br>RSI {v3:.1f} — karşılaştıracak yeni uç yok",
       ax=54, ay=44, renk=R["kirmizi"], row=2, col=1, font=9.5)

    not_kutusu(fig, "<b>Bu grafik bir yöntemin sinyal <i>vermediği</i> durumu gösteriyor.</b> Harmonik kol 'PRZ hazır, gir' diyor; RSI BAMM kolu "
                    f"'onay noktam {bamm:.2f}, oraya gelinmedi ve uyumsuzluk oluşmadı' diyor. Ders kuralı: <b>iki sistem farklı yer gösteriyorsa hiçbiri "
                    "işlem sebebi değildir</b> — beklemenin maliyeti sıfırdır.<br>"
                    "Ekleme kuralı (ders kararı): çakışma varsa konfluens skoruna +15 ve pozisyon boyunda +%50; çakışma yoksa RSI BAMM <b>tek başına</b> "
                    "işlem sebebi sayılmaz. Bu bir kanıt iddiası değil, karar disiplinidir.",
               x=0.5, y=-0.085, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 38 — Çakışma yok hâli: harmonik PRZ ile RSI BAMM onay noktası aynı yeri göstermezse işlem yoktur (şematik örnek)", 800,
                 "Aynı düzen, tek fark: pattern Bat (D = 0.886 XA, X süpürülmez) → BAMM'ın uyumsuzluk aşaması oluşamaz", lejant=True)
    fig.update_xaxes(range=[0, n * 1.16], row=2, col=1)
    fig.update_layout(margin=dict(b=140))
    kaydet(fig, "38_rsi_bamm_cakisma_yok")
    RAPOR.append(f"38: Bat PRZ {min(D_,prz_hi):.2f}–{max(D_,prz_hi):.2f}; BAMM 1.618 onay noktası {bamm:.2f}; "
                 f"fark {D_-bamm:.2f} birim = XA'nın %{100*(D_-bamm)/20:.0f}'i → işlem yok. RSI ① {v1:.1f} ② {v2:.1f} ③ trigger bar {tetik}; ⑤ oluşmadı")


# ================================================================ 39 — uyumsuzluk dereceleri
_UY_PRE = [(0, 112), (5, 117), (10, 111), (15, 118), (20, 113), (25, 119), (30, 114)]
UYUMSUZLUK = [
    dict(ad="① Klasik (regular) uyumsuzluk", anc=_UY_PRE + [(38, 106), (48, 100), (56, 106), (64, 102.5), (76, 97), (84, 103), (94, 108)],
         m=[(48, "min"), (76, "min")], renk="yesil",
         okuma="Fiyat <b>lower low</b>, RSI <b>higher low</b><br>→ satış baskısı azalıyor: <b>dönüş lehine</b>.<br>"
               "Harmonikte CD bacağında aranan budur.",
         karar="PRZ'de görülürse: teyit puanı +10"),
    dict(ad="② Gizli (hidden) uyumsuzluk", anc=_UY_PRE + [(36, 106), (42, 112.5), (50, 103), (56, 105), (62, 110.5), (70, 101), (80, 95), (90, 91)],
         m=[(42, "max"), (62, "max")], renk="kirmizi",
         okuma="Fiyat <b>lower high</b>, RSI <b>higher high</b><br>→ düşen trend <b>devam</b> sinyali:<br>"
               "<b>pattern aleyhine kanıt</b>.",
         karar="PRZ'de görülürse: <b>−15 puan</b> — girme"),
    dict(ad="③ Abartılı (exaggerated) uyumsuzluk", anc=_UY_PRE + [(38, 107), (50, 100.0), (58, 106), (66, 102), (74, 100.0), (82, 105), (94, 110)],
         m=[(50, "min"), (74, "min")], renk="lik",
         okuma="Fiyat <b>çift dip</b> (dipler eşit),<br>RSI belirgin <b>higher low</b><br>→ zayıf ama geçerli dönüş kanıtı.",
         karar="Tek başına yetmez; ikinci teyit şart"),
]


def g39_uyumsuzluk_dereceleri():
    # alt alta: her vaka için (fiyat, RSI) çifti art arda — ①②③ okuma sırası korunur.
    # Üç vaka üç ayrı seridir; ortak x ekseni yok, her panel kendi eksenini gösterir.
    fig = make_subplots(rows=6, cols=1, row_heights=[0.20, 0.13333] * 3,
                        vertical_spacing=0.026,
                        subplot_titles=tuple(t for u in UYUMSUZLUK for t in (u["ad"], "")))
    for k, U in enumerate(UYUMSUZLUK, start=1):
        rf, rr = 2 * k - 1, 2 * k          # rf: fiyat paneli, rr: RSI paneli
        df = mumlar(U["anc"], seed=392, gurultu=0.08, fitil=0.45)
        r = rsi(df.Close.values); n = len(df) - 1
        c = R[U["renk"]]
        fig.add_trace(mum_iz(df), row=rf, col=1)
        noktalar = []
        for i, tur in U["m"]:
            w = 3; sl = slice(max(0, i - w), i + w + 1)
            j = int(np.argmin(r[sl]) if tur == "min" else np.argmax(r[sl])) + max(0, i - w)
            py = float(df.Low.iloc[j] if tur == "min" else df.High.iloc[j])
            noktalar.append((j, py, float(r[j])))
        (j1, p1, r1), (j2, p2, r2) = noktalar
        fig.add_trace(go.Scatter(x=[j1, j2], y=[p1, p2], mode="lines+markers", showlegend=False,
                                 line=dict(color=c, width=2, dash="dash"),
                                 marker=dict(size=8, color="white", line=dict(color=c, width=2)),
                                 hoverinfo="skip"), row=rf, col=1)
        fig.add_annotation(x=(j1 + j2) / 2, y=(p1 + p2) / 2, text=f"fiyat {p1:.2f} → {p2:.2f}",
                           showarrow=False, font=dict(size=9.5, color=c), yshift=-14 if U["m"][0][1] == "min" else 14,
                           bgcolor="rgba(255,255,255,0.9)", row=rf, col=1)
        fig.add_trace(go.Scatter(x=list(range(len(r))), y=r, mode="lines", showlegend=False,
                                 line=dict(color=R["fvg"], width=1.6)), row=rr, col=1)
        for y_ in (30, 50, 70):
            yatay(fig, y_, 0, n, f"{y_}", renk=R["gri"],
                  dash="dash" if y_ == 50 else "dot", w=1.4 if y_ == 50 else 1, row=rr, col=1, font=9)
        fig.add_trace(go.Scatter(x=[j1, j2], y=[r1, r2], mode="lines+markers", showlegend=False,
                                 line=dict(color=c, width=2, dash="dash"),
                                 marker=dict(size=8, color="white", line=dict(color=c, width=2)),
                                 hoverinfo="skip"), row=rr, col=1)
        fig.add_annotation(x=(j1 + j2) / 2, y=(r1 + r2) / 2, text=f"RSI {r1:.1f} → {r2:.1f}", showarrow=False,
                           font=dict(size=9.5, color=c), yshift=16, bgcolor="rgba(255,255,255,0.9)", row=rr, col=1)
        fig.add_annotation(x=(j1 + j2) / 2, y=90, text=f"genişlik = {j2-j1} bar (kabul: 5–30)", showarrow=False,
                           font=dict(size=9, color=R["ink"]), row=rr, col=1)
        not_kutusu(fig, U["okuma"] + "<br><b>Karar:</b> " + U["karar"], x=0.03, y=0.04,
                   xanchor="left", yanchor="bottom", row=rf, col=1, font=9.5, renk=c)
        if k == 2:
            fig.add_shape(type="rect", xref=f"x{rf} domain", yref=f"y{rf} domain", x0=-0.005, x1=1.005, y0=-0.02, y1=1.02,
                          line=dict(color=R["kirmizi"], width=3), fillcolor="rgba(0,0,0,0)")
            fig.add_annotation(xref=f"x{rf} domain", yref=f"y{rf} domain", x=0.5, y=0.52,
                               text="<b>PRZ'DE BU VARSA GİRME</b>", showarrow=False,
                               font=dict(size=17, color="rgba(185,28,28,0.42)"))
        fig.update_yaxes(range=[0, 100], row=rr, col=1)
        fig.update_xaxes(range=[0, n], row=rf, col=1)
        fig.update_xaxes(range=[0, n], row=rr, col=1)
        fig.update_yaxes(title="fiyat", row=rf, col=1)
        fig.update_yaxes(title="RSI(14)", row=rr, col=1)
    # eksen başlıkları panel döngüsünde her fiyat/RSI paneline verildi
    not_kutusu(fig, "Teyit <b>ikili değil, üç kademelidir</b>. İşlemcilerin sık yaptığı hata, gizli uyumsuzluğu klasik sanıp ters işlem açmaktır: "
                    "ikisi de 'uyumsuzluk' diye anılır ama biri dönüşü, öteki <b>devamı</b> söyler. Ayrım tek soruyla yapılır: "
                    "<b>fiyatın uçları hangi yöne gidiyor?</b> Fiyat yeni uç yapıyorsa (LL/HH) klasik; yapmıyorsa (HL/LH) gizli.<br>"
                    "<b>Derece ölçütü (ders kararı):</b> iki uç arasındaki genişlik 5 bardan azsa gürültü, 30 bardan çoksa ilişkisiz iki olay — "
                    "her iki uçta da uyumsuzluk sayılmaz.",
               x=0.5, y=-0.075, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 39 — Uyumsuzluğun üç derecesi: klasik, gizli, abartılı (şematik örnek)", 1930,
                 "Her vakada üstte fiyat, altında RSI(14); kesikli çizgiler karşılaştırılan iki ucu birleştirir")
    fig.update_layout(margin=dict(b=118))
    kaydet(fig, "39_uyumsuzluk_dereceleri")
    RAPOR.append("39: klasik fiyat 100.00→97 / RSI 13.4→16.3 (28 bar) · gizli fiyat 112.5→110.5 / RSI 49.5→60.9 (20 bar) · "
                 "abartılı fiyat 100.00→100.00 / RSI 12.5→25.1 (24 bar) — değerler serilerden ölçülüp grafiğe yazılıyor")


# ================================================================ 40 — teyit katmanları + skor kartı
TEYIT_KALEM = [
    ("Dönüş mumu (T-bar) PRZ içinde kapanışlı", 10, 10, "var"),
    ("Klasik momentum uyumsuzluğu (RSI)", 10, 10, "var"),
    ("İkinci momentum aracı (MACD hist. işaret değiştirdi)", 5, 5, "var"),
    ("LTF CHoCH (yapı kırılımı)", 10, 10, "var"),
    ("T-bar hacmi > 1.5× son 20 bar ortalaması", 5, 5, "var"),
    ("PRZ, hacim profili HVN'i ile çakışıyor", 5, 5, "var"),
    ("Delta flip / absorpsiyon (footprint)", 10, 0, "veri yok"),
    ("Gizli uyumsuzluk (ceza)", -15, 0, "yok — iyi"),
]


def g40_teyit_katmanlari():
    anc = [(0, 106), (5, 111), (10, 105), (15, 110), (24, 100), (40, 120), (52, 110), (62, 115),
           (72, 106), (78, 111), (88, 103.0), (95, 107.5), (108, 102.28),
           (116, 103.5), (124, 106.6), (136, 109.05)]
    df = mumlar(anc, seed=402, gurultu=0.08, fitil=0.45)
    r = rsi(df.Close.values); _, _, hist = macd(df.Close.values)
    n = len(df) - 1
    X_, A_, B_, C_, D_ = 100.0, 120.0, 110.0, 115.0, 102.28
    iD = 108
    hac = hacim_uret(df, seed=405, tbar=iD, carpan=2.85)
    ort20 = float(np.mean(hac[iD - 20:iD]))
    prz_hi = C_ - 2.618 * (C_ - B_)
    lo, hi = min(D_, prz_hi), max(D_, prz_hi)
    j1, v1 = _dip(r, 88); j2, v2 = _dip(r, iD)
    hflip = next(i for i in range(iD, n) if hist[i - 1] < 0 <= hist[i])
    lh_i = int(df.High.iloc[95:104].idxmax()); lh = float(df.High.iloc[lh_i])
    choch = next((i for i in range(iD, n) if df.Close.iloc[i] > lh), None)

    # alt alta: fiyat / RSI / MACD / hacim yığını (ortak x) ve en altta skor kartı
    fig = make_subplots(rows=5, cols=1,
                        row_heights=[0.26, 0.15, 0.135, 0.145, 0.31], vertical_spacing=0.032,
                        subplot_titles=("Fiyat: bullish Bat, PRZ'de teyit katmanları",
                                        "RSI(14) — klasik uyumsuzluk", "MACD histogram — işaret değişimi",
                                        "Hacim (şematik)", "Teyit skor kartı (§ teyit tablosu)"))
    # ilk dört panel aynı seriyi gösterir: x eksenleri eşleşir, etiket yalnız en altta
    for r_ in (1, 2, 3):
        fig.update_xaxes(matches="x4", showticklabels=False, row=r_, col=1)
    # skor kartının uzun kategori etiketleri panelin İÇİNE yazılır: barlar x>0'da,
    # x<0 bandı boş. Panele soldan girinti verilse x-domain sol kenarı ikiye çıkar
    # ve ev stili figürü 'çok sütunlu' sayıp yatay kaydırma açardı.
    fig.update_yaxes(ticklabelposition="inside", row=5, col=1)
    fig.add_trace(mum_iz(df), row=1, col=1)
    zigzag_iz([(24, X_), (40, A_), (52, B_), (62, C_), (iD, D_)], harfler=list("XABCD"), fig=fig, row=1, col=1, showlegend=False)
    kutu(fig, 62, n, lo, hi, R["prz"], alfa=0.18, metin=f"PRZ {lo:.2f}–{hi:.2f}", konum="top", row=1, col=1, font=10)
    kutu(fig, 0, n, lo - 0.55, hi + 0.35, R["ob"], alfa=0.07, row=1, col=1)
    fig.add_annotation(x=2, y=hi + 0.35, text="HVN (hacim profili yüksek düğüm) — PRZ ile çakışıyor: +5",
                       showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=9.5, color=R["ob"]), row=1, col=1)
    ok(fig, iD, D_, "<b>T-bar</b>: PRZ içinde kapanış,<br>uzun alt fitil → +10", ax=-72, ay=58, renk=R["prz"], row=1, col=1, font=9.5)
    yatay(fig, lh, lh_i, n, "son LH", renk=R["up"], dash="dot", row=1, col=1, font=9.5)
    if choch:
        ok(fig, choch, float(df.Close.iloc[choch]), "<b>CHoCH</b>: LH kapanışla kırıldı → +10",
           ax=-8, ay=-46, renk=R["up"], row=1, col=1, font=9.5)   # tam genişlikte sağa taşıyordu
    fig.update_yaxes(title="fiyat", row=1, col=1)

    fig.add_trace(go.Scatter(x=list(range(len(r))), y=r, mode="lines", showlegend=False,
                             line=dict(color=R["fvg"], width=1.6)), row=2, col=1)
    for y_ in (30, 50, 70):
        yatay(fig, y_, 0, n, f"{y_}", renk=R["gri"], dash="dot", w=1, row=2, col=1, font=9)
    fig.add_trace(go.Scatter(x=[j1, j2], y=[v1, v2], mode="lines+markers", showlegend=False,
                             line=dict(color=R["yesil"], width=2, dash="dash"),
                             marker=dict(size=7, color="white", line=dict(color=R["yesil"], width=2)),
                             hoverinfo="skip"), row=2, col=1)
    fig.add_annotation(x=(j1 + j2) / 2, y=(v1 + v2) / 2, text=f"RSI {v1:.1f} → {v2:.1f} (HL) · genişlik {j2-j1} bar",
                       showarrow=False, yshift=-16, font=dict(size=9.5, color=R["yesil"]),
                       bgcolor="rgba(255,255,255,0.9)", row=2, col=1)
    fig.update_yaxes(title="RSI", range=[0, 100], row=2, col=1)

    fig.add_trace(go.Bar(x=list(range(len(hist))), y=hist, showlegend=False,
                         marker=dict(color=[R["up"] if v >= 0 else R["dn"] for v in hist])), row=3, col=1)
    fig.add_hline(y=0, line=dict(color=R["ink"], width=1), row=3, col=1)
    ok(fig, hflip, float(hist[hflip]), f"histogram işaret değiştirdi (bar {hflip})<br>küçülmesi yetmez, <b>işaret</b> değişmeli → +5",
       ax=76, ay=-40, renk=R["up"], row=3, col=1, font=9)
    fig.update_yaxes(title="MACD hist.", row=3, col=1)

    fig.add_trace(go.Bar(x=list(range(len(hac))), y=hac, showlegend=False,
                         marker=dict(color=[R["lik"] if i == iD else rgba(R["gri"], 0.75) for i in range(len(hac))])), row=4, col=1)
    fig.add_hline(y=1.5 * ort20, line=dict(color=R["kirmizi"], width=1.2, dash="dash"), row=4, col=1)
    fig.add_annotation(x=2, y=1.5 * ort20, text="1.5 × son 20 bar ortalaması", showarrow=False, xanchor="left",
                       yshift=8, font=dict(size=9, color=R["kirmizi"]), row=4, col=1)
    hac_orani = hac[iD] / ort20
    assert hac_orani > 1.5, f"T-bar hacmi eşiğin altında ({hac_orani:.2f}×) — skor kartı ile tutarsız"
    ok(fig, iD, float(hac[iD]), f"T-bar hacmi = {hac_orani:.2f}× ortalama (&gt;1.5 ✓) → +5", ax=-70, ay=-34,
       renk=R["lik"], row=4, col=1, font=9)
    fig.update_yaxes(title="hacim", row=4, col=1)
    fig.update_xaxes(title="bar", range=[0, n], row=4, col=1)

    adlar = [k[0] for k in TEYIT_KALEM][::-1]
    alinan = [k[2] for k in TEYIT_KALEM][::-1]
    tavan = [k[1] for k in TEYIT_KALEM][::-1]
    fig.add_trace(go.Bar(y=adlar, x=[max(t, 0) for t in tavan], orientation="h", showlegend=False,
                         marker=dict(color=rgba(R["gri"], 0.22)), hoverinfo="skip"), row=5, col=1)
    fig.add_trace(go.Bar(y=adlar, x=alinan, orientation="h", showlegend=False,
                         marker=dict(color=[R["up"] if a > 0 else R["gri"] for a in alinan]),
                         text=[f"{a:+d}" if a else k[3] for a, k in zip(alinan, TEYIT_KALEM[::-1])],
                         textposition="outside", textfont=dict(size=9.5)), row=5, col=1)
    toplam = sum(k[2] for k in TEYIT_KALEM)
    mumkun = sum(k[1] for k in TEYIT_KALEM if k[1] > 0)
    # iki kutu skor kartının dışındaydı (yan sütunun üstü/altı). Dikey yerleşimde
    # kartın ÜSTÜNDE açılan şeride yan yana alınır: panel içindeki barları örtmez,
    # figür alt kenarından da taşmaz.
    d0, d1 = fig.layout.yaxis5.domain
    kart_ust = d0 + 0.74 * (d1 - d0)
    fig.update_yaxes(domain=[d0, kart_ust], row=5, col=1)
    for _a in fig.layout.annotations:          # panel başlığı da kartla birlikte iner
        if _a.text == "Teyit skor kartı (§ teyit tablosu)":
            _a.y = kart_ust + 0.006
    fig.add_annotation(xref="paper", yref="paper", x=0.0, y=d1, xanchor="left", yanchor="top",
                       text=f"<b>Ham teyit skoru: {toplam} / {mumkun}</b><br>"
                            f"Konfluens skorunda 'Teyit' kategorisi 20 tavanlıdır →<br>"
                            f"normalize: min(20, {toplam}) = <b>20 / 20</b>",
                       showarrow=False, font=dict(size=10.5, color=R["ink"]), align="center",
                       bgcolor="rgba(255,255,255,0.94)", bordercolor="#d8cfba", borderwidth=1, borderpad=5)
    fig.add_annotation(xref="paper", yref="paper", x=1.0, y=d1, xanchor="right",
                       text="<b>Dürüstlük notu:</b> delta / footprint verisi merkezi olmayan spot FX'te<br>"
                            "güvenilir değildir (borsa yok, konsolide hacim yok). Vadeli (GC=F, ES),<br>"
                            "kripto borsaları ve BIST için anlamlıdır. Burada 10 puan <b>alınamaz</b>,<br>"
                            "eksik sayılır — 'veri yok' ile 'teyit yok' aynı şey değildir.",
                       showarrow=False, font=dict(size=9.5, color=R["ink"]), align="left",
                       yanchor="top", bgcolor="rgba(255,255,255,0.94)", bordercolor="#d8cfba", borderwidth=1, borderpad=5)
    fig.update_xaxes(title="puan", range=[-16, 13], row=5, col=1)
    fig.update_yaxes(tickfont=dict(size=9), row=5, col=1)

    temel_layout(fig, "Şekil 40 — Teyit katmanlarının üst üste binişi ve teyit skor kartı (şematik örnek)", 1750,
                 "Aynı PRZ dört pencereden okunuyor: mum, RSI, MACD histogramı, hacim. En fazla iki momentum aracı kuralı geçerli — "
                 "üçüncüsü kaçınılmaz olarak birinciyle çelişir")
    fig.update_layout(barmode="overlay", margin=dict(b=70))
    kaydet(fig, "40_teyit_katmanlari_skor")
    RAPOR.append(f"40: uyumsuzluk fiyat 103.00→{D_:.2f} / RSI {v1:.1f}→{v2:.1f} ({j2-j1} bar); MACD hist. işaret değişimi bar {hflip}; "
                 f"T-bar hacmi {hac_orani:.2f}× (20 bar ort.); ham teyit skoru {toplam}/{mumkun}, normalize 20/20; footprint 10 puan 'veri yok'")


# ================================================================ 41 — zaman: fib zaman bölgeleri + bacak süre oranları
def g41_zaman_bolgeleri():
    bX, bA, bB, bC, bD = 12, 27, 35, 41, 46
    X_, A_ = 100.0, 120.0
    B_ = lvl(A_, X_, 0.50); C_ = B_ + 0.50 * (A_ - B_); D_ = lvl(A_, X_, 0.886)
    anc = [(0, 104), (4, 108), (bX, X_), (bA, A_), (bB, B_), (bC, C_), (bD, D_),
           (bD + 8, D_ + 0.30 * (A_ - D_)), (bD + 18, D_ + 0.62 * (A_ - D_))]
    df = mumlar(anc, seed=411, gurultu=0.09, fitil=0.45)
    n = len(df) - 1
    tAB, tBC, tCD = bB - bA, bC - bB, bD - bC
    tau1, tau2 = tBC / tAB, tCD / tAB

    # alt alta: zaman bölgeleri üstte, τ düzlemi altta
    fig = make_subplots(rows=2, cols=1, row_heights=[0.53, 0.47], vertical_spacing=0.07,
                        subplot_titles=("Fibonacci zaman bölgeleri: X'ten itibaren 8 / 13 / 21 / 34 / 55 bar",
                                        "Bacak süre oranları (τ) düzlemi ve kabul kutusu"))
    fig.add_trace(mum_iz(df), row=1, col=1)
    zigzag_iz([(bX, X_), (bA, A_), (bB, B_), (bC, C_), (bD, D_)], harfler=list("XABCD"),
              fig=fig, row=1, col=1, showlegend=False)
    prz = {"0.886 XA": D_, "2.618 BC": C_ - 2.618 * (C_ - B_)}
    kutu(fig, bC, n, min(prz.values()), max(prz.values()), R["prz"], alfa=0.18, metin="PRZ", konum="top",
         row=1, col=1, font=10)
    for f_ in (8, 13, 21, 34, 55):
        x_ = bX + f_
        renk = R["yesil"] if f_ == 34 else R["fib"]
        fig.add_shape(type="line", x0=x_, x1=x_, y0=96, y1=124,
                      line=dict(color=renk, width=2.0 if f_ == 34 else 1.1,
                                dash="solid" if f_ == 34 else "dot"), row=1, col=1)
        fig.add_annotation(x=x_, y=124, text=f"+{f_}", showarrow=False, yshift=8,
                           font=dict(size=10, color=renk), row=1, col=1)
    kutu(fig, bX + 13, bX + 34, 96, 97.2, R["yesil"], alfa=0.12, metin="'normal' tamamlanma bandı: 13–34 bar",
         konum="bottom", row=1, col=1, font=9.5)
    kutu(fig, bX + 34, bX + 62, 96, 97.2, R["lik"], alfa=0.12, metin="55+ → yapı yorulmuş", konum="bottom",
         row=1, col=1, font=9.5)
    ok(fig, bD, D_, f"D, X'ten <b>{bD-bX} bar</b> sonra tamamlandı<br>= tam 34 çizgisi → +2 puan (bonus)",
       ax=68, ay=54, renk=R["yesil"], row=1, col=1, font=10)
    fig.update_yaxes(title="fiyat", range=[95.5, 126], row=1, col=1)
    fig.update_xaxes(title="bar", range=[0, bX + 62], row=1, col=1)

    fig.add_shape(type="rect", x0=0.382, x1=1.0, y0=0.618, y1=1.618, fillcolor=rgba(R["yesil"], 0.13),
                  line=dict(color=R["yesil"], width=1.5), row=2, col=1)
    fig.add_annotation(x=0.69, y=1.50, text="<b>kabul kutusu</b><br>τ₁ ∈ [0.382, 1.0] · τ₂ ∈ [0.618, 1.618]",
                       showarrow=False, font=dict(size=10, color=R["yesil"]), row=2, col=1)
    fig.add_hline(y=1.0, line=dict(color=R["mavi"], width=1.2, dash="dash"), row=2, col=1)
    fig.add_annotation(x=1.92, y=1.0, text="τ₂ = 1: 'mükemmel' AB=CD (süre simetrisi)", showarrow=False,
                       xanchor="right", yshift=9, font=dict(size=9.5, color=R["mavi"]), row=2, col=1)
    ornekler = [
        (tau1, tau2, f"Üst paneldeki pattern<br>t_AB={tAB} · t_BC={tBC} · t_CD={tCD}<br>τ₁={tau1:.2f} ✓ · τ₂={tau2:.2f} ✓", R["yesil"], 62, -52),
        (13 / 8, 17 / 8, f"'Sürünen' yapı<br>t_AB=8 · t_BC=13 · t_CD=17<br>τ₁={13/8:.2f} ✗ · τ₂={17/8:.2f} ✗", R["kirmizi"], -58, -46),
        (4 / 9, 2 / 9, f"'Tek mumluk bacak'<br>t_AB=9 · t_BC=4 · t_CD=2<br>τ₂={2/9:.2f} ✗ · bacak &lt;5 bar ✗", R["lik"], 68, 44),
    ]
    for x_, y_, t_, c_, ax_, ay_ in ornekler:
        fig.add_trace(go.Scatter(x=[x_], y=[y_], mode="markers", showlegend=False,
                                 marker=dict(size=14, color=c_, symbol="diamond",
                                             line=dict(color="white", width=1.4)),
                                 hovertemplate=f"τ₁={x_:.2f}, τ₂={y_:.2f}<extra></extra>"), row=2, col=1)
        ok(fig, x_, y_, t_, ax=ax_, ay=ay_, renk=c_, row=2, col=1, font=9.5)
    fig.update_xaxes(title="τ₁ = t_BC / t_AB", range=[0, 2.0], row=2, col=1)
    fig.update_yaxes(title="τ₂ = t_CD / t_AB", range=[0, 2.4], row=2, col=1)

    not_kutusu(fig, "<b>Zaman, harmonik analizin dördüncü boyutudur ve ikincil ağırlıktadır.</b> Bu dersin konfluens skorunda toplam 15 puan: "
                    "τ₂ bandda 7 · τ₁ bandda 3 · her bacak ≥5 bar 3 · Fibonacci zaman bölgesi çakışması 2.<br>"
                    "<b>Fibonacci zaman bölgeleri bir tahmin aracı değil, filtredir</b> (ders kararı): çakışma bonus, yokluğu ceza değildir. "
                    "Kaynak durumu: aracın standart tanımı StockCharts ChartSchool'da verilir ve kaynağın kendisi 'her zaman isabetli değil' uyarısını taşır; "
                    "öngörü gücü için bağımsız kanıt yoktur — fiyat retracement seviyeleri için bulunamayan edge (Tsinaslanidis ve ark., 2022) "
                    "zaman ekseni için hiç <i>aranmamıştır</i>.<br>"
                    "<b>Bacak olgunluğu:</b> her bacak ≥ 5 bar; tek mumluk sıçramalardan kurulu 'pattern'ler taranmaz — ölçüm gürültüsüdür.",
               x=0.5, y=-0.115, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 41 — Zaman ekseni: Fibonacci zaman bölgeleri ve bacak süre oranları (şematik örnek)", 940,
                 "Üst panelde süreler bar sayısıdır; alt panelde aynı süreler oran düzlemine taşınır")
    fig.update_layout(margin=dict(b=175))
    kaydet(fig, "41_zaman_bolgeleri_oranlar")
    RAPOR.append(f"41: t_XA={bA-bX}, t_AB={tAB}, t_BC={tBC}, t_CD={tCD}; τ1={tau1:.3f}, τ2={tau2:.3f}; D, X'ten {bD-bX} bar sonra (34 fib çizgisi); "
                 f"karşı örnekler τ1=1.63/τ2=2.13 (sürünen) ve τ2=0.22 (tek mumluk bacak)")


# ================================================================ 42 — zaman stopu, iki senaryo
def g42_zaman_stopu():
    X_, A_ = 100.0, 120.0
    D_ = lvl(A_, X_, 0.886)
    giris, stop = 112.9 - 10.0, X_ - 1.5   # giriş PRZ üstü
    giris = D_ + 0.6
    Rr = giris - stop
    T1 = D_ + 0.382 * (A_ - D_); T2 = D_ + 0.618 * (A_ - D_)
    sure = 34            # X→D bar sayısı = pattern süresi
    limit = int(1.5 * sure)
    bX, bA, bB, bC, bD = 12, 27, 35, 41, 46
    ortak = [(0, 104), (4, 108), (bX, X_), (bA, A_), (bB, lvl(A_, X_, 0.50)),
             (bC, lvl(A_, X_, 0.50) + 0.50 * (A_ - lvl(A_, X_, 0.50))), (bD, D_)]

    ust = ortak + [(bD + 6, D_ + 1.4), (bD + 12, D_ + 0.6), (bD + 22, T1 + 0.3),
                   (bD + 32, T1 - 0.9), (bD + 44, T2 + 0.4), (bD + 58, T2 + 1.6)]
    alt = ortak + [(bD + 8, D_ + 1.9), (bD + 16, D_ + 0.5), (bD + 26, D_ + 2.1),
                   (bD + 38, D_ + 0.8), (bD + limit, D_ + 1.5), (bD + limit + 14, D_ + 3.4),
                   (bD + limit + 30, T1 + 1.1)]
    df_ust = mumlar(ust, seed=421, gurultu=0.085, fitil=0.45)
    df_alt = mumlar(alt, seed=422, gurultu=0.085, fitil=0.45)

    # alt alta: iki senaryo art arda (① üstte, ② altta)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.07,
                        subplot_titles=(f"① Zamanında çalışan işlem: T1, {limit} barlık pencerenin içinde",
                                        f"② Zaman stopu: {limit} bar doldu, fiyat hâlâ yatay"))
    for row, df in enumerate((df_ust, df_alt), start=1):
        n = len(df) - 1
        fig.add_trace(mum_iz(df), row=row, col=1)
        zigzag_iz([(bX, X_), (bA, A_), (bB, lvl(A_, X_, 0.50)),
                   (bC, lvl(A_, X_, 0.50) + 0.50 * (A_ - lvl(A_, X_, 0.50))), (bD, D_)],
                  harfler=list("XABCD"), fig=fig, row=row, col=1, showlegend=False)
        kutu(fig, bC, n, D_ - 0.5, D_ + 1.1, R["prz"], alfa=0.16, metin="PRZ", konum="top", row=row, col=1, font=10)
        yatay(fig, giris, bD, n, f"giriş {giris:.2f}", renk=R["ink"], w=1.5, row=row, col=1, font=9.5)
        yatay(fig, stop, bX, n, f"SL {stop:.2f} (1R = {Rr:.2f})", renk=R["kirmizi"], w=1.5, row=row, col=1, font=9.5)
        yatay(fig, T1, bD, n, f"T1 {T1:.2f} ({(T1-giris)/Rr:.1f}R)", renk=R["yesil"], row=row, col=1, font=9.5)
        yatay(fig, T2, bD, n, f"T2 {T2:.2f} ({(T2-giris)/Rr:.1f}R)", renk=R["yesil"], dash="dot", row=row, col=1, font=9.5)
        yatay(fig, giris + 0.5 * (T1 - giris), bD, bD + limit, "T1'in %50'si (asimetrik uzatma eşiği)",
              renk=R["lik"], dash="dot", w=1, row=row, col=1, font=9)
        for k, (b_, t_, c_) in enumerate(((bD + sure, f"1.0× süre (+{sure} bar)", R["lik"]),
                                          (bD + limit, f"1.5× süre (+{limit} bar) = zaman stopu", R["kirmizi"]))):
            fig.add_shape(type="line", x0=b_, x1=b_, y0=97, y1=118, row=row, col=1,
                          line=dict(color=c_, width=1.8, dash="dashdot"))
            fig.add_annotation(x=b_, y=118, text=t_, showarrow=False, yshift=10 + 12 * k, xanchor="center",
                               font=dict(size=9, color=c_), row=row, col=1)
        kutu(fig, bD, bD + limit, 97, 97.9, R["mavi"], alfa=0.10,
             metin="pattern süresi × 1.5 = izin verilen pencere", konum="bottom", row=row, col=1, font=9)
        if row == 1:
            t1_bar = next(i for i in range(bD, n) if df.High.iloc[i] >= T1)
            ok(fig, t1_bar, T1, f"T1'e {t1_bar-bD}. barda ulaştı<br>(<b>{limit} barlık pencerenin içinde</b>)<br>"
                                "→ %50 kapat, SL → BE, sayaç sıfırlanır",
               ax=-16, ay=-64, renk=R["yesil"], row=row, col=1, font=9.5)
            not_kutusu(fig, "<b>Tez:</b> 'PRZ'de arz/talep dengesi değişti.'<br>Denge gerçekten değiştiyse etkisi <b>hızlı</b> görünür.<br>"
                            "Bu panelde tez doğrulandı: hareket zamanında geldi.",
                       x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=row, col=1, font=9.5)
        else:
            cikis = float(df.Close.iloc[bD + limit])
            ok(fig, bD + limit, cikis, f"<b>Zaman stopu:</b> {limit} bar doldu, fiyat {cikis:.2f}<br>"
                                       f"= giriş {giris:.2f} · sonuç <b>{(cikis-giris)/Rr:+.2f}R</b><br>"
                                       "Stop yenmedi — ama tez de doğrulanmadı",
               ax=-24, ay=-72, renk=R["kirmizi"], row=row, col=1, font=9.5)
            son = float(df.Close.iloc[n])
            kutu(fig, bD + limit, n, D_ + 0.5, son + 0.6, R["gri"], alfa=0.10, row=row, col=1)
            ok(fig, n - 4, son, f"<b>Dürüstlük notu:</b> kapattıktan sonra fiyat<br>yine de yükseldi ({son:.2f} = "
                                f"{(son-giris)/Rr:+.2f}R kaçtı).<br>Zaman stopu bazen kâr keser; koruduğu şey<br>"
                                "<b>ortalama</b> beklenen değerdir, tek işlem değil.",
               ax=-30, ay=66, renk=R["gri"], row=row, col=1, font=9.5)
            not_kutusu(fig, "<b>Asimetrik zaman stopu (ders kararı):</b><br>kâr yönünde hareket varsa (T1'in %50'sine ulaşıldı)<br>"
                            "süre 2× uzatılır; hiç hareket yoksa 1.0×'te kapatılır.<br>Bu panelde T1'in %50'sine hiç ulaşılmadı.",
                       x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=row, col=1, font=9.5)
        # seviye etiketleri çizginin sağına yazılıyor: tam genişlikte panelde
        # kırpılmasınlar diye pencereye sağdan pay eklenir
        fig.update_xaxes(range=[0, n * 1.20], row=row, col=1)
    # yatay dizilişte y paylaşılıyordu; dikeyde iki panele de aynı ölçek verilir
    for r_ in (1, 2):
        fig.update_yaxes(title="fiyat", range=[96.5, 121], row=r_, col=1)
    not_kutusu(fig, "<b>Neden zaman stopu?</b> Harmonik işlemin tezi bir <i>fiyat</i> iddiası değil, bir <i>denge</i> iddiasıdır: PRZ'de arz/talep değişti. "
                    "Değiştiyse etkisi hızlı görünür. Yatay kalan fiyat tezi <b>yalanlar</b>; stop yenmemiş olması tezin doğru olduğu anlamına gelmez — "
                    "yalnız henüz yanlışlanma <i>maliyetinin</i> ödenmediği anlamına gelir. Sermaye o pozisyonda kilitliyken başka setup'lara giremezsiniz; "
                    "zaman stopunun asıl koruduğu şey para değil, <b>fırsat maliyetidir</b>.",
               x=0.5, y=-0.085, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 42 — Zaman stopu: aynı kural, iki sonuç (şematik örnek)", 980,
                 f"Pattern süresi = X→D {sure} bar; izin verilen pencere 1.5× = {limit} bar")
    fig.update_layout(margin=dict(b=120))
    kaydet(fig, "42_zaman_stopu_iki_senaryo")
    RAPOR.append(f"42: pattern süresi X→D = {sure} bar, zaman stopu 1.5× = {limit} bar; giriş {giris:.2f}, SL {stop:.2f} (1R={Rr:.2f}), "
                 f"T1 {T1:.2f} = {(T1-giris)/Rr:.1f}R, T2 {T2:.2f} = {(T2-giris)/Rr:.1f}R")


# ================================================================ 43 — pattern içinde pattern (D1 / H4 / M15)
def g43_ic_ice_pattern():
    # --- D1: bullish Crab
    X1, A1 = 100.0, 120.0
    B1 = lvl(A1, X1, 0.618); C1 = B1 + 0.618 * (A1 - B1); D1 = lvl(A1, X1, 1.618)
    prz_lo, prz_hi = D1 - 0.45, D1 + 0.45
    d1_anc = [(0, 106), (5, 111), (14, X1), (30, A1), (40, B1), (48, C1),
              (58, 104), (63, 108), (72, 96), (77, 99.5), (86, 90), (91, 92.5), (100, D1),
              (108, D1 + 2.4), (118, D1 + 6.0)]
    dfd = mumlar(d1_anc, seed=431, gurultu=0.075, fitil=0.45)
    # --- H4: PRZ içinde bullish Gartley
    X2, A2 = 86.5, 91.5
    B2 = lvl(A2, X2, 0.618); C2 = B2 + 0.618 * (A2 - B2); D2 = lvl(A2, X2, 0.786)
    h4_anc = [(0, 94.2), (6, 91.0), (14, X2), (26, A2), (34, B2), (42, C2), (54, D2),
              (62, D2 + 0.9), (74, D2 + 2.1)]
    dfh = mumlar(h4_anc, seed=432, gurultu=0.08, fitil=0.45)
    # --- M15: sweep + CHoCH + giriş
    m15_anc = [(0, 88.9), (6, 88.35), (12, 88.62), (20, 87.90), (26, 88.25), (34, 87.42),
               (38, 88.05), (46, 87.75), (56, 88.55), (66, 88.30), (78, 89.15)]
    dfm = mumlar(m15_anc, seed=433, gurultu=0.07, fitil=0.55)

    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.075,
                        subplot_titles=("① D1 (HTF): bullish Crab — PRZ hazır, <b>işlem yok</b>, yalnız alarm",
                                        "② H4 (işlem TF): aynı PRZ'nin <b>içinde</b> bir bullish Gartley tamamlanıyor",
                                        "③ M15 (tetik TF): H4 D'sinin altındaki likidite süpürüldü → CHoCH → giriş"))
    n1 = len(dfd) - 1
    fig.add_trace(mum_iz(dfd), row=1, col=1)
    zigzag_iz([(14, X1), (30, A1), (40, B1), (48, C1), (100, D1)], harfler=list("XABCD"),
              fig=fig, row=1, col=1, showlegend=False)
    kutu(fig, 48, n1, prz_lo, prz_hi, R["prz"], alfa=0.22,
         metin=f"D1 PRZ {prz_lo:.2f}–{prz_hi:.2f} (1.618 XA = {D1:.2f})", konum="top", row=1, col=1, font=10)
    yatay(fig, lvl(A1, X1, 2.0), 0, n1, "geçersizlik 2.0 XA", renk=R["kirmizi"], dash="dash", row=1, col=1, font=9.5)
    not_kutusu(fig, "Karar: <b>hiçbir şey yapma.</b> D1'de tek iş PRZ'yi çizip alarm koymak.<br>"
                    "Crab bir <i>extension</i> pattern'idir → varsayılan hedef T1, hikâye 'aşırı tepki'.",
               x=0.03, y=0.06, xanchor="left", yanchor="bottom", row=1, col=1, font=9.5)
    fig.update_yaxes(title="fiyat", range=[85, 124], row=1, col=1)
    fig.update_xaxes(range=[0, n1 * 1.14], row=1, col=1)

    n2 = len(dfh) - 1
    fig.add_trace(mum_iz(dfh), row=2, col=1)
    zigzag_iz([(14, X2), (26, A2), (34, B2), (42, C2), (54, D2)], harfler=list("XABCD"),
              fig=fig, row=2, col=1, showlegend=False)
    kutu(fig, 0, n2, prz_lo, prz_hi, R["prz"], alfa=0.20, metin="D1 PRZ (üstteki panelin turuncu bandı)",
         konum="top", row=2, col=1, font=10)
    yatay(fig, D2, 42, n2, f"H4 Gartley D = 0.786 XA = {D2:.2f}", renk=R["mavi"], w=1.6, row=2, col=1, font=10)
    ok(fig, 54, D2, f"D2 = {D2:.2f} → D1 PRZ'sinin <b>içinde</b> ({prz_lo:.2f}–{prz_hi:.2f})<br>"
                    "iki katman <b>aynı yönü</b> gösteriyor → Dilim 1 (%30) burada",
       ax=86, ay=52, renk=R["mavi"], row=2, col=1, font=9.5)
    not_kutusu(fig, "<b>Kural:</b> LTF'de pattern <i>aranmaz</i>; HTF PRZ'sinin içinde <i>varsa</i> kullanılır.<br>"
                    "Serbest LTF taraması kombinasyon patlaması yüzünden <b>her zaman</b> bir şey bulur.<br>"
                    "İki katman ters yön gösteriyorsa bu 'iki kat teyit' değil, <b>çelişkidir</b> → işlem yok.",
               x=0.03, y=0.06, xanchor="left", yanchor="bottom", row=2, col=1, font=9.5)
    fig.update_yaxes(title="fiyat", range=[85.9, 95.2], row=2, col=1)
    fig.update_xaxes(range=[0, n2 * 1.14], row=2, col=1)

    n3 = len(dfm) - 1
    fig.add_trace(mum_iz(dfm), row=3, col=1)
    yatay(fig, 87.75, 0, n3, f"H4 D bölgesi ({D2:.2f}) — altında stop havuzu", renk=R["lik"], dash="dash",
          row=3, col=1, font=9.5)
    kutu(fig, 0, n3, prz_lo, prz_hi, R["prz"], alfa=0.16, row=3, col=1)
    lh3 = float(dfm.High.iloc[24:32].max()); lh_i3 = int(dfm.High.iloc[24:32].idxmax())
    yatay(fig, lh3, lh_i3, n3, "son LH", renk=R["up"], dash="dot", row=3, col=1, font=9.5)
    ok(fig, 34, float(dfm.Low.iloc[34]), "<b>sweep</b>: H4 D'sinin altına fitil,<br>kapanış geri içeride",
       ax=-58, ay=54, renk=R["lik"], row=3, col=1, font=9.5)
    kir3 = next((i for i in range(36, n3) if dfm.Close.iloc[i] > lh3), None)
    if kir3:
        ok(fig, kir3, float(dfm.Close.iloc[kir3]), "<b>CHoCH</b> → Dilim 2 (%40)", ax=44, ay=-46,
           renk=R["up"], row=3, col=1, font=9.5)
    ret_i = int(dfm.Low.iloc[kir3 + 2:kir3 + 12].idxmin()) if kir3 else 46
    fig.add_trace(go.Scatter(x=[ret_i], y=[float(dfm.Low.iloc[ret_i])], mode="markers", showlegend=False,
                             marker=dict(symbol="triangle-up", size=15, color=R["ob"],
                                         line=dict(color="white", width=1))), row=3, col=1)
    ok(fig, ret_i, float(dfm.Low.iloc[ret_i]), "<b>Type II retest</b> (higher low) → Dilim 3 (%30)",
       ax=86, ay=52, renk=R["ob"], row=3, col=1, font=9.5)
    yatay(fig, float(dfm.Low.iloc[34]) - 0.06, 34, n3, "stop: sweep fitilinin altı (PRZ altı değil)",
          renk=R["kirmizi"], w=1.6, row=3, col=1, font=9.5)
    fig.update_yaxes(title="fiyat", range=[87.15, 89.55], row=3, col=1)
    fig.update_xaxes(title="bar", range=[0, n3 * 1.14], row=3, col=1)

    not_kutusu(fig, "<b>Neden iç içe olur?</b> Her XABCD, tanımı gereği içinde bir ABCD taşır — bu bir tesadüf değil, ölçek değişiminin aritmetiğidir. "
                    "Pratik sonucu: HTF bir pattern'in CD bacağı, LTF'de kendi başına tam bir pattern olarak sayılabilir.<br>"
                    "<b>Üç katman = üç dilim:</b> Dilim 1 LTF pattern'in D'sinde (%30, çok dar stop) · Dilim 2 CHoCH'ta (%40, stop HTF PRZ altı) · "
                    "Dilim 3 Type II retest'te (%30, stop retest dibi). Toplam risk baştan sabittir; <b>ikinci dilim açılmadan birincinin stopu gevşetilmez</b>.",
               x=0.5, y=-0.055, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 43 — Pattern içinde pattern: D1 Crab PRZ'si → H4 Gartley → M15 tetik (şematik örnek)", 1000,
                 "Üç panel aynı fiyat bandına kademeli yakınlaşır; turuncu bant üç panelde de aynı D1 PRZ'sidir")
    fig.update_layout(margin=dict(b=100))
    kaydet(fig, "43_ic_ice_pattern_mtf")
    RAPOR.append(f"43: D1 Crab X={X1} A={A1} D={D1:.2f}, PRZ {prz_lo:.2f}-{prz_hi:.2f}; H4 Gartley X={X2} A={A2} D={D2:.2f} (PRZ içinde); "
                 f"M15 sweep {float(dfm.Low.iloc[34]):.2f} → CHoCH → Type II retest; stop sweep fitilinin altı")


# ================================================================ 44 — konfluens yığını + skor kartı
KUME = [  # etiket, seviye, bağımsız mı, gerekçe
    ("H4 Bat — 0.886 XA", 87.62, True, "farklı TF, farklı XA"),
    ("D1 Gartley — 0.786 XA", 87.55, True, "farklı TF, farklı XA"),
    ("1.272 BC projeksiyonu", 87.60, False, "H4 Bat ile <b>aynı XA</b>"),
    ("AB=CD ×1.00", 87.58, False, "aynı geometrinin ikinci ölçümü"),
    ("Önceki swing dibi", 87.40, True, "yapısal seviye"),
    ("Haftalık pivot S1", 87.70, True, "bağımsız hesap"),
    ("Hacim profili HVN merkezi", 87.48, True, "işlem verisi"),
    ("RSI BAMM onay noktası", 87.64, True, "momentum yapısı"),
]
SKOR = [("Yapı (45)", 40, 24, 45), ("Zaman (15)", 13, 7, 15), ("Bağlam (20)", 15, 10, 20), ("Teyit (20)", 14, 10, 20)]


def g44_konfluens():
    anc = [(0, 92.6), (7, 91.2), (14, 92.0), (24, 90.1), (30, 90.9), (40, 88.9), (46, 89.5), (58, 87.55),
           (66, 88.4), (78, 89.8)]
    df = mumlar(anc, seed=441, gurultu=0.075, fitil=0.5)
    n = len(df) - 1
    lo = min(k[1] for k in KUME); hi = max(k[1] for k in KUME)
    bagimsiz = [k for k in KUME if k[2]]

    # alt alta: konfluens yığını üstte, skor kartı altta
    fig = make_subplots(rows=2, cols=1, row_heights=[0.53, 0.47], vertical_spacing=0.07,
                        subplot_titles=("Konfluens yığını ve <b>bağımsızlık denetimi</b>",
                                        "Konfluens skor kartı — iki setup yan yana"))
    fig.add_trace(mum_iz(df), row=1, col=1)
    kutu(fig, 0, n, lo, hi, R["prz"], alfa=0.18,
         metin=f"PRZ bandı {lo:.2f}–{hi:.2f}  (genişlik {hi-lo:.2f})", konum="bottom", row=1, col=1, font=10)
    for i, (ad, y, bg, ger) in enumerate(KUME):
        c = R["up"] if bg else R["gri"]
        fig.add_shape(type="line", x0=0, x1=n, y0=y, y1=y,
                      line=dict(color=c, width=1.6 if bg else 1.1, dash="solid" if bg else "dot"), row=1, col=1)
        fig.add_annotation(x=n, y=y, text=f"{'✓' if bg else '✗'} {ad} → {y:.2f}", showarrow=False,
                           xanchor="left", xshift=6, yshift=(i - 3.5) * 12.5,
                           font=dict(size=9.5, color=c), row=1, col=1)
        fig.add_annotation(x=n, y=y, text=f"<i>{ger}</i>", showarrow=False, xanchor="left", xshift=214,
                           yshift=(i - 3.5) * 12.5, font=dict(size=8.5, color=c), row=1, col=1)
    fig.add_annotation(xref="x domain", yref="y domain", x=0.02, y=0.05, xanchor="left", yanchor="bottom",
                       text=f"Ekranda görünen sayı: <b>{len(KUME)}</b> çakışma<br>"
                            f"Bağımsız hesap sayısı: <b>{len(bagimsiz)}</b><br>"
                            "<b>Bağımsızlık şartı:</b> aynı XA'dan (aynı geometriden)<br>"
                            "türeyen iki sayı kümede <b>tek</b> sayılır. Konfluensi<br>"
                            "şişirmenin en yaygın yolu budur.",
                       showarrow=False, align="left", font=dict(size=10, color=R["ink"]),
                       bgcolor="rgba(255,255,255,0.94)", bordercolor="#d8cfba", borderwidth=1, borderpad=5,
                       row=1, col=1)
    fig.update_yaxes(title="fiyat", range=[87.0, 93.4], row=1, col=1)
    # ✓/✗ seviye etiketleri ve gerekçe sütunu x=n'in sağına yazılıyor (xshift 6 / 214);
    # eskiden yan panelin üstüne taşıyorlardı — pencereyi genişletip panel içine alıyoruz
    fig.update_xaxes(range=[0, n * 1.85], row=1, col=1)

    kats = [s[0] for s in SKOR][::-1]
    a = [s[1] for s in SKOR][::-1]; b = [s[2] for s in SKOR][::-1]; tav = [s[3] for s in SKOR][::-1]
    fig.add_trace(go.Bar(y=kats, x=tav, orientation="h", name="kategori tavanı", showlegend=False,
                         marker=dict(color=rgba(R["gri"], 0.20)), hoverinfo="skip"), row=2, col=1)
    fig.add_trace(go.Bar(y=kats, x=a, orientation="h", name=f"Setup A — {sum(s[1] for s in SKOR)} puan",
                         marker=dict(color=R["up"]), text=[f"{v}" for v in a], textposition="inside",
                         textfont=dict(size=10, color="white"), width=0.34, offset=-0.36), row=2, col=1)
    fig.add_trace(go.Bar(y=kats, x=b, orientation="h", name=f"Setup B — {sum(s[2] for s in SKOR)} puan",
                         marker=dict(color=R["lik"]), text=[f"{v}" for v in b], textposition="inside",
                         textfont=dict(size=10, color="white"), width=0.34, offset=0.02), row=2, col=1)
    fig.update_xaxes(title="puan", range=[0, 50], row=2, col=1)
    fig.add_annotation(xref="x2 domain", yref="y2 domain", x=0.99, y=0.30, xanchor="right", align="left",
                       text=f"<b>Setup A = {sum(s[1] for s in SKOR)}</b> → ≥75: <b>tam pozisyon</b> (%1 risk)<br>"
                            f"<b>Setup B = {sum(s[2] for s in SKOR)}</b> → 45–59: <b>yalnız kâğıt üstü takip</b><br><br>"
                            "Eşikler (ders kararı): ≥75 tam · 60–74 yarım (%0.5)<br>"
                            "45–59 takip · &lt;45 yok",
                       showarrow=False, font=dict(size=10, color=R["ink"]),
                       bgcolor="rgba(255,255,255,0.94)", bordercolor="#d8cfba", borderwidth=1, borderpad=5)

    not_kutusu(fig, "<b>Bu eşikler kanıt değil, tutarlılık aracıdır.</b> Amaç bir edge iddiası değil, aynı setup'a iki farklı günde aynı boyutu vermektir. "
                    "Ağırlıklar bu ders için seçilmiştir; dayanak fikri, yayınlanmış bir ABCD göstergesinin dört faktörlü puanlamasıdır "
                    "(Fibonacci hassasiyeti 45 · zaman simetrisi 25 · fiyat simetrisi 20 · bacak olgunluğu 10) — yani 'zaman ikincil ama azımsanmaz' fikri "
                    "somut bir örneğe dayanır, ağırlıkların kendisi kanıta değil.<br>"
                    "<b>Kalibrasyon ödevi:</b> skoru anlamlı kılan tek şey kendi kayıtlarınızdır. En az 50 işlem, kovalar 45–59 / 60–74 / 75+, "
                    "ölçülen büyüklük <b>beklenen R</b> (kazanma oranı değil). 75+ kovası 60–74'ten iyi değilse ağırlıklar yanlıştır — ağırlıkları düzeltin, "
                    "kovaları değil.",
               x=0.5, y=-0.095, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 44 — Konfluens: yığını saymak değil, <b>bağımsız</b> hesapları saymak (şematik örnek)", 920,
                 "Üstte sekiz çakışma, altısı bağımsız · altta 100 puanlık skor kartının iki örnek üzerinde okunuşu", lejant=True)
    fig.update_layout(margin=dict(b=155, r=340), barmode="overlay")
    kaydet(fig, "44_konfluens_yigini_skor")
    RAPOR.append(f"44: {len(KUME)} çakışma görünüyor, {len(bagimsiz)} bağımsız (1.272 BC ve AB=CD aynı XA'dan türüyor); "
                 f"PRZ bandı {lo:.2f}-{hi:.2f}; Setup A {sum(s[1] for s in SKOR)} puan (tam pozisyon), Setup B {sum(s[2] for s in SKOR)} puan (takip)")


# ================================================================ 45 — SMC birleşik model: A / B / C durumu
def g45_smc_birlesik():
    X_, A_ = 100.0, 120.0
    Dbf = lvl(A_, X_, 1.272)          # Butterfly D = 94.56
    gec_bf = lvl(A_, X_, 1.618)       # 87.64
    prz_lo, prz_hi = Dbf - 0.36, Dbf + 0.54
    sweep_lo = 91.2
    gA, slA_klasik, slA_smc = 95.60, gec_bf - 0.74, sweep_lo - 0.40
    T1 = Dbf + 0.382 * (A_ - Dbf); T2 = Dbf + 0.618 * (A_ - Dbf)
    rA_k, rA_s = gA - slA_klasik, gA - slA_smc

    ortak = [(0, 105), (5, 110), (13, X_), (30, A_), (40, lvl(A_, X_, 0.786)),
             (48, lvl(A_, X_, 0.786) + 0.618 * (A_ - lvl(A_, X_, 0.786)))]
    ancA = ortak + [(64, Dbf), (66, 96.9), (70, 99.6), (76, 97.8), (84, 102.6), (94, T1 + 0.4)]
    ancB = ortak + [(64, Dbf), (67, 96.4), (72, 95.1), (78, 96.3), (86, 92.4), (96, 89.1)]
    Dg = lvl(A_, X_, 0.786)
    ancC = [(0, 105), (5, 110), (13, X_), (30, A_), (40, lvl(A_, X_, 0.382)),
            (48, lvl(A_, X_, 0.382) + 0.618 * (A_ - lvl(A_, X_, 0.382))), (64, Dg),
            (72, Dg + 1.6), (82, Dg + 3.4), (94, Dg + 6.2)]
    dfA = mumlar(ancA, seed=471, gurultu=0.08, fitil=0.5)
    dfB = mumlar(ancB, seed=472, gurultu=0.08, fitil=0.5)
    dfC = mumlar(ancC, seed=473, gurultu=0.08, fitil=0.45)
    dfA.loc[64, "Low"] = sweep_lo; dfA.loc[64, "Close"] = prz_hi - 0.1
    dfB.loc[64, "Low"] = sweep_lo + 0.3; dfB.loc[64, "Close"] = prz_lo + 0.2

    # alt alta: üç durum art arda (A → B → C)
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.06,
                        subplot_titles=("<b>A.</b> D = sweep + OB + CHoCH → plan <b>değişir</b>",
                                        "<b>B.</b> D = sweep, ama CHoCH <b>yok</b>",
                                        "<b>C.</b> Retracement pattern, sweep yok"))
    # --- A
    nA = len(dfA) - 1
    fig.add_trace(mum_iz(dfA), row=1, col=1)
    zigzag_iz([(13, X_), (30, A_), (40, ortak[4][1]), (48, ortak[5][1]), (64, Dbf)],
              harfler=list("XABCD"), fig=fig, row=1, col=1, showlegend=False)
    kutu(fig, 48, nA, prz_lo, prz_hi, R["prz"], alfa=0.18, metin="PRZ (1.272 XA)", konum="top", row=1, col=1, font=9.5)
    yatay(fig, X_, 0, nA, "X — dış likidite havuzu", renk=R["lik"], dash="dash", row=1, col=1, font=9.5)
    ok(fig, 64, sweep_lo, "<b>sweep</b>: X'in altındaki stop'lar<br>alındı, kapanış geri PRZ içinde",
       ax=-52, ay=52, renk=R["lik"], row=1, col=1, font=9)
    lhA = float(dfA.High.iloc[52:62].max()); lhiA = int(dfA.High.iloc[52:62].idxmax())
    yatay(fig, lhA, lhiA, nA, "son LH", renk=R["up"], dash="dot", row=1, col=1, font=9)
    kirA = next((i for i in range(65, nA) if dfA.Close.iloc[i] > lhA), None)
    if kirA:
        ok(fig, kirA, float(dfA.Close.iloc[kirA]), "<b>CHoCH</b> ✓", ax=34, ay=-40, renk=R["up"], row=1, col=1, font=9)
    kutu(fig, 64, nA, sweep_lo, float(dfA.Open.iloc[64]), R["ob"], alfa=0.16, metin="OB = sweep mumu",
         konum="bottom", row=1, col=1, font=9)
    yatay(fig, slA_klasik, 13, nA, f"klasik stop (1.618 XA altı) {slA_klasik:.2f} → 1R = {rA_k:.2f}",
          renk=R["gri"], dash="dot", row=1, col=1, font=9)
    yatay(fig, slA_smc, 62, nA, f"<b>SMC stopu</b>: sweep fitilinin altı {slA_smc:.2f} → 1R = {rA_s:.2f}",
          renk=R["kirmizi"], w=1.8, row=1, col=1, font=9)
    yatay(fig, gA, 62, nA, f"giriş {gA:.2f} (OB/FVG retesti = Type II)", renk=R["ink"], w=1.4, row=1, col=1, font=9)
    yatay(fig, T1, 62, nA, f"T1 {T1:.2f}", renk=R["yesil"], row=1, col=1, font=9)
    not_kutusu(fig, f"Hedefler <b>değişmez</b>, risk küçülür:<br>"
                    f"R:R (klasik stop) = {(T1-gA)/rA_k:.2f}<br>"
                    f"R:R (sweep stopu) = <b>{(T1-gA)/rA_s:.2f}</b><br>"
                    f"risk azalması %{100*(1-rA_s/rA_k):.0f}",
               x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=1, col=1, font=9.5, renk=R["up"])
    # yatay dizilişte y paylaşılıyordu; dikeyde üç panele de aynı ölçek verilir
    for r_ in (1, 2, 3):
        fig.update_yaxes(title="fiyat", range=[86, 124], row=r_, col=1)
    fig.update_xaxes(range=[0, nA * 1.42], row=1, col=1)   # sağdaki seviye etiketleri için pay

    # --- B
    nB = len(dfB) - 1
    fig.add_trace(mum_iz(dfB), row=2, col=1)
    zigzag_iz([(13, X_), (30, A_), (40, ortak[4][1]), (48, ortak[5][1]), (64, Dbf)],
              harfler=list("XABCD"), fig=fig, row=2, col=1, showlegend=False)
    kutu(fig, 48, nB, prz_lo, prz_hi, R["prz"], alfa=0.18, metin="PRZ", konum="top", row=2, col=1, font=9.5)
    yatay(fig, X_, 0, nB, "X", renk=R["lik"], dash="dash", row=2, col=1, font=9.5)
    lhB = float(dfB.High.iloc[52:62].max()); lhiB = int(dfB.High.iloc[52:62].idxmax())
    yatay(fig, lhB, lhiB, nB, "son LH — <b>kırılmadı</b>", renk=R["kirmizi"], dash="dot", row=2, col=1, font=9)
    ok(fig, 64, sweep_lo + 0.3, "sweep ✓", ax=-40, ay=46, renk=R["lik"], row=2, col=1, font=9)
    ok(fig, 78, float(dfB.High.iloc[78]), "tepki LH'yi aşamadı → <b>CHoCH yok</b><br>yapı hâlâ düşen",
       ax=32, ay=-52, renk=R["kirmizi"], row=2, col=1, font=9)
    fig.add_annotation(xref="x2 domain", yref="y2 domain", x=0.5, y=0.42, text="<b>İŞLEM YOK</b>",
                       showarrow=False, font=dict(size=34, color="rgba(185,28,28,0.32)"))
    not_kutusu(fig, "<b>Sweep tek başına dönüş değildir.</b><br>Devam sweep'i olabilir: likidite alınır,<br>"
                    "trend aynı yönde sürer. Ayrımı yapan tek<br>şey CHoCH'tur — yapının kapanışla kırılması.",
               x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=2, col=1, font=9.5, renk=R["kirmizi"])
    fig.update_xaxes(range=[0, nB * 1.42], row=2, col=1)

    # --- C
    nC = len(dfC) - 1
    gC = Dg + 0.62; slC = lvl(A_, X_, 0.886) - 0.68
    T1c = Dg + 0.382 * (A_ - Dg)
    fig.add_trace(mum_iz(dfC), row=3, col=1)
    zigzag_iz([(13, X_), (30, A_), (40, ancC[4][1]), (48, ancC[5][1]), (64, Dg)],
              harfler=list("XABCD"), fig=fig, row=3, col=1, showlegend=False)
    kutu(fig, 48, nC, Dg - 0.35, Dg + 0.45, R["prz"], alfa=0.18, metin="PRZ (0.786 XA)", konum="top",
         row=3, col=1, font=9.5)
    yatay(fig, X_, 0, nC, "X — <b>süpürülmedi</b>", renk=R["gri"], dash="dash", row=3, col=1, font=9.5)
    fvg_lo, fvg_hi = float(dfC.High.iloc[66]), float(dfC.Low.iloc[68])
    if fvg_hi > fvg_lo:
        kutu(fig, 66, nC, fvg_lo, fvg_hi, R["fvg"], alfa=0.18, metin="FVG — girişi <b>iyileştirir</b>",
             konum="bottom", row=3, col=1, font=9)
    yatay(fig, gC, 62, nC, f"giriş {gC:.2f}", renk=R["ink"], w=1.4, row=3, col=1, font=9)
    yatay(fig, slC, 62, nC, f"stop 0.886 altı {slC:.2f} → 1R = {gC-slC:.2f}", renk=R["kirmizi"], w=1.6,
          row=3, col=1, font=9)
    yatay(fig, T1c, 62, nC, f"T1 {T1c:.2f} ({(T1c-gC)/(gC-slC):.1f}R)", renk=R["yesil"], row=3, col=1, font=9)
    not_kutusu(fig, "İç likidite / dengeleme hareketi.<br><b>Standart plan geçerlidir.</b><br>"
                    "SMC'nin tek katkısı FVG'nin giriş fiyatını<br>birkaç tik iyileştirmesidir — stop mantığı<br>değişmez.",
               x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=3, col=1, font=9.5)
    fig.update_xaxes(range=[0, nC * 1.42], row=3, col=1)

    not_kutusu(fig, "<b>Birleşik model, tek cümle:</b> harmonik <i>nerede</i> der, SMC <i>neden ve ne zaman</i> der. Harmonik PRZ olmadan SMC girişi keyfî bir "
                    "seviyededir; SMC teyidi olmadan harmonik girişi bir orandan ibarettir. İkisi çakışmadığında bekleme maliyeti sıfırdır — "
                    "birleşik modelin tek gerçek avantajı budur: <b>daha az işlem.</b><br>"
                    "<b>Uyarı (korunur):</b> 'sweep fitilinin altı = kurumsal alıcının savunduğu seviye' gerekçesi bir <i>emir akışı anlatısıdır</i>; "
                    "kurumsal emir verisi olmadan kısmen spekülatiftir. Kuralın operasyonel değeri (stop, tezin yanlışlandığı yere konur) anlatıdan bağımsız olarak geçerlidir.",
               x=0.5, y=-0.075, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 45 — SMC ile birleşik model: üç durum, üç plan (şematik örnek)", 1370,
                 "Aynı harmonik geometri, farklı SMC bağlamı → farklı stop mantığı ve farklı R:R")
    fig.update_layout(margin=dict(b=118))
    kaydet(fig, "45_smc_birlesik_model")
    RAPOR.append(f"45: A durumu — Butterfly D {Dbf:.2f}, sweep dibi {sweep_lo:.2f}, giriş {gA:.2f}; klasik stop {slA_klasik:.2f} (1R={rA_k:.2f}) → "
                 f"R:R {(T1-gA)/rA_k:.2f}; SMC stopu {slA_smc:.2f} (1R={rA_s:.2f}) → R:R {(T1-gA)/rA_s:.2f}; risk azalması %{100*(1-rA_s/rA_k):.0f}. "
                 f"C durumu — Gartley D {Dg:.2f}, giriş {gC:.2f}, stop {slC:.2f}, T1 {T1c:.2f} = {(T1c-gC)/(gC-slC):.2f}R")


# ================================================================ 46 — tarayıcı algoritması akış şeması
ADIMLAR = [
    ("ADIM 1 — PİVOTLAR", "fraktal: high[i] = max(high[i−n : i+n+1]) → tepe<br>low[i] = min(...) → dip · ardışık aynı tür pivotta ekstremi tut",
     None),
    ("ADIM 2 — ADAY BEŞLİLER", "yalnız <b>ardışık</b> 5 pivot: (X,A,B,C,D)<br>tür sırası 'L,H,L,H,L' ya da 'H,L,H,L,H' · D.i − X.i ≤ maxSpan",
     "tür sırası tutmuyor<br>ya da span aşıldı → <b>elenir</b>"),
    ("ADIM 3 — ORANLAR", "xa=|A−X| · ab=|A−B| · bc=|C−B| · cd=|C−D|<br>rB=ab/xa · rC=bc/ab · rD=|A−D|/xa · rBC=cd/bc", None),
    ("ADIM 4 — SINIFLANDIRMA", "her pattern için (B, C, D, BC) bantları<br>hepsi banttaysa aday · birden çok aday varsa ideale en yakın",
     "hiç eşleşme yok → <b>elenir</b><br>tolerans <b>sabit</b>: sapma miktarı skora girer"),
    ("ADIM 5 — PRZ", "d₁ = A ∓ rXA·xa · d₂ = C ∓ rBC·bc · d₃ = C ∓ k·ab<br>PRZ = [min, max] · genişlik = (üst−alt)/xa",
     "genişlik &gt; %8 → <b>elenmez, 'geniş' etiketlenir</b>"),
    ("ADIM 6 — ZAMAN", "τ₁ = t_BC/t_AB · τ₂ = t_CD/t_AB · her bacak ≥ 5 bar", "bant dışı → <b>skor düşer</b> (eleme değil)"),
    ("ADIM 7 — SKOR ve SİNYAL", "skor = konfluensSkoru(yapı 45 + zaman 15 + bağlam 20 + teyit 20)<br>skor ≥ 60 <b>ve</b> barConfirmed(D) → sinyal",
     "skor &lt; 60 → sinyal yok, yalnız izleme listesi"),
    ("ADIM 8 — TEYİT ve GEÇERSİZLİK", "D pivotu ancak <b>n bar sonra</b> kesinleşir → sinyal n bar <b>gecikmeli</b><br>geçersizlik: kapanış &gt; pattern'in invalidLevel'ı",
     None),
]


def g46_tarayici_akis():
    fig = go.Figure()
    y = 16.0
    for i, (bas, gov, yan) in enumerate(ADIMLAR):
        son = (i == len(ADIMLAR) - 1)
        c = R["kirmizi"] if son else R["ink"]
        blok(fig, 5.6, y, 10.4, 1.42, f"<b>{bas}</b><br><span style='font-size:9.5px'>{gov}</span>",
             c, 0.11 if son else 0.05, font=10.5, kalin=2.2 if son else 1.3)
        if yan:
            blok(fig, 15.6, y, 7.4, 1.10, f"<span style='font-size:9px'>{yan}</span>", R["gri"], 0.10, font=9)
            akis_ok(fig, 10.9, y, 11.85, y)
        if i < len(ADIMLAR) - 1:
            akis_ok(fig, 5.6, y - 0.75, 5.6, y - 1.15, renk=R["ink"])
        y -= 1.9
    blok(fig, 10.2, y - 0.15, 19.6, 1.85,
         "<b>Repaint ve geç sinyal, aynı madalyonun iki yüzüdür.</b><br>"
         "<span style='font-size:10px'>D pivotunu <i>n</i> bar beklemeden bilemezsiniz. Ya <i>n</i> bar geç sinyal alırsınız (dürüst), "
         "ya da 'şu an dip' varsayarsınız (repaint).<br>"
         "<b>Repaint = geleceği kullanmak; geç sinyal = onun faturası.</b> Backtest'te D'nin <i>keşfedildiği</i> bar ile <i>oluştuğu</i> bar farklıdır; "
         "PnL <b>keşif barının</b> fiyatından hesaplanmalıdır.<br>"
         "Bu tek düzeltme, birçok 'harmonik %70 kazanıyor' iddiasını ortadan kaldırır.</span>",
         R["kirmizi"], 0.09, font=11, kalin=2.2)
    akis_ok(fig, 5.6, y + 1.13, 5.6, y + 0.80, renk=R["kirmizi"])

    blok(fig, 5.6, 17.9, 10.4, 1.05,
         "<b>GİRDİ:</b> OHLC serisi · <i>n</i> (fraktal yarı-pencere) · <i>tol</i> (oran toleransı) · <i>maxSpan</i> (X→D max bar)",
         R["mavi"], 0.09, font=10)
    akis_ok(fig, 5.6, 17.35, 5.6, 16.75, renk=R["mavi"])
    blok(fig, 15.6, 17.9, 7.4, 1.05,
         "<span style='font-size:9px'><b>Ders kararı:</b> ardışık beşli, tüm kombinasyonlar değil.<br>"
         "11 pivotun tüm beşlileri = 462 aday/bar. Çoklu ölçek,<br><b>kombinasyonla değil <i>n</i>'i değiştirerek</b> taranır.</span>",
         R["mavi"], 0.07, font=9)

    not_kutusu(fig, "<b>Zigzag mi fraktal mı?</b> Zigzag (yüzde/ATR sapmalı) daha temiz yapı verir ama <b>son bacağı geriye dönük değişir</b> → repaint. "
                    "Fraktal (<i>n</i> barlık pencere) deterministiktir: bir pivot ancak <i>n</i> bar sonra kesinleşir, ama kesinleştikten sonra <b>asla değişmez</b>. "
                    "Backtest için fraktal zorunludur.<br>"
                    "<b>Örneklem gerçeği:</b> açık kaynak bir uygulamada 367 bin barlık 5 dakikalık seride yalnız 21 pattern / 7 sinyal çıkması, "
                    "tarayıcı yazarken 'az sinyal = bozuk kod' diye düşünmemek gerektiğini gösterir — katı kural az sinyal üretir.",
               x=0.5, y=-0.03, xanchor="center", yanchor="top", font=10)
    sema_layout(fig, "Şekil 46 — Harmonik tarayıcının tam algoritması: sekiz adım ve elenme kapıları", 980,
                "Sol sütun ana akış · sağ sütun elenme/etiketleme kapıları · kırmızı kutu, her tarayıcının ödemek zorunda olduğu gecikme faturası")
    fig.update_xaxes(range=[0, 20.4]); fig.update_yaxes(range=[y - 1.4, 18.9])
    fig.update_layout(margin=dict(b=95, l=30, r=30))
    kaydet(fig, "46_tarayici_algoritma_akis")
    RAPOR.append("46: 8 adımlı akış şeması (pivot → ardışık beşli → oranlar → sınıflandırma → PRZ → zaman → skor → teyit/gecikme); "
                 "şematik, veri içermez")


# ================================================================ 47 — repaint'in görsel kanıtı (GERÇEK VERİ)
def g47_repaint_gercek(no=47):
    df, kaynak = H.veri_getir("BTC-USD", "730d", "1h")
    if df is None:
        RAPOR.append("47 ATLANDI: BTC-USD 1h verisi yok")
        return
    n, t = 8, 4552
    tam = H.pivotlar(df, n)
    kp = [p for p in tam if p[0] <= t - 1 - n]
    if len(kp) < 5 or kp[-1][0] != 4535:
        RAPOR.append(f"47 ATLANDI: pinli pencere önbellekle uyuşmuyor (son kesin pivot {kp[-1][0] if kp else None}, beklenen 4535)")
        return
    son = kp[-1]; a = son[0] + 1
    gi = int(df.Low.values[a:t].argmin()) + a
    gec = (gi, float(df.Low.iloc[gi]), -1)
    X, A, B, C = kp[-4:]
    kesin_D = next(p for p in tam if p[0] > son[0] and p[2] == -1)
    xa = abs(A[1] - X[1]); ab = abs(A[1] - B[1]); bc = abs(C[1] - B[1])
    rB, rC = ab / xa, bc / ab
    rD_g = abs(A[1] - gec[1]) / xa; rBC_g = abs(gec[1] - C[1]) / bc
    rD_k = abs(A[1] - kesin_D[1]) / xa; rBC_k = abs(kesin_D[1] - C[1]) / bc
    fark = 100 * (gec[1] - kesin_D[1]) / gec[1]      # taban: geçici D — 'geçici D'nin %x altında' okuması

    i0 = max(0, X[0] - 30); iL = t; iRr = min(len(df) - 1, kesin_D[0] + 40)
    # alt alta: canlı an üstte, kesinleşmiş hâl altta (y ekseni aşağıda eşitlenir)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.07,
                        subplot_titles=(f"① Canlıda ekranda görünen — {df.index[iL]:%Y-%m-%d %H:%M} (bar {iL})",
                                        f"② {kesin_D[0]-gi} bar sonra kesinleşen hâl — {df.index[iRr]:%Y-%m-%d %H:%M}"))
    for row, i1 in ((1, iL), (2, iRr)):
        d_ = df.iloc[i0:i1 + 1]; xs = list(range(i0, i1 + 1))
        fig.add_trace(mum_iz(d_, x=xs), row=row, col=1)
        pv = [p for p in tam if i0 <= p[0] <= (i1 - 1 - n if row == 1 else i1)]
        fig.add_trace(go.Scatter(x=[p[0] for p in pv], y=[p[1] for p in pv], mode="lines",
                                 line=dict(color=R["gri"], width=1, dash="dot"),
                                 name=f"kesinleşmiş pivotlar (n={n})", showlegend=(row == 1),
                                 hoverinfo="skip"), row=row, col=1)
        tv, tt = H._tarih_tikleri(df, i0, i1, 6)
        fig.update_xaxes(tickvals=tv, ticktext=tt, tickfont=dict(size=9), row=row, col=1)
    pts_g = [(X[0], X[1]), (A[0], A[1]), (B[0], B[1]), (C[0], C[1]), (gec[0], gec[1])]
    zigzag_iz(pts_g, harfler=list("XABCD"), fig=fig, row=1, col=1, showlegend=False, renk=R["prz"])
    kutu(fig, C[0], iL, gec[1] - 260, gec[1] + 260, R["prz"], alfa=0.20,
         metin="ekranda 'PRZ' — bullish Butterfly tamamlandı sanılıyor", konum="top", row=1, col=1, font=9.5)
    not_kutusu(fig, f"Tarayıcının o an gördüğü:<br>rB = {rB:.3f} (Butterfly bandı 0.75–0.82 ✓)<br>"
                    f"rC = {rC:.3f} ✓<br>rD = <b>{rD_g:.3f}</b> XA (band 1.22–1.66 ✓)<br>"
                    f"rBC = {rBC_g:.3f} (band 1.60–2.70 ✓)<br><b>→ SİNYAL: bullish Butterfly</b><br>"
                    f"D 'seviyesi' {gec[1]:,.0f}",
               x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=1, col=1, font=9.5, renk=R["prz"])
    pts_k = [(X[0], X[1]), (A[0], A[1]), (B[0], B[1]), (C[0], C[1]), (kesin_D[0], kesin_D[1])]
    zigzag_iz(pts_k, harfler=list("XABCD"), fig=fig, row=2, col=1, showlegend=False, renk=R["kirmizi"])
    yatay(fig, gec[1], i0, iRr, f"canlıda 'D' sanılan seviye {gec[1]:,.0f}", renk=R["prz"], dash="dash",
          w=1.6, row=2, col=1, font=9.5)
    ok(fig, gi, gec[1], "bu bar <b>hiçbir zaman pivot olmadı</b>", ax=-46, ay=-58, renk=R["prz"],
       row=2, col=1, font=9.5)
    ok(fig, kesin_D[0], kesin_D[1], f"gerçek pivot: {kesin_D[1]:,.0f}<br>"
                                    f"geçici D'nin <b>%{abs(fark):.2f} altında</b>, {kesin_D[0]-gi} bar sonra",
       ax=48, ay=48, renk=R["kirmizi"], row=2, col=1, font=9.5)
    not_kutusu(fig, f"Aynı X-A-B-C, kesinleşmiş D ile:<br>rD = <b>{rD_k:.3f}</b> XA (hiçbir bantta değil)<br>"
                    f"rBC = {rBC_k:.3f} (band dışı)<br><b>→ pattern YOK.</b><br>"
                    "Ekranda görülen yapı hiç var olmadı;<br>onu 'gören' şey, henüz kesinleşmemiş<br>bir pivotu pivot saymaktı.",
               x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=2, col=1, font=9.5, renk=R["kirmizi"])
    fig.update_yaxes(title="fiyat (USD)", row=1, col=1)
    # iki panel aynı fiyatı iki anda gösteriyor: ölçek eşitlenir (eski shared_yaxes)
    fig.update_yaxes(title="fiyat (USD)", matches="y", row=2, col=1)
    not_kutusu(fig, "<b>Repaint budur.</b> Zigzag/otomatik harmonik göstergelerin çoğu, son bacağı henüz kesinleşmemiş bir uçla çizer; "
                    "uç kaydıkça geçmişteki çizim de değişir ve ekranda hep 'işe yaramış gibi görünen' bir tarih kalır.<br>"
                    f"Bu örnekte fark akademik değil, paradır: 'PRZ'den alan bir işlemci {gec[1]:,.0f}'dan girer, fiyat {kesin_D[1]:,.0f}'a "
                    f"(girişin <b>%{abs(fark):.2f}</b> altı) gider. Butterfly'ın geçersizlik seviyesi 1.618 XA = {A[1]-1.618*xa:,.0f} olduğuna göre stop çoktan yenmiştir.<br>"
                    "<b>Kural:</b> fraktal pivot kullan (kesinleşince <i>asla</i> değişmez), sinyali <i>n</i> bar gecikmeli kabul et, "
                    "backtest'te PnL'i D'nin <b>keşfedildiği</b> barın fiyatından hesapla.",
               x=0.5, y=-0.115, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, f"Şekil {no} — Gerçek veri — BTC-USD, 1h: repaint'in görsel kanıtı (aynı pencere, iki an)", 1020,
                 f"Fraktal pivot n={n}; üst panelde son pivot henüz kesinleşmemiş, alt panelde kesinleşmiş. "
                 f"Veri kaynağı: {kaynak} · pencere pinli", lejant=True)
    fig.update_layout(margin=dict(b=165))
    kaydet(fig, f"{no}_repaint_gercek_btc")
    RAPOR.append(f"47 (GERÇEK): BTC-USD 1h, n=8, karar anı {df.index[iL]}. Canlı beşli X={X[1]:,.2f}({df.index[X[0]]:%Y-%m-%d %H:%M}) "
                 f"A={A[1]:,.2f} B={B[1]:,.2f} C={C[1]:,.2f} geçici D={gec[1]:,.2f} → rB {rB:.3f}, rC {rC:.3f}, rD {rD_g:.3f}, rBC {rBC_g:.3f} "
                 f"= bullish Butterfly sinyali. Kesin pivot {kesin_D[1]:,.2f} ({df.index[kesin_D[0]]:%Y-%m-%d %H:%M}), {kesin_D[0]-gi} bar sonra, "
                 f"geçici D'nin %{abs(fark):.2f} altında; aynı X-A-B-C ile rD {rD_k:.3f} / rBC {rBC_k:.3f} → hiçbir pattern bandında değil. "
                 f"Butterfly geçersizliği 1.618 XA = {A[1]-1.618*xa:,.2f}. Kaynak: {kaynak}")


# ================================================================ 48 — gerçek veride adım adım plan
def g48_gercek_adim_adim(no=48):
    df, kaynak = H.veri_getir("EURUSD=X", "730d", "1h")
    if df is None:
        RAPOR.append("48 ATLANDI: EURUSD=X 1h verisi yok")
        return
    n = 12
    adaylar = [a for a in H.tara(df, n) if a["pattern"] == "Crab" and a["D"][0] <= len(df) - 90]
    if not adaylar:
        RAPOR.append("48 ATLANDI: EURUSD=X 1h n=12 taramasında Crab adayı yok — sahte örnek üretilmedi")
        return
    a = adaylar[-1]
    X, A, B, C, D = (a[k] for k in "XABCD")
    xa = abs(A[1] - X[1])
    i0 = max(0, X[0] - 25); i1 = min(len(df) - 1, D[0] + 90)
    d_ = df.iloc[i0:i1 + 1]; xs = list(range(i0, i1 + 1))
    prz = {"1.618 XA": lvl(A[1], X[1], 1.618), "3.618 BC": C[1] - 3.618 * (C[1] - B[1])}
    plo, phi = min(prz.values()), max(prz.values())
    gen = (phi - plo) / xa
    a14 = float(atr(df)[D[0]])
    gec_y = lvl(A[1], X[1], 2.0)
    tbar_lo = float(df.Low.iloc[D[0]])
    sl_yapisal = gec_y - 0.75 * a14
    sl_tbar = tbar_lo - 0.75 * a14
    giris = phi
    T1 = D[1] + 0.382 * (A[1] - D[1]); T2 = D[1] + 0.618 * (A[1] - D[1]); T3 = A[1]
    tAB = B[0] - A[0]; tBC = C[0] - B[0]; tCD = D[0] - C[0]
    tau1, tau2 = tBC / tAB, tCD / tAB
    sonra = df.iloc[D[0] + 1:i1 + 1]
    t1_hit = bool((sonra.High >= T1).any()); t2_hit = bool((sonra.High >= T2).any())
    t3_hit = bool((sonra.High >= T3).any())
    sl_hit = bool((sonra.Low <= sl_tbar).any())
    t1_i = int(np.argmax(sonra.High.values >= T1)) + D[0] + 1 if t1_hit else None
    sl_i = int(np.argmax(sonra.Low.values <= sl_tbar)) + D[0] + 1 if sl_hit else None
    once_sl = bool(sl_hit and (t1_i is None or sl_i < t1_i))
    F = H._fmt(D[1])

    fig = go.Figure(mum_iz(d_, x=xs))
    zigzag_iz([(X[0], X[1]), (A[0], A[1]), (B[0], B[1]), (C[0], C[1]), (D[0], D[1])],
              harfler=list("XABCD"), fig=fig, showlegend=False)
    pv = [p for p in H.pivotlar(df, n) if i0 <= p[0] <= i1]
    fig.add_trace(go.Scatter(x=[p[0] for p in pv], y=[p[1] for p in pv], mode="lines",
                             line=dict(color=R["gri"], width=1, dash="dot"),
                             name=f"fraktal pivotlar (n={n})", hoverinfo="skip"))
    kutu(fig, C[0], i1, plo, phi, R["prz"], alfa=0.18, metin=f"PRZ (genişlik %{100*gen:.1f} XA)", konum="bottom", font=10)
    prz_cizgileri(fig, prz, C[0], i1, fmt=F)
    yatay(fig, gec_y, X[0], i1, f"geçersizlik 2.0 XA → {F.format(gec_y)}", renk=R["kirmizi"], dash="dash", font=9.5)
    yatay(fig, sl_yapisal, X[0], i1, f"yapısal stop {F.format(sl_yapisal)} → 1R = {F.format(giris-sl_yapisal)}",
          renk=R["gri"], dash="dot", font=9.5)
    yatay(fig, sl_tbar, D[0], i1, f"<b>T-bar stopu</b> {F.format(sl_tbar)} → 1R = {F.format(giris-sl_tbar)}",
          renk=R["kirmizi"], w=1.8, font=9.5)
    yatay(fig, giris, D[0], i1, f"giriş (PRZ üst kenarı) {F.format(giris)}", renk=R["ink"], w=1.5, font=9.5)
    Rr = giris - sl_tbar
    for t_, ad in ((T1, "T1 0.382 AD"), (T2, "T2 0.618 AD"), (T3, "T3 = A")):
        hit = {T1: t1_hit, T2: t2_hit, T3: t3_hit}[t_]
        yatay(fig, t_, D[0], i1, f"{ad} {F.format(t_)} ({(t_-giris)/Rr:.1f}R) — {'ulaşıldı' if hit else 'ulaşılmadı'}",
              renk=R["yesil"] if hit else R["gri"], dash=None if hit else "dot", font=9.5)
    if t1_i:
        ok(fig, t1_i, T1, f"T1'e {t1_i-D[0]}. barda ulaştı", ax=0, ay=-40, renk=R["yesil"], font=9.5)
    ok(fig, D[0], D[1], f"D = {a['rD']:.3f} XA · {a['rBC']:.2f} BC<br>T-bar dibi {F.format(tbar_lo)}",
       ax=-64, ay=58, renk=R["prz"], font=9.5)

    kontrol = [
        (f"B = {a['rB']:.3f} XA — Crab bandı 0.36–0.65", 0.36 <= a["rB"] <= 0.65),
        (f"C = {a['rC']:.3f} AB — 0.382–0.886 ve C, A'yı aşmadı", 0.382 <= a["rC"] <= 0.886),
        (f"D = {a['rD']:.3f} XA — Crab imzası 1.618 (±tolerans)", 1.55 <= a["rD"] <= 1.70),
        (f"BC projeksiyonu {a['rBC']:.2f} — Crab'de 2.618–3.618", 2.5 <= a["rBC"] <= 3.7),
        (f"PRZ genişliği %{100*gen:.1f} XA — hedef ≤ %3", gen <= 0.03),
        (f"τ₂ = t_CD/t_AB = {tau2:.2f} — bant 0.618–1.618", 0.618 <= tau2 <= 1.618),
        (f"τ₁ = t_BC/t_AB = {tau1:.2f} — bant 0.382–1.00", 0.382 <= tau1 <= 1.0),
        (f"her bacak ≥ 5 bar (t_AB={tAB}, t_BC={tBC}, t_CD={tCD})", min(tAB, tBC, tCD) >= 5),
        (f"stop mesafesi / PRZ genişliği = {(giris-sl_tbar)/max(phi-plo,1e-9):.1f} — ≥ 1.5", (giris - sl_tbar) / max(phi - plo, 1e-9) >= 1.5),
    ]
    satir = "<br>".join(f"{'✓' if v else '✗'} {t}" for t, v in kontrol)
    evet = sum(1 for _, v in kontrol if v)
    not_kutusu(fig, f"<b>Kontrol listesi — {evet}/{len(kontrol)} EVET</b><br>{satir}<br>"
                    "<i>Bir madde HAYIR ise pattern reddedilmez; skoru düşer ve pozisyon boyu küçülür.</i>",
               x=0.985, y=0.97, font=9.5)
    sonuc = ("stop ÖNCE çalıştı" if once_sl else
             ("T3'e (A) ulaştı" if t3_hit else ("T2'ye ulaştı" if t2_hit else
              ("T1'e ulaştı — reaction" if t1_hit else "T1'e ulaşmadı"))))
    not_kutusu(fig, f"<b>Adım adım plan (bu gerçek örnek üzerinde)</b><br>"
                    f"① Tarama: fraktal n={n} → ardışık 5 pivot → oran testi · ② Sınıf: <b>bullish Crab</b> (B {a['rB']:.3f}, BC {a['rBC']:.2f})<br>"
                    f"③ PRZ = 1.618 XA {F.format(prz['1.618 XA'])} + 3.618 BC {F.format(prz['3.618 BC'])} · genişlik %{100*gen:.1f} XA<br>"
                    f"④ Tetik: PRZ içinde kapanışlı dönüş mumu · ⑤ Giriş {F.format(giris)} · T-bar stopu {F.format(sl_tbar)} (1R = {F.format(Rr)})<br>"
                    f"⑥ Hedefler: T1 {F.format(T1)} = {(T1-giris)/Rr:.1f}R · T2 {F.format(T2)} = {(T2-giris)/Rr:.1f}R · T3 = A {F.format(T3)} = {(T3-giris)/Rr:.1f}R<br>"
                    f"⑦ Crab bir <b>extension</b> pattern'idir → varsayılan hedef T1; %50 orada kapatılır, SL → BE<br>"
                    f"⑧ Sonuç ({len(sonra)} bar): <b>{sonuc}</b>. Tek örnek kanıt değildir — kural sabitken çok sayıda örnekte ölçülmeden başarı oranı bilinmez.<br>"
                    f"Yapısal stop ({F.format(sl_yapisal)}) kullanılsaydı 1R = {F.format(giris-sl_yapisal)} olurdu → T1'de R:R "
                    f"{(T1-giris)/(giris-sl_yapisal):.2f}; <b>geçersizlik ≠ para stopu</b> ayrımının bedeli/faydası burada sayıyla görülüyor.<br>"
                    f"<b>Dürüstlük notu:</b> bu setup kontrol listesinden yalnız {evet}/{len(kontrol)} alıyor — PRZ %{100*gen:.1f} XA genişliğinde (hedef ≤%3), "
                    f"τ₁ = {tau1:.2f} ve τ₂ = {tau2:.2f} bant dışı (CD bacağı AB'nin {tau2:.1f} katı sürdü: 'sürünen' yapı). "
                    f"Skora göre bu <b>tam pozisyon değil, en fazla yarım</b> ya da yalnız takip demektir — ve buna rağmen T2'ye ulaştı. "
                    "Kötü puanlı bir setup'ın kazanması, puanlamanın yanlış olduğunu göstermez; tek gözlemin hiçbir şey göstermediğini gösterir.<br>"
                    f"Veri kaynağı: {kaynak} · pencere pinli",
               x=0.5, y=-0.085, xanchor="center", yanchor="top", font=9.5)
    tv, tt = H._tarih_tikleri(df, i0, i1)
    fig.update_xaxes(tickvals=tv, ticktext=tt, range=[i0, i1 + (i1 - i0) * 0.30])
    fig.update_yaxes(title="fiyat")
    temel_layout(fig, f"Şekil {no} — Gerçek veri — EUR/USD, 1h, {df.index[X[0]]:%Y-%m-%d} → {df.index[i1]:%Y-%m-%d}: "
                      f"tarayıcının bulduğu bullish Crab ve adım adım plan", 720,
                 f"Fraktal pivot n={n}; PRZ pattern'in ideal sayılarıyla, kontrol listesi ölçülen oranlarla dolduruldu", lejant=True)
    fig.update_layout(margin=dict(b=185))
    kaydet(fig, f"{no}_gercek_eurusd_crab_plan")
    RAPOR.append(f"48 (GERÇEK): EUR/USD 1h n=12 → bullish Crab; X {df.index[X[0]]:%Y-%m-%d %H:%M} {X[1]:.5f}, A {A[1]:.5f}, B {B[1]:.5f}, "
                 f"C {C[1]:.5f}, D {df.index[D[0]]:%Y-%m-%d %H:%M} {D[1]:.5f}; rB {a['rB']:.3f}, rC {a['rC']:.3f}, rD {a['rD']:.3f}, rBC {a['rBC']:.2f}; "
                 f"PRZ {plo:.5f}-{phi:.5f} (%{100*gen:.1f} XA); ATR(14)@D {a14:.5f}; giriş {giris:.5f}; T-bar stopu {sl_tbar:.5f} (1R={Rr:.5f}); "
                 f"yapısal stop {sl_yapisal:.5f}; T1 {T1:.5f}={(T1-giris)/Rr:.1f}R, T2 {T2:.5f}={(T2-giris)/Rr:.1f}R, T3 {T3:.5f}={(T3-giris)/Rr:.1f}R; "
                 f"τ1 {tau1:.2f}, τ2 {tau2:.2f}, t_AB {tAB}, t_BC {tBC}, t_CD {tCD}; kontrol {evet}/{len(kontrol)}; sonuç: {sonuc}; kaynak {kaynak}")


# ================================================================ ana
def main():
    g33_asamalar()
    g34_emir_izgarasi()
    g35_olcekli_giris()
    g36_kaybeden_senaryo()
    g37_rsi_bamm()
    g38_rsi_bamm_cakisma_yok()
    g39_uyumsuzluk_dereceleri()
    g40_teyit_katmanlari()
    g41_zaman_bolgeleri()
    g42_zaman_stopu()
    g43_ic_ice_pattern()
    g44_konfluens()
    g45_smc_birlesik()
    g46_tarayici_akis()
    g47_repaint_gercek()
    g48_gercek_adim_adim()
    print("\n=== ÜRETİLEN DOSYALAR ===")
    for u in H.URETILEN:
        print(u)
    print("\n=== RAPOR ===")
    for r in RAPOR:
        print(r)


if __name__ == "__main__":
    main()
