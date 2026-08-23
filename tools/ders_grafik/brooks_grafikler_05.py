#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Al Brooks fiyat hareketi dersi — figür 64–78.

Kapsam:
  B8B  kalıp kataloğu — kama dönüşü/geri çekilmesi, başarısız kama, son bayrak,
       genişleyen üçgen, baş-omuz, dönüşlerin %80 kuralı, küçük zaman dilimi tuzağı
  B9   mıknatıslar, vakum, ölçülmüş hareket türleri, hedef seçimi

Kurallar (ortak katmanla aynı): paneller ALT ALTA, gerçek veri pencereleri İNDİSLE
pinlenir, şematik figürlerin barları ELLE kurulur, işaretlenen her şey etiketlenir,
metinle karşılaştırılacak sayılar kaydet(..., olcum=) ile bırakılır.

Veri notu — iki sapma ve gerekçesi (rapora da yazıldı):
  · Figür 67 müfredatta USDTRY 5dk; önbellekteki USDTRY 5dk serisi gövde/menzil
    oranı ~0,13 olan kuyruk gürültüsü (yfinance FX sentetiği) — bar bar okuma
    öğretilemez. Müfredatın kendi veri önceliğindeki 1 numaralı enstrümana,
    XU030 5dk'ya geçildi ve altbaşlıkta belirtildi.
  · Figür 71 müfredatta 1dk + 5dk; önbellekte 1 dakikalık veri YOK. Görev
    talimatı uyarınca 5dk (küçük) + 15dk (büyük) ikilisine çevrildi.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from brooks_ortak import (
    TEAL, BORDO, ALTIN, MAVI, MOR, TURUNCU, GRI, YESIL, MUREKKEP, rgba,
    yukle, dilim, df_yap, bar, yol_uret, mumlar, kutu, yatay, cizgi, not_,
    lejant, lejant_cizgi, ema, ema_ciz, bar_say, bar_etiketle, islem,
    olculmus_hareket, trend_cizgisi, duzen, zaman_ekseni, hover, kaydet, defter_yaz,
)

# ------------------------------------------------------------------ küçük yardımcılar
def panel(fig, df, row=None, ad="fiyat", goster=False):
    m = mumlar(df, ad=ad)
    m.showlegend = goster
    if row is None:
        fig.add_trace(m)
    else:
        fig.add_trace(m, row=row, col=1)


def kaydir(barlar, dy):
    return [(o + dy, h + dy, l + dy, c + dy) for o, h, l, c in barlar]


def aynala(barlar):
    """Bar dizisini fiyat ekseninde ters çevirir (boğa kalıbı → ayı kalıbı)."""
    return [(-o, -l, -h, -c) for o, h, l, c in barlar]


def olcek(barlar, k):
    return [(o * k, h * k, l * k, c * k) for o, h, l, c in barlar]


def uzat_cizgi(fig, x0, y0, x1, y1, x_son, **kw):
    """İki noktadan geçen doğruyu x_son'a kadar uzatır."""
    egim = (y1 - y0) / (x1 - x0)
    cizgi(fig, x0, y0, x_son, y0 + egim * (x_son - x0), **kw)
    return egim


def bar_menzil_ort(df, i, n=30):
    a = max(0, i - n)
    return float((df.h[a:i] - df.l[a:i]).mean())


# ============================================================ ŞEMATİK KAMA GEOMETRİSİ
# Üç itiş aşağı, yakınsayan kama. Tepe 0,00'da; üçüncü itişin dibi −5,20.
# Kilit indisler: itiş1 dibi 3 · ralli1 tepesi 5 · itiş2 dibi 9 · ralli2 tepesi 11
#                 itiş3 dibi ve ilk dönüş barı 14
KAMA_ASAGI = [
    bar(0.00, -0.90, 0.25, 0.15),   # 0  kamanın tepesi (yüksek +0,25)
    bar(-0.90, -1.90, 0.10, 0.20),  # 1
    bar(-1.90, -2.70, 0.10, 0.25),  # 2
    bar(-2.70, -2.40, 0.15, 0.30),  # 3  itiş 1 dibi  −3,00
    bar(-2.40, -1.60, 0.25, 0.15),  # 4
    bar(-1.60, -1.35, 0.15, 0.20),  # 5  ralli 1 tepesi −1,20
    bar(-1.35, -2.20, 0.10, 0.20),  # 6
    bar(-2.20, -3.10, 0.10, 0.25),  # 7
    bar(-3.10, -3.90, 0.10, 0.30),  # 8
    bar(-3.90, -3.60, 0.15, 0.50),  # 9  itiş 2 dibi  −4,40
    bar(-3.60, -3.00, 0.20, 0.15),  # 10
    bar(-3.00, -2.95, 0.15, 0.20),  # 11 ralli 2 tepesi −2,80
    bar(-2.95, -3.60, 0.10, 0.20),  # 12
    bar(-3.60, -4.50, 0.10, 0.15),  # 13
    bar(-4.50, -4.35, 0.12, 0.70),  # 14 itiş 3 dibi −5,20 · boğa dönüş barı
]
K_ITIS1, K_RALLI1, K_ITIS2, K_RALLI2, K_ITIS3 = 3, 5, 9, 11, 14
KAMA_TEPE_Y, KAMA_DIP_Y = 0.25, -5.20

# dönüş bağlamı: birinci giriş stoplanır, ikinci giriş çalışır
KAMA_DONUS_SONRASI = [
    bar(-4.35, -4.90, 0.10, 0.55),  # 15 marjinal daha düşük dip −5,45 → 1. giriş stop
    bar(-4.90, -4.50, 0.15, 0.35),  # 16 2. sinyal barı
    bar(-4.50, -3.70, 0.25, 0.15),  # 17 2. giriş tetiklendi
    bar(-3.70, -3.00, 0.20, 0.15),  # 18
    bar(-3.00, -2.20, 0.25, 0.20),  # 19
    bar(-2.20, -2.50, 0.20, 0.30),  # 20
    bar(-2.50, -1.50, 0.30, 0.20),  # 21
    bar(-1.50, -0.80, 0.25, 0.25),  # 22
    bar(-0.80, -1.10, 0.20, 0.30),  # 23
    bar(-1.10, -0.20, 0.30, 0.20),  # 24
]
# geri çekilme bağlamı: ilk sinyal yeter, trend hemen sürer
KAMA_BAYRAK_SONRASI = [
    bar(-4.35, -3.50, 0.25, 0.12),  # 15 giriş tetiklendi (ilk sinyal)
    bar(-3.50, -2.70, 0.20, 0.15),  # 16
    bar(-2.70, -1.90, 0.25, 0.20),  # 17
    bar(-1.90, -2.20, 0.20, 0.30),  # 18
    bar(-2.20, -1.20, 0.30, 0.20),  # 19
    bar(-1.20, -0.30, 0.25, 0.20),  # 20
    bar(-0.30, 0.60, 0.30, 0.20),   # 21
    bar(0.60, 1.40, 0.25, 0.25),    # 22
    bar(1.40, 1.10, 0.25, 0.30),    # 23
    bar(1.10, 2.20, 0.35, 0.20),    # 24
]


def kama_ciz(fig, ofs, dy, row, yon="asagi", uzat=None, etiket_ofs=0.35):
    """Kama gövdesinin işaretleri: üç itiş numarası + yakınsayan iki çizgi.

    ofs: kamanın ilk barının grafikteki x indisi · dy: fiyat kaydırması
    yon: 'asagi' (üç itiş aşağı) / 'yukari' (aynalanmış)
    """
    isaret = 1 if yon == "asagi" else -1
    tepe = [(0, KAMA_TEPE_Y), (K_RALLI1, -1.20), (K_RALLI2, -2.80)]
    dip = [(K_ITIS1, -3.00), (K_ITIS2, -4.40), (K_ITIS3, -5.20)]
    tepe = [(x, y * isaret + dy) for x, y in tepe]
    dip = [(x, y * isaret + dy) for x, y in dip]
    uzat = uzat if uzat is not None else K_ITIS3 + 5
    rc = dict(row=row, col=1) if row is not None else {}
    # trend çizgisi (tepelerden) ve trend kanal çizgisi (diplerden)
    uzat_cizgi(fig, ofs + tepe[0][0], tepe[0][1], ofs + tepe[2][0], tepe[2][1],
               ofs + uzat, renk=GRI, dash="dash", w=1.5, **rc)
    uzat_cizgi(fig, ofs + dip[0][0], dip[0][1], ofs + dip[1][0], dip[1][1],
               ofs + uzat, renk=GRI, dash="dot", w=1.5, **rc)
    for k, (x, y) in enumerate(dip, start=1):
        # üçüncü itişin etiketi sinyal barı yazılarıyla çakışmasın: daha uzağa, oklu
        if k < 3:
            not_(fig, ofs + x, y - etiket_ofs * isaret, f"itiş {k}", renk=ALTIN, ok=False,
                 boyut=11, yanchor="top" if isaret > 0 else "bottom", **rc)
        elif isaret > 0:
            not_(fig, ofs + x, y, "itiş 3", renk=ALTIN, boyut=11, ax=-58, ay=58, **rc)
        else:
            not_(fig, ofs + x, y, "itiş 3", renk=ALTIN, boyut=11, ax=54, ay=64, **rc)
    return tepe, dip


