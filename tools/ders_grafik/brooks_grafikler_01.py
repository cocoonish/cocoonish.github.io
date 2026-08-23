#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Al Brooks fiyat hareketi dersi — FİGÜR 01–12.

Kapsam: B0 (çerçeve: piyasa kimin, olasılık, atalet) ve B1 (bar okuma: gövde,
kuyruk, kapanış, baskı, doji, duraklama, klimaks). Numaralar müfredat SÜRÜM 2'nin
"3. GRAFİK LİSTESİ" tablosundan (01–94) gelir.

Gerçek veri notu. Müfredat 03 ve 08'de USDTRY 5 dakikalık ister; önbellekteki
USDTRY serisi spot kotasyon akışıdır (barların %66–92'si doji, uçlar tekrar
ediyor, gövdesiz kuyruklar var) ve bar okuma dersinde kullanılamaz. Bu iki figür
müfredatın birinci öncelikli enstrümanı olan XU030 5 dakikalıkla üretildi;
altbaşlıkta belirtildi. 02 numaralı figür 1 dakikalık veri ister; önbellekte
1 dakikalık seri yok, üçleme 5dk / 15dk / 1saat olarak kuruldu (altbaşlıkta yazılı).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from brooks_ortak import (
    ALTIN, BORDO, CIZGI, GRI, MAVI, MOR, MUREKKEP, TEAL, TURUNCU,
    cizgi, defter_yaz, dilim, duzen, ema_ciz, hover, islem, kaydet, kutu,
    lejant, lejant_cizgi, mumlar, not_, rgba, trend_cizgisi, yatay, yol_uret, yukle,
    zaman_ekseni,
)

XU5 = "XU030.IS", "5m"


# ---------------------------------------------------------------- yardımcılar
def cerceve(ohlc, baslangic="2026-01-05 09:30", dakika=5) -> pd.DataFrame:
    """Elle kurulmuş barlar → DataFrame. df_yap'tan farkı: None satırı (boşluk)
    kabul eder — kartela figürlerinde gruplar arası ayraç için gerekli."""
    satir = []
    for x in ohlc:
        satir.append((np.nan,) * 4 if x is None else tuple(float(v) for v in x))
    d = pd.DataFrame(satir, columns=["o", "h", "l", "c"])
    d["ts"] = pd.date_range(baslangic, periods=len(d), freq=f"{dakika}min")
    dolu = d.dropna()
    kotu = dolu[(dolu.h < dolu[["o", "c"]].max(axis=1) - 1e-9)
                | (dolu.l > dolu[["o", "c"]].min(axis=1) + 1e-9)]
    if len(kotu):
        raise ValueError(f"geçersiz bar(lar): {list(kotu.index)}")
    return d


def x_basliklari(fig, n_satir: int, metin="bar sırası"):
    """duzen() bütün eksenlere x başlığı yazıyor; çok panelli figürde yalnız en
    alttakinde kalsın."""
    for r in range(1, n_satir + 1):
        fig.update_xaxes(title_text=(metin if r == n_satir else ""), row=r, col=1)


def y_baslik(fig, row, metin, secondary=False):
    """duzen() bütün y eksenlerine 'fiyat' yazıyor; özel eksenleri ONDAN SONRA
    düzeltmek gerekir (yoksa puan/yüzde ekseni 'fiyat' diye etiketlenir)."""
    fig.update_yaxes(title_text=metin, row=row, col=1, secondary_y=secondary)


def panel_basliklari(fig, boyut=12.5):
    for a in fig.layout.annotations or ():
        if a.text and a.font and a.font.size and a.font.size >= 15 and a.xref == "paper":
            a.font.size = boyut
            a.font.color = MUREKKEP
            a.xanchor = "left"
            a.x = 0.0


def karis(c1: str, c2: str, t: float) -> str:
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{int(round(a[i] + (b[i] - a[i]) * t)):02x}" for i in range(3))


def merkezle(barlar, hedef=100.0):
    orta = np.mean([(b[1] + b[2]) / 2 for b in barlar])
    k = hedef - orta
    return [(b[0] + k, b[1] + k, b[2] + k, b[3] + k) for b in barlar]


def bant_uret(n, genlik, govde_orani, tohum, egim=0.0, bas=100.0):
    """Ortalamaya dönen (mean-reverting) bar dizisi — yatay bant / dar bant /
    barbwire kesitleri için. yol_uret rastgele yürüyüştür ve bant üretmez."""
    rng = np.random.default_rng(tohum)
    out, p = [], 0.0
    for i in range(n):
        merkez = egim * i
        c = merkez + np.clip(p - merkez + rng.normal(0, genlik * 0.75), -genlik, genlik)
        o = p
        govde = abs(c - o)
        kuyruk = min(genlik * 0.85,
                     max(genlik * 0.30, govde * (1 - govde_orani) / max(govde_orani, 0.05)))
        ust = min(abs(rng.normal(0, kuyruk * 0.7)), kuyruk)
        alt = min(abs(rng.normal(0, kuyruk * 0.7)), kuyruk)
        out.append((bas + o, bas + max(o, c) + ust, bas + min(o, c) - alt, bas + c))
        p = c
    return out


def kuyruk_oranlari(df):
    m = (df.h - df.l).replace(0, np.nan)
    ust = (df.h - df[["o", "c"]].max(axis=1)) / m
    alt = (df[["o", "c"]].min(axis=1) - df.l) / m
    return ust.fillna(0), alt.fillna(0)


# ================================================================== 01
def f01_tayf():
    """Fiyat hareketi tayfı şeridi — Ş · 2 panel.
    Solda uç trend, sağda uç bant, arada 5 ara rejim; altta her rejime kesit."""
    rejim = [
        ("1", "Uç trend<br>kırılım / spike"),
        ("2", "Güçlü trend<br>sıkı kanal"),
        ("3", "Trend<br>geniş kanal"),
        ("4", "Trend eden<br>yatay bant"),
        ("5", "Yatay bant"),
        ("6", "Dar yatay bant"),
        ("7", "Uç bant<br>barbwire"),
    ]
    kesit = [
        merkezle(yol_uret(14, 100, 1.60, 0.20, tohum=4101, govde_orani=0.92)),
        merkezle(yol_uret(14, 100, 0.95, 0.35, tohum=4102, govde_orani=0.78)),
        merkezle(yol_uret(14, 100, 0.60, 0.80, tohum=4103, govde_orani=0.60)),
        merkezle(bant_uret(14, 2.8, 0.55, tohum=4104, egim=0.55)),
        merkezle(bant_uret(14, 3.0, 0.50, tohum=4105)),
        merkezle(bant_uret(14, 1.5, 0.45, tohum=4106)),
        merkezle(bant_uret(14, 1.1, 0.15, tohum=4107)),
    ]

    fig = make_subplots(rows=2, cols=1, row_heights=[0.28, 0.72], vertical_spacing=0.12,
                        subplot_titles=(
                            "Panel 1 — tayf şeridi: bir uçta saf trend, öbür uçta saf bant",
                            "Panel 2 — her rejimin kesiti (14'er bar, aynı dikey bantta ortalanmış)"))

    for i, (no, ad) in enumerate(rejim):
        renk = karis(TEAL, GRI, i / (len(rejim) - 1))
        kutu(fig, i + 0.04, i + 0.96, 0, 1, renk, a=0.45, cizgi=1.0, row=1, col=1)
        not_(fig, i + 0.5, 0.5, f"<b>{no}</b><br>{ad}", renk=MUREKKEP, ok=False, boyut=9,
             row=1, col=1, arka=False)
    not_(fig, 0.0, 1.52, "◀ saf yön: her bar bir kırılım, geri çekilme yok, yönsel olasılık %70+",
         renk=TEAL, ok=False, boyut=10.5, xanchor="left", row=1, col=1)
    not_(fig, 7.0, -0.42, "saf belirsizlik: her kırılım başarısız, yönsel olasılık %50 ▶",
         renk=GRI, ok=False, boyut=10.5, xanchor="right", row=1, col=1)
    fig.update_yaxes(range=[-0.85, 1.95], showticklabels=False, showgrid=False, row=1, col=1)
    fig.update_xaxes(range=[-0.1, 7.1], showticklabels=False, showgrid=False, row=1, col=1)

    barlar, ayrac, etiket = [], [], []
    x = 0
    for i, (no, ad) in enumerate(rejim):
        if i:
            barlar.append(None)
            ayrac.append(x - 0.5)
            x += 1
        etiket.append((x + 6.5, f"<b>{no}</b> {ad}"))
        barlar.extend(kesit[i])
        x += 14
    d = cerceve(barlar)
    fig.add_trace(mumlar(d, ad="rejim kesiti"), row=2, col=1)
    tavan, taban = float(d.h.max()), float(d.l.min())
    for xa in ayrac:
        cizgi(fig, xa, taban - 3, xa, tavan + 6.2, renk=CIZGI, dash="dot", w=1.0,
              row=2, col=1)
    for xa, met in etiket:
        not_(fig, xa, tavan + 2.4, met, renk=MUREKKEP, ok=False, boyut=9.5, row=2, col=1)
    yatay(fig, 100, -1, len(d), renk=GRI, dash="dot", w=1.0, row=2, col=1)
    fig.update_yaxes(range=[taban - 3.5, tavan + 7.0], row=2, col=1)

    duzen(fig, "Fiyat hareketi tayfı: trend ile yatay bant aynı çizginin iki ucudur",
          "her ekran görüntüsü bu şeridin bir yerine düşer — mesele adlandırmak değil, konumlandırmak",
          h=900, sematik=True)
    x_basliklari(fig, 2)
    fig.update_xaxes(title_text="", row=1, col=1)
    y_baslik(fig, 1, "")
    panel_basliklari(fig)
    kaydet(fig, "01_tayf_seridi", olcum=dict(
        rejim_sayisi=7, kesit_bar_sayisi=14,
        rejimler=[r[1].replace("<br>", " ") for r in rejim]))


