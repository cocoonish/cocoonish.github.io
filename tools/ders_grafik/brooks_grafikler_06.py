#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Al Brooks fiyat hareketi dersi — FİGÜR 79–94.

Kapsanan bölümler:
  B10 · işlem matematiği, trader denklemi            → 79, 80, 81, 82, 83, 84
  B11 · giriş, stop, kâr alma, ölçekleme             → 85, 86, 87, 88
  B12 · always-in ve gün tipleri                     → 89, 90
  B13 · seans, açılış aralığı, dönüm saatleri        → 91, 92
  B14 · üst zaman dilimi üçlemesi                    → 93
  B16 · kaçınılacak işlem                            → 94

Numaralar MÜFREDAT.md sürüm 2'nin "3. GRAFİK LİSTESİ" tablosundan (94 satır) gelir.

Kural notu: Brooks'un yüzdeleri (%40, %50, %60, %80…) istatistiksel ölçüm değil,
deneyime dayalı pratik eşiklerdir; figürlerde bu her seferinde altbaşlıkta yazılır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from brooks_ortak import (  # noqa: F401
    TEAL, BORDO, ALTIN, MAVI, MOR, TURUNCU, GRI, YESIL, MUREKKEP, KAGIT, IZGARA, CIZGI,
    rgba, yukle, dilim, seans, df_yap, bar, yol_uret, mumlar, kutu, yatay, cizgi, not_,
    lejant, lejant_cizgi, ema, ema_ciz, swingler, bar_say, bar_etiketle, islem,
    olculmus_hareket, trend_cizgisi, bosluk_isaretle, duzen, zaman_ekseni, hover,
    kaydet, defter_yaz,
)

ESIK = "yüzdeler Brooks'un deneyime dayalı pratik eşikleridir, ölçülmüş istatistik değildir"


# ===================================================================== yardımcılar
def zincir(bas: float, parcalar: list[tuple[int, float, float, int]]) -> list[tuple]:
    """(n, eğim, oynaklık, tohum) parçalarını uç uca ekleyerek deterministik yol üretir."""
    out: list[tuple] = []
    fiyat = bas
    for n, egim, oyn, tohum in parcalar:
        p = yol_uret(n, fiyat, egim, oyn, tohum)
        out += p
        fiyat = p[-1][3]
    return out


def olcekle(ohlc: list[tuple], lo: float = 0.0, hi: float = 100.0) -> list[tuple]:
    """Bir yolu dikeyde [lo, hi] aralığına doğrusal sıkıştırır (gün tipi silueti için)."""
    dizi = np.array(ohlc, dtype=float)
    a, b = dizi[:, 2].min(), dizi[:, 1].max()
    k = (hi - lo) / (b - a)
    dizi = (dizi - a) * k + lo
    return [tuple(round(v, 3) for v in satir) for satir in dizi]


def bar_okuma(df: pd.DataFrame) -> list[str]:
    """Her bar için tek satırlık Brooks okuması (hover metni).

    Ders bar okumayı öğretiyor; şematik figürlerde barın üstüne gelince gövde/menzil
    oranını ve kapanışın menzil içindeki yerini görmek, metne bakmadan aynı yargıyı
    kurmayı mümkün kılıyor.
    """
    out = []
    for i in range(len(df)):
        o, h, l, c = float(df.o[i]), float(df.h[i]), float(df.l[i]), float(df.c[i])
        menzil = max(h - l, 1e-9)
        govde = abs(c - o) / menzil
        yer = (c - l) / menzil
        if govde < 0.25:
            tip = "doji / duraklama barı"
        elif c > o:
            tip = "boğa trend barı" if govde >= 0.6 else "boğa barı"
        else:
            tip = "ayı trend barı" if govde >= 0.6 else "ayı barı"
        ust_k = (h - max(o, c)) / menzil
        alt_k = (min(o, c) - l) / menzil
        out.append(
            f"bar {i} · {tip}<br>gövde/menzil %{govde * 100:.0f}"
            f" · kapanış menzilin %{yer * 100:.0f} seviyesinde<br>"
            f"üst kuyruk %{ust_k * 100:.0f} · alt kuyruk %{alt_k * 100:.0f}"
            f" · menzil {tr(menzil)}")
    return out


def tr(x: float, n: int = 2, isaretli: bool = False) -> str:
    """Türkçe sayı biçimi: ondalık ayırıcı virgül (site dili Türkçe)."""
    return (f"{x:+.{n}f}" if isaretli else f"{x:.{n}f}").replace(".", ",")


AY_TR = {"Jan": "Oca", "Feb": "Şub", "Mar": "Mar", "Apr": "Nis", "May": "May",
         "Jun": "Haz", "Jul": "Tem", "Aug": "Ağu", "Sep": "Eyl", "Oct": "Eki",
         "Nov": "Kas", "Dec": "Ara"}
AY_TAM = {"January": "Ocak", "February": "Şubat", "March": "Mart", "April": "Nisan",
          "May": "Mayıs", "June": "Haziran", "July": "Temmuz", "August": "Ağustos",
          "September": "Eylül", "October": "Ekim", "November": "Kasım",
          "December": "Aralık"}


def gun_tr(t) -> str:
    """'18 June 2026' → '18 Haziran 2026'."""
    m = t.strftime("%d %B %Y")
    for en, tr_ in AY_TAM.items():
        m = m.replace(en, tr_)
    return m


