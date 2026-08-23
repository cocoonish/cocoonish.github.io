#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Al Brooks dersi — figür 30–45 (B4 yatay bant ailesi · B5 kırılım ve başarısız kırılım).

Numaralama MÜFREDAT.md sürüm 2, "# 3. GRAFİK LİSTESİ" tablosundan (94 satır).
Çizim dili brooks_ortak.py'den gelir; burada yalnızca figürlerin kendisi kurulur.

Gerçek veri figürlerinde pencere İNDİSLE pinlenir (dilim(df, bas, adet)); "son N bar"
yok. Şematik figürlerde barlar elle kurulur.

ENSTRÜMAN NOTU. Müfredat 33 · 38 · 43'te USDTRY 5dk istiyor. Önbellekteki USDTRY
5dk/15dk/1s serisi yfinance FX kotasyon artefaktı taşıyor: gövdeler ~0, her barda
aynı yere inen hayalet kuyruklar (ör. 45,97 kapanış — 45,89 dip, saatlerce). Bu seri
bar okuma dersine elverişli değil. Sentetik veriyi "gerçek" diye sunmamak için bu üç
figür önbellekteki gerçek yapıya sahip serilere taşındı ve altbaşlıkta belirtildi:
33 → ES=F 5dk · 38 → GC=F (XAUUSD ailesi) 5dk · 43 → XU100 5dk.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from brooks_ortak import (ALTIN, BORDO, CIZGI, GRI, KAGIT, MAVI, MOR, MUREKKEP, TEAL,
                          TURUNCU, YESIL, bar, bar_say, bar_etiketle, bosluk_isaretle,
                          cizgi, defter_yaz, df_yap, dilim, duzen, ema, ema_ciz, hover,
                          islem, kaydet, kutu, lejant, lejant_cizgi, make_subplots,
                          mumlar, not_, olculmus_hareket, rgba, swingler, yatay,
                          yukle, zaman_ekseni)

TIK = "✓"
CARPI = "✗"


# ------------------------------------------------------------------ ortak yardımcılar
def _panel_baslik(fig, metin, row, y=1.0):
    """Alt panelin kendi başlığı (make_subplots subplot_titles yerine — konumu net)."""
    eks = "" if row == 1 else str(row)
    fig.add_annotation(text=f"<b>{metin}</b>", xref=f"x{eks} domain", yref=f"y{eks} domain",
                       x=0, y=y, xanchor="left", yanchor="bottom", showarrow=False,
                       font=dict(size=12, color=MUREKKEP))


def puan_karti(fig, row, satirlar, sol_baslik="ölçüt", sag_baslik="durum"):
    """Bir alt panele onay/ret tablosu çizer. satirlar: [(metin, 'evet'|'hayir'|'yok')]."""
    n = len(satirlar)
    fig.update_xaxes(range=[0, 1], visible=False, row=row, col=1)
    fig.update_yaxes(range=[n + 0.9, -1.9], visible=False, row=row, col=1)
    not_(fig, 0.012, -0.85, f"<b>{sol_baslik}</b>", renk=MUREKKEP, ok=False, boyut=11,
         xanchor="left", row=row, col=1, arka=False)
    not_(fig, 0.965, -0.85, f"<b>{sag_baslik}</b>", renk=MUREKKEP, ok=False, boyut=11,
         xanchor="right", row=row, col=1, arka=False)
    for j, (metin, durum) in enumerate(satirlar):
        if j % 2 == 0:
            fig.add_shape(type="rect", x0=0, x1=1, y0=j - 0.45, y1=j + 0.45,
                          fillcolor=rgba(GRI, 0.07), line=dict(width=0), layer="below",
                          row=row, col=1)
        renk = {"evet": TEAL, "hayir": BORDO, "yok": GRI}[durum]
        isaret = {"evet": TIK, "hayir": CARPI, "yok": "—"}[durum]
        not_(fig, 0.012, j, f"{j+1}. {metin}", renk=MUREKKEP, ok=False, boyut=11,
             xanchor="left", row=row, col=1, arka=False)
        not_(fig, 0.965, j, f"<b>{isaret}</b>", renk=renk, ok=False, boyut=13,
             xanchor="right", row=row, col=1, arka=False)


def izgara(fig, row, basliklar, satirlar, x_konum):
    """Çok sütunlu metin ızgarası (giriş yolları karşılaştırması gibi)."""
    n = len(satirlar)
    fig.update_xaxes(range=[0, 1], visible=False, row=row, col=1)
    fig.update_yaxes(range=[n + 0.9, -1.2], visible=False, row=row, col=1)
    for x, b in zip(x_konum, basliklar):
        not_(fig, x, -0.7, f"<b>{b}</b>", renk=MUREKKEP, ok=False, boyut=11,
             xanchor="left", row=row, col=1, arka=False)
    for j, satir in enumerate(satirlar):
        if j % 2 == 0:
            fig.add_shape(type="rect", x0=0, x1=1, y0=j - 0.45, y1=j + 0.45,
                          fillcolor=rgba(GRI, 0.07), line=dict(width=0), layer="below",
                          row=row, col=1)
        for x, hucre in zip(x_konum, satir):
            not_(fig, x, j, hucre, renk=MUREKKEP, ok=False, boyut=11,
                 xanchor="left", row=row, col=1, arka=False)


def kapsa(fig, satirlar=2, pay=0.12, sag=0.0, sol=0.6):
    """Aralığı elle kilitler: veri + şekil + anotasyon hepsi çerçevenin içinde kalsın.

    Plotly'nin otomatik aralığı grafiğin dışına taşan etiketleri her zaman hesaba
    katmıyor; kırpılan bir etiket dersteki sayıyı görünmez yapar. Aralığı zaten elle
    verilmiş eksenlere dokunulmaz.
    """
    for row in range(1, satirlar + 1):
        eks = "" if row == 1 else str(row)
        ya, xa = f"y{eks}", f"x{eks}"
        y_eks, x_eks = fig.layout[f"yaxis{eks}"], fig.layout[f"xaxis{eks}"]
        ys, xs = [], []
        for tr in fig.data:
            if (tr.yaxis or "y") != ya:
                continue
            for alan in ("low", "high", "y"):
                v = getattr(tr, alan, None)
                if v is not None:
                    ys += [float(t) for t in v if t is not None]
            if getattr(tr, "x", None) is not None:
                xs += [float(t) for t in tr.x if isinstance(t, (int, float))]
        for sh in fig.layout.shapes:
            if (sh.yref or "y") == ya and sh.y0 is not None:
                ys += [float(sh.y0), float(sh.y1)]
            if (sh.xref or "x") == xa and isinstance(sh.x0, (int, float)):
                xs += [float(sh.x0), float(sh.x1)]
        for an in fig.layout.annotations:
            if (an.yref or "y") == ya and an.y is not None:
                ys.append(float(an.y))
            if (an.xref or "x") == xa and isinstance(an.x, (int, float)):
                xs.append(float(an.x))
        hedef = dict(row=row, col=1) if getattr(fig, "_grid_ref", None) else {}
        if ys and y_eks.range is None:
            lo, hi = min(ys), max(ys)
            d = (hi - lo) * pay or 1.0
            fig.update_yaxes(range=[lo - d, hi + d], **hedef)
        if xs and x_eks.range is None:
            lo, hi = min(xs), max(xs)
            fig.update_xaxes(range=[lo - sol, hi + sag], **hedef)


def _ortusme_orani(d):
    return float(np.mean([min(d.h[i], d.h[i - 1]) - max(d.l[i], d.l[i - 1]) >
                          0.5 * min(d.h[i] - d.l[i], d.h[i - 1] - d.l[i - 1])
                          for i in range(1, len(d))]))


def _doji_orani(d):
    return float(np.mean([abs(d.c[i] - d.o[i]) < 0.30 * (d.h[i] - d.l[i]) for i in range(len(d))]))


# ================================================================== 30 · bant tanı listesi
def f30_bant_tanisi():
    """G · XU030 5dk · 2 panel — bant günü + bandın 10 tanı ölçütü."""
    df = yukle("XU030.IS", "5m")
    if df is None:
        return
    GUN, BANT0 = 5329, 5356                      # 2026-08-18 seansı · bandın başladığı bar
    p1 = dilim(df, GUN, 97)
    p2 = dilim(df, 5352, 74)
    a1, a2 = BANT0 - GUN, BANT0 - 5352           # bandın panel içi başlangıçları

    ust = float(p1.h[a1:].max())
    alt = float(p1.l[a1:].min())
    yuk = ust - alt
    gun_net = abs(float(p1.c.iloc[-1] - p1.o.iloc[0]))
    gun_aralik = float(p1.h.max() - p1.l.min())

    e = ema(p2, 20)
    kesisme = int(sum(1 for i in range(a2 + 1, len(p2))
                      if (p2.c[i] - e[i]) * (p2.c[i - 1] - e[i - 1]) < 0))
    bant = p2.iloc[a2:].reset_index(drop=True)
    ovl, doji = _ortusme_orani(bant), _doji_orani(bant)

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.10,
                        row_heights=[0.44, 0.56])
    fig.add_trace(mumlar(p1, "XU030 5dk", hover=hover(p1)), row=1, col=1)
    kutu(fig, a1 - 0.5, len(p1) - 0.5, alt, ust, GRI, a=0.13, cizgi=1.2, row=1, col=1)
    yatay(fig, ust, a1 - 0.5, len(p1) - 0.5, renk=BORDO, w=1.4, row=1, col=1)
    yatay(fig, alt, a1 - 0.5, len(p1) - 0.5, renk=TEAL, w=1.4, row=1, col=1)
    not_(fig, a1 + 34, ust, f"bandın tavanı {ust:,.0f}", renk=BORDO, ok=False, boyut=10,
         yanchor="bottom", row=1, col=1)
    not_(fig, a1 + 60, alt, f"bandın tabanı {alt:,.0f}", renk=TEAL, ok=False, boyut=10,
         yanchor="top", row=1, col=1)
    not_(fig, 12, float(p1.l[8:18].min()), "sabah: atak ve dönüş<br>(gün burada yön arıyor)",
         renk=MUREKKEP, ax=-14, ay=52, row=1, col=1)
    not_(fig, a1 + 12, alt - yuk * 0.30,
         f"bandın içi: {len(p1) - a1} bar · gün net/aralık = %{100*gun_net/gun_aralik:.0f}",
         renk=MUREKKEP, ok=False, boyut=10, row=1, col=1)
    _panel_baslik(fig, "Panel 1 — bant günü: 27. bardan sonra fiyat aynı kutuda dönüyor", 1)

    # ---- panel 2: 10 tanı ölçütü
    fig.add_trace(mumlar(p2, "XU030 5dk (yakın)", hover=hover(p2)), row=2, col=1)
    ema_ciz(fig, p2, 20, renk=ALTIN, row=2, col=1, ad="20 bar EMA")
    yatay(fig, ust, a2 - 0.5, len(p2) - 0.5, renk=BORDO, w=1.3, row=2, col=1)
    yatay(fig, alt, a2 - 0.5, len(p2) - 0.5, renk=TEAL, w=1.3, row=2, col=1)

    o = yuk * 0.05
    isaretler = [
        (26, p2.l[26] - o, "① barlar büyük ölçüde örtüşüyor<br>"
                           f"(örtüşme oranı %{100*ovl:.0f})", MUREKKEP, 52),
        (34, p2.l[34] - o, f"② doji ve belirgin kuyruk bolluğu (%{100*doji:.0f} doji)",
         MUREKKEP, 96),
        (20, p2.h[20] + o, "③ tavanda başarısız kırılım", BORDO, -30),
        (37, p2.h[37] + o, "③ tavanda ikinci başarısız kırılım", BORDO, -62),
        (55, p2.l[55] - o, "④ tabanda aynı seviyeyi tutan destek", TEAL, 30),
        (54, p2.l[54] - o, "⑤ uçtaki trend barı geri emiliyor<br>(sonraki bar tümünü geri aldı)",
         TURUNCU, 62),
        (43, p2.h[43] + o, "⑦ iki bacaklı hareket (aşağı–yukarı–aşağı)", MUREKKEP, -34),
        (69, p2.h[69] + o, "⑧ salınım tepeleri aynı hizada", BORDO, -30),
    ]
    for i, y, metin, renk, ay in isaretler:
        ax = -24 if ay < 0 else 24
        if metin.startswith("⑤"):
            ax = 140
        not_(fig, i, y, metin, renk=renk, ax=ax, ay=ay, boyut=10, row=2, col=1)
    not_(fig, 1, float(bant.l.min()) + yuk * 0.10,
         f"⑥ 20 bar EMA yatay; fiyat onu {kesisme} kez kesiyor", renk=ALTIN, ok=False,
         boyut=10, xanchor="left", row=2, col=1)
    not_(fig, 1, float(bant.l.min()) + yuk * 0.02,
         "⑩ belirsizlik: bant boyu tek yönlü kanıt yok — 'aciliyet radarı' sessiz",
         renk=MUREKKEP, ok=False, boyut=10, xanchor="left", row=2, col=1)
    # ⑨ stop girişi kaybettirir: tavan kırılımının üstüne konan alış stopu
    giris9 = float(p2.h[20]) + yuk * 0.02
    yatay(fig, giris9, 20, len(p2) - 0.5, renk=MAVI, dash="solid", w=1.3, row=2, col=1)
    not_(fig, len(p2) - 0.4, giris9,
         f"⑨ tavanda stop alımı {giris9:,.0f} → 6 bar sonra {p2.c[26]:,.0f} (kayıp)",
         renk=MAVI, ok=False, boyut=10, xanchor="left", row=2, col=1)
    _panel_baslik(fig, "Panel 2 — aynı bandın on tanı ölçütü", 2)

    lejant(fig, "yatay bant", GRI, a=0.13)
    lejant_cizgi(fig, "bandın tavanı / tabanı", BORDO, dash="dash")
    duzen(fig, "Yatay bandın tanı listesi",
          "XU030 5dk · 2026-08-18 seansı · pencere indisle pinli (bar 5329–5425)", h=980)
    fig.update_xaxes(title_text="", row=1, col=1)
    zaman_ekseni(fig, p1, 8, "%H:%M", row=1, col=1)
    zaman_ekseni(fig, p2, 8, "%H:%M", row=2, col=1)
    kapsa(fig, 2, pay=0.16, sag=26.0)
    kaydet(fig, "30_bant_tanisi", olcum=dict(
        gun="2026-08-18", pencere_p1=[5329, 5425], pencere_p2=[5352, 5425],
        bant_tavani=round(ust, 2), bant_tabani=round(alt, 2), bant_yuksekligi=round(yuk, 2),
        bant_bar_sayisi=len(p1) - a1, gun_net=round(gun_net, 2), gun_araligi=round(gun_aralik, 2),
        gun_net_bolu_aralik=round(gun_net / gun_aralik, 3), ema_kesisme=kesisme,
        ortusme_orani=round(ovl, 3), doji_orani=round(doji, 3)))


