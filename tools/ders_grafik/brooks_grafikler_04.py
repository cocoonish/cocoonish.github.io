#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Al Brooks fiyat hareketi dersi — FİGÜR 46–63.

Kapsam (müfredat sürüm 2, "3. GRAFİK LİSTESİ" tablosu, 94 satır):
  B6  geri çekilme ve bar sayma ....... 46–52
  B7  hareketli ortalama hattı ........ 53–55
  B8A dönüşün anatomisi ............... 56–63

Şematik figürlerde barlar ELLE kurulur (kavramı gösteren geometri tesadüfe
bırakılmaz). Gerçek veri figürlerinde pencere İNDİSLE pinlenir; her koşuda
birebir aynı barlar çizilir.

Enstrüman sapması (raporlanır): müfredat 50 ve 54'ü USDTRY 5dk'ya bağlıyor.
Önbellekteki USDTRY OHLC mum düzeyinde kullanılamaz — gövde/menzil medyan oranı
0.06–0.09 (XU030 0.45, XAUUSD 0.42, XU100 0.52). Yani "gövde" yok, sadece
gürültü fitili var; bir sinyal barı ya da dönüş barı okumak mümkün değil.
Bu iki figür müfredatın öncelik listesindeki bir sonraki enstrümana, XAUUSD'ye
(GC=F) taşındı ve alt başlıkta belirtildi.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import brooks_ortak as b
from brooks_ortak import (TEAL, BORDO, ALTIN, MAVI, MOR, TURUNCU, GRI, YESIL,
                          MUREKKEP, rgba)

H1P, H2P, H3P = 580, 880, 1180        # 1 / 2 / 3 panelli figür yüksekliği


def B(o, c, ust=0.0, alt=0.0):
    """Kısayol: b.bar() — gövde + kuyruk uzunluklarıyla bar."""
    return b.bar(o, c, ust=ust, alt=alt)


def ayna(ohlc, k):
    """Bar dizisini k ekseninde dikey aynala (boğa kurgusu → ayı kurgusu)."""
    return [(k - o, k - l, k - h, k - c) for (o, h, l, c) in ohlc]


def panelsiz_x(fig, satir):
    fig.update_xaxes(title_text="", row=satir, col=1)


def lejant_tekille(fig):
    """Çok panelli figürlerde aynı ad birden çok ize düşer (her panelin mumları,
    her panelin EMA'sı). Lejantta ilkini bırak, kalanları gizle."""
    gorulen = set()
    for tr in fig.data:
        ad = getattr(tr, "name", None)
        if not ad:
            continue
        if ad in gorulen:
            tr.showlegend = False
        else:
            gorulen.add(ad)


# ==================================================================== 46
def f46_high_sayimi():
    """46 · Bar sayma: high 1-2-3-4 (Ş, 1 panel)."""
    ham = [
        B(100.0, 101.2, .3, .3), B(101.2, 102.6, .3, .3), B(102.5, 104.0, .4, .3),
        B(104.0, 105.4, .5, .3), B(105.3, 106.6, .6, .4),          # 0-4 boğa trendi
        B(106.5, 105.4, .3, .4), B(105.4, 104.4, .2, .4),          # 5-6 geri çekilme
        B(104.5, 105.3, .5, .3),                                   # 7  H1
        B(105.2, 104.0, .2, .4), B(104.0, 103.2, .2, .3),          # 8-9
        B(103.3, 104.2, .4, .3),                                   # 10 H2
        B(104.1, 103.0, .2, .4), B(103.0, 102.3, .2, .3),          # 11-12
        B(102.4, 103.2, .4, .3),                                   # 13 H3
        B(103.1, 102.2, .2, .5), B(102.2, 101.6, .3, .4),          # 14-15
        B(101.7, 103.4, .3, .2),                                   # 16 H4 — sinyal
        B(103.4, 104.6, .3, .2), B(104.6, 105.8, .3, .3),
        B(105.8, 107.0, .4, .3), B(107.0, 107.9, .5, .3),          # 17-20 devam
    ]
    df = b.df_yap(ham)
    isaret = b.bar_say(df, "bull")
    fig = go.Figure(b.mumlar(df))
    eski_tepe = df.h[4]
    b.yatay(fig, eski_tepe, 4, len(df) - 1, renk=GRI, dash="dash")
    b.not_(fig, len(df) - 1, eski_tepe, "trendin ucu (eski tepe)", renk=GRI, ok=False,
           boyut=10, xanchor="right", yanchor="bottom")
    b.kutu(fig, 4.6, 16.4, df.l[5:17].min() - .35, df.h[5:17].max() + .35, ALTIN, a=0.07)
    b.not_(fig, 10.5, df.l[5:17].min() - .55, "geri çekilme: yana–aşağı hareket",
           renk=ALTIN, ok=False, boyut=11, yanchor="top")
    b.not_(fig, 2, df.l[0] - .35, "boğa trendi", renk=TEAL, ok=False, boyut=11, yanchor="top")
    b.bar_etiketle(fig, df, isaret, "bull")
    for i, et in isaret:
        b.kutu(fig, i - .42, i + .42, df.l[i], df.h[i], TEAL, a=0.13, cizgi=1.0)
    b.not_(fig, 7, df.h[7] + 1.15, "H1: geri çekilmede önceki barın<br>yükseğini aşan İLK bar",
           renk=TEAL, ax=-6, ay=-34, boyut=10)
    b.not_(fig, 16, df.h[16] + 1.5, "H4: dördüncü deneme tuttu —<br>alış sinyali",
           renk=MAVI, ax=32, ay=-40, boyut=10)
    b.not_(fig, 20.4, 100.4, "sayaç, trend kaldığı yerden<br>devam edince sıfırlanır",
           renk=GRI, ok=False, boyut=10, xanchor="right")
    b.lejant(fig, "sayılan bar (H1–H4)", TEAL)
    b.lejant_cizgi(fig, "trendin ucu", GRI)
    lejant_tekille(fig)
    b.duzen(fig, "Bar sayma: high 1 – high 2 – high 3 – high 4",
            "boğa trendindeki geri çekilmede, önceki barın yükseğini aşan her bar bir sonraki sayıdır",
            h=H1P, sematik=True)
    b.kaydet(fig, "46_bar_sayma_high", olcum={
        "sayim": {e: i for i, e in isaret}, "h_sayisi": len(isaret),
        "eski_tepe": round(float(eski_tepe), 2),
        "h4_sinyal_yuksek": round(float(df.h[16]), 2),
        "h4_sinyal_dip": round(float(df.l[16]), 2)})


# ==================================================================== 47
def f47_low_sayimi():
    """47 · Bar sayma aynası: low 1-2-3-4 (Ş, 1 panel)."""
    ham = [
        B(100.0, 101.2, .3, .3), B(101.2, 102.6, .3, .3), B(102.5, 104.0, .4, .3),
        B(104.0, 105.4, .5, .3), B(105.3, 106.6, .6, .4),
        B(106.5, 105.4, .3, .4), B(105.4, 104.4, .2, .4), B(104.5, 105.3, .5, .3),
        B(105.2, 104.0, .2, .4), B(104.0, 103.2, .2, .3), B(103.3, 104.2, .4, .3),
        B(104.1, 103.0, .2, .4), B(103.0, 102.3, .2, .3), B(102.4, 103.2, .4, .3),
        B(103.1, 102.2, .2, .5), B(102.2, 101.6, .3, .4), B(101.7, 103.4, .3, .2),
        B(103.4, 104.6, .3, .2), B(104.6, 105.8, .3, .3), B(105.8, 107.0, .4, .3),
        B(107.0, 107.9, .5, .3),
    ]
    K = 208.0
    df = b.df_yap(ayna(ham, K))
    isaret = b.bar_say(df, "bear")
    fig = go.Figure(b.mumlar(df))
    eski_dip = df.l[4]
    b.yatay(fig, eski_dip, 4, len(df) - 1, renk=GRI, dash="dash")
    b.not_(fig, len(df) - 1, eski_dip, "trendin ucu (eski dip)", renk=GRI, ok=False,
           boyut=10, xanchor="right", yanchor="top")
    b.kutu(fig, 4.6, 16.4, df.l[5:17].min() - .35, df.h[5:17].max() + .35, ALTIN, a=0.07)
    b.not_(fig, 10.5, df.h[5:17].max() + .55, "geri çekilme: yana–yukarı hareket",
           renk=ALTIN, ok=False, boyut=11, yanchor="bottom")
    b.not_(fig, 2, df.h[0] + .35, "ayı trendi", renk=BORDO, ok=False, boyut=11, yanchor="bottom")
    b.bar_etiketle(fig, df, isaret, "bear")
    for i, et in isaret:
        b.kutu(fig, i - .42, i + .42, df.l[i], df.h[i], BORDO, a=0.13, cizgi=1.0)
    b.not_(fig, 7, df.l[7] - 1.15, "L1: geri çekilmede önceki barın<br>düşüğünün altına inen İLK bar",
           renk=BORDO, ax=-6, ay=34, boyut=10)
    b.not_(fig, 16, df.l[16] - 1.5, "L4: dördüncü deneme tuttu —<br>satış sinyali",
           renk=MAVI, ax=32, ay=40, boyut=10)
    b.lejant(fig, "sayılan bar (L1–L4)", BORDO)
    b.lejant_cizgi(fig, "trendin ucu", GRI)
    lejant_tekille(fig)
    b.duzen(fig, "Bar sayma aynası: low 1 – low 2 – low 3 – low 4",
            "46 numaralı figürün birebir dikey aynası: ayı trendinde geri çekilme, önceki barın düşüğünü kıran her bar sayılır",
            h=H1P, sematik=True)
    b.kaydet(fig, "47_bar_sayma_low", olcum={
        "sayim": {e: i for i, e in isaret}, "l_sayisi": len(isaret),
        "eski_dip": round(float(eski_dip), 2),
        "l4_sinyal_dip": round(float(df.l[16]), 2)})


# ==================================================================== 48
def f48_h2_trend_bant():
    """48 · Trend içi high 2 ile bant içi high 2 farkı (G, XU030 5dk, 2 panel)."""
    d = b.yukle("XU030.IS", "5m")
    if d is None:
        return
    p1 = b.dilim(d, 4978, 34)          # 12 Ağu 2026 — boğa trend günü
    p2 = b.dilim(d, 2259, 30)          # 2 Tem 2026 — bandın üst yarısı
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Panel 1 — güçlü boğa trendi içinde high 2 (12 Ağustos 2026, bar 4978–5011)",
        "Panel 2 — yatay bandın üst yarısında high 2 (2 Temmuz 2026, bar 2259–2288)"))

    fig.add_trace(b.mumlar(p1, "XU030 5dk", hover=b.hover(p1)), row=1, col=1)
    s1 = [x for x in b.bar_say(p1, "bull") if x[0] <= 13]
    b.bar_etiketle(fig, p1, s1, "bull", row=1, col=1)
    i1 = 11                                                   # H2 sinyal barı
    b.trend_cizgisi(fig, p1, (0, 11), yon="bull", renk=TEAL, dash="dash", row=1, col=1)
    tepe1 = float(p1.h[:11].max())
    b.yatay(fig, tepe1, 0, len(p1) - 1, renk=GRI, dash="dot", row=1, col=1)
    b.not_(fig, 1, tepe1, "geri çekilme öncesi tepe", renk=GRI, ok=False, boyut=10,
           xanchor="left", yanchor="bottom", row=1, col=1)
    t1 = b.islem(fig, p1, i1, "bull", hedefler=(tepe1, float(p1.h.max())),
                 etiketler=("eski tepe", "trend devamı"), ondalik=1, row=1, col=1)
    b.not_(fig, 20, float(p1.l.min()) + 8, "yön trendle aynı → high 2 alışı yüksek olasılıklı;<br>"
           "geri çekilme bir boğa bayrağıdır", renk=TEAL, ok=False, boyut=10, row=1, col=1)

    fig.add_trace(b.mumlar(p2, "XU030 5dk", hover=b.hover(p2)), row=2, col=1)
    s2 = [x for x in b.bar_say(p2, "bull") if 5 <= x[0] <= 12]
    b.bar_etiketle(fig, p2, s2, "bull", row=2, col=1)
    i2 = 11                                                   # H2 sinyal barı
    bant_ust = float(p2.h[5:20].max())
    bant_alt = float(p2.l[5:20].min())
    b.kutu(fig, 4.5, 22.5, bant_alt, bant_ust, GRI, a=0.10, cizgi=1.0, row=2, col=1)
    b.not_(fig, 13, bant_ust, "yatay bant", renk=GRI, ok=False, boyut=10,
           yanchor="bottom", row=2, col=1)
    t2 = b.islem(fig, p2, i2, "bull", hedefler=(bant_ust,), etiketler=("bant tepesi",),
                 ondalik=1, row=2, col=1)
    dip_sonra = float(p2.l[12:].min())
    b.not_(fig, 15, float(p2.l[12:18].min()) - 4,
           "stop bir sonraki barda alındı: bant tepesinde alım,<br>"
           "bandın en pahalı yerinden alım demektir", renk=TURUNCU, ax=40, ay=40,
           boyut=10, row=2, col=1)
    b.yatay(fig, dip_sonra, 12, len(p2) - 1, renk=TURUNCU, dash="dot", row=2, col=1)
    b.not_(fig, len(p2) - 1, dip_sonra, f"bandın dibi {dip_sonra:.1f}", renk=TURUNCU,
           ok=False, boyut=10, xanchor="left", row=2, col=1)

    b.lejant(fig, "sinyal barı", ALTIN)
    b.lejant_cizgi(fig, "giriş", MAVI, dash="solid")
    b.lejant_cizgi(fig, "stop", BORDO, dash="dot")
    b.lejant_cizgi(fig, "hedef", MOR)
    lejant_tekille(fig)
    b.duzen(fig, "Aynı kalıp, iki konum: trend içinde high 2 · bant içinde high 2",
            "XU030 5 dakika · pencereler indisle pinli (indis 4978–5011 · 2259–2288) · "
            "kurulum aynı, konum farklı — Brooks'ta olasılığı belirleyen kalıp değil piyasa döngüsündeki yerdir",
            h=H2P)
    b.zaman_ekseni(fig, p1, adet=7, fmt="%H:%M", row=1, col=1)
    b.zaman_ekseni(fig, p2, adet=7, fmt="%H:%M", row=2, col=1)
    panelsiz_x(fig, 1)
    b.kaydet(fig, "48_high2_trend_bant", olcum={
        "trend_giris": round(t1["giris"], 1), "trend_stop": round(t1["stop"], 1),
        "trend_risk": round(t1["risk"], 1), "trend_r": [round(x, 1) for x in t1["r"]],
        "bant_giris": round(t2["giris"], 1), "bant_stop": round(t2["stop"], 1),
        "bant_risk": round(t2["risk"], 1),
        "bant_sonrasi_dip": round(dip_sonra, 1),
        "bant_kayip_r": round((t2["giris"] - dip_sonra) / t2["risk"], 1),
        "p1_pencere": "XU030.IS 5m indis 4978–5011",
        "p2_pencere": "XU030.IS 5m indis 2259–2288"})


