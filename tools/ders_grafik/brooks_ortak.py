#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Al Brooks fiyat hareketi dersi — ORTAK ÇİZİM KATMANI.

Dersin bütün grafik üreticileri (brooks_grafikler_*.py) buradan import eder. Amaç:
altı ayrı dosyada üretilen 60+ figürün tek bir çizim dili konuşması — aynı palet,
aynı bar geometrisi, aynı etiket biçimi, aynı kaydetme yolu.

İki tür grafik var ve ikisi de açıkça etiketlenir:
  · ŞEMATİK — bar bar elle kurulmuş, tek bir kavramı ders kitabı netliğinde gösterir.
    Başlığın altında "şematik örnek" yazar; fiyat ekseni birimsizdir.
  · GERÇEK VERİ — `_veri/` önbelleğinden okunur (brooks_veri.py indirir). Pencere
    İNDİSLE pinlenir: aynı kod her koşuda AYNI barları çizer, metindeki sayılar
    grafikle çelişmez.

Brooks'a özgü yardımcılar: bar sayma (H1/H2/L1/L2…), sinyal barı/giriş/stop/hedef
kümesi ve R katları, ölçülmüş hareket (measured move) projeksiyonu, trend çizgisi ve
trend kanal çizgisi, 20 barlık EMA, boşluk (gap) işaretleme.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots   # noqa: F401  (üreticiler kullanıyor)

BURASI = Path(__file__).resolve().parent
SITE = BURASI.parents[1]                      # site/
VERI = BURASI / "_veri"
SLUG = "fiyat-hareketi-brooks"
CIKTI = SITE / "public" / "arastirma" / SLUG
CIKTI.mkdir(parents=True, exist_ok=True)

URETILEN: list[str] = []
YUKSEKLIK: dict[str, int] = {}                # dosya → px (MDX'teki yukseklik={} ile eşleşir)
OLCUM: dict[str, dict] = {}                   # figürden çıkan sayılar → metinle karşılaştırma

# ------------------------------------------------------------------ palet (ev stili)
TEAL = "#0f766e"      # boğa / yükseliş
BORDO = "#7f1d1d"     # ayı / düşüş
ALTIN = "#b45309"     # dikkat: sinyal barı, kırılım
MAVI = "#1d4ed8"      # giriş / emir
MOR = "#6d28d9"       # hedef / ölçülmüş hareket
TURUNCU = "#ea580c"   # başarısızlık / tuzak
GRI = "#6b7280"       # yardımcı çizgi
YESIL = "#15803d"     # kâr
MUREKKEP = "#211b12"
KAGIT = "#ffffff"
IZGARA = "#efe9dc"
CIZGI = "#d8cfba"


def rgba(hex_: str, a: float) -> str:
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


# ================================================================== veri: gerçek
def yukle(ticker: str, aralik: str) -> pd.DataFrame | None:
    """`_veri/` önbelleğinden OHLC oku. Yoksa None (sahte 'gerçek' veri ÜRETİLMEZ).

    Önbellekte İKİ biçim var: bu dersin yazdığı (o,h,l,c,v,ts) ve daha eski derslerin
    bıraktığı yfinance ham biçimi (Date/Datetime,Open,High,Low,Close). İkincisi
    tarih sütununda saat dilimi de taşıyor. Burada ikisi de tek biçime indirilir;
    aksi hâlde eski dosyalar sessizce okunamaz ve o figür kaybolurdu.
    """
    yol = VERI / f"{ticker.replace('=', '_').replace('^', '')}_{aralik}.csv"
    if not yol.exists():
        print(f"  ! önbellek yok: {yol.name} — python3 brooks_veri.py")
        return None
    df = pd.read_csv(yol)
    if "ts" not in df.columns:
        zaman = next((c for c in ("Datetime", "Date", "index") if c in df.columns), None)
        if zaman is None:
            print(f"  ! {yol.name}: zaman sütunu yok")
            return None
        df = df.rename(columns={zaman: "ts", "Open": "o", "High": "h",
                                "Low": "l", "Close": "c", "Volume": "v"})
    ts = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df["ts"] = ts.dt.tz_convert("UTC").dt.tz_localize(None)
    df = df.dropna(subset=["ts", "o", "h", "l", "c"])
    return df[["ts", "o", "h", "l", "c"] + (["v"] if "v" in df else [])].reset_index(drop=True)


