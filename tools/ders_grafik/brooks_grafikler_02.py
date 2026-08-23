#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Al Brooks fiyat hareketi dersi — FİGÜR 13–29.

Kapsanan bölümler:
  B2 (13–19) sinyal barı, kurulum, giriş mekaniği, örtüşme kuralı, iç/dış bar
             kalıpları, ikinci giriş
  B3 (20–29) trend türleri, spike ve kanal, mikro kanal, trend çizgisi ve
             kanal çizgisi

Kurallar (ortak katmanla aynı):
  · Şematik figürlerde barlar ELLE kurulur; geometri kavramı gösterecek şekilde
    seçilir, tesadüfe bırakılmaz.
  · Gerçek veri figürlerinde pencere İNDİSLE pinlenir (dilim/seans) — "son N bar"
    yok; ders metnindeki sayılar grafikle birebir tutar.
  · Çok panelli figürlerde paneller ALT ALTA (rows=N, cols=1).
  · Metinle kıyaslanacak her sayı kaydet(..., olcum={...}) ile bırakılır.

VERİ NOTU (önemli, ders metnine de geçmeli): müfredat 19 ve 24 numaralı figürler
için USDTRY 5dk istiyor. Önbellekteki USDTRY içgün serisi (yfinance spot) fiyat
hareketi öğretmeye elverişli değil: medyan bar gövdesi medyan menzilin %6'sı,
barların yükseği/düşüğü büyük ölçüde bayat kotasyon tırnakları. Bu yüzden bu iki
figür müfredatın kendi öncelik listesindeki TEMİZ enstrümanlara alındı
(19 → XU030 5dk, 24 → XAUUSD/GC vadeli 15dk) ve durum altbaşlıkta yazıyor.
Sentetik veri "gerçek" diye sunulmadı.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from brooks_ortak import (
    ALTIN, BORDO, CIZGI, GRI, KAGIT, MAVI, MOR, MUREKKEP, TEAL, TURUNCU, YESIL,
    bar, bar_etiketle, bar_say, bosluk_isaretle, cizgi, defter_yaz, df_yap, dilim,
    duzen, ema_ciz, hover, kutu, lejant, lejant_cizgi, mumlar, not_,
    olculmus_hareket, rgba, seans, trend_cizgisi, yatay, yukle, zaman_ekseni,
)
from brooks_ortak import kaydet as _kaydet


def kaydet(fig, ad, olcum=None):
    """Kayıttan hemen önce lejantı tekilleştirir.

    Çok panelli figürlerde her panele ayrı 20 bar EMA izi ekleniyor; hepsi
    lejanta girerse aynı ad üst üste yazılır. Ortak katmanı değiştirmemek için
    tekilleştirme burada yapılır.
    """
    gorulen = set()
    for tr in fig.data:
        ad_ = getattr(tr, "name", None)
        if ad_ is None or getattr(tr, "showlegend", None) is False:
            continue
        if ad_ in gorulen:
            tr.showlegend = False
        else:
            gorulen.add(ad_)
    _kaydet(fig, ad, olcum=olcum)

# ------------------------------------------------------------------ yerel yardımcılar


def mum_ekle(fig, df, row=None, col=None, ad="fiyat", zaman=False):
    """Mum serisini ekler; lejantta yer kaplamasın diye gösterilmez."""
    tr = mumlar(df, ad=ad, hover=hover(df) if zaman else None)
    tr.showlegend = False
    fig.add_trace(tr, row=row, col=col)
    return tr


def olcu(fig, x, y0, y1, metin, renk=MOR, row=None, col=None, yan="sag", boyut=10):
    """Dikey ölçü çubuğu: iki uçta kısa yatay tırnak + ortada etiket."""
    cizgi(fig, x, y0, x, y1, renk=renk, w=1.6, row=row, col=col)
    for y in (y0, y1):
        cizgi(fig, x - 0.28, y, x + 0.28, y, renk=renk, w=1.6, row=row, col=col)
    not_(fig, x + (0.45 if yan == "sag" else -0.45), (y0 + y1) / 2, metin, renk=renk,
         ok=False, boyut=boyut, xanchor="left" if yan == "sag" else "right",
         row=row, col=col)


def olcu_yatay(fig, y, x0, x1, metin, renk=MOR, row=None, col=None, boyut=10):
    """Yatay ölçü çubuğu (bar sayısı / süre ölçmek için)."""
    cizgi(fig, x0, y, x1, y, renk=renk, w=1.6, row=row, col=col)
    return not_(fig, (x0 + x1) / 2, y, metin, renk=renk, ok=False, boyut=boyut,
                row=row, col=col)


def tick_of(df, oran=0.004):
    return (df.h.max() - df.l.min()) * oran


def eksen_pad(fig, df, alt=0.10, ust=0.10, row=None, col=None):
    """Etiketler bara yapışmasın diye y eksenine pay bırak."""
    r = df.h.max() - df.l.min()
    fig.update_yaxes(range=[df.l.min() - r * alt, df.h.max() + r * ust], row=row, col=col)


def sag_oluk(fig, df, pay=0.34, sol=1.0, row=None, col=None):
    """Sağda etiket oluğu aç ve x eksenini oraya kadar SABİTLE.

    Plotly, sağa yaslı etiketleri eksene katmaz; oluk açılmazsa 'giriş / stop / 2R'
    yazıları grafiğin dışına taşar ya da eksen rastgele uzar. Dönüş: etiketlerin
    konacağı x.
    """
    n = len(df) - 1
    son = n + max(3.0, n * pay)
    fig.update_xaxes(range=[-sol, son], row=row, col=col)
    return n + max(1.5, n * pay * 0.16)


# ==================================================================== 13
def f13():
    """Kurulum → sinyal → giriş → takip zinciri (şematik, 1 panel)."""
    ohlc = [
        bar(100.00, 100.90, .20, .25), bar(100.85, 101.70, .25, .20),
        bar(101.65, 102.55, .20, .30), bar(102.50, 103.45, .30, .20),
        bar(103.40, 104.30, .25, .25),
        bar(104.30, 103.75, .15, .35), bar(103.70, 103.20, .20, .30),
        bar(103.20, 102.75, .25, .30),                     # 7 kurulum barı
        bar(102.80, 103.40, .12, .50),                     # 8 sinyal barı
        bar(103.45, 104.00, .15, .20),                     # 9 giriş barı
        bar(104.00, 104.90, .20, .15),                     # 10 takip barı
        bar(104.88, 105.55, .22, .18), bar(105.50, 106.15, .25, .20),
        bar(106.10, 106.75, .20, .25), bar(106.70, 106.45, .30, .20),
    ]
    df = df_yap(ohlc)
    fig = go.Figure()
    mum_ekle(fig, df)

    t = tick_of(df)
    giris = df.h[8] + t
    stop = df.l[8] - t
    risk = giris - stop
    h1, h2 = giris + risk, giris + 2 * risk

    x_et = sag_oluk(fig, df, pay=0.42)
    x_son = x_et - 0.3

    for i, (ad, renk, ax, ay) in enumerate([("① kurulum barı", GRI, -62, 58),
                                            ("② sinyal barı", ALTIN, -20, 96),
                                            ("③ giriş barı", MAVI, 26, 134),
                                            ("④ takip barı", YESIL, 76, 172)]):
        j = 7 + i
        kutu(fig, j - 0.45, j + 0.45, df.l[j], df.h[j], renk, a=0.18, cizgi=1.3)
        not_(fig, j, df.l[j] - t * 2, ad, renk=renk, ok=True, ax=ax, ay=ay, boyut=11)

    yatay(fig, giris, 7.6, x_son, renk=MAVI, dash="solid", w=1.8)
    not_(fig, x_et, giris, f"buy stop {giris:.2f}<br>(sinyal barının 1 tick üstü)",
         renk=MAVI, ok=False, boyut=10, xanchor="left")
    yatay(fig, stop, 7.6, x_son, renk=BORDO, dash="dot", w=1.6)
    not_(fig, x_et, stop, f"koruyucu stop {stop:.2f}<br>risk {risk:.2f} = 1R",
         renk=BORDO, ok=False, boyut=10, xanchor="left")
    for y, ad in ((h1, "1R — scalp hedefi"), (h2, "2R — swing hedefi")):
        yatay(fig, y, 7.6, x_son, renk=MOR, dash="dash", w=1.4)
        not_(fig, x_et, y, f"{ad} {y:.2f}", renk=MOR, ok=False, boyut=10, xanchor="left")

    not_(fig, 0.2, 108.2,
         "<b>Zincirin kuralı</b><br>"
         "· sinyal barı = kurulumun SON barı; emir onun ötesine konur<br>"
         "· giriş barı = emri tetikleyen bar; risk burada başlar<br>"
         "· takip barının asgari ölçütü: giriş barının KAPANIŞININ ötesinde kapanmak",
         renk=MUREKKEP, ok=False, boyut=10, xanchor="left")
    not_(fig, 10, float(df.c[10]),
         "takip barı ölçütü sağlandı:<br>"
         f"{df.c[10]:.2f} > giriş barının kapanışı {df.c[9]:.2f}",
         renk=YESIL, ok=True, ax=126, ay=132, boyut=10)

    lejant(fig, "kurulum barı", GRI)
    lejant(fig, "sinyal barı", ALTIN)
    lejant(fig, "giriş barı", MAVI)
    lejant(fig, "takip barı", YESIL)
    lejant_cizgi(fig, "giriş / stop / hedef", MOR)
    fig.update_yaxes(range=[98.7, 109.0])
    duzen(fig, "13 · Kurulum → sinyal → giriş → takip zinciri",
          "boğa trendinde geri çekilme alımı: dört barın her biri ayrı bir iş yapar",
          h=620, sematik=True)
    kaydet(fig, "13_giris_zinciri", olcum=dict(
        sinyal_bar=8, giris=round(giris, 2), stop=round(stop, 2), risk_1R=round(risk, 2),
        hedef_1R=round(h1, 2), hedef_2R=round(h2, 2),
        takip_bari_kapanis=round(float(df.c[10]), 2),
        giris_bari_kapanis=round(float(df.c[9]), 2)))


# ==================================================================== 14
def f14():
    """En iyi boğa dönüş barının nitelikleri (şematik, 1 panel)."""
    ohlc = [
        (101.80, 101.90, 101.00, 101.05),
        (101.00, 101.10, 100.30, 100.35),
        (100.50, 100.60, 99.60, 99.70),
        (99.55, 100.90, 99.00, 100.75),      # 3 — dönüş barı
        (100.78, 101.60, 100.65, 101.50),
    ]
    df = df_yap(ohlc)
    o, h, l, c = (float(df[k][3]) for k in ("o", "h", "l", "c"))
    menzil = h - l
    govde = c - o
    alt_k = o - l
    ust_k = h - c
    kap_yeri = (c - l) / menzil

    fig = go.Figure()
    mum_ekle(fig, df)
    kutu(fig, 2.55, 3.45, l, h, ALTIN, a=0.10, cizgi=1.4)

    # dönüş barının dört seviyesi sağa taşınır: cetveller barın üstüne binmesin
    CET = 6.2                       # cetvellerin başladığı x
    for y, renk in ((h, GRI), (c, TEAL), (o, TEAL), (l, GRI)):
        yatay(fig, y, 3.45, CET + 2.5, renk=rgba(renk, 0.55), dash="dot", w=1.0)
    olcu(fig, CET, l, h, f"menzil {menzil:.2f}", renk=GRI)
    olcu(fig, CET + 1.1, o, c,
         f"gövde {govde:.2f} — menzilin %{govde/menzil*100:.0f}'i", renk=TEAL)
    olcu(fig, CET + 2.5, l, o,
         f"alt kuyruk {alt_k:.2f} — %{alt_k/menzil*100:.0f}", renk=MAVI)
    olcu(fig, CET + 2.5, c, h,
         f"üst kuyruk {ust_k:.2f} — %{ust_k/menzil*100:.0f}", renk=TURUNCU)

    orta = (h + l) / 2
    yatay(fig, orta, 2.55, 5.3, renk=GRI, dash="dash", w=1.3)
    not_(fig, 5.4, orta, "menzilin orta noktası", renk=GRI, ok=False, boyut=9,
         xanchor="left")

    not_(fig, 3, c, f"kapanış menzilin %{kap_yeri*100:.0f}'inde",
         renk=YESIL, ok=True, ax=-58, ay=-40, boyut=10)
    yatay(fig, float(df.l[2]), 1.55, 3.45, renk=BORDO, dash="dash", w=1.2)
    yatay(fig, float(df.h[2]), 1.55, 3.45, renk=TEAL, dash="dash", w=1.2)
    not_(fig, 3, o, "açılış önceki barın DÜŞÜĞÜNÜN altında", renk=BORDO,
         ok=True, ax=-96, ay=54, boyut=10)
    not_(fig, 4, float(df.h[4]),
         "kapanış önceki barın YÜKSEĞİNİN üstünde", renk=TEAL,
         ok=True, ax=64, ay=-30, boyut=10)

    for j, y in ((1, float(df.c[1])), (2, float(df.c[2]))):
        yatay(fig, y, j - 0.45, 3.45, renk=rgba(TURUNCU, 0.9), dash="dot", w=1.1)
        not_(fig, j - 0.5, y, f"kapanış {y:.2f}", renk=TURUNCU, ok=False, boyut=9,
             xanchor="right")

    not_(fig, -2.05, 98.92,
         "<b>EN İYİ boğa dönüş barı</b><br>"
         f"· gövde menzilin %{govde/menzil*100:.0f}'i — büyük ve boğa<br>"
         f"· alt kuyruk %{alt_k/menzil*100:.0f} — satıcı reddedildi<br>"
         f"· üst kuyruk %{ust_k/menzil*100:.0f} — tepede satış yok<br>"
         "· açılış önceki barın düşüğünün ALTINDA<br>"
         "· kapanış İKİ barın kapanışını tersine çevirdi<br>"
         "· takip barı yükseği aşıp üstünde kapattı",
         renk=MUREKKEP, ok=False, boyut=10, xanchor="left", yanchor="top")

    lejant(fig, "dönüş barı", ALTIN)
    lejant_cizgi(fig, "önceki barın uçları", TEAL)
    lejant_cizgi(fig, "tersine çevrilen kapanışlar", TURUNCU, dash="dot")
    fig.update_xaxes(range=[-2.2, 11.6], showticklabels=False, title_text="")
    fig.update_yaxes(range=[97.45, 102.25])
    duzen(fig, "14 · En iyi boğa dönüş barının nitelikleri",
          "asgari koşul değil, EN İYİ hâli: büyük gövde · belirgin alt kuyruk · "
          "kuyruksuz tepe · uçta kapanış",
          h=620, sematik=True)
    kaydet(fig, "14_donus_bari_nitelikleri", olcum=dict(
        menzil=round(menzil, 2), govde=round(govde, 2),
        govde_orani_yuzde=round(govde / menzil * 100),
        alt_kuyruk=round(alt_k, 2), alt_kuyruk_yuzde=round(alt_k / menzil * 100),
        ust_kuyruk=round(ust_k, 2), ust_kuyruk_yuzde=round(ust_k / menzil * 100),
        kapanis_menzil_yuzde=round(kap_yeri * 100),
        tersine_cevrilen_kapanis_sayisi=2,
        acilis_onceki_barin_dusugunun_altinda=True))