# ================================================================== 64
def f64():
    """Kama dönüşü ile kama geri çekilmesi — aynı şekil, iki bağlam."""
    on1 = yol_uret(12, 3.8, -0.32, 0.28, tohum=6401)          # ayı trendi
    dy1 = on1[-1][3]
    g1 = on1 + kaydir(KAMA_ASAGI + KAMA_DONUS_SONRASI, dy1)
    d1 = df_yap(g1)

    on2 = yol_uret(12, -3.8, 0.32, 0.28, tohum=6402)          # boğa trendi
    dy2 = on2[-1][3]
    g2 = on2 + kaydir(KAMA_ASAGI + KAMA_BAYRAK_SONRASI, dy2)
    d2 = df_yap(g2)

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11, subplot_titles=(
        "Panel 1 — KAMA DÖNÜŞÜ: ayı trendinin dibinde. Karşı trend işlem → İKİNCİ giriş şart.",
        "Panel 2 — KAMA GERİ ÇEKİLMESİ: boğa trendi içinde. Trend yönlü işlem → ilk sinyal yeter."))
    panel(fig, d1, 1)
    panel(fig, d2, 2)

    ofs = len(on1)
    # ---- panel 1
    kama_ciz(fig, ofs, dy1, 1)
    s1 = ofs + K_ITIS3
    kutu(fig, s1 - 0.45, s1 + 0.45, d1.l[s1], d1.h[s1], ALTIN, a=0.20, cizgi=1.2, row=1, col=1)
    not_(fig, s1, float(d1.l[s1]), "1. sinyal barı", renk=ALTIN, ax=-70, ay=40,
         boyut=10, row=1, col=1)
    yatay(fig, d1.h[s1], s1 - 0.4, s1 + 3, renk=MAVI, dash="solid", w=1.5, row=1, col=1)
    not_(fig, s1 + 3.1, d1.h[s1], "1. giriş (al-stop)", renk=MAVI, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    yatay(fig, d1.l[s1], s1 - 0.4, s1 + 3, renk=BORDO, dash="dot", w=1.4, row=1, col=1)
    not_(fig, ofs + 15, float(d1.l[ofs + 15]), "stop yendi:<br>marjinal daha düşük dip",
         renk=TURUNCU, ax=6, ay=78, boyut=10, row=1, col=1)
    s2 = ofs + 16
    kutu(fig, s2 - 0.45, s2 + 0.45, d1.l[s2], d1.h[s2], YESIL, a=0.20, cizgi=1.2, row=1, col=1)
    not_(fig, s2, float(d1.l[s2]), "2. sinyal barı", renk=YESIL, ax=66, ay=44,
         boyut=10, row=1, col=1)
    yatay(fig, d1.h[s2], s2 - 0.4, len(d1) - 1, renk=MAVI, dash="solid", w=1.7, row=1, col=1)
    not_(fig, len(d1) - 1, d1.h[s2], "2. GİRİŞ — kama dönüşünde kural", renk=MAVI, ok=False,
         boyut=10, xanchor="left", row=1, col=1)
    not_(fig, 4, float(d1.h[4]) + 0.55, "önce trend var: ayı bacağı", renk=BORDO,
         ok=False, boyut=10, xanchor="left", row=1, col=1)

    # ---- panel 2
    kama_ciz(fig, ofs, dy2, 2)
    t1 = ofs + K_ITIS3
    kutu(fig, t1 - 0.45, t1 + 0.45, d2.l[t1], d2.h[t1], YESIL, a=0.20, cizgi=1.2, row=2, col=1)
    not_(fig, t1, float(d2.l[t1]), "tek sinyal barı", renk=YESIL, ax=-6, ay=58,
         boyut=10, row=2, col=1)
    yatay(fig, d2.h[t1], t1 - 0.4, len(d2) - 1, renk=MAVI, dash="solid", w=1.7, row=2, col=1)
    not_(fig, len(d2) - 1, d2.h[t1], "İLK giriş yeter — trend yönlü", renk=MAVI, ok=False,
         boyut=10, xanchor="left", row=2, col=1)
    yatay(fig, d2.l[t1], t1 - 0.4, t1 + 4, renk=BORDO, dash="dot", w=1.4, row=2, col=1)
    not_(fig, t1 + 4.1, d2.l[t1], "stop", renk=BORDO, ok=False, boyut=10, xanchor="left",
         row=2, col=1)
    not_(fig, 4, float(d2.l[4]) - 0.60, "önce trend var: boğa bacağı", renk=TEAL,
         ok=False, boyut=10, xanchor="left", row=2, col=1)
    not_(fig, ofs + 21, float(d2.c[ofs + 21]) + 0.85,
         "kama, boğa bayrağının şekli:<br>trend yeniden başlar", renk=TEAL, ok=False,
         boyut=10, row=2, col=1)

    lejant(fig, "sinyal barı (dönüş bağlamı)", ALTIN)
    lejant(fig, "sinyal barı (trend yönlü)", YESIL)
    lejant_cizgi(fig, "kamanın yakınsayan çizgileri", GRI)
    lejant_cizgi(fig, "giriş", MAVI, dash="solid")
    duzen(fig, "64 · Kama dönüşü ile kama geri çekilmesi",
          "aynı üç itişli kama — soldaki bağlam kararı değiştirir", h=880, sematik=True,
          x_baslik="")
    fig.update_xaxes(title_text="bar sırası", row=2, col=1)
    kaydet(fig, "64_kama_donusu_geri_cekilme", olcum=dict(
        itis_sayisi=3, kama_tepe=round(KAMA_TEPE_Y, 2), kama_dip=round(KAMA_DIP_Y, 2),
        kama_yuksekligi=round(KAMA_TEPE_Y - KAMA_DIP_Y, 2),
        panel1_kural="ikinci giriş", panel2_kural="ilk sinyal"))


# ================================================================== 65
KAMA_YUKARI = aynala(KAMA_ASAGI)            # üç itiş yukarı; tepe +5,20, dip −0,25
KAMA_BASARISIZ_SONRASI = [
    bar(4.35, 4.10, 0.10, 0.25),   # 15 short tetiklendi (giriş 4,23)
    bar(4.10, 4.60, 0.20, 0.15),   # 16 toparlanma
    bar(4.60, 5.30, 0.15, 0.10),   # 17 STOP: kamanın tepesi 5,20 aşıldı
    bar(5.30, 6.10, 0.25, 0.15),   # 18
    bar(6.10, 6.90, 0.20, 0.20),   # 19
    bar(6.90, 6.60, 0.25, 0.30),   # 20
    bar(6.60, 7.60, 0.30, 0.20),   # 21
    bar(7.60, 8.40, 0.25, 0.25),   # 22
    bar(8.40, 8.10, 0.25, 0.35),   # 23
    bar(8.10, 9.20, 0.35, 0.20),   # 24
    bar(9.20, 9.90, 0.30, 0.25),   # 25
    bar(9.90, 9.60, 0.25, 0.35),   # 26
    bar(9.60, 10.45, 0.30, 0.25),  # 27 hedefe varış
]


def f65():
    """Başarısız kama ve ters yöne ölçülmüş hareket."""
    on = yol_uret(12, -4.2, 0.35, 0.28, tohum=6501)
    dy = on[-1][3]
    g = on + kaydir(KAMA_YUKARI + KAMA_BASARISIZ_SONRASI, dy)
    d = df_yap(g)
    ofs = len(on)
    tepe_y = KAMA_TEPE_Y * -1 + dy          # aynalandı: kamanın DİBİ
    dip_y = KAMA_DIP_Y * -1 + dy            # kamanın TEPESİ (+5,20)
    H = dip_y - tepe_y                       # kama yüksekliği
    hedef = dip_y + H

    fig = go.Figure()
    panel(fig, d, None)
    kama_ciz(fig, ofs, dy, None, yon="yukari")
    s = ofs + K_ITIS3
    kutu(fig, s - 0.45, s + 0.45, d.l[s], d.h[s], ALTIN, a=0.20, cizgi=1.2)
    not_(fig, s, float(d.h[s]), "kama sinyal barı (sat)", renk=ALTIN, ax=-70, ay=-36,
         boyut=10)
    yatay(fig, d.l[s], s - 0.4, s + 4, renk=MAVI, dash="solid", w=1.5)
    not_(fig, s + 4.1, d.l[s], "short giriş", renk=MAVI, ok=False, boyut=10, xanchor="left")
    yatay(fig, dip_y, s - 0.4, len(d) - 1, renk=BORDO, dash="dot", w=1.5)
    not_(fig, ofs + 17, float(d.h[ofs + 17]),
         f"BAŞARISIZ KAMA: stop yendi<br>(kamanın tepesi {dip_y:.2f} aşıldı)",
         renk=TURUNCU, ax=-118, ay=-86, boyut=10)
    # kama yüksekliği + ters projeksiyon
    xb = ofs + 1
    fig.add_shape(type="line", x0=xb, y0=tepe_y, x1=xb, y1=dip_y,
                  line=dict(color=MOR, width=2.6))
    not_(fig, xb - 0.3, (tepe_y + dip_y) / 2, f"kama yüksekliği H = {H:.2f}", renk=MOR,
         ok=False, boyut=10, xanchor="right")
    xp = ofs + 19
    fig.add_shape(type="line", x0=xp, y0=dip_y, x1=xp, y1=hedef,
                  line=dict(color=MOR, width=2.6))
    not_(fig, xp, (dip_y + hedef) / 2, "H kadar<br>YUKARI projeksiyon", renk=MOR,
         ax=-86, ay=52, boyut=10)
    yatay(fig, hedef, xp, len(d) - 1, renk=MOR, dash="dash", w=1.6)
    not_(fig, len(d) - 1, hedef, f"hedef {hedef:.2f}", renk=MOR, ok=False, boyut=10,
         xanchor="left")
    yatay(fig, tepe_y, ofs, ofs + 6, renk=GRI, dash="dot", w=1.1)
    not_(fig, ofs + 6.1, tepe_y, "kamanın tabanı", renk=GRI, ok=False, boyut=10, xanchor="left")
    not_(fig, 3, float(d.l[3]) - 0.65, "önceki boğa trendi", renk=TEAL, ok=False,
         boyut=10, xanchor="left")
    tepe_i = int(np.argmax(d.h.values[ofs + K_ITIS3:])) + ofs + K_ITIS3
    not_(fig, tepe_i, float(d.h[tepe_i]),
         f"varış: bar {tepe_i} · tepe {float(d.h[tepe_i]):.2f}", renk=MOR, ax=-40, ay=-48,
         boyut=10)

    lejant(fig, "kama sinyal barı", ALTIN)
    lejant_cizgi(fig, "kama çizgileri", GRI)
    lejant_cizgi(fig, "ölçülmüş hareket hedefi", MOR)
    duzen(fig, "65 · Başarısız kama ve ters ölçülmüş hareket",
          "kama dönüşü tutmazsa kama yüksekliği ters yöne projekte edilir", h=640,
          sematik=True)
    kaydet(fig, "65_basarisiz_kama", olcum=dict(
        kama_tabani=round(tepe_y, 2), kama_tepesi=round(dip_y, 2), H=round(H, 2),
        hedef=round(hedef, 2), stop_bari_ofset=17, itis_sayisi=3,
        gerceklesen_tepe=round(float(d.h[ofs + K_ITIS3:].max()), 2),
        hedefe_varildi=bool(float(d.h[ofs + K_ITIS3:].max()) >= hedef)))


# ================================================================== 66
def _son_bayrak_govde(tohum):
    """Boğa bacağı (tepe 8,60) + beş barlık sıkı son bayrak (8,10–8,45)."""
    bacak = yol_uret(13, 0.0, 0.62, 0.30, tohum=tohum)
    # bacağın son barını 8,60 tepesine çiviliyoruz
    son = bacak[-1][3]
    bacak = kaydir(bacak, 8.20 - son)
    bacak[-1] = bar(bacak[-1][0], 8.20, 0.40, 0.15)      # tepe 8,60
    bayrak = [
        bar(8.20, 8.32, 0.10, 0.18),   # +0
        bar(8.32, 8.18, 0.11, 0.14),   # +1
        bar(8.18, 8.30, 0.13, 0.12),   # +2
        bar(8.30, 8.22, 0.15, 0.15),   # +3  bayrak tepesi 8,45
        bar(8.22, 8.28, 0.09, 0.18),   # +4  bayrak dibi 8,04
    ]
    return bacak, bayrak


def f66():
    """Son bayrağın üç kırılım biçimi."""
    varyant = [
        ("yükselen tepe", [
            bar(8.28, 8.95, 0.35, 0.10),   # kırılım: yeni trend tepesi 9,30
            bar(8.95, 8.35, 0.12, 0.25),   # dönüş barı
            bar(8.35, 7.70, 0.10, 0.20),
            bar(7.70, 7.00, 0.10, 0.22),
            bar(7.00, 7.30, 0.22, 0.25),
            bar(7.30, 6.40, 0.12, 0.25),
            bar(6.40, 5.60, 0.12, 0.25),
            bar(5.60, 5.95, 0.25, 0.22),
            bar(5.95, 5.05, 0.12, 0.25),
            bar(5.05, 4.35, 0.14, 0.28),
            bar(4.35, 3.75, 0.16, 0.30),
            bar(3.75, 4.05, 0.28, 0.25),
        ]),
        ("alçalan tepe", [
            bar(8.28, 8.40, 0.12, 0.12),   # kırılım 8,52 → trend tepesi 8,60'ın ALTINDA
            bar(8.40, 8.05, 0.10, 0.20),
            bar(8.05, 7.45, 0.10, 0.22),
            bar(7.45, 7.75, 0.22, 0.22),
            bar(7.75, 6.95, 0.10, 0.24),
            bar(6.95, 6.20, 0.12, 0.24),
            bar(6.20, 6.50, 0.24, 0.22),
            bar(6.50, 5.70, 0.12, 0.26),
            bar(5.70, 4.95, 0.14, 0.26),
            bar(4.95, 5.25, 0.26, 0.24),
            bar(5.25, 4.40, 0.14, 0.28),
            bar(4.40, 3.90, 0.16, 0.30),
        ]),
        ("kırılımsız", [
            bar(8.28, 8.10, 0.08, 0.16),   # bayrağın tepesi aşılmıyor
            bar(8.10, 7.85, 0.09, 0.18),   # doğrudan aşağı kırılım
            bar(7.85, 7.15, 0.10, 0.22),
            bar(7.15, 7.45, 0.22, 0.22),
            bar(7.45, 6.65, 0.10, 0.24),
            bar(6.65, 5.90, 0.12, 0.24),
            bar(5.90, 6.20, 0.24, 0.22),
            bar(6.20, 5.40, 0.12, 0.26),
            bar(5.40, 4.70, 0.14, 0.26),
            bar(4.70, 5.00, 0.26, 0.24),
            bar(5.00, 4.20, 0.14, 0.28),
            bar(4.20, 3.70, 0.16, 0.30),
        ]),
    ]
    basliklar = tuple(
        f"Panel {k+1} — {ad}: son bayrağın kırılımı {aciklama}"
        for k, (ad, aciklama) in enumerate([
            ("YÜKSELEN TEPE", "yeni trend zirvesi yapar, sonra döner"),
            ("ALÇALAN TEPE", "bayrağı aşar ama trend zirvesine ULAŞAMAZ"),
            ("KIRILIMSIZ", "hiç olmaz; piyasa doğrudan bayrağın altından çıkar")]))
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.075, subplot_titles=basliklar)
    olcumler = {}
    for k, (ad, kuyruk) in enumerate(varyant, start=1):
        bacak, bayrak = _son_bayrak_govde(6600 + k)
        d = df_yap(bacak + bayrak + kuyruk)
        panel(fig, d, k)
        b0 = len(bacak)
        b1 = b0 + len(bayrak) - 1
        by_h = float(d.h[b0:b1 + 1].max())
        by_l = float(d.l[b0:b1 + 1].min())
        trend_tepe = float(d.h[:b0].max())
        kutu(fig, b0 - 0.5, b1 + 0.5, by_l, by_h, ALTIN, a=0.16, cizgi=1.3, row=k, col=1)
        not_(fig, (b0 + b1) / 2, by_l - 0.30, "SON BAYRAK", renk=ALTIN, ok=False, boyut=11,
             yanchor="top", row=k, col=1)
        yatay(fig, trend_tepe, 0, len(d) - 1, renk=GRI, dash="dash", w=1.2, row=k, col=1)
        not_(fig, 0.2, trend_tepe, f"trend zirvesi {trend_tepe:.2f}", renk=GRI, ok=False,
             boyut=10, xanchor="left", yanchor="bottom", row=k, col=1)
        kir = b1 + 1
        kir_h = float(d.h[kir])
        kutu(fig, kir - 0.45, kir + 0.45, d.l[kir], d.h[kir], TURUNCU, a=0.20, cizgi=1.2,
             row=k, col=1)
        not_(fig, kir, kir_h, f"kırılım denemesi {kir_h:.2f}", renk=TURUNCU,
             ax=-72, ay=-40, boyut=10, row=k, col=1)
        don = kir + 1
        not_(fig, don, float(d.h[don]), "dönüş barı", renk=BORDO, ax=54, ay=-32,
             boyut=10, row=k, col=1)
        # ölçülmüş hareket: bayrak yüksekliği bayrağın dibinden aşağı
        yuk = by_h - by_l
        hedef = by_l - yuk
        yatay(fig, hedef, b1, len(d) - 1, renk=MOR, dash="dash", w=1.4, row=k, col=1)
        not_(fig, len(d) - 1, hedef, f"asgari hedef {hedef:.2f} (bayrak yüksekliği)",
             renk=MOR, ok=False, boyut=10, xanchor="left", row=k, col=1)
        varildi = bool(float(d.l[kir:].min()) <= hedef)
        dip_i = int(np.argmin(d.l.values[kir:])) + kir
        not_(fig, dip_i, float(d.l[dip_i]) - 0.28,
             f"dönüşün gittiği yer {float(d.l[dip_i]):.2f}", renk=BORDO, ok=False,
             boyut=10, yanchor="top", row=k, col=1)
        olcumler[f"panel{k}"] = dict(
            bicim=ad, bayrak_tepe=round(by_h, 2), bayrak_dip=round(by_l, 2),
            trend_zirvesi=round(trend_tepe, 2), kirilim_tepesi=round(kir_h, 2),
            mm_hedefi=round(hedef, 2), hedefe_varildi=varildi,
            donus_dibi=round(float(d.l[dip_i]), 2))
    lejant(fig, "son bayrak", ALTIN)
    lejant(fig, "kırılım denemesi", TURUNCU)
    lejant_cizgi(fig, "trend zirvesi", GRI)
    lejant_cizgi(fig, "bayrak yüksekliği MM", MOR)
    duzen(fig, "66 · Son bayrak: üç kırılım biçimi",
          "üçünde de sonuç aynı — bayrak trendin son duraklamasıdır", h=1180, sematik=True,
          x_baslik="", legend_y=-0.07)
    fig.update_xaxes(title_text="bar sırası", row=3, col=1)
    kaydet(fig, "66_son_bayrak_uc_kirilim", olcum=olcumler)