# ==================================================================== 49
def f49_abc():
    """49 · ABC düzeltmesi ve iki bacak ilkesi (Ş, 1 panel)."""
    ham = [
        B(100.0, 101.2, .3, .3), B(101.2, 102.5, .3, .3), B(102.5, 104.0, .4, .3),
        B(104.0, 105.6, .4, .3), B(105.6, 107.0, .5, .3), B(107.0, 108.2, .6, .3),  # 0-5
        B(108.2, 107.0, .3, .4), B(107.0, 105.6, .2, .4), B(105.6, 104.4, .2, .5),
        B(104.4, 103.6, .2, .5),                                                     # 6-9  A
        B(103.7, 104.8, .3, .3), B(104.8, 105.8, .4, .3), B(105.8, 106.4, .5, .3),   # 10-12 B
        B(106.4, 105.4, .2, .4), B(105.4, 104.4, .2, .4), B(104.4, 103.4, .2, .4),
        B(103.4, 102.4, .2, .5), B(102.4, 101.6, .3, .6),                            # 13-17 C
        B(101.7, 103.0, .3, .4),                                                     # 18 sinyal
        B(103.0, 104.4, .3, .2), B(104.4, 105.6, .3, .3), B(105.6, 106.8, .4, .3),
        B(106.8, 108.0, .4, .3), B(108.0, 109.2, .5, .3),
    ]
    df = b.df_yap(ham)
    fig = go.Figure(b.mumlar(df))
    x_tepe, a_dip, b_tepe, c_dip = float(df.h[5]), float(df.l[9]), float(df.h[12]), float(df.l[17])
    bacak1 = x_tepe - a_dip
    bacak2 = b_tepe - c_dip
    proj = b_tepe - bacak1

    b.cizgi(fig, 5, x_tepe, 9, a_dip, renk=BORDO, dash="dot", w=2.0)
    b.cizgi(fig, 9, a_dip, 12, b_tepe, renk=TEAL, dash="dot", w=2.0)
    b.cizgi(fig, 12, b_tepe, 17, c_dip, renk=BORDO, dash="dot", w=2.0)
    for x, y, et, r, ya, xa in [(5, x_tepe, "X · trendin ucu", GRI, "bottom", "right"),
                                (9, a_dip, "A · birinci bacağın dibi", BORDO, "top", "center"),
                                (12, b_tepe, "B · bacaklar arası tepe", TEAL, "bottom", "center")]:
        b.not_(fig, x, y, et, renk=r, ok=False, boyut=10, yanchor=ya, xanchor=xa)
    b.not_(fig, 17, c_dip, "C · ikinci bacağın dibi", renk=BORDO, ax=-78, ay=16, boyut=10)
    b.yatay(fig, proj, 8, 20, renk=MOR, dash="dash", w=1.6)
    b.not_(fig, 8, proj, f"bacak 1 = bacak 2 projeksiyonu {proj:.2f}", renk=MOR,
           ok=False, boyut=10, xanchor="left", yanchor="bottom")
    fig.add_shape(type="line", x0=6.6, y0=x_tepe, x1=6.6, y1=a_dip,
                  line=dict(color=BORDO, width=2.2))
    b.not_(fig, 7.0, x_tepe, f"bacak 1 = {bacak1:.2f}", renk=BORDO,
           ok=False, boyut=10, xanchor="left", yanchor="bottom")
    fig.add_shape(type="line", x0=15.4, y0=b_tepe, x1=15.4, y1=c_dip,
                  line=dict(color=BORDO, width=2.2))
    b.not_(fig, 15.9, (b_tepe + c_dip) / 2, f"bacak 2 = {bacak2:.2f}", renk=BORDO,
           ok=False, boyut=10, xanchor="left")
    t = b.islem(fig, df, 18, "bull", hedefler=(b_tepe, x_tepe),
                etiketler=("B tepesi", "eski tepe"))
    b.not_(fig, 8.2, 110.0, "piyasa iki kez dener: A bacağı yetmedi,<br>"
           "B'de toparlandı, C'de ikinci kez denedi ve döndü", renk=MUREKKEP,
           ok=False, boyut=10, xanchor="left", yanchor="top")
    b.lejant_cizgi(fig, "bacaklar", BORDO, dash="dot")
    b.lejant_cizgi(fig, "bacak 1 = bacak 2 hedefi", MOR)
    lejant_tekille(fig)
    b.duzen(fig, "ABC düzeltmesi: iki bacak ilkesi ve bacak 1 = bacak 2 projeksiyonu",
            "düzeltmeler tek bacakla bitmez; ikinci bacağın boyu birincininkine eşit varsayılır",
            h=H1P, sematik=True)
    b.kaydet(fig, "49_abc_duzeltme", olcum={
        "x_tepe": round(x_tepe, 2), "a_dip": round(a_dip, 2),
        "b_tepe": round(b_tepe, 2), "c_dip": round(c_dip, 2),
        "bacak1": round(bacak1, 2), "bacak2": round(bacak2, 2),
        "projeksiyon": round(proj, 2), "sapma": round(c_dip - proj, 2),
        "giris": round(t["giris"], 2), "stop": round(t["stop"], 2),
        "risk": round(t["risk"], 2), "r": [round(x, 1) for x in t["r"]]})


# ==================================================================== 50
def f50_kama_boga_bayragi():
    """50 · Kama boğa bayrağı — high 3 (G, XAUUSD/GC=F 15dk, 2 panel)."""
    d = b.yukle("GC=F", "15m")
    if d is None:
        return
    p1 = b.dilim(d, 2912, 30)          # 29 Tem 2026 — atak + üç itişli kama
    p2 = b.dilim(d, 2925, 32)          # aynı kamanın kırılımı ve ölçülmüş hareketi
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Panel 1 — atak, sonra üç itişli kama (bar 2912–2941)",
        "Panel 2 — kamanın kırılımı ve kama ölçülü hareketi (bar 2925–2956)"))

    fig.add_trace(b.mumlar(p1, "XAUUSD 15dk", hover=b.hover(p1)), row=1, col=1)
    it = [2928 - 2912, 2934 - 2912, 2940 - 2912]                # 16, 22, 28
    kama_tepe = float(p1.h[it[0]:it[2] + 1].max())
    kama_dip = float(p1.l[it[2]])
    b.cizgi(fig, it[0], float(p1.l[it[0]]), it[2] + 1,
            float(p1.l[it[0]]) + (float(p1.l[it[2]]) - float(p1.l[it[0]])) / (it[2] - it[0]) * (it[2] + 1 - it[0]),
            renk=ALTIN, dash="dash", w=1.8, row=1, col=1)
    ust_i, ust_j = it[0] + 3, it[1] + 2
    b.cizgi(fig, ust_i, float(p1.h[ust_i]), it[2] + 1,
            float(p1.h[ust_i]) + (float(p1.h[ust_j]) - float(p1.h[ust_i])) / (ust_j - ust_i) * (it[2] + 1 - ust_i),
            renk=ALTIN, dash="dot", w=1.8, row=1, col=1)
    for n, i in enumerate(it, 1):
        b.not_(fig, i, float(p1.l[i]), f"itiş {n}", renk=BORDO, ax=0, ay=34, boyut=10, row=1, col=1)
    b.not_(fig, 2, float(p1.h[2]) + 6, "atak (spike): kamayı önceleyen boğa hareketi",
           renk=TEAL, ok=False, boyut=10, xanchor="left", row=1, col=1)
    b.not_(fig, 12, kama_dip - 9, "yakınsayan çizgiler + küçülen itişler = kama boğa bayrağı;<br>"
           "üçüncü itişin sonu Brooks'un high 3 alışıdır", renk=ALTIN, ok=False, boyut=10, row=1, col=1)
    tick50 = (float(p1.h.max()) - float(p1.l.min())) * 0.004
    t = b.islem(fig, p1, it[2] + 1, "bull", stop=kama_dip - tick50,
                hedefler=(kama_tepe,), etiketler=("kama tepesi",), ondalik=1, row=1, col=1)
    b.not_(fig, it[2], kama_dip - tick50, "stop üçüncü itişin altında (sinyal barının değil)",
           renk=BORDO, ax=-6, ay=44, boyut=10, row=1, col=1)

    fig.add_trace(b.mumlar(p2, "XAUUSD 15dk", hover=b.hover(p2)), row=2, col=1)
    j_dip = 2940 - 2925                                          # 15
    j_kir = 2952 - 2925                                          # 27
    b.yatay(fig, kama_tepe, 0, len(p2) - 1, renk=ALTIN, dash="dash", row=2, col=1)
    b.not_(fig, 1, kama_tepe, "kama tepesi = kırılım noktası", renk=ALTIN, ok=False,
           boyut=10, xanchor="left", yanchor="bottom", row=2, col=1)
    hedef = b.olculmus_hareket(fig, j_dip, kama_dip, j_kir, kama_tepe, len(p2) - 1,
                               etiket="kama ölçülü hareketi", ondalik=1, row=2, col=1)
    b.not_(fig, j_kir, float(p2.h[j_kir]) + 4, "kırılım barı", renk=ALTIN, ax=-30, ay=-30,
           boyut=10, row=2, col=1)
    ulasan = int(np.argmax(p2.h.values > hedef)) if (p2.h.values > hedef).any() else -1
    if ulasan > 0:
        b.not_(fig, ulasan, float(p2.h[ulasan]), f"hedefe varış (bar {2925 + ulasan})",
               renk=MOR, ax=-10, ay=-34, boyut=10, row=2, col=1)
    b.lejant_cizgi(fig, "kama çizgileri", ALTIN)
    b.lejant_cizgi(fig, "ölçülmüş hareket", MOR)
    lejant_tekille(fig)
    b.duzen(fig, "Kama boğa bayrağı (high 3) ve kama ölçülü hareketi",
            "XAUUSD 15 dakika · müfredat bu figüre USDTRY 5dk verir; önbellekteki USDTRY OHLC'sinde "
            "gövde/menzil oranı 0,08 olduğu için bar okunamıyor, öncelik listesinin bir sonraki "
            "enstrümanına geçildi · pencereler indisle pinli (indis 2912–2941 · 2925–2956)",
            h=H2P)
    b.zaman_ekseni(fig, p1, adet=7, fmt="%d %b %H:%M", row=1, col=1)
    b.zaman_ekseni(fig, p2, adet=7, fmt="%d %b %H:%M", row=2, col=1)
    panelsiz_x(fig, 1)
    b.kaydet(fig, "50_kama_boga_bayragi", olcum={
        "itis_barlari": [2928, 2934, 2940],
        "itis_dipleri": [round(float(d.l[i]), 1) for i in (2928, 2934, 2940)],
        "kama_tepe": round(kama_tepe, 1), "kama_dip": round(kama_dip, 1),
        "kama_yuksekligi": round(kama_tepe - kama_dip, 1),
        "mm_hedef": round(hedef, 1), "hedefe_varan_bar": 2925 + ulasan if ulasan > 0 else None,
        "giris": round(t["giris"], 1), "stop": round(t["stop"], 1), "risk": round(t["risk"], 1),
        "mm_r": round((hedef - t["giris"]) / t["risk"], 1),
        "pencere": "GC=F 15m indis 2912–2956"})