# ================================================================== 02
def f02_uc_zaman_dilimi():
    """Aynı hareketin üç zaman diliminde görünümü — G · 3 panel.
    Müfredat 1dk/5dk/15dk ister; önbellekte 1dk yok → 5dk/15dk/1saat."""
    d5, d15, d1 = yukle(*XU5), yukle("XU030.IS", "15m"), yukle("XU030.IS", "1h")
    if d5 is None or d15 is None or d1 is None:
        print("  ! 02 atlandı: XU030 önbelleği eksik")
        return
    p5, p15, p1 = dilim(d5, 1843, 97), dilim(d15, 596, 64), dilim(d1, 5790, 112)
    kutu5 = (1878 - 1843, 1925 - 1843)      # 26 Haz 09:50 → 13:45
    kutu15 = (639 - 596, 655 - 596)   # 15dk barları :45'te başlar → 09:45 barı 09:50'yi kapsar
    kutu1 = (5893 - 5790, 5897 - 5790)   # 1s barları :30'da başlar → 09:30 ve 13:30 barları

    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.075, subplot_titles=(
        "Panel 1 — 5 dakikalık: bölge 48 bar; yatay bir başlangıç, bir ayı kanalı, hızlanan bir son bacak",
        "Panel 2 — 15 dakikalık: aynı bölge 16 bar; tek bir ayı bacağı",
        "Panel 3 — 1 saatlik: aynı bölge 6 bar; üç haftalık düşüşün bir dilimi"))

    for r, (p, k, ad) in enumerate([(p5, kutu5, "5 dakika"), (p15, kutu15, "15 dakika"),
                                    (p1, kutu1, "1 saat")], start=1):
        fig.add_trace(mumlar(p, ad=ad, hover=hover(p)), row=r, col=1)
        ema_ciz(fig, p, 20, renk=GRI, row=r, col=1,
                ad="20 bar EMA" if r == 1 else None)
        if r > 1:
            fig.data[-1].showlegend = False
        y0 = float(p.l[k[0]:k[1] + 1].min())
        y1 = float(p.h[k[0]:k[1] + 1].max())
        pay = (p.h.max() - p.l.min()) * 0.02
        kutu(fig, k[0] - 0.5, k[1] + 0.5, y0 - pay, y1 + pay, ALTIN, a=0.08, cizgi=1.5,
             row=r, col=1)
        not_(fig, (k[0] + k[1]) / 2, y1 + pay,
             f"26 Haz 09:50–13:45 · bu ölçekte {k[1]-k[0]+1} bar"
             + (f" · 5 dakikalıkta {y1-y0:.0f} puanlık düşüş" if r == 1 else ""),
             renk=ALTIN, ay=-26, boyut=10, row=r, col=1)
        zaman_ekseni(fig, p, adet=7, fmt="%d %b %H:%M" if r < 3 else "%d %b", row=r, col=1)

    not_(fig, kutu5[0] + 24, float(p5.h[kutu5[0]:kutu5[1] + 1].max()),
         "aynı iskelet üç ölçekte de var: itiş → kanal → hızlanan son bacak",
         renk=GRI, ok=False, boyut=10, yanchor="top", row=1, col=1)
    lejant(fig, "işaretli bölge — üç panelde aynı 3 saat 55 dakika", ALTIN)

    duzen(fig, "Fraktal yapı: aynı hareket, üç zaman dilimi",
          "XU030 · 26 Haziran 2026 · pencereler indisle pinli · müfredattaki 1dk ayağı "
          "önbellekte olmadığı için üçleme 5dk / 15dk / 1saat kuruldu",
          h=1180)
    x_basliklari(fig, 3)
    panel_basliklari(fig)
    kaydet(fig, "02_uc_zaman_dilimi", olcum=dict(
        enstruman="XU030.IS", bolge="2026-06-26 09:50–13:45",
        bar_5dk=kutu5[1] - kutu5[0] + 1, bar_15dk=kutu15[1] - kutu15[0] + 1,
        bar_1saat=kutu1[1] - kutu1[0] + 1,
        pencere_5dk=[1843, 1939], pencere_15dk=[596, 659], pencere_1saat=[5790, 5901],
        kutu_5dk=[1878, 1925], kutu_15dk=[639, 655], kutu_1saat=[5893, 5897],
        bolge_yuksek=round(float(p5.h[kutu5[0]:kutu5[1] + 1].max()), 1),
        bolge_dusuk=round(float(p5.l[kutu5[0]:kutu5[1] + 1].min()), 1)))


# ================================================================== 03
def f03_atalet():
    """Atalet: üç başarısız dönüş, üç başarısız kırılım — G · 2 panel."""
    d = yukle(*XU5)
    if d is None:
        print("  ! 03 atlandı: XU030 5dk önbelleği yok")
        return
    a = dilim(d, 1878, 48)      # 26 Haz 09:50 → 13:45 · güçlü ayı trendi
    b = dilim(d, 1690, 42)      # 24 Haz 10:20 → 13:45 · yatay bant

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.10, subplot_titles=(
        "Panel 1 — güçlü ayı trendi: üç boğa dönüş denemesi, üçü de yutuluyor",
        "Panel 2 — yatay bant: üç kırılım denemesi, üçü de bandın içine geri düşüyor"))

    # --- panel 1
    fig.add_trace(mumlar(a, ad="XU030 5dk", hover=hover(a)), row=1, col=1)
    ema_ciz(fig, a, 20, renk=GRI, row=1, col=1, ad="20 bar EMA")
    trend_cizgisi(fig, a, (14, 23), yon="bear", renk=BORDO, dash="dash", w=1.3, row=1, col=1)
    pay1 = (a.h.max() - a.l.min()) * 0.022
    for k, (i, j, ay) in enumerate([(26, 27, -34), (33, 35, -52), (42, 44, -34)], start=1):
        kutu(fig, i - 0.45, i + 0.45, a.l[i], a.h[i], TURUNCU, a=0.22, cizgi=1.3, row=1, col=1)
        not_(fig, i, a.h[i] + pay1,
             f"<b>{k}. dönüş denemesi</b> — boğa barı {a.c[i]-a.o[i]:+.0f} puan",
             renk=TURUNCU, ay=ay, boyut=10, row=1, col=1)
        not_(fig, j, a.l[j] - pay1,
             f"{j-i} bar sonra yeni dip {a.l[j]:.0f}", renk=BORDO, ay=28 + 20 * (k == 2),
             boyut=9.5, row=1, col=1)
    not_(fig, 1, a.h.max(), f"trend net {a.c.iloc[-1]-a.o.iloc[0]:+.0f} puan "
         f"(%{(a.c.iloc[-1]/a.o.iloc[0]-1)*100:+.2f}) · 48 barda üç dönüş denemesi, üçü de başarısız",
         renk=BORDO, ok=False, boyut=10, xanchor="left", yanchor="top", row=1, col=1)

    # --- panel 2
    fig.add_trace(mumlar(b, ad="XU030 5dk", hover=hover(b)), row=2, col=1)
    fig.data[-1].showlegend = False
    ema_ciz(fig, b, 20, renk=GRI, row=2, col=1)
    fig.data[-1].showlegend = False
    bant_ust, bant_alt = float(b.h[12:18].max()), float(b.l[12:18].min())
    kutu(fig, 11.5, 41.4, bant_alt, bant_ust, GRI, a=0.09, cizgi=1.1, row=2, col=1)
    yatay(fig, bant_ust, 11.5, 41.4, renk=GRI, dash="dash", w=1.4, row=2, col=1)
    yatay(fig, bant_alt, 11.5, 41.4, renk=GRI, dash="dash", w=1.4, row=2, col=1)
    not_(fig, 41.6, bant_ust, f"bant tavanı {bant_ust:.0f}", renk=GRI, ok=False, boyut=10,
         xanchor="left", row=2, col=1)
    not_(fig, 41.6, bant_alt, f"bant tabanı {bant_alt:.0f}<br>yükseklik "
         f"{bant_ust-bant_alt:.0f} puan", renk=GRI, ok=False, boyut=10, xanchor="left",
         row=2, col=1)
    not_(fig, 0.4, float(b.l.min()) - (b.h.max() - b.l.min()) * 0.10,
         "bant sınırları, bandın ilk altı barından (12–17) türetildi", renk=GRI, ok=False,
         boyut=9, xanchor="left", row=2, col=1)
    pay2 = (b.h.max() - b.l.min()) * 0.022
    for k, (i, yon, j, ay) in enumerate([(18, "yukarı", 20, -34), (24, "aşağı", 26, 34),
                                         (32, "yukarı", 34, -54)], start=1):
        kutu(fig, i - 0.45, i + 0.45, b.l[i], b.h[i], TURUNCU, a=0.22, cizgi=1.3, row=2, col=1)
        if yon == "yukarı":
            not_(fig, i, b.h[i] + pay2, f"<b>{k}. kırılım</b> (yukarı) — tavanı "
                 f"{b.h[i]-bant_ust:+.0f} puan aştı", renk=TURUNCU, ay=ay, boyut=10,
                 row=2, col=1)
            not_(fig, j, b.c[j], f"{j-i} bar sonra bandın içinde", renk=GRI, ay=40,
                 boyut=9.5, row=2, col=1)
        else:
            not_(fig, i, b.l[i] - pay2, f"<b>{k}. kırılım</b> (aşağı) — tabanı "
                 f"{bant_alt-b.l[i]:+.0f} puan deldi", renk=TURUNCU, ay=ay, boyut=10,
                 row=2, col=1)
            not_(fig, j, b.c[j], f"{j-i} bar sonra bandın içinde", renk=GRI, ay=-40,
                 boyut=9.5, row=2, col=1)
    not_(fig, 38, b.h[38] + pay2, f"dördüncü deneme de başarısız — tavanı "
         f"{b.h[38]-bant_ust:+.0f} puan aştı, iki barda geri emildi",
         renk=TURUNCU, ay=-28, boyut=9.5, row=2, col=1)
    genis = float(b.h.max() - b.l.min())
    fig.update_yaxes(range=[float(b.l.min()) - genis * 0.15,
                            float(b.h.max()) + genis * 0.14], row=2, col=1)
    genis1 = float(a.h.max() - a.l.min())
    fig.update_yaxes(range=[float(a.l.min()) - genis1 * 0.10,
                            float(a.h.max()) + genis1 * 0.10], row=1, col=1)
    fig.update_xaxes(range=[-1, 47.5], row=2, col=1)

    lejant(fig, "başarısız deneme (dönüş / kırılım)", TURUNCU)
    lejant(fig, "yatay bant gövdesi", GRI)
    duzen(fig, "Piyasa ataleti: hareket halindeki piyasa hareketine devam eder",
          "XU030 5 dakikalık · pencereler indisle pinli (1878+48 ve 1690+42) · "
          "müfredat USDTRY ister; önbellekteki USDTRY spot akışı bar okumaya elverişsiz "
          "olduğu için birinci öncelikli enstrümana geçildi",
          h=1040)
    x_basliklari(fig, 2)
    panel_basliklari(fig)
    kaydet(fig, "03_atalet_basarisiz_denemeler", olcum=dict(
        enstruman="XU030.IS 5dk",
        panel1_pencere=[1878, 1925], panel1_tarih="2026-06-26 09:50–13:45",
        panel1_bar_sayisi=48,
        panel1_net_puan=round(float(a.c.iloc[-1] - a.o.iloc[0]), 1),
        panel1_net_yuzde=round(float(a.c.iloc[-1] / a.o.iloc[0] - 1) * 100, 2),
        panel1_basarisiz_donus=3, panel1_donus_barlari=[26, 33, 42],
        panel2_pencere=[1690, 1731], panel2_tarih="2026-06-24 10:20–13:45",
        panel2_bant_ust=round(bant_ust, 1), panel2_bant_alt=round(bant_alt, 1),
        panel2_bant_yukseklik=round(bant_ust - bant_alt, 1),
        panel2_basarisiz_kirilim=3, panel2_kirilim_barlari=[18, 24, 32],
        panel2_dorduncu_deneme=38))