def zaman_ekseni_tr(fig, df, adet=9, fmt="%d %b", row=None, col=None):
    """zaman_ekseni'nin Türkçe ay adlı sürümü (site dili Türkçe)."""
    n = len(df)
    adim = list(range(0, n, max(1, n // adet)))
    metin = []
    for i in adim:
        t = df.ts[i].strftime(fmt)
        for en, tr in AY_TR.items():
            t = t.replace(en, tr)
        metin.append(t)
    fig.update_xaxes(tickvals=adim, ticktext=metin, tickangle=0,
                     tickfont=dict(size=10), row=row, col=col)


def mumla(fig, df, row=None, col=None, ad=None, goster=False):
    """Mum serisini ekler; çok panelli figürlerde lejantı 'fiyat, fiyat' diye
    kirletmesin diye varsayılan olarak lejant dışıdır."""
    m = mumlar(df, ad=ad or "fiyat", hover=bar_okuma(df))
    m.showlegend = goster
    fig.add_trace(m, row=row, col=col)
    return m


def mum_grubu(fig, ohlc: list[tuple], x0: int, row=None, col=None, ad=None):
    """Bir siluet grubunu x0 ofsetinden başlayarak çizer (kartela figürleri)."""
    d = pd.DataFrame(ohlc, columns=["o", "h", "l", "c"])
    m = mumlar(d, ad=ad or "gün", x=list(range(x0, x0 + len(d))), hover=bar_okuma(d))
    m.showlegend = False
    fig.add_trace(m, row=row, col=col)
    return d


def ev_bar(fig, x, kazanc, kayip, net, row=None, col=None, ilk=False, hesap=None):
    """Trader denklemi üçlüsü: P×Ödül · (1−P)×Risk · beklenen değer.

    `hesap` verilirse her sütunun aritmetiği hover'da görünür — okur sayıyı grafikten
    okumak yerine hesabı doğrulayabilir.
    """
    metin = hesap or [""] * len(x)
    for dizi, ad, renk, grup in (
            (kazanc, "P × Ödül (kazanç beklentisi)", YESIL, "k"),
            (kayip, "(1−P) × Risk (kayıp beklentisi)", BORDO, "y"),
            (net, "beklenen değer (net)", MAVI, "n")):
        fig.add_trace(go.Bar(x=x, y=dizi, name=ad, text=metin, textposition="none",
                             hoverinfo="x+y+text",
                             marker_color=rgba(renk, 0.75),
                             marker_line=dict(color=renk, width=1.3),
                             showlegend=ilk, legendgroup=grup), row=row, col=col)


def deger_yaz(fig, x, y, birim="", row=None, col=None, kaydir=0.0, boyut=10, renk=MUREKKEP):
    for xi, yi in zip(x, y):
        if yi is None:
            continue
        not_(fig, xi, yi + kaydir,
             (tr(yi, isaretli=True) if yi < 0 else tr(yi)) + birim,
             renk=renk, ok=False, boyut=boyut,
             yanchor="bottom" if yi >= 0 else "top", row=row, col=col, arka=False)


# ===================================================================== 79
def f79_trader_denklemi():
    """Trader denklemi: üç değişkenin yüzeyi (Ş, 2 panel)."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16,
                        subplot_titles=("Panel 1 — tek kurulum: P × Ödül > (1−P) × Risk",
                                        "Panel 2 — aynı denklem, beş senaryo"))

    # --- panel 1: tek kurulum (P = %60, ödül 2 birim, risk 1 birim)
    P, ODUL, RISK = 0.60, 2.0, 1.0
    KOMISYON = 0.12                              # gidiş-dönüş maliyet, 1R'nin %12'si
    kaz, kay = P * ODUL, (1 - P) * RISK
    net = kaz - kay
    net_k = net - KOMISYON
    x1 = ["P × Ödül<br>0,60 × 2,0", "(1−P) × Risk<br>0,40 × 1,0",
          "Beklenen değer<br>1,20 − 0,40", "Komisyon eşiği<br>gidiş-dönüş maliyet",
          "Net beklenen değer<br>0,80 − 0,12"]
    y1 = [kaz, kay, net, KOMISYON, net_k]
    h1 = [f"kazanç beklentisi: {tr(P)} × {tr(ODUL)} = {tr(kaz)} birim",
          f"kayıp beklentisi: {tr(1 - P)} × {tr(RISK)} = {tr(kay)} birim",
          f"beklenen değer: {tr(kaz)} − {tr(kay)} = {tr(net, isaretli=True)} birim",
          f"gidiş-dönüş maliyet varsayımı: {tr(KOMISYON)} birim (1R'nin %{KOMISYON * 100:.0f}'si)",
          f"net beklenen değer: {tr(net)} − {tr(KOMISYON)} = {tr(net_k, isaretli=True)} birim"]
    fig.add_trace(go.Bar(x=x1, y=y1, showlegend=False, text=h1, textposition="none",
                         hoverinfo="x+y+text",
                         marker_color=[rgba(YESIL, 0.75), rgba(BORDO, 0.7), rgba(MAVI, 0.8),
                                       rgba(TURUNCU, 0.7), rgba(MAVI, 0.45)],
                         marker_line=dict(color=[YESIL, BORDO, MAVI, TURUNCU, MAVI],
                                          width=1.4),
                         width=0.52), row=1, col=1)
    deger_yaz(fig, x1, y1, " birim", row=1, col=1, kaydir=0.03)
    yatay(fig, 0, -0.5, 4.5, renk=GRI, dash="solid", w=1.0, row=1, col=1)
    not_(fig, 4.4, 2.28,
         "denklem net olarak pozitif → işlem alınır<br>"
         "üç değişken: olasılık · ödül · risk (dördüncüsü maliyettir)",
         renk=MAVI, ok=False, boyut=11, xanchor="right", row=1, col=1)
    not_(fig, 0, kaz + 0.42,
         "yüksek olasılık ile büyük ödül aynı anda olmaz:<br>"
         "biri artarsa karşı taraf öbürünü fiyatlar (karşı taraf simetrisi)",
         renk=MUREKKEP, ok=False, boyut=10.5, xanchor="left", row=1, col=1)
    not_(fig, 3, 0.86,
         "komisyon eşiği: küçük hedefli işlemlerde<br>maliyet, edge'in tamamını yiyebilir",
         renk=TURUNCU, ax=0, ay=-30, boyut=10, row=1, col=1)

    # --- panel 2: üç senaryo (tick cinsinden)
    sen = [
        ("scalp<br>P %70 · ödül 4 · risk 4", 0.70, 4.0, 4.0),
        ("swing<br>P %40 · ödül 12 · risk 4", 0.40, 12.0, 4.0),
        ("%90 olasılık anı<br>P %90 · ödül 2 · risk 8", 0.90, 2.0, 8.0),
        ("%10 olasılıklı ama geçerli<br>P %10 · ödül 20 · risk 2", 0.10, 20.0, 2.0),
        ("dar bant tepesinden alım<br>P %40 · ödül 4 · risk 8", 0.40, 4.0, 8.0),
    ]
    kazl = [round(s[1] * s[2], 2) for s in sen]
    kayl = [round((1 - s[1]) * s[3], 2) for s in sen]
    netl = [round(a - b, 2) for a, b in zip(kazl, kayl)]
    x2 = [f"{s[0]}<br><b>{tr(s[2] / s[3])}R → {tr(n, isaretli=True)} tick</b>"
          for s, n in zip(sen, netl)]
    hesap2 = [f"{tr(p)} × {o:.0f} = {tr(p * o)} tick<br>"
              f"{tr(1 - p)} × {r:.0f} = {tr((1 - p) * r)} tick<br>"
              f"net {tr(p * o - (1 - p) * r, isaretli=True)} tick · "
              f"ödül/risk {tr(o / r)}R" for _, p, o, r in sen]
    ev_bar(fig, x2, kazl, kayl, netl, row=2, col=1, ilk=True, hesap=hesap2)
    yatay(fig, 0, -0.5, len(sen) - 0.5, renk=GRI, dash="solid", w=1.0, row=2, col=1)
    not_(fig, 2, 7.0,
         "Aynı denklem, bambaşka üsluplar: %90 olasılıklı işlem küçücük bir ödül için "
         "büyük risk alır;<br>%10 olasılıklı işlem neredeyse hep kaybeder ama "
         "kazandığında hepsini geri verir. İkisi de geçerlidir.",
         renk=MUREKKEP, ok=False, boyut=10.5, row=2, col=1)
    not_(fig, 3.55, -3.2,
         "aynı kurulumun tersi (bant tepesini limitle satmak)<br>"
         "+3,20 tick verir: kötü denklem, karşı tarafın iyi denklemidir",
         renk=TURUNCU, ok=False, boyut=10.5, xanchor="right", row=2, col=1)

    fig.update_layout(barmode="group", bargap=0.32, bargroupgap=0.08)
    duzen(fig, "79 · Trader denklemi: üç değişkenin yüzeyi",
          "P × Ödül > (1−P) × Risk · " + ESIK, h=880, sematik=True)
    fig.update_yaxes(title_text="beklenen değer (birim)", row=1, col=1, range=[-0.2, 2.5])
    fig.update_yaxes(title_text="beklenen değer (tick)", row=2, col=1, range=[-5.0, 8.2])
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="senaryo", row=2, col=1)
    kaydet(fig, "79_trader_denklemi", olcum=dict(
        p1=dict(P=P, odul=ODUL, risk=RISK, kazanc=round(kaz, 3), kayip=round(kay, 3),
                beklenen_deger=round(net, 3), komisyon=KOMISYON,
                net_beklenen_deger=round(net_k, 3)),
        p2=[dict(ad=s[0].replace("<br>", " · "), P=s[1], odul=s[2], risk=s[3],
                 kazanc=k, kayip=y, beklenen_deger=n)
            for s, k, y, n in zip(sen, kazl, kayl, netl)]))


# ===================================================================== 80
def f80_takas_egrisi():
    """Olasılık–ödül takası eğrisi (Ş, 1 panel)."""
    fig = go.Figure()
    p = np.linspace(0.30, 0.92, 400)
    gerekli = (1 - p) / p                       # başabaş ödül/risk
    komisyon = 0.15                             # 1R'nin %15'i: gidiş-dönüş maliyet varsayımı
    gerekli_k = (1 - p + komisyon) / p

    fig.add_trace(go.Scatter(x=p * 100, y=np.minimum(gerekli, 4.2), mode="lines",
                             name="asgari gerekli ödül/risk (komisyonsuz)",
                             line=dict(color=MAVI, width=2.6)))
    fig.add_trace(go.Scatter(x=p * 100, y=np.minimum(gerekli_k, 4.2), mode="lines",
                             name=f"komisyon eşiği dâhil (maliyet = {tr(komisyon)}R)",
                             line=dict(color=TURUNCU, width=2.0, dash="dash")))
    # eğrinin altı = negatif denklem
    fig.add_trace(go.Scatter(x=list(p * 100) + [92, 30],
                             y=list(np.minimum(gerekli, 4.2)) + [0, 0],
                             fill="toself", mode="none", name="negatif denklem bölgesi",
                             fillcolor=rgba(TURUNCU, 0.13)))
    fig.add_trace(go.Scatter(x=list(p * 100) + [92, 30],
                             y=list(np.minimum(gerekli, 4.2)) + [4.2, 4.2],
                             fill="toself", mode="none", name="pozitif denklem bölgesi",
                             fillcolor=rgba(YESIL, 0.11)))

    noktalar = [(40, "swing bölgesi"), (50, ""), (60, "Brooks eşiği: 'olası'"),
                (70, "scalp bölgesi"), (80, "")]
    for pp, et in noktalar:
        g = (1 - pp / 100) / (pp / 100)
        fig.add_trace(go.Scatter(x=[pp], y=[g], mode="markers", showlegend=False,
                                 marker=dict(size=10, color=MAVI,
                                             line=dict(color=KAGIT, width=1.5))))
        not_(fig, pp, g, f"%{pp} → {tr(g)}R" + (f"<br>{et}" if et else ""),
             renk=MAVI, ax=32, ay=-34, boyut=10.5)

    kutu(fig, 30, 50, 0, 4.2, MOR, a=0.06, cizgi=0)
    not_(fig, 40, 3.9, "düşük olasılık · büyük ödül<br>(swing / dönüş işlemleri)",
         renk=MOR, ok=False, boyut=11)
    kutu(fig, 62, 92, 0, 4.2, TEAL, a=0.06, cizgi=0)
    not_(fig, 77, 3.9, "yüksek olasılık · küçük ödül<br>(scalp / trend devamı)",
         renk=TEAL, ok=False, boyut=11)
    yatay(fig, 1.0, 30, 92, renk=GRI, dash="dot", w=1.2)
    not_(fig, 91, 1.0, "ödül = risk", renk=GRI, ok=False, boyut=10, xanchor="right",
         yanchor="bottom")

    duzen(fig, "80 · Olasılık–ödül takası eğrisi",
          "denklem başabaş iken ödül/risk = (1−P)/P · " + ESIK,
          y_baslik="asgari gerekli ödül / risk (R)", x_baslik="kazanma olasılığı P (%)",
          h=620, sematik=True)
    fig.update_yaxes(range=[0, 4.2], title_text="asgari gerekli ödül / risk (R)")
    fig.update_xaxes(range=[30, 92])
    kaydet(fig, "80_takas_egrisi", olcum=dict(
        komisyon_R=komisyon,
        tablo={f"P{int(pp)}": round((1 - pp / 100) / (pp / 100), 3)
               for pp in (35, 40, 50, 60, 70, 80, 90)},
        tablo_komisyonlu={f"P{int(pp)}": round((1 - pp / 100 + komisyon) / (pp / 100), 3)
                          for pp in (35, 40, 50, 60, 70, 80, 90)}))


# ===================================================================== 81
def f81_duzeltme_aritmetigi():
    """Fibonacci yerine risk-ödül: %50 ve %67 düzeltme aritmetiği (Ş, 2 panel)."""
    ohlc = [
        (98.6, 99.7, 98.3, 99.4), (99.4, 100.0, 99.1, 99.8), (99.8, 100.0, 99.3, 99.5),
        (99.5, 99.7, 98.6, 98.8),
        (98.8, 99.0, 97.2, 97.4), (97.4, 97.6, 95.6, 95.8), (95.8, 96.1, 94.0, 94.3),
        (94.3, 94.6, 92.6, 92.8), (92.8, 93.0, 91.0, 91.3), (91.3, 91.6, 90.0, 90.4),
        (90.4, 91.8, 90.2, 91.6), (91.6, 93.2, 91.4, 93.0), (93.0, 94.2, 92.7, 93.9),
        (93.9, 95.3, 93.7, 95.1), (95.1, 95.8, 94.6, 95.5), (95.5, 96.9, 95.3, 96.7),
        (96.7, 97.0, 95.9, 96.1),
        (96.1, 96.3, 94.6, 94.8), (94.8, 95.0, 93.4, 93.6), (93.6, 93.9, 92.4, 92.7),
        (92.7, 92.9, 91.3, 91.5), (91.5, 91.8, 90.4, 90.7), (90.7, 90.9, 89.6, 89.9),
        (89.9, 90.2, 88.9, 89.1), (89.1, 89.5, 88.4, 88.7),
    ]
    df = df_yap(ohlc)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.15,
                        subplot_titles=("Panel 1 — aynı ayı atağı, iki giriş yeri (stop aynı)",
                                        "Panel 2 — iki denklem ve dönüş kurulumunun beklenen değeri"))
    mumla(fig, df, row=1, col=1)

    TEPE, DIP = 100.0, 90.0
    boy = TEPE - DIP
    e50, e67 = DIP + 0.50 * boy, DIP + 0.67 * boy      # 95,00 · 96,70
    for y, ad, renk in ((TEPE, "atağın tepesi 100,00 = ortak stop", BORDO),
                        (e67, "%67 düzeltme 96,70 — giriş B", MOR),
                        (e50, "%50 düzeltme 95,00 — giriş A", MAVI),
                        (DIP, "atağın dibi 90,00 = ortak hedef", YESIL)):
        yatay(fig, y, 0, 30.5, renk=renk, dash="dash", w=1.5, row=1, col=1)
        not_(fig, 0, y, ad, renk=renk, ok=False, boyut=10.5, xanchor="left",
             yanchor="bottom", row=1, col=1)
    kutu(fig, 3.6, 9.6, DIP, TEPE, GRI, a=0.07, cizgi=0.8, dash="dot", row=1, col=1)
    not_(fig, 6.6, DIP - 0.5, "ayı atağı: 10 birim", renk=GRI, ok=False, boyut=10.5,
         yanchor="top", row=1, col=1)
    not_(fig, 15, 97.6, "B: %67'de short<br>risk 3,3 · ödül 6,7 (2,0R)",
         renk=MOR, ax=-6, ay=-34, boyut=10.5, row=1, col=1)
    not_(fig, 13, 95.1, "A: %50'de short<br>risk 5,0 · ödül 5,0 (1,0R)",
         renk=MAVI, ax=-46, ay=-30, boyut=10.5, row=1, col=1)
    not_(fig, 16, 96.55, "dönüş barı", renk=ALTIN, ax=26, ay=-26, boyut=10, row=1, col=1)

    # ölçekli risk/ödül dikdörtgenleri
    for x0, x1, giris, ad, renk in ((26.0, 27.6, e50, "A · %50", MAVI),
                                    (28.8, 30.4, e67, "B · %67", MOR)):
        kutu(fig, x0, x1, giris, TEPE, BORDO, a=0.22, cizgi=1.1, row=1, col=1)
        kutu(fig, x0, x1, DIP, giris, YESIL, a=0.22, cizgi=1.1, row=1, col=1)
        not_(fig, (x0 + x1) / 2, (giris + TEPE) / 2, f"risk<br>{tr(TEPE - giris, 1)}",
             renk=BORDO, ok=False, boyut=9.5, row=1, col=1, arka=False)
        not_(fig, (x0 + x1) / 2, (DIP + giris) / 2, f"ödül<br>{tr(giris - DIP, 1)}",
             renk=YESIL, ok=False, boyut=9.5, row=1, col=1, arka=False)
        not_(fig, (x0 + x1) / 2, TEPE + 0.4, ad, renk=renk, ok=False, boyut=10.5, row=1, col=1)
    fig.update_xaxes(range=[-0.8, 32.5], row=1, col=1)

    # --- panel 2: R cinsinden denklemler
    A = dict(P=0.60, odul_R=1.00, risk=5.0, odul=5.0)
    B = dict(P=0.50, odul_R=6.7 / 3.3, risk=3.3, odul=6.7)
    x2 = ["A · %50 düzeltme<br>P %60 · ödül 1,0R",
          "B · %67 düzeltme<br>P %50 · ödül 2,0R",
          "ortalama dönüş<br>kurulumu",
          "en iyi dönüş<br>kurulumu"]
    kaz = [round(A["P"] * A["odul_R"], 3), round(B["P"] * B["odul_R"], 3), None, None]
    kay = [round((1 - A["P"]) * 1.0, 3), round((1 - B["P"]) * 1.0, 3), None, None]
    net = [round(kaz[0] - kay[0], 3), round(kaz[1] - kay[1], 3), 0.65, 0.95]
    ev_bar(fig, x2, kaz, kay, net, row=2, col=1, ilk=True)
    yatay(fig, 0, -0.5, 3.5, renk=GRI, dash="solid", w=1.0, row=2, col=1)
    not_(fig, 0, 0.78, "birim: 0,60×5 − 0,40×5 = +1,00 birim", renk=MAVI, ok=False,
         boyut=10.5, row=2, col=1)
    not_(fig, 1, 1.20, "birim: 0,50×6,7 − 0,50×3,3 = +1,70 birim", renk=MAVI, ok=False,
         boyut=10.5, row=2, col=1)
    not_(fig, 2.5, 1.20,
         "Brooks'un %61,8 yerine %67'yi anmasının nedeni oranın adı değil,<br>"
         "ürettiği risk-ödül geometrisidir: daha derin giriş, daha küçük risk.",
         renk=MUREKKEP, ok=False, boyut=10.5, row=2, col=1)
    fig.update_layout(barmode="group", bargap=0.32)
    duzen(fig, "81 · Fibonacci yerine risk-ödül: %50 ve %67 düzeltme aritmetiği",
          "düzeltme seviyesi bir kehanet değil bir fiyat noktasıdır · " + ESIK,
          h=1000, sematik=True)
    fig.update_yaxes(title_text="fiyat (şematik birim)", row=1, col=1)
    fig.update_yaxes(title_text="beklenen değer (R)", row=2, col=1, range=[-0.2, 1.55])
    fig.update_xaxes(title_text="bar sırası", row=1, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    kaydet(fig, "81_duzeltme_aritmetigi", olcum=dict(
        tepe=TEPE, dip=DIP, atak=boy, giris_50=e50, giris_67=e67,
        A=dict(risk=5.0, odul=5.0, R=1.0, P=0.60, ev_birim=1.0, ev_R=round(net[0], 3)),
        B=dict(risk=3.3, odul=6.7, R=round(6.7 / 3.3, 2), P=0.50, ev_birim=1.7,
               ev_R=round(net[1], 3)),
        ortalama_donus_R=0.65, en_iyi_donus_R=0.95))


# ===================================================================== 82
def f82_buyuyen_spike():
    """Büyüyen spike'ın matematiği (Ş, 2 panel)."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.15,
                        subplot_titles=("Panel 1 — spike 3 / 7 / 8 puanken denklem",
                                        "Panel 2 — fiyat karşılığı: üç bar, 8 puanlık spike"))

    # --- panel 1
    sen = [
        ("spike 3 puan<br>1. kademe · giriş 103,00", 3.00, 3.00, 0.60),
        ("spike 7 puan<br>2. kademe · giriş 107,00", 3.00, 7.00, 0.50),
        ("spike 8 puan<br>baştan girenin durumu", 3.00, 13.00, 0.60),
        ("spike 8 puan<br>şimdi giren · giriş 108,00", 8.25, 8.00, 0.60),
    ]
    kaz = [round(s[3] * s[2], 2) for s in sen]
    kay = [round((1 - s[3]) * s[1], 2) for s in sen]
    net = [round(a - b, 2) for a, b in zip(kaz, kay)]
    x1 = [f"{s[0]}<br>risk {tr(s[1])} · ödül {tr(s[2])}"
          f"<br><b>{tr(s[2] / s[1])}R → {tr(n, isaretli=True)} puan</b>"
          for s, n in zip(sen, net)]
    hesap1 = [f"{tr(p)} × {tr(o)} = {tr(p * o)} puan<br>"
              f"{tr(1 - p)} × {tr(r)} = {tr((1 - p) * r)} puan<br>"
              f"net {tr(p * o - (1 - p) * r, isaretli=True)} puan · "
              f"ödül/risk {tr(o / r)}R" for _, r, o, p in sen]
    ev_bar(fig, x1, kaz, kay, net, row=1, col=1, ilk=True, hesap=hesap1)
    yatay(fig, 0, -0.5, 3.5, renk=GRI, dash="solid", w=1.0, row=1, col=1)
    not_(fig, 1.5, 8.4,
         "erken girenin riski DONAR (3,00 puan), hedefi BÜYÜR;<br>"
         "geç girenin ikisi birden kötüleşir: 8,25 risk için 8,00 ödül = 0,97R",
         renk=MUREKKEP, ok=False, boyut=11, row=1, col=1)

    # --- panel 2: 8 puanlık spike (bar boyları 14 / 10 / 8 tick, 1 puan = 4 tick)
    ohlc = yol_uret(7, 99.55, 0.02, 0.22, 8201)
    ohlc += [
        (100.00, 103.50, 99.75, 103.50),   # 14 tick, tıraşlı üst
        (103.50, 106.00, 103.50, 106.00),  # 10 tick
        (106.00, 108.25, 106.00, 108.00),  # 8 tick
        (108.00, 108.30, 107.60, 107.90),  # doji: spike bitti
    ]
    ohlc += yol_uret(20, 107.90, 0.44, 0.55, 8202)
    df = df_yap(ohlc)
    mumla(fig, df, row=2, col=1)
    i0 = 7                                   # spike'ın ilk barı
    kutu(fig, i0 - 0.5, i0 + 2.5, 99.75, 108.30, ALTIN, a=0.13, cizgi=1.2, row=2, col=1)
    not_(fig, i0 + 1, 99.4, "spike: 3 boğa trend barı · örtüşme yok · en büyük kuyruk 2 tick<br>"
                            "bar boyları 14 / 10 / 8 tick = 8,00 puan",
         renk=ALTIN, ok=False, boyut=10.5, yanchor="top", row=2, col=1)
    not_(fig, i0 + 3, 108.55, "doji → spike bitti", renk=GRI, ax=30, ay=-28, boyut=10,
         row=2, col=1)

    for y, ad, renk, dash in ((100.00, "spike tabanı 100,00 (1. stop)", BORDO, "dot"),
                              (103.00, "1. kademe giriş 103,00 (spike 3 puan)", MAVI, "solid"),
                              (107.00, "2. kademe giriş 107,00 (spike 7 puan)", MAVI, "solid"),
                              (108.00, "spike kapanışı 108,00 · geç girişin yeri", GRI, "dash"),
                              (116.00, "ölçülmüş hareket hedefi 116,00 = 108,00 + 8,00", MOR, "dash")):
        yatay(fig, y, i0 - 1, len(df) - 1, renk=renk, dash=dash, w=1.5, row=2, col=1)
        not_(fig, len(df) - 1, y, ad, renk=renk, ok=False, boyut=10, xanchor="left",
             row=2, col=1)
    yatay(fig, 99.75, i0 + 3, len(df) - 1, renk=TURUNCU, dash="dot", w=1.4, row=2, col=1)
    not_(fig, len(df) - 1, 99.75, "geç girenin stopu 99,75 → risk 8,25", renk=TURUNCU,
         ok=False, boyut=10, xanchor="left", row=2, col=1)
    fig.add_shape(type="line", x0=i0 + 2, y0=108.00, x1=i0 + 2, y1=116.00,
                  line=dict(color=MOR, width=2.6), row=2, col=1)
    not_(fig, i0 + 2, 112.0, "8,00 puan", renk=MOR, ok=False, boyut=10, row=2, col=1)
    fig.update_xaxes(range=[-0.8, len(df) + 8], row=2, col=1)

    fig.update_layout(barmode="group", bargap=0.30)
    duzen(fig, "82 · Büyüyen spike'ın matematiği",
          "trader denklemi her tick'te yeniden hesaplanır · " + ESIK, h=1020, sematik=True)
    fig.update_yaxes(title_text="beklenen değer (puan)", row=1, col=1, range=[-0.8, 9.6])
    fig.update_yaxes(title_text="fiyat (şematik puan)", row=2, col=1)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="bar sırası", row=2, col=1)
    kaydet(fig, "82_buyuyen_spike", olcum=dict(
        spike_taban=100.00, spike_kapanis=108.00, spike_boyu=8.00,
        bar_tick=[14, 10, 8], mm_hedef=116.00,
        kademeler=[dict(ad=s[0].replace("<br>", " · "), risk=s[1], odul=s[2], P=s[3],
                        R=round(s[2] / s[1], 2), ev=n) for s, n in zip(sen, net)]))


# ===================================================================== 83
def f83_kanal_erozyonu():
    """Yönsel olasılığın kanal boyunca erozyonu (Ş, 1 panel)."""
    ohlc = yol_uret(5, 99.6, 0.0, 0.30, 8301)
    ohlc += [(100.00, 102.10, 99.85, 102.00),
             (102.00, 104.20, 102.00, 104.10),
             (104.10, 106.10, 104.05, 106.00)]
    # kanal ilerledikçe eğim azalır, geri çekilmeler DERİNLEŞİR: alıcının riski büyür
    ohlc += zincir(106.00, [(11, 0.58, 0.30, 8303),
                            (11, 0.36, 0.58, 8321),
                            (12, 0.14, 0.92, 8345)])
    df = df_yap(ohlc)
    fig = go.Figure()
    mumla(fig, df, goster=True)

    kutu(fig, 4.5, 7.5, df.l[5:8].min(), df.h[5:8].max(), ALTIN, a=0.14, cizgi=1.2)
    not_(fig, 6, df.l[5:8].min() - 0.7, "kırılım spike'ı", renk=ALTIN, ok=False, boyut=10.5,
         yanchor="top")
    trend_cizgisi(fig, df, (8, 26), yon="bull", kanal=True, renk=GRI, uzat=38)
    lejant_cizgi(fig, "trend çizgisi (dipler)", GRI, dash="dash")
    lejant_cizgi(fig, "trend kanal çizgisi (tepeler)", GRI, dash="dot")

    etiketler = [(6, 70, "kırılım anı: spike lehte", TEAL),
                 (12, 60, "kanalın başı", TEAL),
                 (19, 55, "kanalın ortası", ALTIN),
                 (27, 50, "kanalın sonu: yazı-tura", TURUNCU),
                 (36, 45, "kanal tepesi / aşım: karşı taraf öne geçti", BORDO)]
    for x, yuzde, ad, renk in etiketler:
        y = df.h[max(0, x - 1):x + 2].max()
        not_(fig, x, y + 0.9, f"%{yuzde}<br>{ad}", renk=renk, ok=True, ax=0, ay=-42,
             boyut=10.5)
    # kanal genişliği = alıcının riski; olasılık erirken risk büyür
    genislikler = []
    for x, ad in ((12, "kanalın başı"), (22, "kanalın ortası"), (34, "kanalın sonu")):
        alt = float(df.l[max(0, x - 4):x + 1].min())
        ust = float(df.h[max(0, x - 4):x + 1].max())
        fig.add_shape(type="line", x0=x + 0.55, y0=alt, x1=x + 0.55, y1=ust,
                      line=dict(color=BORDO, width=2.2))
        for uc in (alt, ust):
            cizgi(fig, x + 0.30, uc, x + 0.80, uc, renk=BORDO, w=2.0)
        not_(fig, x + 0.95, (alt + ust) / 2,
             f"geri çekilme riski<br>{tr(ust - alt)} birim", renk=BORDO, ok=False,
             boyut=9.5, xanchor="left")
        genislikler.append(dict(bar=x, ad=ad, genislik=round(ust - alt, 2)))
    lejant(fig, "aynı işlemin risk mesafesi (kanal derinliği)", BORDO, a=0.25)

    not_(fig, 30, df.l.min() + 0.6,
         "Aynı yönde alım, kanal boyunca aynı işlem DEĞİLDİR:<br>"
         "risk (kanal genişliği) büyürken yönsel olasılık erir.<br>"
         "Boğa kanalı, aynı zamanda bir ayı bayrağıdır.",
         renk=MUREKKEP, ok=False, boyut=11, xanchor="right")
    duzen(fig, "83 · Yönsel olasılığın kanal boyunca erozyonu",
          "eşit uzaklıklı hareketin yönsel olasılığı · " + ESIK, h=640, sematik=True)
    kaydet(fig, "83_kanal_erozyonu", olcum=dict(
        yuzdeler={ad: y for _, y, ad, _ in etiketler},
        spike_barlari=[5, 6, 7], kanal_baslangic=8, kanal_bitis=len(df) - 1,
        risk_mesafeleri=genislikler))


# ===================================================================== 84
def f84_kazanma_orani():
    """Scalp ile swing'in gerekli kazanma oranı (Ş, 1 panel)."""
    fig = go.Figure()
    rr = np.linspace(0.25, 4.0, 400)
    basabas = 100.0 / (1.0 + rr)
    komisyon = 0.10
    basabas_k = 100.0 * (1.0 + komisyon) / (rr + 1.0)

    fig.add_trace(go.Scatter(x=rr, y=basabas, mode="lines",
                             name="başabaş kazanma oranı = 1/(1+ödül/risk)",
                             line=dict(color=MAVI, width=2.6)))
    fig.add_trace(go.Scatter(x=rr, y=basabas_k, mode="lines",
                             name=f"komisyon eşiği dâhil (maliyet = {tr(komisyon)}R)",
                             line=dict(color=TURUNCU, width=2.0, dash="dash")))
    fig.add_trace(go.Scatter(x=list(rr) + [4.0, 0.25], y=list(basabas) + [100, 100],
                             fill="toself", mode="none", name="kârlı bölge (bu oranın üstü)",
                             fillcolor=rgba(YESIL, 0.11)))

    kutu(fig, 0.25, 1.05, 0, 100, TEAL, a=0.06, cizgi=0)
    not_(fig, 0.62, 92, "scalp bölgesi<br>ödül ≈ risk", renk=TEAL, ok=False, boyut=11)
    kutu(fig, 2.0, 4.0, 0, 100, MOR, a=0.06, cizgi=0)
    not_(fig, 3.0, 92, "swing bölgesi<br>ödül ≥ 2 × risk", renk=MOR, ok=False, boyut=11)

    isaret = [(0.5, "4 tick hedef / 8 tick risk"), (1.0, "scalp: 4 tick / 4 tick"),
              (2.0, "swing: 2R"), (3.0, "swing: 3R")]
    for r, ad in isaret:
        y = 100.0 / (1 + r)
        yk = 100.0 * (1 + komisyon) / (r + 1)
        fig.add_trace(go.Scatter(x=[r], y=[y], mode="markers", showlegend=False,
                                 marker=dict(size=10, color=MAVI,
                                             line=dict(color=KAGIT, width=1.5))))
        not_(fig, r, y, f"{ad}<br>başabaş %{tr(y, 1)}  (komisyonla %{tr(yk, 1)})",
             renk=MAVI, ax=54, ay=-30, boyut=10.5)
    yatay(fig, 60, 0.25, 4.0, renk=GRI, dash="dot", w=1.2)
    not_(fig, 3.95, 60, "Brooks'un 'olası' eşiği %60", renk=GRI, ok=False, boyut=10,
         xanchor="right", yanchor="bottom")
    not_(fig, 3.95, 12,
         "Scalper ikilemi: küçük hedef yüksek olasılık verir ama<br>"
         "gerekli kazanma oranını da yükseltir; bir tick'lik ıskalamalar<br>"
         "(17 tick başarısızlığı) denklemin işaretini değiştirebilir.",
         renk=MUREKKEP, ok=False, boyut=10.5, xanchor="right")
    duzen(fig, "84 · Scalp ile swing'in gerekli kazanma oranı",
          "başabaş kazanma oranı ödül/risk'in tersidir · " + ESIK,
          y_baslik="başabaş için gereken kazanma oranı (%)", x_baslik="ödül / risk (R)",
          h=620, sematik=True)
    fig.update_yaxes(range=[0, 100],
                     title_text="başabaş için gereken kazanma oranı (%)")
    fig.update_xaxes(range=[0.25, 4.0])
    kaydet(fig, "84_kazanma_orani", olcum=dict(
        komisyon_R=komisyon,
        basabas={f"R{r}": round(100 / (1 + r), 1) for r in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)},
        basabas_komisyonlu={f"R{r}": round(100 * (1 + komisyon) / (r + 1), 1)
                            for r in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)}))