# ================================================================== 67  (GERÇEK)
def f67():
    """Tek barlı son bayrak — XU030 5dk, indis 676–739 (10 Haziran 2026)."""
    d = yukle("XU030.IS", "5m")
    if d is None:
        print("  ! 67 atlandı: XU030 5dk yok")
        return
    BAS = 676
    p1 = dilim(d, BAS, 30)          # 676–705
    p2 = dilim(d, BAS, 64)          # 676–739
    bayrak, kirilim = 691 - BAS, 692 - BAS
    bacak_bas, bacak_tepe = 679 - BAS, 683 - BAS

    ort_menzil = bar_menzil_ort(d, 691, 30)
    b_menzil = float(d.h[691] - d.l[691])
    asim = float(d.h[692] - d.h[691])
    giris = float(d.l[691])
    stop = float(d.h[692])
    risk = stop - giris
    bacak_dibi = float(d.l[679])
    en_dusuk = float(d.l[692:740].min())

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.115, subplot_titles=(
        "Panel 1 — boğa spike'ı ve içindeki TEK duraklama barı (son bayrak)",
        "Panel 2 — kırılımın başarısızlığı (1,8 puan aşım) ve dönüş"))
    panel(fig, p1, 1)
    panel(fig, p2, 2)

    for r, df, bf, kf in ((1, p1, bayrak, kirilim), (2, p2, bayrak, kirilim)):
        kutu(fig, bf - 0.45, bf + 0.45, df.l[bf], df.h[bf], ALTIN, a=0.24, cizgi=1.4,
             row=r, col=1)
        yatay(fig, float(d.h[691]), bf - 1, len(df) - 1, renk=ALTIN, dash="dash", w=1.3,
              row=r, col=1)

    not_(fig, bayrak, float(d.l[691]) - 14,
         f"tek barlı son bayrak<br>menzil {b_menzil:.1f} (30 bar ort. {ort_menzil:.1f})",
         renk=ALTIN, ax=-58, ay=52, boyut=10, row=1, col=1)
    not_(fig, bacak_tepe, float(d.h[683]) + 8, "spike", renk=TEAL, ok=False, boyut=11,
         yanchor="bottom", row=1, col=1)
    cizgi(fig, bacak_bas, float(d.l[679]), bacak_tepe, float(d.h[683]), renk=TEAL,
          dash="dot", w=1.6, row=1, col=1)
    not_(fig, kirilim, float(d.h[692]) + 6,
         f"kırılım barı: bayrağı yalnız {asim:.1f} puan aştı,<br>kendi dibinde kapandı",
         renk=TURUNCU, ax=52, ay=-40, boyut=10, row=1, col=1)

    # panel 2 — işlem
    islem(fig, p2, sinyal=bayrak, yon="bear", giris=giris, stop=stop,
          hedefler=(bacak_dibi,), etiketler=("bacağın başlangıcı",), row=2, col=1,
          ondalik=1)
    not_(fig, kirilim, float(d.h[692]) + 10,
         "başarısız kırılım = son bayrağın kırılımı", renk=TURUNCU, ax=60, ay=-34,
         boyut=10, row=2, col=1)
    dip_i = int(np.argmin(p2.l.values))
    not_(fig, dip_i, float(p2.l[dip_i]) - 10,
         f"dönüşün dibi {en_dusuk:.1f}  ({(giris - en_dusuk)/risk:.1f}R)", renk=BORDO,
         ax=0, ay=42, boyut=10, row=2, col=1)
    yatay(fig, bacak_dibi, bacak_bas, len(p2) - 1, renk=GRI, dash="dot", w=1.2, row=2, col=1)

    lejant(fig, "son bayrak barı", ALTIN)
    lejant(fig, "sinyal barı", ALTIN)
    lejant_cizgi(fig, "giriş", MAVI, dash="solid")
    lejant_cizgi(fig, "hedef", MOR)
    duzen(fig, "67 · Tek barlı son bayrak",
          "XU030 5 dakika · indis 676–739 (10 Haziran 2026) · pencere indisle pinli · "
          "müfredattaki USDTRY 5dk serisi kuyruk gürültüsü olduğu için XU030'a alındı",
          h=900, x_baslik="", y_baslik="endeks")
    zaman_ekseni(fig, p1, adet=6, fmt="%d %b %H:%M", row=1, col=1)
    zaman_ekseni(fig, p2, adet=8, fmt="%d %b %H:%M", row=2, col=1)
    fig.update_xaxes(title_text="bar (indisle pinli)", row=2, col=1)
    kaydet(fig, "67_tek_barli_son_bayrak", olcum=dict(
        enstruman="XU030 5dk", pencere="indis 676–739",
        bayrak_bari=691, bayrak_menzili=round(b_menzil, 1),
        ort_menzil_30=round(ort_menzil, 1), kirilim_bari=692,
        asim_puan=round(asim, 1), giris=round(giris, 1), stop=round(stop, 1),
        risk=round(risk, 1), bacak_dibi=round(bacak_dibi, 1),
        bacak_dibi_R=round((giris - bacak_dibi) / risk, 1),
        donus_dibi=round(en_dusuk, 1), donus_dibi_R=round((giris - en_dusuk) / risk, 1)))