# ================================================================== 04
def f04_esit_uzaklik():
    """Eşit uzaklıklı hareket ve %50 tabanı — Ş · 1 panel."""
    giris, X, ADIM = 100.0, 6.0, 0.85

    def yol(tohum, n=120):
        rng = np.random.default_rng(tohum)
        p, seri = giris, [giris]
        for _ in range(n):
            p += rng.normal(0, ADIM)
            seri.append(p)
            if p >= giris + X or p <= giris - X:
                break
        return seri

    # deterministik sayım: 400 yol, kaçı önce +X'e vardı
    yukari_say = asagi_say = bitmeyen = 0
    for t in range(1, 401):
        s = yol(t)
        if s[-1] >= giris + X:
            yukari_say += 1
        elif s[-1] <= giris - X:
            asagi_say += 1
        else:
            bitmeyen += 1
    biten = yukari_say + asagi_say

    secili = []
    for t in range(1, 400):
        s = yol(t)
        if len(s) < 16:
            continue
        yon = "yukari" if s[-1] >= giris + X else ("asagi" if s[-1] <= giris - X else None)
        if yon and sum(1 for _, y in secili if y == yon) < 3:
            secili.append((s, yon))
        if len(secili) == 6:
            break

    fig = go.Figure()
    n = max(len(s) for s, _ in secili) + 6
    kutu(fig, -1, n, giris, giris + X, TEAL, a=0.06, cizgi=0)
    kutu(fig, -1, n, giris - X, giris, BORDO, a=0.06, cizgi=0)
    for k, (s, yon) in enumerate(secili):
        renk = TEAL if yon == "yukari" else BORDO
        fig.add_trace(go.Scatter(
            x=list(range(len(s))), y=s, mode="lines",
            name=f"{'A' if yon == 'yukari' else 'B'}{k+1} — {'+X' if yon == 'yukari' else '−X'}'e "
                 f"{len(s)-1} barda vardı",
            line=dict(color=rgba(renk, 0.9), width=1.9)))
        fig.add_trace(go.Scatter(x=[len(s) - 1], y=[s[-1]], mode="markers", showlegend=False,
                                 marker=dict(size=9, color=renk, symbol="circle")))
    yatay(fig, giris, -1, n, renk=MAVI, dash="solid", w=2.0)
    yatay(fig, giris + X, -1, n, renk=TEAL, dash="dash", w=1.6)
    yatay(fig, giris - X, -1, n, renk=BORDO, dash="dash", w=1.6)
    not_(fig, n, giris, "giriş fiyatı (şu an)", renk=MAVI, ok=False, boyut=11, xanchor="left")
    not_(fig, n, giris + X, f"+X = {X:.0f} birim", renk=TEAL, ok=False, boyut=11, xanchor="left")
    not_(fig, n, giris - X, f"−X = {X:.0f} birim", renk=BORDO, ok=False, boyut=11, xanchor="left")
    not_(fig, 1, giris + X * 0.62, "<b>%50</b> — önce X kadar yukarı gitme olasılığı",
         renk=TEAL, ok=False, boyut=11.5, xanchor="left")
    not_(fig, 1, giris - X * 0.62, "<b>%50</b> — önce X kadar aşağı gitme olasılığı",
         renk=BORDO, ok=False, boyut=11.5, xanchor="left")
    not_(fig, n * 0.50, giris + X * 1.30,
         f"<b>Aynı üreteçten 400 yol koşturuldu:</b> {biten} tanesi bir tarafa vardı — "
         f"{yukari_say}'i (%{yukari_say/biten*100:.1f}) önce +X'e, {asagi_say}'i "
         f"(%{asagi_say/biten*100:.1f}) önce −X'e.<br>Hedef ile stop eşit mesafedeyse hangisine "
         "önce değeceği yazı-tura'dır. Kenar buradan değil, mesafeleri EŞİTSİZ kurmaktan "
         "gelir (trader denklemi, B10).",
         renk=MUREKKEP, ok=False, boyut=10.5)
    fig.update_yaxes(range=[giris - X * 1.58, giris + X * 1.62])
    fig.update_xaxes(range=[-1.5, n + 1])
    duzen(fig, "Yönsel olasılık: eşit uzaklıkta her şey %50'dir",
          "altı yol da aynı üreteçten, aynı fiyattan çıktı — üçü +X'e, üçü −X'e ilk vardı",
          x_baslik="bar sırası (giriş anından itibaren)", h=680, sematik=True)
    kaydet(fig, "04_esit_uzaklikli_hareket", olcum=dict(
        giris=giris, X=X, adim_sapmasi=ADIM, yol_sayisi=400, biten_yol=biten,
        once_yukari=yukari_say, once_asagi=asagi_say, bitmeyen=bitmeyen,
        yukari_pay_pct=round(yukari_say / biten * 100, 1),
        asagi_pay_pct=round(asagi_say / biten * 100, 1),
        cizilen_yol=len(secili)))


# ================================================================== 05
def f05_bar_anatomisi():
    """Bar anatomisi kartelası — Ş · 1 panel · 12 bar tipi."""
    B1 = ("1", "Boğa trend<br>barı", "gövde menzilin %85'i", (98.0, 102.3, 97.7, 102.0), False)
    B2 = ("2", "Ayı trend<br>barı", "gövde menzilin %85'i", (102.0, 102.3, 97.7, 98.0), False)
    B3 = ("3", "Doji", "gövde menzilin %5'i", (100.2, 102.0, 98.0, 99.8), False)
    B4 = ("4", "Küçük bar", "menzil yarı boy", (99.6, 100.9, 99.0, 100.6), False)
    B5 = ("5", "Çok küçük<br>bar", "menzil çeyrek boy", (100.0, 100.5, 99.7, 100.3), False)
    B6 = ("6", "Tıraşlı boğa<br>(marubozu)", "iki uçta kuyruk yok", (98.0, 102.0, 98.0, 102.0), False)
    B7 = ("7", "Tıraşlı üst", "tepede kuyruk yok", (98.6, 102.0, 97.7, 102.0), False)
    B8 = ("8", "Tıraşlı alt", "dipte kuyruk yok", (98.0, 102.4, 98.0, 101.4), False)
    B9 = ("9", "Uzun alt<br>kuyruk", "kuyruk menzilin %70'i", (100.8, 102.0, 97.6, 101.6), False)
    B10 = ("10", "Uzun üst<br>kuyruk", "kuyruk menzilin %70'i", (99.2, 102.4, 98.0, 98.4), False)
    R1 = ("", "önceki<br>bar", "", (98.2, 102.2, 97.8, 101.8), True)
    B11 = ("11", "İç bar", "tamamı öncekinin içinde", (100.0, 101.6, 99.2, 101.0), False)
    R2 = ("", "önceki<br>bar", "", (99.2, 101.0, 98.8, 100.6), True)
    B12 = ("12", "Dış bar", "öncekini yutar", (100.4, 101.8, 98.2, 99.0), False)
    N = None
    tipler = [B1, N, B2, N, N,
              B3, N, B4, N, B5, N, N,
              B6, N, B7, N, B8, N, N,
              B9, N, B10, N, N,
              R1, B11, N, N,
              R2, B12]
    ana = [None if (t is None or t[4]) else t[3] for t in tipler]
    ref = [t[3] if (t is not None and t[4]) else None for t in tipler]
    d_ana, d_ref = cerceve(ana), cerceve(ref)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=list(range(len(d_ref))), open=d_ref.o, high=d_ref.h, low=d_ref.l, close=d_ref.c,
        name="bağlam barı (referans)",
        increasing=dict(line=dict(color=GRI, width=1.1), fillcolor=rgba(GRI, 0.28)),
        decreasing=dict(line=dict(color=GRI, width=1.1), fillcolor=rgba(GRI, 0.28)),
        whiskerwidth=0.15))
    fig.add_trace(mumlar(d_ana, ad="bar tipi"))

    sira = 0
    for i, t in enumerate(tipler):
        if t is None:
            continue
        no, ad, acikla, (o, h, l, c), gri = t
        if gri:
            not_(fig, i, 95.9, ad, renk=GRI, ok=False, boyut=8.5, arka=False)
            continue
        y_et = 96.1 if sira % 2 == 0 else 94.6
        sira += 1
        not_(fig, i, h + 0.25, f"<b>{no}</b>", renk=MUREKKEP, ok=False, boyut=11,
             yanchor="bottom", arka=False)
        not_(fig, i, y_et, f"<b>{no}</b> {ad}<br><span style='font-size:8px'>{acikla}</span>",
             renk=MUREKKEP, ok=False, boyut=9)

    cizgi(fig, -1.6, 98.0, -1.6, 102.0, renk=MOR, w=3.2)
    not_(fig, -1.95, 100.0, "gövde", renk=MOR, ok=False, boyut=9.5, xanchor="right")
    cizgi(fig, -1.6, 102.0, -1.6, 102.3, renk=ALTIN, w=3.2)
    not_(fig, -1.95, 102.3, "üst kuyruk", renk=ALTIN, ok=False, boyut=9.5, xanchor="right")
    cizgi(fig, -1.6, 97.7, -1.6, 98.0, renk=ALTIN, w=3.2)
    not_(fig, -1.95, 97.7, "alt kuyruk", renk=ALTIN, ok=False, boyut=9.5, xanchor="right")
    cizgi(fig, -0.85, 97.7, -0.85, 102.3, renk=GRI, w=1.6)
    not_(fig, -0.75, 103.2, "menzil", renk=GRI, ok=False, boyut=9.5, xanchor="left")
    not_(fig, (len(tipler) - 6) / 2, 104.1,
         "Bir barın söylediği tek şey: gövde kimin, kapanış nerede, kuyruk kimi reddetti.",
         renk=MUREKKEP, ok=False, boyut=11)
    fig.update_yaxes(range=[93.9, 104.9])
    fig.update_xaxes(range=[-6.4, len(tipler) - 0.2], showticklabels=False, title_text="")
    duzen(fig, "Bar anatomisi kartelası: on iki tip",
          "hepsi aynı ölçekte kuruldu — fark gövdenin payı, kapanışın yeri ve kuyruğun tarafı",
          x_baslik="", h=700, sematik=True)
    kaydet(fig, "05_bar_anatomisi", olcum=dict(
        bar_tipi_sayisi=12, referans_bar=2,
        tipler=[t[1].replace("<br>", " ") for t in tipler if t and not t[4]]))


# ================================================================== 06
def f06_govde_kapanis():
    """Gövde/menzil oranı ve kapanışın yeri — Ş · 2 panel."""
    H, L, O = 106.0, 94.0, 100.0
    varyant = [
        ("A", 105.6, "Boğalar ezici<br>üstünlükte", TEAL),
        ("B", 103.0, "Boğalar önde", TEAL),
        ("C", 100.0, "Berabere — doji", GRI),
        ("D", 97.0, "Ayılar önde", BORDO),
        ("E", 94.4, "Ayılar ezici<br>üstünlükte", BORDO),
    ]
    d = cerceve([(O, H, L, c) for _, c, _, _ in varyant])
    konum = [(c - L) / (H - L) * 100 for _, c, _, _ in varyant]
    govde = [abs(c - O) / (H - L) * 100 for _, c, _, _ in varyant]

    fig = make_subplots(rows=2, cols=1, row_heights=[0.60, 0.40], vertical_spacing=0.14,
                        subplot_titles=(
                            "Panel 1 — beş bar; aynı yüksek (106), aynı alçak (94), aynı açılış (100)",
                            "Panel 2 — kapanışın menzil içindeki yeri: kim kazandı"))
    fig.add_trace(mumlar(d, ad="varyant"), row=1, col=1)
    yatay(fig, H, -0.6, 4.6, renk=GRI, dash="dash", w=1.2, row=1, col=1)
    yatay(fig, L, -0.6, 4.6, renk=GRI, dash="dash", w=1.2, row=1, col=1)
    yatay(fig, O, -0.6, 4.6, renk=MAVI, dash="dot", w=1.2, row=1, col=1)
    not_(fig, 4.65, H, "yüksek 106", renk=GRI, ok=False, boyut=10, xanchor="left", row=1, col=1)
    not_(fig, 4.65, L, "alçak 94", renk=GRI, ok=False, boyut=10, xanchor="left", row=1, col=1)
    not_(fig, 4.65, O, "açılış 100", renk=MAVI, ok=False, boyut=10, xanchor="left", row=1, col=1)
    for i, (ad, c, hkm, renk) in enumerate(varyant):
        not_(fig, i, H + 0.6, f"<b>{ad}</b>  kapanış {c:.1f}", renk=renk, ok=False, boyut=10.5,
             row=1, col=1)
        not_(fig, i, L - 0.6, f"gövde %{govde[i]:.0f}<br>kapanış %{konum[i]:.0f}",
             renk=GRI, ok=False, boyut=9, yanchor="top", row=1, col=1)
    fig.update_yaxes(range=[L - 4.0, H + 2.2], row=1, col=1)
    fig.update_xaxes(range=[-0.7, 6.0], showticklabels=False, row=1, col=1)

    fig.add_trace(go.Bar(x=[i - 0.16 for i in range(5)], y=konum,
                         name="kapanışın menzil içindeki yeri (%)",
                         marker=dict(color=[rgba(v[3], 0.55) for v in varyant],
                                     line=dict(color=[v[3] for v in varyant], width=1.2)),
                         width=0.30), row=2, col=1)
    fig.add_trace(go.Bar(x=[i + 0.16 for i in range(5)], y=govde,
                         name="gövdenin menzile oranı (%)",
                         marker=dict(color=rgba(MOR, 0.30),
                                     line=dict(color=MOR, width=1.2), pattern_shape="/"),
                         width=0.30), row=2, col=1)
    yatay(fig, 50, -0.6, 4.6, renk=GRI, dash="dash", w=1.2, row=2, col=1)
    not_(fig, 4.65, 50, "%50 — berabere çizgisi", renk=GRI, ok=False, boyut=10,
         xanchor="left", row=2, col=1)
    for i, (ad, c, hkm, renk) in enumerate(varyant):
        not_(fig, i - 0.16, konum[i] + 5, f"%{konum[i]:.0f}", renk=renk, ok=False, boyut=10,
             row=2, col=1)
        not_(fig, i + 0.16, govde[i] + 5, f"%{govde[i]:.0f}", renk=MOR, ok=False, boyut=10,
             row=2, col=1)
        not_(fig, i, -10, f"<b>{ad}</b> · {hkm}", renk=renk, ok=False, boyut=9.5,
             yanchor="top", row=2, col=1)
    not_(fig, 2.0, 112, "A ile E'nin gövde oranı aynı (%47) ama hükümleri zıt — "
         "ayıran şey kapanışın hangi uçta olduğu.", renk=MUREKKEP, ok=False, boyut=9.5,
         row=2, col=1)
    fig.update_yaxes(range=[-42, 122], row=2, col=1)
    fig.update_xaxes(range=[-0.7, 6.0], showticklabels=False, row=2, col=1)

    duzen(fig, "Kapanışın yeri barın hükmüdür",
          "yüksek, alçak ve açılış sabit; değişen tek şey kapanış — ve bar tamamen başka bir şey söylüyor",
          h=920, sematik=True)
    x_basliklari(fig, 2, "")
    y_baslik(fig, 2, "kapanış konumu (%)")
    panel_basliklari(fig)
    kaydet(fig, "06_govde_ve_kapanis", olcum=dict(
        yuksek=H, alcak=L, acilis=O,
        kapanislar={v[0]: v[1] for v in varyant},
        kapanis_konumu_pct={v[0]: round(konum[i], 1) for i, v in enumerate(varyant)},
        govde_orani_pct={v[0]: round(govde[i], 1) for i, v in enumerate(varyant)}))