# ===================================================================== 85
def f85_emir_haritasi():
    """Stop emri ile limit emri giriş haritası (Ş, 1 panel)."""
    ohlc = [(99.6, 100.1, 99.2, 99.9), (99.9, 100.3, 99.5, 99.6),
            (99.6, 100.0, 99.1, 99.8), (99.8, 100.2, 99.4, 99.5),
            (99.5, 99.9, 99.0, 99.7), (99.7, 100.1, 99.3, 99.4),
            (99.4, 99.9, 98.9, 99.8), (99.8, 100.2, 99.5, 99.6),
            (99.6, 100.0, 99.2, 99.9), (99.9, 100.3, 99.5, 99.6),
            (99.6, 100.1, 99.2, 100.0),
            (99.7, 101.4, 99.5, 100.2),                      # 11: merkez bar
            (100.2, 100.6, 99.6, 100.0), (100.0, 100.4, 99.3, 99.5),
            (99.5, 100.1, 99.1, 99.9), (99.9, 100.4, 99.4, 100.1),
            (100.1, 100.5, 99.7, 99.8), (99.8, 100.2, 99.3, 100.0),
            (100.0, 100.4, 99.5, 99.6), (99.6, 100.1, 99.2, 99.9),
            (99.9, 100.3, 99.4, 99.5)]
    df = df_yap(ohlc)
    fig = go.Figure()
    mumla(fig, df, goster=True)
    m = 11
    kutu(fig, -0.5, 10.5, float(df.l[:11].min()), float(df.h[:11].max()), GRI, a=0.08,
         cizgi=0.9, dash="dot")
    not_(fig, 5, float(df.h[:11].max()) + 0.10,
         "ekranın solu: bu bar bir yatay bandın içinde mi, trendin içinde mi?<br>"
         "aynı dört emir, iki bağlamda ters kararlar üretir",
         renk=GRI, ok=False, boyut=10)
    ust, alt = df.h[m], df.l[m]
    tick = 0.05
    kutu(fig, m - 0.45, m + 0.45, alt, ust, ALTIN, a=0.16, cizgi=1.4)
    not_(fig, m, (alt + ust) / 2, "sinyal barı", renk=ALTIN, ok=False, boyut=10.5)

    yatay(fig, ust + tick, 0.5, 19.6, renk=GRI, dash="dash", w=1.3)
    not_(fig, 0.5, ust + tick, "barın 1 tick ÜSTÜ", renk=GRI, ok=False, boyut=10,
         xanchor="left", yanchor="bottom")
    yatay(fig, alt - tick, 0.5, 19.6, renk=GRI, dash="dash", w=1.3)
    not_(fig, 0.5, alt - tick, "barın 1 tick ALTI", renk=GRI, ok=False, boyut=10,
         xanchor="left", yanchor="top")

    emirler = [
        (ust + tick, "① ALIŞ STOPU (buy stop)", MAVI, 19.6, 102.22,
         "gerekçe: boğa kırılımı / trend devamı · fiyatın ÖNÜNE emir"),
        (ust + tick, "② SATIŞ LİMİTİ (sell limit)", BORDO, 19.6, 101.42,
         "gerekçe: bant ya da kanal tepesini fade etmek · fiyatın KARŞISINA emir"),
        (alt - tick, "③ ALIŞ LİMİTİ (buy limit)", TEAL, 19.6, 98.45,
         "gerekçe: boğa bayrağında geri çekilmeyi almak · fiyatın KARŞISINA emir"),
        (alt - tick, "④ SATIŞ STOPU (sell stop)", BORDO, 19.6, 97.65,
         "gerekçe: ayı kırılımı / trend devamı · fiyatın ÖNÜNE emir"),
    ]
    for y, ad, renk, xa, ya, gerekce in emirler:
        not_(fig, xa, ya, f"<b>{ad}</b><br>{gerekce}", renk=renk, ok=False, boyut=10.5,
             xanchor="right")
        fig.add_annotation(x=m + 0.55, y=y, ax=xa - 0.15, ay=ya, xref="x", yref="y",
                           axref="x", ayref="y", showarrow=True, arrowhead=2,
                           arrowsize=1, arrowwidth=1.2, arrowcolor=renk, text="")

    # beşinci emir: son çare / en kötü durum giriş stopu (İ23)
    son_care = round(ust + 0.30, 2)
    yatay(fig, son_care, 0.5, 19.6, renk=MOR, dash="dashdot", w=1.5)
    not_(fig, 0.4, 102.28,
         "<b>⑤ SON ÇARE ALIŞ STOPU</b> (en kötü durum girişi)<br>"
         "gerekçe: geri çekilme gelmiyor, trend tamamen kaçırılmasın<br>"
         "yalnızca gerçek trendde meşrudur; bantta tuzağa döner",
         renk=MOR, ok=False, boyut=10.5, xanchor="left")

    not_(fig, 8.5, 97.45,
         "Aynı barın aynı iki ucunda DÖRT ayrı işlem vardır.<br>"
         "Emri hangi ucun hangi tarafına koyduğun, tezin ne olduğunu söyler:<br>"
         "stop emri kırılıma katılır, limit emri kırılımı fade eder.<br>"
         "Piyasa emri fiilen bir limit emridir — karşı tarafın limitini alırsın.",
         renk=MUREKKEP, ok=False, boyut=10.5)
    fig.update_yaxes(range=[96.9, 102.6])
    fig.update_xaxes(range=[-0.6, 20.0])
    duzen(fig, "85 · Stop emri ile limit emri giriş haritası",
          "tek bar · dört giriş biçimi · dört ayrı gerekçe (+ son çare stopu)", h=700,
          sematik=True)
    kaydet(fig, "85_emir_haritasi", olcum=dict(
        sinyal_bar=m, bar_ust=ust, bar_alt=alt, tick=tick,
        alis_stop=round(ust + tick, 2), satis_limit=round(ust + tick, 2),
        alis_limit=round(alt - tick, 2), satis_stop=round(alt - tick, 2),
        son_care_alis_stopu=son_care))