# ==================================================================== 51
def f51_cift_dip_tepe_bayragi():
    """51 · Çift dip boğa bayrağı ve çift tepe ayı bayrağı (Ş, 2 panel)."""
    ham = [
        B(100.0, 101.3, .3, .3), B(101.3, 102.7, .3, .3), B(102.7, 104.2, .4, .3),
        B(104.2, 105.8, .4, .3), B(105.8, 107.0, .5, .3),                     # 0-4 trend
        B(107.0, 106.2, .4, .4), B(106.2, 105.0, .2, .4), B(105.0, 104.0, .2, .5),
        B(104.0, 103.8, .3, .4),                                              # 5-8  dip 1
        B(103.9, 104.9, .3, .3), B(104.9, 105.6, .4, .3),                     # 9-10 bayrak tepesi
        B(105.5, 104.8, .3, .4), B(104.8, 104.0, .2, .4), B(104.0, 103.7, .2, .4),
        B(103.7, 104.3, .3, .35),                                             # 11-14 dip 2 / sinyal
        B(104.4, 105.4, .3, .2), B(105.4, 106.3, .3, .2), B(106.3, 107.2, .3, .3),
        B(107.2, 108.0, .4, .3), B(108.0, 108.8, .4, .3),
    ]
    d1 = b.df_yap(ham)
    K = 212.0
    d2 = b.df_yap(ayna(ham, K))
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Panel 1 — çift dip boğa bayrağı: boğa trendinde iki eşit dip",
        "Panel 2 — çift tepe ayı bayrağı: aynı kurgunun dikey aynası"))

    fig.add_trace(b.mumlar(d1, "şematik"), row=1, col=1)
    dip1, dip2 = float(d1.l[8]), float(d1.l[14])
    tepe_b = float(d1.h[10])
    b.yatay(fig, dip1, 6, 18, renk=TEAL, dash="dash", row=1, col=1)
    b.yatay(fig, tepe_b, 8, 19, renk=ALTIN, dash="dash", row=1, col=1)
    b.not_(fig, 8, dip1, "dip 1", renk=TEAL, ax=-8, ay=32, boyut=10, row=1, col=1)
    b.not_(fig, 14, dip2, "dip 2 (eşit) = sinyal barı", renk=TEAL, ax=26, ay=38, boyut=10, row=1, col=1)
    b.not_(fig, 10, tepe_b, "bayrak tepesi = kırılım noktası", renk=ALTIN, ok=False,
           boyut=10, yanchor="bottom", row=1, col=1)
    t1 = b.islem(fig, d1, 14, "bull", row=1, col=1)
    h1 = b.olculmus_hareket(fig, 14, dip1, 16, tepe_b, len(d1) - 1,
                            etiket="bayrak yüksekliği MM", row=1, col=1)

    fig.add_trace(b.mumlar(d2, "şematik"), row=2, col=1)
    tep1, tep2 = float(d2.h[8]), float(d2.h[14])
    dip_b = float(d2.l[10])
    b.yatay(fig, tep1, 6, 18, renk=BORDO, dash="dash", row=2, col=1)
    b.yatay(fig, dip_b, 8, 19, renk=ALTIN, dash="dash", row=2, col=1)
    b.not_(fig, 8, tep1, "tepe 1", renk=BORDO, ax=-8, ay=-32, boyut=10, row=2, col=1)
    b.not_(fig, 14, tep2, "tepe 2 (eşit) = sinyal barı", renk=BORDO, ax=26, ay=-38, boyut=10, row=2, col=1)
    b.not_(fig, 10, dip_b, "bayrak dibi = kırılım noktası", renk=ALTIN, ok=False,
           boyut=10, yanchor="top", row=2, col=1)
    t2 = b.islem(fig, d2, 14, "bear", row=2, col=1)
    h2 = b.olculmus_hareket(fig, 14, tep1, 16, dip_b, len(d2) - 1,
                            etiket="bayrak yüksekliği MM", row=2, col=1)

    b.lejant(fig, "sinyal barı", ALTIN)
    b.lejant_cizgi(fig, "bayrak sınırı", ALTIN)
    b.lejant_cizgi(fig, "ölçülmüş hareket", MOR)
    lejant_tekille(fig)
    b.duzen(fig, "Çift dip boğa bayrağı ve çift tepe ayı bayrağı",
            "iki eşit uç, 'piyasa iki kez dener' ilkesinin bayrak hâlidir; hedef bayrak yüksekliği kadardır",
            h=H2P, sematik=True)
    panelsiz_x(fig, 1)
    b.kaydet(fig, "51_cift_dip_tepe_bayragi", olcum={
        "boga_dip1": round(dip1, 2), "boga_dip2": round(dip2, 2),
        "boga_bayrak_tepesi": round(tepe_b, 2),
        "boga_bayrak_yuksekligi": round(tepe_b - dip1, 2), "boga_mm": round(h1, 2),
        "boga_giris": round(t1["giris"], 2), "boga_stop": round(t1["stop"], 2),
        "boga_risk": round(t1["risk"], 2), "boga_mm_r": round((h1 - t1["giris"]) / t1["risk"], 1),
        "ayi_tepe1": round(tep1, 2), "ayi_tepe2": round(tep2, 2),
        "ayi_bayrak_dibi": round(dip_b, 2),
        "ayi_mm": round(h2, 2), "ayi_risk": round(t2["risk"], 2)})


# ==================================================================== 52
class _Yol:
    """Şematik yol kurucu: bar eklerken o ana kadarki 20 barlık EMA'yı okur.

    Geri çekilme derinlik merdiveninde 'MA'ya kadar indi' / 'MA'nın altına sarktı'
    demek için barın konumu EMA'ya GÖRE seçilmek zorunda; EMA ise önceki kapanışların
    fonksiyonu. Bu yüzden yol adım adım kurulur ve her adımda EMA yeniden okunur.
    """

    def __init__(self):
        self.bars: list[tuple] = []

    def ekle(self, o, c, ust=0.0, alt=0.0):
        self.bars.append(B(o, c, ust, alt))
        return self.bars[-1]

    def ema(self, n=20):
        s = pd.Series([x[3] for x in self.bars])
        return float(s.ewm(span=n, adjust=False).mean().iloc[-1])

    def son_kapanis(self):
        return self.bars[-1][3]


def f52_derinlik_merdiveni():
    """52 · Geri çekilme derinlik merdiveni (Ş, 1 panel)."""
    y = _Yol()
    kayit = {}

    def bacak(n, adim, ust=.35, alt=.25):
        for _ in range(n):
            o = y.son_kapanis() if y.bars else 100.0
            y.ekle(o, o + adim, ust, alt)

    y.ekle(100.0, 100.7, .3, .3)
    bacak(4, 0.75)                                   # A bacağı
    # kademe 1 — sadece önceki barın dibi
    onceki_dip = y.bars[-1][2]
    y.ekle(y.son_kapanis(), onceki_dip + 0.05, .25, .18)
    kayit["p1_indis"] = len(y.bars) - 1
    bacak(6, 0.70)                                   # B bacağı
    # kademe 2 — minör (dik) trend çizgisinin altına, EMA'nın belirgin üstünde
    hedef = y.ema() + 1.30
    y.ekle(y.son_kapanis(), hedef + 0.25, .2, .30)
    y.ekle(hedef + 0.25, hedef, .18, .28)
    kayit["p2_indis"] = len(y.bars) - 1
    kayit["p2_ema_ustu"] = round(y.bars[-1][2] - y.ema(), 2)
    bacak(7, 0.72)                                   # C bacağı
    # kademe 3 — tam hareketli ortalamaya
    y.ekle(y.son_kapanis(), y.son_kapanis() - 0.9, .2, .35)
    y.ekle(y.son_kapanis(), y.ema() + 0.30, .2, .32)
    kayit["p3_indis"] = len(y.bars) - 1
    kayit["p3_dip_eksi_ema"] = round(y.bars[-1][2] - y.ema(), 2)
    bacak(7, 0.80)                                   # D bacağı
    # kademe 4 — MA boşluk barı: barın TAMAMI EMA'nın altında
    y.ekle(y.son_kapanis(), y.son_kapanis() - 1.2, .2, .40)
    y.ekle(y.son_kapanis(), y.son_kapanis() - 1.3, .2, .40)
    e = y.ema()
    y.ekle(e - 0.75, e - 1.65, .18, .35)             # yüksek = EMA − 0,57
    kayit["p4_indis"] = len(y.bars) - 1
    kayit["p4_yuksek_eksi_ema"] = round(y.bars[-1][1] - y.ema(), 2)
    y.ekle(y.son_kapanis(), y.son_kapanis() + 1.1, .3, .2)
    bacak(7, 0.95)                                   # E bacağı
    # kademe 5 — majör trend çizgisine kadar (çizgi önce hesaplanır, dip oraya kurulur)
    i2, i3 = kayit["p2_indis"], kayit["p3_indis"]
    l2, l3 = y.bars[i2][2], y.bars[i3][2]
    egim = (l3 - l2) / (i3 - i2)
    paylar = [0.55, 0.75, 0.35, -0.30, 0.70, 0.95]
    p5_indis = len(y.bars) + len(paylar) - 1
    hedef_dip = l2 + egim * (p5_indis - i2)
    bas_c = y.son_kapanis()
    toplam = bas_c - (hedef_dip + 0.45)
    pay_top = sum(paylar)
    for k, a in enumerate(paylar):
        o = y.son_kapanis()
        c = o - toplam * a / pay_top
        son = (k == len(paylar) - 1)
        y.ekle(o, c, .28, (min(o, c) - hedef_dip - 0.03) if son else .40)
    kayit["p5_indis"] = len(y.bars) - 1
    kayit["p5_dip_eksi_cizgi"] = round(y.bars[-1][2] - hedef_dip, 2)
    bacak(4, 0.9)

    df = b.df_yap(y.bars)
    fig = go.Figure(b.mumlar(df))
    e = b.ema_ciz(fig, df, 20, renk=MAVI, ad="20 bar EMA")
    b.trend_cizgisi(fig, df, (i2, i3), yon="bull", uzat=len(df) - 1, renk=BORDO,
                    dash="dash", w=1.8)
    b.not_(fig, i3 + 6, l2 + egim * (i3 + 6 - i2),
           "majör trend çizgisi<br>(2. ve 3. kademe diplerinden)", renk=BORDO, ok=False,
           boyut=10, xanchor="left", yanchor="top")
    b.trend_cizgisi(fig, df, (kayit["p1_indis"], kayit["p2_indis"]), yon="bull",
                    uzat=kayit["p2_indis"] + 4, renk=GRI, dash="dot", w=1.6)
    b.not_(fig, kayit["p2_indis"] + 4, float(df.l[kayit["p2_indis"]]) + 0.6,
           "minör (dik) trend çizgisi", renk=GRI, ok=False, boyut=10, xanchor="left")

    kademeler = [
        (kayit["p1_indis"], "1 · önceki barın dibi", TEAL, 46),
        (kayit["p2_indis"], "2 · minör trend çizgisi", GRI, 60),
        (kayit["p3_indis"], "3 · hareketli ortalama", MAVI, 46),
        (kayit["p4_indis"], "4 · MA boşluk barı", TURUNCU, 62),
        (kayit["p5_indis"], "5 · majör trend çizgisi", BORDO, 46),
    ]
    for i, et, renk, dy in kademeler:
        b.kutu(fig, i - .5, i + .5, float(df.l[i]), float(df.h[i]), renk, a=0.20, cizgi=1.2)
        b.not_(fig, i, float(df.l[i]), et, renk=renk, ax=0, ay=dy, boyut=10)
    i4 = kayit["p4_indis"]
    b.kutu(fig, i4 - .7, i4 + .7, float(df.h[i4]), float(e[i4]), TURUNCU, a=0.30, cizgi=1.0)
    b.not_(fig, i4, float(e[i4]), f"boşluk {float(e[i4]) - float(df.h[i4]):.2f} birim",
           renk=TURUNCU, ax=-56, ay=-26, boyut=10)
    b.not_(fig, 1, float(df.h.max()) - 0.4,
           "trend olgunlaştıkça geri çekilmeler derinleşir:<br>"
           "aynı trend, gitgide daha aşağıdaki mıknatısta duruyor",
           renk=MUREKKEP, ok=False, boyut=10, xanchor="left")
    b.lejant_cizgi(fig, "majör trend çizgisi", BORDO)
    b.lejant_cizgi(fig, "minör trend çizgisi", GRI, dash="dot")
    b.lejant(fig, "MA boşluğu", TURUNCU)
    lejant_tekille(fig)
    b.duzen(fig, "Geri çekilme derinlik merdiveni: bar → minör çizgi → MA → MA boşluğu → majör çizgi",
            "ilk geri çekilme dizisi; her kademe bir öncekinden derin ve trendin olgunlaştığının ölçüsü",
            h=H1P + 40, sematik=True)
    b.kaydet(fig, "52_derinlik_merdiveni", olcum={
        "kademe_indisleri": {k: v for k, v in kayit.items() if k.endswith("indis")},
        "p2_dip_ema_ustunde": kayit["p2_ema_ustu"],
        "p3_dip_eksi_ema": kayit["p3_dip_eksi_ema"],
        "p4_yuksek_eksi_ema": kayit["p4_yuksek_eksi_ema"],
        "p5_dip_eksi_major_cizgi": kayit["p5_dip_eksi_cizgi"],
        "bar_sayisi": len(df)})