# ================================================================== 31 · bant içi gradyan
BANT_BARLARI = [
    (102.0, 104.5, 101.5, 104.0), (104.0, 106.0, 103.2, 105.4), (105.4, 108.2, 105.0, 107.6),
    (107.6, 109.6, 107.0, 108.2), (108.2, 110.0, 107.4, 107.8), (107.8, 108.4, 105.6, 106.0),
    (106.0, 106.6, 103.8, 104.2), (104.2, 105.0, 102.2, 102.6), (102.6, 103.4, 100.4, 101.0),
    (101.0, 101.8, 100.0, 101.4), (101.4, 103.6, 101.0, 103.2), (103.2, 105.4, 102.8, 105.0),
    (105.0, 107.0, 104.6, 105.2), (105.2, 106.0, 103.4, 103.8), (103.8, 104.6, 101.8, 102.2),
    (102.2, 103.2, 100.2, 102.8), (102.8, 105.0, 102.4, 104.6), (104.6, 106.8, 104.2, 106.4),
    (106.4, 108.6, 106.0, 108.0), (108.0, 109.8, 107.6, 107.9), (107.9, 108.2, 106.0, 106.4),
    (106.4, 107.0, 104.2, 104.6), (104.6, 105.4, 103.0, 105.0), (105.0, 107.2, 104.6, 106.8),
    (106.8, 108.8, 106.4, 107.2), (107.2, 107.8, 105.2, 105.6), (105.6, 106.2, 103.2, 103.6),
    (103.6, 104.2, 101.4, 101.8), (101.8, 102.6, 100.1, 101.6), (101.6, 103.8, 101.2, 103.4),
    (103.4, 105.6, 103.0, 105.2), (105.2, 106.4, 104.0, 104.4),
]


def f31_gradyan():
    """Ş · 1 panel — bandın dikey beş dilimi ve her dilimde yönsel olasılık."""
    d = df_yap(BANT_BARLARI)
    n = len(d)
    fig = go.Figure()
    fig.add_trace(mumlar(d, "şematik bant"))

    dilimler = [
        (108, 110, "üst %20 — PAHALI", "al ~%30 · sat ~%70", BORDO),
        (106, 108, "üst orta", "al ~%40 · sat ~%60", "#a13c3c"),
        (104, 106, "tam orta — İŞLEM YOK", "al ~%50 · sat ~%50", GRI),
        (102, 104, "alt orta", "al ~%60 · sat ~%40", "#2f8a80"),
        (100, 102, "alt %20 — UCUZ", "al ~%70 · sat ~%30", TEAL),
    ]
    for y0, y1, ad, olasilik, renk in dilimler:
        fig.add_shape(type="rect", x0=-0.6, x1=n + 5.4, y0=y0, y1=y1,
                      fillcolor=rgba(renk, 0.10),
                      line=dict(color=rgba(GRI, 0.5), width=0.8, dash="dot"), layer="below")
        not_(fig, n + 0.4, (y0 + y1) / 2, f"<b>{ad}</b><br>{olasilik}",
             renk=renk, ok=False, boyut=10, xanchor="left")

    yatay(fig, 110.0, -0.6, n + 5.4, renk=BORDO, w=1.5)
    yatay(fig, 100.0, -0.6, n + 5.4, renk=TEAL, w=1.5)
    not_(fig, 1, 110.0, "bandın tavanı", renk=BORDO, ok=False, boyut=10, yanchor="bottom")
    not_(fig, 1, 100.0, "bandın tabanı", renk=TEAL, ok=False, boyut=10, yanchor="top")
    for i in (4, 19):
        not_(fig, i, d.h[i] + 0.35, "tavanda sat", renk=BORDO, ax=0, ay=-30, boyut=10)
    for i in (9, 28):
        not_(fig, i, d.l[i] - 0.35, "tabanda al", renk=TEAL, ax=0, ay=32, boyut=10)
    not_(fig, 13, 105.0, "ortada işlem yok:<br>ödül/risk her iki yönde de kötü",
         renk=GRI, ok=False, boyut=10)

    lejant(fig, "olasılık dilimi", GRI, a=0.12)
    duzen(fig, "Bant içi yön olasılığı gradyanı",
          "yüzdeler Brooks'un kaba yönsel olasılık dili (≥%60 'olası', ≤%40 'olası değil') — "
          "kesin sayı değil, eğim", h=640, sematik=True)
    fig.update_xaxes(range=[-1.2, n + 12])
    kapsa(fig, 1, pay=0.09, sag=0.0)
    kaydet(fig, "31_bant_gradyani", olcum=dict(
        bant_tavani=110.0, bant_tabani=100.0, bant_yuksekligi=10.0, dilim_sayisi=5,
        dilim_yuksekligi=2.0, bar_sayisi=n,
        olasiliklar={"ust_%20": "al 30 / sat 70", "ust_orta": "al 40 / sat 60",
                     "orta": "al 50 / sat 50", "alt_orta": "al 60 / sat 40",
                     "alt_%20": "al 70 / sat 30"}))


# ================================================================== 32 · dar bantta stop vs limit
DAR_BANT = [
    (101.0, 102.4, 100.6, 102.0), (102.0, 103.0, 101.4, 101.6), (101.6, 102.2, 100.4, 100.8),
    (100.8, 101.6, 100.0, 101.4), (101.4, 102.6, 101.0, 101.2), (101.2, 103.2, 100.8, 101.0),
    (101.0, 101.8, 99.8, 100.2), (100.2, 102.0, 100.0, 101.8), (101.8, 103.4, 101.6, 102.0),
    (102.0, 102.4, 100.6, 100.8), (100.8, 101.4, 99.6, 101.0), (101.0, 102.2, 100.8, 102.0),
    (102.0, 102.8, 101.2, 101.4), (101.4, 102.0, 100.2, 101.0),
]
# (bar, yön, giriş, çıkış barı, çıkış) — dolumlar bar geometrisinden okunur
STOP_ISLEMLERI = [("al", 5, 103.1, 6, 100.2), ("sat", 6, 99.9, 7, 101.8),
                  ("al", 8, 103.3, 9, 100.8), ("sat", 10, 99.7, 11, 102.0)]
LIMIT_ISLEMLERI = [("sat", 5, 102.8, 6, 100.2), ("al", 6, 100.2, 7, 101.8)]


def f32_dar_bant():
    """Ş · 2 panel — aynı barlarda stop girişlerinin dizisi ve limit girişleri."""
    d = df_yap(DAR_BANT)
    n = len(d)
    ust, alt = float(d.h.max()), float(d.l.min())
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11)

    for row in (1, 2):
        fig.add_trace(mumlar(d, "dar bant", hover=None), row=row, col=1)
        kutu(fig, -0.5, n - 0.5, alt, ust, GRI, a=0.10, cizgi=1.0, row=row, col=1)
        yatay(fig, ust, -0.5, n - 0.5, renk=BORDO, w=1.2, row=row, col=1)
        yatay(fig, alt, -0.5, n - 0.5, renk=TEAL, w=1.2, row=row, col=1)

    stop_toplam = 0.0
    for k, (yon, i, giris, j, cikis) in enumerate(STOP_ISLEMLERI, 1):
        kar = (cikis - giris) if yon == "al" else (giris - cikis)
        stop_toplam += kar
        renk = MAVI
        cizgi(fig, i - 0.45, giris, j + 0.45, giris, renk=renk, dash="solid", w=1.4, row=1, col=1)
        cizgi(fig, j, giris, j, cikis, renk=TURUNCU, dash="dot", w=1.6, row=1, col=1)
        etiket = ("AL stop" if yon == "al" else "SAT stop")
        y_et = giris + 0.30 if yon == "al" else giris - 0.30
        not_(fig, i, y_et, f"{k}. {etiket} {giris:.1f}", renk=renk, ok=False, boyut=10,
             yanchor="bottom" if yon == "al" else "top", row=1, col=1)
        not_(fig, j + 0.15, cikis, f"{CARPI} {kar:+.1f}", renk=BORDO, ok=False, boyut=10,
             xanchor="left", row=1, col=1)
    not_(fig, 1.0, alt - 0.75,
         f"dört stop girişinin dördü de kaybetti · toplam {stop_toplam:+.1f} birim",
         renk=BORDO, ok=False, boyut=11, xanchor="left", row=1, col=1)
    _panel_baslik(fig, "Panel 1 — stop emriyle giriş: her kırılım denemesi geri emiliyor", 1)

    limit_toplam = 0.0
    for k, (yon, i, giris, j, cikis) in enumerate(LIMIT_ISLEMLERI, 1):
        kar = (cikis - giris) if yon == "al" else (giris - cikis)
        limit_toplam += kar
        cizgi(fig, i - 0.45, giris, j + 0.45, giris, renk=MOR, dash="solid", w=1.4, row=2, col=1)
        cizgi(fig, j, giris, j, cikis, renk=YESIL, dash="dot", w=1.8, row=2, col=1)
        etiket = ("AL limit" if yon == "al" else "SAT limit")
        y_et = giris - 0.30 if yon == "al" else giris + 0.30
        not_(fig, i, y_et, f"{k}. {etiket} {giris:.1f}", renk=MOR, ok=False, boyut=10,
             yanchor="top" if yon == "al" else "bottom", row=2, col=1)
        not_(fig, j + 0.15, cikis, f"{TIK} {kar:+.1f}", renk=YESIL, ok=False, boyut=10,
             xanchor="left", row=2, col=1)
    not_(fig, 1.0, alt - 0.75,
         f"aynı barlar, ters emir tipi: iki limit girişinin ikisi de kazandı · "
         f"toplam {limit_toplam:+.1f} birim", renk=YESIL, ok=False, boyut=11,
         xanchor="left", row=2, col=1)
    not_(fig, 8.4, ust + 0.55, "dar bantta kural: pahalıdan sat, ucuzdan al, scalp yap",
         renk=MUREKKEP, ok=False, boyut=10, row=2, col=1)
    _panel_baslik(fig, "Panel 2 — limit emriyle giriş: aynı bant, ters işaret", 2)

    lejant_cizgi(fig, "stop girişi (kırılımın ötesi)", MAVI, dash="solid")
    lejant_cizgi(fig, "limit girişi (bandın ucu)", MOR, dash="solid")
    duzen(fig, "Dar bant: stop emri neden kaybettirir",
          "aynı 14 bar, iki emir tipi · çıkış her işlemde bir sonraki barın kapanışı",
          h=880, sematik=True)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_yaxes(range=[alt - 1.15, ust + 0.95], row=1, col=1)
    fig.update_yaxes(range=[alt - 1.15, ust + 0.95], row=2, col=1)
    kaydet(fig, "32_dar_bant_stop_limit", olcum=dict(
        bant_tavani=ust, bant_tabani=alt, bant_yuksekligi=round(ust - alt, 2), bar_sayisi=n,
        stop_islem_sayisi=len(STOP_ISLEMLERI), stop_kazanan=0,
        stop_toplam=round(stop_toplam, 2), limit_islem_sayisi=len(LIMIT_ISLEMLERI),
        limit_kazanan=len(LIMIT_ISLEMLERI), limit_toplam=round(limit_toplam, 2)))