# ===================================================================== 86
def f86_stop_merdiveni():
    """Stop yerleşimi ve sıkılaştırma merdiveni (Ş, 2 panel)."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.15,
                        subplot_titles=("Panel 1 — stop merdiveni: sinyal barı → giriş barı → başabaş → iz süren",
                                        "Panel 2 — doji sonrası stop sıkılaştırma yasağı"))

    # --- panel 1
    ohlc = [(100.0, 100.6, 99.5, 100.3), (100.3, 100.5, 99.4, 99.6),
            (99.6, 99.8, 98.7, 98.9), (98.9, 99.1, 98.0, 98.2),
            (98.2, 98.4, 97.4, 97.6),
            (97.6, 98.9, 97.30, 98.75),                     # 5: sinyal barı (boğa dönüş barı)
            (98.80, 100.20, 98.60, 100.05),                 # 6: giriş barı
            (100.05, 100.90, 99.70, 100.80)]
    ohlc += zincir(100.80, [(6, 0.55, 0.40, 8601), (4, -0.30, 0.35, 8602),
                            (8, 0.65, 0.42, 8603)])
    df = df_yap(ohlc)
    mumla(fig, df, row=1, col=1)
    s = 5
    tick = 0.05
    giris = round(df.h[s] + tick, 2)
    kutu(fig, s - 0.45, s + 0.45, df.l[s], df.h[s], ALTIN, a=0.20, cizgi=1.3, row=1, col=1)
    not_(fig, s, df.h[s] + 0.25, "sinyal barı", renk=ALTIN, ok=False, boyut=10, row=1, col=1)
    not_(fig, 6, df.l[6] - 0.30, "giriş barı", renk=MAVI, ok=False, boyut=10,
         yanchor="top", row=1, col=1)
    yatay(fig, giris, s, len(df) - 1, renk=MAVI, dash="solid", w=1.6, row=1, col=1)
    not_(fig, len(df) - 0.6, giris, f"giriş {tr(giris)}", renk=MAVI, ok=False, boyut=10,
         xanchor="left", row=1, col=1)

    swing_dip = round(df.l[14:18].min() - tick, 2)      # 14–17: bacak içi geri çekilme
    kademeler = [
        (round(df.l[s] - tick, 2), 5, 8, "① sinyal barının 1 tick altı — ilk stop (fiyat hareketi stopu)"),
        (round(df.l[6] - tick, 2), 8, 11, "② giriş barının 1 tick altı — bar kapanınca sıkılaştır"),
        (giris, 11, 18, "③ başabaş — ancak yeterli açık kâr oluştuktan SONRA"),
        (swing_dip, 18, len(df) - 1, "④ iz süren — son salınım dibinin 1 tick altı"),
    ]
    renkler = [BORDO, TURUNCU, GRI, TEAL]
    yanchorlar = ["top", "top", "bottom", "bottom"]
    for (y, x0, x1, ad), renk, ya in zip(kademeler, renkler, yanchorlar):
        yatay(fig, y, x0 - 0.4, x1, renk=renk, dash="dot", w=2.4, row=1, col=1)
        not_(fig, x1 + 0.25, y, ad, renk=renk, ok=False, boyut=10, xanchor="left",
             yanchor=ya, row=1, col=1)
    risk = round(giris - kademeler[0][0], 2)
    not_(fig, 0.0, 109.4,
         f"risk = giriş {tr(giris)} − ilk stop {tr(kademeler[0][0])} = {tr(risk)} birim = 1R<br>"
         "pozisyon boyutu = risk bütçesi ÷ bu mesafe (tezin gücünden değil)",
         renk=MUREKKEP, ok=False, boyut=10.5, xanchor="left", row=1, col=1)
    not_(fig, 0.0, 106.6,
         "başabaşa çekmenin bedeli: başabaş stop bir mıknatıstır,<br>"
         "kırılım testi onu kuruşu kuruşuna avlar (İ14). Kural: en büyük açık kâr<br>"
         "riskin ~1,5 katına ulaşmadan stop başabaşa çekilmez.",
         renk=TURUNCU, ok=False, boyut=10.5, xanchor="left", row=1, col=1)

    # --- panel 2: doji sonrası sıkılaştırma yasağı
    o2 = zincir(100.0, [(7, 0.55, 0.35, 8611)])
    p = o2[-1][3]
    o2 += [(p, p + 0.28, p - 0.26, p + 0.03)]              # 7: doji
    p = o2[-1][3]
    o2 += [(p, p + 0.15, p - 0.95, p - 0.80),              # 8: doji altına sarkma
           (p - 0.80, p - 0.15, p - 1.35, p - 0.30),       # 9: dip
           (p - 0.30, p + 0.55, p - 0.45, p + 0.50)]
    o2 += zincir(o2[-1][3], [(9, 0.62, 0.38, 8612)])
    df2 = df_yap(o2)
    mumla(fig, df2, row=2, col=1)
    doji = 7
    kutu(fig, doji - 0.45, doji + 0.45, df2.l[doji], df2.h[doji], GRI, a=0.18, cizgi=1.2,
         row=2, col=1)
    not_(fig, doji, df2.h[doji] + 0.35, "doji = tek barlık yatay bant", renk=GRI,
         ok=False, boyut=10, row=2, col=1)
    yasak = round(df2.l[doji] - 0.05, 2)
    dogru = round(df2.l[2:6].min() - 0.05, 2)
    yatay(fig, yasak, doji - 1, len(df2) - 1, renk=TURUNCU, dash="dot", w=2.0, row=2, col=1)
    not_(fig, len(df2) - 1, yasak, f"YASAK: dojinin altına sıkılaştırılmış stop {tr(yasak)}",
         renk=TURUNCU, ok=False, boyut=10, xanchor="left", row=2, col=1)
    yatay(fig, dogru, 2, len(df2) - 1, renk=TEAL, dash="dot", w=2.0, row=2, col=1)
    not_(fig, len(df2) - 1, dogru, f"doğru: son salınım dibinin altı {tr(dogru)}",
         renk=TEAL, ok=False, boyut=10, xanchor="left", row=2, col=1)
    not_(fig, 9, df2.l[9] - 0.15, "sıkı stop burada vurulur — sonra trend devam eder",
         renk=TURUNCU, ax=48, ay=42, boyut=10.5, row=2, col=1)
    not_(fig, 1, df2.h.max() - 0.2,
         "Doji, iki tarafın da kazanamadığı bir bardır: yönü değil,<br>"
         "belirsizliği bildirir. Belirsizliğin dibine stop koymak,<br>"
         "trendden atılmanın en yaygın yoludur.",
         renk=MUREKKEP, ok=False, boyut=10.5, xanchor="left", row=2, col=1)
    fig.update_xaxes(range=[-0.8, len(df) + 6], row=1, col=1)
    fig.update_xaxes(range=[-0.8, len(df2) + 8], row=2, col=1)

    duzen(fig, "86 · Stop yerleşimi ve sıkılaştırma merdiveni",
          "kâr hedefi kafada olabilir, stop olamaz", h=1000, sematik=True)
    kaydet(fig, "86_stop_merdiveni", olcum=dict(
        giris=giris, ilk_stop=kademeler[0][0], giris_bari_stop=kademeler[1][0],
        basabas=giris, iz_suren=swing_dip, risk_1R=risk,
        doji_indis=doji, yasak_stop=yasak, dogru_stop=dogru))


# ===================================================================== 87
def f87_olcekli_giris():
    """Ölçekli giriş ve başabaş çıkış mekaniği (Ş, 2 panel)."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16,
                        subplot_titles=("Panel 1 — iki kademeli giriş ve ortalama maliyet",
                                        "Panel 2 — başabaş noktası: 100,00 yerine 99,00"))

    ohlc = zincir(97.5, [(6, 0.75, 0.35, 8701)])            # önceki boğa bacağı
    p = ohlc[-1][3]
    ohlc += [(p, p + 0.15, p - 0.85, p - 0.70), (p - 0.70, p - 0.55, p - 1.60, p - 1.45)]
    ohlc += [(100.55, 100.70, 99.85, 100.00),               # 8: 1. kademe alım barı
             (100.00, 100.20, 99.10, 99.25),
             (99.25, 99.40, 98.35, 98.50),
             (98.50, 98.65, 97.85, 98.00),                  # 11: 2. kademe alım barı
             (98.00, 98.60, 96.95, 98.45),                  # 12: dip · dönüş barı
             (98.45, 99.30, 98.30, 99.20)]
    ohlc += zincir(99.20, [(10, 0.52, 0.38, 8702)])
    df = df_yap(ohlc)
    mumla(fig, df, row=1, col=1)

    E1, E2 = 100.00, 98.00
    ORT = (E1 + E2) / 2
    STOP = 96.50
    yatay(fig, E1, 8 - 0.4, len(df) - 1, renk=MAVI, dash="solid", w=1.6, row=1, col=1)
    not_(fig, len(df) - 1, E1, "1. kademe (yarım) 100,00", renk=MAVI, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    yatay(fig, E2, 11 - 0.4, len(df) - 1, renk=MAVI, dash="solid", w=1.6, row=1, col=1)
    not_(fig, len(df) - 1, E2, "2. kademe (yarım) 98,00", renk=MAVI, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    yatay(fig, ORT, 8 - 0.4, len(df) - 1, renk=MOR, dash="dash", w=2.0, row=1, col=1)
    not_(fig, len(df) - 1, ORT, "ortalama maliyet 99,00", renk=MOR, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    yatay(fig, STOP, 8 - 0.4, len(df) - 1, renk=BORDO, dash="dot", w=1.6, row=1, col=1)
    not_(fig, len(df) - 1, STOP,
         "ortak stop 96,50 (bayrağın altı)<br>toplam risk = 3,50 + 1,50 = 5,00 birim",
         renk=BORDO, ok=False, boyut=10, xanchor="left", row=1, col=1)
    for x, ad, ay in ((8, "1. kademe: yarım boy alım", -34), (11, "2. kademe: yarım boy alım", 40)):
        kutu(fig, x - 0.45, x + 0.45, df.l[x], df.h[x], MAVI, a=0.16, cizgi=1.2, row=1, col=1)
        not_(fig, x, df.h[x] if ay < 0 else df.l[x], ad, renk=MAVI, ax=-30, ay=ay,
             boyut=10, row=1, col=1)
    kutu(fig, 7.5, 12.5, df.l[8:13].min(), df.h[8:13].max(), GRI, a=0.07, cizgi=0.9,
         dash="dot", row=1, col=1)
    not_(fig, 10, df.h[8:13].max() + 0.35, "boğa bayrağı — plan ÖNCEDEN yapıldı",
         renk=GRI, ok=False, boyut=10, row=1, col=1)
    not_(fig, 0.0, 105.8,
         "'Zararda pozisyona ekleme' kuralının doğru okunuşu:<br>"
         "yasak olan, plansız ekleme ve toplam riskin büyümesidir.<br>"
         "Burada iki kademe TEK işlemin parçasıdır; toplam risk baştan bellidir.",
         renk=MUREKKEP, ok=False, boyut=10.5, xanchor="left", row=1, col=1)
    fig.update_xaxes(range=[-0.8, len(df) + 8], row=1, col=1)

    # --- panel 2: kâr/zarar doğruları
    fiyat = np.linspace(96.0, 104.0, 300)
    tek = fiyat - E1
    olcekli = 0.5 * (fiyat - E1) + 0.5 * (fiyat - E2)
    fig.add_trace(go.Scatter(x=fiyat, y=tek, mode="lines",
                             name="tek giriş (1 birim @ 100,00)",
                             line=dict(color=GRI, width=2.2, dash="dash")), row=2, col=1)
    fig.add_trace(go.Scatter(x=fiyat, y=olcekli, mode="lines",
                             name="ölçekli giriş (½ @ 100,00 + ½ @ 98,00)",
                             line=dict(color=MOR, width=2.8)), row=2, col=1)
    yatay(fig, 0, 96, 104, renk=MUREKKEP, dash="solid", w=1.1, row=2, col=1)
    for x, renk, ad, yy in ((E1, GRI, "tek girişin başabaşı 100,00", 4.15),
                            (ORT, MOR, "ölçekli girişin başabaşı 99,00", 3.35)):
        cizgi(fig, x, -4.2, x, 4.6, renk=renk, dash="dot", w=1.5, row=2, col=1)
        not_(fig, x, yy, ad, renk=renk, ok=False, boyut=10.5, row=2, col=1)
    cizgi(fig, STOP, -4.2, STOP, 4.6, renk=BORDO, dash="dot", w=1.5, row=2, col=1)
    not_(fig, STOP, -3.4, "ortak stop 96,50<br>kayıp 2,50 birim", renk=BORDO, ok=False,
         boyut=10.5, xanchor="left", row=2, col=1)
    not_(fig, 103.9, -2.5,
         "Ölçekli giriş başabaş noktasını 1,00 birim aşağı çeker.<br>"
         "Bedeli, her kademenin YARIM boy olmasıdır: aynı stopla toplam risk<br>"
         "2,50 birimde sabit kalır. Boy sabit tutulursa risk iki katına çıkar —<br>"
         "kuralın yasakladığı şey tam olarak budur.",
         renk=MUREKKEP, ok=False, boyut=10.5, xanchor="right", row=2, col=1)

    duzen(fig, "87 · Ölçekli giriş ve başabaş çıkış mekaniği",
          "en az riskli ölçekleme: kademeleri ayrı işlemler gibi planlamak", h=1000,
          sematik=True)
    fig.update_yaxes(title_text="fiyat (şematik birim)", row=1, col=1)
    fig.update_yaxes(title_text="pozisyonun kâr/zararı (birim)", row=2, col=1,
                     range=[-4.2, 4.6])
    fig.update_xaxes(title_text="bar sırası", row=1, col=1)
    fig.update_xaxes(title_text="piyasa fiyatı", row=2, col=1)
    kaydet(fig, "87_olcekli_giris", olcum=dict(
        kademe1=E1, kademe2=E2, ortalama_maliyet=ORT, ortak_stop=STOP,
        risk_kademe1=round(E1 - STOP, 2), risk_kademe2=round(E2 - STOP, 2),
        toplam_risk_yarim_boy=round(0.5 * (E1 - STOP) + 0.5 * (E2 - STOP), 2),
        basabas_tek=E1, basabas_olcekli=ORT))


# ===================================================================== 88
def f88_olcekli_cikis():
    """Ölçekli çıkış merdiveni (Ş, 1 panel)."""
    ohlc = [(99.6, 100.0, 98.9, 99.1), (99.1, 99.4, 98.4, 99.3),
            (99.3, 100.1, 99.1, 99.95),                    # 2: sinyal barı
            (100.0, 101.0, 99.85, 100.85)]
    ohlc += zincir(100.85, [(5, 0.42, 0.32, 8801), (3, -0.22, 0.28, 8802),
                            (6, 0.48, 0.34, 8803), (4, 0.18, 0.30, 8804)])
    df = df_yap(ohlc)
    fig = go.Figure()
    mumla(fig, df, goster=True)

    GIRIS, STOP = 100.00, 98.00
    R = GIRIS - STOP
    kademeler = [(GIRIS + 1 * R, "yarısı (½)", "1R", 6, 0.50),
                 (GIRIS + 2 * R, "çeyreği (¼)", "2R", 12, 0.25),
                 (GIRIS + 2.75 * R, "kalan çeyrek (¼) — iz süren stopla", "2,75R", 20, 0.25)]
    yatay(fig, GIRIS, 2, len(df) + 1.2, renk=MAVI, dash="solid", w=1.7)
    not_(fig, len(df) + 1.4, GIRIS, "giriş 100,00", renk=MAVI, ok=False, boyut=10,
         xanchor="left")
    yatay(fig, STOP, 2, 8, renk=BORDO, dash="dot", w=1.7)
    not_(fig, 2, STOP, "ilk stop 98,00 → risk 2,00 = 1R", renk=BORDO, ok=False, boyut=10,
         xanchor="left", yanchor="top")
    kutu(fig, 1.55, 2.45, df.l[2], df.h[2], ALTIN, a=0.20, cizgi=1.3)
    not_(fig, 2, df.l[2] - 0.20, "sinyal barı", renk=ALTIN, ok=False, boyut=10, yanchor="top")

    for y, ad, r, x, pay in kademeler:
        yatay(fig, y, 2, len(df) + 1.2, renk=MOR, dash="dash", w=1.6)
        not_(fig, len(df) + 1.4, y, f"ÇIKIŞ · {ad} · {tr(y)} ({r})", renk=MOR, ok=False,
             boyut=10, xanchor="left")
        fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers", showlegend=False,
                                 marker=dict(size=11, symbol="triangle-down", color=MOR,
                                             line=dict(color=KAGIT, width=1.2))))
    # çıkış sonrası stop konumları
    stoplar = [(GIRIS, 8, 14, "① yarı çıkıştan sonra: stop başabaşa (100,00)"),
               (GIRIS + 1 * R, 14, 20, "② ikinci çıkıştan sonra: stop 1R'ye (102,00)"),
               (GIRIS + 2 * R, 20, len(df) - 1, "③ kalan çeyrek: iz süren stop (104,00)")]
    for y, x0, x1, ad in stoplar:
        yatay(fig, y, x0, x1, renk=TEAL, dash="dot", w=2.4)
        not_(fig, x0 + 0.2, y, ad, renk=TEAL, ok=False, boyut=10, xanchor="left",
             yanchor="bottom")
    # kalan pozisyon merdiveni
    kalan = [(2, 1.00, "tam pozisyon"), (6, 0.50, "yarım kaldı"),
             (12, 0.25, "çeyrek kaldı"), (20, 0.00, "pozisyon kapandı")]
    for x, pay, ad in kalan:
        not_(fig, x, 97.30, f"{ad}<br>({pay:.0%})", renk=GRI, ok=False, boyut=9.5)
        cizgi(fig, x, 97.75, x, 98.6 if pay else 98.6, renk=rgba(GRI, 0.5), dash="dot",
              w=1.0)
    not_(fig, 10, 96.35,
         "Kâr al emrinin DOLMAMASI da bir bilgidir: hedefe bir tick kala dönen piyasa "
         "(17 tick başarısızlığı)<br>zayıflık bildirir — hedefi bir tick içeri çekmek, "
         "işlemin beklenen değerinin işaretini değiştirebilir.",
         renk=TURUNCU, ok=False, boyut=10.5)

    harman = sum(pay * float(r.replace(",", ".").replace("R", ""))
                 for _, _, r, _, pay in kademeler)
    not_(fig, 1, 107.0,
         f"harmanlanmış sonuç = ½×1R + ¼×2R + ¼×2,75R = <b>{tr(harman, 3)}R</b><br>"
         "ölçekli çıkışın işi ödülü büyütmek değil, ödülün VARYANSINI küçültmek;<br>"
         "ilk çıkış aynı zamanda stopu başabaşa çekmenin bedelini finanse eder.",
         renk=MUREKKEP, ok=False, boyut=10.5, xanchor="left")
    fig.update_xaxes(range=[-0.8, len(df) + 12])
    fig.update_yaxes(range=[95.9, 108.0])
    duzen(fig, "88 · Ölçekli çıkış merdiveni",
          "güçten çık, zayıflıkta yeniden gir · her çıkış bir stop hamlesini tetikler",
          h=680, sematik=True)
    kaydet(fig, "88_olcekli_cikis", olcum=dict(
        giris=GIRIS, ilk_stop=STOP, R=R,
        cikis_1=dict(fiyat=GIRIS + R, pay=0.50, R=1.0),
        cikis_2=dict(fiyat=GIRIS + 2 * R, pay=0.25, R=2.0),
        cikis_3=dict(fiyat=GIRIS + 2.75 * R, pay=0.25, R=2.75),
        harmanlanmis_R=round(harman, 3)))


# ===================================================================== 89
def f89_always_in_donusu():
    """Always-in dönüşünün tamamlanma anı (G · XU030 5dk, 2 panel)."""
    ham = yukle("XU030.IS", "5m")
    if ham is None:
        print("  ! 89 atlandı: XU030.IS 5m önbelleği yok")
        return
    BAS, ADET = 1297, 60                       # 18 Haziran 2026 seansı, indisle pinli
    df = dilim(ham, BAS, ADET)

    # ders kuralı (mekanik always-in vekili): iki ardışık trend barı + önceki
    # salınımın ötesinde kapanış. Kural burada AÇIKÇA yazılır; Brooks bunu yargıyla
    # okur, biz figürde çivilenmiş bir tanım kullanıyoruz.
    r = (df.h - df.l).replace(0, np.nan)
    govde = df.c - df.o
    bogabar = (govde > 0) & (govde.abs() / r >= 0.55) & ((df.h - df.c) / r <= 0.30)
    ayibar = (govde < 0) & (govde.abs() / r >= 0.55) & ((df.c - df.l) / r <= 0.30)
    durum, cur = [0] * len(df), 1              # pencere boğa always-in ile açılıyor
    flipler = []
    for i in range(2, len(df)):
        hi = df.h[max(0, i - 7):i - 1].max()
        lo = df.l[max(0, i - 7):i - 1].min()
        if bogabar[i] and bogabar[i - 1] and df.c[i] > hi and cur != 1:
            cur = 1
            flipler.append((i, 1, hi))
        elif ayibar[i] and ayibar[i - 1] and df.c[i] < lo and cur != -1:
            cur = -1
            flipler.append((i, -1, lo))
        durum[i] = cur
    for i in range(2):
        durum[i] = durum[2]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        row_heights=[0.76, 0.24],
                        subplot_titles=("Panel 1 — iki ardışık trend barı ve takip barı",
                                        "Panel 2 — aynı anda always-in yön etiketinin değişimi"))
    fig.add_trace(mumlar(df, hover=hover(df, "%d %b %H:%M")), row=1, col=1)
    ema_ciz(fig, df, 20, renk=GRI, row=1, col=1)

    olcum_flip = []
    for i, yon, seviye in flipler:
        renk = TEAL if yon == 1 else BORDO
        ad = "boğa" if yon == 1 else "ayı"
        for k, et in ((i - 1, "1. trend barı"), (i, "2. trend barı")):
            kutu(fig, k - 0.45, k + 0.45, df.l[k], df.h[k], renk, a=0.22, cizgi=1.3,
                 row=1, col=1)
            not_(fig, k, (df.h[k] if yon == 1 else df.l[k]),
                 et, renk=renk, ok=False, boyut=9.5,
                 yanchor="bottom" if yon == 1 else "top", row=1, col=1)
        if i + 1 < len(df):
            kutu(fig, i + 0.55, i + 1.45, df.l[i + 1], df.h[i + 1], ALTIN, a=0.20,
                 cizgi=1.2, row=1, col=1)
            not_(fig, i + 1, (df.h[i + 1] if yon == 1 else df.l[i + 1]),
                 "takip barı", renk=ALTIN, ok=False, boyut=9.5,
                 yanchor="bottom" if yon == 1 else "top", row=1, col=1)
        yatay(fig, seviye, max(0, i - 9), len(df) - 1, renk=renk, dash="dash", w=1.3,
              row=1, col=1)
        not_(fig, max(0, i - 9), seviye,
             f"aşılan salınım {'tepesi' if yon == 1 else 'dibi'} {tr(seviye)}",
             renk=renk, ok=False, boyut=9.5, xanchor="left",
             yanchor="bottom" if yon == 1 else "top", row=1, col=1)
        cizgi(fig, i, df.l.min(), i, df.h.max(), renk=rgba(renk, 0.55), dash="dot", w=1.6,
              row=1, col=1)
        not_(fig, i, df.h.max(),
             f"always-in {ad}ya döndü<br>{df.ts[i]:%H:%M} · kapanış {tr(df.c[i])}",
             renk=renk, ax=0, ay=-34, boyut=10, row=1, col=1)
        olcum_flip.append(dict(pencere_indis=i, onbellek_indis=BAS + i,
                               saat=df.ts[i].strftime("%Y-%m-%d %H:%M"),
                               yon="boğa" if yon == 1 else "ayı",
                               asilan_seviye=round(float(seviye), 2),
                               kapanis=round(float(df.c[i]), 2)))

    # --- panel 2: yön şeridi
    for i in range(len(df)):
        renk = TEAL if durum[i] == 1 else BORDO
        kutu(fig, i - 0.5, i + 0.5, 0.15, 0.85, renk, a=0.80, cizgi=0.0, row=2, col=1)
    kesim = [0] + [f[0] for f in flipler] + [len(df)]
    for a, b in zip(kesim[:-1], kesim[1:]):
        if b - a < 4:
            continue
        yon = durum[(a + b) // 2]
        not_(fig, (a + b) / 2, 0.5,
             f"always-in {'LONG' if yon == 1 else 'SHORT'} · {b - a} bar",
             renk=KAGIT, ok=False, boyut=10.5, row=2, col=1, arka=False)
    not_(fig, len(df) - 1, 1.35,
         "Always-in 5 dakikalıkta gün içinde defalarca değişir; baskın trend değişmez.",
         renk=MUREKKEP, ok=False, boyut=10.5, xanchor="right", row=2, col=1)

    zaman_ekseni(fig, df, adet=10, fmt="%H:%M", row=2, col=1)
    duzen(fig, "89 · Always-in dönüşünün tamamlanma anı",
          f"XU030 · 5 dakikalık · {gun_tr(df.ts[0])} seansı · önbellek indisi "
          f"{BAS}–{BAS + ADET - 1} · dönüş kuralı: iki ardışık trend barı + önceki "
          "salınımın ötesinde kapanış + takip barı", h=880)
    fig.update_yaxes(title_text="XU030", row=1, col=1)
    fig.update_yaxes(title_text="", showticklabels=False, showgrid=False, range=[0, 1.6],
                     row=2, col=1)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="seans saati (UTC)", row=2, col=1)
    kaydet(fig, "89_always_in_donusu", olcum=dict(
        enstruman="XU030.IS 5dk", onbellek_indis=[BAS, BAS + ADET - 1],
        seans=str(df.ts[0].date()), bar_sayisi=int(len(df)), flipler=olcum_flip,
        pencere_yuksek=round(float(df.h.max()), 2), pencere_dusuk=round(float(df.l.min()), 2)))