# ==================================================================== 53
def f53_ma_gap_bar():
    """53 · MA gap barı ve ilk MA gap barı → ekstrem testi (G, XU030 5dk, 2 panel)."""
    d = b.yukle("XU030.IS", "5m")
    if d is None:
        return
    p1 = b.dilim(d, 1280, 40)          # 18 Haz 2026 — boğa trendi + ilk MA boşluk barı
    p2 = b.dilim(d, 1282, 58)          # aynı olayın devamı: iki bacaklı düzeltme + ekstrem testi
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Panel 1 — trendin ilk hareketli ortalama boşluk barı (18 Haziran 2026, bar 1280–1319)",
        "Panel 2 — iki bacaklı düzeltme ve trendin ucunun testi (bar 1282–1339)"))

    fig.add_trace(b.mumlar(p1, "XU030 5dk", hover=b.hover(p1)), row=1, col=1)
    e1 = b.ema_ciz(fig, p1, 20, renk=MAVI, row=1, col=1)
    g1 = 1305 - 1280                                            # 25
    b.kutu(fig, g1 - .6, g1 + .6, float(p1.h[g1]), float(e1[g1]), TURUNCU, a=0.28, cizgi=1.2,
           row=1, col=1)
    b.not_(fig, g1, float(p1.h[g1]), "ilk MA boşluk barı:<br>barın tamamı EMA'nın altında",
           renk=TURUNCU, ax=-52, ay=-46, boyut=10, row=1, col=1)
    uc1 = float(p1.h[:g1].max())
    b.yatay(fig, uc1, 0, len(p1) - 1, renk=GRI, dash="dash", row=1, col=1)
    b.not_(fig, 1, uc1, "trendin ucu (ekstrem)", renk=GRI, ok=False, boyut=10,
           xanchor="left", yanchor="bottom", row=1, col=1)
    b.not_(fig, 8, float(p1.l.min()) + 12,
           "boğa trendi: pencerenin ilk yarısında bütün kapanışlar EMA'nın üstünde", renk=TEAL, ok=False,
           boyut=10, row=1, col=1)

    fig.add_trace(b.mumlar(p2, "XU030 5dk", hover=b.hover(p2)), row=2, col=1)
    e2 = b.ema_ciz(fig, p2, 20, renk=MAVI, row=2, col=1)
    off = 1282
    g2, l1, ara, l2, test = 1305 - off, 1314 - off, 1316 - off, 1323 - off, 1334 - off
    uc2 = float(p2.h[:g2].max())
    b.yatay(fig, uc2, 0, len(p2) - 1, renk=GRI, dash="dash", row=2, col=1)
    b.not_(fig, len(p2) - 1, uc2, f"ekstrem {uc2:.1f}", renk=GRI, ok=False, boyut=10,
           xanchor="left", row=2, col=1)
    b.kutu(fig, g2 - .6, g2 + .6, float(p2.h[g2]), float(e2[g2]), TURUNCU, a=0.28, cizgi=1.2,
           row=2, col=1)
    b.not_(fig, g2, float(p2.h[g2]), "MA boşluk barı", renk=TURUNCU, ax=-34, ay=-40,
           boyut=10, row=2, col=1)
    b.cizgi(fig, g2, float(p2.h[g2]), l1, float(p2.l[l1]), renk=BORDO, dash="dot", w=1.8,
            row=2, col=1)
    b.cizgi(fig, l1, float(p2.l[l1]), ara, float(p2.h[ara]), renk=TEAL, dash="dot", w=1.8,
            row=2, col=1)
    b.cizgi(fig, ara, float(p2.h[ara]), l2, float(p2.l[l2]), renk=BORDO, dash="dot", w=1.8,
            row=2, col=1)
    b.not_(fig, l1, float(p2.l[l1]), "bacak 1", renk=BORDO, ax=-14, ay=34, boyut=10, row=2, col=1)
    b.not_(fig, l2, float(p2.l[l2]), "bacak 2", renk=BORDO, ax=14, ay=42, boyut=10, row=2, col=1)
    b.not_(fig, test, float(p2.h[test]), f"ekstremin testi ve aşılması (bar {off + test})",
           renk=MOR, ax=-24, ay=-38, boyut=10, row=2, col=1)
    b.not_(fig, 30, float(p2.l.min()) + 14,
           "kural: bir trendin İLK MA boşluk barı, iki bacaklı bir düzeltmeyi ve<br>"
           "ardından trendin ucunun test edilmesini kurar", renk=MUREKKEP, ok=False,
           boyut=10, row=2, col=1)
    b.lejant_cizgi(fig, "20 bar EMA", MAVI, dash="solid")
    b.lejant(fig, "MA boşluğu", TURUNCU)
    b.lejant_cizgi(fig, "düzeltme bacakları", BORDO, dash="dot")
    lejant_tekille(fig)
    b.duzen(fig, "Hareketli ortalama boşluk barı ve ekstrem testi zinciri",
            "XU030 5 dakika · pencereler indisle pinli (indis 1280–1319 · 1282–1339) · boşluk barı = "
            "barın tamamının EMA'nın karşı tarafında kalması; trendin ilki bir kurulum sinyalidir",
            h=H2P)
    b.zaman_ekseni(fig, p1, adet=7, fmt="%H:%M", row=1, col=1)
    b.zaman_ekseni(fig, p2, adet=8, fmt="%H:%M", row=2, col=1)
    panelsiz_x(fig, 1)
    b.kaydet(fig, "53_ma_gap_bar", olcum={
        "gap_bar_indis": 1305, "gap_bar_yuksek": round(float(d.h[1305]), 1),
        "gap_bar_ema_farki": round(float(e1[g1]) - float(p1.h[g1]), 1),
        "ekstrem": round(uc2, 1),
        "bacak1_dip": round(float(d.l[1314]), 1), "bacak2_dip": round(float(d.l[1323]), 1),
        "test_bari": 1334, "test_yuksek": round(float(d.h[1334]), 1),
        "test_asti": bool(float(d.h[1334]) > uc2),
        "p1_pencere": "XU030.IS 5m indis 1280–1319",
        "p2_pencere": "XU030.IS 5m indis 1282–1339"})


# ==================================================================== 54
def f54_yirmi_gap_bar():
    """54 · 20 gap bar kurulumu (G, XAUUSD/GC=F 15dk, 2 panel)."""
    d = b.yukle("GC=F", "15m")
    if d is None:
        return
    e_tam = b.ema(d, 20)
    p1 = b.dilim(d, 1612, 34)          # 9 Tem 2026 — 20 bar MA'ya dokunulmuyor
    p2 = b.dilim(d, 1632, 34)          # ilk dokunuşta giriş ve devamı
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Panel 1 — sayaç: 20 bar boyunca hiçbir barın düşüğü EMA'ya değmiyor (bar 1612–1645)",
        "Panel 2 — ilk dokunuşta limit alışı (bar 1632–1665)"))

    fig.add_trace(b.mumlar(p1, "XAUUSD 15dk", hover=b.hover(p1)), row=1, col=1)
    e1 = b.ema_ciz(fig, p1, 20, renk=MAVI, row=1, col=1)
    bas, son, dok = 1619 - 1612, 1638 - 1612, 1639 - 1612       # 7, 26, 27
    say = son - bas + 1
    b.kutu(fig, bas - .5, son + .5, float(p1.l[bas:son + 1].min()) - 2.5,
           float(p1.h[bas:son + 1].max()) + 2.5, TEAL, a=0.10, cizgi=1.0, row=1, col=1)
    b.not_(fig, (bas + son) / 2, float(p1.h[bas:son + 1].max()) + 3,
           f"{say} bar · EMA'ya dokunuş yok", renk=TEAL, ok=False, boyut=11,
           yanchor="bottom", row=1, col=1)
    for k, i in enumerate(range(bas, son + 1)):
        if (k + 1) % 5 == 0:
            b.not_(fig, i, float(p1.l[i]) - 1.0, str(k + 1), renk=TEAL, ok=False, boyut=9,
                   yanchor="top", row=1, col=1)
    b.not_(fig, dok, float(p1.l[dok]), "ilk dokunuş (21. bar)", renk=ALTIN, ax=26, ay=40,
           boyut=10, row=1, col=1)
    b.not_(fig, 2, float(p1.h[2]) + 3, "önceki dokunuş burada bitti", renk=GRI, ok=False,
           boyut=10, xanchor="left", row=1, col=1)

    fig.add_trace(b.mumlar(p2, "XAUUSD 15dk", hover=b.hover(p2)), row=2, col=1)
    e2 = b.ema_ciz(fig, p2, 20, renk=MAVI, row=2, col=1)
    j = 1639 - 1632                                             # 7
    giris = float(e_tam[1639])
    stop = float(d.l[1639]) - 0.6
    onceki_tepe = float(d.h[1619:1639].max())
    zirve = float(p2.h.max())
    t = b.islem(fig, p2, j, "bull", giris=giris, stop=stop,
                hedefler=(onceki_tepe, zirve), etiketler=("trendin son tepesi", "sonraki zirve"),
                ondalik=1, row=2, col=1)
    b.not_(fig, j, giris, "EMA'da limit alışı", renk=MAVI, ax=-42, ay=-34, boyut=10, row=2, col=1)
    sonraki_dip = float(p2.l[j + 1:j + 25].min())
    b.yatay(fig, sonraki_dip, j, len(p2) - 1, renk=YESIL, dash="dot", row=2, col=1)
    b.not_(fig, len(p2) - 1, sonraki_dip,
           f"girişten sonraki en düşük {sonraki_dip:.1f} — sinyal barının dibi hiç görülmedi",
           renk=YESIL, ok=False, boyut=10, xanchor="right", yanchor="top", row=2, col=1)
    b.lejant_cizgi(fig, "20 bar EMA", MAVI, dash="solid")
    b.lejant(fig, "dokunuşsuz pencere", TEAL)
    lejant_tekille(fig)
    b.duzen(fig, "20 gap bar kurulumu: MA'ya 20+ bar dokunulmaması ve ilk dokunuşta giriş",
            "XAUUSD 15 dakika · müfredat bu figüre USDTRY 5dk verir; USDTRY OHLC'si mum düzeyinde "
            "okunamadığı için öncelik listesinin bir sonraki enstrümanına geçildi · "
            "pencereler indisle pinli (indis 1612–1645 · 1632–1665)",
            h=H2P)
    b.zaman_ekseni(fig, p1, adet=7, fmt="%d %b %H:%M", row=1, col=1)
    b.zaman_ekseni(fig, p2, adet=7, fmt="%d %b %H:%M", row=2, col=1)
    panelsiz_x(fig, 1)
    b.kaydet(fig, "54_yirmi_gap_bar", olcum={
        "dokunussuz_bar": say, "ilk_dokunus_bari": 1639,
        "giris": round(giris, 2), "stop": round(stop, 2), "risk": round(t["risk"], 2),
        "r": [round(x, 1) for x in t["r"]],
        "girisden_sonraki_dip": round(sonraki_dip, 2),
        "sinyal_bari_dibi": round(float(d.l[1639]), 2),
        "p1_pencere": "GC=F 15m indis 1612–1645",
        "p2_pencere": "GC=F 15m indis 1632–1665"})


# ==================================================================== 55
def f55_ma_sarkmalari():
    """55 · Güçlü trendde MA'nın altına her sarkma (G, BIST100 günlük, 1 panel)."""
    d = b.yukle("XU100.IS", "1d")
    if d is None:
        return
    BAS, ADET = 298, 100                # 27 Eki 2025 – 18 Mar 2026
    e_tam = b.ema(d, 20)                # EMA TAM seriden: pencerede ısınma sapması olmasın
    w = b.dilim(d, BAS, ADET)
    e = e_tam[BAS:BAS + ADET].reset_index(drop=True)
    fig = go.Figure(b.mumlar(w, "BIST 100 günlük", hover=b.hover(w)))
    fig.add_trace(go.Scatter(x=list(range(len(w))), y=e, mode="lines", name="20 gün EMA",
                             line=dict(color=MAVI, width=1.7)))
    alt = (w.l < e).values
    runs, i = [], 0
    while i < len(w):
        if alt[i]:
            j = i
            while j + 1 < len(w) and alt[j + 1]:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    calisan, kayit = 0, []
    for n, (a_, z_) in enumerate(runs, 1):
        on_tepe = float(d.h[max(0, BAS + a_ - 18):BAS + a_].max())
        ileri = w.h[z_ + 1:z_ + 26]
        surdu = bool(len(ileri) and ileri.max() > on_tepe)
        calisan += int(surdu)
        renk = YESIL if surdu else TURUNCU
        b.kutu(fig, a_ - .8, z_ + .8, float(w.l[a_:z_ + 1].min()),
               float(max(float(e[a_:z_ + 1].max()), float(w.h[a_:z_ + 1].max()))),
               renk, a=0.18, cizgi=1.1)
        b.not_(fig, (a_ + z_) / 2, float(w.l[a_:z_ + 1].min()),
               f"{n} · {'sadece geri çekilme' if surdu else 'trendi bitirdi'}",
               renk=renk, ax=0, ay=42, boyut=10)
        kayit.append({"no": n, "bar": int(BAS + a_), "tarih": str(w.ts[a_])[:10],
                      "uzunluk_bar": int(z_ - a_ + 1),
                      "dip": round(float(w.l[a_:z_ + 1].min()), 1),
                      "onceki_tepe": round(on_tepe, 1), "surdu": surdu})
    b.not_(fig, len(w) - 2, float(w.l.min()) + 700,
           f"bu pencerede {len(runs)} sarkma: {calisan} tanesi yalnızca geri çekilme, "
           f"{len(runs) - calisan} tanesi trendi bitirdi (%{100 * calisan / max(len(runs), 1):.0f})<br>"
           "Brooks'un %80 önselini tek pencere kanıtlamaz; kanıtladığı şey şudur: "
           "MA'nın altına sarkmanın kendisi dönüş DEĞİLDİR",
           renk=MUREKKEP, ok=False, boyut=10, xanchor="right")
    b.lejant(fig, "sarkma sürdü (geri çekilme)", YESIL)
    b.lejant(fig, "sarkma trendi bitirdi", TURUNCU)
    lejant_tekille(fig)
    b.duzen(fig, "Güçlü boğa trendinde hareketli ortalamanın altına her sarkma",
            f"BIST 100 günlük · {str(w.ts[0])[:10]} – {str(w.ts.iloc[-1])[:10]} "
            f"(indis {BAS}–{BAS + ADET - 1}) · EMA tam seriden hesaplandı",
            y_baslik="endeks", h=H1P + 60)
    b.zaman_ekseni(fig, w, adet=9, fmt="%d %b %y")
    b.kaydet(fig, "55_ma_sarkmalari", olcum={
        "sarkma_sayisi": len(runs), "sadece_geri_cekilme": calisan,
        "trendi_bitiren": len(runs) - calisan,
        "oran_yuzde": round(100 * calisan / max(len(runs), 1), 1),
        "sarkmalar": kayit, "pencere": f"XU100.IS 1d indis {BAS}–{BAS + ADET - 1}"})