# ================================================================== 07
def f07_alim_baskisi():
    """Birikimli alım baskısı: 10 barlık tarama — G · 2 panel."""
    d = yukle(*XU5)
    if d is None:
        print("  ! 07 atlandı")
        return
    BAS, ADET = 3164, 37            # 16 Tem 2026 11:55 → 14:55
    p = dilim(d, BAS, ADET)
    tarama = (3178 - BAS, 3187 - BAS)       # 10 bar: 13:05 → 13:50
    kirilim = 3188 - BAS
    ust, alt = kuyruk_oranlari(p)
    govde = p.c - p.o
    puan = [(1 if govde[i] > 0 else (-1 if govde[i] < 0 else 0))
            + (1 if alt[i] > 0.35 else 0) - (1 if ust[i] > 0.35 else 0) for i in range(len(p))]
    birikim = np.cumsum(puan)
    tarama_puan = int(sum(puan[tarama[0]:tarama[1] + 1]))
    alt_say = int(sum(1 for i in range(tarama[0], tarama[1] + 1) if alt[i] > 0.35))
    ust_say = int(sum(1 for i in range(tarama[0], tarama[1] + 1) if ust[i] > 0.35))
    boga_say = int(sum(1 for i in range(tarama[0], tarama[1] + 1) if govde[i] > 0))
    tavan = float(p.h[tarama[0]:tarama[1] + 1].max())

    fig = make_subplots(rows=2, cols=1, row_heights=[0.60, 0.40], vertical_spacing=0.11,
                        specs=[[{}], [{"secondary_y": True}]], subplot_titles=(
                            "Panel 1 — ham barlar: yana giden 10 bar, ardından yukarı kırılım",
                            "Panel 2 — aynı barların baskı sayacı (bar başına puan) ve birikimi"))
    fig.add_trace(mumlar(p, ad="XU030 5dk", hover=hover(p)), row=1, col=1)
    ema_ciz(fig, p, 20, renk=GRI, row=1, col=1, ad="20 bar EMA")
    pay = (p.h.max() - p.l.min()) * 0.025
    kutu(fig, tarama[0] - 0.5, tarama[1] + 0.5, float(p.l[tarama[0]:tarama[1] + 1].min()) - pay,
         tavan + pay, ALTIN, a=0.09, cizgi=1.5, row=1, col=1)
    not_(fig, (tarama[0] + tarama[1]) / 2, tavan + pay,
         f"10 barlık tarama · {boga_say} boğa gövdesi · {alt_say} belirgin alt kuyruk · "
         f"{ust_say} belirgin üst kuyruk", renk=ALTIN, ay=-30, boyut=10, row=1, col=1)

    ax, ay_, bx, by = [], [], [], []
    for i in range(tarama[0], tarama[1] + 1):
        if alt[i] > 0.35:
            ax.append(i)
            ay_.append(float(p.l[i]) - pay * 0.7)
        if ust[i] > 0.35:
            bx.append(i)
            by.append(float(p.h[i]) + pay * 0.7)
    fig.add_trace(go.Scatter(x=ax, y=ay_, mode="markers", name="belirgin alt kuyruk (alım baskısı)",
                             marker=dict(symbol="triangle-up", size=9, color=TEAL,
                                         line=dict(color=TEAL, width=1))), row=1, col=1)
    if bx:
        fig.add_trace(go.Scatter(x=bx, y=by, mode="markers",
                                 name="belirgin üst kuyruk (satım baskısı)",
                                 marker=dict(symbol="triangle-down", size=9, color=BORDO,
                                             line=dict(color=BORDO, width=1))), row=1, col=1)
    yatay(fig, tavan, tarama[0] - 0.5, len(p) - 1, renk=GRI, dash="dash", w=1.3, row=1, col=1)
    not_(fig, tarama[0] + 1.0, tavan, f"tarama tavanı {tavan:.0f}", renk=GRI, ok=False,
         boyut=9.5, yanchor="bottom", row=1, col=1)
    kutu(fig, kirilim - 0.45, kirilim + 0.45, p.l[kirilim], p.h[kirilim], TEAL, a=0.22,
         cizgi=1.3, row=1, col=1)
    not_(fig, kirilim, p.l[kirilim] - pay,
         f"kırılım barı — gövde {p.c[kirilim]-p.o[kirilim]:+.0f} puan, tavanın "
         f"{p.c[kirilim]-tavan:+.0f} puan üstünde kapandı", renk=TEAL, ay=36, boyut=10,
         row=1, col=1)
    zirve = float(p.h[kirilim:kirilim + 6].max())
    not_(fig, int(p.h[kirilim:kirilim + 6].idxmax()), zirve + pay,
         f"kırılımdan sonra {zirve-tavan:+.0f} puan", renk=TEAL, ay=-28, boyut=10,
         row=1, col=1)
    zaman_ekseni(fig, p, adet=8, row=1, col=1)

    fig.add_trace(go.Bar(x=list(range(len(p))), y=puan, name="bar başına baskı puanı",
                         marker=dict(color=[rgba(TEAL if v > 0 else (BORDO if v < 0 else GRI), 0.55)
                                            for v in puan],
                                     line=dict(color=[TEAL if v > 0 else (BORDO if v < 0 else GRI)
                                                      for v in puan], width=1.0)),
                         width=0.62), row=2, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=list(range(len(p))), y=birikim, mode="lines",
                             name="birikimli baskı (sağ eksen)", line=dict(color=MOR, width=2.2)),
                  row=2, col=1, secondary_y=True)
    kayan = pd.Series(puan).rolling(10).sum()
    fig.add_trace(go.Scatter(x=list(range(len(p))), y=kayan, mode="lines",
                             name="son 10 barın net puanı (kayan pencere, sağ eksen)",
                             line=dict(color=TEAL, width=1.8, dash="dot")),
                  row=2, col=1, secondary_y=True)
    yatay(fig, 0, -0.5, len(p) - 1, renk=GRI, dash="dot", w=1.0, row=2, col=1)
    kutu(fig, tarama[0] - 0.5, tarama[1] + 0.5, -2.7, 2.7, ALTIN, a=0.08, cizgi=1.2,
         row=2, col=1)
    not_(fig, (tarama[0] + tarama[1]) / 2, -2.45,
         f"tarama penceresinin net puanı: <b>{tarama_puan:+d}</b> → alıcılar birikiyor",
         renk=ALTIN, ok=False, boyut=10, row=2, col=1)
    for i in range(tarama[0], tarama[1] + 1):
        v = puan[i]
        not_(fig, i, v + (0.32 if v >= 0 else -0.32), (f"{v:+d}" if v else "0"),
             renk=TEAL if v > 0 else (BORDO if v < 0 else GRI), ok=False, boyut=8.5,
             arka=False, row=2, col=1)
    ilk_pozitif = next((i for i in range(len(p))
                        if not np.isnan(kayan[i]) and kayan[i] >= 5), None)
    if ilk_pozitif is not None:
        cizgi(fig, ilk_pozitif, -3.1, ilk_pozitif, 3.1, renk=TEAL, dash="dot", w=1.4,
              row=2, col=1)
        not_(fig, ilk_pozitif + 0.3, 2.55,
             f"kayan 10 barlık puan ilk kez +5'e çıktı ({ilk_pozitif}. bar) — "
             f"kırılımdan {kirilim-ilk_pozitif} bar önce", renk=TEAL, ok=False, boyut=9,
             xanchor="left", row=2, col=1)
    fig.update_yaxes(range=[-3.1, 3.1], row=2, col=1, secondary_y=False)
    fig.update_yaxes(showgrid=False, row=2, col=1, secondary_y=True)
    zaman_ekseni(fig, p, adet=8, row=2, col=1)

    lejant_cizgi(fig, "puanlama: +1 boğa gövdesi · +1 alt kuyruk > menzilin %35'i · "
                      "−1 ayı gövdesi · −1 üst kuyruk > %35", ALTIN, dash="dot")
    duzen(fig, "Alım baskısı barlarda birikir, sonra tek hamlede ödenir",
          "XU030 5 dakikalık · 16 Temmuz 2026 11:55–14:55 · pencere indisle pinli (3164+37)",
          h=1000)
    x_basliklari(fig, 2)
    y_baslik(fig, 2, "bar puanı")
    y_baslik(fig, 2, "birikim", secondary=True)
    panel_basliklari(fig)
    kaydet(fig, "07_alim_baskisi_tarama", olcum=dict(
        enstruman="XU030.IS 5dk", pencere=[BAS, BAS + ADET - 1],
        tarih="2026-07-16 11:55–14:55",
        tarama_barlari=[tarama[0], tarama[1]], tarama_bar_sayisi=10,
        boga_govdesi=boga_say, belirgin_alt_kuyruk=alt_say, belirgin_ust_kuyruk=ust_say,
        tarama_net_puani=tarama_puan, tavan=round(tavan, 1),
        kirilim_bari=kirilim,
        kirilim_bari_govde=round(float(p.c[kirilim] - p.o[kirilim]), 1),
        kirilim_bari_kapanis=round(float(p.c[kirilim]), 1),
        kirilim_sonrasi_zirve=round(zirve, 1),
        kirilim_sonrasi_ilerleme=round(zirve - tavan, 1),
        kayan_puan_ilk_bes=ilk_pozitif,
        kayan_puan_kirilimdan_once_bar=(kirilim - ilk_pozitif) if ilk_pozitif is not None else None))