# ===================================================================== 90
def f90_gun_tipleri():
    """Gün tipleri kartelası (Ş, 1 panel)."""
    N, ARA = 14, 5

    def spike_kanal():
        y = [(0.0, 4.3, -0.3, 4.1), (4.1, 8.5, 4.0, 8.3), (8.3, 12.4, 8.2, 12.1)]
        return y + zincir(12.1, [(11, 0.42, 0.40, 9007)])

    gunler = [
        ("açılıştan trend",
         "gün ucu açılışa yakın<br>geri çekilmeler 1–2 bar<br>köşeden köşeye",
         zincir(0.0, [(N, 1.00, 0.20, 9001)]), []),
        ("küçük geri çekilmeli trend",
         "her geri çekilme tek bar<br>en güçlü trend türü<br>yalnızca trend yönünde",
         zincir(0.0, [(3, 1.30, 0.16, 9002), (1, -0.55, 0.12, 9003),
                      (3, 1.30, 0.16, 9004), (1, -0.50, 0.12, 9005),
                      (4, 1.30, 0.16, 9006), (2, 0.70, 0.16, 9021)]),
         [("gc", 3), ("gc", 7)]),
        ("spike ve kanal",
         "sert spike, sonra kanal<br>kanalın eğimi azalır<br>dönüş hedefi kanalın başı",
         spike_kanal(), [("spike", (0, 2)), ("kanal", (3, 13))]),
        ("trend devam günü",
         "sabah bacağı<br>orta dilimde düzeltme<br>öğleden sonra devam",
         zincir(0.0, [(4, 1.35, 0.18, 9008), (3, -0.95, 0.28, 9009),
                      (7, 1.15, 0.20, 9010)]),
         [("duz", (4, 6))]),
        ("yatay bant günü",
         "iki uç arasında salınım<br>kırılımların %80'i başarısız<br>hedef bandın ORTASI",
         zincir(0.0, [(4, 0.65, 0.30, 9011), (4, -0.70, 0.30, 9012),
                      (3, 0.72, 0.30, 9013), (3, -0.62, 0.30, 9014)]),
         [("bant", (0, 13))]),
        ("trend eden yatay bant",
         "ardışık bantlar bir yöne kayar<br>her bant öncekinin üstünde<br>trend ile bandın karışımı",
         zincir(0.0, [(4, 0.05, 0.40, 9015), (2, 1.70, 0.15, 9016),
                      (4, 0.05, 0.40, 9017), (2, 1.70, 0.15, 9018),
                      (2, 0.05, 0.35, 9019)]),
         [("bant", (0, 3)), ("bant", (6, 9)), ("bant", (12, 13))]),
    ]

    fig = go.Figure()
    x0 = 0
    olcumler = {}
    for ad, tani, yol, isaretler in gunler:
        y = olcekle(yol[:N], 0, 100)
        d = mum_grubu(fig, y, x0)
        kutu(fig, x0 - 0.8, x0 + N - 0.2, -6, 106, GRI, a=0.045, cizgi=0.8, dash="dot")
        not_(fig, x0 + (N - 1) / 2, 114, f"<b>{ad}</b>", renk=MUREKKEP, ok=False, boyut=12)
        not_(fig, x0 + (N - 1) / 2, -17, tani, renk=GRI, ok=False, boyut=9)
        for tip, yer in isaretler:
            if tip == "gc":                                   # tek barlık geri çekilme
                not_(fig, x0 + yer, float(d.l[yer]) - 2.5, "geri çekilme", renk=TURUNCU,
                     ok=False, boyut=8.5, yanchor="top")
                kutu(fig, x0 + yer - 0.45, x0 + yer + 0.45, float(d.l[yer]),
                     float(d.h[yer]), TURUNCU, a=0.20, cizgi=1.0)
            else:
                a0, b0 = yer
                alt = float(d.l[a0:b0 + 1].min())
                ust = float(d.h[a0:b0 + 1].max())
                renk = {"spike": ALTIN, "kanal": TEAL, "bant": GRI, "duz": TURUNCU}[tip]
                etiket = {"spike": "spike", "kanal": "kanal", "bant": "bant",
                          "duz": "düzeltme"}[tip]
                kutu(fig, x0 + a0 - 0.5, x0 + b0 + 0.5, alt, ust, renk, a=0.14, cizgi=1.0,
                     dash="dot")
                if b0 - a0 >= 4:                       # geniş kutu: etiket içeride
                    not_(fig, x0 + (a0 + b0) / 2, (alt + ust) / 2, etiket, renk=renk,
                         ok=False, boyut=9, arka=False)
                else:                                  # dar kutu: etiket altta
                    not_(fig, x0 + (a0 + b0) / 2, alt - 2.5, etiket, renk=renk,
                         ok=False, boyut=9, yanchor="top")
        fig.add_trace(go.Scatter(x=[x0], y=[d.o[0]], mode="markers", showlegend=False,
                                 marker=dict(size=8, symbol="circle", color=MAVI,
                                             line=dict(color=KAGIT, width=1.2))))
        fig.add_trace(go.Scatter(x=[x0 + N - 1], y=[d.c[N - 1]], mode="markers",
                                 showlegend=False,
                                 marker=dict(size=8, symbol="square", color=MOR,
                                             line=dict(color=KAGIT, width=1.2))))
        olcumler[ad] = dict(acilis=round(float(d.o[0]), 1),
                            kapanis=round(float(d.c[N - 1]), 1),
                            gun_ucu_konumu=round(float(d.c[N - 1]), 1), bar=N)
        x0 += N + ARA
    lejant(fig, "gün açılışı", MAVI, sekil="circle", a=0.9)
    lejant(fig, "gün kapanışı", MOR, sekil="square", a=0.9)
    not_(fig, (x0 - ARA - 1) / 2, -33,
         "<b>Köşe testi:</b> gün ucu bir köşeye yakınsa trend günü, ortadaysa bant günüdür. "
         "Gün tipini tanıdığın an pozisyon al —<br>teşhis gecikirse günün yarısı biter. "
         "Bir gün tipten tipe geçebilir: her 10–20 barda bir 'hangi rejimdeyim?' diye sor.",
         renk=MUREKKEP, ok=False, boyut=10.5)
    fig.update_yaxes(range=[-40, 122], showticklabels=False)
    fig.update_xaxes(range=[-2, x0 - ARA + 1], showticklabels=False)
    duzen(fig, "90 · Gün tipleri kartelası",
          "altı siluet · hepsi aynı dikey ölçeğe normalize edilmiştir",
          y_baslik="gün aralığı (normalize, şematik)", x_baslik="seans içi bar sırası",
          h=760, sematik=True)
    fig.update_yaxes(title_text="gün aralığı (normalize, şematik)")
    kaydet(fig, "90_gun_tipleri", olcum=dict(bar_sayisi=N, gunler=olcumler))