# ==================================================================== 56
def f56_klimakslar():
    """56 · Klimaks ve ardışık klimakslar (G, XU030 5dk, 3 panel)."""
    d = b.yukle("XU030.IS", "5m")
    if d is None:
        return
    k1, k2, k3 = 528, 536, 539         # 8 Haziran 2026
    p1 = b.dilim(d, 516, 22)
    p2 = b.dilim(d, 520, 26)
    p3 = b.dilim(d, 524, 30)
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.075, subplot_titles=(
        "Panel 1 — tek klimaks: kırılım barı ve ardından duraklama (8 Haziran 2026, bar 516–537)",
        "Panel 2 — ardışık iki klimaks (bar 520–545)",
        "Panel 3 — üçüncü klimakstan sonra 10 bar ve iki bacaklı düzeltme (bar 524–553)"))

    def klimaks_isaretle(p, off, idx, etiket, satir):
        i = idx - off
        b.kutu(fig, i - .45, i + .45, float(p.l[i]), float(p.h[i]), ALTIN, a=0.24, cizgi=1.3,
               row=satir, col=1)
        b.not_(fig, i, float(p.h[i]), etiket, renk=ALTIN, ax=-6, ay=-34, boyut=10,
               row=satir, col=1)
        return float(p.h[i] - p.l[i])

    fig.add_trace(b.mumlar(p1, "XU030 5dk", hover=b.hover(p1)), row=1, col=1)
    r1 = klimaks_isaretle(p1, 516, k1, "klimaks 1 · menzil 48,9", 1)
    ort1 = float((p1.h - p1.l)[:k1 - 516].median())
    b.not_(fig, k1 - 516 + 5, float(p1.l.min()) + 8,
           f"önceki 12 barın medyan menzili {ort1:.1f} → klimaks barı {r1 / ort1:.1f} katı",
           renk=MUREKKEP, ok=False, boyut=10, row=1, col=1)

    fig.add_trace(b.mumlar(p2, "XU030 5dk", hover=b.hover(p2)), row=2, col=1)
    klimaks_isaretle(p2, 520, k1, "klimaks 1", 2)
    klimaks_isaretle(p2, 520, k2, "klimaks 2 · menzil 62,8", 2)
    b.not_(fig, k2 - 520 + 4, float(p2.l.min()) + 10,
           "ikinci klimaks birinciden büyük: alıcılar hâlâ agresif,<br>"
           "ama her klimaks bir sonrakinin yakıtını tüketiyor", renk=MUREKKEP, ok=False,
           boyut=10, row=2, col=1)

    fig.add_trace(b.mumlar(p3, "XU030 5dk", hover=b.hover(p3)), row=3, col=1)
    off = 524
    for kk, et in ((k1, "1"), (k2, "2"), (k3, "3 · menzil 83,6")):
        klimaks_isaretle(p3, off, kk, f"klimaks {et}", 3)
    zirve_i = 540 - off                                      # klimaks dizisinin zirvesi
    zirve = float(p3.h[zirve_i])
    b.yatay(fig, zirve, zirve_i, len(p3) - 1, renk=GRI, dash="dash", row=3, col=1)
    b.not_(fig, zirve_i + 6, zirve, f"zirve {zirve:.1f} (bar {off + zirve_i})", renk=GRI,
           ok=False, boyut=10, yanchor="top", row=3, col=1)
    d1, ar, d2 = 545 - off, 546 - off, 550 - off
    b.cizgi(fig, zirve_i, zirve, d1, float(p3.l[d1]), renk=BORDO, dash="dot", w=1.8, row=3, col=1)
    b.cizgi(fig, d1, float(p3.l[d1]), ar, float(p3.h[ar]), renk=TEAL, dash="dot", w=1.8, row=3, col=1)
    b.cizgi(fig, ar, float(p3.h[ar]), d2, float(p3.l[d2]), renk=BORDO, dash="dot", w=1.8, row=3, col=1)
    b.not_(fig, d1, float(p3.l[d1]), "bacak 1", renk=BORDO, ax=-14, ay=34, boyut=10, row=3, col=1)
    b.not_(fig, d2, float(p3.l[d2]), "bacak 2", renk=BORDO, ax=18, ay=40, boyut=10, row=3, col=1)
    b.kutu(fig, zirve_i + .5, d2 + .5, float(p3.l[d1:d2 + 1].min()) - 4, zirve + 4,
           BORDO, a=0.08, cizgi=1.0, row=3, col=1)
    b.not_(fig, (zirve_i + d2) / 2, float(p3.l[d1:d2 + 1].min()) - 6,
           f"{d2 - zirve_i} bar, iki bacaklı düzeltme", renk=BORDO, ok=False, boyut=11,
           yanchor="top", row=3, col=1)
    b.lejant(fig, "klimaks barı", ALTIN)
    b.lejant_cizgi(fig, "düzeltme bacakları", BORDO, dash="dot")
    lejant_tekille(fig)
    b.duzen(fig, "Klimaks ve ardışık klimakslar: üçüncüden sonra en az 10 bar, iki bacaklı düzeltme",
            "XU030 5 dakika · pencereler indisle pinli (indis 516–537 · 520–545 · 524–553) · aynı gün, "
            "aynı olay zinciri üç ölçekte — pencere büyüdükçe klimaksların sırası görünür oluyor",
            h=H3P)
    for i, p in ((1, p1), (2, p2), (3, p3)):
        b.zaman_ekseni(fig, p, adet=6, fmt="%H:%M", row=i, col=1)
    panelsiz_x(fig, 1)
    panelsiz_x(fig, 2)
    b.kaydet(fig, "56_klimakslar", olcum={
        "klimaks_barlari": [k1, k2, k3],
        "menziller": [round(float(d.h[i] - d.l[i]), 1) for i in (k1, k2, k3)],
        "onceki_medyan_menzil": round(ort1, 1),
        "zirve_bar": off + zirve_i, "zirve": round(zirve, 1),
        "duzeltme_bar_sayisi": d2 - zirve_i,
        "bacak1_dip": round(float(d.l[545]), 1), "bacak2_dip": round(float(d.l[550]), 1),
        "pencereler": ["XU030.IS 5m 516–537", "520–545", "524–553"]})


# ==================================================================== 57
def f57_klimaktik_donus():
    """57 · Klimaktik dönüş = başarısız kırılım (Ş, 1 panel)."""
    ham = [
        B(102.0, 103.0, .3, .4), B(103.0, 104.0, .4, .3), B(104.0, 103.4, .5, .4),
        B(103.4, 104.2, .5, .3), B(104.2, 104.6, .4, .4),                     # 0-4 bant
        B(104.5, 105.8, .3, .3),                                              # 5 kırılım barı
        B(105.8, 107.4, .3, .2),                                              # 6
        B(107.4, 109.4, .3, .2),                                              # 7 klimaks
        B(109.3, 107.2, .3, .3),                                              # 8 dönüş barı
        B(107.2, 105.4, .2, .4), B(105.4, 104.2, .2, .4),                     # 9-10
        B(104.2, 103.0, .2, .4), B(103.0, 101.8, .2, .5), B(101.8, 100.8, .2, .5),
        B(100.8, 99.8, .2, .6),
    ]
    df = b.df_yap(ham)
    fig = go.Figure(b.mumlar(df))
    kirilim = float(df.h[:5].max())
    b.yatay(fig, kirilim, 0, len(df) - 1, renk=ALTIN, dash="dash", w=1.8)
    b.not_(fig, 0, kirilim, "kırılım noktası (bandın tepesi)", renk=ALTIN, ok=False,
           boyut=10, xanchor="left", yanchor="bottom")
    b.kutu(fig, -0.5, 4.5, float(df.l[:5].min()), kirilim, GRI, a=0.12)
    b.not_(fig, 2, float(df.l[:5].min()), "yatay bant", renk=GRI, ok=False, boyut=10, yanchor="top")
    for i, et, renk, ax, ay in ((5, "kırılım barı", ALTIN, -52, -30),
                                (7, "klimaks / tükeniş barı", TURUNCU, -62, -62),
                                (8, "dönüş barı (sinyal)", BORDO, 74, -34)):
        b.kutu(fig, i - .45, i + .45, float(df.l[i]), float(df.h[i]), renk, a=0.20, cizgi=1.2)
        b.not_(fig, i, float(df.h[i]), et, renk=renk, ax=ax, ay=ay, boyut=10)
    b.kutu(fig, 4.6, 10.4, kirilim, float(df.h.max()) + .3, TURUNCU, a=0.10, cizgi=1.0, dash="dot")
    b.not_(fig, 2.0, float(df.h.max()) + 1.3, "başarısız kırılım: fiyat kırılım noktasının "
           "üstünde kalıcı olamadı", renk=TURUNCU, ok=False, boyut=11, xanchor="left",
           yanchor="bottom")
    t = b.islem(fig, df, 8, "bear", hedefler=(kirilim, float(df.l[:5].min()), float(df.l.min())),
                etiketler=("kırılım noktası", "bandın dibi", "ölçülmüş hareket"))
    b.not_(fig, 0.2, 101.2, "klimaktik dönüş, adı üstünde bir dönüş DEĞİL:<br>"
           "yeni bir kırılımın başarısızlığıdır — sinyal, klimaksın<br>"
           "kendisi değil onu izleyen dönüş barıdır", renk=MUREKKEP, ok=False, boyut=10,
           xanchor="left", yanchor="top")
    b.lejant(fig, "kırılım / klimaks / dönüş barı", ALTIN)
    b.lejant_cizgi(fig, "kırılım noktası", ALTIN)
    lejant_tekille(fig)
    b.duzen(fig, "Klimaktik dönüş bir başarısız kırılımdır",
            "üç bar, üç iş: kırılım · tükeniş · dönüş — üçü de aynı dizinin parçası",
            h=H1P, sematik=True)
    b.kaydet(fig, "57_klimaktik_donus", olcum={
        "kirilim_noktasi": round(kirilim, 2),
        "klimaks_menzili": round(float(df.h[7] - df.l[7]), 2),
        "onceki_bar_medyan_menzil": round(float((df.h - df.l)[:5].median()), 2),
        "donus_bari_yuksek": round(float(df.h[8]), 2),
        "giris": round(t["giris"], 2), "stop": round(t["stop"], 2),
        "risk": round(t["risk"], 2), "r": [round(x, 1) for x in t["r"]]})