# ==================================================================== 15
def f15():
    """Örtüşme kuralı — orta nokta ölçütü (şematik, 2 panel)."""
    ortak = [bar(100.00, 100.70, .20, .20), bar(100.70, 101.40, .20, .20),
             bar(101.40, 102.10, .25, .20), bar(102.10, 101.60, .15, .35),
             bar(101.55, 101.15, .20, .30)]
    kabul = df_yap(ortak + [
        bar(101.05, 102.00, .10, .30),          # 5 sinyal barı — kabul
        bar(102.05, 102.75, .15, .15),
        bar(102.75, 103.45, .20, .20),
        bar(103.40, 103.15, .25, .20)])
    ret = df_yap(ortak + [
        bar(101.05, 101.25, .15, .25),          # 5 sinyal barı — ret
        bar(101.20, 100.80, .15, .30),
        bar(100.80, 100.40, .20, .35),
        bar(100.40, 100.05, .15, .30)])

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12, subplot_titles=(
        "Panel 1 — KABUL: sinyal barı önceki barın orta noktasının üstünde kapanıyor",
        "Panel 2 — RET: sinyal barı önceki barın içinde, orta noktanın altında kapanıyor"))

    olcumler = {}
    for r, (df, ad, renk) in enumerate([(kabul, "kabul", YESIL), (ret, "ret", TURUNCU)], start=1):
        mum_ekle(fig, df, row=r, col=1)
        t = tick_of(df)
        onc_h, onc_l = float(df.h[4]), float(df.l[4])
        orta = (onc_h + onc_l) / 2
        yatay(fig, orta, 3.4, 8.5, renk=MUREKKEP, dash="dash", w=1.6, row=r, col=1)
        not_(fig, 8.5, orta, f"önceki barın orta noktası {orta:.2f}", renk=MUREKKEP,
             ok=False, boyut=10, xanchor="left", row=r, col=1)
        kutu(fig, 3.55, 4.45, onc_l, onc_h, GRI, a=0.14, cizgi=1.1, row=r, col=1)
        not_(fig, 4, onc_l - t * 4, "önceki bar", renk=GRI, ok=False, boyut=10,
             yanchor="top", row=r, col=1)
        kutu(fig, 4.55, 5.45, float(df.l[5]), float(df.h[5]), renk, a=0.20, cizgi=1.4,
             row=r, col=1)

        s_h, s_l, s_c = float(df.h[5]), float(df.l[5]), float(df.c[5])
        ortusme = max(0.0, min(s_h, onc_h) - max(s_l, onc_l)) / (s_h - s_l)
        olcumler[ad] = dict(sinyal_kapanis=round(s_c, 2), orta_nokta=round(orta, 2),
                            ortusme_yuzde=round(ortusme * 100),
                            onceki_bar_yuksegi=round(onc_h, 2),
                            sinyal_bari_yuksegi=round(s_h, 2))

        if ad == "kabul":
            giris = s_h + t
            yatay(fig, giris, 4.6, 8.5, renk=MAVI, dash="solid", w=1.6, row=r, col=1)
            not_(fig, 8.5, giris, f"giriş {giris:.2f}", renk=MAVI, ok=False, boyut=10,
                 xanchor="left", row=r, col=1)
            not_(fig, 5, s_c,
                 f"kapanış {s_c:.2f} > orta nokta {orta:.2f}<br>"
                 f"ve önceki barın yükseğinin ({onc_h:.2f}) de üstünde<br>"
                 f"örtüşme %{ortusme*100:.0f} → KABUL",
                 renk=YESIL, ok=True, ax=76, ay=-54, boyut=10, row=r, col=1)
            not_(fig, 7, float(df.c[7]), "takip geldi", renk=YESIL, ok=True,
                 ax=0, ay=-34, boyut=10, row=r, col=1)
        else:
            not_(fig, 5, s_c,
                 f"kapanış {s_c:.2f} < orta nokta {orta:.2f}<br>"
                 f"bar tümüyle önceki barın içinde, örtüşme %{ortusme*100:.0f}<br>"
                 "→ RET: bu iki bar aslında bir yatay bant",
                 renk=TURUNCU, ok=True, ax=86, ay=-58, boyut=10, row=r, col=1)
            not_(fig, 7, float(df.c[7]),
                 "emir verilseydi: dolum olur, sonra düşüş", renk=BORDO, ok=True,
                 ax=0, ay=-40, boyut=10, row=r, col=1)
        eksen_pad(fig, df, .16, .18, row=r, col=1)

    lejant_cizgi(fig, "önceki barın orta noktası", MUREKKEP)
    lejant(fig, "kabul edilen sinyal barı", YESIL)
    lejant(fig, "reddedilen sinyal barı", TURUNCU)
    duzen(fig, "15 · Örtüşme kuralı (orta nokta ölçütü)",
          "aynı geri çekilme, iki farklı sinyal barı — ölçüt kapanışın önceki barın "
          "orta noktasına göre yeri",
          h=880, sematik=True)
    kaydet(fig, "15_ortusme_kurali", olcum=olcumler)


# ==================================================================== 16
def f16():
    """İki barlık ve üç barlık dönüş (şematik, 2 panel)."""
    on = [bar(102.00, 101.50, .15, .30), bar(101.50, 100.90, .15, .35)]

    iki = df_yap(on + [
        bar(100.90, 100.30, .10, .40),
        bar(100.30, 99.60, .10, .45),        # 3 — birinci bar: ayı trend barı
        bar(99.62, 100.35, .12, .40),        # 4 — ikinci bar: boğa trend barı
        bar(100.40, 101.10, .15, .15),
        bar(101.10, 101.85, .20, .15),
        bar(101.85, 102.40, .20, .20)])

    uc = df_yap(on + [
        bar(100.90, 100.35, .12, .35),       # 2 — A: ayı barı
        bar(100.35, 100.05, .15, .45),       # 3 — B: daha düşük dip
        bar(100.10, 100.80, .15, .25),       # 4 — C: boğa barı, B'nin yükseğini aşıp üstünde kapanıyor
        bar(100.85, 101.55, .18, .18),
        bar(101.55, 102.25, .20, .15),
        bar(102.25, 102.75, .20, .20)])

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12, subplot_titles=(
        "Panel 1 — iki barlık dönüş: ayı trend barı + boğa trend barı",
        "Panel 2 — üç barlık dönüş: ayı barı → daha düşük dip → boğa barı"))

    # --- panel 1
    t = tick_of(iki)
    mum_ekle(fig, iki, row=1, col=1)
    kalip_h = max(float(iki.h[3]), float(iki.h[4]))
    kalip_l = min(float(iki.l[3]), float(iki.l[4]))
    kutu(fig, 2.55, 4.45, kalip_l, kalip_h, ALTIN, a=0.16, cizgi=1.4, row=1, col=1)
    giris1 = kalip_h + t
    yatay(fig, giris1, 2.6, 7.5, renk=MAVI, dash="solid", w=1.7, row=1, col=1)
    not_(fig, 4, giris1, f"giriş: iki barın YÜKSEĞİNİN 1 tick üstü — buy stop {giris1:.2f}",
         renk=MAVI, ok=True, ax=64, ay=-46, boyut=10, row=1, col=1)
    stop1 = kalip_l - t
    yatay(fig, stop1, 2.6, 7.5, renk=BORDO, dash="dot", w=1.5, row=1, col=1)
    not_(fig, 7.5, stop1, f"stop {stop1:.2f} · risk {giris1-stop1:.2f}", renk=BORDO,
         ok=False, boyut=10, xanchor="left", row=1, col=1)
    not_(fig, 3, float(iki.l[3]) - t * 3, "① güçlü ayı trend barı", renk=BORDO,
         ok=True, ax=-46, ay=34, boyut=10, row=1, col=1)
    not_(fig, 4, float(iki.l[4]) - t * 3, "② aynı boyda boğa trend barı", renk=TEAL,
         ok=True, ax=46, ay=44, boyut=10, row=1, col=1)
    eksen_pad(fig, iki, .18, .16, row=1, col=1)

    # --- panel 2
    t2 = tick_of(uc)
    mum_ekle(fig, uc, row=2, col=1)
    kalip_h2 = float(uc.h[4])
    kalip_l2 = float(uc.l[3])
    kutu(fig, 1.55, 4.45, kalip_l2, max(float(uc.h[2]), kalip_h2), ALTIN, a=0.14,
         cizgi=1.4, row=2, col=1)
    giris2 = kalip_h2 + t2
    yatay(fig, giris2, 1.6, 7.5, renk=MAVI, dash="solid", w=1.7, row=2, col=1)
    not_(fig, 4, giris2, f"giriş: ÜÇÜNCÜ barın yükseğinin 1 tick üstü — buy stop {giris2:.2f}",
         renk=MAVI, ok=True, ax=60, ay=-46, boyut=10, row=2, col=1)
    stop2 = kalip_l2 - t2
    yatay(fig, stop2, 1.6, 7.5, renk=BORDO, dash="dot", w=1.5, row=2, col=1)
    not_(fig, 7.5, stop2, f"stop {stop2:.2f} · risk {giris2-stop2:.2f}", renk=BORDO,
         ok=False, boyut=10, xanchor="left", row=2, col=1)
    yatay(fig, float(uc.h[3]), 2.6, 4.45, renk=GRI, dash="dot", w=1.2, row=2, col=1)
    for j, et, ax_, ay_ in ((2, "A · ayı barı", -76, 34),
                            (3, "B · daha düşük dip", -10, 74),
                            (4, "C · boğa barı — B'nin yükseğinin üstünde kapanıyor",
                             172, 58)):
        not_(fig, j, float(uc.l[j]) - t2 * 2, et, renk=MUREKKEP, ok=True, ax=ax_,
             ay=ay_, boyut=10, row=2, col=1)
    eksen_pad(fig, uc, .34, .16, row=2, col=1)

    lejant(fig, "dönüş kalıbı", ALTIN)
    lejant_cizgi(fig, "giriş (buy stop)", MAVI, dash="solid")
    lejant_cizgi(fig, "koruyucu stop", BORDO, dash="dot")
    duzen(fig, "16 · İki barlık ve üç barlık dönüş",
          "iki kalıp da tek bir birleşik bar gibi okunur; emir birleşik barın ucuna konur",
          h=880, sematik=True)
    kaydet(fig, "16_iki_uc_barlik_donus", olcum=dict(
        iki_barlik=dict(kalip_yuksegi=round(kalip_h, 2), kalip_dusugu=round(kalip_l, 2),
                        giris=round(giris1, 2), stop=round(stop1, 2),
                        risk=round(giris1 - stop1, 2)),
        uc_barlik=dict(kalip_yuksegi=round(kalip_h2, 2), kalip_dusugu=round(kalip_l2, 2),
                       giris=round(giris2, 2), stop=round(stop2, 2),
                       risk=round(giris2 - stop2, 2))))