# ===================================================================== 91
def f91_acilis_araligi():
    """Açılış aralığı boyutu → gün tipi olasılığı (Ş, 2 panel)."""
    def gun(ilk6, kalan):
        return [tuple(b) for b in ilk6 + kalan]

    dar = gun(
        [(52, 56, 50, 54), (54, 57, 51, 52), (52, 55, 48, 53), (53, 58, 52, 56),
         (56, 57, 52, 53), (53, 56, 51, 55)],
        [(55, 62, 54, 61), (61, 68, 60, 67), (67, 71, 64, 70), (70, 78, 69, 77),
         (77, 82, 74, 80), (80, 88, 79, 86), (86, 90, 83, 88), (88, 95, 87, 94),
         (94, 97, 91, 95), (95, 100, 94, 99), (99, 100, 96, 98), (98, 99, 95, 97)])
    orta = gun(
        [(52, 62, 50, 60), (60, 68, 57, 63), (63, 66, 52, 55), (55, 60, 45, 47),
         (47, 58, 45, 56), (56, 68, 54, 66)],
        [(66, 74, 64, 72), (72, 80, 70, 78), (78, 86, 76, 84), (84, 92, 82, 90),
         (90, 100, 88, 95), (95, 96, 84, 86), (86, 88, 76, 78), (78, 80, 68, 70),
         (70, 74, 60, 62), (62, 68, 52, 54), (54, 58, 44, 46), (46, 52, 40, 50)])
    genis = gun(
        [(55, 78, 53, 76), (76, 90, 74, 88), (88, 90, 66, 68), (68, 72, 48, 50),
         (50, 58, 44, 56), (56, 74, 54, 72)],
        [(72, 82, 68, 78), (78, 86, 70, 72), (72, 76, 58, 60), (60, 70, 54, 68),
         (68, 80, 64, 76), (76, 84, 70, 72), (72, 74, 44, 46), (46, 58, 30, 56),
         (56, 70, 54, 66), (66, 76, 62, 64), (64, 70, 52, 58), (58, 72, 54, 68)])

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.17,
                        subplot_titles=("Panel 1 — üç açılış aralığı boyutu sınıfı (ilk 6 bar taralı)",
                                        "Panel 2 — her sınıfın gün tipi olasılık dağılımı"))
    N = 18
    ARA = 4
    x0 = 0
    ozet = {}
    for ad, yol in (("DAR açılış aralığı", dar), ("ORTA açılış aralığı", orta),
                    ("GENİŞ açılış aralığı", genis)):
        d = mum_grubu(fig, yol, x0, row=1, col=1)
        oru, orl = float(d.h[:6].max()), float(d.l[:6].min())
        gun_u, gun_l = float(d.h.max()), float(d.l.min())
        oran = (oru - orl) / (gun_u - gun_l) * 100
        kutu(fig, x0 - 0.6, x0 + 5.5, orl, oru, ALTIN, a=0.20, cizgi=1.3, row=1, col=1)
        kutu(fig, x0 - 0.8, x0 + N - 0.2, gun_l, gun_u, GRI, a=0.04, cizgi=0.8, dash="dot",
             row=1, col=1)
        not_(fig, x0 + (N - 1) / 2, 126, f"<b>{ad}</b>", renk=MUREKKEP, ok=False, boyut=12,
             row=1, col=1)
        not_(fig, x0 + (N - 1) / 2, 117,
             f"açılış aralığı = günlük aralığın %{oran:.0f}'i", renk=ALTIN, ok=False,
             boyut=10, row=1, col=1)
        not_(fig, x0 + 2.5, orl - 3, "ilk 6 bar", renk=ALTIN, ok=False, boyut=9.5,
             yanchor="top", row=1, col=1)
        ozet[ad] = dict(acilis_araligi=round(oru - orl, 1),
                        gunluk_aralik=round(gun_u - gun_l, 1), oran_yuzde=round(oran, 1))
        x0 += N + ARA
    fig.update_yaxes(range=[18, 132], showticklabels=False, row=1, col=1)
    fig.update_xaxes(range=[-2, x0 - ARA + 1], showticklabels=False, row=1, col=1)

    # --- panel 2
    siniflar = ["DAR<br>(günlük aralığın ≲%30'u)", "ORTA<br>(%30–%60)", "GENİŞ<br>(≳%60)"]
    dagilim = {"trend günü": [60, 40, 25], "yatay bant günü": [25, 40, 50],
               "dönüş günü": [15, 20, 25]}
    renkler = {"trend günü": TEAL, "yatay bant günü": GRI, "dönüş günü": TURUNCU}
    for ad, deger in dagilim.items():
        fig.add_trace(go.Bar(x=siniflar, y=deger, name=ad,
                             marker_color=rgba(renkler[ad], 0.72),
                             marker_line=dict(color=renkler[ad], width=1.3),
                             text=[f"%{v}" for v in deger], textposition="inside",
                             insidetextfont=dict(color=KAGIT, size=11)), row=2, col=1)
    not_(fig, 0, 114,
         "Dar açılış aralığı = kırılım modu: küçük aralıktan çıkan hareket<br>"
         "günün tamamını taşıyabilir; açılıştan trend günü buradan gelir.",
         renk=TEAL, ok=False, boyut=10.5, row=2, col=1)
    not_(fig, 2, 114,
         "Geniş açılış aralığı zaten günün büyük kısmını harcamıştır:<br>"
         "kalan saatlerde bant davranışı ve dönüşler baskındır.",
         renk=GRI, ok=False, boyut=10.5, row=2, col=1)
    fig.update_layout(barmode="stack", bargap=0.42)

    duzen(fig, "91 · Açılış aralığı boyutu → gün tipi olasılığı",
          "açılış aralığı = günün ilk iyi salınımına kadarki dönem · " + ESIK,
          h=1020, sematik=True)
    fig.update_yaxes(title_text="gün aralığı (normalize)", row=1, col=1)
    fig.update_yaxes(title_text="gün tipi olasılığı (%)", range=[0, 132], row=2, col=1)
    fig.update_xaxes(title_text="seans içi bar sırası", row=1, col=1)
    fig.update_xaxes(title_text="açılış aralığı sınıfı", row=2, col=1)
    kaydet(fig, "91_acilis_araligi", olcum=dict(siniflar=ozet, dagilim=dagilim,
                                                bar_sayisi=N))