# ==================================================================== 58
def f58_trend_bitis_bicimleri():
    """58 · Bir boğa trendinin bitme biçimleri — iki yol (Ş, 2 panel)."""
    a = [
        B(100.0, 100.9, .3, .3), B(100.9, 101.8, .3, .3), B(101.7, 101.2, .3, .4),
        B(101.2, 102.3, .4, .3), B(102.3, 103.3, .4, .3), B(103.2, 102.7, .3, .4),
        B(102.7, 103.8, .4, .3), B(103.8, 104.8, .4, .3), B(104.7, 104.2, .3, .4),
        B(104.2, 105.3, .4, .3), B(105.3, 106.3, .4, .3), B(106.2, 105.7, .3, .4),
        B(105.7, 106.8, .4, .3),
        B(106.8, 109.4, .6, .3),                                              # 13 aşım barı
        B(109.3, 108.0, .3, .5), B(108.0, 106.8, .2, .5), B(106.8, 105.6, .2, .5),
        B(105.6, 104.6, .2, .5),                                              # 17 bacak 1 dibi
        B(104.7, 105.6, .4, .3), B(105.6, 106.3, .4, .3), B(106.2, 105.4, .3, .4),
        B(105.4, 104.6, .2, .5), B(104.6, 104.0, .3, .5),                     # 22 bacak 2 dibi
        B(104.1, 105.0, .4, .3), B(105.0, 105.8, .4, .3),
    ]
    c = [
        B(100.0, 100.9, .3, .3), B(100.9, 101.8, .3, .3), B(101.7, 101.2, .3, .4),
        B(101.2, 102.2, .4, .3), B(102.2, 103.2, .4, .3), B(103.1, 102.6, .3, .4),
        B(102.6, 103.6, .4, .3), B(103.6, 104.5, .4, .3), B(104.4, 103.9, .3, .4),
        B(103.9, 104.8, .4, .3), B(104.8, 105.6, .4, .3), B(105.5, 105.0, .3, .4),
        B(105.0, 105.8, .5, .3),                                              # 12 uç, aşım YOK
        B(105.7, 104.8, .3, .4), B(104.8, 103.8, .2, .5), B(103.8, 103.0, .2, .5),
        B(103.1, 104.0, .4, .3), B(104.0, 104.9, .4, .3), B(104.9, 105.5, .5, .3),  # 18 test
        B(105.4, 104.4, .3, .4), B(104.4, 103.2, .2, .5), B(103.2, 102.0, .2, .5),
        B(102.0, 100.9, .2, .5), B(100.9, 99.8, .2, .6), B(99.9, 100.6, .4, .3),
    ]
    d1, d2 = b.df_yap(a), b.df_yap(c)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Yol 1 — kanal aşımı → kanala dönüş → trend çizgisi altına sarkma → iki bacaklı düzeltme",
        "Yol 2 — aşım yok: doğrudan trend çizgisi kırılımı → daha düşük tepe testi"))

    fig.add_trace(b.mumlar(d1, "şematik"), row=1, col=1)
    eg1 = b.trend_cizgisi(fig, d1, (2, 11), yon="bull", kanal=True, kanal_nokta=10,
                          renk=GRI, dash="dash", row=1, col=1)
    kanal1_13 = float(d1.h[10]) + eg1 * (13 - 10)      # kanal çizgisinin 13. bardaki değeri
    b.kutu(fig, 12.5, 13.5, float(d1.l[13]), float(d1.h[13]), TURUNCU, a=0.22, cizgi=1.2,
           row=1, col=1)
    b.not_(fig, 13, float(d1.h[13]),
           f"1 · trend kanal çizgisinin aşılması<br>(kanal {kanal1_13:.1f} · bar yükseği "
           f"{float(d1.h[13]):.1f} → {float(d1.h[13]) - kanal1_13:.1f} birim aşım)",
           renk=TURUNCU, ax=-64, ay=-38, boyut=10, row=1, col=1)
    b.not_(fig, 15, float(d1.h[15]), "2 · kanala geri dönüş", renk=BORDO, ax=44, ay=-30,
           boyut=10, row=1, col=1)
    b.not_(fig, 17, float(d1.l[17]), "3 · trend çizgisinin altına sarkma", renk=BORDO,
           ax=-30, ay=38, boyut=10, row=1, col=1)
    b.cizgi(fig, 13, float(d1.h[13]), 17, float(d1.l[17]), renk=BORDO, dash="dot", w=1.7, row=1, col=1)
    b.cizgi(fig, 17, float(d1.l[17]), 19, float(d1.h[19]), renk=TEAL, dash="dot", w=1.7, row=1, col=1)
    b.cizgi(fig, 19, float(d1.h[19]), 22, float(d1.l[22]), renk=BORDO, dash="dot", w=1.7, row=1, col=1)
    b.not_(fig, 20, float(d1.l[22]) - .5, "4 · iki bacaklı düzeltme", renk=BORDO, ok=False,
           boyut=10, yanchor="top", row=1, col=1)

    fig.add_trace(b.mumlar(d2, "şematik"), row=2, col=1)
    eg2 = b.trend_cizgisi(fig, d2, (2, 11), yon="bull", kanal=True, kanal_nokta=10,
                          renk=GRI, dash="dash", row=2, col=1)
    kanal2_12 = float(d2.h[10]) + eg2 * (12 - 10)
    uc2 = float(d2.h[12])
    b.yatay(fig, uc2, 12, len(d2) - 1, renk=GRI, dash="dot", row=2, col=1)
    b.not_(fig, 12, uc2, f"1 · uç: kanal çizgisine ({kanal2_12:.1f}) değmeden momentum söndü<br>"
           f"({kanal2_12 - uc2:.1f} birim eksik kalma — aşım YOK)", renk=GRI,
           ax=-40, ay=-40, boyut=10, row=2, col=1)
    b.not_(fig, 14, float(d2.l[14]), "2 · trend çizgisi kırılımı", renk=BORDO, ax=-28, ay=36,
           boyut=10, row=2, col=1)
    b.kutu(fig, 17.5, 18.5, float(d2.l[18]), float(d2.h[18]), BORDO, a=0.20, cizgi=1.2,
           row=2, col=1)
    b.not_(fig, 18, float(d2.h[18]), "3 · daha düşük tepe testi = dönüş sinyali", renk=BORDO,
           ax=40, ay=-34, boyut=10, row=2, col=1)
    b.not_(fig, 21, 103.5, "aşım olmadığında dönüşün habercisi trend çizgisi kırılımıdır;<br>"
           "onay, ucun testinde gelir", renk=MUREKKEP, ok=False, boyut=10, row=2, col=1)
    b.lejant_cizgi(fig, "trend çizgisi / kanal çizgisi", GRI)
    b.lejant(fig, "aşım barı", TURUNCU)
    b.lejant_cizgi(fig, "düzeltme bacakları", BORDO, dash="dot")
    lejant_tekille(fig)
    b.duzen(fig, "Bir boğa trendi iki biçimde biter",
            "her ikisinde de sonuç aynı: trend çizgisinin altına sarkma + ucun testi; "
            "değişen yalnızca aşımın olup olmadığı",
            h=H2P, sematik=True)
    panelsiz_x(fig, 1)
    b.kaydet(fig, "58_trend_bitis_bicimleri", olcum={
        "yol1_asim_bari": 13, "yol1_asim_yuksek": round(float(d1.h[13]), 2),
        "yol1_kanal_cizgisi_13": round(kanal1_13, 2),
        "yol1_asim_miktari": round(float(d1.h[13]) - kanal1_13, 2),
        "yol2_kanal_cizgisi_12": round(kanal2_12, 2),
        "yol2_eksik_kalma": round(kanal2_12 - uc2, 2),
        "yol1_bacak1_dip": round(float(d1.l[17]), 2),
        "yol1_bacak2_dip": round(float(d1.l[22]), 2),
        "yol2_uc": round(uc2, 2), "yol2_test_yuksek": round(float(d2.h[18]), 2),
        "yol2_test_farki": round(float(d2.h[18]) - uc2, 2)})


# ==================================================================== 59  (ortak seri)
def _seri59():
    ham = [
        B(100.0, 100.8, .3, .3), B(100.8, 101.7, .3, .4), B(101.6, 101.1, .3, .4),
        B(101.1, 102.2, .4, .3), B(102.2, 103.1, .4, .3), B(103.0, 102.5, .3, .4),
        B(102.5, 103.6, .4, .3), B(103.6, 104.6, .4, .3), B(104.5, 104.0, .3, .4),
        B(104.0, 105.1, .4, .3), B(105.1, 106.1, .4, .3), B(106.0, 105.5, .3, .4),
        B(105.5, 106.6, .4, .3), B(106.6, 107.6, .4, .3), B(107.5, 107.0, .3, .4),
        B(107.0, 108.1, .4, .3), B(108.1, 109.1, .4, .3), B(109.0, 108.5, .3, .4),
        B(108.5, 109.6, .4, .3), B(109.6, 110.2, .6, .3),                     # 19 uç 110.8
        B(110.1, 109.0, .3, .4), B(109.0, 107.6, .2, .5), B(107.6, 106.2, .2, .5),
        B(106.2, 105.0, .2, .5), B(105.0, 103.9, .2, .5), B(103.9, 103.0, .3, .6),  # 25 dip 102.4
        B(103.1, 104.3, .4, .3), B(104.3, 105.5, .4, .3), B(105.4, 105.0, .3, .4),
        B(105.0, 106.3, .4, .3), B(106.3, 107.5, .4, .3), B(107.5, 108.6, .4, .3),
        B(108.6, 109.4, .5, .3), B(109.4, 109.8, .7, .3),                     # 33 test 110.5
        B(109.7, 108.6, .4, .5),                                              # 34 sinyal
        B(108.6, 107.2, .2, .5), B(107.2, 105.8, .2, .5), B(105.8, 104.6, .2, .5),
        B(104.7, 105.3, .4, .3), B(105.2, 104.0, .3, .4), B(104.0, 102.6, .2, .5),
        B(102.6, 101.4, .2, .5), B(101.4, 100.4, .2, .5),                     # 42
        B(100.5, 101.6, .4, .3), B(101.6, 102.3, .5, .3),                     # 43-44 geri çekilme
        B(102.2, 101.2, .3, .4),                                              # 45 sinyal
        B(101.2, 100.0, .2, .5), B(100.0, 98.8, .2, .5), B(98.8, 97.6, .2, .5),
        B(97.7, 98.4, .4, .3), B(98.3, 97.2, .3, .4), B(97.2, 96.0, .2, .5),
        B(96.0, 94.9, .2, .5), B(94.9, 93.8, .2, .6), B(93.9, 94.7, .4, .3),
        B(94.6, 93.5, .3, .5), B(93.5, 92.4, .2, .5), B(92.4, 91.4, .2, .5),
        B(91.4, 90.5, .2, .6),
    ]
    return b.df_yap(ham)


def f59_donus_dizisi():
    """59 · Dönüş dizisi: trend çizgisi kırılımı → uç testi → kırılım geri çekilmesi (Ş, 3 panel)."""
    tam = _seri59()
    p1 = tam.iloc[0:28].reset_index(drop=True)
    p2 = tam.iloc[18:41].reset_index(drop=True)
    p3 = tam.iloc[30:56].reset_index(drop=True)
    uc = float(tam.h[19])
    kir_dip = float(tam.l[25])
    test = float(tam.h[33])
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.075, subplot_titles=(
        "Panel 1 — boğa kanalı ve momentumlu trend çizgisi kırılımı",
        "Panel 2 — eski ucun testi: üç varyant",
        "Panel 3 — testten dönüş = yeni ayı trendinde kırılım geri çekilmesi"))

    fig.add_trace(b.mumlar(p1, "şematik"), row=1, col=1)
    b.trend_cizgisi(fig, p1, (2, 17), yon="bull", kanal=True, kanal_nokta=16, uzat=27,
                    renk=GRI, dash="dash", row=1, col=1)
    b.kutu(fig, 19.5, 25.5, kir_dip - .4, uc + .4, BORDO, a=0.10, cizgi=1.1, row=1, col=1)
    b.not_(fig, 22.5, kir_dip - .5, f"trend çizgisi kırılımı: 6 bar, {uc - kir_dip:.1f} birim<br>"
           "üst üste ayı gövdeleri, örtüşme yok = momentum", renk=BORDO, ok=False, boyut=10,
           yanchor="top", row=1, col=1)
    b.yatay(fig, uc, 19, 27, renk=GRI, dash="dot", row=1, col=1)
    b.not_(fig, 19, uc, f"eski uç {uc:.1f}", renk=GRI, ok=False, boyut=10, xanchor="right",
           yanchor="bottom", row=1, col=1)
    b.not_(fig, 6, float(p1.h[6]) + 1.2, "kanal: her geri çekilme sığ, her bacak yeni tepe",
           renk=TEAL, ok=False, boyut=10, xanchor="left", row=1, col=1)

    fig.add_trace(b.mumlar(p2, "şematik"), row=2, col=1)
    j_uc, j_test = 19 - 18, 33 - 18
    b.yatay(fig, uc, 0, len(p2) - 1, renk=GRI, dash="dash", w=1.6, row=2, col=1)
    b.not_(fig, 0, uc, "eski uç", renk=GRI, ok=False, boyut=10, xanchor="left",
           yanchor="bottom", row=2, col=1)
    for dy, et, renk, dash in ((0.9, "a · aşan test (daha yüksek tepe)", TURUNCU, "dot"),
                               (0.0, "b · eşit test (kusursuz çift tepe)", GRI, "dot")):
        b.yatay(fig, uc + dy, j_test - 4, len(p2) - 1, renk=renk, dash=dash, w=1.3, row=2, col=1)
        b.not_(fig, len(p2) - 1, uc + dy, et, renk=renk, ok=False, boyut=10, xanchor="right",
               yanchor="bottom", row=2, col=1)
    b.kutu(fig, j_test - .5, j_test + 1.5, float(p2.l[j_test + 1]), float(p2.h[j_test]),
           BORDO, a=0.20, cizgi=1.2, row=2, col=1)
    b.not_(fig, j_test, test, f"c · eksik test (daha düşük tepe) {test:.1f}<br>"
           "gerçekleşen varyant — ikinci dönüş barı hemen ardından", renk=BORDO,
           ax=-40, ay=-42, boyut=10, row=2, col=1)
    b.not_(fig, j_uc + 4, float(p2.l.min()) + .6,
           "testin ÜÇ sonucu da meşrudur; belirleyici olan testin nereye vardığı değil,<br>"
           "oradan dönerken üretilen sinyal barının gücüdür", renk=MUREKKEP, ok=False,
           boyut=10, row=2, col=1)

    fig.add_trace(b.mumlar(p3, "şematik"), row=3, col=1)
    off = 30
    j_kir, j_pull, j_sin = 41 - off, 44 - off, 45 - off
    b.yatay(fig, kir_dip, 0, len(p3) - 1, renk=ALTIN, dash="dash", w=1.7, row=3, col=1)
    b.not_(fig, 0, kir_dip, f"kırılım noktası {kir_dip:.1f} (panel 1'in dibi)", renk=ALTIN,
           ok=False, boyut=10, xanchor="left", yanchor="bottom", row=3, col=1)
    b.not_(fig, j_kir, float(p3.l[j_kir]), "kırılım", renk=ALTIN, ax=-24, ay=34, boyut=10,
           row=3, col=1)
    b.not_(fig, j_pull, float(p3.h[j_pull]), "kırılım geri çekilmesi (kırılım noktası testi)",
           renk=MAVI, ax=52, ay=-32, boyut=10, row=3, col=1)
    hedef = kir_dip - (test - kir_dip)
    t = b.islem(fig, p3, j_sin, "bear", hedefler=(hedef,), etiketler=("ölçülmüş hareket",),
                row=3, col=1)
    b.cizgi(fig, j_test if False else (33 - off), test, j_kir, kir_dip, renk=MOR, dash="dot",
            w=1.5, row=3, col=1)
    b.lejant_cizgi(fig, "trend / kanal çizgisi", GRI)
    b.lejant_cizgi(fig, "kırılım noktası", ALTIN)
    b.lejant(fig, "sinyal barı", ALTIN)
    b.lejant_cizgi(fig, "hedef", MOR)
    lejant_tekille(fig)
    b.duzen(fig, "Dönüş dizisi: trend çizgisi kırılımı → eski ucun testi → kırılım geri çekilmesi",
            "üç panel aynı şematik serinin üç penceresi; büyük dönüş bir bar değil bir dizidir",
            h=H3P, sematik=True)
    panelsiz_x(fig, 1)
    panelsiz_x(fig, 2)
    b.kaydet(fig, "59_donus_dizisi", olcum={
        "eski_uc": round(uc, 2), "kirilim_bar_sayisi": 6,
        "kirilim_boyu": round(uc - kir_dip, 2), "kirilim_dibi": round(kir_dip, 2),
        "test_yuksek": round(test, 2), "test_tipi": "eksik (daha düşük tepe)",
        "test_farki": round(test - uc, 2),
        "giris": round(t["giris"], 2), "stop": round(t["stop"], 2),
        "risk": round(t["risk"], 2), "mm_hedef": round(hedef, 2),
        "mm_r": round(t["r"][0], 1)})