# ==================================================================== 17
def f17():
    """ii · iii · ioi · oo kartelası (şematik, 1 panel)."""
    bos = (np.nan, np.nan, np.nan, np.nan)
    ohlc = []
    # ii  (0-3)
    ohlc += [bar(100.00, 100.90, .20, .20), bar(100.90, 100.20, .25, .30),
             bar(100.35, 100.75, .10, .15), bar(100.70, 100.45, .08, .12)]
    ohlc += [bos, bos]                                                     # 4-5
    # iii (6-10)
    ohlc += [bar(100.00, 100.80, .20, .20), bar(100.80, 100.10, .30, .35),
             bar(100.25, 100.70, .12, .18), bar(100.65, 100.35, .08, .12),
             bar(100.40, 100.60, .06, .08)]
    ohlc += [bos, bos]                                                     # 11-12
    # ioi (13-17)
    ohlc += [bar(100.00, 100.85, .20, .20), bar(100.85, 100.15, .28, .32),
             bar(100.30, 100.72, .10, .15), bar(100.70, 100.25, .25, .30),
             bar(100.35, 100.70, .10, .15)]
    ohlc += [bos, bos]                                                     # 18-19
    # oo  (20-22)
    ohlc += [bar(100.00, 100.60, .20, .20), bar(100.65, 100.10, .30, .35),
             bar(100.20, 100.85, .25, .55)]
    df = df_yap(ohlc)

    fig = go.Figure()
    mum_ekle(fig, df)

    gruplar = [
        (1, 3, "ii", "iki ardışık iç bar"),
        (7, 10, "iii", "üç ardışık iç bar"),
        (14, 17, "ioi", "iç · dış · iç"),
        (21, 22, "oo", "iki ardışık dış bar"),
    ]
    Y_AD = 101.92          # kalıp adı satırı
    Y_ACIK = 99.32         # kısa açıklama satırı
    olcumler = {}
    for i0, i1, ad, aciklama in gruplar:
        hh = float(df.h[i0:i1 + 1].max())
        ll = float(df.l[i0:i1 + 1].min())
        pay = (hh - ll) * 0.22
        kutu(fig, i0 - 0.7, i1 + 0.7, ll - pay * 0.45, hh + pay * 0.45, ALTIN,
             a=0.10, cizgi=1.2)
        orta = (i0 + i1) / 2
        not_(fig, orta, Y_AD, f"<b>{ad}</b>", renk=MUREKKEP, ok=False, boyut=16)
        not_(fig, orta, Y_ACIK, aciklama, renk=MUREKKEP, ok=False, boyut=10)
        not_(fig, i1 + 0.7, hh, f"buy stop {hh:.2f}", renk=TEAL, ok=True,
             ax=30, ay=-26, boyut=9)
        not_(fig, i1 + 0.7, ll, f"sell stop {ll:.2f}", renk=BORDO, ok=True,
             ax=30, ay=26, boyut=9)
        yatay(fig, hh, i0 - 0.7, i1 + 0.7, renk=TEAL, dash="solid", w=1.4)
        yatay(fig, ll, i0 - 0.7, i1 + 0.7, renk=BORDO, dash="solid", w=1.4)
        olcumler[ad] = dict(kalip_bar_sayisi=i1 - i0 + 1,
                            ic_veya_dis_bar_sayisi=len(ad),
                            kalip_yuksegi=round(hh, 2),
                            kalip_dusugu=round(ll, 2), yukseklik=round(hh - ll, 2))

    not_(fig, 11.5, 98.92,
         "dördünün ortak dili: kalıp bir YATAY BANTTIR — yön bilinmez, iki tarafa da "
         "emir konur, piyasa hangisini tetiklerse o taraf oynanır",
         renk=GRI, ok=False, boyut=11)

    lejant(fig, "kalıp kutusu", ALTIN)
    lejant_cizgi(fig, "buy stop seviyesi", TEAL, dash="solid")
    lejant_cizgi(fig, "sell stop seviyesi", BORDO, dash="solid")
    fig.update_yaxes(range=[98.72, 102.28])
    fig.update_xaxes(range=[-1.8, 25.4], showticklabels=False, title_text="")
    duzen(fig, "17 · ii · iii · ioi · oo kartelası",
          "dört iç/dış bar kalıbı ve her birinde çift taraflı emir haritası",
          h=620, sematik=True)
    kaydet(fig, "17_ic_dis_bar_kartelasi", olcum=olcumler)


# ==================================================================== 18
def f18():
    """Trend gücü ↔ sinyal barı kalitesi ters ilişkisi (XU030 5dk, 2 panel)."""
    d = yukle("XU030.IS", "5m")
    if d is None:
        print("  ! 18 atlandı: XU030 5dk önbellekte yok")
        return
    guclu = seans(d, "2026-08-19").iloc[20:56].reset_index(drop=True)   # gün barı 20–55
    zayif = seans(d, "2026-08-14").iloc[14:43].reset_index(drop=True)   # gün barı 14–42

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.155, subplot_titles=(
        "Panel 1 — GÜÇLÜ boğa trendi (XU030 5dk, 19 Ağu 2026, günün 20.–55. barı): "
        "sinyal barları çirkin, işlemler kazanıyor",
        "Panel 2 — ZAYIF/bant piyasası (XU030 5dk, 14 Ağu 2026, günün 14.–42. barı): "
        "sinyal barları güzel, işlemler kaybediyor"))

    olcumler = {}

    # ---- panel 1: çirkin ama kazanan
    mum_ekle(fig, guclu, row=1, col=1, zaman=True)
    ema_ciz(fig, guclu, 20, renk=GRI, row=1, col=1)
    t1 = tick_of(guclu)
    kazanan = []
    for yerel, etiket in ((4, "A"), (20, "B")):     # gün barı 24 ve 40
        s_h, s_l = float(guclu.h[yerel]), float(guclu.l[yerel])
        giris = s_h + t1
        stop = s_l - t1
        risk = giris - stop
        tetik = next(j for j in range(yerel + 1, len(guclu)) if float(guclu.h[j]) > giris)
        ileri = guclu.iloc[tetik:tetik + 13]
        enyuksek = float(ileri.h.max())
        endusuk = float(ileri.l.min())
        r = (enyuksek - giris) / risk
        kutu(fig, yerel - 0.45, yerel + 0.45, s_l, s_h, ALTIN, a=0.22, cizgi=1.3,
             row=1, col=1)
        yatay(fig, giris, yerel - 0.4, tetik + 13, renk=MAVI, dash="solid", w=1.4,
              row=1, col=1)
        yatay(fig, stop, yerel - 0.4, tetik + 13, renk=BORDO, dash="dot", w=1.3,
              row=1, col=1)
        not_(fig, yerel, s_l - t1 * 6,
             f"{etiket} · AYI gövdeli sinyal barı ({guclu.c[yerel]-guclu.o[yerel]:+.0f} puan)<br>"
             "çirkin — yine de alınır",
             renk=ALTIN, ok=True, ax=-8, ay=118, boyut=10, row=1, col=1)
        not_(fig, min(tetik + 12, len(guclu) - 1), enyuksek,
             f"{etiket} · stop ({stop:.0f}) hiç görülmedi<br>"
             f"12 barda {r:.1f}R — ara dip {endusuk:.0f}",
             renk=YESIL, ok=True, ax=-120, ay=72, boyut=10, row=1, col=1)
        kazanan.append(dict(etiket=etiket, yerel_bar=yerel,
                            gun_bari=20 + yerel, govde=round(float(guclu.c[yerel] - guclu.o[yerel]), 1),
                            giris=round(giris, 1), stop=round(stop, 1), risk=round(risk, 1),
                            tetik_bari=20 + tetik, ulasilan_R=round(r, 1),
                            tetik_sonrasi_en_dusuk=round(endusuk, 1),
                            stop_oldu=bool(endusuk <= stop)))
    olcumler["guclu_trend"] = dict(gun="2026-08-19", pencere="gün barı 20–55",
                                   sinyaller=kazanan)
    eksen_pad(fig, guclu, .26, .10, row=1, col=1)
    zaman_ekseni(fig, guclu, 7, "%H:%M", row=1, col=1)

    # ---- panel 2: güzel ama kaybeden
    mum_ekle(fig, zayif, row=2, col=1, zaman=True)
    ema_ciz(fig, zayif, 20, renk=GRI, row=2, col=1)
    t2 = tick_of(zayif)
    kaybeden = []
    for yerel, etiket in ((6, "C"), (12, "D")):     # gün barı 20 ve 26
        s_h, s_l = float(zayif.h[yerel]), float(zayif.l[yerel])
        giris = s_h + t2
        stop = s_l - t2
        risk = giris - stop
        tetik = next((j for j in range(yerel + 1, len(zayif))
                      if float(zayif.h[j]) > giris), None)
        ileri = zayif.iloc[tetik:tetik + 13]
        enyuksek = float(ileri.h.max())
        endusuk = float(ileri.l.min())
        stop_oldu = endusuk <= stop
        en_iyi_r = (enyuksek - giris) / risk
        kutu(fig, yerel - 0.45, yerel + 0.45, s_l, s_h, TURUNCU, a=0.22, cizgi=1.3,
             row=2, col=1)
        yatay(fig, giris, yerel - 0.4, tetik + 13, renk=MAVI, dash="solid", w=1.4,
              row=2, col=1)
        yatay(fig, stop, yerel - 0.4, tetik + 13, renk=BORDO, dash="dot", w=1.3,
              row=2, col=1)
        not_(fig, yerel, s_h + t2 * 2,
             f"{etiket} · kusursuz boğa trend barı<br>tepede kapanış — 'güzel' sinyal",
             renk=TURUNCU, ok=True, ax=-58 if etiket == "C" else 30, ay=-48,
             boyut=10, row=2, col=1)
        not_(fig, min(tetik + 10, len(zayif) - 1), endusuk,
             f"{etiket} · giriş doldu, stop ({stop:.0f}) yendi<br>"
             f"gördüğü en iyi kâr {en_iyi_r:.2f}R",
             renk=BORDO, ok=True, ax=26, ay=44 if etiket == "C" else 86,
             boyut=10, row=2, col=1)
        kaybeden.append(dict(etiket=etiket, yerel_bar=yerel, gun_bari=14 + yerel,
                             govde=round(float(zayif.c[yerel] - zayif.o[yerel]), 1),
                             giris=round(giris, 1), stop=round(stop, 1), risk=round(risk, 1),
                             tetik_bari=14 + tetik, stop_oldu=bool(stop_oldu),
                             en_iyi_R=round(en_iyi_r, 2),
                             tetik_sonrasi_en_dusuk=round(endusuk, 1)))
    olcumler["zayif_piyasa"] = dict(gun="2026-08-14", pencere="gün barı 14–42",
                                    sinyaller=kaybeden)
    eksen_pad(fig, zayif, .32, .30, row=2, col=1)
    zaman_ekseni(fig, zayif, 7, "%H:%M", row=2, col=1)

    lejant(fig, "çirkin ama kazanan sinyal barı", ALTIN)
    lejant(fig, "güzel ama kaybeden sinyal barı", TURUNCU)
    lejant_cizgi(fig, "giriş", MAVI, dash="solid")
    lejant_cizgi(fig, "stop", BORDO, dash="dot")
    duzen(fig, "18 · Trend gücü ↔ sinyal barı kalitesi ters ilişkisi",
          "gerçek veri · XU030 5dk · pencere indisle pinlenmiştir · "
          "paradoks: trend ne kadar güçlüyse sinyal barı o kadar kötüdür",
          y_baslik="XU030 (puan)", x_baslik="seans saati (5 dakikalık barlar)", h=980)
    kaydet(fig, "18_sinyal_kalitesi_paradoksu", olcum=olcumler)


# ==================================================================== 19
def f19():
    """İkinci giriş ilkesi (XU030 5dk — USDTRY yerine, 1 panel)."""
    d = yukle("XU030.IS", "5m")
    if d is None:
        print("  ! 19 atlandı: XU030 5dk önbellekte yok")
        return
    gun = seans(d, "2026-07-01")
    df = gun.iloc[8:47].reset_index(drop=True)      # gün barı 8–46
    h1, h2 = 24 - 8, 27 - 8                         # yerel indisler

    fig = go.Figure()
    mum_ekle(fig, df, zaman=True)
    ema_ciz(fig, df, 20, renk=GRI)
    t = tick_of(df)

    # birinci giriş — başarısız
    g1 = float(df.h[h1]) + t
    s1 = float(df.l[h1]) - t
    kutu(fig, h1 - 0.45, h1 + 0.45, float(df.l[h1]), float(df.h[h1]), TURUNCU,
         a=0.22, cizgi=1.3)
    yatay(fig, g1, h1 - 0.4, h1 + 6, renk=MAVI, dash="solid", w=1.4)
    yatay(fig, s1, h1 - 0.4, h1 + 6, renk=BORDO, dash="dot", w=1.4)
    ara = df.iloc[h1 + 1:h2 + 1]
    not_(fig, h1, float(df.h[h1]) + t * 4,
         f"① BİRİNCİ giriş — H1<br>buy stop {g1:.0f} · stop {s1:.0f}",
         renk=TURUNCU, ok=True, ax=-58, ay=-44, boyut=10)
    not_(fig, h1 + 2, float(ara.l.min()),
         f"stop yendi ({ara.l.min():.0f}) — birinci giriş BAŞARISIZ",
         renk=BORDO, ok=True, ax=-124, ay=96, boyut=10)

    # ikinci giriş — başarılı
    g2 = float(df.h[h2]) + t
    s2 = float(df.l[h2]) - t
    risk = g2 - s2
    sonra = df.iloc[h2 + 1:]
    zirve = float(sonra.h.max())
    dip = float(sonra.l.min())
    r = (zirve - g2) / risk
    kutu(fig, h2 - 0.45, h2 + 0.45, float(df.l[h2]), float(df.h[h2]), ALTIN,
         a=0.24, cizgi=1.4)
    yatay(fig, g2, h2 - 0.4, len(df) - 1, renk=MAVI, dash="solid", w=1.7)
    not_(fig, len(df) - 1, g2, f"② giriş {g2:.0f}", renk=MAVI, ok=False, boyut=10,
         xanchor="left")
    yatay(fig, s2, h2 - 0.4, len(df) - 1, renk=BORDO, dash="dot", w=1.5)
    not_(fig, len(df) - 1, s2, f"stop {s2:.0f} · risk {risk:.0f} = 1R", renk=BORDO,
         ok=False, boyut=10, xanchor="left")
    for kat in (1, 2, 4):
        y = g2 + kat * risk
        yatay(fig, y, h2 - 0.4, len(df) - 1, renk=MOR, dash="dash", w=1.2)
        not_(fig, len(df) - 1, y, f"{kat}R = {y:.0f}", renk=MOR, ok=False, boyut=9,
             xanchor="left")
    not_(fig, h2, float(df.l[h2]) - t * 5,
         "② İKİNCİ giriş — H2<br>aynı bölge, aynı yön, ikinci deneme",
         renk=ALTIN, ok=True, ax=-14, ay=52, boyut=10)
    not_(fig, int(sonra.h.idxmax()), zirve,
         f"stop hiç görülmedi (ara dip {dip:.0f} > {s2:.0f})<br>ulaşılan {r:.1f}R",
         renk=YESIL, ok=True, ax=-40, ay=-30, boyut=10)

    isaret = [(i, e) for i, e in bar_say(df, "bull") if i in (h1, h2)]
    bar_etiketle(fig, df, isaret, "bull", renk=MUREKKEP)

    lejant(fig, "birinci sinyal (başarısız)", TURUNCU)
    lejant(fig, "ikinci sinyal (başarılı)", ALTIN)
    lejant_cizgi(fig, "giriş", MAVI, dash="solid")
    lejant_cizgi(fig, "R katları", MOR)
    eksen_pad(fig, df, .12, .10)
    zaman_ekseni(fig, df, 8, "%H:%M")
    duzen(fig, "19 · İkinci giriş ilkesi",
          "gerçek veri · XU030 5dk · 1 Tem 2026 seansının 8.–46. barı (indisle pinli)"
          "<br>müfredat USDTRY 5dk istiyordu; o seri içgünde fiyat hareketi taşımadığı "
          "için temiz enstrümana alındı",
          y_baslik="XU030 (puan)", x_baslik="seans saati (5 dakikalık barlar)", h=680)
    kaydet(fig, "19_ikinci_giris", olcum=dict(
        kaynak="XU030.IS 5dk, 2026-07-01, gün barı 8–46",
        birinci_giris=dict(gun_bari=24, etiket="H1", giris=round(g1, 1),
                           stop=round(s1, 1), sonuc="stop",
                           stop_sonrasi_dip=round(float(ara.l.min()), 1)),
        ikinci_giris=dict(gun_bari=27, etiket="H2", giris=round(g2, 1),
                          stop=round(s2, 1), risk_1R=round(risk, 1),
                          ulasilan_zirve=round(zirve, 1), ulasilan_R=round(r, 1),
                          giris_sonrasi_en_dusuk=round(dip, 1))))