# ===================================================================== 92
def f92_seans_haritasi():
    """Günün üç dilimi ve dönüm saatleri (Ş, 1 panel)."""
    SEANS = 390          # dakika · 6,5 saatlik seans varsayımı (oranlar korunur)
    fig = go.Figure()

    # üstte şematik bir gün: zaman bantlarının fiyat karşılığı görünsün
    yol = zincir(0.0, [(4, 1.60, 0.55, 9201),      # açılış aralığı / kırılım modu
                       (6, -1.10, 0.60, 9202),     # açılış dönüşü
                       (14, 1.05, 0.45, 9203),     # sabah bacağı
                       (22, 0.05, 0.55, 9204),     # orta dilim bandı
                       (12, -0.55, 0.60, 9205),    # geç stop-run
                       (20, 0.75, 0.45, 9206)])    # kapanışa trend
    gun = pd.DataFrame(olcekle(yol[:78], 4.65, 6.45), columns=["o", "h", "l", "c"])
    m = mumlar(gun, ad="şematik gün", x=[i * 5 + 2.5 for i in range(len(gun))],
               hover=bar_okuma(gun))
    m.showlegend = False
    fig.add_trace(m)
    not_(fig, 2, 6.62, "şematik bir günün fiyat karşılığı (5 dakikalık barlar)",
         renk=GRI, ok=False, boyut=10, xanchor="left")

    dilimler = [(0, SEANS / 3, "AÇILIŞ DİLİMİ", TEAL,
                 "kırılım modu · en yüksek oynaklık · günün en iyi kurulumları"),
                (SEANS / 3, 2 * SEANS / 3, "ORTA DİLİM", GRI,
                 "kurumsal bant scalping'i · en düşük olasılıklı saatler"),
                (2 * SEANS / 3, SEANS, "KAPANIŞ DİLİMİ", MOR,
                 "geç tuzaklar · trendin yeniden başlaması · kapanışa trend")]
    for x0, x1, ad, renk, alt in dilimler:
        kutu(fig, x0, x1, 3.15, 3.95, renk, a=0.20, cizgi=1.2)
        not_(fig, (x0 + x1) / 2, 3.72, f"<b>{ad}</b>", renk=renk, ok=False, boyut=12,
             arka=False)
        not_(fig, (x0 + x1) / 2, 3.36, alt, renk=MUREKKEP, ok=False, boyut=9.5, arka=False)

    seritler = [
        (0, 25, 2.55, 2.98, ALTIN, "kırılım modu"),
        (25, 90, 2.55, 2.98, TURUNCU, "açılış dönüşü penceresi"),
        (90, 150, 2.55, 2.98, TEAL, "sabah bacağı / ilk kanal"),
        (150, 260, 2.02, 2.45, GRI, "kurumsal bant scalping'i"),
        (260, 330, 2.02, 2.45, TURUNCU, "geç stop-run penceresi"),
        (330, SEANS, 2.02, 2.45, MOR, "kapanışa trend"),
    ]
    for x0, x1, y0, y1, renk, ad in seritler:
        kutu(fig, x0, x1, y0, y1, renk, a=0.18, cizgi=1.1)
        not_(fig, (x0 + x1) / 2, (y0 + y1) / 2, ad, renk=MUREKKEP, ok=False, boyut=9.5,
             arka=False)

    donum = [
        (15, "+15 dk", "15 dakikalık barın kapanışı:<br>günün ilk yön kararı", 1.62, 78, 44),
        (60, "+1 sa", "ilk saatin sonu — 'ilk saatin<br>stop'u günün stop'udur'", 1.62, 12, 104),
        (120, "+2 sa", "sabah trendinin olgunlaşması;<br>iki bacaklı düzeltme adayı", 1.62, 6, 44),
        (240, "+4 sa", "orta dilimin sonu; trend devam<br>günü buradan başlar", 1.62, 6, 104),
        (300, "+5 sa", "geç stop-run: zayıf elleri<br>çıkaran karşı spike", 1.62, 6, 44),
        (360, "+6 sa", "son yarım saat: kapatma akışı;<br>kapanış üst zaman dilimini yansıtır",
         1.62, -52, 104),
    ]
    for x, kisa, ad, y, ax, ay in donum:
        cizgi(fig, x, 0.05, x, 3.95, renk=BORDO, dash="dot", w=1.3)
        fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers", showlegend=False,
                                 marker=dict(size=10, symbol="diamond", color=BORDO,
                                             line=dict(color=KAGIT, width=1.2))))
        not_(fig, x, y, f"<b>{kisa}</b><br>{ad}", renk=BORDO, ax=ax, ay=ay, boyut=9.5)

    not_(fig, SEANS / 2, -0.42,
         "Bütün saatler SEANS AÇILIŞINDAN İTİBAREN GEÇEN SÜRE olarak okunur; "
         "6,5 saatlik bir seans varsayılmıştır.<br>"
         "Farklı uzunluktaki seanslarda (BIST, VİOP) dilim oranları korunur, "
         "saat etiketleri ölçeklenir.",
         renk=MUREKKEP, ok=False, boyut=10.5)

    fig.update_xaxes(range=[-14, SEANS + 14],
                     tickvals=[0, 60, 120, 180, 240, 300, 390],
                     ticktext=["açılış", "+1 sa", "+2 sa", "+3 sa", "+4 sa", "+5 sa",
                               "kapanış"])
    fig.update_yaxes(range=[-0.75, 6.85], showticklabels=False, showgrid=False,
                     title_text="")
    duzen(fig, "92 · Günün üç dilimi ve dönüm saatleri",
          "zamanın kendisi bir değişkendir · " + ESIK,
          y_baslik="", x_baslik="seans açılışından itibaren geçen süre", h=820,
          sematik=True)
    fig.update_yaxes(title_text="")
    kaydet(fig, "92_seans_haritasi", olcum=dict(
        seans_dakika=SEANS,
        dilimler={ad: [round(x0), round(x1)] for x0, x1, ad, _, _ in dilimler},
        seritler={ad: [x0, x1] for x0, x1, _, _, _, ad in seritler},
        donum_saatleri={k: x for x, k, _, _, _, _ in donum}))


# ===================================================================== 93
def f93_ucleme():
    """Aynı yapının aylık–günlük–5dk üçlemesi (G · XU030, 3 panel)."""
    saatlik = yukle("XU030.IS", "1h")
    besdk = yukle("XU030.IS", "5m")
    if saatlik is None or besdk is None:
        print("  ! 93 atlandı: XU030.IS önbelleği eksik")
        return
    s = saatlik.set_index("ts")
    aylik = (s.resample("MS").agg({"o": "first", "h": "max", "l": "min", "c": "last"})
             .dropna().reset_index())
    gunluk = (s.resample("1D").agg({"o": "first", "h": "max", "l": "min", "c": "last"})
              .dropna().reset_index())
    gunluk = gunluk[(gunluk.ts >= "2026-06-08") & (gunluk.ts <= "2026-07-10")].reset_index(drop=True)
    gun5 = seans(besdk, "2026-06-15")

    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.085,
                        subplot_titles=(
                            "Panel 1 — XU030 aylık (saatlik önbellekten toplanmış, 35 ay)",
                            "Panel 2 — XU030 günlük · 8 Haziran – 10 Temmuz 2026",
                            "Panel 3 — XU030 5 dakikalık · 15 Haziran 2026 seansı"))

    # ---------------- panel 1: aylık
    fig.add_trace(mumlar(aylik, hover=hover(aylik, "%b %Y")), row=1, col=1)
    ay_i = {str(t.date())[:7]: i for i, t in enumerate(aylik.ts)}
    sp, k0, k1 = ay_i["2026-01"], ay_i["2026-02"], ay_i["2026-06"]
    d0 = d1 = ay_i["2026-07"]
    kutu(fig, sp - 0.5, sp + 0.5, aylik.l[sp], aylik.h[sp], ALTIN, a=0.22, cizgi=1.4,
         row=1, col=1)
    not_(fig, sp, aylik.h[sp], f"SPIKE · Oca 2026<br>{aylik.o[sp]:.0f} → {aylik.c[sp]:.0f}",
         renk=ALTIN, ax=-40, ay=-38, boyut=10, row=1, col=1)
    kutu(fig, k0 - 0.5, k1 + 0.5, aylik.l[k0:k1 + 1].min(), aylik.h[k0:k1 + 1].max(),
         TEAL, a=0.10, cizgi=1.1, dash="dot", row=1, col=1)
    not_(fig, (k0 + k1) / 2, float(aylik.h[k0:k1 + 1].max()), "KANAL · Şub–Haz 2026",
         renk=TEAL, ok=False, boyut=10.5, yanchor="bottom", row=1, col=1)
    kutu(fig, d0 - 0.5, d1 + 0.5, aylik.l[d0:d1 + 1].min(), aylik.h[d0:d1 + 1].max(),
         TURUNCU, a=0.13, cizgi=1.1, row=1, col=1)
    not_(fig, d0, aylik.l[d0], f"DÜZELTME · Tem 2026 · dip {aylik.l[d0]:.0f}",
         renk=TURUNCU, ax=-62, ay=52, boyut=10, row=1, col=1)
    zaman_ekseni_tr(fig, aylik, adet=11, fmt="%b %y", row=1, col=1)
    kutu(fig, ay_i["2026-06"] - 0.5, ay_i["2026-07"] + 0.5,
         float(aylik.l[ay_i["2026-06"]:ay_i["2026-07"] + 1].min()),
         float(aylik.h[ay_i["2026-06"]:ay_i["2026-07"] + 1].max()),
         MOR, a=0.10, cizgi=1.4, dash="dash", row=1, col=1)
    not_(fig, ay_i["2026-06"] + 0.5, float(aylik.l[ay_i["2026-06"]:ay_i["2026-07"] + 1].min()),
         "Haz–Tem 2026 = panel 2", renk=MOR, ax=-64, ay=104, boyut=10, row=1, col=1)

    # ---------------- panel 2: günlük
    fig.add_trace(mumlar(gunluk, hover=hover(gunluk, "%d %b %Y")), row=2, col=1)
    g_i = {str(t.date()): i for i, t in enumerate(gunluk.ts)}
    gs, gk0, gk1, gd0, gd1 = (g_i["2026-06-15"], g_i["2026-06-16"], g_i["2026-06-19"],
                              g_i["2026-06-22"], g_i["2026-07-10"])
    kutu(fig, gs - 0.5, gs + 0.5, gunluk.l[gs], gunluk.h[gs], ALTIN, a=0.22, cizgi=1.4,
         row=2, col=1)
    not_(fig, gs, gunluk.h[gs], f"SPIKE · 15 Haz<br>{gunluk.o[gs]:.0f} → {gunluk.c[gs]:.0f}",
         renk=ALTIN, ax=-42, ay=-34, boyut=10, row=2, col=1)
    kutu(fig, gk0 - 0.5, gk1 + 0.5, gunluk.l[gk0:gk1 + 1].min(), gunluk.h[gk0:gk1 + 1].max(),
         TEAL, a=0.10, cizgi=1.1, dash="dot", row=2, col=1)
    not_(fig, (gk0 + gk1) / 2, gunluk.h[gk0:gk1 + 1].max(), "KANAL · 16–19 Haz", renk=TEAL,
         ok=False, boyut=10.5, yanchor="bottom", row=2, col=1)
    kutu(fig, gd0 - 0.5, gd1 + 0.5, gunluk.l[gd0:gd1 + 1].min(), gunluk.h[gd0:gd1 + 1].max(),
         TURUNCU, a=0.13, cizgi=1.1, row=2, col=1)
    not_(fig, (gd0 + gd1) / 2, gunluk.l[gd0:gd1 + 1].min(),
         f"DÜZELTME · 22 Haz – 10 Tem · dip {gunluk.l[gd0:gd1 + 1].min():.0f}",
         renk=TURUNCU, ok=False, boyut=10, yanchor="top", row=2, col=1)
    not_(fig, gs, gunluk.l[gs], "bu tek bar = panel 3'ün tamamı", renk=MOR, ax=0, ay=44,
         boyut=10, row=2, col=1)
    zaman_ekseni_tr(fig, gunluk, adet=10, fmt="%d %b", row=2, col=1)

    # ---------------- panel 3: 5 dakikalık
    fig.add_trace(mumlar(gun5, hover=hover(gun5, "%H:%M")), row=3, col=1)
    ema_ciz(fig, gun5, 20, renk=GRI, row=3, col=1)
    kutu(fig, -0.5, 0.5, gun5.l[0], gun5.h[0], ALTIN, a=0.22, cizgi=1.4, row=3, col=1)
    not_(fig, 0, gun5.h[0], f"AÇILIŞ SPIKE'I<br>{gun5.o[0]:.0f} → {gun5.c[0]:.0f}",
         renk=ALTIN, ax=44, ay=-30, boyut=10, row=3, col=1)
    kutu(fig, 29.5, 59.5, gun5.l[30:60].min(), gun5.h[30:60].max(), TEAL, a=0.10,
         cizgi=1.1, dash="dot", row=3, col=1)
    not_(fig, 44, gun5.h[30:60].max(), "KANAL · 09:25–11:55", renk=TEAL, ok=False,
         boyut=10.5, yanchor="bottom", row=3, col=1)
    kutu(fig, 59.5, 73.5, gun5.l[60:74].min(), gun5.h[60:74].max(), TURUNCU, a=0.13,
         cizgi=1.1, row=3, col=1)
    not_(fig, 66, gun5.l[60:74].min(), "DÜZELTME · 12:00–13:00", renk=TURUNCU, ok=False,
         boyut=10, yanchor="top", row=3, col=1)
    trend_cizgisi(fig, gun5, (29, 52), yon="bull", kanal=True, renk=GRI, uzat=62,
                  row=3, col=1)
    zaman_ekseni(fig, gun5, adet=10, fmt="%H:%M", row=3, col=1)
    not_(fig, 90, gun5.l.min(),
         "Fiyat hareketi ölçek değiştirmez: aynı spike → kanal → düzeltme<br>"
         "döngüsü ayda, günde ve beş dakikada aynı geometriyle tekrarlar.",
         renk=MUREKKEP, ok=False, boyut=10.5, xanchor="right", yanchor="bottom",
         row=3, col=1)

    duzen(fig, "93 · Aynı yapının aylık–günlük–5 dakikalık üçlemesi",
          "XU030 · aylık ve günlük seriler saatlik önbellekten toplanmıştır · "
          "pencereler tarihle pinlidir", h=1360)
    for i, ad in enumerate(("XU030 (aylık)", "XU030 (günlük)", "XU030 (5 dakikalık)"), 1):
        fig.update_yaxes(title_text=ad, row=i, col=1)
    ay_alt, ay_ust = float(aylik.l.min()), float(aylik.h.max())
    fig.update_yaxes(range=[ay_alt - (ay_ust - ay_alt) * 0.06,
                            ay_ust + (ay_ust - ay_alt) * 0.14], row=1, col=1)
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    fig.update_xaxes(title_text="seans saati (UTC)", row=3, col=1)
    kaydet(fig, "93_ucleme", olcum=dict(
        aylik=dict(bar=int(len(aylik)), spike_ay="2026-01",
                   spike=[round(float(aylik.o[sp])), round(float(aylik.c[sp]))],
                   kanal=["2026-02", "2026-06"], duzeltme_dip=round(float(aylik.l[d0]))),
        gunluk=dict(bar=int(len(gunluk)), pencere=["2026-06-08", "2026-07-10"],
                    spike_gun="2026-06-15",
                    spike=[round(float(gunluk.o[gs])), round(float(gunluk.c[gs]))],
                    kanal=["2026-06-16", "2026-06-19"],
                    duzeltme_dip=round(float(gunluk.l[gd0:gd1 + 1].min()))),
        besdk=dict(bar=int(len(gun5)), seans="2026-06-15",
                   acilis_spike=[round(float(gun5.o[0]), 1), round(float(gun5.c[0]), 1)],
                   kanal_bar=[30, 59], duzeltme_bar=[60, 73])))