# ================================================================== 08
def f08_trend_bari_trend_degil():
    """Trend barı ≠ trend — G · 2 panel."""
    d = yukle(*XU5)
    if d is None:
        print("  ! 08 atlandı")
        return
    a = dilim(d, 3048, 33)      # 14 Tem 10:20 → 13:00 · bant içinde büyük bar
    b = dilim(d, 520, 30)       # 8 Haz 09:50 → 12:15 · trend içinde büyük bar
    ia, ib = 26, 16
    gov_a, gov_b = float(a.c[ia] - a.o[ia]), float(b.c[ib] - b.o[ib])

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.10, subplot_titles=(
        "Panel 1 — yatay bantta büyük boğa trend barı: beş barda tamamen geri emiliyor",
        "Panel 2 — boğa trendinde neredeyse aynı boydaki bar: hareket devam ediyor"))

    # --- panel 1
    fig.add_trace(mumlar(a, ad="XU030 5dk", hover=hover(a)), row=1, col=1)
    ema_ciz(fig, a, 20, renk=GRI, row=1, col=1, ad="20 bar EMA")
    ust_a, alt_a = float(a.h[3:26].max()), float(a.l[3:26].min())
    kutu(fig, 2.5, 25.5, alt_a, ust_a, GRI, a=0.09, cizgi=1.1, row=1, col=1)
    yatay(fig, ust_a, 2.5, len(a) - 1, renk=GRI, dash="dash", w=1.3, row=1, col=1)
    yatay(fig, alt_a, 2.5, len(a) - 1, renk=GRI, dash="dash", w=1.3, row=1, col=1)
    pay = (a.h.max() - a.l.min()) * 0.025
    not_(fig, 7, ust_a, f"bant tavanı {ust_a:.0f}", renk=GRI, ok=False, boyut=10,
         yanchor="bottom", row=1, col=1)
    not_(fig, 7, alt_a, f"bant tabanı {alt_a:.0f} · yükseklik {ust_a-alt_a:.0f} puan",
         renk=GRI, ok=False, boyut=10, yanchor="top", row=1, col=1)
    kutu(fig, ia - 0.45, ia + 0.45, a.l[ia], a.h[ia], ALTIN, a=0.22, cizgi=1.4, row=1, col=1)
    not_(fig, ia, a.h[ia] + pay, f"<b>büyük boğa trend barı</b> — gövde {gov_a:+.0f} puan "
         f"(menzil {a.h[ia]-a.l[ia]:.0f}); tavanın {a.c[ia]-ust_a:+.0f} puan üstünde kapandı",
         renk=ALTIN, ay=-32, boyut=10, row=1, col=1)
    j_a = int(a.l[ia + 1:].idxmin())
    dip_a = float(a.l[j_a])
    not_(fig, j_a, dip_a - pay,
         f"{j_a-ia} bar sonra {dip_a:.0f} — bar tamamen yutuldu ({dip_a - a.c[ia]:+.0f} puan) "
         "ve fiyat bandın da altında", renk=TURUNCU, ay=32, boyut=10, row=1, col=1)
    cizgi(fig, ia, a.c[ia], j_a, dip_a, renk=TURUNCU, dash="dot", w=1.6, row=1, col=1)
    zaman_ekseni(fig, a, adet=8, row=1, col=1)

    # --- panel 2
    fig.add_trace(mumlar(b, ad="XU030 5dk", hover=hover(b)), row=2, col=1)
    fig.data[-1].showlegend = False
    ema_ciz(fig, b, 20, renk=GRI, row=2, col=1)
    fig.data[-1].showlegend = False
    trend_cizgisi(fig, b, (6, 11), yon="bull", uzat=22, renk=TEAL, dash="dash", w=1.3,
                  row=2, col=1)
    payb = (b.h.max() - b.l.min()) * 0.025
    kutu(fig, ib - 0.45, ib + 0.45, b.l[ib], b.h[ib], ALTIN, a=0.22, cizgi=1.4, row=2, col=1)
    not_(fig, ib, b.l[ib] - payb, f"<b>büyük boğa trend barı</b> — gövde {gov_b:+.0f} puan "
         f"(menzil {b.h[ib]-b.l[ib]:.0f})", renk=ALTIN, ay=40, boyut=10, row=2, col=1)
    j_b = int(b.h[ib + 1:ib + 7].idxmax())
    tepe_b = float(b.h[j_b])
    not_(fig, j_b, tepe_b + payb,
         f"{j_b-ib} bar sonra {tepe_b:.0f} — kapanışın {tepe_b - b.c[ib]:+.0f} puan ötesi",
         renk=TEAL, ay=-30, boyut=10, row=2, col=1)
    cizgi(fig, ib, b.c[ib], j_b, tepe_b, renk=TEAL, dash="dot", w=1.6, row=2, col=1)
    not_(fig, 2, b.h.max(), "bağlam: bar gelmeden önce zaten yükselen dipler ve "
         "yükselen tepeler dizisi var", renk=TEAL, ok=False, boyut=10, xanchor="left",
         yanchor="top", row=2, col=1)
    zaman_ekseni(fig, b, adet=8, row=2, col=1)

    lejant(fig, "incelenen trend barı", ALTIN)
    lejant(fig, "yatay bant gövdesi", GRI)
    duzen(fig, "Trend barı trend demek değildir: hükmü bağlam verir",
          f"XU030 5 dakikalık · iki bar neredeyse aynı boyda ({gov_a:+.0f} ve {gov_b:+.0f} puan) "
          "· pencereler indisle pinli (3048+33 ve 520+30) · müfredat USDTRY ister, "
          "önbellekteki USDTRY spot akışı bar okumaya elverişsiz",
          h=1020)
    x_basliklari(fig, 2)
    panel_basliklari(fig)
    kaydet(fig, "08_trend_bari_trend_degil", olcum=dict(
        enstruman="XU030.IS 5dk",
        panel1_pencere=[3048, 3080], panel1_tarih="2026-07-14 10:20–13:00",
        panel1_bar_govde=round(gov_a, 1), panel1_bar_menzil=round(float(a.h[ia] - a.l[ia]), 1),
        panel1_bant_ust=round(ust_a, 1), panel1_bant_alt=round(alt_a, 1),
        panel1_sonraki_dip=round(dip_a, 1), panel1_geri_emilim=round(dip_a - float(a.c[ia]), 1),
        panel1_kac_bar_sonra=j_a - ia,
        panel2_pencere=[520, 549], panel2_tarih="2026-06-08 09:50–12:15",
        panel2_bar_govde=round(gov_b, 1), panel2_bar_menzil=round(float(b.h[ib] - b.l[ib]), 1),
        panel2_sonraki_tepe=round(tepe_b, 1), panel2_takip=round(tepe_b - float(b.c[ib]), 1),
        panel2_kac_bar_sonra=j_b - ib))


# ================================================================== 09
def f09_dort_sey():
    """Her trend barı dört şeydir: kırılım · spike · klimaks · boşluk — Ş · 2 panel."""
    p1 = [(99.4, 100.1, 98.9, 99.6), (99.6, 100.2, 99.0, 99.3), (99.3, 100.0, 98.8, 99.6),
          (100.0, 104.7, 99.8, 104.4),                       # BÜYÜK BAR
          (104.5, 105.4, 104.1, 105.1), (105.0, 105.9, 104.5, 105.6)]
    d1 = cerceve(p1)
    ONC_TEPE, GOVDE_TEPE = 100.2, 99.6

    fig = make_subplots(rows=2, cols=1, row_heights=[0.46, 0.54], vertical_spacing=0.13,
                        subplot_titles=(
                            "Panel 1 — tek bir boğa trend barı, dört farklı adla",
                            "Panel 2 — aynı bar üç bağlamda: hangisi olduğunu bağlam söyler"))
    fig.add_trace(mumlar(d1, ad="bar"), row=1, col=1)
    yatay(fig, ONC_TEPE, -0.5, 5.6, renk=GRI, dash="dash", w=1.2, row=1, col=1)
    not_(fig, 5.65, ONC_TEPE, f"önceki üç barın tepesi {ONC_TEPE}", renk=GRI, ok=False,
         boyut=9.5, xanchor="left", row=1, col=1)
    kutu(fig, 2.55, 3.45, d1.l[3], d1.h[3], ALTIN, a=0.18, cizgi=1.4, row=1, col=1)
    kutu(fig, 1.58, 3.45, GOVDE_TEPE, 100.0, MOR, a=0.35, cizgi=1.0, row=1, col=1)

    etiketler = [
        ("<b>1 · KIRILIM</b><br>önceki üç barın tepesini aştı<br>ve ötesinde kapandı",
         -1.2, 103.9, TEAL),
        ("<b>2 · SPIKE</b><br>tek barlık ivme: gövde menzilin<br>%94'ü, içeride geri çekilme yok",
         -1.2, 101.3, ALTIN),
        ("<b>3 · KLİMAKS</b><br>bu boydaki bir bar aşırılıktır: karşı taraf<br>"
         "tükendi, yeni alıcı en pahalı yerden alıyor", 6.0, 103.9, TURUNCU),
        (f"<b>4 · BOŞLUK</b><br>gövde boşluğu: açılışı (100,0) bir önceki<br>"
         f"barın gövde tepesinin ({GOVDE_TEPE}) üstünde", 6.0, 101.3, MOR),
    ]
    for metin, x, y, renk in etiketler:
        not_(fig, x, y, metin, renk=renk, ok=False, boyut=9.5,
             xanchor="left" if x < 0 else "right", row=1, col=1)
        cizgi(fig, x + (1.1 if x < 0 else -1.1), y, 2.55 if x < 0 else 3.45,
              (d1.h[3] + d1.l[3]) / 2, renk=rgba(renk, 0.55), dash="dot", w=1.2, row=1, col=1)
    # ölçü çubukları: gövde ve menzil
    cizgi(fig, 3.62, float(d1.o[3]), 3.62, float(d1.c[3]), renk=MOR, w=3.0, row=1, col=1)
    not_(fig, 3.74, (float(d1.o[3]) + float(d1.c[3])) / 2,
         f"gövde {float(d1.c[3]-d1.o[3]):.1f}", renk=MOR, ok=False, boyut=9, xanchor="left",
         row=1, col=1)
    cizgi(fig, 4.28, float(d1.l[3]), 4.28, float(d1.h[3]), renk=GRI, w=1.8, row=1, col=1)
    not_(fig, 4.40, (float(d1.l[3]) + float(d1.h[3])) / 2,
         f"menzil {float(d1.h[3]-d1.l[3]):.1f}", renk=GRI, ok=False, boyut=9, xanchor="left",
         row=1, col=1)
    fig.update_yaxes(range=[98.2, 106.6], row=1, col=1)
    fig.update_xaxes(range=[-3.4, 9.6], showticklabels=False, row=1, col=1)

    buyuk = (0.0, 4.7, -0.2, 4.4)

    def baglam(oncesi, sonrasi):
        seri = list(oncesi)
        taban = seri[-1][3]
        seri.append(tuple(taban + v for v in buyuk))
        taban2 = seri[-1][3]
        for x in sonrasi:
            seri.append(tuple(taban2 + v for v in x))
        return merkezle(seri)

    a_onc = [(99.6, 100.4, 98.9, 99.2), (99.2, 100.3, 98.8, 100.0), (100.0, 100.5, 99.1, 99.4),
             (99.4, 100.4, 98.9, 99.9), (99.9, 100.4, 99.0, 99.5), (99.5, 100.2, 98.9, 100.0)]
    a_son = [(0.3, 1.9, 0.0, 1.6), (1.7, 3.4, 1.3, 3.1), (3.2, 4.4, 2.6, 4.1),
             (4.2, 5.6, 3.6, 5.3), (5.4, 6.2, 4.6, 5.0), (5.1, 6.9, 4.8, 6.6)]
    b_onc = [(94.0, 95.2, 93.6, 95.0), (95.1, 96.4, 94.7, 96.1), (96.2, 97.0, 95.5, 96.0),
             (96.0, 97.6, 95.6, 97.3), (97.3, 98.6, 96.9, 98.3), (98.4, 99.6, 97.8, 99.2)]
    b_son = [(0.2, 1.4, -0.4, 1.0), (1.1, 2.0, 0.5, 1.7), (1.6, 3.1, 1.2, 2.9),
             (3.0, 4.2, 2.5, 3.9), (3.8, 4.6, 2.9, 3.3), (3.4, 5.1, 3.0, 4.8)]
    c_onc = [(88.0, 90.0, 87.6, 89.6), (89.7, 92.0, 89.3, 91.7), (91.8, 94.4, 91.4, 94.1),
             (94.2, 96.8, 93.8, 96.4), (96.5, 99.0, 96.0, 98.7), (98.8, 100.2, 98.2, 99.9)]
    c_son = [(0.1, 0.6, -2.4, -2.0), (-2.1, -1.6, -4.6, -4.2), (-4.3, -3.4, -6.6, -6.2),
             (-6.3, -5.4, -8.2, -7.8), (-7.9, -6.8, -9.4, -9.0), (-9.1, -8.0, -11.0, -10.6)]

    segmentler = [
        ("A", "Dar bandın kırılımı", "bar = <b>KIRILIM</b> → yeni trend başlıyor", TEAL,
         baglam(a_onc, a_son)),
        ("B", "Trendin ortası", "bar = <b>SPIKE</b> + ölçüm boşluğu → trend sürüyor", ALTIN,
         baglam(b_onc, b_son)),
        ("C", "Uzun bir yükselişin sonu", "bar = <b>KLİMAKS</b> → iki bacaklı düzeltme", TURUNCU,
         baglam(c_onc, c_son)),
    ]
    barlar, ayrac, konum = [], [], []
    x = 0
    for i, (_, _, _, _, seri) in enumerate(segmentler):
        if i:
            barlar.append(None)
            ayrac.append(x - 0.5)
            x += 1
        konum.append((x, x + 6, x + len(seri) - 1))
        barlar.extend(seri)
        x += len(seri)
    d2 = cerceve(barlar)
    fig.add_trace(mumlar(d2, ad="bağlam"), row=2, col=1)
    ust = float(d2.h.max())
    for (harf, ad, sonuc, renk, _), (x0, xb, x1) in zip(segmentler, konum):
        kutu(fig, xb - 0.45, xb + 0.45, d2.l[xb], d2.h[xb], renk, a=0.22, cizgi=1.4,
             row=2, col=1)
        not_(fig, (x0 + x1) / 2, ust + 2.4, f"<b>{harf} · {ad}</b><br>{sonuc}", renk=renk,
             ok=False, boyut=9.5, row=2, col=1)
        not_(fig, xb, d2.l[xb] - 0.7, "aynı bar", renk=renk, ay=28, boyut=9, row=2, col=1)
    for xa in ayrac:
        cizgi(fig, xa, float(d2.l.min()) - 3, xa, ust + 4.6, renk=CIZGI, dash="dot", w=1.0,
              row=2, col=1)
    fig.update_yaxes(range=[float(d2.l.min()) - 3.6, ust + 5.6], row=2, col=1)

    duzen(fig, "Her trend barı aynı anda dört şeydir",
          "kırılım · spike · klimaks · boşluk — dördü de doğrudur; hangisinin işe yarayacağını "
          "barın kendisi değil, solundaki ekran söyler",
          h=1020, sematik=True)
    x_basliklari(fig, 2, "")
    panel_basliklari(fig)
    kaydet(fig, "09_trend_bari_dort_sey", olcum=dict(
        bar_govde=round(float(d1.c[3] - d1.o[3]), 2),
        bar_menzil=round(float(d1.h[3] - d1.l[3]), 2),
        govde_orani_pct=round(float(d1.c[3] - d1.o[3]) / float(d1.h[3] - d1.l[3]) * 100, 1),
        onceki_uc_bar_tepesi=ONC_TEPE, onceki_govde_tepesi=GOVDE_TEPE,
        govde_boslugu=round(float(d1.o[3]) - GOVDE_TEPE, 2),
        baglam_sayisi=3,
        baglamlar=["dar bant kırılımı", "trendin ortası", "uzun bir yükselişin sonu"]))