# ==================================================================== 20
def f20():
    """Trend teşhisi: köşeden köşeye (BIST100 günlük, 2 panel)."""
    d = yukle("XU100.IS", "1d")
    if d is None:
        print("  ! 20 atlandı: XU100 günlük önbellekte yok")
        return
    tr = dilim(d, 310, 66)     # 2025-11-13 → 2026-02-16
    bt = dilim(d, 68, 60)      # 2024-11-25 → 2025-02-18

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13, subplot_titles=(
        "Panel 1 — TREND: BIST100 günlük, indis 310–375 (13 Kas 2025 → 16 Şub 2026)",
        "Panel 2 — YATAY BANT: BIST100 günlük, indis 68–127 (25 Kas 2024 → 18 Şub 2025)"))

    olcumler = {}
    for r, (df, ad, bas_i) in enumerate([(tr, "trend", 310), (bt, "bant", 68)], start=1):
        mum_ekle(fig, df, row=r, col=1, zaman=True)
        ema_ciz(fig, df, 20, renk=GRI, row=r, col=1)
        n = len(df) - 1
        x_et = sag_oluk(fig, df, pay=0.26, sol=1.5, row=r, col=1)
        tepe, dip = float(df.h.max()), float(df.l.min())
        # köşeler: sol alt = ilk beş barın dibi, sağ üst = son beş barın tepesi
        sol_alt = float(df.l[:5].min())
        sag_ust = float(df.h[n - 4:].max())
        cizgi(fig, 0, sol_alt, n, sag_ust, renk=ALTIN, dash="dash", w=2.2, row=r, col=1)
        # pencerenin gerçek köşeleri (kutu) — çizgi bunlara varıyor mu?
        kutu(fig, -0.9, n + 0.9, dip, tepe, GRI, a=0.0, cizgi=1.1, dash="dot",
             row=r, col=1)
        net = sag_ust - sol_alt
        pencere_yuk = tepe - dip
        oran = net / pencere_yuk
        yuzde = (sag_ust / sol_alt - 1) * 100
        olcumler[ad] = dict(indis_araligi=f"{bas_i}–{bas_i+n}",
                            ilk_tarih=str(df.ts.iloc[0].date()),
                            son_tarih=str(df.ts.iloc[-1].date()),
                            sol_alt_kose=round(sol_alt), sag_ust_kose=round(sag_ust),
                            kose_kose_net=round(net),
                            kose_kose_degisim_yuzde=round(yuzde, 1),
                            pencere_dibi=round(dip), pencere_tepesi=round(tepe),
                            pencere_yuksekligi=round(pencere_yuk),
                            net_bolu_pencere=round(oran, 2))
        if ad == "trend":
            not_(fig, int(n * 0.74), sol_alt + net * 0.74,
                 f"sol ALT köşeden sağ ÜST köşeye<br>"
                 f"{sol_alt:.0f} → {sag_ust:.0f} = {net:.0f} puan, %{yuzde:.0f}",
                 renk=ALTIN, ok=True, ax=-58, ay=-58, boyut=11, row=r, col=1)
            not_(fig, x_et, dip + pencere_yuk * 0.06,
                 f"<b>net / pencere yüksekliği = {oran:.2f}</b><br>"
                 "çizgi iki köşeye de değiyor<br>→ TREND",
                 renk=TEAL, ok=False, boyut=10, xanchor="left", row=r, col=1)
            not_(fig, 3, sol_alt,
                 "trendin iki şartı: (1) sürekli aynı yöne ilerleme<br>"
                 "(2) grafiğin bir köşesinden diğerine geçiş",
                 renk=TEAL, ok=True, ax=176, ay=-42, boyut=10, row=r, col=1)
        else:
            for y, et, c, dd in ((tepe, "bant tavanı", BORDO, "dash"),
                                 (dip, "bant tabanı", BORDO, "dash"),
                                 ((tepe + dip) / 2, "bant ortası", GRI, "dot")):
                yatay(fig, y, 0, n, renk=c, dash=dd, w=1.4, row=r, col=1)
                not_(fig, x_et, y, f"{et} {y:.0f}", renk=c, ok=False, boyut=10,
                     xanchor="left", row=r, col=1)
            not_(fig, n, sag_ust,
                 f"çizgi sağ üst köşeye VARMIYOR:<br>"
                 f"{sag_ust:.0f}'te bitiyor, bant tavanı {tepe:.0f}",
                 renk=ALTIN, ok=True, ax=-96, ay=52, boyut=10, row=r, col=1)
            not_(fig, x_et, dip + pencere_yuk * 0.14,
                 f"<b>net / pencere yüksekliği = {oran:.2f}</b><br>"
                 f"net {net:.0f} puan (%{yuzde:.0f}), pencere {pencere_yuk:.0f} puan<br>"
                 "→ TREND YOK, BANT VAR",
                 renk=BORDO, ok=False, boyut=10, xanchor="left", row=r, col=1)
        eksen_pad(fig, df, .08, .12, row=r, col=1)
        zaman_ekseni(fig, df, 6, "%d %b %y", row=r, col=1)

    lejant_cizgi(fig, "köşeden köşeye çizgi", ALTIN)
    lejant_cizgi(fig, "bant sınırları", BORDO)
    lejant(fig, "pencerenin dörtgeni", GRI, a=0.0)
    duzen(fig, "20 · Trend teşhisi: köşeden köşeye",
          "gerçek veri · BIST100 (XU100) günlük · pencereler indisle pinli · nicel "
          "teşhis: köşeden köşeye net hareket / pencere yüksekliği",
          y_baslik="BIST100 (puan)", x_baslik="işlem günü (pencere içi)", h=960)
    kaydet(fig, "20_trend_teshisi", olcum=olcumler)


# ==================================================================== 21
def f21():
    """Spike fazı ve kanal fazı (XU030 5dk, 2 panel)."""
    d = yukle("XU030.IS", "5m")
    if d is None:
        print("  ! 21 atlandı: XU030 5dk önbellekte yok")
        return
    gun = seans(d, "2026-08-19")
    yakin = gun.iloc[40:97].reset_index(drop=True)

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13, subplot_titles=(
        "Panel 1 — bütün gün (XU030 5dk, 19 Ağu 2026, 97 bar): spike fazı 1.–3. bar, "
        "kanal fazı 4.–96. bar",
        "Panel 2 — kanalın yakınlaştırılması (aynı günün 40.–96. barı)"))

    # ---- panel 1
    mum_ekle(fig, gun, row=1, col=1, zaman=True)
    ema_ciz(fig, gun, 20, renk=GRI, row=1, col=1)
    t = tick_of(gun)
    spike_l = float(gun.l[1:4].min())
    spike_h = float(gun.h[1:4].max())
    kutu(fig, 0.6, 3.6, float(gun.l.min()) - t * 6, float(gun.h.max()) + t * 6,
         BORDO, a=0.10, cizgi=1.2, row=1, col=1)
    kutu(fig, 3.6, 96.6, float(gun.l.min()) - t * 6, float(gun.h.max()) + t * 6,
         TEAL, a=0.07, cizgi=1.2, row=1, col=1)
    not_(fig, 3, spike_h,
         f"SPIKE fazı — 3 bar<br>{spike_l:.0f} → {spike_h:.0f} = {spike_h-spike_l:.0f} puan",
         renk=BORDO, ok=True, ax=94, ay=-48, boyut=10, row=1, col=1)
    not_(fig, 55, float(gun.l.min()) + (float(gun.h.max()) - float(gun.l.min())) * 0.18,
         "KANAL fazı — 93 bar<br>aynı mesafe, otuz kat zaman",
         renk=TEAL, ok=True, ax=0, ay=44, boyut=10, row=1, col=1)
    egim = trend_cizgisi(fig, gun, (6, 87), yon="bull", renk=TEAL, dash="dash", w=1.7,
                         kanal=True, row=1, col=1)
    eksen_pad(fig, gun, .10, .10, row=1, col=1)
    zaman_ekseni(fig, gun, 9, "%H:%M", row=1, col=1)

    # ---- panel 2
    mum_ekle(fig, yakin, row=2, col=1, zaman=True)
    ema_ciz(fig, yakin, 20, renk=GRI, row=2, col=1)
    t2 = tick_of(yakin)
    egim2 = trend_cizgisi(fig, yakin, (6, 47), yon="bull", renk=TEAL, dash="dash",
                          w=1.7, kanal=True, row=2, col=1)
    isaret = [(i, e) for i, e in bar_say(yakin, "bull") if e in ("H1", "H2")][:8]
    bar_etiketle(fig, yakin, isaret, "bull", renk=MUREKKEP, row=2, col=1)
    not_(fig, 20, float(yakin.l[20]) - t2 * 6,
         "kanal içinde geri çekilmeler bir–iki bar, sığ ve örtüşmeli;<br>"
         "her H1/H2 yeni tepeye götürüyor — kanalın imzası",
         renk=TEAL, ok=True, ax=60, ay=48, boyut=10, row=2, col=1)
    not_(fig, 50, float(yakin.h.max()),
         "kanal, trend kanal çizgisine yaklaşınca<br>alıcı iştahı azalır (erozyon)",
         renk=MOR, ok=True, ax=-150, ay=44, boyut=10, row=2, col=1)
    eksen_pad(fig, yakin, .12, .16, row=2, col=1)
    zaman_ekseni(fig, yakin, 8, "%H:%M", row=2, col=1)

    lejant(fig, "spike fazı", BORDO)
    lejant(fig, "kanal fazı", TEAL)
    lejant_cizgi(fig, "trend çizgisi / trend kanal çizgisi", TEAL)
    duzen(fig, "21 · Spike fazı ve kanal fazı",
          "gerçek veri · XU030 5dk · 19 Ağu 2026 seansı (indisle pinli) · "
          "spike kısa ve sert, kanal uzun ve dirençli",
          y_baslik="XU030 (puan)", x_baslik="seans saati (5 dakikalık barlar)", h=960)
    kaydet(fig, "21_spike_ve_kanal", olcum=dict(
        kaynak="XU030.IS 5dk, 2026-08-19 seansı, 97 bar",
        spike=dict(barlar="1–3", dip=round(spike_l, 1), tepe=round(spike_h, 1),
                   yukseklik=round(spike_h - spike_l, 1)),
        kanal=dict(barlar="4–96", dip=round(float(gun.l[4:].min()), 1),
                   tepe=round(float(gun.h[4:].max()), 1),
                   yukseklik=round(float(gun.h[4:].max() - gun.l[4:].min()), 1),
                   bar_basina_egim=round(egim, 2)),
        yakin_pencere=dict(barlar="40–96", bar_basina_egim=round(egim2, 2)),
        gun_acilis=round(float(gun.o.iloc[0]), 1), gun_kapanis=round(float(gun.c.iloc[-1]), 1)))