# ================================================================== 33 · barbwire
def f33_barbwire():
    """G · ES=F 5dk · 2 panel — barbwire bölgesi ve kırılımı fade eden işlem.

    Müfredat USDTRY 5dk diyor; o seri kotasyon artefaktlı (bkz. dosya başı notu),
    barbwire'ın ayırt edici geometrisi (büyük gövdesiz barlar + belirgin kuyruk)
    orada okunmuyor. Emini 5 dakika kullanıldı.
    """
    df = yukle("ES=F", "5m")
    if df is None:
        return
    BAS, ADET = 3460, 36                      # 2026-07-01 · indisle pinli
    B0, B1 = 3473, 3480                       # barbwire barları
    p = dilim(df, BAS, ADET)
    a0, a1 = B0 - BAS, B1 - BAS
    bw = p.iloc[a0:a1 + 1].reset_index(drop=True)
    ust, alt = float(bw.h.max()), float(bw.l.min())
    yuk = ust - alt
    ort_bar = float((bw.h - bw.l).mean())
    doji = [a0 + i for i in range(len(bw)) if abs(bw.c[i] - bw.o[i]) < 0.30 * (bw.h[i] - bw.l[i])]
    kir = 3481 - BAS                          # kırılım barı: bandın 1 tick üstünde kapanış

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.10, row_heights=[0.5, 0.5])
    fig.add_trace(mumlar(p, "ES=F 5dk", hover=hover(p)), row=1, col=1)
    kutu(fig, a0 - 0.5, a1 + 0.5, alt, ust, TURUNCU, a=0.16, cizgi=1.4, row=1, col=1)
    yatay(fig, ust, a0 - 0.5, len(p) - 0.5, renk=BORDO, w=1.3, row=1, col=1)
    yatay(fig, alt, a0 - 0.5, len(p) - 0.5, renk=TEAL, w=1.3, row=1, col=1)
    for j, i in enumerate(doji):
        not_(fig, i, float(p.l[i]) - yuk * (0.10 if j % 2 == 0 else 0.30), "doji",
             renk=TURUNCU, ok=False, boyut=9, yanchor="top", row=1, col=1)
    not_(fig, (a0 + a1) / 2, alt - yuk * 0.78,
         f"barbwire: {len(bw)} bar, {len(doji)} doji, hepsi örtüşüyor · "
         f"bant yüksekliği {yuk:.2f} = ortalama bar boyunun {yuk/ort_bar:.1f} katı",
         renk=TURUNCU, ok=False, boyut=10, row=1, col=1)
    not_(fig, kir, p.h[kir] + yuk * 0.12,
         f"kırılım barı: bandın tavanını yalnızca {p.c[kir]-ust:.2f} geçen bir kapanış",
         renk=ALTIN, ax=-10, ay=-38, boyut=10, row=1, col=1)
    not_(fig, 3484 - BAS, p.l[3484 - BAS] - yuk * 0.12,
         "kırılımın çöküşü: tek barda −23,25", renk=BORDO, ax=20, ay=34, boyut=10, row=1, col=1)
    _panel_baslik(fig, "Panel 1 — barbwire bölgesi ve dojileri", 1)

    # ---- panel 2: kardinal kural — kırılımı fade et
    p2 = dilim(df, 3470, 24)
    k2 = 3481 - 3470
    fig.add_trace(mumlar(p2, "ES=F 5dk (yakın)", hover=hover(p2)), row=2, col=1)
    kutu(fig, (B0 - 3470) - 0.5, (B1 - 3470) + 0.5, alt, ust, TURUNCU, a=0.14, cizgi=1.2,
         row=2, col=1)
    giris, stop = ust, float(p2.h[k2]) + 0.25
    mm = alt - yuk                            # bant yüksekliği kadar aşağı projeksiyon
    olcum = islem(fig, p2, sinyal=k2, yon="bear", giris=giris, stop=stop,
                  hedefler=(alt, mm), etiketler=("bandın tabanı", "ölçülmüş hareket"),
                  row=2, col=1, x_son=len(p2) - 1)
    dip = float(p2.l[k2 + 1:].min())
    not_(fig, k2, giris + yuk * 0.28,
         "kardinal kural: barbwire'ın kırılımını FADE et —<br>"
         f"bandın tavanında ({giris:.2f}) limit satış, stop kırılım barının 1 tick üstü",
         renk=MOR, ax=-40, ay=-44, boyut=10, row=2, col=1)
    not_(fig, int(np.argmin(p2.l.values[k2 + 1:])) + k2 + 1, dip - yuk * 0.10,
         f"gerçekleşen dip {dip:.2f} → hedeflerin ikisi de doldu", renk=YESIL, ax=10, ay=34,
         boyut=10, row=2, col=1)
    _panel_baslik(fig, "Panel 2 — kırılımı fade eden işlem: giriş, stop, iki hedef", 2)

    lejant(fig, "barbwire", TURUNCU, a=0.16)
    lejant_cizgi(fig, "bandın tavanı / tabanı", BORDO, dash="dash")
    duzen(fig, "Barbwire ve kardinal kural",
          "ES=F 5dk · 2026-07-01 · pencere indisle pinli (bar 3460–3495) · "
          "müfredatın USDTRY 5dk serisi kotasyon artefaktlı olduğu için Emini kullanıldı",
          h=960)
    fig.update_xaxes(title_text="", row=1, col=1)
    zaman_ekseni(fig, p, 7, "%H:%M", row=1, col=1)
    zaman_ekseni(fig, p2, 7, "%H:%M", row=2, col=1)
    kapsa(fig, 2, sag=6.0)
    kaydet(fig, "33_barbwire", olcum=dict(
        enstruman="ES=F 5dk", gun="2026-07-01", pencere_p1=[3460, 3495], pencere_p2=[3470, 3493],
        barbwire_barlari=[B0, B1], bar_sayisi=len(bw), doji_sayisi=len(doji),
        bant_tavani=round(ust, 2), bant_tabani=round(alt, 2), bant_yuksekligi=round(yuk, 2),
        ortalama_bar=round(ort_bar, 2), yukseklik_bolu_bar=round(yuk / ort_bar, 2),
        kirilim_kapanisi=round(float(p.c[kir]), 2),
        kirilim_asimi=round(float(p.c[kir]) - ust, 2),
        giris=round(giris, 2), stop=round(stop, 2), risk=round(olcum["risk"], 2),
        hedef_bant_tabani=round(alt, 2), hedef_mm=round(mm, 2),
        r_katlari=[round(r, 2) for r in olcum["r"]], gerceklesen_dip=round(dip, 2)))


# ================================================================== 34 · üçgen ailesi
UCGEN_SIMETRIK = [
    (100.0, 105.0, 99.5, 104.4), (104.4, 104.8, 95.6, 96.2), (96.2, 103.2, 95.8, 102.6),
    (102.6, 103.4, 96.8, 97.2), (97.2, 102.0, 96.9, 101.4), (101.4, 101.8, 97.8, 98.2),
    (98.2, 101.0, 98.0, 100.6), (100.6, 100.8, 98.8, 99.0), (99.0, 100.3, 98.9, 100.0),
    (100.0, 100.2, 99.3, 99.5), (99.5, 100.1, 99.2, 99.8),
]
UCGEN_YUKSELEN = [
    (98.0, 104.0, 97.6, 103.4), (103.4, 103.8, 98.4, 98.8), (98.8, 103.9, 98.6, 103.2),
    (103.2, 104.0, 100.0, 100.4), (100.4, 103.8, 100.2, 103.4), (103.4, 104.0, 101.2, 101.6),
    (101.6, 103.9, 101.4, 103.5), (103.5, 104.0, 102.4, 102.8), (102.8, 103.9, 102.6, 103.6),
    (103.6, 104.0, 103.0, 103.2), (103.2, 104.1, 103.0, 103.9),
]
UCGEN_ALCALAN = [
    (102.0, 102.4, 96.0, 96.6), (96.6, 101.6, 96.2, 101.2), (101.2, 101.5, 96.1, 96.5),
    (96.5, 100.4, 96.3, 100.0), (100.0, 100.3, 96.0, 96.4), (96.4, 99.2, 96.2, 98.8),
    (98.8, 99.1, 96.1, 96.5), (96.5, 98.0, 96.2, 97.6), (97.6, 97.9, 96.0, 96.4),
    (96.4, 97.2, 96.1, 96.8), (96.8, 97.0, 95.9, 96.2),
]
UCGEN_GENISLEYEN = [
    (100.0, 101.4, 99.0, 101.0), (101.0, 101.6, 98.4, 98.8), (98.8, 102.6, 98.6, 102.2),
    (102.2, 102.8, 97.4, 97.8), (97.8, 104.0, 97.6, 103.6), (103.6, 104.2, 96.2, 96.6),
    (96.6, 105.4, 96.4, 105.0), (105.0, 105.6, 95.0, 95.4), (95.4, 106.6, 95.2, 106.2),
    (106.2, 106.8, 94.0, 94.4), (94.4, 101.0, 94.2, 100.6),
]


def f34_ucgen_ailesi():
    """Ş · 1 panel — dört üçgen; hepsinin altında aynı yatay bant gölgesi."""
    bloklar = [
        ("simetrik üçgen", UCGEN_SIMETRIK, "iki kenar da eğimli", (0, 10), (1, 8)),
        ("yükselen üçgen", UCGEN_YUKSELEN, "tavan yatay, dipler yükseliyor", (0, 10), (0, 8)),
        ("alçalan üçgen", UCGEN_ALCALAN, "taban yatay, tepeler alçalıyor", (0, 10), (0, 8)),
        ("genişleyen üçgen", UCGEN_GENISLEYEN, "iki kenar da ıraksıyor", (0, 9), (1, 9)),
    ]
    ARA = 4
    fig = go.Figure()
    x0 = 0
    kayitlar = {}
    for ad, barlar, alt_metin, (t0, t1), (d0, d1) in bloklar:
        d = df_yap(barlar)
        n = len(d)
        xs = list(range(x0, x0 + n))
        fig.add_trace(go.Candlestick(
            x=xs, open=d.o, high=d.h, low=d.l, close=d.c, name=ad, showlegend=False,
            increasing=dict(line=dict(color=TEAL, width=1.1), fillcolor=rgba(TEAL, 0.55)),
            decreasing=dict(line=dict(color=BORDO, width=1.1), fillcolor=rgba(BORDO, 0.55)),
            whiskerwidth=0.15))
        ust, alt = float(d.h.max()), float(d.l.min())
        kutu(fig, x0 - 0.6, x0 + n - 0.4, alt, ust, GRI, a=0.12, cizgi=1.0, dash="dot")
        # tepe çizgisi
        cizgi(fig, x0 + t0, float(d.h[t0]), x0 + n - 1 + 1.2,
              float(d.h[t0]) + (float(d.h[t1]) - float(d.h[t0])) / (t1 - t0) * (n - t0 + 0.2),
              renk=BORDO, dash="dash", w=1.5)
        # dip çizgisi
        cizgi(fig, x0 + d0, float(d.l[d0]), x0 + n - 1 + 1.2,
              float(d.l[d0]) + (float(d.l[d1]) - float(d.l[d0])) / (d1 - d0) * (n - d0 + 0.2),
              renk=TEAL, dash="dash", w=1.5)
        not_(fig, x0 + n / 2 - 0.5, 108.6, f"<b>{ad}</b>", renk=MUREKKEP, ok=False, boyut=12)
        not_(fig, x0 + n / 2 - 0.5, 107.3, alt_metin, renk=GRI, ok=False, boyut=10)
        not_(fig, x0 + n / 2 - 0.5, 92.6, f"yatay bant: {alt:.1f} – {ust:.1f}", renk=GRI,
             ok=False, boyut=10)
        kayitlar[ad] = dict(tavan=round(ust, 1), taban=round(alt, 1),
                            yukseklik=round(ust - alt, 1), bar=n)
        x0 += n + ARA
    not_(fig, (x0 - ARA) / 2 - 0.5, 90.6,
         "Dördü de işlevsel olarak yatay banttır: iki taraflı işlem, kırılım modu, "
         "kırılımların çoğu başarısız.", renk=MUREKKEP, ok=False, boyut=11)
    lejant(fig, "yatay bant gölgesi", GRI, a=0.12)
    lejant_cizgi(fig, "tepe çizgisi", BORDO)
    lejant_cizgi(fig, "dip çizgisi", TEAL)
    duzen(fig, "Üçgen ailesi ve hepsinin bant olması",
          "üç itişli her yapı fonksiyonel olarak üçgendir; üçgen de bir yatay banttır",
          h=660, sematik=True)
    fig.update_yaxes(range=[89.4, 110.2])
    fig.update_xaxes(range=[-1.6, x0 - ARA + 1.6], showticklabels=False, title_text="")
    kaydet(fig, "34_ucgen_ailesi", olcum=dict(ucgenler=kayitlar, blok_arasi_bosluk=ARA))


# ================================================================== 35 · kırılım modu emir haritası
KIRILIM_MODU = [
    (100.0, 102.0, 99.4, 101.6), (101.6, 102.2, 100.0, 100.4), (100.4, 101.8, 99.6, 101.4),
    (101.4, 101.9, 100.2, 100.6), (100.6, 101.6, 100.0, 101.2), (101.2, 101.5, 100.4, 100.7),
    (100.7, 101.3, 100.6, 101.1),
]


def f35_kirilim_modu():
    """Ş · 1 panel — dar bant / ii kurulumunda çift taraflı emir ve ters çevirme."""
    d = df_yap(KIRILIM_MODU)
    n = len(d)
    ust, alt = float(d.h.max()), float(d.l.min())
    yuk = ust - alt
    TIK_B = 0.1
    al_stop = float(d.h[6]) + TIK_B
    sat_stop = float(d.l[6]) - TIK_B
    ters_al = ust + TIK_B
    ters_sat = alt - TIK_B
    hedef_yukari = ters_al + yuk
    hedef_asagi = ters_sat - yuk

    fig = go.Figure()
    fig.add_trace(mumlar(d, "kırılım modu"))
    kutu(fig, -0.5, n - 0.5, alt, ust, GRI, a=0.12, cizgi=1.1)
    kutu(fig, 4.55, 6.45, float(d.l[5]), float(d.h[5]), ALTIN, a=0.18, cizgi=1.2)
    not_(fig, 5.5, float(d.l[5]) - yuk * 0.10, "ii: iki ardışık iç bar", renk=ALTIN,
         ok=False, boyut=10, yanchor="top")

    SAG = n + 2.0
    yatay(fig, al_stop, 6 - 0.4, SAG, renk=MAVI, dash="solid", w=1.7)
    not_(fig, SAG, al_stop, f"① AL stop {al_stop:.2f} (ii'nin 1 tick üstü)", renk=MAVI,
         ok=False, boyut=10, xanchor="left")
    yatay(fig, sat_stop, 6 - 0.4, SAG, renk=MAVI, dash="solid", w=1.7)
    not_(fig, SAG, sat_stop, f"② SAT stop {sat_stop:.2f} (ii'nin 1 tick altı)", renk=MAVI,
         ok=False, boyut=10, xanchor="left")
    yatay(fig, ters_al, 0, SAG, renk=TURUNCU, dash="dashdot", w=1.5)
    not_(fig, SAG, ters_al, f"③ ters çevirme ALIŞ {ters_al:.2f} — ② tuzağa düşerse "
                            f"çift boyutla dön", renk=TURUNCU, ok=False, boyut=10, xanchor="left")
    yatay(fig, ters_sat, 0, SAG, renk=TURUNCU, dash="dashdot", w=1.5)
    not_(fig, SAG, ters_sat, f"④ ters çevirme SATIŞ {ters_sat:.2f} — ① tuzağa düşerse "
                             f"çift boyutla dön", renk=TURUNCU, ok=False, boyut=10, xanchor="left")
    yatay(fig, hedef_yukari, 0, SAG, renk=MOR, dash="dash", w=1.4)
    not_(fig, SAG, hedef_yukari, f"yukarı ölçülmüş hareket {hedef_yukari:.2f} "
                                 f"(bant yüksekliği {yuk:.2f})", renk=MOR, ok=False,
         boyut=10, xanchor="left")
    yatay(fig, hedef_asagi, 0, SAG, renk=MOR, dash="dash", w=1.4)
    not_(fig, SAG, hedef_asagi, f"aşağı ölçülmüş hareket {hedef_asagi:.2f}", renk=MOR,
         ok=False, boyut=10, xanchor="left")

    not_(fig, SAG + 4.6, ust + yuk * 1.05,
         "Kırılım modu: kırılım yakın, yön belirsiz. İki yöne birden emir<br>"
         "bırakılır; hangisi dolarsa diğeri koruyucu stopa döner.",
         renk=MUREKKEP, ok=False, boyut=11)
    not_(fig, SAG + 4.6, alt - yuk * 1.15,
         "Tuzaklanan iki taraf kuralı: her iki kırılım da başarısız olursa iki<br>"
         "taraf da hapsolur; ikinci başarısızlığın ardından gelen hareket<br>en büyüğüdür.",
         renk=MUREKKEP, ok=False, boyut=10)

    lejant_cizgi(fig, "giriş stopu", MAVI, dash="solid")
    lejant_cizgi(fig, "ters çevirme emri", TURUNCU, dash="dashdot")
    lejant_cizgi(fig, "ölçülmüş hareket hedefi", MOR)
    duzen(fig, "Kırılım modunda çift taraflı emir haritası",
          "dar bant / ii kurulumu · emirler ii barının uçlarında, ters emirler bandın uçlarında",
          h=680, sematik=True)
    fig.update_xaxes(range=[-1.0, SAG + 10.5], showticklabels=False, title_text="")
    fig.update_yaxes(range=[hedef_asagi - 0.45, hedef_yukari + 0.55])
    kaydet(fig, "35_kirilim_modu", olcum=dict(
        bant_tavani=ust, bant_tabani=alt, bant_yuksekligi=round(yuk, 2),
        al_stop=round(al_stop, 2), sat_stop=round(sat_stop, 2),
        ters_alis=round(ters_al, 2), ters_satis=round(ters_sat, 2),
        hedef_yukari=round(hedef_yukari, 2), hedef_asagi=round(hedef_asagi, 2),
        ii_barlari=[5, 6]))