def dilim(df: pd.DataFrame, bas: int, adet: int) -> pd.DataFrame:
    """İNDİSLE pencere: tarihe göre değil sıraya göre — önbellek sabit olduğu için
    bu pencere kalıcıdır ve metindeki sayılar grafiğe sadık kalır."""
    return df.iloc[bas:bas + adet].reset_index(drop=True)


def seans(df: pd.DataFrame, gun: str) -> pd.DataFrame:
    """Tek bir işlem gününün barları (içgün grafikleri için), UTC tarihine göre."""
    m = df[df.ts.dt.strftime("%Y-%m-%d") == gun]
    return m.reset_index(drop=True)


# ================================================================== veri: şematik
def df_yap(ohlc: list[tuple[float, float, float, float]], baslangic="2026-01-05 09:30",
           dakika=5) -> pd.DataFrame:
    """Elle kurulmuş bar dizisi → DataFrame. Bar geometrisi ne söylüyorsa o çizilir."""
    d = pd.DataFrame(ohlc, columns=["o", "h", "l", "c"])
    d["ts"] = pd.date_range(baslangic, periods=len(d), freq=f"{dakika}min")
    kotu = d[(d.h < d[["o", "c"]].max(axis=1) - 1e-9) | (d.l > d[["o", "c"]].min(axis=1) + 1e-9)]
    if len(kotu):
        raise ValueError(f"geçersiz bar(lar) — gövde kuyruğun dışında: {list(kotu.index)}")
    return d


def bar(o: float, kapanis: float, ust: float = 0.0, alt: float = 0.0) -> tuple:
    """Gövde + kuyruk uzunluklarıyla bar kur: bar(100, 103, ust=0.5, alt=0.3)."""
    h = max(o, kapanis) + ust
    l = min(o, kapanis) - alt
    return (o, h, l, kapanis)


def yol_uret(n: int, bas: float, egim: float, oynaklik: float, tohum: int,
             govde_orani: float = 0.6) -> list[tuple]:
    """Doldurma barları: deterministik (tohumlu) rastgele yürüyüş.

    Şematik figürlerde ANLATILAN barlar elle kurulur; aralardaki 'sıradan' barlar
    buradan gelir. Tohum sabit olduğu için grafik her koşuda birebir aynıdır.
    """
    rng = np.random.default_rng(tohum)
    fiyat = bas
    out = []
    for _ in range(n):
        adim = egim + rng.normal(0, oynaklik)
        o = fiyat
        c = fiyat + adim
        govde = abs(c - o)
        kuyruk = max(govde * (1 - govde_orani) / max(govde_orani, 0.01), oynaklik * 0.35)
        ust = abs(rng.normal(0, kuyruk))
        alt = abs(rng.normal(0, kuyruk))
        out.append((round(o, 4), round(max(o, c) + ust, 4), round(min(o, c) - alt, 4), round(c, 4)))
        fiyat = c
    return out


# ================================================================== çizim temelleri
def mumlar(df: pd.DataFrame, ad="fiyat", x=None, hover=None) -> go.Candlestick:
    # Not: Candlestick'in `width` özelliği yok (Bar'da var); mum genişliği eksen
    # aralığından türer. Bar aralığını değiştirmek isteyen x'i seyrekleştirsin.
    return go.Candlestick(
        x=list(range(len(df))) if x is None else x,
        open=df.o, high=df.h, low=df.l, close=df.c, name=ad,
        increasing=dict(line=dict(color=TEAL, width=1.1), fillcolor=rgba(TEAL, 0.55)),
        decreasing=dict(line=dict(color=BORDO, width=1.1), fillcolor=rgba(BORDO, 0.55)),
        whiskerwidth=0.15,
        text=hover, hoverinfo="x+y+text" if hover else "all",
    )


def kutu(fig, x0, x1, y0, y1, renk, a=0.16, cizgi=0.9, dash=None, row=None, col=None):
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=rgba(renk, a),
                  line=dict(color=renk, width=cizgi, dash=dash), layer="below", row=row, col=col)