# ==================================================================== 22
def f22():
    """Spike ve kanal trendinin dönüş hedefi (şematik, 1 panel)."""
    ohlc = [
        bar(100.00, 100.30, .15, .20), bar(100.30, 100.10, .20, .25),
        bar(100.15, 101.60, .10, .10), bar(101.60, 103.00, .12, .08),
        bar(103.00, 104.20, .15, .10),                       # 2-4 spike
        bar(104.20, 103.60, .15, .45),                       # 5 kanal başlangıcı
        bar(103.65, 104.30, .20, .25), bar(104.30, 104.10, .25, .30),
        bar(104.15, 104.90, .20, .25), bar(104.85, 105.40, .25, .20),
        bar(105.40, 105.15, .20, .35), bar(105.20, 105.85, .20, .25),
        bar(105.85, 106.40, .25, .20), bar(106.35, 106.10, .20, .35),
        bar(106.15, 106.80, .20, .25), bar(106.80, 107.30, .25, .20),
        bar(107.25, 107.05, .20, .35), bar(107.10, 107.70, .20, .25),
        bar(107.70, 108.15, .25, .20), bar(108.10, 107.90, .20, .30),
        bar(107.95, 108.45, .20, .25), bar(108.45, 108.70, .05, .20),
        bar(108.65, 108.30, .25, .35),                       # 22 kanal sonu
        bar(108.30, 107.60, .20, .15), bar(107.55, 106.70, .15, .20),
        bar(106.75, 107.10, .30, .25), bar(107.05, 106.20, .20, .25),
        bar(106.15, 105.20, .15, .20), bar(105.20, 104.40, .15, .25),
        bar(104.35, 103.60, .20, .20), bar(103.55, 103.30, .20, .35),
        bar(103.35, 104.10, .25, .20),
    ]
    df = df_yap(ohlc)
    fig = go.Figure()
    mum_ekle(fig, df)
    t = tick_of(df)

    spike_l = float(df.l[2])
    spike_h = float(df.h[4])
    spike_boy = spike_h - spike_l
    mm = spike_h + spike_boy
    kanal_bas = float(df.l[5])
    kanal_tepe = float(df.h[21])

    kutu(fig, 1.55, 4.5, spike_l - t * 4, spike_h + t * 4, BORDO, a=0.14, cizgi=1.3)
    not_(fig, 3, spike_l - t * 6, f"SPIKE {spike_l:.2f} → {spike_h:.2f} = {spike_boy:.2f}",
         renk=BORDO, ok=True, ax=-24, ay=44, boyut=10)
    kutu(fig, 4.5, 22.5, kanal_bas - t * 4, kanal_tepe + t * 4, TEAL, a=0.09, cizgi=1.2)
    not_(fig, 12, kanal_bas + (kanal_tepe - kanal_bas) * 0.15,
         "KANAL — sığ geri çekilmeler, yavaş ilerleme", renk=TEAL, ok=True,
         ax=0, ay=52, boyut=10)
    trend_cizgisi(fig, df, (5, 19), yon="bull", uzat=23, renk=TEAL, dash="dash",
                  w=1.6, kanal=True, kanal_nokta=21)

    yatay(fig, mm, 4, 31, renk=MOR, dash="dash", w=1.6)
    not_(fig, 31, mm, f"spike tabanlı MM hedefi {mm:.2f}", renk=MOR, ok=False,
         boyut=10, xanchor="left")
    cizgi(fig, 4.15, spike_h, 4.15, mm, renk=MOR, w=2.4)
    not_(fig, 21, kanal_tepe,
         f"kanal, MM hedefinin ({mm:.2f}) hemen altında bitti — {kanal_tepe:.2f}",
         renk=MOR, ok=True, ax=-70, ay=-34, boyut=10)

    yatay(fig, kanal_bas, 5, 31, renk=ALTIN, dash="dash", w=1.8)
    not_(fig, 31, kanal_bas, f"kanal BAŞLANGICI {kanal_bas:.2f}", renk=ALTIN,
         ok=False, boyut=10, xanchor="left")
    fig.add_annotation(x=29.6, y=kanal_bas, ax=22.6, ay=kanal_tepe, xref="x", yref="y",
                       axref="x", ayref="y", showarrow=True, arrowhead=2, arrowsize=1.1,
                       arrowwidth=2.4, arrowcolor=TURUNCU)
    not_(fig, 31.8, (kanal_bas + kanal_tepe) / 2 + 0.9,
         "spike–kanal trendinin OLAĞAN sonu:<br>"
         "kanal biter, fiyat kanalın<br>başlangıcına döner",
         renk=TURUNCU, ok=False, boyut=11, xanchor="left")
    not_(fig, 30, float(df.l[30]),
         f"dönüş kanal başlangıcını {kanal_bas - float(df.l[30]):.2f} aştı",
         renk=TURUNCU, ok=True, ax=-10, ay=44, boyut=10)

    lejant(fig, "spike fazı", BORDO)
    lejant(fig, "kanal fazı", TEAL)
    lejant_cizgi(fig, "kanal başlangıcı", ALTIN)
    lejant_cizgi(fig, "spike tabanlı ölçülmüş hareket", MOR)
    eksen_pad(fig, df, .14, .12)
    duzen(fig, "22 · Spike ve kanal trendinin dönüş hedefi",
          "kanal bir bayraktır: kırıldığında ilk mıknatıs kanalın başladığı yerdir",
          h=680, sematik=True)
    kaydet(fig, "22_spike_kanal_donus_hedefi", olcum=dict(
        spike_dip=round(spike_l, 2), spike_tepe=round(spike_h, 2),
        spike_boyu=round(spike_boy, 2), mm_hedefi=round(mm, 2),
        kanal_baslangici=round(kanal_bas, 2), kanal_tepesi=round(kanal_tepe, 2),
        kanal_bar_sayisi=18, spike_bar_sayisi=3,
        donus_dibi=round(float(df.l[30]), 2),
        kanal_baslangicini_asma=round(kanal_bas - float(df.l[30]), 2)))


# ==================================================================== 23
def f23():
    """Sıkı kanal vs geniş kanal vs mikro kanal (şematik, 3 panel)."""
    siki = df_yap([
        bar(100.00, 100.55, .12, .12), bar(100.55, 100.45, .12, .18),
        bar(100.48, 101.00, .12, .12), bar(101.00, 101.45, .14, .12),
        bar(101.45, 101.30, .10, .18), bar(101.32, 101.85, .12, .12),
        bar(101.85, 102.30, .14, .10), bar(102.28, 102.15, .10, .20),
        bar(102.18, 102.70, .12, .12), bar(102.70, 103.15, .14, .10),
        bar(103.15, 103.00, .10, .18), bar(103.02, 103.55, .12, .12),
        bar(103.55, 104.00, .14, .10), bar(104.00, 103.85, .10, .20),
        bar(103.88, 104.40, .12, .12), bar(104.40, 104.85, .14, .10),
        bar(104.85, 104.70, .12, .18), bar(104.72, 105.25, .14, .10)])
    genis = df_yap([
        bar(100.00, 101.20, .20, .20), bar(101.20, 102.10, .25, .20),
        bar(102.10, 101.40, .20, .35), bar(101.35, 100.75, .25, .30),
        bar(100.80, 101.55, .30, .25), bar(101.55, 102.60, .25, .20),
        bar(102.60, 103.30, .30, .20), bar(103.25, 102.40, .20, .35),
        bar(102.35, 101.85, .30, .40), bar(101.90, 102.75, .30, .25),
        bar(102.75, 103.60, .25, .20), bar(103.60, 104.35, .30, .20),
        bar(104.30, 103.55, .25, .35), bar(103.50, 102.95, .30, .40),
        bar(103.00, 103.60, .30, .25), bar(103.60, 104.10, .25, .20),
        bar(104.10, 104.55, .30, .20), bar(104.50, 103.90, .25, .35)])
    mikro = df_yap([
        bar(99.60, 99.80, .15, .20), bar(99.80, 99.65, .15, .25),
        bar(99.70, 100.00, .10, .15),
        bar(100.00, 100.35, .06, .05), bar(100.35, 100.72, .06, .04),
        bar(100.72, 101.05, .05, .05), bar(101.05, 101.42, .06, .04),
        bar(101.42, 101.75, .05, .05), bar(101.75, 102.10, .06, .04),
        bar(102.10, 102.44, .05, .05), bar(102.44, 102.80, .06, .04),
        bar(102.80, 103.12, .05, .05), bar(103.12, 103.48, .06, .04),
        bar(103.48, 103.80, .05, .05), bar(103.80, 104.18, .06, .04),
        bar(104.18, 103.90, .10, .25), bar(103.85, 104.30, .15, .20)])

    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.09, subplot_titles=(
        "Panel 1 — SIKI kanal: geri çekilmeler bir bar, çizgiler dar",
        "Panel 2 — GENİŞ kanal: geri çekilmeler üç–dört bar, örtüşme bol",
        "Panel 3 — MİKRO kanal: geri çekilme YOK, her barın düşüğü bir öncekinin üstünde"))

    olcumler = {}

    # panel 1
    mum_ekle(fig, siki, row=1, col=1)
    trend_cizgisi(fig, siki, (1, 13), yon="bull", renk=TEAL, dash="dash", w=1.6,
                  kanal=True, kanal_nokta=15, row=1, col=1)
    gc1_ust, gc1_alt = float(siki.h[6]), float(siki.l[7])
    olcu(fig, 7.75, gc1_alt, gc1_ust, f"en büyük geri çekilme {gc1_ust-gc1_alt:.2f}",
         renk=TURUNCU, row=1, col=1)
    not_(fig, 3, float(siki.l.min()),
         "geri çekilme 1 bar · her bar bir öncekinin gövdesini kısmen örtüyor · "
         "karşı bahis yasak", renk=TEAL, ok=True, ax=150, ay=34, boyut=10, row=1, col=1)
    olcumler["siki_kanal"] = dict(bar_sayisi=len(siki),
                                  en_buyuk_geri_cekilme=round(gc1_ust - gc1_alt, 2),
                                  geri_cekilme_bar_sayisi=1,
                                  toplam_hareket=round(float(siki.h.max() - siki.l.min()), 2))
    eksen_pad(fig, siki, .16, .14, row=1, col=1)

    # panel 2
    mum_ekle(fig, genis, row=2, col=1)
    trend_cizgisi(fig, genis, (3, 13), yon="bull", renk=TEAL, dash="dash", w=1.6,
                  kanal=True, kanal_nokta=16, row=2, col=1)
    gc2_ust, gc2_alt = float(genis.h[6]), float(genis.l[8])
    olcu(fig, 8.8, gc2_alt, gc2_ust, f"geri çekilme {gc2_ust-gc2_alt:.2f}",
         renk=TURUNCU, row=2, col=1)
    gc3_ust, gc3_alt = float(genis.h[11]), float(genis.l[13])
    olcu(fig, 13.8, gc3_alt, gc3_ust, f"geri çekilme {gc3_ust-gc3_alt:.2f}",
         renk=TURUNCU, row=2, col=1)
    not_(fig, 4, float(genis.l.min()),
         "geri çekilmeler sıkı kanalın dört katı: iki yönlü işlem var, "
         "karşı bahis meşru", renk=TURUNCU, ok=True, ax=140, ay=32, boyut=10,
         row=2, col=1)
    olcumler["genis_kanal"] = dict(bar_sayisi=len(genis),
                                   geri_cekilme_1=round(gc2_ust - gc2_alt, 2),
                                   geri_cekilme_2=round(gc3_ust - gc3_alt, 2),
                                   geri_cekilme_bar_sayisi=3,
                                   toplam_hareket=round(float(genis.h.max() - genis.l.min()), 2))
    eksen_pad(fig, genis, .14, .12, row=2, col=1)

    # panel 3
    mum_ekle(fig, mikro, row=3, col=1)
    cizgi(fig, 3, float(mikro.l[3]), 14, float(mikro.l[14]), renk=TEAL, dash="dash",
          w=1.8, row=3, col=1)
    cizgi(fig, 3, float(mikro.h[3]), 14, float(mikro.h[14]), renk=TEAL, dash="dot",
          w=1.6, row=3, col=1)
    ardisik = 12
    kutu(fig, 2.6, 14.4, float(mikro.l[3]) - 0.12, float(mikro.h[14]) + 0.12,
         ALTIN, a=0.06, cizgi=1.2, row=3, col=1)
    not_(fig, 6, float(mikro.h[6]),
         f"{ardisik} ardışık boğa barı — hiçbirinin düşüğü bir öncekinin altında değil;<br>"
         "mikro trend çizgisi her barın düşüğüne değiyor",
         renk=ALTIN, ok=True, ax=40, ay=-74, boyut=10, row=3, col=1)
    not_(fig, 15, float(mikro.l[15]),
         "ilk geri çekilme: mikro kanalın kırılması<br>= ilk gerçek sinyal",
         renk=TURUNCU, ok=True, ax=-96, ay=58, boyut=10, row=3, col=1)
    olcumler["mikro_kanal"] = dict(ardisik_bar=ardisik, geri_cekilme=0.0,
                                   toplam_hareket=round(float(mikro.h[14] - mikro.l[3]), 2),
                                   ilk_geri_cekilme_bari=15)
    eksen_pad(fig, mikro, .26, .24, row=3, col=1)

    lejant_cizgi(fig, "trend çizgisi", TEAL)
    lejant_cizgi(fig, "trend kanal çizgisi", TEAL, dash="dot")
    lejant_cizgi(fig, "geri çekilme ölçüsü", TURUNCU)
    duzen(fig, "23 · Sıkı kanal · geniş kanal · mikro kanal",
          "üçü de kanaldır; ayrım geri çekilmenin BOYU ve bar sayısıdır — "
          "işlem üslubunu bu ayrım belirler",
          h=1180, sematik=True)
    kaydet(fig, "23_kanal_aileleri", olcum=olcumler)