# ================================================================== 36 · kırılım anatomisi
ANATOMI = [
    (100.0, 101.4, 99.0, 101.0), (101.0, 102.0, 100.0, 100.4), (100.4, 101.2, 98.4, 98.8),
    (98.8, 100.6, 98.2, 100.2), (100.2, 101.8, 99.8, 100.2), (100.2, 100.8, 98.6, 99.0),
    (99.0, 101.0, 98.8, 100.8), (100.8, 102.0, 100.4, 101.8),
    (101.8, 105.2, 101.6, 105.0),                                    # 8 · kırılım barı
    (105.0, 106.6, 104.6, 106.2), (106.2, 107.0, 105.2, 105.6),
    (105.6, 105.8, 103.4, 103.8), (103.8, 104.2, 103.0, 104.0),      # 11-12 · geri çekilme
    (104.0, 106.2, 103.8, 106.0), (106.0, 108.0, 105.8, 107.6),
    (107.6, 108.0, 105.0, 105.4), (105.4, 105.6, 102.2, 102.6),
    (102.6, 104.4, 102.1, 104.2),                                    # 17 · kırılım testi
    (104.2, 106.0, 104.0, 105.8),
]
# panel 2 · aynı geometri, iki farklı ad
ANA_A = [(100.4, 101.6, 99.8, 101.4), (101.4, 102.0, 100.2, 100.6), (100.6, 101.6, 99.6, 101.6),
         (101.6, 104.8, 101.4, 104.6), (104.6, 105.8, 104.0, 105.4),
         (105.4, 105.6, 102.6, 102.9), (102.9, 103.4, 102.4, 103.2),
         (103.2, 105.0, 103.0, 104.8), (104.8, 106.6, 104.6, 106.4)]
ANA_B = [(100.4, 101.6, 99.8, 101.4), (101.4, 102.0, 100.2, 100.6), (100.6, 101.6, 99.6, 101.6),
         (101.6, 104.8, 101.4, 104.6), (104.6, 105.8, 104.0, 105.4),
         (105.4, 105.6, 101.4, 101.6), (101.6, 101.8, 100.0, 100.2),
         (100.2, 100.6, 98.6, 98.8), (98.8, 99.4, 97.6, 97.9)]


def f36_kirilim_anatomisi():
    """Ş · 2 panel — kırılım noktası / kırılım boşluğu / kırılım testi + iki adlandırma."""
    d = df_yap(ANATOMI)
    n = len(d)
    NOKTA = 102.0                     # bandın tavanı = kırılım noktası
    gc_dip = float(d.l[12])           # geri çekilmenin dibi
    test_dip = float(d.l[17])
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, row_heights=[0.56, 0.44])

    fig.add_trace(mumlar(d, "şematik"), row=1, col=1)
    kutu(fig, -0.5, 7.5, float(d.l[:8].min()), NOKTA, GRI, a=0.11, cizgi=1.0, row=1, col=1)
    yatay(fig, NOKTA, -0.5, n - 0.5, renk=ALTIN, dash="solid", w=1.8, row=1, col=1)
    not_(fig, n - 0.4, NOKTA, "kırılım noktası (aşılan önceki fiyat)", renk=ALTIN, ok=False,
         boyut=10, xanchor="left", row=1, col=1)
    kutu(fig, 8, 13.5, NOKTA, gc_dip, MOR, a=0.20, cizgi=1.1, row=1, col=1)
    not_(fig, 11, (NOKTA + gc_dip) / 2, f"kırılım boşluğu {gc_dip - NOKTA:.1f}", renk=MOR,
         ok=False, boyut=10, row=1, col=1)
    not_(fig, 8, float(d.h[8]) + 0.5, "kırılım barı = spike = klimaks = boşluk", renk=ALTIN,
         ax=-30, ay=-32, boyut=10, row=1, col=1)
    not_(fig, 12, gc_dip - 0.6, "kırılım geri çekilmesi (1–5 bar)<br>boşluk korunuyor",
         renk=MOR, ax=-20, ay=34, boyut=10, row=1, col=1)
    not_(fig, 17, test_dip - 0.5,
         f"kırılım testi: dip {test_dip:.1f}, kırılım noktasının {test_dip - NOKTA:.1f} "
         f"üstünde kaldı → mükemmel test", renk=TEAL, ax=6, ay=36, boyut=10, row=1, col=1)
    not_(fig, 14, float(d.h[14]) + 0.5, "testin zamanlaması: girişten 9 bar sonra<br>"
                                        "(1–2 bar ile 20+ bar arası her şey olabilir)",
         renk=GRI, ok=False, boyut=10, row=1, col=1)
    _panel_baslik(fig, "Panel 1 — üç kavram tek şema üzerinde", 1)

    # ---- panel 2: iki adlandırma
    dA, dB = df_yap(ANA_A), df_yap(ANA_B)
    ARA = 4
    for k, (dd, ad, renk, aciklama) in enumerate((
            (dA, "kırılım geri çekilmesi", TEAL,
             "geri çekilme kırılım noktasının ÜSTÜNDE bitti → boşluk duruyor,<br>"
             "trend yönünde en güvenilir ikinci giriş"),
            (dB, "başarısız kırılım", TURUNCU,
             "geri çekilme kırılım noktasının ALTINA indi → negatif boşluk,<br>"
             "kırılım tezi geçersiz; karşı taraf tuzaklandı"))):
        x0 = k * (len(dA) + ARA)
        xs = list(range(x0, x0 + len(dd)))
        fig.add_trace(go.Candlestick(
            x=xs, open=dd.o, high=dd.h, low=dd.l, close=dd.c, showlegend=False, name=ad,
            increasing=dict(line=dict(color=TEAL, width=1.1), fillcolor=rgba(TEAL, 0.55)),
            decreasing=dict(line=dict(color=BORDO, width=1.1), fillcolor=rgba(BORDO, 0.55)),
            whiskerwidth=0.15), row=2, col=1)
        yatay(fig, NOKTA, x0 - 0.5, x0 + len(dd) - 0.5, renk=ALTIN, w=1.6, row=2, col=1)
        y0, y1 = (NOKTA, float(dd.l[6])) if k == 0 else (float(dd.l[8]), NOKTA)
        kutu(fig, x0 + 4.5, x0 + len(dd) - 0.5, min(y0, y1), max(y0, y1),
             renk, a=0.18, cizgi=1.0, row=2, col=1)
        not_(fig, x0 + len(dd) / 2 - 0.5, 108.4, f"<b>{ad}</b>", renk=renk, ok=False,
             boyut=12, row=2, col=1)
        not_(fig, x0 + len(dd) / 2 - 0.5, 95.6, aciklama, renk=MUREKKEP, ok=False, boyut=10,
             row=2, col=1)
    not_(fig, len(dA) + ARA / 2 - 0.5, 93.4,
         "Aynı geometri, tek fark geri çekilmenin nerede bittiği. Ad da, işlem de buradan değişir.",
         renk=MUREKKEP, ok=False, boyut=11, row=2, col=1)
    _panel_baslik(fig, "Panel 2 — aynı yapının iki adı", 2)

    lejant_cizgi(fig, "kırılım noktası", ALTIN, dash="solid")
    lejant(fig, "kırılım boşluğu", MOR, a=0.20)
    duzen(fig, "Kırılım anatomisi: kırılım noktası · kırılım boşluğu · kırılım testi",
          "formal tanımlar; boşluk taralı", h=940, sematik=True)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(range=[-1.2, 2 * len(dA) + ARA + 0.8], showticklabels=False, row=2, col=1)
    fig.update_yaxes(range=[92.4, 109.8], row=2, col=1)
    kaydet(fig, "36_kirilim_anatomisi", olcum=dict(
        kirilim_noktasi=NOKTA, kirilim_bari=8, geri_cekilme_barlari=[11, 12],
        geri_cekilme_dibi=gc_dip, kirilim_boslugu=round(gc_dip - NOKTA, 2),
        test_bari=17, test_dibi=test_dip, test_mesafesi=round(test_dip - NOKTA, 2),
        test_gecikmesi_bar=9))


# ================================================================== 37 · güçlü kırılım
def f37_guclu_kirilim():
    """G · XU030 5dk · 2 panel — kırılım barı + 14 maddelik güç kontrol listesi."""
    df = yukle("XU030.IS", "5m")
    if df is None:
        return
    BAS, ADET, KIR = 4390, 51, 4416           # 2026-08-04 · indisle pinli
    p = dilim(df, BAS, ADET)
    k = KIR - BAS
    nokta = float(p.h[:k].max())              # kırılım noktası: pencerenin önceki zirvesi
    ort20 = float((p.h - p.l)[max(0, k - 20):k].mean())
    ort_govde = float((p.c - p.o).abs()[max(0, k - 20):k].mean())
    r = float(p.h[k] - p.l[k])
    govde = float(p.c[k] - p.o[k])
    ust_kuyruk = float(p.h[k] - p.c[k])
    bar_ici_geri = float(p.o[k] - p.l[k])
    mikro = float(p.l[k + 1] - p.h[k - 1])    # kırılım barının komşuları değiyor mu
    # ilk geri çekilme: spike bittikten sonraki ilk düşen kapanış (bar içi kuyruk değil)
    gc_bas = next(i for i in range(k + 1, len(p)) if p.c[i] < p.c[i - 1])
    tepe = float(p.h[k:gc_bas + 1].max())
    gc_son = next((i for i in range(gc_bas + 1, len(p)) if p.h[i] > tepe), len(p) - 1)
    gc = int(np.argmin(p.l.values[gc_bas:gc_son])) + gc_bas
    gc_dip = float(p.l[gc])
    spike_bar = gc_bas - k
    cevrilen = sum(1 for i in range(k) if p.h[i] < p.c[k])

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, row_heights=[0.58, 0.42])
    fig.add_trace(mumlar(p, "XU030 5dk", hover=hover(p)), row=1, col=1)
    kutu(fig, -0.5, k - 0.5, float(p.l[:k].min()), nokta, GRI, a=0.11, cizgi=1.0, row=1, col=1)
    yatay(fig, nokta, -0.5, len(p) - 0.5, renk=ALTIN, dash="solid", w=1.7, row=1, col=1)
    not_(fig, len(p) - 0.4, nokta, f"kırılım noktası {nokta:,.0f}", renk=ALTIN, ok=False,
         boyut=10, xanchor="left", row=1, col=1)
    kutu(fig, k - 0.45, k + 0.45, float(p.l[k]), float(p.h[k]), ALTIN, a=0.22, cizgi=1.4,
         row=1, col=1)
    not_(fig, k, float(p.h[k]) + r * 0.14,
         f"kırılım barı: menzil {r:,.0f} = 20 barlık ortalamanın {r/ort20:.1f} katı<br>"
         f"gövde/menzil %{100*govde/r:.0f} · kapanış tepede (üst kuyruk {ust_kuyruk:,.1f})",
         renk=ALTIN, ax=-110, ay=-78, boyut=10, row=1, col=1)
    kutu(fig, k - 1.45, k + 1.45, float(p.h[k - 1]), float(p.l[k + 1]), MOR, a=0.22, cizgi=1.0,
         row=1, col=1)
    not_(fig, k - 1, float(p.h[k - 1]) - r * 0.30, f"mikro boşluk {mikro:,.1f}<br>"
                                                   "(önceki ve sonraki bar değmiyor)",
         renk=MOR, ax=-40, ay=30, boyut=10, row=1, col=1)
    not_(fig, k + 2, float(p.h[k + 1:k + 4].max()) + r * 0.06,
         "üç takip barı", renk=TEAL, ok=False, boyut=10, yanchor="bottom", row=1, col=1)
    kutu(fig, k + 0.55, gc_son - 0.5, nokta, gc_dip, TEAL, a=0.14, cizgi=1.0, row=1, col=1)
    not_(fig, gc, gc_dip - r * 0.10,
         f"ilk geri çekilme {spike_bar} bar sonra başladı; dibi {gc_dip:,.0f} —<br>"
         f"kırılım noktasının {gc_dip - nokta:,.0f} üstünde kaldı (boşluk duruyor)",
         renk=TEAL, ax=40, ay=42, boyut=10, row=1, col=1)
    _panel_baslik(fig, "Panel 1 — kırılım barı, takip barları ve ilk geri çekilme", 1)

    satirlar = [
        (f"gövde menzilin üçte ikisinden büyük (%{100*govde/r:.0f})", "evet"),
        (f"kapanış kendi ucunda; üst kuyruk yok denecek kadar küçük ({ust_kuyruk:,.1f} puan)", "evet"),
        (f"menzil, 20 barlık ortalamanın 2 katından büyük ({r/ort20:.1f}×)", "evet"),
        (f"birden çok seviyeyi birden kırdı: kapanış son {cevrilen} barın tepesinin üstünde", "evet"),
        (f"mikro boşluk var: önceki barın tepesi ile sonraki barın dibi arasında {mikro:,.1f} puan", "evet"),
        (f"gövde boşluğu: açılış ({p.o[k]:,.0f}) önceki kapanışın ({p.c[k-1]:,.0f}) ötesinde", "hayir"),
        (f"takip barları ortalama gövdeli: sonraki üç gövde {abs(p.c[k+1]-p.o[k+1]):,.0f} / "
         f"{abs(p.c[k+2]-p.o[k+2]):,.0f} / {abs(p.c[k+3]-p.o[k+3]):,.0f} (bant ortalaması {ort_govde:,.0f})", "evet"),
        (f"spike birden fazla bara büyüdü ({spike_bar} bar) ve bir bardan fazla geri çekilmedi", "evet"),
        (f"ilk geri çekilme 3+ bar sonra geldi ({spike_bar}. bar)", "evet"),
        (f"ilk geri çekilme kırılım noktasına ulaşmadı ({gc_dip - nokta:,.0f} puan yukarıda durdu)", "evet"),
        (f"bar içi geri çekilme bar boyunun dörtte birinden az (%{100*bar_ici_geri/r:.0f})", "evet"),
        (f"scalper kârı ilk barda üretildi (kırılım barı tek başına {govde:,.0f} puan)", "evet"),
        ("bantta biriken alış baskısı: kırılımdan önceki dipler yükseliyor", "evet"),
        ("hacim ortalamanın 10–20 katı", "yok"),
    ]
    puan_karti(fig, 2, satirlar, "güç ölçütü", "onay")
    evet = sum(1 for _, d_ in satirlar if d_ == "evet")
    _panel_baslik(fig, f"Panel 2 — güç kontrol listesi: {evet} onay / "
                       f"{sum(1 for _, d_ in satirlar if d_ == 'hayir')} ret / "
                       f"{sum(1 for _, d_ in satirlar if d_ == 'yok')} ölçülemedi "
                       f"(hacim önbellekte yok)", 2)

    lejant_cizgi(fig, "kırılım noktası", ALTIN, dash="solid")
    lejant(fig, "mikro boşluk", MOR, a=0.22)
    lejant(fig, "kırılım boşluğu (korunan)", TEAL, a=0.14)
    duzen(fig, "Güçlü kırılım ölçütleri kontrol listesi",
          "XU030 5dk · 2026-08-04 11:40 kırılımı · pencere indisle pinli (bar 4390–4440)",
          h=1020)
    fig.update_xaxes(title_text="", row=1, col=1)
    zaman_ekseni(fig, p, 8, "%H:%M", row=1, col=1)
    kapsa(fig, 1, sag=8.0)
    kaydet(fig, "37_guclu_kirilim", olcum=dict(
        gun="2026-08-04", pencere=[BAS, BAS + ADET - 1], kirilim_bari=KIR,
        kirilim_noktasi=round(nokta, 2), menzil=round(r, 2), ortalama20=round(ort20, 2),
        menzil_kati=round(r / ort20, 2), govde_orani=round(govde / r, 3),
        ust_kuyruk=round(ust_kuyruk, 2), mikro_bosluk=round(mikro, 2),
        spike_bar_sayisi=spike_bar, ilk_geri_cekilme_bari=BAS + gc,
        geri_cekilme_dibi=round(gc_dip, 2),
        bosluk_kalan=round(gc_dip - nokta, 2), bar_ici_geri_orani=round(bar_ici_geri / r, 3),
        cevrilen_bar=cevrilen, onay=evet, ret=1, olculemedi=1))