# ==================================================================== 60
def f60_bes_bar_kurali():
    """60 · Beş bar kuralı: dönüş arayışı ne zaman iptal edilir (Ş, 2 panel)."""
    ortak = [
        B(100.0, 101.2, .3, .3), B(101.2, 102.5, .3, .3), B(102.5, 103.8, .4, .3),
        B(103.8, 105.0, .4, .3), B(105.0, 106.2, .4, .3), B(106.2, 107.4, .5, .3),
        B(107.4, 107.9, .6, .4),                                              # 6 eski uç 108.5
        B(107.8, 106.6, .3, .5), B(106.6, 105.4, .2, .5),
        B(105.5, 106.4, .4, .3), B(106.4, 107.6, .4, .3),                     # 9-10
    ]
    a = ortak + [
        B(107.6, 108.7, .4, .3), B(108.7, 109.2, .5, .3), B(109.1, 108.8, .4, .5),
        B(108.8, 108.6, .4, .5),                                              # 11-14: 4 kapanış üstte
        B(108.5, 107.2, .3, .5), B(107.2, 105.8, .2, .5), B(105.8, 104.4, .2, .5),
        B(104.4, 103.0, .2, .5), B(103.0, 101.8, .2, .6),
    ]
    c = ortak + [
        B(107.6, 108.7, .4, .3), B(108.7, 109.3, .4, .3), B(109.3, 109.9, .4, .3),
        B(109.8, 110.4, .4, .4), B(110.4, 110.9, .4, .3), B(110.9, 111.6, .5, .3),
        B(111.5, 111.0, .4, .5), B(111.0, 111.9, .5, .3), B(111.9, 112.6, .5, .3),
    ]
    d1, d2 = b.df_yap(a), b.df_yap(c)
    uc = float(d1.h[6])
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Panel 1 — eski ucun üstünde 4 kapanış: dönüş kurulumu ayakta",
        "Panel 2 — eski ucun üstünde 5'ten çok kapanış: süreç sıfırlandı"))

    def say_ve_ciz(df, satir, sinir):
        b.yatay(fig, uc, 0, len(df) - 1, renk=GRI, dash="dash", w=1.7, row=satir, col=1)
        b.not_(fig, 0, uc, f"eski uç {uc:.1f}", renk=GRI, ok=False, boyut=10,
               xanchor="left", yanchor="bottom", row=satir, col=1)
        n = 0
        for i in range(7, len(df)):
            if float(df.c[i]) > uc:
                n += 1
                renk = TEAL if n <= 4 else TURUNCU
                b.kutu(fig, i - .45, i + .45, float(df.l[i]), float(df.h[i]), renk,
                       a=0.20, cizgi=1.1, row=satir, col=1)
                b.not_(fig, i, float(df.h[i]), str(n), renk=renk, ok=False, boyut=10,
                       yanchor="bottom", row=satir, col=1)
            elif n:
                break
        return n

    fig.add_trace(b.mumlar(d1, "şematik"), row=1, col=1)
    n1 = say_ve_ciz(d1, 1, 4)
    b.not_(fig, 15, float(d1.h[14]) + .9,
           f"{n1} kapanış (≤ 4) → aşım bir TEST'tir; eski uç referans olarak duruyor",
           renk=TEAL, ok=False, boyut=11, xanchor="left", yanchor="bottom", row=1, col=1)
    t = b.islem(fig, d1, 15, "bear", hedefler=(float(d1.l[8]), float(d1.l.min())),
                etiketler=("düzeltme dibi", "yeni ayı bacağı"), row=1, col=1)

    fig.add_trace(b.mumlar(d2, "şematik"), row=2, col=1)
    n2 = say_ve_ciz(d2, 2, 4)
    b.not_(fig, 14, float(d2.l.min()) + 1.2,
           f"{n2} kapanış (≥ 5) → aşım değil, yeni bacak.<br>"
           "Dönüş sayımı sıfırlanır; referans artık yeni uçtur.", renk=TURUNCU, ok=False,
           boyut=11, row=2, col=1)
    yeni_uc = float(d2.h.max())
    b.yatay(fig, yeni_uc, 16, len(d2) - 1, renk=TEAL, dash="dot", row=2, col=1)
    b.not_(fig, len(d2) - 1, yeni_uc, f"yeni uç {yeni_uc:.1f}", renk=TEAL, ok=False,
           boyut=10, xanchor="right", yanchor="bottom", row=2, col=1)
    b.lejant(fig, "eski ucun üstünde kapanış (≤4)", TEAL)
    b.lejant(fig, "eşiği aşan kapanışlar (≥5)", TURUNCU)
    lejant_tekille(fig)
    b.duzen(fig, "Beş bar kuralı: dönüş arayışı ne zaman iptal edilir",
            "eski ucun ötesinde 5 veya daha çok kapanış varsa aşım değil yeni trend bacağı vardır",
            h=H2P, sematik=True)
    panelsiz_x(fig, 1)
    b.kaydet(fig, "60_bes_bar_kurali", olcum={
        "eski_uc": round(uc, 2), "panel1_kapanis_sayisi": n1, "panel2_kapanis_sayisi": n2,
        "esik": 5, "panel2_yeni_uc": round(yeni_uc, 2),
        "panel1_giris": round(t["giris"], 2), "panel1_risk": round(t["risk"], 2)})


# ==================================================================== 61
def _seri61():
    return [
        B(100.0, 100.9, .3, .3), B(100.9, 101.9, .3, .3), B(101.8, 102.5, .3, .4),
        B(102.5, 103.6, .3, .3), B(103.6, 104.8, .4, .3), B(104.7, 104.2, .3, .4),
        B(104.2, 105.4, .4, .3), B(105.4, 106.6, .4, .3), B(106.6, 107.9, .4, .3),
        B(107.8, 107.2, .3, .5), B(107.2, 108.6, .4, .3), B(108.6, 109.9, .4, .3),
        B(109.9, 111.0, .5, .3), B(111.0, 111.8, .7, .3),                     # 13 uç 112.5
        B(111.7, 110.4, .3, .4), B(110.4, 108.9, .2, .5), B(108.9, 107.6, .2, .5),
        B(107.6, 106.4, .2, .5), B(106.4, 105.6, .3, .5),                     # 18 karşı hareket dibi
        B(105.7, 106.6, .4, .3), B(106.6, 106.0, .3, .4), B(106.0, 106.9, .4, .3),
        B(106.9, 108.2, .4, .3), B(108.2, 109.6, .4, .3), B(109.6, 110.8, .5, .3),
        B(110.8, 111.4, .7, .3),                                              # 25 test 112.1
        B(111.3, 110.2, .4, .5),                                              # 26 ikinci dönüş
        B(110.2, 108.8, .2, .5), B(108.8, 107.4, .2, .5), B(107.4, 106.2, .2, .5),
        B(106.2, 105.2, .2, .5), B(105.2, 103.8, .2, .6), B(103.8, 102.4, .2, .5),
        B(102.5, 103.2, .5, .3), B(103.2, 101.9, .3, .5), B(101.9, 100.6, .2, .5),
        B(100.6, 99.4, .2, .6), B(99.4, 98.2, .2, .6), B(98.2, 97.2, .3, .6),
    ]


def f61_mtr_dort_kosul():
    """61 · Büyük trend dönüşünün dört zorunlu koşulu (Ş, 2 panel)."""
    ham = _seri61()
    d1 = b.df_yap(ham)
    K = 210.0
    d2 = b.df_yap(ayna(ham, K))
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Panel 1 — boğa tepesinde büyük trend dönüşü (MTR)",
        "Panel 2 — ayı dibinde aynı dört koşulun aynası"))

    def ciz(df, satir, yon):
        boga = yon == "bull"
        e = b.ema_ciz(fig, df, 20, renk=MAVI, row=satir, col=1)
        uc = float(df.h[13]) if boga else float(df.l[13])
        karsi = float(df.l[18]) if boga else float(df.h[18])
        test = float(df.h[25]) if boga else float(df.l[25])
        b.trend_cizgisi(fig, df, (0, 9) if boga else (0, 9), yon=yon, uzat=20,
                        renk=GRI, dash="dash", row=satir, col=1)
        b.yatay(fig, uc, 13, len(df) - 1, renk=GRI, dash="dot", row=satir, col=1)
        b.not_(fig, len(df) - 1, uc, f"eski uç {uc:.1f}", renk=GRI, ok=False, boyut=10,
               xanchor="right", yanchor="bottom" if boga else "top", row=satir, col=1)
        renk_t = TEAL if boga else BORDO
        b.kutu(fig, -0.5, 13.5, float(df.l[:14].min()), float(df.h[:14].max()),
               renk_t, a=0.08, cizgi=1.0, row=satir, col=1)
        b.not_(fig, 6, float(df.l[:14].min()) if boga else float(df.h[:14].max()),
               "1 · önünde bir trend olmalı", renk=renk_t, ok=False, boyut=11,
               yanchor="top" if boga else "bottom", row=satir, col=1)
        b.kutu(fig, 13.5, 18.5, min(karsi, uc), max(karsi, uc), TURUNCU, a=0.10, cizgi=1.0,
               row=satir, col=1)
        b.not_(fig, 16, karsi, "2 · trend çizgisini (ve tercihen MA'yı)<br>kıran karşı hareket",
               renk=TURUNCU, ax=-56, ay=(40 if boga else -40), boyut=10, row=satir, col=1)
        b.kutu(fig, 21.5, 26.5, min(test, karsi) if boga else min(karsi, test),
               max(test, karsi), MOR, a=0.10, cizgi=1.0, row=satir, col=1)
        b.not_(fig, 25, test, f"3 · eski ucun testi<br>({'daha düşük tepe' if boga else 'daha yüksek dip'}) "
               "ve ikinci dönüş", renk=MOR, ax=-118, ay=(-30 if boga else 30), boyut=10,
               row=satir, col=1)
        b.kutu(fig, 28.5, len(df) - .5, float(df.l[29:].min()), float(df.h[29:].max()),
               BORDO if boga else TEAL, a=0.10, cizgi=1.0, row=satir, col=1)
        b.not_(fig, 29.5, (float(df.h.max()) + 1.9) if boga else (float(df.l.min()) - 1.9),
               "4 · konsensüs hareketi: karşı hareketin ucu kırıldı → yeni trend",
               renk=BORDO if boga else TEAL, ok=False, boyut=10, xanchor="left",
               yanchor="top" if boga else "bottom", row=satir, col=1)
        b.yatay(fig, karsi, 18, len(df) - 1, renk=TURUNCU, dash="dot", row=satir, col=1)
        t = b.islem(fig, df, 26, "bear" if boga else "bull",
                    hedefler=(karsi, float(df.l.min()) if boga else float(df.h.max())),
                    etiketler=("karşı hareket ucu", "konsensüs"), row=satir, col=1)
        return dict(uc=round(uc, 2), karsi=round(karsi, 2), test=round(test, 2),
                    giris=round(t["giris"], 2), stop=round(t["stop"], 2),
                    risk=round(t["risk"], 2), r=[round(x, 1) for x in t["r"]],
                    ma_kirildi=bool((df.c[14:19] < e[14:19]).any() if boga
                                    else (df.c[14:19] > e[14:19]).any()))

    fig.add_trace(b.mumlar(d1, "şematik"), row=1, col=1)
    o1 = ciz(d1, 1, "bull")
    fig.add_trace(b.mumlar(d2, "şematik"), row=2, col=1)
    o2 = ciz(d2, 2, "bear")

    b.lejant_cizgi(fig, "20 bar EMA", MAVI, dash="solid")
    b.lejant_cizgi(fig, "trend çizgisi", GRI)
    b.lejant(fig, "koşul 2 · karşı hareket", TURUNCU)
    b.lejant(fig, "koşul 3 · uç testi", MOR)
    lejant_tekille(fig)
    b.duzen(fig, "Büyük trend dönüşünün dört zorunlu koşulu",
            "dördü de gerçekleşmeden dönüş yoktur; dördüncüsü gecikebilir (birkaç bar … 50+ bar)",
            h=H2P, sematik=True)
    panelsiz_x(fig, 1)
    b.kaydet(fig, "61_mtr_dort_kosul", olcum={"boga_tepesi": o1, "ayi_dibi": o2,
                                              "kosul_sayisi": 4})