# ==================================================================== 24
def f24():
    """Kanal = bayrak: boğa kanalı bir ayı bayrağıdır (XAUUSD 15dk, 2 panel)."""
    d = yukle("GC=F", "15m")
    if d is None:
        print("  ! 24 atlandı: GC=F 15dk önbellekte yok")
        return
    kanal = dilim(d, 286, 50)     # indis 286–335
    kirilim = dilim(d, 318, 32)   # indis 318–349

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13, subplot_titles=(
        "Panel 1 — yükselen kanal (XAUUSD/GC vadeli 15dk, indis 286–335, 17 Haz 2026)",
        "Panel 2 — kırılım aşağı ve ölçülmüş hareket (aynı seri, indis 318–349)"))

    # ---- panel 1
    mum_ekle(fig, kanal, row=1, col=1, zaman=True)
    ema_ciz(fig, kanal, 20, renk=GRI, row=1, col=1)
    t = tick_of(kanal)
    x_et1 = sag_oluk(fig, kanal, pay=0.20, sol=1.2, row=1, col=1)
    dip_y = 295 - 286      # 9
    tepe_y = 331 - 286     # 45
    kir_y = 332 - 286      # 46
    kanal_dip = float(kanal.l[dip_y])
    kanal_tepe = float(kanal.h[tepe_y])
    yukseklik = kanal_tepe - kanal_dip
    trend_cizgisi(fig, kanal, (dip_y, 326 - 286), yon="bull", uzat=len(kanal) - 1,
                  renk=TEAL, dash="dash", w=1.7, kanal=True, kanal_nokta=317 - 286,
                  row=1, col=1)
    yatay(fig, kanal_dip, 0, x_et1 - 0.4, renk=ALTIN, dash="dash", w=1.5, row=1, col=1)
    yatay(fig, kanal_tepe, 0, x_et1 - 0.4, renk=ALTIN, dash="dash", w=1.5, row=1, col=1)
    olcu(fig, x_et1 + 0.8, kanal_dip, kanal_tepe,
         f"kanal yüksekliği<br>{yukseklik:.1f}", renk=MOR, row=1, col=1)
    not_(fig, 24, kanal_dip + yukseklik * 0.15,
         "yükselen kanal — boğaların gözünde bir boğa trendi;<br>"
         "Brooks'un gözünde bir AYI BAYRAĞI",
         renk=TEAL, ok=True, ax=0, ay=44, boyut=11, row=1, col=1)
    not_(fig, kir_y, float(kanal.c[kir_y]),
         "kanal aşağı kırıldı — bayrak açıldı", renk=BORDO, ok=True, ax=-46, ay=-24,
         boyut=10, row=1, col=1)
    eksen_pad(fig, kanal, .10, .10, row=1, col=1)
    zaman_ekseni(fig, kanal, 8, "%d %b %H:%M", row=1, col=1)

    # ---- panel 2
    mum_ekle(fig, kirilim, row=2, col=1, zaman=True)
    t2 = tick_of(kirilim)
    x_et2 = sag_oluk(fig, kirilim, pay=0.34, sol=1.2, row=2, col=1)
    k_dip = 0  # yerel referanslar
    yerel_tepe = 331 - 318
    yerel_kir = 332 - 318
    mm = kanal_dip - yukseklik
    dip_ulasilan = float(kirilim.l.min())
    dip_bari = int(kirilim.l.idxmin())
    yatay(fig, kanal_dip, 0, x_et2 - 0.3, renk=ALTIN, dash="dash", w=1.6,
          row=2, col=1)
    not_(fig, x_et2, kanal_dip, f"kanal tabanı {kanal_dip:.1f}<br>= kırılım noktası",
         renk=ALTIN, ok=False, boyut=10, xanchor="left", row=2, col=1)
    yatay(fig, kanal_tepe, 0, yerel_kir, renk=ALTIN, dash="dot", w=1.3, row=2, col=1)
    yatay(fig, mm, 0, x_et2 - 0.3, renk=MOR, dash="dash", w=1.8, row=2, col=1)
    not_(fig, x_et2, mm,
         f"MM hedefi {mm:.1f}<br>= {kanal_dip:.1f} − {yukseklik:.1f}", renk=MOR,
         ok=False, boyut=10, xanchor="left", row=2, col=1)
    cizgi(fig, 1.2, kanal_dip, 1.2, mm, renk=MOR, w=2.6, row=2, col=1)
    kutu(fig, yerel_kir - 0.45, yerel_kir + 0.45, float(kirilim.l[yerel_kir]),
         float(kirilim.h[yerel_kir]), BORDO, a=0.22, cizgi=1.4, row=2, col=1)
    not_(fig, yerel_kir, float(kirilim.l[yerel_kir]),
         "kırılım barı: tıraşlı ayı trend barı,<br>kanalın tamamını tek barda yutuyor",
         renk=BORDO, ok=True, ax=-196, ay=66, boyut=10, row=2, col=1)
    not_(fig, dip_bari, dip_ulasilan,
         f"MM hedefi aşıldı: {dip_ulasilan:.1f} (hedef {mm:.1f})",
         renk=YESIL, ok=True, ax=88, ay=-44, boyut=10, row=2, col=1)
    eksen_pad(fig, kirilim, .16, .08, row=2, col=1)
    zaman_ekseni(fig, kirilim, 7, "%d %b %H:%M", row=2, col=1)

    lejant_cizgi(fig, "kanal sınırları", ALTIN)
    lejant_cizgi(fig, "trend çizgisi / kanal çizgisi", TEAL)
    lejant_cizgi(fig, "ölçülmüş hareket hedefi", MOR)
    duzen(fig, "24 · Kanal = bayrak: boğa kanalı bir ayı bayrağıdır",
          "gerçek veri · XAUUSD (GC vadeli) 15dk · pencere indisle pinli · müfredattaki "
          "USDTRY 5dk yerine (o seri içgünde fiyat hareketi taşımıyor)",
          y_baslik="XAUUSD (USD)", x_baslik="tarih ve saat (15 dakikalık barlar)", h=980)
    kaydet(fig, "24_kanal_bayrak", olcum=dict(
        kaynak="GC=F 15dk, indis 286–349 (17–18 Haz 2026)",
        kanal_dibi=round(kanal_dip, 1), kanal_tepesi=round(kanal_tepe, 1),
        kanal_yuksekligi=round(yukseklik, 1), kanal_bar_sayisi=tepe_y - dip_y + 1,
        kirilim_bari_indis=332,
        kirilim_bari_govde=round(float(d.c[332] - d.o[332]), 1),
        mm_hedefi=round(mm, 1), ulasilan_dip=round(dip_ulasilan, 1),
        hedef_asildi=bool(dip_ulasilan <= mm)))


# ==================================================================== 25
def f25():
    """Trend çizgisi çizim yöntemleri (şematik, 1 panel).

    Dipler BİLEREK içbükey (yavaşlayan) kuruldu: ancak böyle üç FARKLI eğimde,
    üçü de geçerli (aralarındaki hiçbir dip çizgiyi delmeyen) trend çizgisi
    çizilebilir. Eğimler ve kırılma sıraları koddan hesaplanır; metne elle sayı
    yazılmaz.
    """
    ohlc = [
        bar(100.20, 100.90, .20, .25), bar(100.90, 100.35, .20, .35),
        bar(100.35, 101.05, .15, .55),                       # 2  majör dip 1
        bar(101.05, 101.75, .25, .20), bar(101.75, 102.30, .30, .20),
        bar(102.30, 101.10, .15, .80),                       # 5  tek spike
        bar(101.15, 102.05, .25, .25), bar(102.05, 102.60, .30, .20),
        bar(102.55, 101.90, .20, .30),                       # 8  majör dip 2
        bar(102.00, 102.80, .25, .05), bar(102.80, 103.40, .30, .20),
        bar(103.40, 103.90, .25, .25), bar(103.85, 103.20, .20, .30),
        bar(103.25, 103.85, .30, .10),
        bar(103.85, 103.60, .25, .20),                       # 14 majör dip 3
        bar(103.75, 104.30, .25, .00), bar(104.30, 104.75, .25, .25),
        bar(104.70, 104.35, .20, .00),
        bar(104.45, 104.95, .25, .05),                       # 18 majör dip 4
        bar(104.95, 105.45, .30, .20), bar(105.40, 105.80, .25, .25),
        bar(105.75, 105.10, .20, .20),                       # 21
        bar(105.15, 105.70, .25, .20), bar(105.70, 106.20, .30, .20),
        bar(106.15, 105.60, .20, .25), bar(105.65, 106.40, .30, .25),
    ]
    df = df_yap(ohlc)
    fig = go.Figure()
    mum_ekle(fig, df)
    n = len(df) - 1

    def cizim(i, j, renk, no, aciklama):
        yi, yj = float(df.l[i]), float(df.l[j])
        e = (yj - yi) / (j - i)
        cizgi(fig, i, yi, n, yi + e * (n - i), renk=renk, dash="dash", w=1.9)
        # ilk kırılma: çizginin ALTINA kapanan değil, düşüğü altına inen ilk bar
        kir = next((k for k in range(j + 1, len(df))
                    if float(df.l[k]) < yi + e * (k - i)), None)
        lejant_cizgi(fig, f"{no} dip {i}–{j} · eğim {e:.3f}/bar · {aciklama}", renk)
        return e, kir

    e1, k1 = cizim(14, 18, BORDO, "①", "en son iki majör dip")
    e2, k2 = cizim(2, 18, TEAL, "②", "ilk dipten son dibe (tek spike yok sayılır)")
    e3, k3 = cizim(8, 14, MOR, "③", "ortadaki iki majör dip")

    for i, et, ay_ in ((2, "majör dip 1", 62), (8, "majör dip 2", 34),
                       (14, "majör dip 3", 34), (18, "majör dip 4", 34)):
        not_(fig, i, float(df.l[i]), et, renk=MUREKKEP, ok=True, ax=0, ay=ay_, boyut=9)
    not_(fig, 5, float(df.l[5]),
         "tek spike — Brooks bunu yok saymayı meşru sayar;<br>"
         "② çizgisi yalnızca bu barın altından geçmiyor",
         renk=TURUNCU, ok=True, ax=64, ay=112, boyut=10)

    sira = sorted([(k, no, e) for k, no, e in
                   ((k1, "①", e1), (k2, "②", e2), (k3, "③", e3)) if k is not None])
    if sira:
        ilk_k, ilk_no, ilk_e = sira[0]
        kutu(fig, ilk_k - 0.5, ilk_k + 0.5, float(df.l[ilk_k]), float(df.h[ilk_k]),
             ALTIN, a=0.22, cizgi=1.3)
        not_(fig, ilk_k, float(df.l[ilk_k]),
             f"ilk kırılan {ilk_no} — en DİK çizgi (eğim {ilk_e:.3f})<br>bar {ilk_k}",
             renk=ALTIN, ok=True, ax=54, ay=66, boyut=10)

    not_(fig, 9.6, 99.05,
         "Aynı veri, üç geçerli çizim: hiçbirinin altına aradaki dipler inmiyor "
         "(② yalnızca tek spike'ı yok sayıyor).<br>"
         "Üçü de işleme değer. Fark eğimdedir: en dik çizgi ilk kırılır ve en erken "
         "sinyali verir;<br>en sığ çizgi en geç kırılır ama kırıldığında olay daha "
         "büyüktür. Önemli olan hangi çizgi değil, kırılımın MOMENTUMU'dur.",
         renk=MUREKKEP, ok=False, boyut=10, xanchor="left")

    fig.update_yaxes(range=[98.05, 107.4])
    fig.update_xaxes(range=[-1.2, 26.5])
    duzen(fig, "25 · Trend çizgisi çizim yöntemleri",
          "aynı veri, üç geçerli çizim — trend çizgisi bir gerçek değil, bir araçtır",
          h=700, sematik=True, legend_y=-0.18)
    kaydet(fig, "25_trend_cizgisi_yontemleri", olcum=dict(
        cizgi_1=dict(dipler=[14, 18], egim=round(e1, 3), ilk_kirilma_bari=k1,
                     dip_degerleri=[round(float(df.l[14]), 2), round(float(df.l[18]), 2)]),
        cizgi_2=dict(dipler=[2, 18], egim=round(e2, 3), ilk_kirilma_bari=k2,
                     dip_degerleri=[round(float(df.l[2]), 2), round(float(df.l[18]), 2)]),
        cizgi_3=dict(dipler=[8, 14], egim=round(e3, 3), ilk_kirilma_bari=k3,
                     dip_degerleri=[round(float(df.l[8]), 2), round(float(df.l[14]), 2)]),
        en_dik="③", ilk_kirilan=sira[0][1] if sira else None,
        yoksayilan_spike_bari=5, spike_dibi=round(float(df.l[5]), 2)))