# ================================================================== 38 · zayıf kırılım
def f38_zayif_kirilim():
    """G · GC=F 5dk · 2 panel — kırılım ve zayıflığın erken uyarı barları.

    Müfredat USDTRY 5dk diyor; o seri kotasyon artefaktlı (dosya başı notu). Kuyruk ve
    örtüşme okunabilen bir seri gerekiyordu: XAUUSD ailesinden GC=F 5 dakika.
    """
    df = yukle("GC=F", "5m")
    if df is None:
        return
    BAS, ADET, KIR = 8758, 45, 8781           # 2026-07-29 · indisle pinli
    p = dilim(df, BAS, ADET)
    k = KIR - BAS
    b0 = 8766 - BAS                            # bandın başı
    nokta = float(p.h[b0:k].max())
    alt = float(p.l[b0:k].min())
    ort20 = float((p.h - p.l)[max(0, k - 20):k].mean())
    r = float(p.h[k] - p.l[k])
    ust_kuyruk = float(p.h[k] - p.c[k])
    govde_orta = (float(p.o[k]) + float(p.c[k])) / 2
    tetik = float(p.h[k])                      # kırılım barının tepesinin üstündeki alış stopu
    sonra_max = float(p.h[k + 1:].max())
    dip = float(p.l[k + 1:].min())
    dip_i = int(np.argmin(p.l.values[k + 1:])) + k + 1
    geri_i = next(i for i in range(k + 1, len(p)) if p.c[i] < nokta)

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, row_heights=[0.5, 0.5])
    fig.add_trace(mumlar(p, "GC=F 5dk", hover=hover(p)), row=1, col=1)
    kutu(fig, b0 - 0.5, k - 0.5, alt, nokta, GRI, a=0.13, cizgi=1.0, row=1, col=1)
    yatay(fig, nokta, b0 - 0.5, len(p) - 0.5, renk=ALTIN, dash="solid", w=1.6, row=1, col=1)
    not_(fig, len(p) - 0.4, nokta, f"kırılım noktası {nokta:,.2f}", renk=ALTIN, ok=False,
         boyut=10, xanchor="left", row=1, col=1)
    kutu(fig, k - 0.45, k + 0.45, float(p.l[k]), float(p.h[k]), TURUNCU, a=0.20, cizgi=1.3,
         row=1, col=1)
    not_(fig, b0 + 6, alt - r * 0.55,
         f"piyasa {k - b0} bardır bu bantta: bağlam kırılımı olası kılmıyor",
         renk=GRI, ok=False, boyut=10, row=1, col=1)
    not_(fig, k, float(p.h[k]) + r * 0.35, "kırılım barı", renk=TURUNCU, ax=-30, ay=-30,
         boyut=10, row=1, col=1)
    not_(fig, geri_i, float(p.c[geri_i]) - r * 0.5,
         f"{geri_i - k}. barda kırılım noktasının altında kapanış", renk=BORDO, ax=26, ay=30,
         boyut=10, row=1, col=1)
    not_(fig, dip_i, dip - r * 0.10,
         f"başarısızlığın bedeli: dip {dip:,.2f} —<br>kırılım noktasının {nokta - dip:,.2f} altı "
         f"({(nokta - dip)/ort20:.1f}× ortalama bar)", renk=BORDO, ax=-186, ay=-34,
         boyut=10, row=1, col=1)
    _panel_baslik(fig, "Panel 1 — dar bandın yukarı kırılımı ve sonrası", 1)

    # ---- panel 2 · uyarı barları
    p2 = dilim(df, 8774, 22)
    k2 = KIR - 8774
    fig.add_trace(mumlar(p2, "GC=F 5dk (yakın)", hover=hover(p2)), row=2, col=1)
    yatay(fig, nokta, -0.5, len(p2) - 0.5, renk=ALTIN, dash="solid", w=1.6, row=2, col=1)
    yatay(fig, tetik, k2 - 0.4, len(p2) - 0.5, renk=MAVI, dash="dot", w=1.4, row=2, col=1)
    not_(fig, len(p2) - 0.4, tetik, f"alış stopu {tetik:,.2f} — hiç tetiklenmedi<br>"
                                    f"(sonraki en yüksek {sonra_max:,.2f})", renk=MAVI,
         ok=False, boyut=10, xanchor="left", row=2, col=1)
    yatay(fig, govde_orta, k2 - 0.4, k2 + 2.4, renk=GRI, dash="dot", w=1.2, row=2, col=1)
    uyarilar = [
        (k2, float(p2.h[k2]), f"① üst kuyruk: menzilin %{100*ust_kuyruk/r:.0f}'i "
                              f"({ust_kuyruk:,.2f} puan)<br>alıcılar tepede reddedildi",
         -170, -34),
        (k2 + 1, float(p2.h[k2 + 1]), "② takip yok: sonraki bar ters gövdeli ve<br>"
                                      "kırılım noktasının altında kapandı", 150, -46),
        (k2 + 1, float(p2.l[k2 + 1]), f"③ örtüşme: dip {p2.l[k2+1]:,.2f}, kırılım barının<br>"
                                      f"gövde ortasının ({govde_orta:,.2f}) altında", 130, 54),
        (k2 - 1, float(p2.l[k2 - 1]), f"④ mikro boşluk yok: önceki barın tepesi "
                                      f"{p2.h[k2-1]:,.2f}<br>> kırılım barının dibi "
                                      f"{p2.l[k2]:,.2f}", -120, 74),
    ]
    for x, y, metin, ax, ay in uyarilar:
        not_(fig, x, y, metin, renk=TURUNCU, ax=ax, ay=ay, boyut=10, row=2, col=1)
    kutu(fig, k2 - 0.45, k2 + 0.45, float(p2.c[k2]), float(p2.h[k2]), TURUNCU, a=0.26,
         cizgi=1.0, row=2, col=1)
    not_(fig, 0.6, float(p2.l.min()) + r * 0.55,
         "⑤ scalper kârı üretilmedi &nbsp;·&nbsp; ⑥ 'kafa karışıklığı' hissi —<br>"
         "Brooks'un başarısızlık listesinde bu da bir maddedir",
         renk=MUREKKEP, ok=False, boyut=10, xanchor="left", row=2, col=1)
    _panel_baslik(fig, "Panel 2 — zayıflığın erken uyarıları", 2)

    lejant_cizgi(fig, "kırılım noktası", ALTIN, dash="solid")
    lejant(fig, "uyarı", TURUNCU, a=0.22)
    duzen(fig, "Zayıf kırılımın erken uyarıları",
          "GC=F 5dk · 2026-07-29 11:45 kırılımı · pencere indisle pinli (bar 8758–8802) · "
          "müfredatın USDTRY 5dk serisi kotasyon artefaktlı olduğu için altın kullanıldı",
          h=980)
    fig.update_xaxes(title_text="", row=1, col=1)
    zaman_ekseni(fig, p, 8, "%H:%M", row=1, col=1)
    zaman_ekseni(fig, p2, 7, "%H:%M", row=2, col=1)
    kapsa(fig, 2, sag=6.0)
    kaydet(fig, "38_zayif_kirilim", olcum=dict(
        enstruman="GC=F 5dk", gun="2026-07-29", pencere_p1=[BAS, BAS + ADET - 1],
        pencere_p2=[8774, 8795], kirilim_bari=KIR, kirilim_noktasi=round(nokta, 2),
        bant_tabani=round(alt, 2), bant_bar_sayisi=k - b0, menzil=round(r, 2),
        ust_kuyruk=round(ust_kuyruk, 2), ust_kuyruk_orani=round(ust_kuyruk / r, 3),
        govde_ortasi=round(govde_orta, 2), tetiklenmeyen_alis_stopu=round(tetik, 2),
        sonraki_en_yuksek=round(sonra_max, 2), geri_donus_bari=geri_i - k,
        dip=round(dip, 2), dusus=round(nokta - dip, 2),
        dusus_ortalama_bar_kati=round((nokta - dip) / ort20, 2), uyari_sayisi=6))


# ================================================================== 39 · bir gündeki tüm kırılımlar
def _kirilim_denemeleri(d, k=3, pencere=20, takip=5):
    """Bir seansın kırılım denemeleri.

    Deneme = son `pencere` bar içinde oluşmuş bir salınım ucunu (k bar sağında ve
    solunda aşılmayan tepe/dip) ilk kez aşan bar. Başarılı = izleyen `takip` bar
    içinde kırılım noktasının bir ortalama bar boyu ötesine gidip geri dönmemesi.
    Ölçüt mekaniktir; ders metni tek tek tartışır.
    """
    n = len(d)
    ortbar = float((d.h - d.l).mean())
    sh = [i for i in range(k, n - k) if d.h[i] == max(d.h[i - k:i + k + 1])]
    sl = [i for i in range(k, n - k) if d.l[i] == min(d.l[i - k:i + k + 1])]
    out = []
    for i in range(k + 1, n):
        yukari = [s for s in sh if s < i - k and i - s <= pencere and d.h[i] > d.h[s]]
        if yukari:
            s = max(yukari, key=lambda x: d.h[x])
            if all(d.h[j] <= d.h[s] for j in range(s + 1, i)):
                son = min(n - 1, i + takip)
                ok = son > i and float(d.h[i + 1:son + 1].max()) > d.h[s] + ortbar \
                    and float(d.l[i + 1:son + 1].min()) > d.h[s] - 0.25 * ortbar
                out.append((i, "yukarı", float(d.h[s]), bool(ok)))
        asagi = [s for s in sl if s < i - k and i - s <= pencere and d.l[i] < d.l[s]]
        if asagi:
            s = min(asagi, key=lambda x: d.l[x])
            if all(d.l[j] >= d.l[s] for j in range(s + 1, i)):
                son = min(n - 1, i + takip)
                ok = son > i and float(d.l[i + 1:son + 1].min()) < d.l[s] - ortbar \
                    and float(d.h[i + 1:son + 1].max()) < d.l[s] + 0.25 * ortbar
                out.append((i, "aşağı", float(d.l[s]), bool(ok)))
    return out


def f39_kirilim_denemeleri():
    """G · XU030 5dk · 2 panel — bir seanstaki bütün kırılım denemeleri ve sayımı."""
    df = yukle("XU030.IS", "5m")
    if df is None:
        return
    BAS, ADET = 5135, 97                        # 2026-08-14 seansı · indisle pinli
    p = dilim(df, BAS, ADET)
    den = _kirilim_denemeleri(p)
    basarili = [x for x in den if x[3]]
    basarisiz = [x for x in den if not x[3]]
    oran = 100 * len(basarisiz) / len(den)
    yayilim = float(p.h.max() - p.l.min())

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13, row_heights=[0.68, 0.32])
    fig.add_trace(mumlar(p, "XU030 5dk", hover=hover(p)), row=1, col=1)
    for no, (i, yon, nokta, ok) in enumerate(den, 1):
        renk = YESIL if ok else TURUNCU
        yatay(fig, nokta, max(0, i - 14), min(len(p) - 1, i + 6), renk=renk, dash="dot",
              w=1.1, row=1, col=1)
        if yon == "yukarı":
            not_(fig, i, float(p.h[i]) + yayilim * 0.012, f"<b>{no}</b>", renk=renk,
                 ax=0, ay=-26, boyut=11, row=1, col=1)
        else:
            not_(fig, i, float(p.l[i]) - yayilim * 0.012, f"<b>{no}</b>", renk=renk,
                 ax=0, ay=26, boyut=11, row=1, col=1)
    i_ok = basarili[0][0]
    not_(fig, i_ok, float(p.l[i_ok:i_ok + 8].min()) - yayilim * 0.02,
         f"tek başarılı kırılım: {basarili[0][1]} yönde, {basarili[0][2]:,.0f} seviyesi<br>"
         f"→ sonraki 5 barda {p.l[i_ok+1:i_ok+6].min():,.0f}", renk=YESIL, ax=-118, ay=54,
         boyut=10, row=1, col=1)
    not_(fig, 6, float(p.l.min()) + yayilim * 0.05,
         f"seansta {len(den)} kırılım denemesi işaretlendi", renk=MUREKKEP, ok=False,
         boyut=11, xanchor="left", row=1, col=1)
    _panel_baslik(fig, "Panel 1 — seansın her kırılım denemesi numaralı "
                       "(turuncu: başarısız · yeşil: başarılı)", 1)

    fig.add_trace(go.Bar(x=["başarısız", "başarılı"], y=[len(basarisiz), len(basarili)],
                         marker=dict(color=[rgba(TURUNCU, 0.75), rgba(YESIL, 0.75)],
                                     line=dict(color=[TURUNCU, YESIL], width=1.3)),
                         text=[f"{len(basarisiz)}", f"{len(basarili)}"], textposition="outside",
                         showlegend=False, width=0.45), row=2, col=1)
    not_(fig, 0.62, len(den) * 0.86,
         f"başarısızlık oranı %{oran:.0f} — Brooks: kırılımların yaklaşık %80'i başarısızdır;<br>"
         "en güçlü kırılımlar bile ~%30 başarısız olur", renk=MUREKKEP, ok=False, boyut=11,
         row=2, col=1)
    _panel_baslik(fig, "Panel 2 — sayım", 2)

    duzen(fig, "Bir gündeki bütün kırılım denemeleri",
          "XU030 5dk · 2026-08-14 seansı · pencere indisle pinli (bar 5135–5231) · "
          "deneme tanımı: son 20 barda oluşmuş bir salınım ucunun ilk kez aşılması",
          h=980)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    fig.update_yaxes(title_text="deneme sayısı", range=[0, len(den) + 1.2], row=2, col=1)
    zaman_ekseni(fig, p, 8, "%H:%M", row=1, col=1)
    kapsa(fig, 1, sag=4.0)
    kaydet(fig, "39_kirilim_denemeleri", olcum=dict(
        gun="2026-08-14", pencere=[BAS, BAS + ADET - 1], deneme_sayisi=len(den),
        basarili=len(basarili), basarisiz=len(basarisiz), basarisizlik_orani=round(oran, 1),
        denemeler=[dict(no=j + 1, bar=BAS + i, yon=yon, nokta=round(nk, 2), basarili=ok)
                   for j, (i, yon, nk, ok) in enumerate(den)]))