# ===================================================================== 94
def f94_kacinilacak_islem():
    """Kaçınılacak tek en önemli işlem (Ş, 2 panel)."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16,
                        subplot_titles=("Panel 1 — dar bandın TEPESİNDEN alım",
                                        "Panel 2 — aynı barın iki tarafının matematiği"))

    ohlc = [(99.9, 100.4, 99.5, 100.1), (100.1, 100.5, 99.6, 99.7),
            (99.7, 100.3, 99.4, 100.2), (100.2, 100.5, 99.7, 99.8),
            (99.8, 100.4, 99.5, 100.3), (100.3, 100.6, 99.8, 99.9),
            (99.9, 100.4, 99.4, 100.2), (100.2, 100.5, 99.6, 99.8),
            (99.8, 100.3, 99.5, 100.1), (100.1, 100.6, 99.7, 99.9),
            (99.9, 100.5, 99.6, 100.4), (100.4, 100.6, 99.9, 100.0),
            (100.0, 100.5, 99.5, 100.3), (100.3, 100.6, 99.8, 100.0),
            (100.0, 100.4, 99.6, 100.2),
            (100.2, 101.10, 100.10, 101.00),                 # 15: kırılım barı (tuzak)
            (101.00, 101.15, 100.20, 100.30),                # 16: geri emiliyor
            (100.30, 100.45, 99.60, 99.70),
            (99.70, 99.95, 99.20, 99.30),
            (99.30, 99.60, 98.85, 98.95),
            (98.95, 99.35, 98.70, 99.25), (99.25, 99.60, 99.05, 99.45),
            (99.45, 99.80, 99.25, 99.60)]
    df = df_yap(ohlc)
    mumla(fig, df, row=1, col=1)
    BANT_UST, BANT_ALT = 100.60, 99.40
    ORTA = (BANT_UST + BANT_ALT) / 2
    kutu(fig, -0.5, 15.5, BANT_ALT, BANT_UST, GRI, a=0.12, cizgi=1.2, row=1, col=1)
    not_(fig, 6, ORTA, "dar yatay bant — 15 bar, örtüşme yoğun, bant yüksekliği 1,20",
         renk=GRI, ok=False, boyut=10.5, row=1, col=1)
    for y, ad, renk, ya in ((BANT_UST, "bant tepesi 100,60", GRI, "top"),
                            (ORTA, "bant ortası 100,00 — bant gününün hedefi", MOR, "middle"),
                            (BANT_ALT, "bant dibi 99,40", GRI, "middle")):
        yatay(fig, y, -0.5, len(df) - 1, renk=renk, dash="dash", w=1.3, row=1, col=1)
        not_(fig, len(df) - 1, y, ad, renk=renk, ok=False, boyut=10, xanchor="left",
             yanchor=ya, row=1, col=1)

    GIRIS, STOP, HEDEF = 100.70, 99.30, 101.10
    kutu(fig, 14.55, 15.45, df.l[15], df.h[15], TURUNCU, a=0.22, cizgi=1.4, row=1, col=1)
    not_(fig, 15, df.h[15], "kırılım barı — 'güçlü' görünür", renk=TURUNCU,
         ax=-74, ay=-26, boyut=10, row=1, col=1)
    yatay(fig, GIRIS, 15, len(df) - 1, renk=BORDO, dash="solid", w=1.7, row=1, col=1)
    not_(fig, len(df) - 1, GIRIS, "KÖTÜ giriş: bant tepesinin üstünden alış stopu 100,70",
         renk=BORDO, ok=False, boyut=10, xanchor="left", yanchor="bottom", row=1, col=1)
    yatay(fig, STOP, 15, len(df) - 1, renk=BORDO, dash="dot", w=1.5, row=1, col=1)
    not_(fig, len(df) - 1, STOP, "stop 99,30 → risk 1,40", renk=BORDO, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    yatay(fig, HEDEF, 15, len(df) - 1, renk=BORDO, dash="dash", w=1.2, row=1, col=1)
    not_(fig, len(df) - 1, HEDEF, "umulan scalp hedefi 101,10 → ödül 0,40 (0,29R)",
         renk=BORDO, ok=False, boyut=10, xanchor="left", row=1, col=1)
    not_(fig, 17, df.l[17], "kırılım geri emiliyor: %80 kuralı işliyor", renk=TURUNCU,
         ax=-96, ay=34, boyut=10.5, row=1, col=1)
    yatay(fig, BANT_UST + 0.02, 10, len(df) - 1, renk=TEAL, dash="solid", w=1.7,
          row=1, col=1)
    not_(fig, 0.2, BANT_UST + 0.03,
         "DOĞRU işlem aynı yerde: bant tepesine LİMİTLE SATIŞ (fade)",
         renk=TEAL, ok=False, boyut=10, xanchor="left", yanchor="bottom", row=1, col=1)
    not_(fig, 1, 98.75,
         "Kaçınılacak tek en önemli işlem: dar bandın tepesinden almak "
         "(ve dibinden satmak).<br>Kaybın anatomisi hep aynıdır — küçük ödül, "
         "büyük risk, düşük olasılık.",
         renk=MUREKKEP, ok=False, boyut=11, xanchor="left", row=1, col=1)
    fig.update_xaxes(range=[-0.8, len(df) + 11], row=1, col=1)

    # --- panel 2
    sen = [("dar bant TEPESİNDEN alım<br>P %40 · ödül 4 tick · risk 8 tick", 0.40, 4.0, 8.0),
           ("aynı yerde LİMİTLE SATIŞ<br>P %60 · ödül 8 tick · risk 4 tick", 0.60, 8.0, 4.0)]
    kaz = [round(s[1] * s[2], 2) for s in sen]
    kay = [round((1 - s[1]) * s[3], 2) for s in sen]
    net = [round(a - b, 2) for a, b in zip(kaz, kay)]
    x2 = [f"{s[0]}<br><b>{tr(s[2] / s[3])}R → {tr(n, isaretli=True)} tick</b>"
          for s, n in zip(sen, net)]
    hesap2 = [f"{tr(p)} × {o:.0f} = {tr(p * o)} tick<br>"
              f"{tr(1 - p)} × {r:.0f} = {tr((1 - p) * r)} tick<br>"
              f"net {tr(p * o - (1 - p) * r, isaretli=True)} tick · "
              f"ödül/risk {tr(o / r)}R" for _, p, o, r in sen]
    ev_bar(fig, x2, kaz, kay, net, row=2, col=1, ilk=True, hesap=hesap2)
    yatay(fig, 0, -0.5, 1.5, renk=GRI, dash="solid", w=1.0, row=2, col=1)
    for i in range(2):
        not_(fig, i, net[i], f"beklenen değer {tr(net[i], isaretli=True)} tick",
             renk=TURUNCU if net[i] < 0 else TEAL, ok=False, boyut=11,
             yanchor="top" if net[i] < 0 else "bottom", row=2, col=1)
    not_(fig, 0.5, -5.9,
         "İki sütun aynı barın iki tarafıdır ve toplamları sıfırdır.<br>"
         "Kötü işlemi almak, karşı tarafa +3,20 tick'lik iyi işlemi hediye etmektir.<br>"
         "Günün en önemli işi kâr eden işlemi bulmak değil, bu işlemi ALMAMAKTIR.",
         renk=MUREKKEP, ok=False, boyut=11, yanchor="bottom", row=2, col=1)
    fig.update_layout(barmode="group", bargap=0.42)

    duzen(fig, "94 · Kaçınılacak tek en önemli işlem",
          "kayıpların anatomisi: küçük ödül · büyük risk · düşük olasılık · " + ESIK,
          h=1020, sematik=True)
    fig.update_yaxes(title_text="fiyat (şematik birim)", row=1, col=1)
    fig.update_yaxes(title_text="beklenen değer (tick)", row=2, col=1, range=[-8.6, 6.4])
    fig.update_xaxes(title_text="bar sırası", row=1, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    kaydet(fig, "94_kacinilacak_islem", olcum=dict(
        bant_ust=BANT_UST, bant_alt=BANT_ALT, bant_orta=ORTA,
        bant_yuksekligi=round(BANT_UST - BANT_ALT, 2), bant_bar=15,
        kotu=dict(giris=GIRIS, stop=STOP, hedef=HEDEF, risk=round(GIRIS - STOP, 2),
                  odul=round(HEDEF - GIRIS, 2), R=round((HEDEF - GIRIS) / (GIRIS - STOP), 2),
                  P=0.40, ev_tick=net[0]),
        iyi=dict(P=0.60, odul_tick=8.0, risk_tick=4.0, ev_tick=net[1])))


# ===================================================================== main
def main():
    print("Al Brooks · figür 79–94 (B10–B14, B16)")
    for f in (f79_trader_denklemi, f80_takas_egrisi, f81_duzeltme_aritmetigi,
              f82_buyuyen_spike, f83_kanal_erozyonu, f84_kazanma_orani,
              f85_emir_haritasi, f86_stop_merdiveni, f87_olcekli_giris,
              f88_olcekli_cikis, f89_always_in_donusu, f90_gun_tipleri,
              f91_acilis_araligi, f92_seans_haritasi, f93_ucleme,
              f94_kacinilacak_islem):
        f()
    defter_yaz()


if __name__ == "__main__":
    main()