# ================================================================== 68  (GERÇEK)
def f68():
    """Genişleyen üçgen dip — BIST100 günlük, indis 155–235."""
    d = yukle("XU100.IS", "1d")
    if d is None:
        print("  ! 68 atlandı: XU100 günlük yok")
        return
    B1, B2 = 155, 188
    p1 = dilim(d, B1, 81)          # 155–235
    p2 = dilim(d, B2, 32)          # 188–219
    N = [166, 172, 179, 184, 196]  # beş nokta
    tip = ["dip", "tepe", "dip", "tepe", "dip"]
    y = [float(d.l[166]), float(d.h[172]), float(d.l[179]), float(d.h[184]), float(d.l[196])]

    H = y[3] - y[4]                       # genişleyen üçgenin yüksekliği
    mm = y[3] + H
    varis = next(i for i in range(197, 236) if float(d.h[i]) >= mm)

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.115, subplot_titles=(
        "Panel 1 — beş nokta: daha düşük dipler, daha yüksek tepeler (genişleyen üçgen dip)",
        "Panel 2 — 5. noktada İKİNCİ giriş: 3. noktanın altına kırılım başarısız oldu"))
    panel(fig, p1, 1)
    panel(fig, p2, 2)

    for k, (i, t, yy) in enumerate(zip(N, tip, y), start=1):
        x = i - B1
        renk = TEAL if t == "dip" else BORDO
        not_(fig, x, yy + (-150 if t == "dip" else 150), f"{k}",
             renk=renk, ok=False, boyut=13,
             yanchor="top" if t == "dip" else "bottom", row=1, col=1)
        yatay(fig, yy, x - 2, x + 2, renk=renk, dash="dot", w=1.2, row=1, col=1)
    # genişleyen kenarlar
    uzat_cizgi(fig, N[0] - B1, y[0], N[2] - B1, y[2], N[4] - B1 + 4, renk=GRI, dash="dash",
               w=1.6, row=1, col=1)
    uzat_cizgi(fig, N[1] - B1, y[1], N[3] - B1, y[3], N[4] - B1 + 4, renk=GRI, dash="dash",
               w=1.6, row=1, col=1)
    not_(fig, N[2] - B1, y[2] - 420, "iki kenar AÇILIYOR: dipler alçalır, tepeler yükselir",
         renk=GRI, ok=False, boyut=10, xanchor="left", row=1, col=1)
    # MM
    xh = N[3] - B1
    fig.add_shape(type="line", x0=xh, y0=y[4], x1=xh, y1=y[3], line=dict(color=MOR, width=2.6),
                  row=1, col=1)
    not_(fig, xh - 0.5, (y[3] + y[4]) / 2, f"H = {H:.0f}", renk=MOR, ok=False, boyut=10,
         xanchor="right", row=1, col=1)
    fig.add_shape(type="line", x0=N[4] - B1 + 6, y0=y[3], x1=N[4] - B1 + 6, y1=mm,
                  line=dict(color=MOR, width=2.6), row=1, col=1)
    yatay(fig, mm, N[4] - B1 + 6, len(p1) - 1, renk=MOR, dash="dash", w=1.5, row=1, col=1)
    not_(fig, len(p1) - 1, mm, f"MM hedefi {mm:.0f}", renk=MOR, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    not_(fig, varis - B1, float(d.h[varis]) + 130,
         f"hedefe varış: {d.ts[varis]:%d %b %Y}", renk=MOR, ax=-40, ay=-32, boyut=10,
         row=1, col=1)

    # panel 2 — ikinci giriş
    ilk = 179 - B2
    kutu(fig, ilk - 0.5, ilk + 0.5, float(d.l[179]), float(d.h[179]), TURUNCU, a=0.20,
         cizgi=1.2, row=2, col=1) if ilk >= 0 else None
    s = 196 - B2
    o = islem(fig, p2, sinyal=s, yon="bull", giris=float(d.h[196]), stop=float(d.l[196]),
              hedefler=(y[1], y[3]), etiketler=("2. nokta tepesi", "4. nokta tepesi"),
              row=2, col=1, ondalik=0)
    yatay(fig, y[2], 0, len(p2) - 1, renk=TURUNCU, dash="dash", w=1.3, row=2, col=1)
    not_(fig, 0.4, y[2], "3. nokta (ilk deneme buradaydı)", renk=TURUNCU, ok=False,
         boyut=10, xanchor="left", yanchor="bottom", row=2, col=1)
    not_(fig, s, float(d.l[196]) - 130,
         "5. nokta: 3. noktanın altına kırılım<br>başarısız → İKİNCİ giriş (al)",
         renk=YESIL, ax=-30, ay=54, boyut=10, row=2, col=1)

    lejant_cizgi(fig, "genişleyen üçgenin kenarları", GRI)
    lejant(fig, "sinyal barı", ALTIN)
    lejant_cizgi(fig, "ölçülmüş hareket", MOR)
    duzen(fig, "68 · Genişleyen üçgen dip: her zaman bir MTR kurulumu",
          "BIST100 günlük · panel 1 indis 155–235, panel 2 indis 188–219 · pencereler "
          "indisle pinli", h=920, x_baslik="", y_baslik="endeks")
    zaman_ekseni(fig, p1, adet=9, fmt="%d %b", row=1, col=1)
    zaman_ekseni(fig, p2, adet=7, fmt="%d %b", row=2, col=1)
    fig.update_xaxes(title_text="bar (indisle pinli)", row=2, col=1)
    kaydet(fig, "68_genisleyen_ucgen_dip", olcum=dict(
        enstruman="BIST100 günlük", noktalar={f"{k+1}": dict(indis=N[k], tarih=str(d.ts[N[k]].date()),
                                                            fiyat=round(y[k], 1)) for k in range(5)},
        H=round(H, 1), mm_hedefi=round(mm, 1), mm_varis_indis=varis,
        mm_varis_tarih=str(d.ts[varis].date()),
        giris=round(o["giris"], 1), stop=round(o["stop"], 1), risk=round(o["risk"], 1),
        hedef_R=[round(r, 2) for r in o["r"]]))


# ================================================================== 69  (GERÇEK)
def f69():
    """Baş-omuz tepesinin akış anatomisi — BIST100 günlük, indis 440–494."""
    d = yukle("XU100.IS", "1d")
    if d is None:
        print("  ! 69 atlandı")
        return
    B1, B2 = 440, 462
    p1 = dilim(d, B1, 55)      # 440–494
    p2 = dilim(d, B2, 33)      # 462–494
    SOL, BAS, SAG1, SAG2 = 445, 457, 468, 472
    boyun = float(d.l[465])                     # 14031,7 — en çok test edilen dip
    H = float(d.h[BAS]) - boyun
    hedef = boyun - H
    dip_i = 483
    dip = float(d.l[dip_i])

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.115, subplot_titles=(
        "Panel 1 — sol omuz · baş · iki sağ omuz ve boyun çizgisi",
        "Panel 2 — boyun çizgisi kırılımında satışın gücü, MM hedefi ve kalıbın başarısızlığı"))
    panel(fig, p1, 1)
    panel(fig, p2, 2)

    for i, ad, renk in ((SOL, "sol omuz", GRI), (BAS, "BAŞ", BORDO),
                        (SAG1, "sağ omuz 1", GRI), (SAG2, "sağ omuz 2", GRI)):
        x = i - B1
        kutu(fig, x - 0.6, x + 0.6, float(d.l[i]), float(d.h[i]), renk, a=0.14, cizgi=1.0,
             row=1, col=1)
        not_(fig, x, float(d.h[i]) + 90, f"{ad} {d.h[i]:.0f}", renk=renk, ok=False,
             boyut=10, yanchor="bottom", row=1, col=1)
    yatay(fig, boyun, 0, len(p1) - 1, renk=ALTIN, dash="solid", w=1.8, row=1, col=1)
    not_(fig, 0.4, boyun, f"boyun çizgisi {boyun:.0f} (en çok test edilen dip)", renk=ALTIN,
         ok=False, boyut=10, xanchor="left", yanchor="bottom", row=1, col=1)
    # kitap boyun çizgisi: başı kuşatan iki dipten geçen — yükseliyor, erken kırılır
    uzat_cizgi(fig, 451 - B1, float(d.l[451]), 465 - B1, float(d.l[465]), 474 - B1,
               renk=GRI, dash="dot", w=1.3, row=1, col=1)
    not_(fig, 458 - B1, float(d.l[451]) + 120,
         "kitap boyun çizgisi (başı kuşatan iki dip) — YÜKSELEN, erken kırılır",
         renk=GRI, ok=False, boyut=10, xanchor="left", row=1, col=1)
    for i in (465, 471, 473):
        not_(fig, i - B1, float(d.l[i]) - 60, "test", renk=ALTIN, ok=False, boyut=9,
             yanchor="top", row=1, col=1)

    # panel 2 — kırılım gücü + MM
    yatay(fig, boyun, 0, len(p2) - 1, renk=ALTIN, dash="solid", w=1.8, row=2, col=1)
    not_(fig, 0.4, boyun, f"boyun {boyun:.0f}", renk=ALTIN, ok=False, boyut=10,
         xanchor="left", yanchor="bottom", row=2, col=1)
    kutu(fig, 480 - B2 - 0.5, 483 - B2 + 0.5, float(d.l[483]), float(d.h[480]), BORDO,
         a=0.14, cizgi=1.2, row=2, col=1)
    not_(fig, 481 - B2, float(d.h[480]) + 90,
         "satışın gücü: 4 ardışık ayı barı · kapanışlar dip yakınında ·<br>"
         "üst kuyruk yok · geri çekilme yok",
         renk=BORDO, ax=10, ay=-46, boyut=10, row=2, col=1)
    fig.add_shape(type="line", x0=2, y0=boyun, x1=2, y1=float(d.h[BAS]),
                  line=dict(color=MOR, width=2.4), row=2, col=1) if BAS >= B2 else None
    yatay(fig, hedef, 480 - B2, len(p2) - 1, renk=MOR, dash="dash", w=1.6, row=2, col=1)
    not_(fig, len(p2) - 1, hedef, f"MM hedefi {hedef:.0f}  (baş−boyun = {H:.0f})",
         renk=MOR, ok=False, boyut=10, xanchor="left", row=2, col=1)
    not_(fig, dip_i - B2, dip - 70,
         f"dönüşün dibi {dip:.0f} — MM hedefinin {dip - hedef:.0f} puan ÜSTÜNDE kaldı "
         f"(%{abs(dip - hedef)/hedef*100:.2f} ıskalama)",
         renk=BORDO, ax=-10, ay=52, boyut=10, row=2, col=1)
    kutu(fig, 484 - B2 - 0.5, len(p2) - 0.5, float(d.l[483]), float(d.h[493]), YESIL,
         a=0.10, cizgi=1.0, dash="dot", row=2, col=1)
    not_(fig, 490 - B2, float(d.h[493]) + 70,
         "kalıp BAŞARISIZ: fiyat boyun çizgisinin üstüne döndü —<br>"
         "iki sağ omuzlu baş-omuz çoğu zaman boğa bayrağıdır",
         renk=YESIL, ax=-24, ay=-40, boyut=10, row=2, col=1)

    lejant_cizgi(fig, "boyun çizgisi", ALTIN, dash="solid")
    lejant_cizgi(fig, "kitap boyun çizgisi", GRI, dash="dot")
    lejant_cizgi(fig, "ölçülmüş hareket", MOR)
    lejant(fig, "kalıbın başarısızlığı", YESIL)
    duzen(fig, "69 · Baş-omuz tepesinin akış anatomisi",
          "BIST100 günlük · panel 1 indis 440–494, panel 2 indis 462–494 · pencereler "
          "indisle pinli", h=920, x_baslik="", y_baslik="endeks")
    zaman_ekseni(fig, p1, adet=8, fmt="%d %b", row=1, col=1)
    zaman_ekseni(fig, p2, adet=7, fmt="%d %b", row=2, col=1)
    fig.update_xaxes(title_text="bar (indisle pinli)", row=2, col=1)
    kaydet(fig, "69_bas_omuz_tepesi", olcum=dict(
        enstruman="BIST100 günlük",
        sol_omuz=dict(indis=SOL, tarih=str(d.ts[SOL].date()), tepe=round(float(d.h[SOL]), 1)),
        bas=dict(indis=BAS, tarih=str(d.ts[BAS].date()), tepe=round(float(d.h[BAS]), 1)),
        sag_omuz_1=dict(indis=SAG1, tepe=round(float(d.h[SAG1]), 1)),
        sag_omuz_2=dict(indis=SAG2, tarih=str(d.ts[SAG2].date()),
                        tepe=round(float(d.h[SAG2]), 1)),
        boyun=round(boyun, 1), boyun_testleri=[465, 471, 473],
        H=round(H, 1), mm_hedefi=round(hedef, 1),
        gerceklesen_dip=round(dip, 1), dip_indis=dip_i, dip_tarih=str(d.ts[dip_i].date()),
        iskalama_puan=round(dip - hedef, 1),
        iskalama_yuzde=round(abs(dip - hedef) / hedef * 100, 2),
        sonrasi="boyun çizgisinin üstüne dönüş — kalıp başarısız"))


# ================================================================== 70  (GERÇEK)
def _donus_denemeleri(w, ileri=25):
    """Ayı trendinde boğa dönüş denemeleri ve sonuçları (mekanik tanım)."""
    out = []
    for i in range(2, len(w) - 12):
        g = float(w.h[i] - w.l[i])
        if g <= 0:
            continue
        alt_kuyruk = float(min(w.o[i], w.c[i]) - w.l[i])
        if not (w.c[i] > w.o[i] and alt_kuyruk > 0.30 * g and w.c[i] > w.l[i] + 0.6 * g):
            continue
        if w.l[i] > w.l[i - 1]:
            continue
        if w.h[i + 1] <= w.h[i]:            # tetiklenmemiş sinyal sayılmaz
            continue
        son = min(i + 1 + ileri, len(w))
        yeni_dip = bool(float(w.l[i + 1:son].min()) < float(w.l[i]))
        zirve = float(w.h[i + 1:son].max())
        out.append(dict(i=i, bayrak=yeni_dip, zirve=zirve))
    return out