# ================================================================== 40 · temel dizi
TEMEL_DIZI = [
    (100.0, 101.2, 99.0, 100.8), (100.8, 101.8, 99.8, 100.0), (100.0, 101.0, 98.6, 99.2),
    (99.2, 101.0, 99.0, 100.6), (100.6, 101.9, 100.2, 100.6), (100.6, 102.0, 100.0, 101.8),
    (101.8, 104.4, 101.6, 104.2),                                # 6 · ① kırılım
    (104.2, 105.0, 103.4, 103.6),
    (103.6, 103.8, 101.4, 101.6), (101.6, 101.8, 100.4, 100.8),  # 8-9 · ② başarısızlık
    (100.8, 102.4, 100.6, 102.2), (102.2, 103.6, 102.0, 103.4),  # 10-11 · ③ geri çekilme
    (103.4, 105.6, 103.2, 105.4), (105.4, 107.4, 105.2, 107.0),  # 12-14 · ④ devam
    (107.0, 108.6, 106.6, 108.2),
]


def f40_temel_dizi():
    """Ş · 1 panel — kırılım → başarısızlık → pullback → devam, her evrede emir yeri."""
    d = df_yap(TEMEL_DIZI)
    n = len(d)
    NOKTA = 102.0
    bant_alt = float(d.l[:6].min())
    yuk = NOKTA - bant_alt
    giris1, stop1 = NOKTA + 0.1, bant_alt - 0.1
    giris2, stop2 = float(d.h[10]) + 0.1, float(d.l[9]) - 0.1
    hedef = NOKTA + yuk

    fig = go.Figure()
    fig.add_trace(mumlar(d, "şematik"))
    kutu(fig, -0.5, 5.5, bant_alt, NOKTA, GRI, a=0.11, cizgi=1.0)
    yatay(fig, NOKTA, -0.5, n - 0.5, renk=ALTIN, dash="solid", w=1.7)
    not_(fig, n - 0.4, NOKTA, "kırılım noktası 102,0", renk=ALTIN, ok=False, boyut=10,
         xanchor="left")

    evreler = [
        (6, 7, "① KIRILIM", ALTIN, f"alış stopu {giris1:.1f} (bandın 1 tick üstü)"),
        (8, 9, "② BAŞARISIZLIK", TURUNCU, f"stop {stop1:.1f} tetiklendi — kırılım geri alındı"),
        (10, 11, "③ GERİ ÇEKİLME", TEAL, f"ikinci giriş: alış stopu {giris2:.1f}\n"
                                         f"(başarısızlığın başarısızlığı)"),
        (12, 14, "④ DEVAM", YESIL, f"ölçülmüş hareket {hedef:.1f} = kırılım noktası + "
                                   f"bant yüksekliği {yuk:.1f}"),
    ]
    tepe = float(d.h.max())
    for x0, x1, ad, renk, aciklama in evreler:
        kutu(fig, x0 - 0.45, x1 + 0.45, float(d.l[x0:x1 + 1].min()) - 0.25,
             float(d.h[x0:x1 + 1].max()) + 0.25, renk, a=0.13, cizgi=1.1)
        not_(fig, (x0 + x1) / 2, tepe + 1.6, f"<b>{ad}</b>", renk=renk, ok=False, boyut=12)
        not_(fig, (x0 + x1) / 2, tepe + 0.75, aciklama.replace("\n", "<br>"), renk=renk,
             ok=False, boyut=10)

    yatay(fig, giris1, 5.6, 9.4, renk=MAVI, dash="solid", w=1.5)
    not_(fig, 5.6, giris1, f"giriş 1 {giris1:.1f}", renk=MAVI, ok=False, boyut=10,
         xanchor="right")
    yatay(fig, stop1, 5.6, 9.4, renk=BORDO, dash="dot", w=1.5)
    not_(fig, 5.6, stop1, f"stop 1 {stop1:.1f}", renk=BORDO, ok=False, boyut=10,
         xanchor="right")
    yatay(fig, giris2, 10.6, n - 0.5, renk=MAVI, dash="solid", w=1.6)
    not_(fig, n - 0.4, giris2, f"giriş 2 {giris2:.1f}", renk=MAVI, ok=False, boyut=10,
         xanchor="left")
    yatay(fig, stop2, 10.6, n - 0.5, renk=BORDO, dash="dot", w=1.5)
    not_(fig, n - 0.4, stop2, f"stop 2 {stop2:.1f} (risk {giris2 - stop2:.1f} = 1R)",
         renk=BORDO, ok=False, boyut=10, xanchor="left")
    yatay(fig, hedef, 10.6, n - 0.5, renk=MOR, dash="dash", w=1.5)
    not_(fig, n - 0.4, hedef, f"hedef {hedef:.1f}  ({(hedef - giris2)/(giris2 - stop2):.1f}R)",
         renk=MOR, ok=False, boyut=10, xanchor="left")
    not_(fig, 2.0, bant_alt - 1.15,
         "Brooks'un temel dizisi: piyasa önce kırar, sonra kırılımı bozar, sonra bozulmayı "
         "bozar. En güvenilir giriş üçüncü adımdadır.", renk=MUREKKEP, ok=False, boyut=11,
         xanchor="left")

    lejant_cizgi(fig, "giriş", MAVI, dash="solid")
    lejant_cizgi(fig, "stop", BORDO, dash="dot")
    lejant_cizgi(fig, "hedef", MOR)
    duzen(fig, "Temel dizi: kırılım → başarısızlık → pullback → devam",
          "dört evre numaralı; her evrede emrin yeri", h=700, sematik=True)
    fig.update_xaxes(range=[-1.4, n + 4.2])
    fig.update_yaxes(range=[bant_alt - 1.7, tepe + 2.4])
    kaydet(fig, "40_temel_dizi", olcum=dict(
        kirilim_noktasi=NOKTA, bant_tabani=bant_alt, bant_yuksekligi=round(yuk, 2),
        evre_barlari={"kirilim": [6, 7], "basarisizlik": [8, 9], "geri_cekilme": [10, 11],
                      "devam": [12, 14]},
        giris1=round(giris1, 2), stop1=round(stop1, 2),
        giris2=round(giris2, 2), stop2=round(stop2, 2), risk2=round(giris2 - stop2, 2),
        hedef=round(hedef, 2), r_kati=round((hedef - giris2) / (giris2 - stop2), 2)))


# ================================================================== 41 · kırılım testi ve başabaş stop avı
TEST_ONEK = [
    (100.2, 101.2, 99.4, 100.8), (100.8, 102.0, 100.0, 100.4), (100.4, 101.4, 99.6, 101.2),
    (101.2, 102.0, 100.6, 101.9),
    (101.9, 104.6, 101.7, 104.4),                    # 4 · kırılım barı
    (104.4, 105.4, 103.8, 105.0), (105.0, 105.6, 103.6, 103.9),
]
TEST_VURAN = [(103.9, 104.0, 102.0, 102.4), (102.4, 103.2, 102.1, 103.0),
              (103.0, 104.6, 102.8, 104.4), (104.4, 106.4, 104.2, 106.2),
              (106.2, 107.6, 105.8, 107.2)]
TEST_MUKEMMEL = [(103.9, 104.0, 102.2, 102.6), (102.6, 103.4, 102.3, 103.2),
                 (103.2, 104.8, 103.0, 104.6), (104.6, 106.6, 104.4, 106.4),
                 (106.4, 107.8, 106.0, 107.4)]


def f41_kirilim_testi():
    """Ş · 2 panel — test kırılım noktasına tam dönüyor / bir tick beride kalıyor."""
    NOKTA = 102.0
    giris = NOKTA + 0.1
    stop_ilk = 99.4 - 0.1
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11)

    for row, kuyruk, baslik, sonuc, renk in (
            (1, TEST_VURAN, "Panel 1 — test kırılım noktasına tam dönüyor",
             "başabaş stop tetiklendi: pozisyon 0R'de kapandı, hareket sensiz devam etti", BORDO),
            (2, TEST_MUKEMMEL, "Panel 2 — mükemmel kırılım testi",
             "test 1 tick beride durdu: başabaş stop hayatta, pozisyon hareketi taşıdı", TEAL)):
        d = df_yap(TEST_ONEK + kuyruk)
        n = len(d)
        fig.add_trace(mumlar(d, "şematik", hover=None), row=row, col=1)
        kutu(fig, -0.5, 3.5, float(d.l[:4].min()), NOKTA, GRI, a=0.11, cizgi=1.0, row=row, col=1)
        yatay(fig, NOKTA, -0.5, n - 0.5, renk=ALTIN, dash="solid", w=1.7, row=row, col=1)
        not_(fig, n - 0.4, NOKTA, "kırılım noktası 102,0", renk=ALTIN, ok=False, boyut=10,
             xanchor="left", row=row, col=1)
        yatay(fig, giris, 3.6, n - 0.5, renk=MAVI, dash="solid", w=1.5, row=row, col=1)
        not_(fig, n - 0.4, giris, f"giriş {giris:.1f} = başabaş stop", renk=MAVI, ok=False,
             boyut=10, xanchor="left", row=row, col=1)
        yatay(fig, stop_ilk, 3.6, 7.4, renk=BORDO, dash="dot", w=1.3, row=row, col=1)
        not_(fig, 3.6, stop_ilk, f"ilk stop {stop_ilk:.1f}", renk=BORDO, ok=False, boyut=10,
             xanchor="right", row=row, col=1)
        test_dip = float(d.l[7])
        kutu(fig, 6.55, 8.45, min(test_dip, giris) - 0.15, max(test_dip, giris) + 0.15,
             renk, a=0.16, cizgi=1.1, row=row, col=1)
        not_(fig, 7, test_dip - 0.55,
             f"testin dibi {test_dip:.1f} — başabaş stopun {test_dip - giris:+.1f} "
             f"{'altında' if test_dip < giris else 'üstünde'}", renk=renk, ax=-28, ay=36,
             boyut=10, row=row, col=1)
        not_(fig, 9.2, float(d.h.max()) + 0.5, sonuc, renk=renk, ok=False, boyut=11,
             row=row, col=1)
        not_(fig, 4, float(d.h[4]) + 0.35, "kırılım barı", renk=ALTIN, ok=False, boyut=10,
             yanchor="bottom", row=row, col=1)
        fig.update_yaxes(range=[98.6, float(d.h.max()) + 1.5], row=row, col=1)
        _panel_baslik(fig, baslik, row)

    lejant_cizgi(fig, "kırılım noktası / başabaş", ALTIN, dash="solid")
    duzen(fig, "Kırılım testi ve başabaş stop avı",
          "iki varyantın tek farkı testin dibi: 102,0 ile 102,2 arasındaki 2 tick "
          "işlemin sonucunu belirliyor", h=900, sematik=True)
    fig.update_xaxes(title_text="", row=1, col=1)
    kaydet(fig, "41_kirilim_testi", olcum=dict(
        kirilim_noktasi=NOKTA, giris=round(giris, 2), basabas_stop=round(giris, 2),
        ilk_stop=round(stop_ilk, 2), test_dibi_vuran=102.0, test_dibi_mukemmel=102.2,
        fark_tick=2, kirilim_bari=4, test_bari=7))


# ================================================================== 42 · bir tick / beş tick
TICK_ONEK = [(994, 997, 992, 996), (996, 999, 995, 998), (998, 1000, 996, 997),
             (997, 999, 995, 996), (996, 1000, 995, 999)]
TICK_BIR = [(999, 1001, 997, 997), (997, 998, 993, 994), (994, 995, 990, 991),
            (991, 993, 988, 989), (989, 991, 986, 987), (987, 989, 983, 984),
            (984, 986, 981, 982)]
TICK_BES = [(999, 1005, 998, 1000), (1000, 1001, 996, 997), (997, 998, 993, 994),
            (994, 996, 991, 992), (992, 993, 988, 989), (989, 991, 986, 987),
            (987, 988, 983, 984)]