def yatay(fig, y, x0, x1, renk=GRI, dash="dash", w=1.2, row=None, col=None):
    fig.add_shape(type="line", x0=x0, x1=x1, y0=y, y1=y,
                  line=dict(color=renk, width=w, dash=dash), row=row, col=col)


def cizgi(fig, x0, y0, x1, y1, renk=GRI, dash=None, w=1.4, row=None, col=None):
    fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                  line=dict(color=renk, width=w, dash=dash), row=row, col=col)


def not_(fig, x, y, metin, renk=MUREKKEP, ax=0, ay=-30, ok=True, boyut=11,
         xanchor="center", yanchor=None, row=None, col=None, arka=True):
    fig.add_annotation(x=x, y=y, text=metin, showarrow=ok, arrowhead=2, arrowsize=1,
                       arrowwidth=1.1, arrowcolor=renk, ax=ax, ay=ay,
                       font=dict(size=boyut, color=renk), xanchor=xanchor, yanchor=yanchor,
                       bgcolor="rgba(255,255,255,0.82)" if arka else None,
                       bordercolor=rgba(renk, 0.35) if arka else None, borderwidth=0.6 if arka else 0,
                       borderpad=2, row=row, col=col)


def lejant(fig, ad, renk, sekil="square", a=0.35):
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=ad, showlegend=True,
                             marker=dict(size=10, symbol=sekil, color=rgba(renk, a),
                                         line=dict(color=renk, width=1.2))))


def lejant_cizgi(fig, ad, renk, dash="dash"):
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=ad, showlegend=True,
                             line=dict(color=renk, width=2, dash=dash)))