# ==================================================================== 26
def f26():
    """Trend kanal çizgisi aşımı ve dönüş (XAUUSD 15dk, 2 panel)."""
    d = yukle("GC=F", "15m")
    if d is None:
        print("  ! 26 atlandı: GC=F 15dk önbellekte yok")
        return
    bas = 3003
    df = dilim(d, bas, 40)          # indis 3003–3042
    A, B, C = 3006 - bas, 3019 - bas, 3028 - bas        # 3, 16, 25
    H1, H2 = 3031 - bas, 3032 - bas                     # 28, 29
    DIP = 3036 - bas                                    # 33

    a_y = float(df.l[A])
    b_y = float(df.h[B])
    c_y = float(df.l[C])
    mm = c_y + (b_y - a_y)
    asim_h = float(df.h[H2])
    donus_dip = float(df.l[DIP])

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13, subplot_titles=(
        "Panel 1 — trend kanal çizgisi aşımı ve dönüş barı "
        "(XAUUSD/GC vadeli 15dk, indis 3003–3042, 30 Tem 2026)",
        "Panel 2 — aynı bölgenin ölçülmüş hareketi: aşım tam MM hedefinde oldu"))

    # ---- panel 1
    mum_ekle(fig, df, row=1, col=1, zaman=True)
    ema_ciz(fig, df, 20, renk=GRI, row=1, col=1)
    t = tick_of(df)
    # trend çizgisi: A ve C diplerinden
    e_tc = (c_y - a_y) / (C - A)
    cizgi(fig, A, a_y, len(df) - 1, a_y + e_tc * (len(df) - 1 - A), renk=TEAL,
          dash="dash", w=1.7, row=1, col=1)
    # trend kanal çizgisi: 3010 ve 3019 tepelerinden
    K1, K2 = 3010 - bas, B
    k1_y, k2_y = float(df.h[K1]), float(df.h[K2])
    e_kk = (k2_y - k1_y) / (K2 - K1)
    kk = lambda x: k1_y + e_kk * (x - K1)               # noqa: E731
    cizgi(fig, K1, k1_y, len(df) - 1, kk(len(df) - 1), renk=MOR, dash="dot", w=1.8,
          row=1, col=1)
    asim = asim_h - kk(H2)
    kutu(fig, H1 - 0.45, H2 + 0.45, kk(H1), asim_h, TURUNCU, a=0.20, cizgi=1.3,
         row=1, col=1)
    not_(fig, H2, asim_h,
         f"AŞIM: iki bar trend kanal çizgisini deldi<br>"
         f"tepe {asim_h:.1f}, çizgi {kk(H2):.1f} → {asim:.1f} puan aşım",
         renk=TURUNCU, ok=True, ax=-206, ay=30, boyut=10, row=1, col=1)
    kutu(fig, H2 - 0.45, H2 + 0.45, float(df.l[H2]), float(df.h[H2]), BORDO, a=0.22,
         cizgi=1.4, row=1, col=1)
    not_(fig, H2, float(df.l[H2]) - t * 5,
         f"dönüş barı: üst kuyruk {asim_h - max(float(df.o[H2]), float(df.c[H2])):.1f}, "
         f"kapanış dipte", renk=BORDO, ok=True, ax=46, ay=44, boyut=10, row=1, col=1)
    not_(fig, DIP, donus_dip,
         f"dönüş trend çizgisine kadar: {asim_h:.1f} → {donus_dip:.1f} "
         f"= {asim_h - donus_dip:.1f} puan",
         renk=BORDO, ok=True, ax=54, ay=36, boyut=10, row=1, col=1)
    eksen_pad(fig, df, .10, .18, row=1, col=1)
    zaman_ekseni(fig, df, 7, "%d %b %H:%M", row=1, col=1)

    # ---- panel 2
    mum_ekle(fig, df, row=2, col=1, zaman=True)
    x_et2 = sag_oluk(fig, df, pay=0.16, sol=1.5, row=2, col=1)
    for x, y, et, renk in ((A, a_y, "A", TEAL), (B, b_y, "B", TEAL), (C, c_y, "C", TEAL)):
        not_(fig, x, y, et, renk=renk, ok=True, ax=0,
             ay=(30 if et != "B" else -30), boyut=12, row=2, col=1)
    cizgi(fig, A, a_y, B, b_y, renk=TEAL, dash="dot", w=1.6, row=2, col=1)
    cizgi(fig, B, b_y, C, c_y, renk=TEAL, dash="dot", w=1.6, row=2, col=1)
    olcu(fig, A - 0.9, a_y, b_y, f"bacak AB = {b_y - a_y:.1f}", renk=MOR, yan="sag",
         row=2, col=1)
    olcu(fig, x_et2 + 0.4, c_y, mm, f"C + AB<br>= {mm:.1f}", renk=MOR, yan="sag",
         row=2, col=1)
    yatay(fig, mm, C, x_et2, renk=MOR, dash="dash", w=1.9, row=2, col=1)
    not_(fig, H1, float(df.h[H1]),
         f"hedefe varan bar: tepe {float(df.h[H1]):.1f} — hedef {mm:.1f}<br>"
         f"fark {float(df.h[H1]) - mm:+.1f} puan",
         renk=YESIL, ok=True, ax=-118, ay=-46, boyut=10, row=2, col=1)
    not_(fig, H2, asim_h,
         f"sonraki bar hedefi {asim_h - mm:.1f} puan aştı ve döndü —<br>"
         "mıknatısa varış + kanal çizgisi aşımı aynı barda",
         renk=TURUNCU, ok=True, ax=132, ay=-38, boyut=10, row=2, col=1)
    eksen_pad(fig, df, .10, .28, row=2, col=1)
    zaman_ekseni(fig, df, 7, "%d %b %H:%M", row=2, col=1)

    lejant_cizgi(fig, "trend çizgisi", TEAL)
    lejant_cizgi(fig, "trend kanal çizgisi", MOR, dash="dot")
    lejant(fig, "aşım bölgesi", TURUNCU)
    lejant(fig, "dönüş barı", BORDO)
    duzen(fig, "26 · Trend kanal çizgisi aşımı ve dönüş",
          "gerçek veri · XAUUSD (GC vadeli) 15dk · pencere indisle pinli · "
          "aşım tek başına dönüş değildir; dönüş barıyla birlikte anlam kazanır",
          y_baslik="XAUUSD (USD)", x_baslik="tarih ve saat (15 dakikalık barlar)", h=980)
    kaydet(fig, "26_kanal_cizgisi_asimi", olcum=dict(
        kaynak="GC=F 15dk, indis 3003–3042 (30 Tem 2026)",
        A_indis=3006, A=round(a_y, 1), B_indis=3019, B=round(b_y, 1),
        C_indis=3028, C=round(c_y, 1),
        bacak_AB=round(b_y - a_y, 1), mm_hedefi=round(mm, 1),
        hedefe_varan_bar_indis=3031, hedefe_varan_tepe=round(float(df.h[H1]), 1),
        hedef_sapmasi=round(float(df.h[H1]) - mm, 1),
        asim_bari_indis=3032, asim_tepesi=round(asim_h, 1),
        kanal_cizgisi_degeri=round(kk(H2), 1), asim_puan=round(asim, 1),
        donus_dibi_indis=3036, donus_dibi=round(donus_dip, 1),
        donus_boyu=round(asim_h - donus_dip, 1)))


# ==================================================================== 27
def f27():
    """Düello çizgileri (şematik, 1 panel)."""
    ohlc = [
        bar(101.80, 103.90, .30, .35), bar(103.90, 104.30, .30, .25),
        bar(104.25, 103.20, .20, .40), bar(103.15, 101.60, .20, .60),
        bar(101.65, 102.80, .30, .25), bar(102.80, 103.75, .35, .25),
        bar(103.70, 102.60, .25, .35), bar(102.55, 101.95, .25, .50),
        bar(102.00, 102.90, .30, .25), bar(102.90, 103.40, .30, .25),
        bar(103.35, 102.70, .20, .35), bar(102.65, 102.20, .25, .30),
        bar(102.25, 102.85, .25, .20), bar(102.85, 103.10, .25, .20),
        bar(103.05, 102.65, .20, .25), bar(102.60, 102.50, .20, .20),
        bar(102.55, 102.85, .15, .15), bar(102.85, 102.90, .15, .15),
        bar(102.88, 102.75, .12, .15), bar(102.78, 102.95, .07, .05),
        bar(102.98, 104.10, .15, .10), bar(104.10, 104.90, .20, .15),
        bar(104.85, 105.60, .25, .20), bar(105.55, 106.20, .30, .25),
    ]
    df = df_yap(ohlc)
    fig = go.Figure()
    mum_ekle(fig, df)
    n = len(df) - 1
    t = tick_of(df)
    x_et = sag_oluk(fig, df, pay=0.30, sol=1.2)

    # ayı trend çizgisi: alçalan tepeler (1, 13)
    i1, i2 = 1, 13
    y1, y2 = float(df.h[i1]), float(df.h[i2])
    e_ayi = (y2 - y1) / (i2 - i1)
    cizgi(fig, i1, y1, n, y1 + e_ayi * (n - i1), renk=BORDO, dash="dash", w=2.0)
    # boğa trend kanal çizgisi (yükselen dipler): (3, 15)
    j1, j2 = 3, 15
    z1, z2 = float(df.l[j1]), float(df.l[j2])
    e_boga = (z2 - z1) / (j2 - j1)
    cizgi(fig, j1, z1, n, z1 + e_boga * (n - j1), renk=TEAL, dash="dash", w=2.0)

    # kesişim
    x_k = ((y1 - e_ayi * i1) - (z1 - e_boga * j1)) / (e_boga - e_ayi)
    y_k = z1 + e_boga * (x_k - j1)
    fig.add_trace(go.Scatter(x=[x_k], y=[y_k], mode="markers", showlegend=False,
                             marker=dict(size=15, symbol="x", color=ALTIN,
                                         line=dict(color=MUREKKEP, width=1.2))))
    not_(fig, x_k, y_k, f"DÜELLO NOKTASI — bar {x_k:.1f}, {y_k:.2f}<br>"
         "iki çizgi kesişiyor: piyasanın gidecek yeri kalmadı",
         renk=ALTIN, ok=True, ax=-176, ay=-118, boyut=11)

    for i, (et, renk) in [(1, ("alçalan tepeler → AYI TREND ÇİZGİSİ", BORDO)),
                          (3, ("yükselen dipler → aynı ayı hareketinin<br>"
                               "TREND KANAL ÇİZGİSİ", TEAL))]:
        y = float(df.h[i]) if renk == BORDO else float(df.l[i])
        not_(fig, i, y, et, renk=renk, ok=True, ax=96, ay=-34 if renk == BORDO else 40,
             boyut=10)

    giris = float(df.h[19]) + t
    stop = float(df.l[18]) - t
    risk = giris - stop
    yatay(fig, giris, 18.5, x_et - 0.3, renk=MAVI, dash="solid", w=1.8)
    not_(fig, x_et, giris, f"giriş (buy stop) {giris:.2f}", renk=MAVI, ok=False,
         boyut=10, xanchor="left")
    not_(fig, 20, float(df.c[20]), "kesişimde kırılım barı", renk=MAVI, ok=True,
         ax=-40, ay=-70, boyut=10)
    yatay(fig, stop, 18.5, x_et - 0.3, renk=BORDO, dash="dot", w=1.5)
    not_(fig, x_et, stop, f"stop {stop:.2f}<br>risk {risk:.2f} = 1R", renk=BORDO,
         ok=False, boyut=10, xanchor="left")
    for kat in (1, 2, 3):
        y = giris + kat * risk
        yatay(fig, y, 18.5, x_et - 0.3, renk=MOR, dash="dash", w=1.2)
        not_(fig, x_et, y, f"{kat}R = {y:.2f}", renk=MOR, ok=False, boyut=9,
             xanchor="left")

    not_(fig, 9, 101.22,
         "iki çizgi yakınsarken barlar küçülür, kuyruklar uzar, gövdeler kaybolur — "
         "her iki tarafın da emirleri kesişim noktasında yığılır",
         renk=GRI, ok=False, boyut=10)

    lejant_cizgi(fig, "ayı trend çizgisi (tepelerden)", BORDO)
    lejant_cizgi(fig, "trend kanal çizgisi (diplerden)", TEAL)
    lejant_cizgi(fig, "giriş", MAVI, dash="solid")
    lejant_cizgi(fig, "R katları", MOR)
    eksen_pad(fig, df, .18, .16)
    duzen(fig, "27 · Düello çizgileri",
          "ayı hareketinin trend çizgisi (tepelerden) ile trend kanal çizgisi "
          "(diplerden) kesişiyorsa piyasa sıkışmıştır; kırılım kesişimde alınır",
          h=680, sematik=True)
    kaydet(fig, "27_duello_cizgileri", olcum=dict(
        ayi_cizgisi_dipler=[i1, i2], ayi_egim=round(e_ayi, 4),
        boga_cizgisi_dipler=[j1, j2], boga_egim=round(e_boga, 4),
        kesisim_bar=round(float(x_k), 1), kesisim_fiyat=round(float(y_k), 2),
        giris=round(giris, 2), stop=round(stop, 2), risk_1R=round(risk, 2),
        kirilim_bari=20, kirilim_bari_govde=round(float(df.c[20] - df.o[20]), 2)))


# ==================================================================== 28
def f28():
    """Merdiven ve küçülen merdiven (şematik, 2 panel)."""
    TICK = 0.05

    esit = df_yap([
        bar(105.00, 104.60, .00, .05), bar(104.60, 104.20, .05, .10),
        bar(104.20, 104.02, .06, .02),                       # 2 → dip 104.00
        bar(104.05, 104.35, .10, .05), bar(104.35, 104.45, .05, .06),   # 4 → tepe 104.50
        bar(104.45, 104.10, .05, .10), bar(104.10, 103.75, .06, .10),
        bar(103.75, 103.52, .06, .02),                       # 7 → dip 103.50
        bar(103.55, 103.85, .10, .05), bar(103.85, 103.95, .05, .06),   # 9 → tepe 104.00
        bar(103.95, 103.60, .06, .10), bar(103.60, 103.25, .06, .10),
        bar(103.25, 103.02, .06, .02),                       # 12 → dip 103.00
        bar(103.05, 103.35, .10, .05), bar(103.35, 103.45, .05, .06),   # 14 → tepe 103.50
        bar(103.45, 103.10, .06, .12)])

    kucul = df_yap([
        bar(105.00, 104.60, .00, .05), bar(104.60, 104.20, .05, .10),
        bar(104.20, 104.02, .06, .02),                       # 2 → dip 104.00
        bar(104.05, 104.30, .10, .05), bar(104.30, 104.40, .05, .06),   # 4 → tepe 104.45
        bar(104.40, 104.15, .05, .08), bar(104.15, 103.95, .06, .08),
        bar(103.95, 103.83, .06, .03),                       # 7 → dip 103.80
        bar(103.86, 104.05, .08, .04), bar(104.05, 104.10, .05, .05),   # 9 → tepe 104.15
        bar(104.10, 103.95, .05, .06), bar(103.95, 103.80, .05, .05),   # 11 → dip 103.75
        bar(103.82, 104.05, .08, .04), bar(104.05, 104.35, .10, .05),
        bar(104.35, 104.75, .12, .06), bar(104.75, 105.05, .12, .08)])

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13, subplot_titles=(
        "Panel 1 — MERDİVEN: üç eşit basamak, momentum korunuyor",
        "Panel 2 — KÜÇÜLEN MERDİVEN: her basamak kısalıyor, momentum kayboluyor"))

    olcumler = {}

    # ---- panel 1
    mum_ekle(fig, esit, row=1, col=1)
    x_et1 = sag_oluk(fig, esit, pay=0.52, sol=1.2, row=1, col=1)
    bacaklar1 = [(0, float(esit.h[0]), 2, float(esit.l[2])),
                 (4, float(esit.h[4]), 7, float(esit.l[7])),
                 (9, float(esit.h[9]), 12, float(esit.l[12]))]
    kayit1 = []
    for k, (xa, ya, xb, yb) in enumerate(bacaklar1, start=1):
        boy = ya - yb
        tick = round(boy / TICK)
        cizgi(fig, xa, ya, xb, yb, renk=BORDO, dash="dot", w=1.6, row=1, col=1)
        yatay(fig, ya, xa, x_et1 + 0.9 + 1.5 * (k - 1), renk=rgba(BORDO, 0.35),
              dash="dot", w=1.0, row=1, col=1)
        yatay(fig, yb, xb, x_et1 + 0.9 + 1.5 * (k - 1), renk=rgba(BORDO, 0.35),
              dash="dot", w=1.0, row=1, col=1)
        olcu(fig, x_et1 + 0.9 + 1.5 * (k - 1), yb, ya,
             f"bacak {k}<br>{boy:.2f} = {tick} tick", renk=BORDO, row=1, col=1)
        kayit1.append(dict(bacak=k, tepe=round(ya, 2), dip=round(yb, 2),
                           boy=round(boy, 2), tick=tick))
        # örtüşme: geri çekilme önceki bacağın içine giriyor
    not_(fig, 7, 104.86,
         "her geri çekilme önceki bacağın İÇİNE giriyor (örtüşme) — "
         "bu bir merdiven, dar bir kanal değil",
         renk=GRI, ok=False, boyut=10, row=1, col=1)
    not_(fig, 12, float(esit.l[12]),
         "üç eşit bacak → dördüncü bacak beklenmeye devam edilir",
         renk=BORDO, ok=True, ax=-40, ay=40, boyut=10, row=1, col=1)
    olcumler["esit_merdiven"] = dict(tick_birimi=TICK, bacaklar=kayit1)
    eksen_pad(fig, esit, .24, .14, row=1, col=1)

    # ---- panel 2
    mum_ekle(fig, kucul, row=2, col=1)
    x_et2 = sag_oluk(fig, kucul, pay=0.52, sol=1.2, row=2, col=1)
    bacaklar2 = [(0, float(kucul.h[0]), 2, float(kucul.l[2])),
                 (4, float(kucul.h[4]), 7, float(kucul.l[7])),
                 (9, float(kucul.h[9]), 11, float(kucul.l[11]))]
    kayit2 = []
    for k, (xa, ya, xb, yb) in enumerate(bacaklar2, start=1):
        boy = ya - yb
        tick = round(boy / TICK)
        cizgi(fig, xa, ya, xb, yb, renk=TURUNCU, dash="dot", w=1.6, row=2, col=1)
        yatay(fig, ya, xa, x_et2 + 0.9 + 1.5 * (k - 1), renk=rgba(TURUNCU, 0.35),
              dash="dot", w=1.0, row=2, col=1)
        yatay(fig, yb, xb, x_et2 + 0.9 + 1.5 * (k - 1), renk=rgba(TURUNCU, 0.35),
              dash="dot", w=1.0, row=2, col=1)
        olcu(fig, x_et2 + 0.9 + 1.5 * (k - 1), yb, ya,
             f"bacak {k}<br>{boy:.2f} = {tick} tick", renk=TURUNCU, row=2, col=1)
        kayit2.append(dict(bacak=k, tepe=round(ya, 2), dip=round(yb, 2),
                           boy=round(boy, 2), tick=tick))
    oran = kayit2[2]["tick"] / kayit2[0]["tick"]
    not_(fig, 11, float(kucul.l[11]),
         f"üçüncü bacak birincinin %{oran*100:.0f}'i — satıcılar tükendi",
         renk=TURUNCU, ok=True, ax=-206, ay=26, boyut=10, row=2, col=1)
    kutu(fig, 11.55, 15.45, float(kucul.l[11]), float(kucul.h[15]), YESIL, a=0.12,
         cizgi=1.2, row=2, col=1)
    not_(fig, 13, float(kucul.l[13]),
         "küçülen merdiven bir kama dönüşüdür:<br>üç itiş + momentum kaybı → yukarı dönüş",
         renk=YESIL, ok=True, ax=-96, ay=94, boyut=10, row=2, col=1)
    olcumler["kuculen_merdiven"] = dict(tick_birimi=TICK, bacaklar=kayit2,
                                        ucuncu_birinci_orani=round(oran, 2))
    eksen_pad(fig, kucul, .30, .14, row=2, col=1)

    lejant_cizgi(fig, "eşit bacak", BORDO, dash="dot")
    lejant_cizgi(fig, "küçülen bacak", TURUNCU, dash="dot")
    lejant(fig, "dönüş bölgesi", YESIL)
    duzen(fig, "28 · Merdiven ve küçülen merdiven",
          "1 tick = 0,05 şematik birim · bacak boyları ölçülür: eşit kalıyorsa trend, "
          "kısalıyorsa dönüş hazırlığı",
          h=900, sematik=True)
    kaydet(fig, "28_merdiven", olcum=olcumler)