def f70():
    """Dönüşlerin %80'i bayrağa döner — XU030 5dk, indis 1590–1679."""
    d = yukle("XU030.IS", "5m")
    if d is None:
        print("  ! 70 atlandı")
        return
    BAS, ADET = 1590, 90
    w = dilim(d, BAS, ADET)
    dn = _donus_denemeleri(w)
    bayrak = sum(1 for x in dn if x["bayrak"])
    oran = bayrak / len(dn) * 100

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.115, subplot_titles=(
        f"Panel 1 — güçlü ayı trendi içinde {len(dn)} boğa dönüş denemesi (numaralı)",
        f"Panel 2 — sonuçlar: {bayrak} tanesi BAYRAĞA döndü (yeni dip yapıldı), "
        f"{len(dn)-bayrak} tanesi dönüş oldu → %{oran:.0f}"))
    panel(fig, w, 1)
    panel(fig, w, 2)
    trend_cizgisi(fig, w, (2, 62), yon="bear", renk=GRI, dash="dash", row=1, col=1)

    for k, x in enumerate(dn, start=1):
        i = x["i"]
        kutu(fig, i - 0.45, i + 0.45, w.l[i], w.h[i], ALTIN, a=0.22, cizgi=1.2, row=1, col=1)
        not_(fig, i, float(w.l[i]) - 18, f"{k}", renk=ALTIN, ok=False, boyut=11,
             yanchor="top", row=1, col=1)
        renk = TURUNCU if x["bayrak"] else YESIL
        kutu(fig, i - 0.45, i + 0.45, w.l[i], w.h[i], renk, a=0.26, cizgi=1.3, row=2, col=1)
        not_(fig, i, float(x["zirve"]),
             f"{k}: " + ("bayrak" if x["bayrak"] else "DÖNÜŞ"), renk=renk,
             ax=(-46 if k % 2 else 46), ay=-26, boyut=10, row=2, col=1)
        fig.add_shape(type="line", x0=i, y0=float(w.l[i]), x1=i, y1=float(x["zirve"]),
                      line=dict(color=rgba(renk, 0.7), width=2.0), row=2, col=1)

    not_(fig, 6, float(w.h[:12].max()) + 25,
         "trend: köşeden köşeye, geri çekilmeler sığ", renk=BORDO, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    not_(fig, len(w) - 2, float(w.l.min()) + 26,
         f"{len(dn)} denemenin {bayrak}'i yeni dip gördü → deneme bir BAYRAKTI<br>"
         f"başarısızlık oranı %{oran:.0f} — Brooks'un %80 taban oranı",
         renk=MUREKKEP, ok=False, boyut=11, xanchor="right", row=2, col=1)

    lejant(fig, "dönüş denemesi (sinyal barı)", ALTIN)
    lejant(fig, "bayrağa döndü", TURUNCU)
    lejant(fig, "gerçek dönüş", YESIL)
    duzen(fig, "70 · Dönüşlerin %80'i bayrağa döner",
          f"XU030 5 dakika · indis {BAS}–{BAS+ADET-1} "
          f"({w.ts.iloc[0]:%d %b %H:%M} → {w.ts.iloc[-1]:%d %b %H:%M}) · pencere indisle pinli",
          h=920, x_baslik="", y_baslik="endeks")
    zaman_ekseni(fig, w, adet=8, fmt="%d %b %H:%M", row=1, col=1)
    zaman_ekseni(fig, w, adet=8, fmt="%d %b %H:%M", row=2, col=1)
    fig.update_xaxes(title_text="bar (indisle pinli)", row=2, col=1)
    kaydet(fig, "70_donuslerin_yuzde_sekseni", olcum=dict(
        enstruman="XU030 5dk", pencere=f"indis {BAS}–{BAS+ADET-1}",
        deneme_sayisi=len(dn), bayraga_donen=bayrak, gercek_donus=len(dn) - bayrak,
        basarisizlik_yuzdesi=round(oran, 1),
        deneme_indisleri=[BAS + x["i"] for x in dn],
        bayrak_mi=[x["bayrak"] for x in dn]))


# ================================================================== 71  (GERÇEK)
def _kt_short(w, ileri=20):
    """Boğa trendinde karşı trend short sinyalleri; 1R scalp hedefi tutuyor mu?"""
    out = []
    for i in range(2, len(w) - 8):
        g = float(w.h[i] - w.l[i])
        if g <= 0:
            continue
        ust_kuyruk = float(w.h[i] - max(w.o[i], w.c[i]))
        ayi = bool(w.c[i] < w.o[i] and w.c[i] < w.l[i] + 0.45 * g)
        kuyruklu = ust_kuyruk > 0.35 * g
        if not (ayi or kuyruklu):
            continue
        if w.h[i] < w.h[i - 1]:
            continue
        giris, stop = float(w.l[i]), float(w.h[i])
        if w.l[i + 1] >= giris or stop <= giris:
            continue
        risk = stop - giris
        hedef = giris - risk
        sonuc, nerede = "açık", None
        for j in range(i + 1, min(i + 1 + ileri, len(w))):
            if w.h[j] >= stop:
                sonuc, nerede = "stop", j
                break
            if w.l[j] <= hedef:
                sonuc, nerede = "hedef", j
                break
        out.append(dict(i=i, giris=giris, stop=stop, risk=risk, hedef=hedef,
                        sonuc=sonuc, nerede=nerede))
    return out


def f71():
    """Küçük zaman diliminde dönüş avının matematiği — XU030 5dk vs 15dk."""
    d5 = yukle("XU030.IS", "5m")
    d15 = yukle("XU030.IS", "15m")
    if d5 is None or d15 is None:
        print("  ! 71 atlandı")
        return
    B5, A5 = 5455, 62          # 5dk: 5455–5516
    B15, A15 = 1845, 38        # 15dk: 1845–1882
    w5 = dilim(d5, B5, A5)
    w15 = dilim(d15, B15, A15)
    ss = _kt_short(w5)

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.115, subplot_titles=(
        f"Panel 1 — KÜÇÜK zaman dilimi (5 dakika): {len(ss)} karşı trend short, "
        f"hiçbiri 1R scalp hedefine ulaşmıyor",
        "Panel 2 — BÜYÜK zaman dilimi (15 dakika): aynı gün tek bir mesaj — "
        "her geri çekilme bir trend yönlü alım"))
    panel(fig, w5, 1)
    panel(fig, w15, 2)

    for k, x in enumerate(ss, start=1):
        i = x["i"]
        kutu(fig, i - 0.45, i + 0.45, w5.l[i], w5.h[i], BORDO, a=0.22, cizgi=1.2,
             row=1, col=1)
        not_(fig, i, float(w5.h[i]) + 9, f"{k}", renk=BORDO, ok=False, boyut=11,
             yanchor="bottom", row=1, col=1)
        yatay(fig, x["hedef"], i - 0.4, min(i + 8, len(w5) - 1), renk=MOR, dash="dot",
              w=1.1, row=1, col=1)
        if x["nerede"] is not None and x["sonuc"] == "stop":
            not_(fig, x["nerede"], float(w5.h[x["nerede"]]) + 5, "✕", renk=TURUNCU,
                 ok=False, boyut=13, yanchor="bottom", row=1, col=1)
    ema_ciz(fig, w5, 20, renk=GRI, row=1, col=1, ad="20 bar EMA (5dk)")
    not_(fig, len(w5) - 2, float(w5.l.min()) + 20,
         f"{len(ss)} short · {sum(1 for x in ss if x['sonuc']=='stop')} stop · "
         f"{sum(1 for x in ss if x['sonuc']=='hedef')} hedef<br>"
         "✕ = stop yendi · nokta çizgi = 1R scalp hedefi",
         renk=MUREKKEP, ok=False, boyut=10, xanchor="right", row=1, col=1)

    # panel 2 — aynı dönem gölgelenir + tek trend yönlü kurulum
    g0 = int(w15.index[w15.ts >= w5.ts.iloc[0]][0])
    g1 = int(w15.index[w15.ts <= w5.ts.iloc[-1]][-1])
    kutu(fig, g0 - 0.5, g1 + 0.5, float(w15.l.min()), float(w15.h.max()), ALTIN, a=0.07,
         cizgi=1.0, dash="dot", row=2, col=1)
    not_(fig, (g0 + g1) / 2, float(w15.h.max()),
         "panel 1'in penceresi", renk=ALTIN, ok=False, boyut=10, yanchor="bottom",
         row=2, col=1)
    isaret = bar_say(w15, "bull")
    bar_etiketle(fig, w15, isaret, yon="bull", row=2, col=1)
    sig = 1866 - B15
    o = islem(fig, w15, sinyal=sig, yon="bull", giris=float(d15.h[1866]),
              stop=float(d15.l[1866]), hedefler=(float(d15.h[1873]),),
              etiketler=("swing hedefi",), row=2, col=1, ondalik=1)
    not_(fig, sig, float(d15.l[1866]) - 45,
         "trend yönlü H1 alımı: risk küçük, hedef trendin kendisi", renk=TEAL,
         ax=-30, ay=48, boyut=10, row=2, col=1)
    ema_ciz(fig, w15, 20, renk=GRI, row=2, col=1, ad="20 bar EMA (15dk)")

    lejant(fig, "karşı trend short sinyali", BORDO)
    lejant(fig, "trend yönlü sinyal barı", ALTIN)
    lejant_cizgi(fig, "1R scalp hedefi", MOR, dash="dot")
    duzen(fig, "71 · Küçük zaman diliminde dönüş avının matematiği",
          f"XU030 · panel 1: 5 dakika indis {B5}–{B5+A5-1}, panel 2: 15 dakika indis "
          f"{B15}–{B15+A15-1} · önbellekte 1 dakikalık veri olmadığı için müfredatın "
          "1dk+5dk ikilisi 5dk+15dk'ya çevrildi",
          h=940, x_baslik="", y_baslik="endeks")
    zaman_ekseni(fig, w5, adet=8, fmt="%d %b %H:%M", row=1, col=1)
    zaman_ekseni(fig, w15, adet=8, fmt="%d %b %H:%M", row=2, col=1)
    fig.update_xaxes(title_text="bar (indisle pinli)", row=2, col=1)
    kaydet(fig, "71_kucuk_zaman_dilimi_donus", olcum=dict(
        kucuk_tf="XU030 5dk", buyuk_tf="XU030 15dk",
        pencere_5dk=f"indis {B5}–{B5+A5-1}", pencere_15dk=f"indis {B15}–{B15+A15-1}",
        short_sayisi=len(ss),
        stop_olan=sum(1 for x in ss if x["sonuc"] == "stop"),
        hedefe_varan=sum(1 for x in ss if x["sonuc"] == "hedef"),
        short_indisleri=[B5 + x["i"] for x in ss],
        ortalama_risk=round(float(np.mean([x["risk"] for x in ss])), 1),
        trend_yonlu_giris=round(o["giris"], 1), trend_yonlu_stop=round(o["stop"], 1),
        trend_yonlu_risk=round(o["risk"], 1),
        trend_yonlu_hedef_R=round(o["r"][0], 1)))


# ================================================================== 72  (GERÇEK)
def f72():
    """Mıknatıs haritası — USDTRY günlük, indis 148–272."""
    d = yukle("USDTRY=X", "1d")
    if d is None:
        print("  ! 72 atlandı")
        return
    B, A = 148, 125
    w = dilim(d, B, A)
    uc = float(d.h[151])                       # spike zirvesi (önceki uç)
    uc_varis = next(i for i in range(152, B + A) if float(d.h[i]) >= uc)
    bacak_dip, bacak_tepe = float(d.l[151]), float(d.h[156])
    boy = bacak_tepe - bacak_dip
    pb = float(d.l[166])
    mm = pb + boy
    mm_varis = next(i for i in range(167, B + A) if float(d.h[i]) >= mm)
    yuv = 40.0
    yuv_varis = next(i for i in range(152, B + A) if float(d.h[i]) >= yuv)
    bant = d.iloc[152:176]
    bl, bh = float(bant.l.min()), float(bant.h.max())
    orta = (bl + bh) / 2
    orta_dokunus = [i for i in range(152, B + A) if float(d.l[i]) <= orta <= float(d.h[i])]

    fig = go.Figure()
    panel(fig, w, None)
    e = ema_ciz(fig, w, 20, renk=GRI, ad="20 gün EMA (mıknatıs)")
    n = len(w) - 1

    yatay(fig, uc, 151 - B, n, renk=BORDO, dash="dash", w=1.8)
    not_(fig, n, uc, f"ÖNCEKİ UÇ {uc:.3f}", renk=BORDO, ok=False, boyut=10, xanchor="left")
    not_(fig, 151 - B, uc + 0.12,
         f"19 Mar 2025 spike zirvesi — {uc_varis-151} bar sonra ({d.ts[uc_varis]:%d %b %Y}) "
         "yeniden dokunuldu", renk=BORDO, ax=90, ay=-26, boyut=10)
    not_(fig, uc_varis - B, uc + 0.05, "dokunuş", renk=BORDO, ax=0, ay=-34, boyut=10)

    yatay(fig, yuv, 0, n, renk=ALTIN, dash="dash", w=1.6)
    not_(fig, n, yuv, "YUVARLAK SAYI 40,00", renk=ALTIN, ok=False, boyut=10, xanchor="left")
    not_(fig, 227 - B, float(d.h[227]) - 0.22,
         f"bir tick kala: {d.h[227]:.3f} ({d.ts[227]:%d %b}) → ertesi gün {d.h[228]:.3f}",
         renk=ALTIN, ax=-96, ay=34, boyut=10)

    yatay(fig, mm, 166 - B, n, renk=MOR, dash="dash", w=1.6)
    not_(fig, n, mm, f"MM HEDEFİ {mm:.3f}", renk=MOR, ok=False, boyut=10, xanchor="left")
    cizgi(fig, 151 - B, bacak_dip, 156 - B, bacak_tepe, renk=MOR, dash="dot", w=1.5)
    fig.add_shape(type="line", x0=166 - B, y0=pb, x1=166 - B, y1=mm,
                  line=dict(color=MOR, width=2.4))
    not_(fig, 166 - B, (pb + mm) / 2, f"bacak boyu {boy:.3f}<br>geri çekilme dibi {pb:.3f}",
         renk=MOR, ax=-46, ay=-16, boyut=10)
    not_(fig, mm_varis - B, float(d.h[mm_varis]) + 0.10,
         f"MM'ye varış {d.h[mm_varis]:.3f} ({d.ts[mm_varis]:%d %b %Y})", renk=MOR,
         ax=-24, ay=-34, boyut=10)

    kutu(fig, 152 - B, 175 - B, bl, bh, GRI, a=0.10, cizgi=1.0, dash="dot")
    yatay(fig, orta, 152 - B, 200 - B, renk=TEAL, dash="dashdot", w=1.5)
    not_(fig, 200 - B, orta, f"BANT ORTASI {orta:.3f} ({len(orta_dokunus)} bar dokundu)",
         renk=TEAL, ok=False, boyut=10, xanchor="left")
    not_(fig, 163 - B, bl - 0.18, f"spike sonrası bant {bl:.3f}–{bh:.3f}", renk=GRI,
         ok=False, boyut=10, yanchor="top")
    not_(fig, 120, float(e.iloc[120]) - 0.30,
         "20 gün EMA: her geri çekilmenin mıknatısı", renk=GRI, ax=-40, ay=42, boyut=10)

    lejant_cizgi(fig, "önceki uç", BORDO)
    lejant_cizgi(fig, "yuvarlak sayı", ALTIN)
    lejant_cizgi(fig, "ölçülmüş hareket hedefi", MOR)
    lejant_cizgi(fig, "bant ortası", TEAL, dash="dashdot")
    duzen(fig, "72 · Mıknatıs haritası: bir grafikte bütün mıknatıslar",
          f"USDTRY günlük · indis {B}–{B+A-1} ({w.ts.iloc[0]:%d %b %Y} → "
          f"{w.ts.iloc[-1]:%d %b %Y}) · pencere indisle pinli",
          h=700, y_baslik="USDTRY", x_baslik="bar (indisle pinli)")
    zaman_ekseni(fig, w, adet=9, fmt="%d %b")
    kaydet(fig, "72_miknatis_haritasi", olcum=dict(
        enstruman="USDTRY günlük", pencere=f"indis {B}–{B+A-1}",
        onceki_uc=round(uc, 3), onceki_uc_indis=151,
        onceki_uc_varis_indis=uc_varis, onceki_uc_varis_tarih=str(d.ts[uc_varis].date()),
        onceki_uc_bekleme_bar=uc_varis - 151,
        yuvarlak_sayi=yuv, yuvarlak_varis_indis=yuv_varis,
        yuvarlak_bir_tick_kala=round(float(d.h[227]), 3),
        mm_bacak=round(boy, 3), mm_geri_cekilme=round(pb, 3), mm_hedefi=round(mm, 3),
        mm_varis_indis=mm_varis, mm_varis_yuksek=round(float(d.h[mm_varis]), 3),
        bant=f"{bl:.3f}–{bh:.3f}", bant_ortasi=round(orta, 3),
        bant_ortasi_dokunus=len(orta_dokunus),
        ema20_son=round(float(e.iloc[-1]), 3)))