def f42_tick_basarisizliklari():
    """Ş · 2 panel — bir tick'lik ve beş tick'lik başarısız kırılım."""
    SEVIYE = 1000
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11)
    olcumler = {}

    for row, kuyruk, baslik in ((1, TICK_BIR, "Panel 1 — bir tick'lik başarısız kırılım"),
                                (2, TICK_BES, "Panel 2 — beş tick başarısızlığı")):
        d = df_yap(TICK_ONEK + kuyruk)
        n = len(d)
        k = 5                                   # kırılım barı
        asim = int(d.h[k] - SEVIYE)
        giris = SEVIYE + 1                      # seviyenin 1 tick üstündeki alış stopu
        stop = int(d.l[k]) - 1
        fig.add_trace(mumlar(d, "şematik (tick)", hover=None), row=row, col=1)
        kutu(fig, -0.5, k - 0.5, float(d.l[:k].min()), SEVIYE, GRI, a=0.11, cizgi=1.0,
             row=row, col=1)
        yatay(fig, SEVIYE, -0.5, n - 0.5, renk=ALTIN, dash="solid", w=1.7, row=row, col=1)
        not_(fig, n - 0.4, SEVIYE, "kırılım noktası 1000", renk=ALTIN, ok=False, boyut=10,
             xanchor="left", row=row, col=1)
        yatay(fig, giris, k - 0.4, n - 0.5, renk=MAVI, dash="solid", w=1.5, row=row, col=1)
        not_(fig, n - 0.4, giris, f"alış stopu {giris} (+1 tick)", renk=MAVI, ok=False,
             boyut=10, xanchor="left", row=row, col=1)
        yatay(fig, stop, k - 0.4, n - 0.5, renk=BORDO, dash="dot", w=1.4, row=row, col=1)
        not_(fig, n - 0.4, stop, f"stop {stop} (risk {giris - stop} tick)", renk=BORDO,
             ok=False, boyut=10, xanchor="left", row=row, col=1)
        kutu(fig, k - 0.45, k + 0.45, SEVIYE, float(d.h[k]), TURUNCU, a=0.28, cizgi=1.2,
             row=row, col=1)
        not_(fig, k, float(d.h[k]) + 1.6, f"aşım {asim} tick", renk=TURUNCU, ax=-26, ay=-28,
             boyut=10, row=row, col=1)
        if row == 2:
            hedef = giris + 4
            yatay(fig, hedef, k - 0.4, n - 0.5, renk=MOR, dash="dash", w=1.5, row=row, col=1)
            not_(fig, n - 0.4, hedef, f"scalp hedefi {hedef} (+4 tick)", renk=MOR, ok=False,
                 boyut=10, xanchor="left", row=row, col=1)
            not_(fig, k + 1.6, SEVIYE + 4.2,
                 f"altı tick kuralı: 4 tick'lik hedefin dolması için piyasanın {hedef+1}–"
                 f"{hedef+2}'e gitmesi gerekir.<br>Piyasa tam {int(d.h[k])}'e değdi ve döndü → "
                 "emir dolmadı, sonra stop tetiklendi.", renk=MOR, ok=False, boyut=10,
                 row=row, col=1)
            olcumler["bes_tick"] = dict(asim=asim, giris=giris, stop=stop, hedef=hedef,
                                        gereken_dolum=hedef + 1,
                                        ulasilan=int(d.h[k]), doldu=False)
        else:
            not_(fig, k + 1.8, SEVIYE + 3.0,
                 "Klasik tuzak: seviye tam 1 tick aşılır, kapanış içeriye döner.<br>"
                 "Kırılımı alan boğalar hapsolur; onların stopu satıcıya yakıt olur.",
                 renk=TURUNCU, ok=False, boyut=10, row=row, col=1)
            olcumler["bir_tick"] = dict(asim=asim, giris=giris, stop=stop,
                                        kapanis=int(d.c[k]), doldu=False)
        dip = int(d.l.min())
        not_(fig, n - 2, dip + 1.0, f"dönüşün getirdiği yer: {dip}", renk=BORDO, ok=False,
             boyut=10, row=row, col=1)
        fig.update_yaxes(range=[dip - 3, 1010], title_text="fiyat (tick)", row=row, col=1)
        _panel_baslik(fig, baslik, row)

    lejant_cizgi(fig, "kırılım noktası", ALTIN, dash="solid")
    lejant(fig, "aşım", TURUNCU, a=0.28)
    duzen(fig, "Bir-tick ve beş-tick başarısızlığı",
          "eksen tick cinsinden · seviye 1000 tick", h=900, sematik=True)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_yaxes(title_text="fiyat (tick)", row=1, col=1)
    fig.update_yaxes(title_text="fiyat (tick)", row=2, col=1)
    kaydet(fig, "42_tick_basarisizliklari", olcum=dict(seviye=SEVIYE, **olcumler))


# ================================================================== 43 · ekranın soluna bak
def f43_ekranin_solu():
    """G · XU100 5dk · 2 panel — aynı kırılım barı, iki bağlam, ters karar.

    Müfredat USDTRY 5dk diyor; o seri kotasyon artefaktlı (dosya başı notu).
    BIST100 5 dakika kullanıldı (aynı ailede, gerçek bar yapısı var).
    """
    df = yukle("XU100.IS", "5m")
    if df is None:
        return
    # --- panel 1: soldaki zirve tavan yapıyor
    A_BAS, A_ADET, A_KIR = 1166, 58, 1209
    a = dilim(df, A_BAS, A_ADET)
    ka = A_KIR - A_BAS
    kucuk_ust = float(a.h[ka - 10:ka].max())            # kırılan küçük bant tavanı
    sol_tepe = float(a.h[:ka - 20].max())               # sabahın arz bölgesinin tepesi
    sol_i = int(np.argmax(a.h.values[:ka - 20]))
    # en yakın tavan: kırılım noktasının hemen üstünde kalan en alçak eski tepe
    adaylar = [(float(a.h[i]), i) for i in range(ka - 20) if float(a.h[i]) > kucuk_ust]
    yakin_tavan, yakin_i = min(adaylar)
    tepe_sonra = float(a.h[ka:ka + 6].max())
    tepe_i = int(np.argmax(a.h.values[ka:ka + 6])) + ka
    dip_sonra = float(a.l[ka:].min())
    dip_i = int(np.argmin(a.l.values[ka:])) + ka
    ort_a = float((a.h - a.l).mean())

    # --- panel 2: solda tavan yok
    B_BAS, B_ADET, B_KIR = 3305, 56, 3345
    b = dilim(df, B_BAS, B_ADET)
    kb = B_KIR - B_BAS
    b_sol = float(b.h[:kb - 20].max())
    b_sol_i = int(np.argmax(b.h.values[:kb - 20]))
    b_kucuk = float(b.h[kb - 10:kb].max())
    b_tepe = float(b.h[kb:].max())
    b_tepe_i = int(np.argmax(b.h.values[kb:])) + kb
    ort_b = float((b.h - b.l).mean())

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11)

    fig.add_trace(mumlar(a, "XU100 5dk", hover=hover(a)), row=1, col=1)
    kutu(fig, sol_i - 0.5, len(a) - 0.5, yakin_tavan, sol_tepe, BORDO, a=0.10, cizgi=0.8,
         dash="dot", row=1, col=1)
    yatay(fig, yakin_tavan, yakin_i, len(a) - 0.5, renk=BORDO, dash="dash", w=1.7,
          row=1, col=1)
    not_(fig, len(a) - 0.4, yakin_tavan, f"en yakın eski tavan {yakin_tavan:,.2f} — taşındı",
         renk=BORDO, ok=False, boyut=10, xanchor="left", row=1, col=1)
    yatay(fig, sol_tepe, sol_i, len(a) - 0.5, renk=BORDO, dash="dot", w=1.2, row=1, col=1)
    not_(fig, len(a) - 0.4, sol_tepe, f"arz bölgesinin tepesi {sol_tepe:,.0f}", renk=BORDO,
         ok=False, boyut=10, xanchor="left", row=1, col=1)
    yatay(fig, kucuk_ust, ka - 12, len(a) - 0.5, renk=ALTIN, dash="solid", w=1.4, row=1, col=1)
    not_(fig, len(a) - 0.4, kucuk_ust, f"küçük bandın tavanı {kucuk_ust:,.0f}", renk=ALTIN,
         ok=False, boyut=10, xanchor="left", row=1, col=1)
    kutu(fig, ka - 0.45, ka + 0.45, float(a.l[ka]), float(a.h[ka]), ALTIN, a=0.20, cizgi=1.3,
         row=1, col=1)
    not_(fig, ka, float(a.l[ka]) - ort_a * 0.9,
         "kırılım barı: tıraşlı boğa barı, kapanış tepede — tek başına 'al' diyor",
         renk=ALTIN, ax=-56, ay=44, boyut=10, row=1, col=1)
    not_(fig, sol_i + 3, (yakin_tavan + sol_tepe) / 2,
         f"ekranın solu: sabahın arz bölgesi — üst üste eski tepeler<br>"
         f"{yakin_tavan:,.2f} … {sol_tepe:,.2f}, kırılımdan {ka - sol_i}–{ka - yakin_i} bar önce",
         renk=BORDO, ax=96, ay=44, boyut=10, row=1, col=1)
    not_(fig, tepe_i, tepe_sonra + ort_a * 0.35,
         f"kırılım {tepe_sonra:,.2f}'de durdu:<br>en yakın eski tavanın yalnızca "
         f"{tepe_sonra - yakin_tavan:+,.2f} üstü", renk=TURUNCU, ax=-72, ay=-46,
         boyut=10, row=1, col=1)
    not_(fig, dip_i, dip_sonra + ort_a * 0.2,
         f"sonuç: {dip_sonra:,.0f} — kırılım noktasının {kucuk_ust - dip_sonra:,.0f} altı",
         renk=BORDO, ax=-58, ay=34, boyut=10, row=1, col=1)
    _panel_baslik(fig, "Panel 1 — geniş bandın içindeki küçük bant kırılımı: solda tavan var", 1)

    fig.add_trace(mumlar(b, "XU100 5dk", hover=hover(b)), row=2, col=1)
    yatay(fig, b_sol, b_sol_i, len(b) - 0.5, renk=GRI, dash="dash", w=1.5, row=2, col=1)
    not_(fig, len(b) - 0.4, b_sol, f"soldaki tek zirve {b_sol:,.0f}<br>"
                                   f"= kırılım noktasının {b_kucuk - b_sol:,.0f} ALTINDA",
         renk=GRI, ok=False, boyut=10, xanchor="left", row=2, col=1)
    yatay(fig, b_kucuk, kb - 12, len(b) - 0.5, renk=ALTIN, dash="solid", w=1.4, row=2, col=1)
    not_(fig, len(b) - 0.4, b_kucuk, f"kırılım noktası {b_kucuk:,.0f}", renk=ALTIN, ok=False,
         boyut=10, xanchor="left", row=2, col=1)
    kutu(fig, kb - 0.45, kb + 0.45, float(b.l[kb]), float(b.h[kb]), ALTIN, a=0.20, cizgi=1.3,
         row=2, col=1)
    not_(fig, kb, float(b.l[kb]) - ort_b * 0.9,
         "aynı görünümde kırılım barı: tıraşlı boğa barı, kapanış tepede",
         renk=ALTIN, ax=-46, ay=44, boyut=10, row=2, col=1)
    kutu(fig, b_sol_i - 0.5, b_sol_i + 1.5, float(b.l[b_sol_i:b_sol_i + 2].min()),
         float(b.h[b_sol_i:b_sol_i + 2].max()), GRI, a=0.12, cizgi=1.0, row=2, col=1)
    not_(fig, b_sol_i + 1, float(b.h[b_sol_i]) + ort_b * 0.4,
         "ekranın solu: yolda engel yok", renk=GRI, ax=40, ay=-30, boyut=10, row=2, col=1)
    not_(fig, b_tepe_i, b_tepe + ort_b * 0.3,
         f"kırılım koştu: {b_tepe:,.0f} — kırılım noktasının {b_tepe - b_kucuk:,.0f} üstü "
         f"({(b_tepe - b_kucuk)/ort_b:.1f}× ortalama bar)", renk=YESIL, ax=-40, ay=-34,
         boyut=10, row=2, col=1)
    _panel_baslik(fig, "Panel 2 — aynı kalıbın gerçek trend hâli: solda bar yok", 2)

    lejant_cizgi(fig, "soldaki zirve", BORDO, dash="dash")
    lejant_cizgi(fig, "kırılım noktası", ALTIN, dash="solid")
    duzen(fig, "«Ekranın soluna bak»: aynı bar, iki bağlam, ters karar",
          "XU100 5dk · pencereler indisle pinli (1166–1223 ve 3305–3360) · "
          "karşılaştırma penceresi 20–30 bar · müfredatın USDTRY 5dk serisi kotasyon "
          "artefaktlı olduğu için BIST100 kullanıldı", h=980)
    fig.update_xaxes(title_text="", row=1, col=1)
    zaman_ekseni(fig, a, 8, "%d %b %H:%M", row=1, col=1)
    zaman_ekseni(fig, b, 8, "%d %b %H:%M", row=2, col=1)
    kapsa(fig, 2, pay=0.14, sag=19.0)
    kaydet(fig, "43_ekranin_solu", olcum=dict(
        enstruman="XU100.IS 5dk",
        panel1=dict(pencere=[A_BAS, A_BAS + A_ADET - 1], kirilim_bari=A_KIR,
                    arz_bolgesi_tepesi=round(sol_tepe, 2), arz_bolgesi_bari=A_BAS + sol_i,
                    en_yakin_tavan=round(yakin_tavan, 2), en_yakin_tavan_bari=A_BAS + yakin_i,
                    mesafe_bar=ka - yakin_i, kirilim_noktasi=round(kucuk_ust, 2),
                    ulasilan_tepe=round(tepe_sonra, 2),
                    yakin_tavan_asimi=round(tepe_sonra - yakin_tavan, 2),
                    arz_tepesine_uzaklik=round(sol_tepe - tepe_sonra, 2),
                    sonraki_dip=round(dip_sonra, 2),
                    dusus=round(kucuk_ust - dip_sonra, 2)),
        panel2=dict(pencere=[B_BAS, B_BAS + B_ADET - 1], kirilim_bari=B_KIR,
                    soldaki_zirve=round(b_sol, 2), kirilim_noktasi=round(b_kucuk, 2),
                    zirve_kirilim_farki=round(b_kucuk - b_sol, 2),
                    ulasilan_tepe=round(b_tepe, 2), yukselis=round(b_tepe - b_kucuk, 2),
                    ortalama_bar_kati=round((b_tepe - b_kucuk) / ort_b, 2))))


# ================================================================== 44 · kırılıma giriş yolları
GIRIS_YOLLARI = [
    (100.0, 101.2, 99.2, 100.8), (100.8, 102.0, 100.0, 100.4), (100.4, 101.4, 99.4, 101.0),
    (101.0, 101.8, 100.2, 100.6), (100.6, 101.6, 99.8, 101.4), (101.4, 102.0, 100.8, 101.8),
    (101.8, 105.2, 101.6, 105.0),                                  # 6 · spike / kırılım barı
    (105.0, 106.4, 104.4, 106.0),                                  # 7 · takip barı
    (106.0, 106.2, 104.0, 104.4), (104.4, 105.0, 103.6, 104.8),    # 8-9 · geri çekilme
    (104.8, 107.0, 104.6, 106.8), (106.8, 108.4, 106.4, 108.0),    # 10-11 · devam
]