# ================================================================== 10
def f10_doji():
    """Doji = tek barlık yatay bant — Ş · 2 panel."""
    komsu = [(97.4, 98.2, 97.1, 98.0), (98.0, 98.8, 97.6, 98.5), (98.5, 99.0, 98.0, 98.6),
             (98.6, 99.4, 98.1, 99.2), (99.2, 100.3, 98.9, 100.1), (100.1, 100.9, 99.6, 100.4),
             (100.4, 101.0, 99.9, 100.1),
             (100.1, 103.5, 96.5, 99.9),                    # DOJİ
             (99.9, 100.8, 99.2, 100.5), (100.5, 101.2, 99.8, 100.0),
             (100.0, 100.6, 99.1, 99.4), (99.4, 100.2, 98.7, 99.9),
             (99.9, 100.7, 99.5, 100.5), (100.5, 101.4, 100.2, 101.1)]
    d1 = cerceve(komsu)
    D = 7
    H, L, O, C = float(d1.h[D]), float(d1.l[D]), float(d1.o[D]), float(d1.c[D])

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.125, subplot_titles=(
        "Panel 1 — büyük doji: menzil geniş, gövde yok",
        "Panel 2 — aynı barın alt zaman dilimindeki açılımı: bir yatay bant"))
    fig.add_trace(mumlar(d1, ad="bar"), row=1, col=1)
    SON1 = len(d1) - 0.4
    kutu(fig, D - 0.45, D + 0.45, L, H, ALTIN, a=0.14, cizgi=1.4, row=1, col=1)
    yatay(fig, H, 0, SON1, renk=GRI, dash="dash", w=1.2, row=1, col=1)
    yatay(fig, L, 0, SON1, renk=GRI, dash="dash", w=1.2, row=1, col=1)
    yatay(fig, O, D - 0.9, D + 0.9, renk=MAVI, dash="dot", w=1.4, row=1, col=1)
    not_(fig, SON1 + 0.15, H, f"yüksek {H:.1f}", renk=GRI, ok=False, boyut=10, xanchor="left",
         row=1, col=1)
    not_(fig, SON1 + 0.15, L, f"alçak {L:.1f}", renk=GRI, ok=False, boyut=10, xanchor="left",
         row=1, col=1)
    ort_menzil = float((d1.h - d1.l).drop(index=D).mean())
    not_(fig, D, H + 0.3, f"<b>doji</b> — menzil {H-L:.1f} (komşuların "
         f"{(H-L)/ort_menzil:.1f} katı), gövde {abs(C-O):.1f} "
         f"(menzilin %{abs(C-O)/(H-L)*100:.0f}'i)", renk=ALTIN, ay=-32, boyut=10, row=1, col=1)
    cizgi(fig, D + 0.62, L, D + 0.62, H, renk=GRI, w=1.8, row=1, col=1)
    cizgi(fig, D + 0.62, min(O, C), D + 0.62, max(O, C), renk=MOR, w=3.4, row=1, col=1)
    not_(fig, D + 0.78, (H + L) / 2, f"menzil {H-L:.1f}<br><span style='color:#6d28d9'>"
         f"gövde {abs(C-O):.1f}</span>", renk=GRI, ok=False, boyut=9, xanchor="left",
         row=1, col=1)
    not_(fig, 0.2, L + 0.4, f"komşu barların ortalama menzili {ort_menzil:.1f}", renk=GRI,
         ok=False, boyut=9, xanchor="left", row=1, col=1)
    not_(fig, SON1 + 0.15, (H + L) / 2 - 1.0, "Boğalar da ayılar da<br>bu barı kazanamadı:<br>"
         "bar bittiğinde fiyat<br>başladığı yerde.", renk=MUREKKEP, ok=False, boyut=9.5,
         xanchor="left", row=1, col=1)
    fig.update_yaxes(range=[L - 1.5, H + 1.9], row=1, col=1)
    fig.update_xaxes(range=[-0.6, len(d1) + 4.4], showticklabels=False, row=1, col=1)

    ic = [(100.1, 100.9, 99.6, 100.7), (100.7, 101.8, 100.5, 101.6),
          (101.6, 103.5, 101.4, 102.9),                        # tepe testi (H)
          (102.9, 103.2, 101.6, 101.8), (101.8, 102.2, 100.4, 100.6),
          (100.6, 101.0, 99.2, 99.4), (99.4, 99.8, 97.9, 98.1),
          (98.1, 98.6, 96.5, 96.9),                            # dip testi (L)
          (96.9, 98.4, 96.7, 98.2), (98.2, 99.6, 98.0, 99.4),
          (99.4, 100.5, 99.1, 100.2), (100.2, 101.4, 100.0, 101.1),
          (101.1, 101.6, 100.2, 100.4), (100.4, 100.8, 99.4, 99.6),
          (99.6, 100.6, 99.3, 100.4), (100.4, 101.2, 100.1, 100.9),
          (100.9, 101.3, 99.8, 100.0), (100.0, 100.4, 99.1, 99.3),
          (99.3, 100.1, 99.0, 99.8), (99.8, 100.3, 99.5, 100.1),
          (100.1, 100.5, 99.6, 99.9)]
    d2 = cerceve(ic)
    fig.add_trace(mumlar(d2, ad="alt zaman dilimi"), row=2, col=1)
    kutu(fig, -0.5, len(d2) - 0.5, L, H, GRI, a=0.09, cizgi=1.2, row=2, col=1)
    yatay(fig, H, -0.5, len(d2) + 0.4, renk=GRI, dash="dash", w=1.3, row=2, col=1)
    yatay(fig, L, -0.5, len(d2) + 0.4, renk=GRI, dash="dash", w=1.3, row=2, col=1)
    not_(fig, len(d2) + 0.5, H, f"dojinin yükseği {H:.1f}<br>= bandın tavanı", renk=GRI,
         ok=False, boyut=10, xanchor="left", row=2, col=1)
    not_(fig, len(d2) + 0.5, L, f"dojinin alçağı {L:.1f}<br>= bandın tabanı", renk=GRI,
         ok=False, boyut=10, xanchor="left", row=2, col=1)
    kutu(fig, 1.55, 2.45, d2.l[2], d2.h[2], TURUNCU, a=0.20, cizgi=1.2, row=2, col=1)
    not_(fig, 2, d2.h[2] + 0.2, "tavan denemesi başarısız", renk=TURUNCU, ay=-26, boyut=9.5,
         row=2, col=1)
    kutu(fig, 6.55, 7.45, d2.l[7], d2.h[7], TURUNCU, a=0.20, cizgi=1.2, row=2, col=1)
    not_(fig, 7, d2.l[7] - 0.2, "taban denemesi başarısız", renk=TURUNCU, ay=28, boyut=9.5,
         row=2, col=1)
    not_(fig, 0, O, f"açılış {O:.1f}", renk=MAVI, ay=-26, boyut=9.5, row=2, col=1)
    not_(fig, len(d2) - 1, C, f"kapanış {C:.1f}", renk=MAVI, ay=26, boyut=9.5, row=2, col=1)
    cizgi(fig, 0, O, 2, H, renk=TEAL, dash="dot", w=1.6, row=2, col=1)
    cizgi(fig, 2, H, 7, L, renk=BORDO, dash="dot", w=1.6, row=2, col=1)
    cizgi(fig, 7, L, 11, 101.1, renk=TEAL, dash="dot", w=1.6, row=2, col=1)
    not_(fig, 1.0, 102.6, "bacak 1 ↑", renk=TEAL, ok=False, boyut=9, row=2, col=1)
    not_(fig, 4.5, 100.4, "bacak 2 ↓", renk=BORDO, ok=False, boyut=9, row=2, col=1)
    not_(fig, 9.2, 98.4, "bacak 3 ↑", renk=TEAL, ok=False, boyut=9, row=2, col=1)
    kutu(fig, 10.5, len(d2) - 0.5, 99.0, 101.4, GRI, a=0.14, cizgi=1.1, row=2, col=1)
    not_(fig, 15.5, 101.5, "son bacaktan sonra uzlaşma:<br>bar açıldığı yere dönüyor",
         renk=GRI, ok=False, boyut=9, row=2, col=1)
    not_(fig, 11.6, L + 0.45, "Üst zaman diliminde tek bar; burada iki başarısız kırılım, "
         "üç bacak ve bir uzlaşma.", renk=MUREKKEP, ok=False, boyut=9.5, xanchor="right",
         row=2, col=1)
    fig.update_yaxes(range=[L - 1.3, H + 1.3], row=2, col=1)
    fig.update_xaxes(range=[-1.0, len(d2) + 4.4], showticklabels=False, row=2, col=1)

    duzen(fig, "Doji tek barlık bir yatay banttır",
          "alt zaman dilimi açılımı şematiktir (önbellekte 1 dakikalık seri yok) — "
          "geometri dojinin dört fiyatına sadık kurulmuştur",
          h=1000, sematik=True)
    x_basliklari(fig, 2, "")
    panel_basliklari(fig)
    kaydet(fig, "10_doji_yatay_bant", olcum=dict(
        doji_acilis=O, doji_yuksek=H, doji_alcak=L, doji_kapanis=C,
        menzil=round(H - L, 2), govde=round(abs(C - O), 2),
        govde_orani_pct=round(abs(C - O) / (H - L) * 100, 1),
        komsu_ort_menzil=round(ort_menzil, 2),
        menzil_kati=round((H - L) / ort_menzil, 2),
        alt_bar_sayisi=len(d2), alt_basarisiz_kirilim=2, alt_bacak_sayisi=3))