# ==================================================================== 62
def f62_kosul3_varyantlari():
    """62 · Koşul 3'ün altı test varyantı (Ş, 2 panel)."""
    ortak = [
        B(100.0, 101.4, .3, .3), B(101.4, 102.9, .4, .3), B(102.9, 104.4, .4, .3),
        B(104.4, 105.8, .5, .3), B(105.8, 106.9, .7, .3),                     # 4 eski uç 107.6
        B(106.8, 105.6, .3, .5), B(105.6, 104.4, .2, .5),
        B(104.5, 105.4, .4, .3), B(105.4, 106.4, .4, .3),
    ]
    kuyruk = {
        "asan": [B(106.4, 107.6, .6, .3), B(107.5, 106.2, .3, .5), B(106.2, 104.9, .2, .5),
                 B(104.9, 103.6, .2, .6)],
        "esit": [B(106.4, 107.2, .4, .3), B(107.1, 105.9, .3, .5), B(105.9, 104.6, .2, .5),
                 B(104.6, 103.3, .2, .6)],
        "eksik": [B(106.4, 106.9, .4, .3), B(106.8, 105.6, .3, .5), B(105.6, 104.3, .2, .5),
                  B(104.3, 103.0, .2, .6)],
    }
    etiket = {"asan": "a · AŞAN test — daha yüksek tepe",
              "esit": "b · EŞİT test — kusursuz çift tepe",
              "eksik": "c · EKSİK test — daha düşük tepe"}
    etiket_dip = {"asan": "d · AŞAN test — daha düşük dip",
                  "esit": "e · EŞİT test — kusursuz çift dip",
                  "eksik": "f · EKSİK test — daha yüksek dip"}
    K = 210.0
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Panel 1 — tepede üç varyant (eski uç noktalı yatay çizgi)",
        "Panel 2 — dipte aynı üç varyantın aynası"))

    olcum = {}
    for satir, tersi in ((1, False), (2, True)):
        for k, (ad, kuy) in enumerate(kuyruk.items()):
            ham = ortak + kuy
            if tersi:
                ham = ayna(ham, K)
            df = b.df_yap(ham)
            off = k * 16
            x = list(range(off, off + len(df)))
            fig.add_trace(b.mumlar(df, ad, x=x), row=satir, col=1)
            uc = float(df.h[4]) if not tersi else float(df.l[4])
            test = float(df.h[9]) if not tersi else float(df.l[9])
            b.yatay(fig, uc, off - .6, off + len(df) - .4, renk=GRI, dash="dot", w=1.5,
                    row=satir, col=1)
            b.kutu(fig, off + 8.5, off + 10.5, float(df.l[9:11].min()), float(df.h[9:11].max()),
                   MOR, a=0.16, cizgi=1.1, row=satir, col=1)
            et = (etiket if not tersi else etiket_dip)[ad]
            b.not_(fig, off + 5, float(df.h.max()) + .8,
                   f"{et}<br>fark {test - uc:+.1f}", renk=MOR, ok=False, boyut=10,
                   yanchor="bottom", row=satir, col=1)
            b.not_(fig, off + 4, uc, "eski uç", renk=GRI, ok=False, boyut=9,
                   xanchor="left", yanchor="top" if not tersi else "bottom", row=satir, col=1)
            olcum[("tepe_" if not tersi else "dip_") + ad] = {
                "eski_uc": round(uc, 2), "test": round(test, 2), "fark": round(test - uc, 2)}

    b.not_(fig, 24, 99.0, "üç varyantın hiçbiri diğerinden üstün değildir: koşul 3 için "
           "gereken şey<br>ucun 'aşılıp aşılmadığı' değil, testten SONRA gelen ikinci dönüştür",
           renk=MUREKKEP, ok=False, boyut=10, row=1, col=1)
    b.lejant(fig, "test ve ikinci dönüş barı", MOR)
    b.lejant_cizgi(fig, "eski uç", GRI, dash="dot")
    lejant_tekille(fig)
    b.duzen(fig, "Koşul 3'ün altı test varyantı: aşan · eşit · eksik",
            "üç varyant tepede, üç varyant dipte; her biri 'iki itiş kuralı'nın bir hâli",
            h=H2P, sematik=True)
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    panelsiz_x(fig, 1)
    fig.update_xaxes(title_text="üç varyant yan yana (aynı panelde, ortak fiyat ekseni)",
                     row=2, col=1)
    fig.update_layout(showlegend=True)
    for tr in fig.data:
        if isinstance(tr, go.Candlestick):
            tr.showlegend = False
    b.kaydet(fig, "62_kosul3_varyantlari", olcum=olcum)


# ==================================================================== 63
def f63_erken_gec_giris():
    """63 · Erken giriş ile geç giriş: aynı dönüş, iki denklem (Ş, 2 panel)."""
    ham = [
        B(100.0, 101.4, .3, .3), B(101.4, 102.9, .4, .3), B(102.9, 104.5, .4, .3),
        B(104.5, 106.0, .4, .3), B(106.0, 107.4, .4, .3), B(107.4, 108.8, .5, .3),
        B(108.8, 109.8, .6, .3),                                              # 6 uç 110.4
        B(109.7, 108.4, .3, .5), B(108.4, 107.0, .2, .5), B(107.0, 106.0, .2, .5),  # 9 boyun
        B(106.1, 107.2, .4, .3), B(107.2, 108.4, .4, .3), B(108.4, 109.2, .5, .3),
        B(109.2, 109.6, .8, .3),                                              # 13 test 110.4
        B(109.5, 108.4, .4, .5),                                              # 14 ikinci dönüş barı
        B(108.4, 107.0, .2, .5), B(107.0, 105.8, .2, .5),
        B(105.8, 104.6, .2, .5),                                              # 17 boyun kırılımı
        B(104.7, 105.6, .4, .3), B(105.5, 104.4, .3, .4), B(104.4, 103.0, .2, .5),
        B(103.0, 101.6, .2, .5), B(101.6, 100.4, .2, .5), B(100.4, 99.2, .2, .6),
        B(99.2, 98.0, .2, .6), B(98.1, 98.9, .4, .3), B(98.8, 97.6, .3, .5),
        B(97.6, 96.4, .2, .5),
    ]
    df = b.df_yap(ham)
    uc = float(df.h[6])
    boyun = float(df.l[9])
    hedef = round(boyun - (uc - boyun), 2)

    erken_giris, erken_stop = 108.40, round(float(df.h[13]) + 0.20, 2)
    gec_giris, gec_stop = round(boyun - 0.20, 2), round(float(df.h[14]) + 0.20, 2)
    r_erken = (erken_giris - hedef) / (erken_stop - erken_giris)
    r_gec = (gec_giris - hedef) / (gec_stop - gec_giris)
    p_erken, p_gec = 0.45, 0.65
    bd_erken = p_erken * r_erken - (1 - p_erken)
    bd_gec = p_gec * r_gec - (1 - p_gec)

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13,
                        row_heights=[0.64, 0.36], subplot_titles=(
        "Panel 1 — aynı dönüş, iki giriş: E (erken, ucun testinde) ve G (geç, boyun kırılımında)",
        "Panel 2 — iki denklem: olasılık × ödül"))

    fig.add_trace(b.mumlar(df, "şematik"), row=1, col=1)
    b.yatay(fig, uc, 6, 24, renk=GRI, dash="dot", row=1, col=1)
    b.not_(fig, 6, uc, f"eski uç {uc:.1f}", renk=GRI, ok=False, boyut=10, xanchor="right",
           yanchor="bottom", row=1, col=1)
    b.yatay(fig, boyun, 9, 24, renk=ALTIN, dash="dash", row=1, col=1)
    b.not_(fig, 9, boyun, f"boyun (karşı hareketin dibi) {boyun:.1f}", renk=ALTIN, ok=False,
           boyut=10, xanchor="right", yanchor="top", row=1, col=1)
    b.yatay(fig, hedef, 17, 24, renk=MOR, dash="dash", w=1.6, row=1, col=1)
    b.not_(fig, 20, hedef, f"ortak hedef (ölçülmüş hareket) {hedef:.1f}", renk=MOR,
           ok=False, boyut=10, xanchor="left", yanchor="bottom", row=1, col=1)
    b.not_(fig, 14, erken_giris, f"E · erken giriş {erken_giris:.1f}", renk=BORDO,
           ax=-70, ay=-52, boyut=10, row=1, col=1)
    b.not_(fig, 17, gec_giris, f"G · geç giriş {gec_giris:.1f}", renk=MAVI,
           ax=-16, ay=54, boyut=10, row=1, col=1)

    # risk / ödül dikdörtgenleri — aynı fiyat ekseninde, yan yana ve ÖLÇEKLİ
    for x0, x1, gir, stp, renk, ad, rr in (
            (26.2, 27.4, erken_giris, erken_stop, BORDO, "E", r_erken),
            (28.6, 29.8, gec_giris, gec_stop, MAVI, "G", r_gec)):
        b.kutu(fig, x0, x1, gir, stp, BORDO, a=0.26, cizgi=1.1, row=1, col=1)
        b.kutu(fig, x0, x1, hedef, gir, YESIL, a=0.16, cizgi=1.0, row=1, col=1)
        b.not_(fig, (x0 + x1) / 2, hedef, f"{ad}<br>risk {stp - gir:.1f}<br>"
               f"ödül {gir - hedef:.1f}<br>{rr:.2f}R", renk=renk, ok=False, boyut=10,
               yanchor="top", row=1, col=1)
    b.not_(fig, 0.5, 99.6, "E: dönüş henüz kanıtlanmadı → olasılık düşük, stop küçük, ödül büyük<br>"
           "G: ikinci dönüş barı geçti, boyun kırıldı → olasılık yüksek,<br>"
           "ama stop bütün dönüş yapısının üstünde kalmak zorunda: ödül küçük",
           renk=MUREKKEP, ok=False, boyut=10, xanchor="left", row=1, col=1)

    kategori = ["olasılık (0–1)", "ödül / risk (R)", "beklenen değer (R)"]
    fig.add_trace(go.Bar(x=kategori, y=[p_erken, r_erken, bd_erken], name="E · erken giriş",
                         marker=dict(color=rgba(BORDO, 0.55), line=dict(color=BORDO, width=1.2)),
                         text=[f"%{p_erken*100:.0f}", f"{r_erken:.2f}R", f"{bd_erken:+.2f}R"],
                         textposition="outside", textfont=dict(size=11)), row=2, col=1)
    fig.add_trace(go.Bar(x=kategori, y=[p_gec, r_gec, bd_gec], name="G · geç giriş",
                         marker=dict(color=rgba(MAVI, 0.55), line=dict(color=MAVI, width=1.2)),
                         text=[f"%{p_gec*100:.0f}", f"{r_gec:.2f}R", f"{bd_gec:+.2f}R"],
                         textposition="outside", textfont=dict(size=11)), row=2, col=1)
    b.not_(fig, 2.45, 3.9,
           "iki üslup da meşrudur: beklenen değer ikisinde de pozitif.<br>"
           f"Erken girişin beklenen değeri büyük ({bd_erken:+.2f}R) ama on işlemin altısı "
           "zararla kapanır;<br>"
           f"geç girişin beklenen değeri küçük ({bd_gec:+.2f}R) ama seri çok daha az sarsıcıdır.<br>"
           "Seçim, traderın hangi hatayı taşıyabildiğine bağlıdır.", renk=MUREKKEP,
           ok=False, boyut=10, xanchor="right", yanchor="top", row=2, col=1)
    lejant_tekille(fig)
    b.duzen(fig, "Erken giriş ile geç giriş: aynı dönüş, iki denklem",
            "olasılık ile ödül ters yönde hareket eder; kazanma oranı yüksek olan üslup daha iyi üslup değildir",
            h=H2P + 120, sematik=True)
    fig.update_layout(barmode="group")
    panelsiz_x(fig, 1)
    fig.update_yaxes(title_text="değer (olasılık 0–1 · geri kalanı R)", range=[0, 4.6],
                     row=2, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    b.kaydet(fig, "63_erken_gec_giris", olcum={
        "eski_uc": round(uc, 2), "boyun": round(boyun, 2), "hedef": hedef,
        "erken": {"giris": erken_giris, "stop": erken_stop,
                  "risk": round(erken_stop - erken_giris, 2),
                  "odul": round(erken_giris - hedef, 2), "r": round(r_erken, 2),
                  "olasilik": p_erken, "beklenen_deger_r": round(bd_erken, 2)},
        "gec": {"giris": gec_giris, "stop": gec_stop,
                "risk": round(gec_stop - gec_giris, 2),
                "odul": round(gec_giris - hedef, 2), "r": round(r_gec, 2),
                "olasilik": p_gec, "beklenen_deger_r": round(bd_gec, 2)}})


# ==================================================================== main
def main():
    print("Brooks figürleri 46–63 (B6 · B7 · B8A)")
    for fn in (f46_high_sayimi, f47_low_sayimi, f48_h2_trend_bant, f49_abc,
               f50_kama_boga_bayragi, f51_cift_dip_tepe_bayragi, f52_derinlik_merdiveni,
               f53_ma_gap_bar, f54_yirmi_gap_bar, f55_ma_sarkmalari, f56_klimakslar,
               f57_klimaktik_donus, f58_trend_bitis_bicimleri, f59_donus_dizisi,
               f60_bes_bar_kurali, f61_mtr_dort_kosul, f62_kosul3_varyantlari,
               f63_erken_gec_giris):
        fn()
    b.defter_yaz()


if __name__ == "__main__":
    main()