def f44_giris_yollari():
    """Ş · 2 panel — tek kırılım üzerinde altı giriş yolu + risk/ödül/olasılık ızgarası."""
    d = df_yap(GIRIS_YOLLARI)
    n = len(d)
    NOKTA, HEDEF = 102.0, 108.0
    yollar = [
        ("① spike kapanışında piyasa emri", 6, 105.0, 101.5, MAVI, "kesin", "yüksek"),
        ("② high 1 stop girişi", 7, 106.5, 101.5, MAVI, "kesin", "orta"),
        ("③ son çare (last-ditch) stopu", 6, 105.3, 101.5, TURUNCU, "kesin", "yüksek"),
        ("④ geri çekilmede limit alım", 9, 104.2, 103.5, TEAL, "olası", "orta"),
        ("⑤ kırılım testinde alım", 11, 102.2, 101.4, MOR, "düşük", "düşük"),
        ("⑥ fade: kırılımı satmak", 6, 105.0, 106.6, BORDO, "kesin", "—"),
    ]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12, row_heights=[0.55, 0.45])
    fig.add_trace(mumlar(d, "şematik", hover=None), row=1, col=1)
    kutu(fig, -0.5, 5.5, float(d.l[:6].min()), NOKTA, GRI, a=0.11, cizgi=1.0, row=1, col=1)
    yatay(fig, NOKTA, -0.5, n + 2.4, renk=ALTIN, dash="solid", w=1.7, row=1, col=1)
    not_(fig, n + 2.5, NOKTA - 0.45, "kırılım noktası 102,0", renk=ALTIN, ok=False,
         boyut=10, xanchor="left", row=1, col=1)
    yatay(fig, HEDEF, 6, n + 2.4, renk=MOR, dash="dash", w=1.5, row=1, col=1)
    not_(fig, n + 2.5, HEDEF, "ortak hedef 108,0", renk=MOR, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    isaret_yeri = {"①": (5.45, 105.0), "②": (7.0, 106.62), "③": (6.6, 105.62),
                   "④": (9.0, 104.02), "⑤": (11.0, 102.2), "⑥": (6.0, 104.45)}
    for ad, x, giris, stop, renk, _dolum, _olasilik in yollar:
        cizgi(fig, x - 0.4, giris, n + 2.4, giris, renk=renk, dash="dot", w=1.1, row=1, col=1)
        ix, iy = isaret_yeri[ad[0]]
        not_(fig, ix, iy, f"<b>{ad[0]}</b>", renk=renk, ok=False, boyut=13,
             xanchor="center", yanchor="middle", row=1, col=1)
    sag_etiket = [(106.50, "② high 1 stop girişi", MAVI),
                  (105.62, "③ son çare (last-ditch) stopu", TURUNCU),
                  (104.92, "① spike kapanışında piyasa emri · ⑥ fade (aynı fiyat, ters yön)", MAVI),
                  (104.15, "④ geri çekilmede limit alım", TEAL),
                  (102.62, "⑤ kırılım testinde alım — bu örnekte DOLMADI", MOR)]
    for y, metin, renk in sag_etiket:
        not_(fig, n + 2.5, y, metin, renk=renk, ok=False, boyut=10, xanchor="left",
             row=1, col=1)
    not_(fig, n / 2, float(d.h.max()) + 1.1,
         "Altı yolun hepsi meşru. Ayrım olasılıkta değil, üç şeyde: "
         "dolum kesinliği, risk büyüklüğü, kaçırma riski.",
         renk=MUREKKEP, ok=False, boyut=11, row=1, col=1)
    _panel_baslik(fig, "Panel 1 — tek kırılım, altı giriş noktası", 1)

    satirlar, kayit = [], []
    for ad, _x, giris, stop, _renk, dolum, kacirma in yollar:
        risk = abs(giris - stop)
        if ad.startswith("⑥"):
            odul = giris - NOKTA
            oran = odul / risk
            not_metni = "trende karşı; yalnızca bant bağlamında"
        else:
            odul = HEDEF - giris
            oran = odul / risk
            not_metni = {"①": "kurumsal davranış: spike'ta gir, presle",
                         "②": "en güvenli dolum, en kötü denklem",
                         "③": "trendi kaçırmamak için ödenen prim",
                         "④": "en iyi denklem; dolmama riski var",
                         "⑤": "en iyi denklem, en düşük dolum olasılığı"}[ad[0]]
        satirlar.append([ad, f"{giris:.1f}", f"{stop:.1f}", f"{risk:.1f}", f"{odul:.1f}",
                         f"{oran:.1f}R", dolum, kacirma, not_metni])
        kayit.append(dict(yol=ad, giris=giris, stop=stop, risk=round(risk, 2),
                          odul=round(odul, 2), r=round(oran, 2), dolum=dolum,
                          kacirma_riski=kacirma))
    izgara(fig, 2, ["yol", "giriş", "stop", "risk", "ödül", "ödül/risk", "dolum", "kaçırma", "not"],
           satirlar, [0.005, 0.215, 0.275, 0.335, 0.392, 0.452, 0.535, 0.605, 0.675])
    _panel_baslik(fig, "Panel 2 — aynı hedefe altı denklem (şematik fiyatlarla)", 2)

    duzen(fig, "Kırılıma giriş yollarının haritası (altı yol)",
          "hedef altı yolda da 108,0; stop her yolun kendi gerekçesine göre", h=980,
          sematik=True)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(range=[-1.0, n + 15.5], showticklabels=False, row=1, col=1)
    fig.update_yaxes(range=[98.6, 110.8], row=1, col=1)
    kaydet(fig, "44_giris_yollari", olcum=dict(kirilim_noktasi=NOKTA, hedef=HEDEF,
                                               yollar=kayit))


# ================================================================== 45 · yeni zirvenin üç sonucu
BOGA_ONEK = [(100.0, 101.6, 99.6, 101.4), (101.4, 103.0, 101.0, 102.8),
             (102.8, 103.4, 101.8, 102.2), (102.2, 104.4, 102.0, 104.2),
             (104.2, 105.0, 103.4, 103.8), (103.8, 106.2, 103.6, 106.0)]
BOGA_DEVAM = [(106.0, 108.0, 105.8, 107.8), (107.8, 109.6, 107.4, 109.4),
              (109.4, 110.2, 108.6, 109.0), (109.0, 111.4, 108.8, 111.2),
              (111.2, 112.8, 110.8, 112.6)]
BOGA_BAYRAK = [(106.0, 106.4, 104.4, 104.8), (104.8, 105.4, 103.8, 104.2),
               (104.2, 105.0, 103.6, 104.8), (104.8, 106.6, 104.6, 106.4),
               (106.4, 108.4, 106.2, 108.2)]
BOGA_DONUS = [(106.0, 106.2, 103.8, 104.0), (104.0, 104.4, 102.0, 102.2),
              (102.2, 102.6, 100.4, 100.6), (100.6, 101.2, 98.8, 99.0),
              (99.0, 99.6, 97.4, 97.6)]
AYI_ONEK = [(100.0, 100.4, 98.4, 98.6), (98.6, 99.0, 97.0, 97.2),
            (97.2, 98.2, 96.6, 97.8), (97.8, 98.0, 95.6, 95.8),
            (95.8, 96.6, 95.0, 96.2), (96.2, 96.4, 94.0, 94.2)]
AYI_DEVAM = [(94.2, 94.4, 92.2, 92.4), (92.4, 92.6, 90.6, 90.8),
             (90.8, 91.6, 90.2, 91.2), (91.2, 91.4, 88.8, 89.0),
             (89.0, 89.4, 87.4, 87.6)]
AYI_BAYRAK = [(94.2, 96.0, 94.0, 95.6), (95.6, 96.4, 95.0, 95.4),
              (95.4, 96.2, 94.8, 95.2), (95.2, 95.4, 93.6, 93.8),
              (93.8, 94.0, 91.8, 92.0)]
AYI_DONUS = [(94.2, 96.4, 94.0, 96.2), (96.2, 98.4, 96.0, 98.2),
             (98.2, 99.0, 97.4, 98.8), (98.8, 101.0, 98.6, 100.8),
             (100.8, 102.6, 100.4, 102.4)]


def _uc_dal(fig, row, onek, dallar, uc_deger, uc_etiket, yon):
    """Ortak öneki üç kez çizip her seferinde farklı devam kolunu ekler."""
    ARA = 3
    genislik = len(onek) + len(dallar[0][1])
    for k, (ad, kuyruk, renk, aciklama) in enumerate(dallar):
        d = df_yap(onek + kuyruk)
        x0 = k * (genislik + ARA)
        xs = list(range(x0, x0 + len(d)))
        fig.add_trace(go.Candlestick(
            x=xs, open=d.o, high=d.h, low=d.l, close=d.c, name=ad, showlegend=False,
            increasing=dict(line=dict(color=TEAL, width=1.1), fillcolor=rgba(TEAL, 0.55)),
            decreasing=dict(line=dict(color=BORDO, width=1.1), fillcolor=rgba(BORDO, 0.55)),
            whiskerwidth=0.15), row=row, col=1)
        yatay(fig, uc_deger, x0 - 0.5, x0 + len(d) - 0.5, renk=ALTIN, dash="solid", w=1.5,
              row=row, col=1)
        kutu(fig, x0 + len(onek) - 0.45, x0 + len(d) - 0.5,
             float(d.l[len(onek):].min()), float(d.h[len(onek):].max()),
             renk, a=0.12, cizgi=1.1, row=row, col=1)
        not_(fig, x0 + len(onek) - 1, uc_deger, uc_etiket, renk=ALTIN, ok=False, boyut=9,
             yanchor="bottom" if yon == "bull" else "top", row=row, col=1)
        yust = 114.6 if yon == "bull" else 105.2
        not_(fig, x0 + genislik / 2 - 0.5, yust, f"<b>{ad}</b>", renk=renk, ok=False,
             boyut=12, row=row, col=1)
        not_(fig, x0 + genislik / 2 - 0.5, yust - 1.5, aciklama, renk=MUREKKEP, ok=False,
             boyut=10, row=row, col=1)
    return 3 * genislik + 2 * ARA


def f45_yeni_zirve():
    """Ş · 2 panel — yeni zirvenin üç sonucu ve yeni dibin üç okuması."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12)
    UC_B, UC_A = 106.2, 94.0

    gen = _uc_dal(fig, 1, BOGA_ONEK, [
        ("① DEVAM", BOGA_DEVAM, TEAL,
         "yeni zirve gerçek kırılım: takip barları geliyor,<br>always-in boğa kalıyor"),
        ("② BAYRAK", BOGA_BAYRAK, ALTIN,
         "geri çekilme bir bayrağa dönüşüyor;<br>trend yönlü ikinci giriş doğuyor"),
        ("③ DÖNÜŞ", BOGA_DONUS, TURUNCU,
         "yeni zirve başarısız kırılım çıkıyor:<br>boğalar hapsoldu, ayılar devraldı")],
        UC_B, "yeni zirve", "bull")
    not_(fig, gen / 2 - 0.5, 96.4,
         "Güçlü boğa trendinde dağılım eşit değildir: karşı yönlü denemelerin yaklaşık "
         "%80'i ① ya da ②'ye, yani devama döner. ③ azınlıktır — ve dönüş için Brooks'un "
         "dört koşulu ayrıca aranır.", renk=MUREKKEP, ok=False, boyut=11, row=1, col=1)
    _panel_baslik(fig, "Panel 1 — boğa trendinde yeni zirve: üç olası sonuç", 1)
    fig.update_yaxes(range=[95.6, 116.4], row=1, col=1)
    fig.update_xaxes(range=[-1.2, gen + 0.6], showticklabels=False, row=1, col=1)

    gen2 = _uc_dal(fig, 2, AYI_ONEK, [
        ("① DEVAM", AYI_DEVAM, BORDO,
         "yeni dip gerçek kırılım: satış sürüyor,<br>always-in ayı kalıyor"),
        ("② BAYRAK", AYI_BAYRAK, ALTIN,
         "yukarı tepki bir ayı bayrağı:<br>trend yönlü satış kurulumu doğuyor"),
        ("③ DÖNÜŞ", AYI_DONUS, TEAL,
         "yeni dip başarısız kırılım çıkıyor:<br>ayılar hapsoldu, boğalar devraldı")],
        UC_A, "yeni dip", "bear")
    not_(fig, gen2 / 2 - 0.5, 106.6,
         "Ayna görüntüsü: güçlü ayı trendinde swing dibinin kırılması çoğunlukla devam ya da "
         "bayrak üretir; dönüş okuması ancak trend zayıflamışsa ağır basar.",
         renk=MUREKKEP, ok=False, boyut=11, row=2, col=1)
    _panel_baslik(fig, "Panel 2 — ayı trendinde yeni dip: aynanın öbür yüzü", 2)
    fig.update_yaxes(range=[86.4, 108.4], row=2, col=1)
    fig.update_xaxes(range=[-1.2, gen2 + 0.6], showticklabels=False, row=2, col=1)

    lejant_cizgi(fig, "yeni zirve / yeni dip", ALTIN, dash="solid")
    duzen(fig, "Yeni zirvenin üç sonucu / yeni dibin üç okuması",
          "aynı önek üç kez çizildi; tek fark devam kolu", h=980, sematik=True)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    kaydet(fig, "45_yeni_zirve_uc_sonuc", olcum=dict(
        boga_uc=UC_B, ayi_uc=UC_A, onek_bar=len(BOGA_ONEK), dal_bar=len(BOGA_DEVAM),
        dallar=["devam", "bayrak", "dönüş"],
        boga_devam_zirvesi=112.8, boga_bayrak_dibi=103.6, boga_donus_dibi=97.4,
        ayi_devam_dibi=87.4, ayi_bayrak_zirvesi=96.4, ayi_donus_zirvesi=102.6))


# ================================================================== main
def main():
    for f in (f30_bant_tanisi, f31_gradyan, f32_dar_bant, f33_barbwire, f34_ucgen_ailesi,
              f35_kirilim_modu, f36_kirilim_anatomisi, f37_guclu_kirilim, f38_zayif_kirilim,
              f39_kirilim_denemeleri, f40_temel_dizi, f41_kirilim_testi,
              f42_tick_basarisizliklari, f43_ekranin_solu, f44_giris_yollari, f45_yeni_zirve):
        f()
    defter_yaz()


if __name__ == "__main__":
    main()