# ================================================================== 11
def f11_duraklama_mikro_gap():
    """Duraklama barı ve mikro ölçüm boşluğu — Ş · 1 panel."""
    barlar = [
        (95.8, 96.1, 95.1, 95.3), (95.3, 96.0, 95.0, 95.8), (95.8, 96.2, 95.3, 95.5),
        (95.5, 95.9, 94.8, 95.0),
        (94.9, 95.6, 94.6, 95.4), (95.4, 95.8, 95.0, 95.2), (95.2, 95.9, 94.9, 95.7),
        (95.6, 96.2, 95.2, 96.0), (96.0, 96.4, 95.6, 95.9), (95.9, 96.3, 95.5, 96.2),
        (96.3, 97.6, 96.1, 97.5),                     # spike 1
        (97.6, 99.5, 97.4, 99.3),                     # spike 2
        (99.4, 101.9, 99.2, 101.8),                   # spike 3 → yüksek 101,9
        (102.0, 103.4, 101.8, 102.4),                 # DURAKLAMA BARI 1
        (103.4, 105.4, 103.3, 105.2),                 # spike 4 → alçak 103,3
        (105.3, 107.0, 105.1, 106.8),
        (106.9, 108.4, 106.6, 108.2),                 # spike 6 → yüksek 108,4
        (108.4, 109.6, 108.2, 108.7),                 # DURAKLAMA BARI 2
        (109.7, 111.4, 109.5, 111.2),                 # spike 7 → alçak 109,5
        (111.3, 112.6, 111.0, 112.4),
    ]
    d = cerceve(barlar)
    SPIKE0 = 10
    P, P2 = SPIKE0 + 3, SPIKE0 + 7
    g0, g1 = float(d.h[P - 1]), float(d.l[P + 1])
    h0, h1 = float(d.h[P2 - 1]), float(d.l[P2 + 1])
    bosluk, bosluk2 = g1 - g0, h1 - h0
    orta, orta2 = (g0 + g1) / 2, (h0 + h1) / 2
    hareket_bas = float(d.l[SPIKE0 - 1])
    hedef = orta + (orta - hareket_bas)
    SAG = len(d) - 0.2

    fig = go.Figure()
    fig.add_trace(mumlar(d, ad="bar", hover=[f"bar {i}" for i in range(len(d))]))
    on_ust, on_alt = float(d.h[:SPIKE0].max()), float(d.l[:SPIKE0].min())
    kutu(fig, -0.5, SPIKE0 - 0.55, on_alt, on_ust, GRI, a=0.10, cizgi=1.1)
    yatay(fig, on_ust, -0.5, SPIKE0 + 1.4, renk=GRI, dash="dash", w=1.2)
    not_(fig, -0.3, on_alt, f"spike öncesi dar bant: {SPIKE0} bar, yükseklik "
         f"{on_ust-on_alt:.1f} birim<br>(tavanı {on_ust:.1f}) — spike bu bandın kırılımıdır",
         renk=GRI, ok=False, boyut=9, xanchor="left", yanchor="top")
    kutu(fig, SPIKE0 - 0.45, len(d) - 0.55, float(d.l[SPIKE0]) - 0.3,
         float(d.h[len(d) - 1]) + 0.3, TEAL, a=0.05, cizgi=1.0, dash="dot")
    not_(fig, SPIKE0 + 1.2, float(d.l[SPIKE0]) - 0.6,
         f"spike ({len(d)-SPIKE0} bar, hiç geri çekilme yok)", renk=TEAL, ok=False,
         boyut=10, yanchor="top")
    # gövde boşlukları: ardışık gövdeler arasında kalan boşluklar (B1 kaydı)
    govde_bosluklari = []
    for i in range(SPIKE0 + 1, len(d)):
        onc_ust = max(float(d.o[i - 1]), float(d.c[i - 1]))
        bu_alt = min(float(d.o[i]), float(d.c[i]))
        if bu_alt > onc_ust + 0.05:
            govde_bosluklari.append((i, onc_ust, bu_alt))
    en_buyuk = sorted(govde_bosluklari, key=lambda t: t[2] - t[1], reverse=True)[:2]
    for i, y0, y1 in en_buyuk:
        kutu(fig, i - 0.72, i - 0.18, y0, y1, TEAL, a=0.40, cizgi=0.8)
    if en_buyuk:
        i, y0, y1 = en_buyuk[0]
        not_(fig, i - 0.45, (y0 + y1) / 2, "<b>gövde boşluğu</b> — ardışık iki gövde "
             f"arasında {y1-y0:.1f} birimlik boşluk<br>(spike boyunca "
             f"{len(govde_bosluklari)} kez oluşuyor; en büyük ikisi işaretli)",
             renk=TEAL, ax=-118, ay=78, boyut=9.5)

    # --- birinci duraklama barı ve boşluğu
    kutu(fig, P - 1.48, P + 1.48, g0, g1, ALTIN, a=0.28, cizgi=1.3)
    yatay(fig, g0, P - 1.48, SAG, renk=ALTIN, dash="dash", w=1.3)
    yatay(fig, g1, P - 1.48, SAG, renk=ALTIN, dash="dash", w=1.3)
    not_(fig, P - 2.5, orta, f"<b>mikro ölçüm boşluğu 1</b> — {bosluk:.1f} birim<br>"
         f"öncekinin yükseği {g0:.1f} · sonrakinin alçağı {g1:.1f}<br>"
         f"ortası {orta:.2f} — duraklama barının iki komşusu hiç örtüşmüyor",
         renk=ALTIN, ok=False, boyut=9.5, xanchor="right")
    kutu(fig, P - 0.45, P + 0.45, d.l[P], d.h[P], MOR, a=0.20, cizgi=1.4)
    not_(fig, P, float(d.h[P]) + 0.4, f"<b>duraklama barı 1</b> — gövde "
         f"{abs(float(d.c[P]-d.o[P])):.1f}, menzil {float(d.h[P]-d.l[P]):.1f}<br>"
         "spike duruyor ama geri çekilme YOK", renk=MOR, ay=-40, boyut=10)

    # --- ikinci duraklama barı ve boşluğu
    kutu(fig, P2 - 1.48, P2 + 1.48, h0, h1, ALTIN, a=0.28, cizgi=1.3)
    kutu(fig, P2 - 0.45, P2 + 0.45, d.l[P2], d.h[P2], MOR, a=0.20, cizgi=1.4)
    not_(fig, P2 - 4.6, orta2 + 3.9, f"<b>duraklama barı 2</b> ve <b>mikro boşluk 2</b> "
         f"({h0:.1f} → {h1:.1f}, {bosluk2:.1f} birim)<br>aynı spike içinde kalıp tekrar ediyor",
         renk=MOR, ok=False, boyut=9.5, xanchor="left")

    yatay(fig, orta, P - 1.48, SAG, renk=MOR, dash="dot", w=1.2)
    yatay(fig, hareket_bas, SPIKE0 - 1, SAG, renk=GRI, dash="dot", w=1.2)
    yatay(fig, hedef, P + 1, SAG, renk=MOR, dash="dash", w=1.6)
    cizgi(fig, SAG + 5.6, hareket_bas, SAG + 5.6, orta, renk=GRI, w=3.0)
    cizgi(fig, SAG + 5.6, orta, SAG + 5.6, hedef, renk=MOR, w=3.0)
    not_(fig, SAG + 5.85, (hareket_bas + orta) / 2, f"1. yarı<br>{orta-hareket_bas:.2f}",
         renk=GRI, ok=False, boyut=9, xanchor="left")
    not_(fig, SAG + 5.85, (orta + hedef) / 2, f"2. yarı<br>{hedef-orta:.2f}",
         renk=MOR, ok=False, boyut=9, xanchor="left")
    not_(fig, SAG + 0.15, hareket_bas, f"hareketin başı {hareket_bas:.1f}", renk=GRI,
         ok=False, boyut=9, xanchor="left")
    # duraklama barı aynı zamanda bir sinyal barıdır: spike yönünde stop emriyle giriş
    sonuc = islem(fig, d, sinyal=P, yon="bull", hedefler=(hedef,),
                  etiketler=("ölçülmüş hareket hedefi",), x_son=SAG, ondalik=1,
                  r_goster=True)
    not_(fig, -3.1, orta2 + 1.8, "Duraklama barı aynı zamanda bir sinyal barıdır: "
         "spike yönünde barın bir tick üstünden alım,<br>stop barın bir tick altında — "
         f"risk {sonuc['risk']:.1f} birim, ölçülmüş hareket hedefi {sonuc['r'][0]:.1f}R.",
         renk=MAVI, ok=False, boyut=9.5, xanchor="left")
    not_(fig, -3.1, float(d.h.max()) + 0.4, "'Ölçüm' boşluğu adını buradan alır: hareket, "
         "boşluğun ortasında<br>yarılanmış sayılır. Aynı spike içinde birden çok mikro "
         "boşluk çıkabilir.", renk=MUREKKEP, ok=False, boyut=10, xanchor="left")
    # iç içe ölçüm: ikinci boşluk, birinci boşluktan sonraki bacağı ikiye böler
    hedef2 = orta2 + (orta2 - orta)
    yatay(fig, orta2, P2 - 1.48, SAG, renk=TEAL, dash="dot", w=1.2)
    yatay(fig, hedef2, P2 + 1, SAG, renk=TEAL, dash="dash", w=1.5)
    not_(fig, SAG + 0.15, hedef2, f"iç içe ölçüm hedefi {hedef2:.2f}<br>"
         "(boşluk 2, birinci boşluktan sonraki bacağı ikiye böler)", renk=TEAL, ok=False,
         boyut=9, xanchor="left")

    # spike tanısı: her barın dibi bir öncekinin üstünde → hiç geri çekilme yok
    yukselen = [i for i in range(SPIKE0, len(d)) if float(d.l[i]) > float(d.l[i - 1])]
    fig.add_trace(go.Scatter(
        x=yukselen, y=[float(d.l[i]) - 0.30 for i in yukselen], mode="markers",
        name=f"dibi bir öncekinin üstünde olan bar ({len(yukselen)}/{len(d)-SPIKE0}) — "
             "spike boyunca hiç geri çekilme yok",
        marker=dict(symbol="triangle-up", size=8, color=TEAL,
                    line=dict(color=TEAL, width=1))))
    lejant(fig, "mikro ölçüm boşluğu (komşular örtüşmüyor)", ALTIN, a=0.28)
    lejant(fig, "duraklama barı", MOR, a=0.20)
    lejant(fig, "gövde boşluğu (ardışık gövdeler arası)", TEAL, a=0.40)
    fig.update_yaxes(range=[hareket_bas - 2.0, hedef2 + 1.6])
    fig.update_xaxes(range=[-3.3, len(d) + 11.4], showticklabels=False, title_text="")
    duzen(fig, "Duraklama barı ve mikro ölçüm boşluğu",
          "spike içinde bir bar durur ama geri çekilmez; komşuları örtüşmez ve arada bir boşluk kalır",
          x_baslik="", h=720, sematik=True)
    kaydet(fig, "11_duraklama_mikro_gap", olcum=dict(
        spike_bar_sayisi=len(d) - SPIKE0, duraklama_bari_sayisi=2,
        on_bant_bar=SPIKE0, on_bant_tavan=round(on_ust, 2),
        on_bant_taban=round(on_alt, 2), on_bant_yukseklik=round(on_ust - on_alt, 2),
        govde_boslugu_sayisi=len(govde_bosluklari),
        dibi_yukselen_bar=len(yukselen),
        duraklama1_indis=P,
        duraklama1_govde=round(abs(float(d.c[P] - d.o[P])), 2),
        duraklama1_menzil=round(float(d.h[P] - d.l[P]), 2),
        bosluk1_alt=round(g0, 2), bosluk1_ust=round(g1, 2), bosluk1_boyu=round(bosluk, 2),
        bosluk1_ortasi=round(orta, 2),
        duraklama2_indis=P2,
        bosluk2_alt=round(h0, 2), bosluk2_ust=round(h1, 2), bosluk2_boyu=round(bosluk2, 2),
        bosluk2_ortasi=round(orta2, 2),
        hareket_basi=round(hareket_bas, 2),
        olculmus_hareket_hedefi=round(hedef, 2),
        ic_ice_olcum_hedefi=round(hedef2, 2),
        birinci_yari=round(orta - hareket_bas, 2), ikinci_yari=round(hedef - orta, 2),
        ulasilan_zirve=round(float(d.h.max()), 2),
        duraklama_girisi=round(sonuc["giris"], 2), duraklama_stopu=round(sonuc["stop"], 2),
        duraklama_riski_1R=round(sonuc["risk"], 2),
        duraklama_hedef_R=round(sonuc["r"][0], 2)))