# ==================================================================== 29
def f29():
    """Trendin olgunlaşması ve devrilme noktası (BIST100 günlük, 3 panel)."""
    d = yukle("XU100.IS", "1d")
    if d is None:
        print("  ! 29 atlandı: XU100 günlük önbellekte yok")
        return
    ESIK = 0.025                  # iki panelde de AYNI eşik — sayılar kıyaslanabilsin
    erken = dilim(d, 308, 47)     # 2025-11-11 (trendin dibi) → 2026-01-16
    olgun = dilim(d, 350, 90)     # 2026-01-12 → 2026-05-21
    devril = dilim(d, 420, 75)    # 2026-04-21 → 2026-08-17

    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.085, subplot_titles=(
        "Panel 1 — ERKEN trend: BIST100 günlük indis 308–354 "
        "(11 Kas 2025 → 16 Oca 2026) · geri çekilmeler sığ ve seyrek",
        "Panel 2 — OLGUN trend: indis 350–439 (12 Oca → 21 May 2026) · "
        "geri çekilmeler derin, sık ve örtüşmeli",
        "Panel 3 — DEVRİLME NOKTASI ve ilk gerçek aralık: indis 420–494 "
        "(21 Nis → 17 Ağu 2026)"))

    olcumler = {}

    def geri_cekilmeler(df, esik_oran=0.025):
        """Tepeden dibe düşüşler: kabaca zigzag ile ölçülür."""
        out = []
        zirve = float(df.h[0])
        zi = 0
        for i in range(1, len(df)):
            if df.h[i] > zirve:
                zirve = float(df.h[i])
                zi = i
                continue
            dip = float(df.l[zi:i + 1].min())
            if (zirve - dip) / zirve >= esik_oran and float(df.h[i]) > dip * (1 + esik_oran * 0.6):
                out.append((zi, zirve, int(df.l[zi:i + 1].idxmin()), dip))
                zirve = float(df.h[i])
                zi = i
        return out

    # ---- panel 1
    mum_ekle(fig, erken, row=1, col=1, zaman=True)
    ema_ciz(fig, erken, 20, renk=GRI, row=1, col=1)
    gc1 = geri_cekilmeler(erken, ESIK)
    for zi, zv, di, dv in gc1:
        kutu(fig, zi - 0.4, di + 0.4, dv, zv, TURUNCU, a=0.14, cizgi=1.0, row=1, col=1)
        not_(fig, di, dv, f"−%{(zv-dv)/zv*100:.1f}", renk=TURUNCU, ok=False, boyut=9,
             yanchor="top", row=1, col=1)
    trend_cizgisi(fig, erken, (0, 26), yon="bull", renk=TEAL, dash="dash", w=1.7,
                  row=1, col=1)
    d1 = float(erken.l.min())
    t1 = float(erken.h.max())
    en_derin1 = max((zv - dv) / zv * 100 for _, zv, _, dv in gc1)
    sik1 = len(gc1) / len(erken) * 100
    not_(fig, 20, d1 + (t1 - d1) * 0.12,
         f"{len(erken)} barda {len(gc1)} geri çekilme (100 barda {sik1:.0f}) · "
         f"en derini %{en_derin1:.1f}",
         renk=TEAL, ok=True, ax=0, ay=44, boyut=10, row=1, col=1)
    olcumler["erken_trend"] = dict(
        indis="308–354", bar_sayisi=len(erken), esik_yuzde=ESIK * 100,
        geri_cekilme_sayisi=len(gc1),
        yuz_barda_geri_cekilme=round(sik1, 1),
        en_derin_yuzde=round(en_derin1, 1),
        dip=round(d1), tepe=round(t1),
        toplam_yuzde=round((t1 / d1 - 1) * 100, 1))
    eksen_pad(fig, erken, .10, .10, row=1, col=1)
    zaman_ekseni(fig, erken, 6, "%d %b %y", row=1, col=1)

    # ---- panel 2
    mum_ekle(fig, olgun, row=2, col=1, zaman=True)
    ema_ciz(fig, olgun, 20, renk=GRI, row=2, col=1)
    gc2 = geri_cekilmeler(olgun, ESIK)
    for zi, zv, di, dv in gc2:
        kutu(fig, zi - 0.4, di + 0.4, dv, zv, TURUNCU, a=0.14, cizgi=1.0, row=2, col=1)
        if (zv - dv) / zv >= 0.04:      # yalnız derin olanlar etiketlenir (metin çakışmasın)
            not_(fig, di, dv, f"−%{(zv-dv)/zv*100:.1f}", renk=TURUNCU, ok=False,
                 boyut=9, yanchor="top", row=2, col=1)
    trend_cizgisi(fig, olgun, (0, 40), yon="bull", renk=TEAL, dash="dash", w=1.7,
                  row=2, col=1)
    d2 = float(olgun.l.min())
    t2v = float(olgun.h.max())
    en_derin2 = max((zv - dv) / zv * 100 for _, zv, _, dv in gc2)
    sik2 = len(gc2) / len(olgun) * 100
    not_(fig, 52, d2 + (t2v - d2) * 0.11,
         f"{len(olgun)} barda {len(gc2)} geri çekilme (100 barda {sik2:.0f}) · "
         f"en derini %{en_derin2:.1f}<br>panel 1 ile AYNI eşikle ölçüldü: "
         f"sıklık {sik2/sik1:.1f} kat, derinlik {en_derin2/en_derin1:.1f} kat arttı",
         renk=TURUNCU, ok=False, boyut=10, xanchor="left", row=2, col=1)
    zirve_i = int(olgun.h.idxmax())
    not_(fig, zirve_i, t2v, f"trendin son tepesi {t2v:.0f}", renk=BORDO, ok=True,
         ax=-40, ay=-28, boyut=10, row=2, col=1)
    olcumler["olgun_trend"] = dict(
        indis="350–439", bar_sayisi=len(olgun), esik_yuzde=ESIK * 100,
        geri_cekilme_sayisi=len(gc2),
        yuz_barda_geri_cekilme=round(sik2, 1),
        en_derin_yuzde=round(en_derin2, 1),
        siklik_carpani=round(sik2 / sik1, 1),
        derinlik_carpani=round(en_derin2 / en_derin1, 1),
        dip=round(d2), tepe=round(t2v), tepe_indis=350 + zirve_i,
        toplam_yuzde=round((t2v / d2 - 1) * 100, 1))
    eksen_pad(fig, olgun, .14, .12, row=2, col=1)
    zaman_ekseni(fig, olgun, 7, "%d %b %y", row=2, col=1)

    # ---- panel 3
    mum_ekle(fig, devril, row=3, col=1, zaman=True)
    ema_ciz(fig, devril, 20, renk=GRI, row=3, col=1)
    zir_i = int(devril.h.idxmax())
    zir = float(devril.h[zir_i])
    dip_i = int(devril.l.idxmin())
    dip = float(devril.l[dip_i])
    kutu(fig, zir_i - 0.6, zir_i + 0.6, float(devril.l[zir_i]), zir, BORDO, a=0.22,
         cizgi=1.4, row=3, col=1)
    not_(fig, zir_i, zir, f"DEVRİLME NOKTASI {zir:.0f} (indis {420+zir_i})",
         renk=BORDO, ok=True, ax=-116, ay=64, boyut=11, row=3, col=1)
    yatay(fig, zir, 0, len(devril) - 1, renk=BORDO, dash="dot", w=1.3, row=3, col=1)
    # ilk gerçek aralık: devrilme sonrası
    bant = devril.iloc[dip_i:].reset_index(drop=True)
    b_ust = float(bant.h.max())
    b_alt = float(bant.l.min())
    kutu(fig, dip_i - 0.5, len(devril) - 1, b_alt, b_ust, GRI, a=0.10, cizgi=1.2,
         row=3, col=1)
    yatay(fig, b_ust, dip_i, len(devril) - 1, renk=GRI, dash="dash", w=1.4, row=3, col=1)
    yatay(fig, b_alt, dip_i, len(devril) - 1, renk=GRI, dash="dash", w=1.4, row=3, col=1)
    not_(fig, dip_i + (len(devril) - dip_i) // 2, (b_ust + b_alt) / 2,
         f"trendden sonraki İLK GERÇEK ARALIK<br>"
         f"{b_alt:.0f} – {b_ust:.0f} · yükseklik {b_ust-b_alt:.0f} puan · "
         f"{len(bant)} bar",
         renk=MUREKKEP, ok=False, boyut=11, row=3, col=1)
    not_(fig, dip_i, dip, f"devrilme bacağı: {zir:.0f} → {dip:.0f} = "
         f"−%{(zir-dip)/zir*100:.1f}",
         renk=BORDO, ok=True, ax=40, ay=40, boyut=10, row=3, col=1)
    olcumler["devrilme"] = dict(
        indis="420–494", devrilme_indis=420 + zir_i, devrilme_fiyat=round(zir),
        dip_indis=420 + dip_i, dip=round(dip),
        devrilme_bacagi_yuzde=round((zir - dip) / zir * 100, 1),
        aralik_ust=round(b_ust), aralik_alt=round(b_alt),
        aralik_yuksekligi=round(b_ust - b_alt), aralik_bar_sayisi=len(bant))
    eksen_pad(fig, devril, .08, .14, row=3, col=1)
    zaman_ekseni(fig, devril, 7, "%d %b %y", row=3, col=1)

    lejant(fig, "geri çekilme", TURUNCU)
    lejant_cizgi(fig, "trend çizgisi", TEAL)
    lejant(fig, "devrilme barı", BORDO)
    lejant(fig, "ilk gerçek aralık", GRI)
    duzen(fig, "29 · Trendin olgunlaşması ve devrilme noktası",
          "gerçek veri · BIST100 (XU100) günlük · pencereler indisle pinli · "
          "aynı boğa trendinin üç yaşı: genç, olgun, bitmiş",
          y_baslik="BIST100 (puan)", x_baslik="işlem günü (pencere içi)", h=1360)
    kaydet(fig, "29_trendin_olgunlasmasi", olcum=olcumler)


# ==================================================================== main
def main():
    print("Brooks figürleri 13–29 üretiliyor…")
    for fn in (f13, f14, f15, f16, f17, f18, f19, f20, f21, f22,
               f23, f24, f25, f26, f27, f28, f29):
        fn()
    defter_yaz()


if __name__ == "__main__":
    main()