# ================================================================== 73
def f73():
    """Vakum: emirlerin çekilmesi ve mıknatısta geri dönmesi."""
    fiyat = 100.0
    miknatis = 105.0
    seviye = [float(f"{x:.1f}") for x in np.arange(96.5, 106.6, 0.5)]
    # normal derinlik ile vakum derinliği
    normal, vakum, renkler = [], [], []
    for s in seviye:
        if s > fiyat:
            n = 34 - abs(s - fiyat) * 2
            v = 3.0 if s < miknatis - 0.2 else 46.0
        else:
            n = 34 - abs(s - fiyat) * 2
            v = 6.0 if s > fiyat - 2.6 else 24.0
        normal.append(max(n, 8.0))
        vakum.append(v)
        renkler.append(BORDO if s > fiyat else TEAL)

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13, subplot_titles=(
        "Panel 1 — emir defteri (kavramsal): mıknatısın altındaki satış emirleri çekildi",
        "Panel 2 — fiyat karşılığı: vakumda hızlanma, mıknatısta agresif ters işlem"))
    fig.add_trace(go.Bar(y=seviye, x=normal, orientation="h", name="normal derinlik",
                         marker=dict(color=rgba(GRI, 0.30),
                                     line=dict(color=rgba(GRI, 0.55), width=0.8)),
                         width=0.22, offset=-0.23), row=1, col=1)
    fig.add_trace(go.Bar(y=seviye, x=vakum, orientation="h",
                         name="vakum anındaki derinlik (üstte satış, altta alış)",
                         marker=dict(color=[rgba(r, 0.55) for r in renkler],
                                     line=dict(color=renkler, width=1.0)),
                         width=0.22, offset=0.01), row=1, col=1)
    yatay(fig, fiyat, 0, 50, renk=MAVI, dash="solid", w=1.8, row=1, col=1)
    not_(fig, 50, fiyat, "son fiyat 100,0", renk=MAVI, ok=False, boyut=10, xanchor="left",
         row=1, col=1)
    yatay(fig, miknatis, 0, 50, renk=ALTIN, dash="dash", w=1.8, row=1, col=1)
    not_(fig, 50, miknatis, "MIKNATIS 105,0", renk=ALTIN, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    kutu(fig, 0, 50, 100.4, 104.6, TURUNCU, a=0.10, cizgi=1.0, dash="dot", row=1, col=1)
    not_(fig, 26, 102.5,
         "VAKUM: ayılar 105'e kadar satmıyor —<br>emirlerini çektiler, boşluk kaldı",
         renk=TURUNCU, ok=False, boyut=11, row=1, col=1)
    not_(fig, 46, 105.0, "mıknatısta devasa satış duvarı geri döndü", renk=BORDO,
         ax=-70, ay=-30, boyut=10, row=1, col=1)
    not_(fig, 20, 98.4, "boğalar da bekliyor: fiyat mıknatısa gidecek,<br>"
                        "aşağıda alıcı da seyrekleşti", renk=TEAL, ok=False, boyut=10,
         row=1, col=1)

    # panel 2 — fiyat
    on = yol_uret(20, 96.9, 0.10, 0.24, tohum=7301)
    on = kaydir(on, 100.0 - on[-1][3])
    hizlanma = [
        bar(100.00, 101.10, 0.15, 0.10),
        bar(101.10, 102.60, 0.18, 0.08),
        bar(102.60, 104.30, 0.20, 0.10),
        bar(104.30, 104.70, 0.50, 0.12),   # klimaks: 105,20 — mıknatısı bir tick aştı
        bar(104.70, 103.40, 0.14, 0.25),   # agresif ters işlem
        bar(103.40, 102.20, 0.16, 0.28),
        bar(102.20, 102.70, 0.35, 0.30),
        bar(102.70, 101.40, 0.18, 0.32),
        bar(101.40, 100.60, 0.20, 0.30),
        bar(100.60, 101.10, 0.35, 0.28),
        bar(101.10, 100.40, 0.22, 0.30),
        bar(100.40, 99.70, 0.20, 0.32),
        bar(99.70, 100.20, 0.32, 0.28),
        bar(100.20, 99.30, 0.18, 0.34),
        bar(99.30, 98.60, 0.20, 0.30),
        bar(98.60, 99.10, 0.34, 0.26),
    ]
    d2 = df_yap(on + hizlanma)
    panel(fig, d2, 2)
    b0 = len(on)
    yatay(fig, miknatis, 0, len(d2) - 1, renk=ALTIN, dash="dash", w=1.8, row=2, col=1)
    not_(fig, len(d2) - 1, miknatis, "MIKNATIS 105,0", renk=ALTIN, ok=False, boyut=10,
         xanchor="left", row=2, col=1)
    kutu(fig, b0 - 0.5, b0 + 3.5, 100.4, 105.2, TURUNCU, a=0.10, cizgi=1.0, dash="dot",
         row=2, col=1)
    not_(fig, b0 + 1.4, 101.2, "vakum bölgesi: karşı taraf yok,<br>barlar büyüyor",
         renk=TURUNCU, ok=False, boyut=10, row=2, col=1)
    kl = b0 + 3
    kutu(fig, kl - 0.45, kl + 0.45, d2.l[kl], d2.h[kl], BORDO, a=0.22, cizgi=1.3,
         row=2, col=1)
    not_(fig, kl, float(d2.h[kl]) + 0.25,
         "klimaks barı: mıknatısı bir tick aştı,<br>üst kuyrukla kapandı", renk=BORDO,
         ax=52, ay=-34, boyut=10, row=2, col=1)
    not_(fig, kl + 1, float(d2.c[kl + 1]) - 0.5,
         "mıknatısta agresif satış: emirler geri döndü", renk=BORDO, ax=64, ay=36,
         boyut=10, row=2, col=1)
    lejant_cizgi(fig, "mıknatıs", ALTIN)
    duzen(fig, "73 · Vakum: emirlerin çekilmesi ve geri dönmesi",
          "mıknatısa kadar boşluk, mıknatısta duvar", h=920, sematik=True, x_baslik="")
    fig.update_xaxes(title_text="bekleyen emir büyüklüğü (kavramsal birim)", row=1, col=1)
    fig.update_xaxes(title_text="bar sırası", row=2, col=1)
    fig.update_yaxes(title_text="fiyat seviyesi", row=1, col=1)
    fig.update_layout(barmode="overlay")
    kaydet(fig, "73_vakum", olcum=dict(
        son_fiyat=100.0, miknatis=105.0, vakum_bolgesi="100,4–104,6",
        klimaks_tepesi=105.20, asim=0.20, donus_dibi=100.30))


# ================================================================== 74
def f74():
    """Spike tabanlı ölçülmüş hareket ve ölçüm noktası permütasyonu."""
    on = yol_uret(18, 96.2, 0.06, 0.22, tohum=7401)
    on = kaydir(on, 97.92 - on[-1][3])
    spike = [
        bar(98.00, 99.40, 0.14, 0.22),   # spike barı 1 (açılış 98,00 · dip 97,78)
        bar(99.40, 100.80, 0.16, 0.08),
        bar(100.80, 102.10, 0.18, 0.10),
        bar(102.10, 103.30, 0.42, 0.10),  # spike barı 4 (kapanış 103,30 · tepe 103,72)
    ]
    sonra = [
        bar(103.30, 102.70, 0.20, 0.30),
        bar(102.70, 103.60, 0.35, 0.20),
        bar(103.60, 104.40, 0.28, 0.22),
        bar(104.40, 105.30, 0.30, 0.25),
        bar(105.30, 104.90, 0.28, 0.32),
        bar(104.90, 106.00, 0.35, 0.22),
        bar(106.00, 106.90, 0.30, 0.28),
        bar(106.90, 107.90, 0.32, 0.25),
        bar(107.90, 107.40, 0.30, 0.35),
        bar(107.40, 108.60, 0.40, 0.25),
        bar(108.60, 109.40, 0.32, 0.30),
    ]
    d = df_yap(on + spike + sonra)
    s0 = len(on)
    s1 = s0 + len(spike) - 1
    onceki_kapanis = float(d.c[s0 - 1])
    acilis = float(d.o[s0])
    dip = float(d.l[s0:s1 + 1].min())
    tepe = float(d.h[s0:s1 + 1].max())
    kapanis = float(d.c[s1])
    capa = kapanis                       # projeksiyon çıpası: spike'ın kapanışı

    olcumler = [
        ("A", "ilk barın açılışı → son barın kapanışı", acilis, kapanis, MAVI),
        ("B", "spike öncesi barın kapanışı → son barın kapanışı", onceki_kapanis, kapanis, TEAL),
        ("C", "spike'ın dibi → spike'ın tepesi (en agresif)", dip, tepe, BORDO),
        ("D", "spike'ın dibi → son barın kapanışı", dip, kapanis, MOR),
    ]
    fig = go.Figure()
    panel(fig, d, None)
    kutu(fig, s0 - 0.5, s1 + 0.5, dip, tepe, ALTIN, a=0.10, cizgi=1.2)
    not_(fig, (s0 + s1) / 2, dip - 0.35, "spike (4 bar)", renk=ALTIN, ok=False, boyut=11,
         yanchor="top")
    n = len(d) - 1
    satir = []
    for k, (ad, aciklama, y0, y1, renk) in enumerate(olcumler):
        x = s0 - 5.2 + k * 1.25
        boy = y1 - y0
        hedef = capa + boy
        fig.add_shape(type="line", x0=x, y0=y0, x1=x, y1=y1,
                      line=dict(color=renk, width=3.0))
        not_(fig, x, y1 + 0.16, ad, renk=renk, ok=False, boyut=12, yanchor="bottom")
        not_(fig, x, y0 - 0.16, f"{boy:.2f}", renk=renk, ok=False, boyut=9, yanchor="top")
        yatay(fig, hedef, s1 + 1, n, renk=renk, dash="dash", w=1.4)
        varildi = "✓" if float(d.h[s1 + 1:].max()) >= hedef else "—"
        satir.append(f"<span style='color:{renk}'><b>{ad}</b> boy {boy:.2f} → "
                     f"hedef {hedef:.2f} {varildi}</span>")
    not_(fig, n, float(d.l.min()) + 1.6, "<br>".join(satir), renk=MUREKKEP, ok=False,
         boyut=10, xanchor="right")
    # muhafazakâr seçim = en küçük boy
    en_kucuk = min(olcumler, key=lambda t: t[3] - t[2])
    ek_hedef = capa + (en_kucuk[3] - en_kucuk[2])
    kutu(fig, s1 + 1, n, ek_hedef - 0.10, ek_hedef + 0.10, YESIL, a=0.20, cizgi=1.2)
    not_(fig, s1 + 2, ek_hedef,
         f"MUHAFAZAKÂR SEÇİM: {en_kucuk[0]} — en küçük boy.<br>"
         "Hedefe önce varılır; ıskalayıp geri dönme riski en düşük.",
         renk=YESIL, ax=30, ay=-56, boyut=10)
    yatay(fig, capa, s1, n, renk=GRI, dash="dot", w=1.2)
    not_(fig, s1 + 0.4, capa - 0.30, "projeksiyon çıpası: spike'ın kapanışı", renk=GRI,
         ok=False, boyut=10, xanchor="left", yanchor="top")
    aciklama = "<br>".join(f"<b>{a}</b> — {b}" for a, b, *_ in olcumler)
    not_(fig, 0.3, float(d.h.max()) + 0.4, aciklama, renk=MUREKKEP, ok=False, boyut=10,
         xanchor="left", yanchor="top")
    duzen(fig, "74 · Spike tabanlı ölçülmüş hareket: dört geçerli ölçüm noktası",
          "aynı spike, dört boy, dört hedef — hangisini seçtiğin işlem denklemini değiştirir",
          h=680, sematik=True)
    kaydet(fig, "74_spike_olculmus_hareket", olcum=dict(
        spike_acilis=round(acilis, 2), spike_onceki_kapanis=round(onceki_kapanis, 2),
        spike_dip=round(dip, 2), spike_tepe=round(tepe, 2), spike_kapanis=round(kapanis, 2),
        capa=round(capa, 2),
        olcumler={a: dict(boy=round(y1 - y0, 2), hedef=round(capa + (y1 - y0), 2))
                  for a, _b, y0, y1, _r in olcumler},
        muhafazakar=en_kucuk[0]))


# ================================================================== 75
def f75():
    """Leg 1 = Leg 2 (AB=CD)."""
    bacak1 = [
        bar(100.00, 100.90, 0.25, 0.40),   # A dibi 99,60
        bar(100.90, 101.90, 0.22, 0.15),
        bar(101.90, 102.80, 0.20, 0.18),
        bar(102.80, 103.70, 0.24, 0.16),
        bar(103.70, 104.40, 0.45, 0.18),   # B tepesi 104,85
    ]
    duzeltme = [
        bar(104.40, 103.60, 0.20, 0.30),
        bar(103.60, 102.90, 0.18, 0.28),
        bar(102.90, 103.20, 0.30, 0.35),
        bar(103.20, 102.35, 0.16, 0.35),   # C dibi 102,00
        bar(102.35, 103.00, 0.28, 0.22),
    ]
    bacak2 = [
        bar(103.00, 103.90, 0.22, 0.20),
        bar(103.90, 104.80, 0.24, 0.16),
        bar(104.80, 105.60, 0.20, 0.20),
        bar(105.60, 106.20, 0.30, 0.22),
        bar(106.20, 105.80, 0.25, 0.32),
        bar(105.80, 106.70, 0.28, 0.20),
        bar(106.70, 107.00, 0.35, 0.22),   # D tepesi 107,35
        bar(107.00, 106.50, 0.25, 0.40),
        bar(106.50, 105.90, 0.28, 0.35),
        bar(105.90, 106.60, 0.35, 0.30),
        bar(106.60, 105.80, 0.25, 0.38),
        bar(105.80, 106.40, 0.34, 0.28),
    ]
    on = yol_uret(16, 97.0, 0.10, 0.22, tohum=7501)
    on = kaydir(on, 100.00 - on[-1][3])
    d = df_yap(on + bacak1 + duzeltme + bacak2)
    o = len(on)
    A, B = o + 0, o + 4
    C = o + len(bacak1) + 3
    D = o + len(bacak1) + len(duzeltme) + 6
    yA, yB, yC = float(d.l[A]), float(d.h[B]), float(d.l[C])
    boy = yB - yA
    yD = yC + boy

    fig = go.Figure()
    panel(fig, d, None)
    for x, y, ad, renk, yer in ((A, yA, "A", TEAL, "top"), (B, yB, "B", BORDO, "bottom"),
                                (C, yC, "C", TEAL, "top"), (D, yD, "D", MOR, "bottom")):
        not_(fig, x, y + (0.55 if yer == "bottom" else -0.45), ad, renk=renk, ok=False,
             boyut=14, yanchor=yer)
    cizgi(fig, A, yA, B, yB, renk=TEAL, dash="dot", w=1.8)
    cizgi(fig, B, yB, C, yC, renk=GRI, dash="dot", w=1.4)
    cizgi(fig, C, yC, D, yD, renk=MOR, dash="dot", w=1.8)
    fig.add_shape(type="line", x0=A - 1.2, y0=yA, x1=A - 1.2, y1=yB,
                  line=dict(color=TEAL, width=2.6))
    not_(fig, A - 1.4, (yA + yB) / 2, f"Leg 1 = B − A = {boy:.2f}", renk=TEAL, ok=False,
         boyut=11, xanchor="right")
    fig.add_shape(type="line", x0=D + 2.0, y0=yC, x1=D + 2.0, y1=yD,
                  line=dict(color=MOR, width=2.6))
    not_(fig, D + 2.2, (yC + yD) / 2, f"Leg 2 = {boy:.2f}", renk=MOR, ok=False, boyut=11,
         xanchor="left")
    yatay(fig, yD, C, len(d) - 1, renk=MOR, dash="dash", w=1.6)
    not_(fig, len(d) - 1, yD, f"D = C + (B − A) = {yD:.2f}", renk=MOR, ok=False, boyut=10,
         xanchor="left")
    yatay(fig, yA, A, C + 2, renk=GRI, dash="dot", w=1.1)
    yatay(fig, yB, B, D, renk=GRI, dash="dot", w=1.1)
    yatay(fig, yC, C, D, renk=GRI, dash="dot", w=1.1)
    not_(fig, (B + C) / 2, yC - 0.55,
         "ABC düzeltmesi: C dibi A'nın üstünde kaldı → boğa yapısı bozulmadı",
         renk=GRI, ok=False, boyut=10)
    not_(fig, D, yD,
         f"hedefe varış: bar {D} · tepe {float(d.h[D]):.2f}", renk=MOR, ax=-64, ay=-56,
         boyut=10)
    duzen(fig, "75 · Leg 1 = Leg 2 (AB = CD)",
          "iki bacaklı hareketin ikinci bacağı birincisi kadar olur — Brooks'un en sık "
          "kullandığı ölçülmüş hareket", h=660, sematik=True)
    kaydet(fig, "75_ab_cd", olcum=dict(
        A=round(yA, 2), B=round(yB, 2), C=round(yC, 2), D_hedef=round(yD, 2),
        leg=round(boy, 2), formul="D = C + (B − A)",
        gerceklesen_tepe=round(float(d.h[D]), 2), hedefe_varildi=bool(float(d.h[D]) >= yD)))


# ================================================================== 76
KAMA_MM_SONRASI = [
    bar(4.35, 3.55, 0.12, 0.18),   # 15 kırılım barı (short giriş 4,23)
    bar(3.55, 2.80, 0.15, 0.20),   # 16 son geri çekilme dibi 2,80 kırılıyor
    bar(2.80, 3.10, 0.25, 0.20),   # 17
    bar(3.10, 2.20, 0.15, 0.25),   # 18
    bar(2.20, 1.40, 0.18, 0.22),   # 19
    bar(1.40, 0.60, 0.20, 0.25),   # 20
    bar(0.60, 0.90, 0.25, 0.20),   # 21
    bar(0.90, 0.05, 0.15, 0.25),   # 22
    bar(0.05, -0.75, 0.18, 0.25),  # 23
    bar(-0.75, -0.20, 0.25, 0.20), # 24
    bar(-0.20, -0.95, 0.15, 0.25), # 25
    bar(-0.95, -1.70, 0.18, 0.22), # 26
    bar(-1.70, -1.35, 0.25, 0.20), # 27
    bar(-1.35, -2.20, 0.15, 0.25), # 28
    bar(-2.20, -2.55, 0.18, 0.30), # 29 hedef −2,65 aşıldı (dip −2,85)
    bar(-2.55, -2.10, 0.30, 0.20), # 30
]


def f76():
    """Kama ölçülü hareketi — kama yüksekliği kırılım noktasından projekte."""
    on = yol_uret(12, -4.2, 0.35, 0.28, tohum=7601)
    dy = on[-1][3]
    d = df_yap(on + kaydir(KAMA_YUKARI + KAMA_MM_SONRASI, dy))
    ofs = len(on)
    taban = KAMA_TEPE_Y * -1 + dy      # kamanın tabanı (−0,25 aynalandı)
    tepe = KAMA_DIP_Y * -1 + dy        # kamanın tepesi (+5,20)
    H = tepe - taban
    kirilim = -2.80 * -1 + dy          # son geri çekilme dibi = kırılım noktası (+2,80)
    hedef = kirilim - H

    fig = go.Figure()
    panel(fig, d, None)
    kama_ciz(fig, ofs, dy, None, yon="yukari", uzat=K_ITIS3 + 4)
    s = ofs + K_ITIS3
    kutu(fig, s - 0.45, s + 0.45, d.l[s], d.h[s], ALTIN, a=0.22, cizgi=1.3)
    not_(fig, s, float(d.h[s]) + 0.35, "kama dönüş sinyali (sat)", renk=ALTIN, ok=False,
         boyut=10, yanchor="bottom")
    # kama yüksekliği
    xb = ofs + 1
    fig.add_shape(type="line", x0=xb, y0=taban, x1=xb, y1=tepe,
                  line=dict(color=MOR, width=2.8))
    not_(fig, xb - 0.35, (taban + tepe) / 2,
         f"kama yüksekliği<br>H = {tepe:.2f} − {taban:.2f} = {H:.2f}", renk=MOR, ok=False,
         boyut=10, xanchor="right")
    yatay(fig, taban, ofs, ofs + 6, renk=GRI, dash="dot", w=1.1)
    yatay(fig, tepe, ofs + K_ITIS3 - 3, len(d) - 1, renk=GRI, dash="dot", w=1.1)
    # kırılım noktası
    xk = ofs + 16
    yatay(fig, kirilim, ofs + K_RALLI2, len(d) - 1, renk=ALTIN, dash="dash", w=1.6)
    not_(fig, ofs + K_RALLI2, kirilim,
         f"KIRILIM NOKTASI {kirilim:.2f}<br>(kamanın son geri çekilme dibi)", renk=ALTIN,
         ax=-70, ay=44, boyut=10)
    fig.add_shape(type="line", x0=xk, y0=kirilim, x1=xk, y1=hedef,
                  line=dict(color=MOR, width=2.8))
    not_(fig, xk, (kirilim + hedef) / 2, "H kadar AŞAĞI projeksiyon", renk=MOR, ax=76,
         ay=0, boyut=10)
    yatay(fig, hedef, xk, len(d) - 1, renk=MOR, dash="dash", w=1.7)
    not_(fig, len(d) - 1, hedef, f"kama MM hedefi {hedef:.2f}", renk=MOR, ok=False,
         boyut=10, xanchor="left")
    sonra = ofs + K_ITIS3
    dip_i = int(np.argmin(d.l.values[sonra:])) + sonra
    dip_y = float(d.l[dip_i])
    not_(fig, dip_i, dip_y - 0.30,
         f"varış: bar {dip_i} · dip {dip_y:.2f}", renk=MOR, ax=-20, ay=40, boyut=10)
    lejant(fig, "kama sinyal barı", ALTIN)
    lejant_cizgi(fig, "kama çizgileri", GRI)
    lejant_cizgi(fig, "kırılım noktası", ALTIN)
    lejant_cizgi(fig, "kama MM hedefi", MOR)
    duzen(fig, "76 · Kama ölçülü hareketi",
          "kama yüksekliği H, kırılım noktasından projekte edilir", h=680, sematik=True)
    kaydet(fig, "76_kama_olculmus_hareket", olcum=dict(
        kama_tabani=round(taban, 2), kama_tepesi=round(tepe, 2), H=round(H, 2),
        kirilim_noktasi=round(kirilim, 2), hedef=round(hedef, 2),
        gerceklesen_dip=round(dip_y, 2),
        hedefe_varildi=bool(dip_y <= hedef), itis_sayisi=3))


# ================================================================== 77
def f77():
    """Ölçüm boşluğu: kırılım noktası ile ilk duraklama arası."""
    bant = [
        bar(100.00, 100.60, 0.30, 0.35),
        bar(100.60, 99.90, 0.25, 0.40),   # bant dibi 99,50
        bar(99.90, 100.70, 0.35, 0.30),
        bar(100.70, 100.10, 0.28, 0.38),
        bar(100.10, 100.80, 0.40, 0.25),   # bant tepesi 101,20
        bar(100.80, 100.20, 0.25, 0.42),
        bar(100.20, 100.90, 0.30, 0.28),
        bar(100.90, 100.35, 0.26, 0.40),
        bar(100.35, 100.95, 0.25, 0.30),
        bar(100.95, 100.30, 0.22, 0.44),
        bar(100.30, 100.85, 0.32, 0.26),
        bar(100.85, 100.25, 0.24, 0.38),
        bar(100.25, 100.90, 0.28, 0.30),
        bar(100.90, 100.40, 0.24, 0.36),
    ]
    kirilim = [
        bar(100.40, 101.90, 0.22, 0.12),   # kırılım barı
        bar(101.90, 103.30, 0.20, 0.10),
        bar(103.30, 104.60, 0.24, 0.08),
    ]
    duraklama = [
        bar(104.60, 104.10, 0.30, 0.35),   # ilk duraklama; dip 103,75
        bar(104.10, 104.55, 0.35, 0.28),
        bar(104.55, 104.20, 0.28, 0.45),   # duraklamanın dibi 103,75
    ]
    devam = [
        bar(104.20, 104.75, 0.20, 0.18),
        bar(104.75, 105.10, 0.18, 0.22),
        bar(105.10, 104.80, 0.22, 0.28),
        bar(104.80, 105.35, 0.22, 0.20),
        bar(105.35, 105.05, 0.20, 0.26),
        bar(105.05, 105.45, 0.24, 0.22),   # hedef 105,45 · tepe 105,69
        bar(105.45, 105.10, 0.22, 0.30),
        bar(105.10, 105.50, 0.26, 0.24),
        bar(105.50, 105.15, 0.20, 0.32),
        bar(105.15, 104.70, 0.22, 0.30),
        bar(104.70, 105.20, 0.30, 0.26),
    ]
    d = df_yap(bant + kirilim + duraklama + devam)
    nb = len(bant)
    kir_nokta = float(max(b[1] for b in bant))          # bant tepesi = kırılım noktası
    dur0 = nb + len(kirilim)
    dur_dip = float(d.l[dur0:dur0 + len(duraklama)].min())
    bosluk = dur_dip - kir_nokta
    orta = (kir_nokta + dur_dip) / 2
    bas = float(min(b[2] for b in bant))                # hareketin başlangıcı = bant dibi
    hedef = bas + 2 * (orta - bas)
    n = len(d) - 1

    fig = go.Figure()
    panel(fig, d, None)
    kutu(fig, -0.5, nb - 0.5, bas, kir_nokta, GRI, a=0.10, cizgi=1.1, dash="dot")
    not_(fig, nb - 1.5, bas - 0.30, "yatay bant", renk=GRI, ok=False, boyut=10,
         yanchor="top")
    yatay(fig, kir_nokta, 0, n, renk=ALTIN, dash="dash", w=1.6)
    not_(fig, n, kir_nokta, f"kırılım noktası {kir_nokta:.2f}", renk=ALTIN, ok=False,
         boyut=10, xanchor="left")
    yatay(fig, dur_dip, nb, n, renk=ALTIN, dash="dash", w=1.6)
    not_(fig, n, dur_dip, f"ilk duraklamanın dibi {dur_dip:.2f}", renk=ALTIN, ok=False,
         boyut=10, xanchor="left")
    kutu(fig, dur0 - 0.5, n, kir_nokta, dur_dip, ALTIN, a=0.20, cizgi=1.2)
    not_(fig, dur0 + 1.0, (kir_nokta + dur_dip) / 2,
         f"ÖLÇÜM BOŞLUĞU {bosluk:.2f}<br>kırılımdan sonra piyasa bu şeride<br>"
         "bir daha hiç girmedi", renk=ALTIN, ax=64, ay=64, boyut=10)
    yatay(fig, orta, 0, n, renk=MOR, dash="dashdot", w=1.6)
    not_(fig, n, orta, f"boşluğun ortası {orta:.2f}", renk=MOR, ok=False, boyut=10,
         xanchor="left")
    yatay(fig, bas, 0, n, renk=TEAL, dash="dot", w=1.4)
    not_(fig, n, bas, f"hareketin başlangıcı {bas:.2f}", renk=TEAL, ok=False, boyut=10,
         xanchor="left")
    yatay(fig, hedef, dur0, n, renk=MOR, dash="dash", w=1.8)
    not_(fig, n, hedef, f"hedef {hedef:.2f}", renk=MOR, ok=False, boyut=10, xanchor="left")
    xp = 2.0
    fig.add_shape(type="line", x0=xp, y0=bas, x1=xp, y1=orta, line=dict(color=TEAL, width=3.0))
    fig.add_shape(type="line", x0=xp + 0.7, y0=orta, x1=xp + 0.7, y1=hedef,
                  line=dict(color=MOR, width=3.0))
    not_(fig, xp + 0.9, (bas + hedef) / 2,
         f"boşluk hareketin ORTASINDADIR:<br>{orta:.2f} − {bas:.2f} = {orta-bas:.2f}"
         f"  →  hedef = {orta:.2f} + {orta-bas:.2f} = {hedef:.2f}",
         renk=MOR, ax=112, ay=-4, boyut=10)
    tepe_i = int(np.argmax(d.h.values[dur0:])) + dur0
    not_(fig, tepe_i, float(d.h[tepe_i]),
         f"varış: bar {tepe_i} · tepe {float(d.h[tepe_i]):.2f}", renk=MOR, ax=-30, ay=-46,
         boyut=10)
    lejant_cizgi(fig, "ölçüm boşluğunun sınırları", ALTIN)
    lejant_cizgi(fig, "boşluğun ortası", MOR, dash="dashdot")
    lejant_cizgi(fig, "hedef", MOR)
    duzen(fig, "77 · Ölçüm boşluğu: kırılım noktası – ilk duraklama",
          "boşluk hareketin ortasıdır; hedef, ortaya olan mesafenin bir katı daha ileridedir",
          h=700, sematik=True)
    kaydet(fig, "77_olcum_boslugu", olcum=dict(
        bant_tepesi=round(kir_nokta, 2), bant_dibi=round(bas, 2),
        ilk_duraklama_dibi=round(dur_dip, 2), bosluk=round(bosluk, 2),
        bosluk_ortasi=round(orta, 2), hedef=round(hedef, 2),
        gerceklesen_tepe=round(float(d.h.max()), 2),
        hedefe_varildi=bool(float(d.h.max()) >= hedef)))


# ================================================================== 78  (GERÇEK)
def f78():
    """Yatay bant yüksekliği tabanlı MM — XU030 5dk, indis 1620–1710."""
    d = yukle("XU030.IS", "5m")
    if d is None:
        print("  ! 78 atlandı")
        return
    B = 1620
    p1 = dilim(d, B, 47)        # 1620–1666
    p2 = dilim(d, B, 91)        # 1620–1710
    b0, b1 = 1630, 1661
    hi = float(d.h[b0:b1 + 1].max())        # 16837,3 (bar 1650)
    lo = float(d.l[b0:b1 + 1].min())        # 16713,2 (bar 1661)
    yuk = hi - lo
    kir = 1665                              # bandın altına ilk kapanış
    hedef = lo - yuk
    varis = next(i for i in range(kir, 1711) if float(d.l[i]) <= hedef)
    testler = [i for i in range(b0, b1 + 1) if float(d.l[i]) <= lo + yuk * 0.16]
    tepeler = [i for i in range(b0, b1 + 1) if float(d.h[i]) >= hi - yuk * 0.16]

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.115, subplot_titles=(
        "Panel 1 — yatay bant ve yüksekliği (üst kenar ve alt kenar test sayılarıyla)",
        "Panel 2 — aşağı kırılım ve bant yüksekliği kadar ölçülmüş hareket"))
    panel(fig, p1, 1)
    panel(fig, p2, 2)

    for r, df in ((1, p1), (2, p2)):
        kutu(fig, b0 - B - 0.5, b1 - B + 0.5, lo, hi, GRI, a=0.12, cizgi=1.3, row=r, col=1)
        yatay(fig, hi, b0 - B - 0.5, len(df) - 1, renk=GRI, dash="dash", w=1.4, row=r, col=1)
        yatay(fig, lo, b0 - B - 0.5, len(df) - 1, renk=GRI, dash="dash", w=1.4, row=r, col=1)

    not_(fig, len(p1) - 1, hi, f"bant tepesi {hi:.1f}", renk=GRI, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    not_(fig, len(p1) - 1, lo, f"bant dibi {lo:.1f}", renk=GRI, ok=False, boyut=10,
         xanchor="left", row=1, col=1)
    xb = b0 - B + 1
    fig.add_shape(type="line", x0=xb, y0=lo, x1=xb, y1=hi, line=dict(color=MOR, width=2.8),
                  row=1, col=1)
    not_(fig, xb, (lo + hi) / 2, f"bant yüksekliği {yuk:.1f} puan", renk=MOR, ax=66, ay=0,
         boyut=10, row=1, col=1)
    for i in tepeler:
        not_(fig, i - B, float(d.h[i]) + 6, "•", renk=BORDO, ok=False, boyut=13,
             yanchor="bottom", row=1, col=1)
    for i in testler:
        not_(fig, i - B, float(d.l[i]) - 6, "•", renk=TEAL, ok=False, boyut=13,
             yanchor="top", row=1, col=1)
    not_(fig, (b0 + b1) / 2 - B, hi + 22,
         f"üst kenar {len(tepeler)} kez, alt kenar {len(testler)} kez test edildi —<br>"
         "bant tanısı: iki taraf da kazanamıyor", renk=MUREKKEP, ok=False, boyut=10,
         row=1, col=1)
    not_(fig, kir - B, float(d.c[kir]) - 22, "kırılım barı", renk=ALTIN, ax=26, ay=40,
         boyut=10, row=1, col=1)

    # panel 2 — MM
    kutu(fig, kir - B - 0.45, kir - B + 0.45, float(d.l[kir]), float(d.h[kir]), ALTIN,
         a=0.22, cizgi=1.3, row=2, col=1)
    not_(fig, kir - B, float(d.h[kir]) + 14,
         f"aşağı kırılım: {d.ts[kir]:%d %b %H:%M} kapanışı bandın altında", renk=ALTIN,
         ax=54, ay=-34, boyut=10, row=2, col=1)
    xp = kir - B + 6
    fig.add_shape(type="line", x0=xp, y0=lo, x1=xp, y1=hedef, line=dict(color=MOR, width=2.8),
                  row=2, col=1)
    not_(fig, xp, (lo + hedef) / 2, f"bant yüksekliği {yuk:.1f} aşağı projekte",
         renk=MOR, ax=76, ay=0, boyut=10, row=2, col=1)
    yatay(fig, hedef, kir - B, len(p2) - 1, renk=MOR, dash="dash", w=1.7, row=2, col=1)
    not_(fig, len(p2) - 1, hedef, f"MM hedefi {hedef:.1f}", renk=MOR, ok=False, boyut=10,
         xanchor="left", row=2, col=1)
    not_(fig, varis - B, float(d.l[varis]) - 16,
         f"varış: {d.ts[varis]:%d %b %H:%M} · dip {float(d.l[varis]):.1f} "
         f"({varis - kir} bar sonra)", renk=MOR, ax=-14, ay=46, boyut=10, row=2, col=1)

    lejant(fig, "kırılım barı", ALTIN)
    lejant_cizgi(fig, "bant kenarları", GRI)
    lejant_cizgi(fig, "bant yüksekliği MM", MOR)
    duzen(fig, "78 · Yatay bant yüksekliği tabanlı ölçülmüş hareket",
          f"XU030 5 dakika · bant indis {b0}–{b1}, panel 1 indis {B}–{B+46}, "
          f"panel 2 indis {B}–{B+90} · pencereler indisle pinli",
          h=920, x_baslik="", y_baslik="endeks")
    zaman_ekseni(fig, p1, adet=7, fmt="%d %b %H:%M", row=1, col=1)
    zaman_ekseni(fig, p2, adet=8, fmt="%d %b %H:%M", row=2, col=1)
    fig.update_xaxes(title_text="bar (indisle pinli)", row=2, col=1)
    kaydet(fig, "78_bant_yuksekligi_mm", olcum=dict(
        enstruman="XU030 5dk", bant=f"indis {b0}–{b1}",
        bant_tepesi=round(hi, 1), bant_dibi=round(lo, 1), bant_yuksekligi=round(yuk, 1),
        ust_kenar_test=len(tepeler), alt_kenar_test=len(testler),
        kirilim_indis=kir, kirilim_saat=str(d.ts[kir]),
        mm_hedefi=round(hedef, 1), varis_indis=varis, varis_saat=str(d.ts[varis]),
        varis_bar_sayisi=varis - kir, varis_dip=round(float(d.l[varis]), 1)))


# ================================================================== main
def main():
    for f in (f64, f65, f66, f67, f68, f69, f70, f71, f72, f73, f74, f75, f76, f77, f78):
        print(f"· {f.__name__}  {f.__doc__.splitlines()[0]}")
        f()
    defter_yaz()


if __name__ == "__main__":
    main()