# ================================================================== 12
def f12_klimaks_vakum():
    """Klimaks barı ve vakum — Ş · 2 panel."""
    MIKNATIS = 90.0
    p1 = [(101.8, 102.2, 100.9, 101.2), (101.2, 101.9, 100.6, 101.6),
          (101.6, 101.8, 100.4, 100.6), (100.6, 101.3, 100.1, 100.9),
          (100.9, 101.1, 100.0, 100.2),
          (100.2, 100.6, 99.2, 99.4), (99.4, 100.1, 98.7, 98.9), (98.9, 99.6, 98.4, 99.3),
          (99.3, 99.5, 98.0, 98.2), (98.2, 98.7, 97.5, 97.8), (97.8, 98.0, 96.8, 96.9),
          (96.9, 97.2, 96.3, 97.0), (97.0, 97.1, 95.6, 95.8),
          (95.8, 95.9, 94.1, 94.3), (94.3, 94.5, 92.4, 92.6),
          (92.6, 92.7, 91.0, 91.1), (91.1, 91.2, 90.1, 90.2)]
    d1 = cerceve(p1)
    VAKUM = 13
    normal_menzil = float((d1.h - d1.l)[:VAKUM].mean())
    vakum_menzil = float((d1.h - d1.l)[VAKUM:].mean())

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.125, subplot_titles=(
        "Panel 1 — vakum: alıcılar emirlerini çekiyor, fiyat mıknatısa emiliyor",
        "Panel 2 — mıknatısta klimaks barı ve agresif ters işlem"))
    fig.add_trace(mumlar(d1, ad="bar"), row=1, col=1)
    yatay(fig, MIKNATIS, -0.5, len(d1) + 0.4, renk=MOR, dash="dash", w=2.0, row=1, col=1)
    not_(fig, len(d1) + 0.5, MIKNATIS, "<b>mıknatıs 90,0</b><br>önceki dip + yuvarlak sayı",
         renk=MOR, ok=False, boyut=10, xanchor="left", row=1, col=1)
    yatay(fig, 96.0, -0.5, len(d1) + 0.4, renk=GRI, dash="dot", w=1.2, row=1, col=1)
    not_(fig, len(d1) + 0.5, 96.0, "vakumun başladığı yer 96,0", renk=GRI, ok=False,
         boyut=9.5, xanchor="left", row=1, col=1)
    kutu(fig, VAKUM - 0.6, len(d1) - 0.5, MIKNATIS - 0.4, 96.2, TURUNCU, a=0.10, cizgi=1.2,
         row=1, col=1)
    for i in range(VAKUM, len(d1)):
        kutu(fig, i - 0.45, i + 0.45, d1.l[i], d1.h[i], TURUNCU, a=0.16, cizgi=1.0,
             row=1, col=1)
    kutu(fig, -0.5, VAKUM - 0.6, 96.0, float(d1.h.max()), GRI, a=0.07, cizgi=1.0,
         row=1, col=1)
    not_(fig, 0.2, 99.0, f"normal ayı hareketi ({VAKUM} bar): ortalama menzil "
         f"{normal_menzil:.1f}<br>aralarda boğa barları ve küçük geri çekilmeler var",
         renk=GRI, ok=False, boyut=9.5, xanchor="left", row=1, col=1)
    not_(fig, len(d1) + 0.5, 94.4, f"<b>vakum bölgesi</b> ({len(d1)-VAKUM} bar)<br>"
         f"ortalama menzil {vakum_menzil:.1f} ({vakum_menzil/normal_menzil:.1f} kat)<br>"
         "üst üste kuyruksuz ayı barları<br>geri çekilme kalmadı", renk=TURUNCU, ok=False,
         boyut=9.5, xanchor="left", row=1, col=1)
    not_(fig, VAKUM - 0.9, 92.6, "Alıcı 'mıknatısa kadar bekleyeyim' diyor: emir defterinin<br>"
         "alış tarafı boşalıyor, satıcı az emirle çok yol alıyor.", renk=TURUNCU, ok=False,
         boyut=9.5, xanchor="right", row=1, col=1)
    fig.add_annotation(x=len(d1) - 0.6, y=MIKNATIS + 0.5, ax=VAKUM - 0.4, ay=95.6,
                       xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                       arrowhead=2, arrowsize=1.3, arrowwidth=2.0, arrowcolor=TURUNCU,
                       text="", row=1, col=1)
    fig.update_yaxes(range=[88.4, 103.4], row=1, col=1)
    fig.update_xaxes(range=[-0.8, len(d1) + 6.8], showticklabels=False, row=1, col=1)

    p2 = [(96.9, 97.2, 96.3, 97.0), (97.0, 97.1, 95.6, 95.8), (95.8, 95.9, 94.1, 94.3),
          (94.3, 94.5, 92.4, 92.6), (92.6, 92.7, 91.0, 91.1),
          (91.1, 91.2, 88.6, 88.8),                       # KLİMAKS BARI
          (88.8, 91.5, 88.5, 91.3),                       # DÖNÜŞ BARI (uzun alt kuyruk)
          (91.4, 92.6, 91.0, 92.4), (92.4, 93.8, 92.0, 93.6), (93.6, 94.4, 92.9, 94.1),
          (94.1, 95.6, 93.8, 95.4), (95.4, 96.6, 94.9, 96.4), (96.4, 97.4, 96.0, 97.2)]
    d2 = cerceve(p2)
    K, S = 5, 6
    fig.add_trace(mumlar(d2, ad="bar"), row=2, col=1)
    fig.data[-1].showlegend = False
    yatay(fig, MIKNATIS, -0.5, len(d2) + 0.4, renk=MOR, dash="dash", w=2.0, row=2, col=1)
    not_(fig, 0.2, MIKNATIS, "mıknatıs 90,0", renk=MOR, ok=False, boyut=10, xanchor="left",
         yanchor="top", row=2, col=1)
    kutu(fig, K - 0.45, K + 0.45, d2.l[K], d2.h[K], TURUNCU, a=0.20, cizgi=1.4, row=2, col=1)
    onceki_ort = float((d2.h - d2.l)[:K].mean())
    not_(fig, K, float(d2.l[K]) - 0.25, f"<b>klimaks barı</b> — menzil "
         f"{float(d2.h[K]-d2.l[K]):.1f} (öncekilerin {float(d2.h[K]-d2.l[K])/onceki_ort:.1f} "
         f"katı), mıknatısı {MIKNATIS-float(d2.l[K]):.1f} birim aştı", renk=TURUNCU, ay=38,
         boyut=10, row=2, col=1)
    not_(fig, S, float(d2.h[S]) + 0.25, "<b>dönüş barı</b> — uzun alt kuyruk: mıknatısta "
         "bekleyen agresif alıcılar<br>tek barda hem klimaks barını hem de öncesini geri aldı",
         renk=TEAL, ay=-34, boyut=10, row=2, col=1)
    sonuc = islem(fig, d2, sinyal=S, yon="bull",
                  hedefler=(94.3, 96.9),
                  etiketler=("hedef 1 — vakumun ortası", "hedef 2 — vakumun başı"),
                  row=2, col=1, x_son=len(d2) - 1, ondalik=1)
    not_(fig, 0.2, 88.6, "Klimaks dönüşünün bedeli: sinyal barı geniştir, bu yüzden 1R "
         f"büyüktür ({sonuc['risk']:.1f} birim).<br>Vakum simetriktir — emirler ne kadar "
         "hızlı çekildiyse mıknatısta o kadar hızlı geri gelir.", renk=MUREKKEP, ok=False,
         boyut=9.5, xanchor="left", row=2, col=1)
    fig.update_yaxes(range=[87.2, 99.4], row=2, col=1)
    fig.update_xaxes(range=[-0.8, len(d2) + 6.4], showticklabels=False, row=2, col=1)

    lejant(fig, "vakum / klimaks", TURUNCU)
    lejant_cizgi(fig, "mıknatıs seviyesi", MOR)
    duzen(fig, "Vakum etkisi: klimaks, karşı tarafın yokluğundan doğar",
          "karşı taraf emirlerini çeker → fiyat mıknatısa emilir → mıknatısta emirler "
          "toplu döner ve klimaks tersine çevrilir",
          h=1040, sematik=True)
    x_basliklari(fig, 2, "")
    panel_basliklari(fig)
    kaydet(fig, "12_klimaks_vakum", olcum=dict(
        miknatis=MIKNATIS,
        vakum_oncesi_bar=VAKUM, vakum_bar=len(d1) - VAKUM,
        vakum_oncesi_ort_menzil=round(normal_menzil, 2),
        vakum_ort_menzil=round(vakum_menzil, 2),
        vakum_menzil_kati=round(vakum_menzil / normal_menzil, 2),
        klimaks_menzil=round(float(d2.h[K] - d2.l[K]), 2),
        klimaks_asim=round(MIKNATIS - float(d2.l[K]), 2),
        donus_bari_alt_kuyruk=round(float(min(d2.o[S], d2.c[S]) - d2.l[S]), 2),
        giris=round(sonuc["giris"], 2), stop=round(sonuc["stop"], 2),
        risk_1R=round(sonuc["risk"], 2),
        hedefler=[94.3, 96.9], hedef_R=[round(r, 2) for r in sonuc["r"]]))


# ================================================================== main
def main():
    print("Brooks figürleri 01–12 (B0 çerçeve · B1 bar okuma)")
    for f in (f01_tayf, f02_uc_zaman_dilimi, f03_atalet, f04_esit_uzaklik,
              f05_bar_anatomisi, f06_govde_kapanis, f07_alim_baskisi,
              f08_trend_bari_trend_degil, f09_dort_sey, f10_doji,
              f11_duraklama_mikro_gap, f12_klimaks_vakum):
        f()
    defter_yaz()


if __name__ == "__main__":
    main()