# ================================================================== Brooks yardımcıları
def ema(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """Brooks'un tek göstergesi: 20 barlık üssel hareketli ortalama (kapanış)."""
    return df.c.ewm(span=n, adjust=False).mean()


def ema_ciz(fig, df, n=20, renk=GRI, row=None, col=None, ad=None):
    e = ema(df, n)
    fig.add_trace(go.Scatter(x=list(range(len(df))), y=e, mode="lines",
                             name=ad or f"{n} bar EMA", line=dict(color=renk, width=1.6)),
                  row=row, col=col)
    return e


def swingler(df: pd.DataFrame, k: int = 1):
    """k bar sağında ve solunda aşılmayan tepe/dipler (Brooks: swing high / swing low)."""
    sh, sl = [], []
    for i in range(k, len(df) - k):
        pencere = range(i - k, i + k + 1)
        if df.h[i] == max(df.h[j] for j in pencere):
            sh.append(i)
        if df.l[i] == min(df.l[j] for j in pencere):
            sl.append(i)
    return sh, sl


def bar_say(df: pd.DataFrame, yon: str = "bull", bas: int = 0, son: int | None = None):
    """Brooks bar sayımı: boğa geri çekilmesinde H1/H2/H3…, ayı geri çekilmesinde L1/L2…

    Brooks'un tanımı (Trading Ranges, "Bar Counting" bölümü, s.519 civarı, kendi
    ifademizle): boğa trendinde ya da yatay bantta YANA/AŞAĞI hareket sırasında,
    yükseği bir önceki barın yükseğini aşan İLK bar High 1'dir ve o ilk bacağı
    bitirir. Piyasa boğa salınımına dönmez de yana/aşağı devam ederse, önceki barın
    yükseğini aşan bir sonraki bar High 2'dir; böyle sürer. Ayıda ayna görüntüsü:
    düşüğü bir önceki barın düşüğünün altına inen bar Low 1, Low 2…

    Uygulama notları (ders metninde de böyle anlatılır):
    · Sayaç, trend KALDIĞI yerden devam edince sıfırlanır: etiketlenen bar aynı
      zamanda geri çekilme ÖNCESİNDEKİ tepeyi de aşıyorsa, o bacak bitmiştir ve
      bir sonraki geri çekilme yeniden H1'den başlar.
    · Brooks "H1 ile H2 arasında en azından küçük bir trend çizgisi kırılması olmalı"
      der. Bu nitel koşul burada ZORLANMAZ; mekanik sayım verilir, grafikte hangi
      sayımın gerçek bir kurulum olduğu metinde tartışılır. (Aksi hâlde araç, dersin
      anlatmak istediği yargı payını gizlerdi.)
    Dönüş: [(indis, etiket)] listesi.
    """
    son = len(df) if son is None else son
    isaret: list[tuple[int, str]] = []
    sayac = 0
    geri_cekilmede = False
    # Bacağın ucu: boğada o ana kadarki en yüksek tepe, ayıda en düşük dip.
    uc = df.h[bas] if yon == "bull" else df.l[bas]
    for i in range(max(bas + 1, 1), son):
        if yon == "bull":
            if not geri_cekilmede:
                if df.h[i] > uc:            # trend yeni tepe yaptı → bacak bitti
                    uc, sayac = df.h[i], 0
                if df.h[i] <= df.h[i - 1]:  # yükselemedi → yana/aşağı hareket başladı
                    geri_cekilmede = True
            elif df.h[i] > df.h[i - 1]:     # önceki barın yükseğini aştı → H(n)
                sayac += 1
                isaret.append((i, f"H{sayac}"))
                geri_cekilmede = False
                if df.h[i] > uc:
                    uc, sayac = df.h[i], 0  # aynı barda bacak da bitti
        else:
            if not geri_cekilmede:
                if df.l[i] < uc:
                    uc, sayac = df.l[i], 0
                if df.l[i] >= df.l[i - 1]:
                    geri_cekilmede = True
            elif df.l[i] < df.l[i - 1]:
                sayac += 1
                isaret.append((i, f"L{sayac}"))
                geri_cekilmede = False
                if df.l[i] < uc:
                    uc, sayac = df.l[i], 0
    return isaret


def bar_etiketle(fig, df, isaretler, yon="bull", renk=None, ofs=None, row=None, col=None):
    """bar_say() çıktısını grafiğe yazar."""
    renk = renk or (TEAL if yon == "bull" else BORDO)
    ofs = ofs if ofs is not None else (df.h.max() - df.l.min()) * 0.03
    for i, etiket in isaretler:
        y = df.h[i] + ofs if yon == "bull" else df.l[i] - ofs
        not_(fig, i, y, etiket, renk=renk, ok=False, boyut=10,
             yanchor="bottom" if yon == "bull" else "top", row=row, col=col)


def islem(fig, df, sinyal: int, yon: str, giris: float | None = None, stop: float | None = None,
          hedefler: tuple[float, ...] = (), etiketler=("hedef",), row=None, col=None,
          x_son: int | None = None, ondalik: int = 2, r_goster=True):
    """Sinyal barı → giriş → stop → hedef kümesini çizer ve R katlarını yazar.

    Brooks konvansiyonu: giriş, sinyal barının bir tick ötesinde stop emriyle olur;
    koruyucu stop sinyal barının DİĞER ucunun bir tick ötesindedir. Risk = bu ikisinin
    farkı; hedefler R cinsinden etiketlenir (ölçülmüş hareket kaç R'ye denk geliyor,
    okur bunu görmeden 'trader denklemi'ni kuramaz).
    """
    x_son = len(df) - 1 if x_son is None else x_son
    tick = (df.h.max() - df.l.min()) * 0.004
    if giris is None:
        giris = (df.h[sinyal] + tick) if yon == "bull" else (df.l[sinyal] - tick)
    if stop is None:
        stop = (df.l[sinyal] - tick) if yon == "bull" else (df.h[sinyal] + tick)
    risk = abs(giris - stop)
    # sinyal barını kutula
    kutu(fig, sinyal - 0.45, sinyal + 0.45, df.l[sinyal], df.h[sinyal], ALTIN, a=0.20, cizgi=1.2,
         row=row, col=col)
    not_(fig, sinyal, df.l[sinyal] - tick * 4 if yon == "bull" else df.h[sinyal] + tick * 4,
         "sinyal barı", renk=ALTIN, ok=False, boyut=10,
         yanchor="top" if yon == "bull" else "bottom", row=row, col=col)
    yatay(fig, giris, sinyal - 0.4, x_son, renk=MAVI, dash="solid", w=1.6, row=row, col=col)
    not_(fig, x_son, giris, f"giriş {giris:.{ondalik}f}", renk=MAVI, ok=False, boyut=10,
         xanchor="left", row=row, col=col)
    yatay(fig, stop, sinyal - 0.4, x_son, renk=BORDO, dash="dot", w=1.5, row=row, col=col)
    not_(fig, x_son, stop, f"stop {stop:.{ondalik}f}  (risk {risk:.{ondalik}f} = 1R)",
         renk=BORDO, ok=False, boyut=10, xanchor="left", row=row, col=col)
    for k, hf in enumerate(hedefler):
        et = etiketler[k] if k < len(etiketler) else f"hedef {k+1}"
        r = abs(hf - giris) / risk if risk else 0
        yatay(fig, hf, sinyal - 0.4, x_son, renk=MOR, dash="dash", w=1.4, row=row, col=col)
        not_(fig, x_son, hf, f"{et} {hf:.{ondalik}f}" + (f"  ({r:.1f}R)" if r_goster else ""),
             renk=MOR, ok=False, boyut=10, xanchor="left", row=row, col=col)
    return dict(giris=giris, stop=stop, risk=risk,
                r=[abs(h - giris) / risk if risk else 0 for h in hedefler])


def olculmus_hareket(fig, x0, y0, x1, y1, x_hedef, renk=MOR, etiket="ölçülmüş hareket",
                     row=None, col=None, ondalik=2):
    """İlk bacağın boyunu kırılım noktasından ileri taşır (measured move).

    Brooks'ta en sık kullanılan mıknatıs: bacak boyu = |y1 − y0|; hedef, kırılım
    noktasına (y1) aynı boy eklenerek bulunur.
    """
    boy = y1 - y0
    hedef = y1 + boy
    cizgi(fig, x0, y0, x1, y1, renk=rgba(renk, 0.9), dash="dot", w=1.4, row=row, col=col)
    fig.add_shape(type="line", x0=x1, y0=y1, x1=x1, y1=hedef,
                  line=dict(color=renk, width=2.4), row=row, col=col)
    yatay(fig, hedef, x1, x_hedef, renk=renk, dash="dash", w=1.5, row=row, col=col)
    not_(fig, x_hedef, hedef, f"{etiket} {hedef:.{ondalik}f}", renk=renk, ok=False, boyut=10,
         xanchor="left", row=row, col=col)
    return hedef


def trend_cizgisi(fig, df, noktalar: tuple[int, int], yon="bull", uzat: int | None = None,
                  renk=GRI, dash="dash", w=1.5, kanal=False, kanal_nokta: int | None = None,
                  row=None, col=None):
    """İki dip (boğa) ya da iki tepeden (ayı) trend çizgisi; kanal=True ise karşı
    taraftan paralel trend KANAL çizgisi de çizilir (Brooks: trend channel line)."""
    i, j = noktalar
    y_i = df.l[i] if yon == "bull" else df.h[i]
    y_j = df.l[j] if yon == "bull" else df.h[j]
    egim = (y_j - y_i) / (j - i)
    uzat = len(df) - 1 if uzat is None else uzat
    cizgi(fig, i, y_i, uzat, y_i + egim * (uzat - i), renk=renk, dash=dash, w=w, row=row, col=col)
    if kanal:
        k = kanal_nokta
        if k is None:
            sapma = [(df.h[t] if yon == "bull" else df.l[t]) - (y_i + egim * (t - i)) for t in range(i, j + 1)]
            k = i + int(np.argmax(sapma) if yon == "bull" else np.argmin(sapma))
        y_k = df.h[k] if yon == "bull" else df.l[k]
        c = y_k - egim * (k - i)
        cizgi(fig, i, c + egim * 0, uzat, c + egim * (uzat - i), renk=renk, dash="dot", w=w,
              row=row, col=col)
    return egim


def bosluk_isaretle(fig, df, i: int, renk=ALTIN, etiket="boşluk", row=None, col=None):
    """Barlar arası boşluk (gap): önceki barın yükseği ile bu barın düşüğü arasındaki
    aralık. Brooks bunu 'ölçen boşluk' (measuring gap) adayı olarak okur."""
    if df.l[i] > df.h[i - 1]:
        y0, y1 = df.h[i - 1], df.l[i]
    elif df.h[i] < df.l[i - 1]:
        y0, y1 = df.h[i], df.l[i - 1]
    else:
        return None
    kutu(fig, i - 1.4, i + 0.45, y0, y1, renk, a=0.22, cizgi=1.0, row=row, col=col)
    not_(fig, i, (y0 + y1) / 2, etiket, renk=renk, ok=False, boyut=10, row=row, col=col)
    return (y0, y1)


# ================================================================== yerleşim + kayıt
def duzen(fig, baslik: str, alt: str = "", y_baslik="fiyat", x_baslik="bar sırası",
          h=560, legend_y=None, sematik=False):
    if sematik:
        y_baslik = "fiyat (şematik birim)"
        alt = (alt + " · " if alt else "") + "şematik örnek"
    fig.update_layout(
        title=dict(text=f"{baslik}<br><sup style='color:#6b6355'>{alt}</sup>" if alt else baslik,
                   x=0.01, xanchor="left", font=dict(size=15, color=MUREKKEP)),
        paper_bgcolor=KAGIT, plot_bgcolor=KAGIT,
        font=dict(family="-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
                  size=12.5, color=MUREKKEP),
        legend=dict(orientation="h", yanchor="top", y=-0.12 if legend_y is None else legend_y,
                    xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=62, r=96, t=92, b=100), height=h, hovermode="x",
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor=IZGARA, linecolor=CIZGI, title_text=x_baslik,
                     rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor=IZGARA, linecolor=CIZGI, title_text=y_baslik)
    for eks in fig.layout:
        if eks.startswith("xaxis"):
            fig.layout[eks].rangeslider = dict(visible=False)


def zaman_ekseni(fig, df, adet=9, fmt="%d %b %H:%M", row=None, col=None):
    n = len(df)
    adim = list(range(0, n, max(1, n // adet)))
    fig.update_xaxes(tickvals=adim, ticktext=[df.ts[i].strftime(fmt) for i in adim],
                     tickangle=0, tickfont=dict(size=10), row=row, col=col)


def hover(df, fmt="%Y-%m-%d %H:%M"):
    return [f"{t:{fmt}}" for t in df.ts]


def kaydet(fig, ad: str, olcum: dict | None = None):
    """HTML yaz + yüksekliği ve figürden çıkan sayıları kaydet.

    yukseklikler.json MDX'teki yukseklik={} ile karşılaştırılır: figür bir dipnot
    yüzünden uzayınca MDX'teki sayı elle yazıldığı için sessizce ayrışır ve iframe
    grafiği kırpar. Bu dosya o ayrışmayı görünür yapar.
    """
    yol = CIKTI / f"{ad}.html"
    fig.write_html(str(yol), include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    URETILEN.append(ad)
    YUKSEKLIK[f"{ad}.html"] = int(fig.layout.height or 560)
    if olcum:
        OLCUM[ad] = olcum
    print("  ✓", yol.name)


def defter_yaz():
    """Üretim sonunda çağrılır: yükseklikler + ölçümler diske.

    BİRLEŞTİREREK yazar. Ders 94 figürü altı ayrı script'e bölünmüş durumda ve her
    biri ayrı süreçte koşuyor; üzerine yazmak, son koşan script'in dışındaki bütün
    figürlerin yükseklik kaydını silerdi (ve sayfa denetimi hepsini "eksik" sanardı).
    """
    y = CIKTI / "yukseklikler.json"
    birlesik = {}
    if y.exists():
        try:
            birlesik = json.loads(y.read_text(encoding="utf-8"))
        except Exception:
            birlesik = {}
    birlesik.update(YUKSEKLIK)
    y.write_text(json.dumps(dict(sorted(birlesik.items())), ensure_ascii=False, indent=1),
                 encoding="utf-8")
    if OLCUM:
        y = CIKTI / "olcumler.json"
        eski = json.loads(y.read_text(encoding="utf-8")) if y.exists() else {}
        eski.update(OLCUM)
        y.write_text(json.dumps(dict(sorted(eski.items())), ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"  ✓ {len(YUKSEKLIK)} figür · yukseklikler.json"
          + (f" · olcumler.json ({len(OLCUM)} kayıt)" if OLCUM else ""))
