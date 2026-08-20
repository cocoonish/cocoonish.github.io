#!/usr/bin/env python3
"""SMC (Smart Money Concepts) dersi — grafik seti üreticisi.

Tek komut:  python3 site/tools/ders_grafik/smc_grafikler.py
Çıktı:      site/public/arastirma/smc-teknik-analiz/*.html  (Plotly, plotly.js CDN)

- Sentetik/şematik OHLC serileri sabit tohumla (deterministik) kurgulanır; her
  grafik tek bir kavramı ders kitabı netliğinde gösterir. Başlıkta "şematik örnek".
- Gerçek veri örnekleri yfinance ile çekilir; basit tespit fonksiyonlarıyla
  (3/5-mum swing, gövde-kapanışlı kırılım, sweep, FVG, OB) işaretlenir.
  yfinance başarısız olursa o grafik atlanır ve raporlanır (sahte "gerçek" veri yok).
- Ev stili (başlık solda, lejant altta, beyaz zemin) burada temel olarak verilir;
  site/tools/plotly_stil.py ile son rötuş yapılır.
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

KOK = Path(__file__).resolve().parents[2]  # site/
CIKTI = KOK / "public" / "arastirma" / "smc-teknik-analiz"
CIKTI.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- palet
TEAL = "#0f766e"      # yükseliş
BORDO = "#7f1d1d"     # düşüş
ALTIN = "#b45309"     # likidite / sweep
MAVI = "#1d4ed8"      # order block
MOR = "#6d28d9"       # FVG
TURUNCU = "#ea580c"   # PRZ / breaker
GRI = "#6b7280"       # fib / yardımcı
MUREKKEP = "#211b12"


def rgba(hex_: str, a: float) -> str:
    h = hex_.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


URETILEN: list[str] = []
RAPOR: list[str] = []


# ---------------------------------------------------------------- sentetik seri üretici
class Seri:
    """Bacak bacak kurgulanan, gerçekçi gürültülü ama net şematik OHLC serisi."""

    def __init__(self, seed: int, baslangic: float = 100.0, birim: float = 0.10):
        self.rng = np.random.default_rng(seed)
        self.o: list[float] = []
        self.h: list[float] = []
        self.l: list[float] = []
        self.c: list[float] = []
        self.lab: list[str] = []
        self._son = baslangic
        self.birim = birim  # gürültü/fitil ölçeği (fiyat birimi)

    # son kapanış
    @property
    def son(self) -> float:
        return self.c[-1] if self.c else self._son

    @property
    def n(self) -> int:
        return len(self.c)

    def mum(self, o, h, l, c, lab: str = "") -> int:
        h = max(h, o, c)
        l = min(l, o, c)
        self.o.append(float(o)); self.h.append(float(h)); self.l.append(float(l)); self.c.append(float(c))
        self.lab.append(lab)
        return self.n - 1

    def bacak(self, hedef: float, n: int, gurultu: float = 1.0, fitil: float = 1.0, lab: str = "") -> int:
        """Son kapanıştan `hedef`e n mumda git (son mum tam hedefte kapanır)."""
        bas = self.son
        for i in range(n):
            t = (i + 1) / n
            taban = bas + (hedef - bas) * t
            c = hedef if i == n - 1 else taban + self.rng.normal(0, gurultu * self.birim)
            o = self.son + self.rng.normal(0, 0.15 * self.birim)
            hi = max(o, c) + abs(self.rng.normal(0, fitil * self.birim))
            lo = min(o, c) - abs(self.rng.normal(0, fitil * self.birim))
            self.mum(o, hi, lo, c, lab if i == n - 1 else "")
        return self.n - 1

    def yatay(self, n: int, merkez: float | None = None, genlik: float = 1.0, lab: str = "") -> int:
        """Dar aralıkta n mum (birikim)."""
        m = self.son if merkez is None else merkez
        for i in range(n):
            c = m + self.rng.normal(0, genlik * self.birim)
            o = self.son + self.rng.normal(0, 0.15 * self.birim)
            hi = max(o, c) + abs(self.rng.normal(0, 0.8 * self.birim))
            lo = min(o, c) - abs(self.rng.normal(0, 0.8 * self.birim))
            self.mum(o, hi, lo, c, lab if i == n - 1 else "")
        return self.n - 1

    def df(self) -> pd.DataFrame:
        return pd.DataFrame(dict(o=self.o, h=self.h, l=self.l, c=self.c, lab=self.lab))


# ---------------------------------------------------------------- tespit fonksiyonları (sentetik + gerçek ortak)
def swingler(df: pd.DataFrame, k: int = 1):
    """k-komşu fraktal: ortadaki mumun high'ı (low'u) iki yandaki k mumdan kesin büyük (küçük)."""
    h, l = df.h.values, df.l.values
    sh, sl = [], []
    for i in range(k, len(df) - k):
        kom = [j for j in range(i - k, i + k + 1) if j != i]
        if all(h[i] > h[j] for j in kom):
            sh.append(i)
        if all(l[i] < l[j] for j in kom):
            sl.append(i)
    return sh, sl


def swing_etiketle(df, sh, sl):
    """HH/HL/LH/LL: bir önceki aynı tür swing ile kıyas."""
    et = {}
    onc = None
    for i in sh:
        et[i] = ("HH" if df.h[i] > df.h[onc] else "LH") if onc is not None else "H"
        onc = i
    onc = None
    for i in sl:
        et[i] = ("HL" if df.l[i] > df.l[onc] else "LL") if onc is not None else "L"
        onc = i
    return et


def orta_swingler(df, sh, sl):
    """ITH: iki yanında daha alçak STH bulunan STH; ITL simetrik."""
    ith = [sh[j] for j in range(1, len(sh) - 1) if df.h[sh[j]] > df.h[sh[j - 1]] and df.h[sh[j]] > df.h[sh[j + 1]]]
    itl = [sl[j] for j in range(1, len(sl) - 1) if df.l[sl[j]] < df.l[sl[j - 1]] and df.l[sl[j]] < df.l[sl[j + 1]]]
    return ith, itl


def fvg_bul(df: pd.DataFrame, min_boy: float = 0.0):
    """3-mum kuralı: high(M1) < low(M3) → BISI; low(M1) > high(M3) → SIBI. i = M1 indeksi."""
    out = []
    h, l = df.h.values, df.l.values
    for i in range(0, len(df) - 2):
        if h[i] < l[i + 2] and (l[i + 2] - h[i]) >= min_boy:
            out.append(dict(i=i, tip="BISI", alt=h[i], ust=l[i + 2]))
        elif l[i] > h[i + 2] and (l[i] - h[i + 2]) >= min_boy:
            out.append(dict(i=i, tip="SIBI", alt=h[i + 2], ust=l[i]))
    return out


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df.c.shift(1)
    tr = pd.concat([df.h - df.l, (df.h - pc).abs(), (df.l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=1).mean()


def yapi_olaylari(df: pd.DataFrame, k: int = 2):
    """Gövde kapanışlı kırılım tespiti. Onaylı (k mum sonra bilinen) en son swing
    high/low referans alınır; close ötesine geçerse trend yönünde BOS, aleyhine CHoCH.
    Fitil ötede + gövde içeride → sweep."""
    sh, sl = swingler(df, k)
    sh_set, sl_set = set(sh), set(sl)
    olay = []
    trend = None
    ref_h = None  # (idx, seviye)
    ref_l = None
    n = len(df)
    for i in range(n):
        # i-k mumu bugün onaylanan swing olabilir
        j = i - k
        if j >= 0:
            if j in sh_set and (ref_h is None or df.h[j] >= 0):
                if ref_h is None or df.h[j] != ref_h[1]:
                    ref_h = (j, df.h[j])
            if j in sl_set:
                if ref_l is None or df.l[j] != ref_l[1]:
                    ref_l = (j, df.l[j])
        c = df.c[i]
        if ref_h is not None and i > ref_h[0]:
            if c > ref_h[1]:
                olay.append(dict(i=i, ref=ref_h[0], seviye=ref_h[1], tip="BOS" if trend in ("up", None) else "CHoCH", yon="up"))
                trend = "up"
                ref_h = None
            elif df.h[i] > ref_h[1] and c < ref_h[1]:
                olay.append(dict(i=i, ref=ref_h[0], seviye=ref_h[1], tip="sweep", yon="up"))
        if ref_l is not None and i > ref_l[0]:
            if c < ref_l[1]:
                olay.append(dict(i=i, ref=ref_l[0], seviye=ref_l[1], tip="BOS" if trend in ("down", None) else "CHoCH", yon="down"))
                trend = "down"
                ref_l = None
            elif df.l[i] < ref_l[1] and c > ref_l[1]:
                olay.append(dict(i=i, ref=ref_l[0], seviye=ref_l[1], tip="sweep", yon="down"))
    return olay, sh, sl


# ---------------------------------------------------------------- çizim yardımcıları
def mum_izi(df: pd.DataFrame, x=None, ad="Mum", hover_ek=None, gorunur=True):
    x = list(range(len(df))) if x is None else x
    if hover_ek is None:
        metin = [f"<b>{lb}</b>" if lb else "" for lb in df.get("lab", [""] * len(df))]
    else:
        metin = hover_ek
    return go.Candlestick(
        x=x, open=df.o, high=df.h, low=df.l, close=df.c, name=ad, text=metin,
        increasing_line_color=TEAL, increasing_fillcolor=TEAL,
        decreasing_line_color=BORDO, decreasing_fillcolor=BORDO,
        line_width=1.2, whiskerwidth=0.4, showlegend=gorunur,
    )


def kutu(fig, x0, x1, y0, y1, renk, a=0.18, cizgi=0.8, row=None, col=None, dash=None):
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=rgba(renk, a),
                  line=dict(color=renk, width=cizgi, dash=dash), layer="below", row=row, col=col)


def yatay(fig, y, x0, x1, renk=GRI, dash="dash", w=1.2, row=None, col=None):
    fig.add_shape(type="line", x0=x0, x1=x1, y0=y, y1=y, line=dict(color=renk, width=w, dash=dash), row=row, col=col)


def not_(fig, x, y, metin, renk=MUREKKEP, ax=0, ay=-30, ok=True, boyut=11, row=None, col=None,
         xanchor="center", yanchor="auto", bg=None, align="center"):
    fig.add_annotation(x=x, y=y, text=metin, showarrow=ok, ax=ax, ay=ay, arrowhead=2, arrowsize=0.9,
                       arrowwidth=1.3, arrowcolor=renk, font=dict(size=boyut, color=renk),
                       bgcolor=bg if bg else "rgba(255,255,255,0.85)", bordercolor=renk if bg is None else bg,
                       borderwidth=0.6, borderpad=2, row=row, col=col, xanchor=xanchor, yanchor=yanchor, align=align)


def daire(fig, x, y, r_x=0.6, r_y=0.25, renk=ALTIN, row=None, col=None):
    fig.add_shape(type="circle", x0=x - r_x, x1=x + r_x, y0=y - r_y, y1=y + r_y,
                  line=dict(color=renk, width=1.8), row=row, col=col)


def lejant(fig, ad, renk, a=0.35, sekil="square"):
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=ad,
                             marker=dict(size=12, color=rgba(renk, a), symbol=sekil,
                                         line=dict(color=renk, width=1.2))))


def lejant_cizgi(fig, ad, renk, dash="dash"):
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=ad,
                             line=dict(color=renk, width=1.5, dash=dash)))


def swing_isaretle(fig, df, sh, sl, et=None, x=None, ith=None, itl=None, row=None, col=None, ofs=None, k=1):
    x = list(range(len(df))) if x is None else x
    ad_k = f"{2 * k + 1}-mum"
    ofs = ofs if ofs is not None else (df.h.max() - df.l.min()) * 0.02
    fig.add_trace(go.Scatter(x=[x[i] for i in sh], y=[df.h[i] + ofs for i in sh], mode="markers+text",
                             marker=dict(symbol="triangle-down", size=9, color=BORDO),
                             text=[et.get(i, "") if et else "" for i in sh], textposition="top center",
                             textfont=dict(size=10, color=BORDO), name=f"swing high ({ad_k})"), row=row, col=col)
    fig.add_trace(go.Scatter(x=[x[i] for i in sl], y=[df.l[i] - ofs for i in sl], mode="markers+text",
                             marker=dict(symbol="triangle-up", size=9, color=TEAL),
                             text=[et.get(i, "") if et else "" for i in sl], textposition="bottom center",
                             textfont=dict(size=10, color=TEAL), name=f"swing low ({ad_k})"), row=row, col=col)
    if ith:
        fig.add_trace(go.Scatter(x=[x[i] for i in ith], y=[df.h[i] + 2.6 * ofs for i in ith], mode="markers",
                                 marker=dict(symbol="circle-open", size=16, color=BORDO, line_width=2),
                                 name="ITH (orta vadeli tepe)"), row=row, col=col)
    if itl:
        fig.add_trace(go.Scatter(x=[x[i] for i in itl], y=[df.l[i] - 2.6 * ofs for i in itl], mode="markers",
                                 marker=dict(symbol="circle-open", size=16, color=TEAL, line_width=2),
                                 name="ITL (orta vadeli dip)"), row=row, col=col)


def duzen(fig, baslik: str, alt: str = "", y_baslik="fiyat (şematik birim)", x_baslik="mum sırası", h=560,
          legend_y=None):
    # legend_y: lejant çizim alanının altına paper biriminde yerleşir; alt alta dizilmiş
    # (uzun) figürlerde -0.12 sabit oranı marjı taşırdığı için dışarıdan verilir.
    fig.update_layout(
        title=dict(text=f"{baslik}<br><sup style='color:#6b6355'>{alt}</sup>" if alt else baslik,
                   x=0.01, xanchor="left", font=dict(size=15, color=MUREKKEP)),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(family="-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif", size=12.5, color=MUREKKEP),
        legend=dict(orientation="h", yanchor="top", y=-0.12 if legend_y is None else legend_y,
                    xanchor="left", x=0, font=dict(size=11)),
        margin=dict(l=60, r=70, t=90, b=100), height=h, hovermode="x",
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#efe9dc", linecolor="#d8cfba", title_text=x_baslik,
                     rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="#efe9dc", linecolor="#d8cfba", title_text=y_baslik)


def _alt_baslik_kir(fig, esik=24, font=12):
    """make_subplots alt panel başlıklarını sitede (~800 px iframe) çakışmasın diye
    düzenler: çok panelli figürlerde font 12 px'e sabitlenir, 3+ SÜTUNLU figürlerde uzun
    başlıklar ayrıca en yakın boşluktan iki satıra bölünür. Tek sütunlu (alt alta) yerleşimde
    panel tam genişlik olduğu için kırmaya gerek yoktur. Alt başlıklar make_subplots'un
    ürettiği ilk N annotation'dır (yanchor='bottom', xref '... domain'); kullanıcı
    annotation'larına dokunulmaz."""
    # sütun sayısı = x eksen domain'lerinin farklı SOL kenar sayısı (tek sütunda 1)
    alanlar = [tuple(ax.domain) for ax in fig.select_xaxes() if ax.domain is not None]
    cols = len({round(d[0], 4) for d in alanlar}) if alanlar else 1
    panel = max(len(alanlar), 1)
    # alt panel başlıkları y eksen domain'lerinin ÜST kenarına oturur; alt alta yerleşimde
    # bu kenarlar 1.0'ın altına iner, o yüzden "üstte mi" yerine kenar eşleşmesine bakılır
    ust_kenarlar = {round(tuple(ax.domain)[1], 4) for ax in fig.select_yaxes() if ax.domain is not None}
    for a in fig.layout.annotations:
        xref = str(getattr(a, "xref", ""))
        if getattr(a, "yanchor", None) != "bottom" or not (xref.endswith("domain") or xref == "paper"):
            continue
        if round(getattr(a, "y", 0) or 0, 4) not in ust_kenarlar or getattr(a, "bgcolor", None):
            continue   # panel üst kenarında değil ya da kutulu: kullanıcı notu
        t = a.text or ""
        if panel > 1 or cols >= 3 or len(t) > 40:
            a.font = a.font or {}
            a.font.size = font
        if cols >= 3 and len(t) > esik and "<br>" not in t:
            k = t.rfind(" ", 0, max(esik, len(t) // 2 + 4))
            if k > 8:
                a.text = t[:k] + "<br>" + t[k + 1:]
    m = fig.layout.margin
    if m is not None and (m.r or 0) < 110:
        fig.update_layout(margin=dict(r=110))


def kaydet(fig, ad: str):
    _alt_baslik_kir(fig)
    yol = CIKTI / f"{ad}.html"
    fig.write_html(str(yol), include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    URETILEN.append(str(yol))
    print("  ✓", yol.name)


def fib_ciz(fig, low, high, x0, x1, yon="bull", seviyeler=(0, 0.5, 0.62, 0.705, 0.79, 1.0, -0.27, -0.62),
            ote=True, etiket_x=None, row=None, col=None, ondalik=2, kisa=False):
    """ICT fib: bull → 0 = high, 1 = low (retracement aşağı ölçülür); bear → 0 = low, 1 = high."""
    r = high - low
    sev = {}
    for s in seviyeler:
        y = high - s * r if yon == "bull" else low + s * r
        sev[s] = y
        kalin = s == 0.705
        yatay(fig, y, x0, x1, renk=GRI if s not in (0.705,) else ALTIN, dash="dot" if s < 0 else "dash",
              w=2.0 if kalin else 1.0, row=row, col=col)
        ad = {0: "0", 0.5: "0.5 (EQ)", 0.62: "0.62", 0.705: "0.705 (OTE merkezi)", 0.79: "0.79", 1.0: "1.0 (SL referansı)",
              -0.27: "−0.27 (T1)", -0.62: "−0.62 (T2)", -1.0: "−1.0", -2.0: "−2.0"}.get(s, str(s))
        if kisa:
            ad = {0.705: "0.705", 0.5: "0.5", 1.0: "1.0", -0.27: "−0.27", -0.62: "−0.62"}.get(s, ad)
        not_(fig, etiket_x if etiket_x is not None else x1, y, f"{ad} — {y:.{ondalik}f}", renk=ALTIN if kalin else GRI,
             ok=False, boyut=10, xanchor="left", row=row, col=col)
    if ote and 0.62 in sev and 0.79 in sev:
        y0, y1 = sorted([sev[0.62], sev[0.79]])
        kutu(fig, x0, x1, y0, y1, ALTIN, a=0.16, cizgi=0, row=row, col=col)
    return sev


# =====================================================================================
# 01 — Swing high/low ve HH/HL/LH/LL yapısı
# =====================================================================================
def g01_swing_yapi():
    s = Seri(1)
    g = dict(gurultu=0.45, fitil=0.8)
    s.bacak(103.0, 6, **g); s.bacak(101.6, 4, **g); s.bacak(105.0, 6, **g); s.bacak(103.4, 4, **g); s.bacak(107.5, 6, **g)
    s.bacak(103.2, 5, **g); s.bacak(104.9, 3, **g); s.bacak(102.0, 5, **g); s.bacak(103.3, 3, **g); s.bacak(100.5, 5, **g)
    df = s.df()
    sh, sl = swingler(df, 2)
    et = swing_etiketle(df, sh, sl)
    ith, itl = orta_swingler(df, sh, sl)
    fig = go.Figure(mum_izi(df))
    swing_isaretle(fig, df, sh, sl, et, ith=ith, itl=itl, k=2)
    # yükseliş → düşüş bölgeleri
    tepe = int(df.h.idxmax())
    fig.add_vrect(x0=-0.5, x1=tepe + 0.5, fillcolor=rgba(TEAL, 0.06), line_width=0, layer="below",
                  annotation_text="yükseliş yapısı: HH + HL", annotation_position="top left",
                  annotation_font=dict(size=11, color=TEAL))
    fig.add_vrect(x0=tepe + 0.5, x1=len(df) - 0.5, fillcolor=rgba(BORDO, 0.06), line_width=0, layer="below",
                  annotation_text="düşüş yapısı: LH + LL", annotation_position="top right",
                  annotation_font=dict(size=11, color=BORDO))
    # 3-mum kuralı açıklaması: ilk swing high
    i0 = sh[0]
    kutu(fig, i0 - 1.5, i0 + 1.5, df.l[i0 - 1:i0 + 2].min() - 0.15, df.h[i0] + 0.15, GRI, a=0.08, cizgi=1, dash="dot")
    not_(fig, i0, df.h[i0] + 0.5, "3-mum kuralı: ortadaki mumun high'ı<br>iki komşusundan kesin yüksek → swing high",
         ax=60, ay=-45, boyut=10)
    # korunan dip
    kor = [i for i in sl if et.get(i) == "HL" and i < tepe]
    if kor:
        i = kor[-1]
        yatay(fig, df.l[i], i, tepe + 6, renk=TEAL, dash="dash")
        not_(fig, tepe + 6, df.l[i], "korunan dip (protected low): son HH'yi üreten bacağın HL'i<br>→ gövdeyle kırılınca yapı düşüşe döndü",
             renk=TEAL, ok=False, boyut=10, xanchor="left")
    duzen(fig, "Şekil 02 — Swing high/low ve HH/HL/LH/LL yapısı (şematik örnek)",
          "Kutu: 3-mum kuralı. İşaretler: gürültüyü elemek için 5-mum (k=2) sürümü; ITH/ITL = iki yanında daha alçak/yüksek swing bulunan swing")
    kaydet(fig, "02_swing_yapi_hh_hl")


# =====================================================================================
# 02 — BOS: gövde kapanışıyla yapı kırılımı; fitil aşımı BOS değildir
# =====================================================================================
def g02_bos():
    s = Seri(2)
    s.bacak(103.0, 6)                       # H1
    s.bacak(101.7, 4)                       # HL
    s.bacak(102.8, 3, gurultu=0.5)
    s.mum(s.son, 103.35, s.son - 0.05, 103.25, "BOS mumu: gövde 103.0 üstünde kapandı")  # gövde kapanışı > 103
    s.bacak(105.0, 4)                       # HH
    s.bacak(103.6, 4)                       # HL2
    s.bacak(104.7, 3, gurultu=0.5)
    s.mum(s.son + 0.05, 105.45, s.son - 0.15, s.son - 0.12, "fitil 105.0 üstüne çıktı, gövde altında kapandı → sweep, BOS değil")
    s.bacak(103.9, 3)
    s.bacak(104.9, 3, gurultu=0.5)
    s.mum(s.son, 105.6, s.son - 0.05, 105.5, "BOS #2: gövde 105.0 üstünde")
    s.bacak(107.2, 5)
    df = s.df()
    fig = go.Figure(mum_izi(df))
    sh, sl = swingler(df, 2)
    et = swing_etiketle(df, sh, sl)
    swing_isaretle(fig, df, sh, sl, et, k=2)
    # BOS 1
    i_b1 = int(df.index[df.lab.str.startswith("BOS mumu")][0])
    h1 = 103.0
    yatay(fig, h1, 5, i_b1, renk=TEAL, dash="solid", w=1.6)
    not_(fig, i_b1, df.c[i_b1], "<b>BOS</b> — gövde önceki HH'nin<br>üstünde kapandı (devam onayı)", renk=TEAL, ax=-10, ay=-60)
    # sweep
    i_sw = int(df.index[df.lab.str.startswith("fitil")][0])
    yatay(fig, 105.0, sh[[j for j in range(len(sh)) if abs(df.h[sh[j]] - 105.0) < 0.3][0]], i_sw + 3, renk=ALTIN, dash="dash")
    daire(fig, i_sw, 105.3, r_y=0.3)
    not_(fig, i_sw, 105.55, "fitil aştı, gövde geride → <b>sweep</b><br>(BOS DEĞİL: yapı için gövde, likidite için fitil)",
         renk=ALTIN, ax=-90, ay=-45)
    # BOS 2
    i_b2 = int(df.index[df.lab.str.startswith("BOS #2")][0])
    not_(fig, i_b2, df.c[i_b2], "<b>BOS #2</b> — bu kez gövde 105.0 üstünde", renk=TEAL, ax=-60, ay=-45)
    lejant_cizgi(fig, "kırılan swing seviyesi (BOS)", TEAL, "solid")
    lejant_cizgi(fig, "likidite seviyesi (sweep)", ALTIN)
    duzen(fig, "Şekil 03 — BOS: yapı kırılımı gövde kapanışıyla sayılır (şematik örnek)",
          "Aynı seviyede iki deneme: fitil aşımı = sweep (likidite), gövde kapanışı = BOS (yapı)")
    kaydet(fig, "03_bos_govde_kapanisi")


# =====================================================================================
# 03 — CHoCH / MSS: sweep → displacement → governing swing kırılımı (+ FVG)
# =====================================================================================
def g04_choch_mss():
    s = Seri(3)
    s.bacak(103.0, 5); s.bacak(101.8, 3); s.bacak(104.5, 5, lab="ITH")   # ITH 104.5 civarı
    s.bacak(103.0, 3, lab="ITL (governing swing)")                       # ITL 103.0
    s.bacak(104.1, 3)                                                    # STH
    s.bacak(103.7, 2, lab="STL (minör dip)")                             # STL 103.7
    s.bacak(104.3, 2, gurultu=0.4)
    s.mum(104.3, 104.95, 104.2, 104.25, "sweep: ITH üstüne fitil, gövde altında")   # sweep of ITH
    # displacement — 3 büyük kırmızı mum, ortada FVG bırakır
    s.mum(104.2, 104.3, 103.40, 103.45, "displacement 1: STL (≈103.60) altında gövde kapanışı → CHoCH")
    s.mum(103.45, 103.48, 103.00, 103.05, "displacement 2 (FVG mumu): ITL'nin (≈102.93) hâlâ üstünde kapanış")
    s.mum(103.05, 103.06, 102.05, 102.15, "displacement 3: ITL altında gövde kapanışı → MSS")
    s.bacak(101.9, 2, gurultu=0.4)
    s.bacak(103.25, 4)          # FVG'ye (CE'ye) geri çekilme
    s.bacak(102.4, 2)
    s.bacak(100.6, 5)
    df = s.df()
    fig = go.Figure(mum_izi(df))
    sh, sl = swingler(df, 1)
    et = swing_etiketle(df, sh, sl)
    swing_isaretle(fig, df, sh, sl, {})
    i_ith = int(df.index[df.lab == "ITH"][0]); i_itl = int(df.index[df.lab.str.startswith("ITL")][0])
    i_stl = int(df.index[df.lab.str.startswith("STL")][0])
    i_sw = int(df.index[df.lab.str.startswith("sweep")][0])
    i_d1 = i_sw + 1; i_d3 = i_sw + 3
    ith_h = df.h[i_ith - 1:i_ith + 2].max(); itl_l = df.l[i_itl - 1:i_itl + 2].min(); stl_l = df.l[i_stl - 1:i_stl + 2].min()
    # ITH / sweep
    yatay(fig, ith_h, i_ith, i_sw + 1, renk=ALTIN)
    daire(fig, i_sw, df.h[i_sw], r_y=0.22)
    not_(fig, i_sw, df.h[i_sw] + 0.15, "<b>sweep</b>: ITH üstündeki BSL alındı<br>(fitil ötede, gövde içeride)", renk=ALTIN, ax=60, ay=-55)
    # STL → CHoCH
    yatay(fig, stl_l, i_stl, i_d1 + 1, renk=BORDO, dash="dot")
    not_(fig, i_d1, stl_l, "<b>CHoCH</b> — ilk trend-aleyhine kırılım (STL)<br>= uyarı, tek başına işlem değil", renk=BORDO, ax=-130, ay=-140)
    # ITL → MSS
    yatay(fig, itl_l, i_itl, i_d3 + 1, renk=BORDO, dash="dash", w=1.8)
    not_(fig, i_d3, df.c[i_d3], "<b>MSS</b> — governing swing (ITL) gövde kapanışıyla kırıldı<br>displacement + FVG + sweep hikâyesi tamam", renk=BORDO, ax=120, ay=70)
    # FVG in displacement leg
    fv = [f for f in fvg_bul(df) if f["tip"] == "SIBI" and i_sw <= f["i"] <= i_d1]  # M1 sweep veya d1: FVG displacement bacağının içinde
    if fv:
        f = fv[-1]  # MSS mumuna en yakın (en alttaki) FVG — geri çekilmenin hedefi
        kutu(fig, f["i"], len(df) - 1, f["alt"], f["ust"], MOR, a=0.18)
        not_(fig, f["i"] + 8, (f["alt"] + f["ust"]) / 2, "FVG (SIBI) — displacement kanıtı;<br>geri çekilme buraya (CE)", renk=MOR, ax=60, ay=-95)
    # liquidity void: displacement bacağının tek yönlü, hızlı geçilen dikey aralığı (içinde FVG'ler)
    kutu(fig, i_d1 - 0.5, i_d3 + 0.5, df.l[i_d3], df.c[i_sw], GRI, a=0.07, cizgi=1, dash="dot")
    not_(fig, i_d1 - 0.8, df.l[i_d3] + 0.05, "<b>liquidity void</b>: tek yönlü, az işlemli<br>dikey aralık (içinde FVG'ler) — IRL", renk=GRI, ok=False, boyut=9, xanchor="right", yanchor="top")
    not_(fig, i_ith, ith_h + 0.6, "ITH", renk=BORDO, ok=False, boyut=10)
    not_(fig, i_itl, itl_l - 0.5, "ITL — düzeltmenin asıldığı dip", renk=TEAL, ok=False, boyut=10)
    lejant(fig, "FVG (SIBI)", MOR)
    lejant(fig, "liquidity void", GRI, a=0.12)
    lejant_cizgi(fig, "likidite (BSL)", ALTIN)
    lejant_cizgi(fig, "CHoCH (STL) / MSS (ITL) seviyesi", BORDO)
    duzen(fig, "Şekil 04 — CHoCH ve MSS: sweep → displacement → governing swing kırılımı (şematik örnek)",
          "CHoCH = ilk trend-aleyhine kırılım (uyarı); MSS = sweep sonrası displacement'lı, FVG bırakan, ITL'yi gövdeyle kıran kırılım (işlem gerekçesi)")
    kaydet(fig, "04_choch_mss")


# =====================================================================================
# 04 — Swing (external) yapı vs internal yapı
# =====================================================================================
def g05_internal_vs_swing():
    s = Seri(4)
    s.bacak(103.0, 5); s.bacak(101.5, 3, lab="swing HL (korunan dip)"); s.bacak(106.0, 8, lab="swing HH")
    # internal düşüş yapısı (düzeltme)
    s.bacak(104.9, 3, lab="ll"); s.bacak(105.5, 2, lab="lh"); s.bacak(104.0, 3, lab="ll"); s.bacak(104.7, 2, lab="lh")
    s.bacak(103.3, 3, lab="ll — swing HL adayı")
    s.bacak(104.9, 3, lab="internal CHoCH: lh kırıldı")
    s.bacak(104.3, 2); s.bacak(106.4, 4, lab="swing BOS"); s.bacak(108.0, 4)
    df = s.df()
    fig = go.Figure(mum_izi(df))
    def idx(p): return int(df.index[df.lab.str.startswith(p)][0])
    i_hl = idx("swing HL"); i_hh = idx("swing HH"); i_hl2 = idx("ll — swing"); i_ich = idx("internal CHoCH"); i_bos = idx("swing BOS")
    # swing yapısı büyük harf
    fig.add_trace(go.Scatter(x=[i_hl, i_hh, i_hl2], y=[df.l[i_hl] - 0.35, df.h[i_hh] + 0.35, df.l[i_hl2] - 0.35],
                             mode="markers+text", text=["HL", "HH", "HL"], textposition=["bottom center", "top center", "bottom center"],
                             marker=dict(size=13, color=[TEAL, BORDO, TEAL], symbol=["triangle-up", "triangle-down", "triangle-up"]),
                             textfont=dict(size=13, color=MUREKKEP), name="swing (external) yapı"))
    # internal
    ii = [i for i in range(i_hh + 1, i_hl2 + 1) if df.lab[i] in ("ll", "lh") or df.lab[i].startswith("ll —")]
    fig.add_trace(go.Scatter(x=ii, y=[df.h[i] + 0.2 if df.lab[i] == "lh" else df.l[i] - 0.2 for i in ii], mode="markers+text",
                             text=[df.lab[i][:2] for i in ii], textposition=["top center" if df.lab[i] == "lh" else "bottom center" for i in ii],
                             marker=dict(size=7, color=GRI), textfont=dict(size=10, color=GRI), name="internal (iç) yapı"))
    fig.add_vrect(x0=i_hh + 0.5, x1=i_ich + 0.5, fillcolor=rgba(GRI, 0.10), line_width=0, layer="below",
                  annotation_text="internal düşüş yapısı (lh/ll) — swing HL içinde", annotation_position="top left",
                  annotation_font=dict(size=11, color=GRI))
    yatay(fig, df.l[i_hl - 1:i_hl + 2].min(), i_hl, len(df) - 1, renk=TEAL, dash="dash")
    not_(fig, len(df) - 1, df.l[i_hl - 1:i_hl + 2].min(), "swing korunan dip — bu kırılmadıkça<br>swing yapısı yükseliştir", renk=TEAL, ok=False, boyut=10, xanchor="right", ay=20)
    # internal choch
    lh_lvl = df.h[[i for i in ii if df.lab[i] == "lh"][-1]]
    yatay(fig, lh_lvl, ii[-2], i_ich, renk=GRI, dash="dot")
    not_(fig, i_ich, lh_lvl, "internal CHoCH — düzeltme bitti sinyali<br>(swing CHoCH DEĞİL)", renk=GRI, ax=70, ay=35)
    hh_lvl = df.h[i_hh - 1:i_hh + 2].max()
    yatay(fig, hh_lvl, i_hh, i_bos, renk=TEAL, dash="solid", w=1.6)
    not_(fig, i_bos, hh_lvl, "<b>swing BOS</b> — external yapı devam", renk=TEAL, ax=-70, ay=-40)
    duzen(fig, "Şekil 05 — Swing (external) yapı ile internal yapı aynı grafikte (şematik örnek)",
          "Büyük harf = swing yapısı; küçük harf = swing HL'in içindeki düzeltmenin iç yapısı. Internal kırılım swing'i değiştirmez.")
    kaydet(fig, "05_internal_vs_swing")


# =====================================================================================
# 05 — Dealing range, premium/discount, EQ ve OTE fib
# =====================================================================================
def g05_dealing_range_ote():
    s = Seri(5)
    s.bacak(103.5, 4); s.bacak(100.6, 5)
    s.mum(100.6, 100.75, 99.60, 100.35, "sweep low (fib 1.0 çıpası)")
    s.mum(100.35, 101.7, 100.3, 101.6, "displacement")
    s.mum(101.6, 103.5, 101.55, 103.4, "displacement")
    s.bacak(105.3, 3); s.mum(s.son, 106.20, s.son - 0.1, 105.9, "swing high (fib 0 çıpası)")
    s.bacak(104.0, 3); s.bacak(102.4, 3); s.bacak(101.55, 3, gurultu=0.4, lab="OTE'ye dönüş (0.705)")
    s.bacak(103.8, 3); s.bacak(106.0, 3); s.bacak(108.0, 4, lab="T1 (−0.27)")
    df = s.df()
    L, H = 99.60, 106.20
    i_L = int(df.index[df.lab.str.startswith("sweep low")][0]); i_H = int(df.index[df.lab.str.startswith("swing high")][0])
    fig = go.Figure(mum_izi(df))
    n = len(df)
    eq = (L + H) / 2
    # dealing range: premium / discount
    kutu(fig, i_L - 0.5, n + 5, eq, H, BORDO, a=0.07, cizgi=0)
    kutu(fig, i_L - 0.5, n + 5, L, eq, TEAL, a=0.07, cizgi=0)
    not_(fig, i_L + 1, H - 0.3, "PREMIUM (pahalı) — sadece satış aranır", renk=BORDO, ok=False, boyut=11, xanchor="left")
    not_(fig, i_L + 1, L + 0.35, "DISCOUNT (ucuz) — sadece alım aranır", renk=TEAL, ok=False, boyut=11, xanchor="left")
    sev = fib_ciz(fig, L, H, i_L, n + 5, yon="bull", etiket_x=n + 5.2)
    fig.add_annotation(x=i_L, y=L, ax=i_H, ay=H, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                       arrowhead=0, arrowwidth=1.2, arrowcolor=ALTIN, text="")
    not_(fig, i_L, L - 0.4, "fib 1.0: sweep low (fitil)", renk=ALTIN, ok=False, boyut=10)
    not_(fig, i_H, H + 0.4, "fib 0: displacement bacağının high'ı (fitil)", renk=ALTIN, ok=False, boyut=10)
    i_ote = int(df.index[df.lab.str.startswith("OTE")][0])
    not_(fig, i_ote, df.l[i_ote], "<b>OTE bandı</b> 0.62–0.79 içinde dönüş<br>(0.705 sweet spot)", renk=ALTIN, ax=60, ay=45)
    not_(fig, (i_L + i_H) / 2 + 2, eq, "EQ = L + 0,5·(H − L)", renk=GRI, ok=False, boyut=10)
    lejant(fig, "OTE bandı (0.62–0.79)", ALTIN, a=0.16)
    lejant(fig, "premium", BORDO, a=0.1); lejant(fig, "discount", TEAL, a=0.1)
    fig.update_yaxes(range=[L - 1.2, 110.9])
    duzen(fig, "Şekil 06 — Dealing range, premium/discount, equilibrium ve ICT fib/OTE (şematik örnek)",
          "Bullish: fib sweep low (1.0) → displacement high (0) çekilir; 0.62–0.79 = OTE; −0.27/−0.62 hedef basamakları")
    kaydet(fig, "06_dealing_range_premium_discount_ote")


# =====================================================================================
# 06 — Equal highs/lows likiditesi, BSL/SSL, PDH/PDL, DOL
# =====================================================================================
def g06_eqh_eql():
    s = Seri(6)
    s.bacak(102.0, 3); s.bacak(105.0, 4); s.mum(s.son, 105.05, s.son - 0.2, 104.7, "EQH #1")
    s.bacak(101.2, 5); s.mum(s.son, s.son + 0.1, 100.98, 101.4, "EQL #1")
    s.bacak(104.6, 4); s.mum(s.son, 105.12, s.son - 0.2, 104.75, "EQH #2")
    s.bacak(101.4, 5); s.mum(s.son, s.son + 0.1, 100.92, 101.35, "EQL #2")
    s.bacak(104.5, 4); s.mum(s.son, 104.97, s.son - 0.2, 104.6, "EQH #3")
    s.bacak(103.0, 3); s.bacak(103.6, 3, gurultu=0.4)
    s.mum(103.6, 105.45, 103.5, 104.55, "EQH sweep: fitil 105.1 üstü, gövde altı")
    s.bacak(103.4, 3)
    df = s.df(); n = len(df)
    fig = go.Figure(mum_izi(df))
    eqh = [int(i) for i in df.index[df.lab.str.startswith("EQH #")]]
    eql = [int(i) for i in df.index[df.lab.str.startswith("EQL #")]]
    i_sw = int(df.index[df.lab.str.startswith("EQH sweep")][0])
    hy = np.mean([df.h[i] for i in eqh]); ly = np.mean([df.l[i] for i in eql])
    tol = 0.09
    kutu(fig, eqh[0], i_sw, hy - tol, hy + tol, ALTIN, a=0.16, cizgi=0)
    yatay(fig, hy, eqh[0], i_sw, renk=ALTIN, w=1.6)
    kutu(fig, eql[0], n, ly - tol, ly + tol, ALTIN, a=0.16, cizgi=0)
    yatay(fig, ly, eql[0], n, renk=ALTIN, w=1.6)
    for i in eqh: not_(fig, i, df.h[i] + 0.12, "EQH", renk=ALTIN, ok=False, boyut=10)
    for i in eql: not_(fig, i, df.l[i] - 0.12, "EQL", renk=ALTIN, ok=False, boyut=10)
    not_(fig, eqh[1], hy + 0.55, "<b>BSL &#36;&#36;&#36;</b> — short stopları + breakout alımları<br>EQH = direnç değil, mıknatıs", renk=ALTIN, ok=False, boyut=10)
    not_(fig, eql[1], ly - 0.55, "<b>SSL &#36;&#36;&#36;</b> — long stopları + breakdown satışları", renk=ALTIN, ok=False, boyut=10)
    not_(fig, eql[0] + 1, ly + 0.25, "tolerans bandı ≈ %10–15 ATR(14) (ders önerisi)", renk=GRI, ok=False, boyut=9, xanchor="left")
    # PDH / PDL
    yatay(fig, 105.9, -0.5, n, renk=BORDO, dash="dashdot", w=1.4); not_(fig, 0, 105.9, "PDH (önceki gün high) — BSL", renk=BORDO, ok=False, boyut=10, xanchor="left", ay=-12)
    yatay(fig, 100.4, -0.5, n, renk=TEAL, dash="dashdot", w=1.4); not_(fig, 0, 100.4, "PDL (önceki gün low) — SSL", renk=TEAL, ok=False, boyut=10, xanchor="left", ay=12)
    # sweep + DOL
    daire(fig, i_sw, df.h[i_sw], r_y=0.25)
    fig.add_annotation(x=i_sw, y=hy, text="✕", showarrow=False, font=dict(size=18, color=ALTIN))
    not_(fig, i_sw, df.h[i_sw] + 0.2, "EQH süpürüldü (sweep): fitil ötede, gövde içeride<br>→ çizgi üstüne ✕", renk=ALTIN, ax=-110, ay=-45)
    fig.add_annotation(x=n - 1, y=df.c[n - 1], ax=n - 1, ay=ly + 0.15, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowwidth=2, arrowcolor=TEAL, text="")
    not_(fig, n - 1, (df.c[n - 1] + ly) / 2, "<b>DOL</b> (draw on liquidity):<br>BSL alındı → sıradaki mıknatıs EQL/SSL", renk=TEAL, ok=False, boyut=10, xanchor="right")
    lejant(fig, "eşit tepe/dip tolerans bandı", ALTIN, a=0.16)
    duzen(fig, "Şekil 09 — Equal highs / equal lows: likidite havuzları, PDH/PDL ve DOL (şematik örnek)",
          "Üç eşit tepe = BSL mıknatısı; alınınca ✕; fiyat ERL → karşı ERL'ye (DOL) salınır")
    kaydet(fig, "09_equal_highs_lows_likidite")


# =====================================================================================
# 07 — Sweep (turtle soup) vs liquidity run — iki panel
# =====================================================================================
def g07_sweep_vs_run():
    def on_kisim(seed):
        s = Seri(seed)
        s.bacak(102.5, 3); s.bacak(100.0, 4, lab="PDL / eski dip"); s.bacak(101.6, 4); s.bacak(100.5, 3, gurultu=0.5)
        return s
    # (a) sweep
    a = on_kisim(71)
    a.mum(a.son, a.son + 0.05, 99.45, 100.35, "SWEEP: fitil 100.0 altı, gövde üstünde kapandı")
    a.mum(100.35, 101.0, 100.3, 100.95, "displacement")
    a.mum(100.95, 101.9, 100.9, 101.8, "MSS: 101.6 üstü gövde kapanışı")
    a.bacak(103.2, 4)
    # (b) run
    b = on_kisim(72)
    b.mum(b.son, b.son + 0.05, 99.3, 99.4, "RUN: gövde 100.0 altında kapandı")
    b.mum(99.4, 99.45, 98.5, 98.6, "devam")
    b.bacak(98.9, 2, gurultu=0.4); b.bacak(97.6, 4)
    da, db = a.df(), b.df()
    # okunabilirlik: paneller alt alta (tek sütun) — okuma sırası (a) üst, (b) alt
    fig = make_subplots(rows=2, cols=1, subplot_titles=("(a) SWEEP — fitil ötede, gövde içeride → turtle soup / dönüş",
                                                        "(b) LIQUIDITY RUN — gövde ötede kapandı → kırılım / devam"),
                        vertical_spacing=0.09)
    fig.add_trace(mum_izi(da, ad="Mum (a)"), row=1, col=1)
    fig.add_trace(mum_izi(db, ad="Mum (b)", gorunur=False), row=2, col=1)
    for satir, d in ((1, da), (2, db)):
        i_pdl = int(d.index[d.lab.str.startswith("PDL")][0])
        pdl = d.l[i_pdl - 1:i_pdl + 2].min()
        yatay(fig, pdl, i_pdl, len(d) - 1, renk=ALTIN, w=1.6, row=satir, col=1)
        not_(fig, i_pdl, pdl - 0.25, "PDL / eski dip — SSL", renk=ALTIN, ok=False, boyut=10, row=satir, col=1)
    i_sw = int(da.index[da.lab.str.startswith("SWEEP")][0])
    daire(fig, i_sw, da.l[i_sw] + 0.15, r_y=0.3, row=1, col=1)
    not_(fig, i_sw, da.l[i_sw], "<b>sweep</b>: stoplar tetiklendi,<br>gövde seviyenin üstünde", renk=ALTIN, ax=-70, ay=40, row=1, col=1)
    i_m = int(da.index[da.lab.str.startswith("MSS")][0])
    yatay(fig, 101.6, i_sw - 4, i_m, renk=BORDO, dash="dot", row=1, col=1)
    not_(fig, i_m, da.c[i_m], "MSS: yakın swing high gövdeyle kırıldı<br>→ turtle soup girişi (Raschke: eski dip üstüne buy-stop)", renk=TEAL, ax=-60, ay=-45, row=1, col=1)
    i_r = int(db.index[db.lab.str.startswith("RUN")][0])
    not_(fig, i_r, db.c[i_r], "<b>run</b>: gövde 100.0 altında kapandı,<br>büyük kırmızı mumlar → karşı işlem yok,<br>DOL aşağıdaki sonraki havuza kayar", renk=BORDO, ax=110, ay=-110, row=2, col=1)
    duzen(fig, "Şekil 10 — Aynı seviyede iki farklı sonuç: sweep mi, liquidity run mı? (şematik örnek)",
          "Ayrım ancak mum KAPANIŞIYLA yapılır — canlıda fitil ötedeyken henüz bilinmez", h=860)
    fig.update_xaxes(title_text="mum sırası", row=2, col=1)
    kaydet(fig, "10_sweep_vs_liquidity_run")


# =====================================================================================
# 08 — Inducement (IDM)
# =====================================================================================
def g11_inducement():
    s = Seri(8)
    s.bacak(105.5, 3); s.bacak(103.0, 4); s.bacak(101.5, 3, gurultu=0.5)
    s.mum(101.5, 101.65, 100.7, 101.05, "OB mumu (son kırmızı) + SSL sweep")
    s.mum(101.05, 102.2, 101.0, 102.1, "displacement"); s.mum(102.1, 103.7, 102.05, 103.6, "displacement"); s.mum(103.6, 104.3, 103.5, 104.2, "displacement")
    s.bacak(105.0, 2, gurultu=0.4)
    s.bacak(103.9, 2, gurultu=0.4); s.mum(s.son, s.son + 0.05, 103.62, 103.78, "IDM: ilk pullback dibi (retail long + stop yeri)")
    s.bacak(104.6, 3)
    s.mum(104.5, 104.55, 103.25, 103.35, "IDM süpürüldü (gövde altta)")
    s.bacak(102.4, 2); s.mum(102.4, 102.45, 101.2, 101.6, "OB'ye dokunuş → giriş")
    s.bacak(103.5, 2); s.bacak(105.5, 3); s.bacak(107.0, 3)
    df = s.df(); n = len(df)
    fig = go.Figure(mum_izi(df))
    i_ob = int(df.index[df.lab.str.startswith("OB")][0]); i_idm = int(df.index[df.lab.str.startswith("IDM:")][0])
    i_sw = int(df.index[df.lab.str.startswith("IDM süp")][0]); i_g = int(df.index[df.lab.str.startswith("OB'ye")][0])
    kutu(fig, i_ob, n, df.c[i_ob], df.o[i_ob], MAVI, a=0.22)
    not_(fig, i_ob + 1, df.o[i_ob], "POI: bullish OB (sweep + displacement)", renk=MAVI, ok=False, boyut=10, xanchor="left", ay=-14)
    idm_l = df.l[i_idm]
    yatay(fig, idm_l, i_idm, i_sw + 1, renk=ALTIN, dash="dash", w=1.5)
    fig.add_annotation(x=i_sw, y=idm_l, text="✕", showarrow=False, font=dict(size=18, color=ALTIN))
    not_(fig, i_idm, idm_l - 0.2, "<b>IDM</b> (inducement): POI'den önceki ilk minör dip —<br>retail burada long alır, stopunu altına koyar", renk=ALTIN, ax=-90, ay=45)
    not_(fig, i_sw, df.c[i_sw], "IDM süpürüldü → yem alındı,<br>şimdi POI'ye dokunuş beklenir", renk=ALTIN, ax=80, ay=-30)
    fig.add_annotation(x=i_g, y=df.l[i_g], ax=i_g, ay=df.l[i_g] - 0.9, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowwidth=2, arrowcolor=TEAL, text="")
    not_(fig, i_g, df.l[i_g] - 1.0, "OB'ye giriş (limit)<br>SL: OB fitilinin altı", renk=TEAL, ok=False, boyut=10, yanchor="top")
    not_(fig, i_idm - 8, 106.6, "kural: geçerli swing, IDM alındıktan sonra oluşur;<br>IDM'de erken alan, POI'ye gelmeden stoplanır", renk=GRI, ok=False, boyut=10, xanchor="left")
    lejant(fig, "Order block (POI)", MAVI); lejant_cizgi(fig, "IDM seviyesi", ALTIN)
    duzen(fig, "Şekil 11 — Inducement (IDM): POI'den önce duran yem (şematik örnek)",
          "İlk pullback'in STL'i süpürülmeden POI'ye giriş aranmaz; STL kırılışı MSS değil, inducement'tır")
    kaydet(fig, "11_inducement")


# =====================================================================================
# 09 — Trendline liquidity
# =====================================================================================
def g09_trendline():
    s = Seri(9)
    s.bacak(101.4, 3); s.mum(s.son, s.son + 0.1, 100.5, 100.9, "temas 1")   # i=3
    s.bacak(103.5, 6); s.bacak(102.4, 3, gurultu=0.4); s.mum(s.son, s.son + 0.05, 102.0, 102.35, "temas 2")  # i=13
    s.bacak(105.2, 6); s.bacak(103.9, 3, gurultu=0.4); s.mum(s.son, s.son + 0.05, 103.5, 103.85, "temas 3")  # i=23
    s.bacak(106.4, 5); s.bacak(105.6, 3, gurultu=0.4)
    df0 = s.df()
    t = [int(i) for i in df0.index[df0.lab.str.startswith("temas")]]
    x1, x2 = t[0], t[-1]
    y1, y2 = df0.l[t[0]], df0.l[t[-1]]
    egim = (y2 - y1) / (x2 - x1)
    def cizgi(x): return y1 + egim * (x - x1)
    i_sw = s.n
    s.mum(s.son, s.son + 0.05, cizgi(i_sw) - 0.55, cizgi(i_sw) + 0.25, "trendline SWEEP: çizgi altına fitil, gövde üstte")
    s.mum(s.son, s.son + 0.9, s.son - 0.05, s.son + 0.85, "geri kazanım")
    s.bacak(107.5, 3); s.bacak(108.8, 3)
    df = s.df(); n = len(df)
    fig = go.Figure(mum_izi(df))
    xs = [x1 - 1, n - 1]
    fig.add_trace(go.Scatter(x=xs, y=[cizgi(x) for x in xs], mode="lines", line=dict(color=ALTIN, width=1.8), name="trend çizgisi (≥3 temas)"))
    # diyagonal SSL gölgesi
    fig.add_shape(type="path", path=f"M {x1-1},{cizgi(x1-1)} L {n-1},{cizgi(n-1)} L {n-1},{cizgi(n-1)-0.6} L {x1-1},{cizgi(x1-1)-0.6} Z",
                  fillcolor=rgba(ALTIN, 0.15), line_width=0, layer="below")
    for k, i in enumerate(t, 1):
        not_(fig, i - 0.7, df.l[i] - 0.05, f"temas {k}", renk=ALTIN, ok=False, boyut=10, xanchor="right", yanchor="top")
    daire(fig, i_sw, df.l[i_sw] + 0.2, r_y=0.35)
    not_(fig, i_sw, df.l[i_sw], "<b>trendline sweep</b>: çizgi altındaki sell-stop'lar alındı,<br>gövde çizginin üstünde kapandı → kırılım değil", renk=ALTIN, ax=-120, ay=45)
    not_(fig, t[1], cizgi(t[1]) - 0.9, "diyagonal SSL: 'herkes çiziyor' → çizginin altı stop havuzu", renk=ALTIN, ok=False, boyut=10)
    lejant(fig, "trendline likiditesi (SSL bandı)", ALTIN, a=0.15)
    duzen(fig, "Şekil 12 — Trendline liquidity: görünür trend çizgisi altındaki stop havuzu (şematik örnek)",
          "≥3 temaslı çizgi = diyagonal likidite; senaryo 'kırılım' değil 'sweep + geri kazanım'")
    kaydet(fig, "12_trendline_liquidity")


# =====================================================================================
# 10 — FVG (BISI / SIBI) + CE — iki panel
# =====================================================================================
def g10_fvg():
    def bull(seed):
        s = Seri(seed)
        s.bacak(100.5, 5, gurultu=0.6); s.bacak(100.2, 3, gurultu=0.5)
        s.mum(100.2, 100.55, 100.0, 100.45, "M1 (öncü)")
        s.mum(100.45, 102.3, 100.4, 102.2, "M2 (displacement)")
        s.mum(102.2, 102.7, 101.4, 102.55, "M3 (takip)")
        s.bacak(103.2, 3); s.bacak(101.05, 3, lab="CE'ye kısmi dolum → tepki"); s.bacak(103.8, 4)
        return s.df()
    def bear(seed):
        s = Seri(seed)
        s.bacak(103.5, 5, gurultu=0.6); s.bacak(103.8, 3, gurultu=0.5)
        s.mum(103.8, 104.0, 103.45, 103.55, "M1 (öncü)")
        s.mum(103.55, 103.6, 101.7, 101.8, "M2 (displacement)")
        s.mum(101.8, 102.6, 101.3, 101.45, "M3 (takip)")
        s.bacak(100.8, 3); s.bacak(102.95, 3, lab="CE'ye kısmi dolum → tepki"); s.bacak(100.2, 4)
        return s.df()
    da, db = bull(101), bear(102)
    # okunabilirlik: paneller alt alta (tek sütun)
    fig = make_subplots(rows=2, cols=1, subplot_titles=("(a) Bullish FVG — BISI: high(M1) < low(M3)", "(b) Bearish FVG — SIBI: low(M1) > high(M3)"), vertical_spacing=0.09)
    fig.add_trace(mum_izi(da, ad="Mum (a)"), row=1, col=1)
    fig.add_trace(mum_izi(db, ad="Mum (b)", gorunur=False), row=2, col=1)
    for satir, d, tip in ((1, da, "BISI"), (2, db, "SIBI")):
        i1 = int(d.index[d.lab.str.startswith("M1")][0])
        f = [f for f in fvg_bul(d) if f["i"] == i1][0]
        n = len(d)
        kutu(fig, i1, n - 1, f["alt"], f["ust"], MOR, a=0.2, row=satir, col=1)
        ce = (f["alt"] + f["ust"]) / 2
        yatay(fig, ce, i1, n - 1, renk=MOR, dash="dash", row=satir, col=1)
        not_(fig, n - 1, ce, f"CE = %50 → {ce:.2f}", renk=MOR, ok=False, boyut=10, xanchor="right", ay=-12, row=satir, col=1)
        for k in range(3):
            not_(fig, i1 + k, d.h[i1 + k] + 0.12 if satir == 1 else d.l[i1 + k] - 0.12, f"M{k+1}", renk=GRI, ok=False, boyut=10, row=satir, col=1)
        a_ = atr(d, 14)[i1 + 1]
        govde = abs(d.c[i1 + 1] - d.o[i1 + 1])
        not_(fig, i1 + 1, (d.o[i1 + 1] + d.c[i1 + 1]) / 2, f"M2 gövde ≈ {govde/a_:.1f}×ATR(14)<br>gövde/aralık %{100*govde/(d.h[i1+1]-d.l[i1+1]):.0f}",
             renk=TEAL if satir == 1 else BORDO, ax=-100, ay=-20 if satir == 1 else 10, row=satir, col=1)
        alt_ad = "high(M1)" if tip == "BISI" else "high(M3)"; ust_ad = "low(M3)" if tip == "BISI" else "low(M1)"
        not_(fig, i1 + 3, f["alt"], f"{alt_ad} = {f['alt']:.2f}", renk=MOR, ok=False, boyut=9, xanchor="left", ay=10, row=satir, col=1)
        not_(fig, i1 + 3, f["ust"], f"{ust_ad} = {f['ust']:.2f}", renk=MOR, ok=False, boyut=9, xanchor="left", ay=-10, row=satir, col=1)
        i_ce = int(d.index[d.lab.str.startswith("CE")][0])
        not_(fig, i_ce, d.l[i_ce] if satir == 1 else d.h[i_ce], "kısmi dolum: CE'ye kadar girdi, tepki<br>(fresh → partially filled)", renk=MOR, ax=40, ay=40 if satir == 1 else -40, row=satir, col=1)
    lejant(fig, "FVG (imbalance)", MOR); lejant_cizgi(fig, "CE (consequent encroachment)", MOR)
    duzen(fig, "Şekil 15 — Fair Value Gap: BISI ve SIBI, CE (%50) ve kısmi dolum (şematik örnek)",
          "Üç mum: 1. ve 3. mumun fitilleri örtüşmez; orta mum displacement mumu (gövde ≥ %60, ≥1,5× ATR)", h=860)
    fig.update_xaxes(title_text="mum sırası", row=2, col=1)
    kaydet(fig, "15_fvg_bisi_sibi_ce")


# =====================================================================================
# 11 — Inversion FVG
# =====================================================================================
def g11_ifvg():
    s = Seri(11)
    s.bacak(100.6, 4, gurultu=0.5)
    s.mum(100.6, 100.85, 100.4, 100.75, "M1"); s.mum(100.75, 102.4, 100.7, 102.3, "M2 displacement"); s.mum(102.3, 102.8, 101.6, 102.6, "M3")
    s.bacak(103.4, 3); s.bacak(101.5, 2); s.mum(s.son, s.son + 0.05, 101.15, 101.45, "ilk dönüş: CE tuttu"); s.bacak(103.0, 3)
    s.mum(103.0, 103.05, 100.4, 100.5, "gövde FVG'nin ALTINDA kapandı → inversion")
    s.bacak(100.35, 2, gurultu=0.4); s.mum(100.45, 101.35, 100.25, 100.3, "IFVG retest (fitil), red"); s.bacak(99.0, 3); s.bacak(98.0, 3)
    df = s.df(); n = len(df)
    fig = go.Figure(mum_izi(df))
    i1 = int(df.index[df.lab == "M1"][0]); f = [f for f in fvg_bul(df) if f["i"] == i1][0]
    i_inv = int(df.index[df.lab.str.startswith("gövde")][0]); i_rt = int(df.index[df.lab.str.startswith("IFVG")][0])
    kutu(fig, i1, i_inv, f["alt"], f["ust"], MOR, a=0.2)
    kutu(fig, i_inv, n - 1, f["alt"], f["ust"], BORDO, a=0.2)
    ce = (f["alt"] + f["ust"]) / 2
    yatay(fig, ce, i1, n - 1, renk=MOR, dash="dash")
    not_(fig, i1 + 4, f["ust"] + 0.15, "bullish FVG (BISI) — destek beklenir", renk=MOR, ok=False, boyut=10, xanchor="left")
    i_ce = int(df.index[df.lab.str.startswith("ilk")][0])
    not_(fig, i_ce, df.l[i_ce], "1. dönüş: CE'de tuttu (kısmi dolum)", renk=MOR, ax=-70, ay=35)
    not_(fig, i_inv, df.c[i_inv], "<b>inversion</b>: FVG'nin tamamı GÖVDEYLE geçildi<br>(fitil yetmez) → bullish FVG artık bearish IFVG", renk=BORDO, ax=-120, ay=40)
    not_(fig, i_rt, df.h[i_rt], "IFVG retest: fitil eski FVG'ye girdi,<br>gövde altında kapandı → short girişi<br>SL: IFVG üst kenarının üstü", renk=BORDO, ax=70, ay=-55)
    daire(fig, i_rt, df.h[i_rt] - 0.15, r_y=0.3, renk=BORDO)
    lejant(fig, "FVG (bullish)", MOR); lejant(fig, "IFVG (bearish — rol tersine döndü)", BORDO)
    duzen(fig, "Şekil 16 — Inversion FVG: gövdeyle geçilen FVG rol değiştirir (şematik örnek)",
          "Destek olan boşluk, gövde kapanışıyla aşılınca direnç olur; ilk retest giriş yeri")
    kaydet(fig, "16_inversion_fvg")


# =====================================================================================
# 12 — Order block anatomisi: sweep + displacement + FVG + MSS, MT, stop referansı
# =====================================================================================
def g12_order_block():
    s = Seri(12)
    s.bacak(103.5, 3); s.bacak(100.0, 4, lab="eski dip (SSL)"); s.bacak(102.4, 4, lab="LH — MSS referansı"); s.bacak(100.7, 4, gurultu=0.5)
    s.mum(100.65, 100.72, 99.50, 100.20, "OB mumu: son kırmızı mum + SSL sweep (fitil 99.50)")
    s.mum(100.20, 101.55, 100.15, 101.45, "displacement 1")
    s.mum(101.45, 103.25, 101.40, 103.15, "displacement 2 (FVG mumu, MSS: 102.4 üstü kapanış)")
    s.mum(103.15, 103.9, 103.0, 103.75, "displacement 3")
    s.bacak(104.3, 2, gurultu=0.4)
    s.bacak(102.2, 3); s.bacak(101.05, 3, gurultu=0.4)
    s.mum(101.05, 101.08, 100.40, 100.80, "OB retest: fitil MT'ye kadar, gövde FVG içinde / OB'nin hemen üstünde")
    s.bacak(102.6, 3); s.bacak(105.0, 4)
    df = s.df(); n = len(df)
    fig = go.Figure(mum_izi(df))
    i_ob = int(df.index[df.lab.str.startswith("OB mumu")][0]); i_lh = int(df.index[df.lab.str.startswith("LH")][0])
    i_d2 = i_ob + 2; i_rt = int(df.index[df.lab.str.startswith("OB retest")][0])
    ob_ust, ob_alt, ob_fitil = df.o[i_ob], df.c[i_ob], df.l[i_ob]
    mt = (ob_ust + ob_alt) / 2
    # OB
    kutu(fig, i_ob, n - 1, ob_alt, ob_ust, MAVI, a=0.24)
    yatay(fig, mt, i_ob, n - 1, renk=MAVI, dash="dash")
    yatay(fig, ob_fitil, i_ob, n - 1, renk=BORDO, dash="dot")
    not_(fig, n - 0.5, ob_ust, f"OB open {ob_ust:.2f} — 1. giriş", renk=MAVI, ok=False, boyut=10, xanchor="left", ay=-6)
    not_(fig, n - 0.5, mt, f"MT (gövde %50) {mt:.2f} — 2. giriş", renk=MAVI, ok=False, boyut=10, xanchor="left", ay=6)
    not_(fig, n - 0.5, ob_fitil, f"fitil low {ob_fitil:.2f} — SL ref. (+ tampon)", renk=BORDO, ok=False, boyut=10, xanchor="left", ay=0)
    not_(fig, i_ob, ob_fitil - 0.05, "<b>OB mumu</b>: displacement'tan hemen önceki<br>son kırmızı mum (gövde = bölge)", renk=MAVI, ax=-60, ay=45)
    # sweep
    ssl = df.l[int(df.index[df.lab.str.startswith('eski dip')][0]) - 1: int(df.index[df.lab.str.startswith('eski dip')][0]) + 2].min()
    yatay(fig, ssl, 3, i_ob + 1, renk=ALTIN, w=1.5)
    daire(fig, i_ob, ob_fitil + 0.2, r_y=0.3)
    not_(fig, i_ob - 4, ssl - 0.15, "① SSL süpürüldü (fitil eski dibin altına)", renk=ALTIN, ok=False, boyut=10)
    # FVG
    # OB'nin hemen üstündeki FVG (M1 = OB mumu): OB+FVG confluence; geri çekilme bu FVG'nin alt kenarını gövdeyle geçmez
    f = [f for f in fvg_bul(df) if f["tip"] == "BISI" and f["i"] == i_ob][0]
    kutu(fig, f["i"], n - 1, f["alt"], f["ust"], MOR, a=0.18)
    not_(fig, f["i"] + 4, (f["alt"] + f["ust"]) / 2, "② displacement + FVG (imbalance) — OB'nin hemen üstünde", renk=MOR, ax=60, ay=-30)
    # MSS
    lh = df.h[i_lh - 1:i_lh + 2].max()
    yatay(fig, lh, i_lh, i_d2 + 1, renk=BORDO, dash="dash", w=1.6)
    not_(fig, i_d2, df.c[i_d2], "③ MSS/BOS: LH gövdeyle kırıldı<br>(OB, kırılımı yapan bacakta)", renk=TEAL, ax=90, ay=-30)
    # retest
    not_(fig, i_rt, df.l[i_rt], "④ fresh OB'ye ilk dönüş: fitil MT'ye kadar<br>(OB open limiti doldu), gövde OB'nin hemen üstünde<br>→ giriş; MT altına gövde = zayıflama", renk=MAVI, ax=30, ay=80)
    # premium/discount — retest anında bilinen aralık: sweep low → displacement/MSS high (hindsight yok)
    eq = (ob_fitil + df.h[:i_rt].max()) / 2
    yatay(fig, eq, i_ob, n - 1, renk=GRI, dash="dot")
    not_(fig, i_ob + 1, eq, f"EQ {eq:.2f} (sweep low → displacement high) → OB discount'ta ✓ (⑤)", renk=GRI, ok=False, boyut=10, xanchor="left", ay=-12)
    lejant(fig, "Order block (gövde)", MAVI); lejant(fig, "FVG", MOR); lejant_cizgi(fig, "SSL", ALTIN, "solid"); lejant_cizgi(fig, "MT", MAVI)
    fig.update_xaxes(range=[-1, n + 11]); fig.update_yaxes(range=[98.9, 105.5])
    duzen(fig, "Şekil 17 — Order block anatomisi: 5 geçerlilik kriteri tek grafikte (şematik örnek)",
          "① sweep ② displacement + FVG ③ yapı kırılımı ④ fresh (ilk test) ⑤ discount'ta; bölge = gövde, stop = fitil")
    kaydet(fig, "17_order_block_anatomisi")


# =====================================================================================
# 13 — Breaker block (bullish)
# =====================================================================================
def g13_breaker():
    s = Seri(13, baslangic=102.4)
    s.bacak(101.0, 4, lab="L"); s.bacak(103.4, 4, gurultu=0.5)
    s.mum(s.son, 104.05, s.son - 0.05, 103.95, "H — breaker mumu (LL'ye düşüşten önceki son yeşil mum)")
    s.bacak(102.2, 4); s.bacak(101.3, 2, gurultu=0.4)
    s.mum(101.3, 101.35, 100.45, 100.85, "LL: L'nin altına sweep")
    s.mum(100.85, 102.3, 100.8, 102.2, "displacement"); s.mum(102.2, 103.7, 102.15, 103.6, "displacement")
    s.mum(103.6, 104.7, 103.55, 104.6, "HH: H'nin üstünde gövde kapanışı → OB kırıldı, breaker doğdu")
    s.bacak(105.4, 3); s.bacak(104.4, 3); s.mum(104.4, 104.45, 103.55, 103.9, "breaker retest → destek"); s.bacak(105.5, 3); s.bacak(107.0, 4)
    df = s.df(); n = len(df)
    fig = go.Figure(mum_izi(df))
    i_L = int(df.index[df.lab == "L"][0]); i_H = int(df.index[df.lab.str.startswith("H —")][0])
    i_LL = int(df.index[df.lab.str.startswith("LL")][0]); i_HH = int(df.index[df.lab.str.startswith("HH")][0]); i_rt = int(df.index[df.lab.str.startswith("breaker retest")][0])
    L = df.l[i_L - 1:i_L + 2].min(); H = df.h[i_H]
    yatay(fig, L, i_L, i_LL + 1, renk=ALTIN); not_(fig, i_L, L - 0.2, "L (eski low)", renk=ALTIN, ok=False, boyut=10)
    yatay(fig, H, i_H, i_HH + 1, renk=BORDO, dash="dash", w=1.6); not_(fig, i_H, H + 0.25, "H (kırılan high)", renk=BORDO, ok=False, boyut=10)
    daire(fig, i_LL, df.l[i_LL] + 0.15, r_y=0.3); not_(fig, i_LL, df.l[i_LL], "<b>LL = sweep</b> (breaker'ın zorunlu koşulu)", renk=ALTIN, ax=-40, ay=45)
    # başarısız bearish OB → bullish breaker
    kutu(fig, i_H, i_HH, df.o[i_H], df.c[i_H], BORDO, a=0.12, dash="dot")
    not_(fig, i_H, df.o[i_H] - 0.15, "bearish OB adayı (son yeşil mum) — tutmadı", renk=BORDO, ax=-90, ay=40)
    kutu(fig, i_HH, n - 1, df.o[i_H], df.c[i_H], TURUNCU, a=0.25)
    not_(fig, i_HH, df.c[i_HH], "<b>HH</b>: H'nin üstünde gövde → OB kırıldı,<br>aynı gövde artık <b>bullish breaker</b>", renk=TEAL, ax=-30, ay=-55)
    not_(fig, i_rt, df.l[i_rt], "breaker retest: destek → giriş,<br>SL breaker altı", renk=TURUNCU, ax=60, ay=45)
    not_(fig, i_L + 1, 106.4, "dizi: L → H → LL (sweep) → HH (gövde kırılımı) → retest", renk=GRI, ok=False, boyut=10, xanchor="left")
    lejant(fig, "breaker block (bullish)", TURUNCU); lejant(fig, "başarısız OB", BORDO, a=0.12)
    duzen(fig, "Şekil 18 — Breaker block: sweep sonrası kırılan OB rol değiştirir (şematik örnek)",
          "Breaker = kırılmış OB, yön tersine döner; mitigation block = tutmuş OB, yön aynı (Şekil 19)")
    kaydet(fig, "18_breaker_block")


# =====================================================================================
# 14 — Mitigation block (V1 tutan OB / V2 ICT-orijinal sweep'siz)
# =====================================================================================
def g14_mitigation():
    # (a) V1
    a = Seri(141)
    a.bacak(103.0, 3); a.bacak(100.6, 4, gurultu=0.5); a.mum(a.son, a.son + 0.05, 99.7, 100.2, "OB mumu + sweep")
    a.mum(100.2, 101.4, 100.15, 101.3, "d1"); a.mum(101.3, 102.9, 101.25, 102.8, "d2"); a.mum(102.8, 103.6, 102.7, 103.5, "d3")
    a.bacak(104.6, 3); a.bacak(101.4, 4); a.mum(101.4, 101.45, 100.35, 100.9, "MB retest: OB low'unu gövde geçmedi"); a.bacak(102.8, 3); a.bacak(105.5, 4)
    # (b) V2 bearish
    b = Seri(142)
    b.bacak(105.0, 4, lab="H"); b.bacak(102.0, 4, lab="L"); b.bacak(103.9, 3, gurultu=0.4)
    b.mum(b.son, 104.25, b.son - 0.05, 104.15, "LH — H'yi süpüremedi (sweep yok); son yeşil mum = MB")
    b.mum(104.15, 104.2, 103.0, 103.1, "d1"); b.mum(103.1, 103.15, 101.5, 101.6, "d2: L altında gövde → kırılım"); b.mum(101.6, 101.7, 100.8, 100.9, "d3")
    b.bacak(100.3, 2); b.bacak(103.5, 4); b.mum(103.5, 104.2, 103.4, 103.6, "MB retest → direnç"); b.bacak(101.5, 3); b.bacak(99.5, 4)
    da, db = a.df(), b.df()
    # okunabilirlik: paneller alt alta (tek sütun)
    fig = make_subplots(rows=2, cols=1, subplot_titles=("(a) V1 (yaygın): tutan OB'nin devam retest'i", "(b) V2 (ICT-orijinal): sweep OLMADAN kırılan bacağın son zıt mumu"), vertical_spacing=0.09)
    fig.add_trace(mum_izi(da, ad="Mum (a)"), row=1, col=1); fig.add_trace(mum_izi(db, ad="Mum (b)", gorunur=False), row=2, col=1)
    # (a)
    i_ob = int(da.index[da.lab.str.startswith("OB")][0]); i_rt = int(da.index[da.lab.str.startswith("MB")][0]); n = len(da)
    kutu(fig, i_ob, n - 1, da.c[i_ob], da.o[i_ob], MAVI, a=0.24, row=1, col=1)
    yatay(fig, da.l[i_ob], i_ob, n - 1, renk=BORDO, dash="dot", row=1, col=1)
    not_(fig, i_ob + 1, da.o[i_ob], "bullish OB (sweep + displacement)", renk=MAVI, ok=False, boyut=10, xanchor="left", ay=-14, row=1, col=1)
    not_(fig, i_rt, da.l[i_rt], "<b>MB retest</b>: fitil OB'ye girdi, gövde OB low'unun<br>altına KAPANMADI → devam; kapansaydı breaker olurdu", renk=MAVI, ax=90, ay=-95, row=1, col=1)
    not_(fig, i_ob + 1, da.l[i_ob] - 0.25, "OB fitil low — geçilirse breaker", renk=BORDO, ok=False, boyut=9, xanchor="left", row=1, col=1)
    # (b)
    i_H = int(db.index[db.lab == "H"][0]); i_L = int(db.index[db.lab == "L"][0]); i_LH = int(db.index[db.lab.str.startswith("LH")][0])
    i_k = int(db.index[db.lab.str.startswith("d2")][0]); i_rt = int(db.index[db.lab.str.startswith("MB retest")][0]); n = len(db)
    H = db.h[i_H - 1:i_H + 2].max(); L = db.l[i_L - 1:i_L + 2].min()
    yatay(fig, H, i_H, i_LH + 1, renk=ALTIN, row=2, col=1); not_(fig, i_H, H + 0.25, "H — süpürülmedi", renk=ALTIN, ok=False, boyut=10, row=2, col=1)
    yatay(fig, L, i_L, i_k + 1, renk=BORDO, dash="dash", w=1.6, row=2, col=1); not_(fig, i_L, L - 0.25, "L — kırılan dip", renk=BORDO, ok=False, boyut=10, row=2, col=1)
    kutu(fig, i_LH, n - 1, db.o[i_LH], db.c[i_LH], MAVI, a=0.24, row=2, col=1)
    not_(fig, i_LH, db.h[i_LH], "<b>LH</b>: yeni high yapamadı (sweep yok)<br>son yeşil mum = <b>mitigation block</b>", renk=MAVI, ax=-90, ay=-45, row=2, col=1)
    not_(fig, i_k, db.c[i_k], "L gövdeyle kırıldı", renk=BORDO, ax=60, ay=30, row=2, col=1)
    not_(fig, i_rt, db.h[i_rt], "MB retest → direnç, short;<br>SL MB üstü", renk=MAVI, ax=60, ay=-45, row=2, col=1)
    lejant(fig, "OB / mitigation block", MAVI)
    duzen(fig, "Şekil 19 — Mitigation block: iki tanım alt alta (şematik örnek)",
          "Aynı seviye, zıt işlem fikri: breaker'da OB kırılmıştır (yön döner); mitigation'da OB tutar (yön aynı) — V2'de fark sweep'in olmamasıdır", h=860)
    fig.update_xaxes(title_text="mum sırası", row=2, col=1)
    kaydet(fig, "19_mitigation_block")


# =====================================================================================
# 15 — Power of Three (AMD) — bir günün saatlik mumları + günlük mum
# =====================================================================================
def g15_po3():
    s = Seri(15, baslangic=100.0, birim=0.06)
    s.yatay(3, 100.0, genlik=1.0)                    # 00-02 Asya sonu / birikim (A)
    s.bacak(99.75, 1, gurultu=0.3); s.bacak(99.42, 1, gurultu=0.3, lab="Judas dibi (Londra KZ, 04:00)")   # 03-04 manipulation (Londra KZ 02–05 içinde)
    s.mum(s.son, s.son + 0.6, s.son - 0.05, s.son + 0.55, "geri kazanım (00:00 open üstü)")           # 05
    s.bacak(100.7, 2); s.bacak(101.65, 2, lab="günün high'ı (NY AM KZ)"); s.bacak(101.25, 4, gurultu=0.4); s.bacak(101.45, 10, gurultu=0.3)
    df = s.df()
    n = len(df); assert n == 24  # 24 saat
    saat = [f"{h:02d}:00" for h in range(n)]
    # okunabilirlik: saatlik mumlar üstte, günün tek mumu altta (tek sütun)
    fig = make_subplots(rows=2, cols=1, row_heights=[0.70, 0.30], vertical_spacing=0.10,
                        subplot_titles=("saatlik mumlar (NY saati)", "günlük mum"))
    fig.add_trace(mum_izi(df, x=saat, ad="saatlik mum"), row=1, col=1)
    fig.add_trace(go.Candlestick(x=["gün"], open=[df.o[0]], high=[df.h.max()], low=[df.l.min()], close=[df.c[n - 1]],
                                 increasing_line_color=TEAL, increasing_fillcolor=TEAL, decreasing_line_color=BORDO, decreasing_fillcolor=BORDO,
                                 name="günlük mum", showlegend=False, whiskerwidth=0.6), row=2, col=1)
    o0 = df.o[0]
    yatay(fig, o0, saat[0], saat[-1], renk=MUREKKEP, dash="dash", w=1.5, row=1, col=1)
    not_(fig, saat[-1], o0, "00:00 NY open (true day open)", renk=MUREKKEP, ok=False, boyut=10, xanchor="right", ay=12, row=1, col=1)
    # A box
    kutu(fig, saat[0], saat[2], df.l[:3].min() - 0.05, df.h[:3].max() + 0.05, GRI, a=0.12, dash="dot", row=1, col=1)
    not_(fig, saat[0], df.h[:3].max() + 0.25, "<b>A</b> — Accumulation (Asya sonu, dar aralık)", renk=GRI, ok=False, boyut=11, xanchor="left", row=1, col=1)
    i_j = int(df.index[df.lab.str.startswith("Judas")][0])
    fig.add_annotation(x=saat[i_j], y=df.l[i_j], ax=saat[2], ay=o0, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowwidth=2.5, arrowcolor=BORDO, text="")
    not_(fig, saat[i_j], df.l[i_j] - 0.15, "<b>M</b> — Manipulation: <b>Judas swing</b><br>açılışın ALTINA, SSL süpürülür (bullish gün)", renk=BORDO, ok=False, boyut=11, yanchor="top", row=1, col=1)
    i_h = int(df.index[df.lab.str.startswith("günün")][0])
    fig.add_annotation(x=saat[i_h], y=df.h[i_h], ax=saat[i_j + 1], ay=df.c[i_j + 1], xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowwidth=2.5, arrowcolor=TEAL, text="")
    not_(fig, saat[7], 101.55, "<b>D</b> — Distribution: gerçek yön,<br>genişleme, kapanış tepeye yakın", renk=TEAL, ok=False, boyut=11, xanchor="left", row=1, col=1)
    fig.add_vrect(x0=saat[2], x1=saat[5], fillcolor=rgba(ALTIN, 0.10), line_width=0, layer="below", row=1, col=1,
                  annotation_text="Londra KZ 02–05", annotation_position="top left", annotation_font=dict(size=9, color=ALTIN))
    fig.add_vrect(x0=saat[7], x1=saat[10], fillcolor=rgba(ALTIN, 0.10), line_width=0, layer="below", row=1, col=1,
                  annotation_text="NY AM KZ 07–10", annotation_position="top left", annotation_font=dict(size=9, color=ALTIN))
    not_(fig, "gün", df.o[0], "open dibe yakın", renk=GRI, ok=False, boyut=9, xanchor="left", ax=6, row=2, col=1)
    not_(fig, "gün", df.l.min(), "alt fitil = Judas", renk=BORDO, ok=False, boyut=9, ay=12, row=2, col=1)
    not_(fig, "gün", df.c[n - 1], "kapanış tepeye yakın", renk=TEAL, ok=False, boyut=9, xanchor="left", ax=6, row=2, col=1)
    duzen(fig, "Şekil 26 — Power of Three (AMD) ve Judas swing: bullish gün (şematik örnek)",
          "Referans 00:00 NY açılışı; A birikim → M açılışın yanlış tarafına yem → D genişleme; altta günün tek mumu", x_baslik="NY saati", h=880)
    fig.update_xaxes(tickangle=-45, row=1, col=1); fig.update_xaxes(title_text="", row=2, col=1)
    kaydet(fig, "26_power_of_three_amd")


# =====================================================================================
# 16 — Kill zone'lar: bir günün 15 dk mumları, gölgeli bantlar, NY + TSİ ekseni
# =====================================================================================
def g16_kill_zones():
    # 20:00 (önceki gün) → 16:00 NY, 15 dk = 80 mum
    zaman = pd.date_range("2025-07-15 20:00", periods=80, freq="15min")
    s = Seri(16, baslangic=100.0, birim=0.05)
    s.yatay(16, 100.0, genlik=1.0)                                  # Asya 20-00
    s.yatay(8, 100.05, genlik=0.8)                                  # 00-02
    s.bacak(99.55, 6, gurultu=0.5, lab="Londra Judas / günün low'u")  # 02:00-03:30
    s.bacak(100.6, 6)                                               # 03:30-05:00
    s.yatay(8, 100.55, genlik=0.8)                                  # 05-07
    s.bacak(101.4, 8, gurultu=0.6, lab="NY AM devam")               # 07-09
    s.bacak(101.9, 6, lab="günün high'ı (10:30 civarı)")             # 09-10:30
    s.bacak(101.3, 6)                                               # 10:30-12 Londra kapanış geri çekilme
    s.yatay(6, 101.35, genlik=0.7)                                  # 12-13:30 öğle
    s.bacak(101.75, 10, gurultu=0.6)                                # 13:30-16
    df = s.df()
    assert len(df) == 80
    fig = go.Figure(mum_izi(df, x=zaman, ad="15 dk mum"))
    def z(h, m=0):
        t = pd.Timestamp("2025-07-16") + pd.Timedelta(hours=h, minutes=m)
        return t if h >= 0 else pd.Timestamp("2025-07-15") + pd.Timedelta(hours=24 + h, minutes=m)
    bant = [(-4, 0, "Asya KZ 20:00–00:00", GRI, 0.10), (2, 5, "Londra KZ 02–05", ALTIN, 0.14), (7, 10, "NY AM KZ 07–10 (ICT)", TEAL, 0.14),
            (10, 12, "Londra kapanış 10–12", MAVI, 0.10), (12, 13.5, "NY öğle 12–13:30 (kaçın)", BORDO, 0.10), (13.5, 16, "NY PM 13:30–16", MOR, 0.10)]
    for h0, h1, ad, renk, a in bant:
        fig.add_vrect(x0=z(int(h0), int((h0 % 1) * 60)), x1=z(int(h1), int((h1 % 1) * 60)), fillcolor=rgba(renk, a), line_width=0, layer="below",
                      annotation_text=ad, annotation_position="top left", annotation_font=dict(size=9, color=renk))
        lejant(fig, ad, renk, a=a + 0.15)
    for h0 in (3, 10, 14):
        fig.add_vrect(x0=z(h0), x1=z(h0 + 1), fillcolor=rgba(ALTIN, 0.22), line_width=0, layer="below")
        not_(fig, z(h0, 30), 99.35, "Silver Bullet", renk=ALTIN, ok=False, boyut=9)
    lejant(fig, "Silver Bullet 03–04 / 10–11 / 14–15", ALTIN, a=0.4)
    for h, ad in ((0, "00:00 true day open"), (8.5, "08:30 veri"), (9.5, "09:30 NYSE açılış")):
        fig.add_vline(x=z(int(h), int((h % 1) * 60)), line=dict(color=MUREKKEP, width=1, dash="dot"))
        not_(fig, z(int(h), int((h % 1) * 60)), 102.35, ad, renk=MUREKKEP, ok=False, boyut=9, ay=0)
    # eksen: NY + TSİ (yaz: +7)
    tv = [z(h) for h in range(-4, 17, 2)]
    tt = [f"{(h % 24):02d}:00 NY<br>{((h + 7) % 24):02d}:00 TSİ" for h in range(-4, 17, 2)]
    fig.update_xaxes(tickvals=tv, ticktext=tt, tickfont=dict(size=10))
    i_l = int(df.index[df.lab.str.startswith("Londra")][0]); i_h = int(df.index[df.lab.str.startswith("günün high")][0])
    not_(fig, zaman[i_l], df.l[i_l], "günün low'u Londra KZ'de (Judas)", renk=ALTIN, ax=-150, ay=-110)
    not_(fig, zaman[i_h], df.h[i_h], "günün high'ı NY AM / SB penceresinde", renk=TEAL, ax=-60, ay=-40)
    fig.update_yaxes(range=[99.2, 102.6])
    duzen(fig, "Şekil 28 — Kill zone'lar ve günlük profil: bir günün 15 dk mumları (şematik örnek)",
          "NY yerel saat (yaz: TSİ = NY + 7; kış: NY + 8). Asya birikimi → Londra Judas → NY AM genişleme → Londra kapanış geri çekilme → öğle → PM", x_baslik="saat (NY / TSİ, yaz saati)")
    kaydet(fig, "28_kill_zones_gunluk_profil")


# =====================================================================================
# 16b — Haftalık profil: Classic Tuesday Low (bullish hafta) ve Seek & Destroy Friday
# =====================================================================================
def g27_haftalik_profil():
    gun = ["Pzt", "Sal", "Çar", "Per", "Cum"]
    # (a) Classic Tuesday Low — bullish hafta
    a = pd.DataFrame(dict(
        o=[100.00, 99.60, 99.90, 101.00, 101.90], h=[100.30, 100.00, 101.10, 102.15, 102.05],
        l=[99.30, 98.62, 99.70, 100.80, 101.20], c=[99.60, 99.90, 101.00, 101.90, 101.55],
        lab=["Pzt: haftalık açılış; açılışın ALTINA manipülasyon", "Sal: haftalık low — HTF discount / PD array'e dokunuş, uzun alt fitil",
             "Çar: genişleme", "Per: PWH (DOL) süpürüldü, haftalık high", "Cum: geri çekilme / konsolidasyon"]))
    # (b) Seek & Destroy Friday — Pzt–Per yatay, Cuma iki yönlü stop avı
    b = pd.DataFrame(dict(
        o=[100.00, 100.10, 99.95, 100.05, 100.10], h=[100.45, 100.50, 100.40, 100.48, 100.95],
        l=[99.60, 99.55, 99.62, 99.58, 99.10], c=[100.10, 99.95, 100.05, 100.10, 100.02],
        lab=["Pzt: dar aralık", "Sal: dar aralık", "Çar: dar aralık", "Per: dar aralık (haftalık ekstrem hâlâ yok)",
             "Cum: önce aralık üstü BSL, sonra aralık altı SSL süpürüldü; kapanış ortada"]))
    # okunabilirlik: paneller alt alta (tek sütun)
    fig = make_subplots(rows=2, cols=1, subplot_titles=("(a) Classic Tuesday Low (bullish hafta)", "(b) Seek & Destroy Friday"),
                        vertical_spacing=0.09)
    for an in fig.layout.annotations:
        an.font.size = 12
    fig.add_trace(mum_izi(a, ad="günlük mum"), row=1, col=1)
    fig.add_trace(mum_izi(b, ad="günlük mum (b)", gorunur=False), row=2, col=1)
    # (a) haftalık açılış, HTF discount kutusu, PWH, genişleme oku
    o0 = a.o[0]
    yatay(fig, o0, 0, 4, renk=MUREKKEP, dash="dash", w=1.5, row=1, col=1)
    not_(fig, 4.5, o0, "Pzt open (haftalık açılış)", renk=MUREKKEP, ok=False, boyut=9, xanchor="right", ay=12, row=1, col=1)
    kutu(fig, -0.5, 4.5, 98.55, 98.95, TEAL, a=0.18, dash="dot", row=1, col=1)
    not_(fig, 0, 98.75, "HTF discount / PD array (günlük FVG–OB)", renk=TEAL, ok=False, boyut=9, xanchor="left", row=1, col=1)
    yatay(fig, 102.0, 0, 4, renk=ALTIN, w=1.5, row=1, col=1)
    not_(fig, 0, 102.0, "önceki hafta high (PWH) = DOL", renk=ALTIN, ok=False, boyut=9, xanchor="left", ay=-11, row=1, col=1)
    daire(fig, 1, a.l[1] + 0.08, r_x=0.35, r_y=0.16, row=1, col=1)
    not_(fig, 1, a.l[1] - 0.05, "<b>haftalık low = Salı</b><br>(Pzt manipülasyonundan sonra,<br>HTF discount'a dokunarak)", renk=TEAL, ok=False, boyut=9, yanchor="top", row=1, col=1)
    fig.add_annotation(x=3, y=a.h[3] - 0.05, ax=1, ay=a.l[1] + 0.3, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowwidth=2.5, arrowcolor=TEAL, text="", row=1, col=1)
    not_(fig, 2, 100.35, "Salı–Perşembe:<br>haftalık genişleme", renk=TEAL, ok=False, boyut=10, xanchor="right", row=1, col=1)
    not_(fig, 3, a.h[3] + 0.08, "PWH süpürüldü → haftalık high", renk=ALTIN, ok=False, boyut=9, ay=-6, row=1, col=1)
    not_(fig, 0, a.l[0] - 0.05, "Pzt: açılış altına<br>manipülasyon (Judas)", renk=BORDO, ok=False, boyut=9, yanchor="top", row=1, col=1)
    # (b) aralık kutusu, iki yönlü sweep
    rh, rl = b.h[:4].max(), b.l[:4].min()
    kutu(fig, -0.5, 3.5, rl, rh, GRI, a=0.10, dash="dot", row=2, col=1)
    yatay(fig, rh, 0, 4, renk=ALTIN, w=1.4, row=2, col=1); yatay(fig, rl, 0, 4, renk=ALTIN, w=1.4, row=2, col=1)
    not_(fig, 0, rh, "Pzt–Per aralık high — BSL", renk=ALTIN, ok=False, boyut=9, xanchor="left", ay=-11, row=2, col=1)
    not_(fig, 0, rl, "Pzt–Per aralık low — SSL", renk=ALTIN, ok=False, boyut=9, xanchor="left", ay=11, row=2, col=1)
    daire(fig, 4, b.h[4] - 0.08, r_x=0.35, r_y=0.14, row=2, col=1); daire(fig, 4, b.l[4] + 0.08, r_x=0.35, r_y=0.14, row=2, col=1)
    not_(fig, 4, b.h[4] + 0.05, "<b>Cuma</b>: her iki taraf süpürüldü,<br>kapanış aralığın içinde", renk=BORDO, ok=False, boyut=9, yanchor="bottom", row=2, col=1)
    not_(fig, 1, rl - 0.35, "haftalık ekstremler Pzt–Salı'da oluşmadı,<br>Salı–Per genişleme yok → 'seek & destroy' adayı;<br>haber/faiz haftası veya sıkışma", renk=GRI, ok=False, boyut=9, xanchor="left", row=2, col=1)
    lejant(fig, "HTF discount / PD array", TEAL); lejant(fig, "Pzt–Per aralığı", GRI, a=0.12); lejant_cizgi(fig, "likidite (PWH / aralık H-L)", ALTIN, "solid"); lejant_cizgi(fig, "haftalık açılış", MUREKKEP)
    fig.update_yaxes(range=[98.2, 102.6], row=1, col=1); fig.update_yaxes(range=[98.6, 101.4], row=2, col=1)
    for r in (1, 2):
        fig.update_xaxes(tickvals=list(range(5)), ticktext=gun, range=[-0.6, 4.6], row=r, col=1)
    duzen(fig, "Şekil 27 — Haftalık profil: Classic Tuesday Low ve Seek & Destroy Friday (şematik örnek)",
          "Günlük mumlar; referans Pzt açılışı ve önceki hafta H/L. Haftalık ekstrem çoğunlukla Pzt–Salı; Salı–Perşembe azami genişleme; Cuma stop avı varyantı altta", x_baslik="gün", h=860)
    fig.update_xaxes(title_text="gün", row=2, col=1)
    kaydet(fig, "27_haftalik_profil")


# =====================================================================================
# 17-19 + 23 — Tam giriş modeli (HTF → sweep+MSS → giriş) ve MTF paneli
# =====================================================================================
def _htf():
    s = Seri(171, birim=0.25)
    s.bacak(96.0, 5); s.mum(s.son, s.son + 0.1, 94.6, 95.4, "H4 sweep low"); s.bacak(99.5, 4); s.bacak(97.5, 3); s.bacak(103.0, 5, lab="H4 BOS")
    s.bacak(100.0, 3, lab="dealing range low (100.0)")
    s.mum(100.0, 100.9, 99.9, 100.8, "d1"); s.mum(100.8, 103.6, 100.7, 103.5, "H4 displacement (FVG mumu)"); s.mum(103.5, 104.4, 103.0, 104.3, "d3")
    s.bacak(110.0, 5, lab="dealing range high (110.0)"); s.bacak(107.5, 3); s.bacak(103.4, 4, lab="şimdi: discount")
    return s.df()


def g17_giris_1_htf():
    df = _htf(); n = len(df)
    fig = go.Figure(mum_izi(df, ad="H4 mum"))
    i_L = int(df.index[df.lab.str.startswith("dealing range low")][0]); i_H = int(df.index[df.lab.str.startswith("dealing range high")][0])
    L = df.l[i_L - 1:i_L + 2].min(); H = df.h[i_H - 1:i_H + 2].max(); eq = (L + H) / 2
    kutu(fig, i_L, n + 3, eq, H, BORDO, a=0.07, cizgi=0); kutu(fig, i_L, n + 3, L, eq, TEAL, a=0.07, cizgi=0)
    yatay(fig, eq, i_L, n + 3, renk=GRI, dash="dash"); not_(fig, n + 3, eq, f"EQ {eq:.1f}", renk=GRI, ok=False, boyut=10, xanchor="left")
    not_(fig, i_L + 1, H - 0.5, "premium", renk=BORDO, ok=False, boyut=11, xanchor="left"); not_(fig, i_L + 1, L + 0.5, "discount ← fiyat burada", renk=TEAL, ok=False, boyut=11, xanchor="left")
    i_b = int(df.index[df.lab.str.startswith("H4 BOS")][0])
    sh_, _ = swingler(df.iloc[:i_b], 2); i_ref = sh_[-1]; ref = df.h[i_ref]
    i_kir = next(i for i in range(i_ref + 1, i_b + 1) if df.c[i] > ref)
    yatay(fig, ref, i_ref, i_kir, renk=TEAL, dash="solid"); not_(fig, i_kir, df.c[i_kir], "H4 BOS (gövde kapanışı) → <b>bias bullish</b>", renk=TEAL, ax=-80, ay=-45)
    yatay(fig, H, i_H, n + 3, renk=ALTIN, w=1.6); not_(fig, i_H, H + 0.4, "BSL / dealing range high", renk=ALTIN, ok=False, boyut=10)
    fig.add_annotation(x=n - 1, y=df.c[n - 1] + 0.3, ax=n - 1, ay=H - 0.2, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowwidth=2, arrowcolor=ALTIN, text="")
    not_(fig, n + 0.3, (df.c[n - 1] + H) / 2, "<b>DOL</b>: süpürülmemiş BSL yukarıda<br>→ bias ile uyumlu, 'A sınıfı' bağlam", renk=ALTIN, ok=False, boyut=10, xanchor="left")
    # HTF PD array (FVG) discount içinde
    fv = [f for f in fvg_bul(df) if f["tip"] == "BISI" and i_L <= f["i"] < i_H]
    if fv:
        f = fv[0]; kutu(fig, f["i"], n + 3, f["alt"], f["ust"], MOR, a=0.18); not_(fig, f["i"] + 3, f["ust"], "HTF FVG (PD array) — LTF girişi buradan aranır", renk=MOR, ok=False, boyut=10, xanchor="left", ay=-12)
    lejant(fig, "premium", BORDO, a=0.1); lejant(fig, "discount", TEAL, a=0.1); lejant(fig, "HTF FVG", MOR)
    duzen(fig, "Şekil 30 — Giriş modeli, aşama 1 (H4): bias + dealing range + premium/discount + DOL (şematik örnek)",
          "Çıktı: 'bugün alıcıyım'; fiyat discount'ta ve DOL yukarıda → LTF'de SSL sweep + MSS aranacak", x_baslik="H4 mum sırası")
    kaydet(fig, "30_giris_modeli_1_htf_bias")


def _ltf():
    """15m/5m: discount içinde sweep → displacement → MSS + FVG + OB, sonra OTE'ye dönüş ve hedef."""
    s = Seri(181, baslangic=103.1, birim=0.06)
    s.bacak(102.9, 3, gurultu=0.6); s.bacak(103.35, 3, lab="LTF governing swing high / ITH (MSS referansı) ≈103.35–103.39"); s.bacak(102.75, 3, gurultu=0.5)
    s.mum(s.son, s.son + 0.05, 102.38, 102.6, "EQL/Asya low ≈102.4"); s.bacak(103.0, 3); s.bacak(102.7, 3, gurultu=0.5)
    s.mum(102.7, 102.72, 102.42, 102.55, "eşit dip #2")
    s.bacak(102.85, 2, gurultu=0.4); s.bacak(102.68, 2, gurultu=0.4)
    s.mum(102.66, 102.7, 102.00, 102.30, "SWEEP: EQL altına fitil 102.00, gövde içeride — OB mumu (son kırmızı)")
    s.mum(102.30, 102.44, 102.28, 102.42, "displacement 1")
    s.mum(102.42, 103.02, 102.40, 103.00, "displacement 2 (FVG mumu)")
    s.mum(103.00, 103.55, 102.70, 103.50, "displacement 3: 103.35 üstü gövde kapanışı → MSS")
    s.bacak(103.4, 2, gurultu=0.4); s.bacak(103.05, 2); s.bacak(102.75, 2, gurultu=0.4)
    s.mum(102.75, 102.78, 102.42, 102.6, "OTE ∩ FVG'ye dönüş → giriş dolumu")
    s.bacak(102.9, 2); s.bacak(103.5, 3); s.bacak(104.05, 3, lab="TP1"); s.bacak(103.5, 2); s.bacak(104.65, 4, lab="TP2 / BSL")
    return s.df()


def _ltf_meta(df):
    m = {}
    m["i_sw"] = int(df.index[df.lab.str.startswith("SWEEP")][0]); m["i_ref"] = int(df.index[df.lab.str.startswith("LTF governing swing high")][0])
    m["i_mss"] = m["i_sw"] + 3; m["i_g"] = int(df.index[df.lab.str.startswith("OTE")][0]); m["i_eq1"] = int(df.index[df.lab.str.startswith("EQL")][0])
    m["i_eq2"] = int(df.index[df.lab.str.startswith("eşit dip")][0]); m["i_t1"] = int(df.index[df.lab == "TP1"][0]); m["i_t2"] = int(df.index[df.lab.str.startswith("TP2")][0])
    m["L"] = df.l[m["i_sw"]]; m["H"] = df.h[m["i_mss"]]; m["ref"] = df.h[m["i_ref"] - 1:m["i_ref"] + 2].max()
    m["eql"] = (df.l[m["i_eq1"]] + df.l[m["i_eq2"]]) / 2
    fv = [f for f in fvg_bul(df) if f["tip"] == "BISI" and m["i_sw"] <= f["i"] <= m["i_sw"] + 2]
    m["fvg"] = fv[0]
    m["ob"] = (df.c[m["i_sw"]], df.o[m["i_sw"]])
    return m


def g18_giris_2_sweep_mss():
    df = _ltf(); m = _ltf_meta(df); n = m["i_mss"] + 2
    d = df.iloc[:n].reset_index(drop=True)
    fig = go.Figure(mum_izi(d, ad="15m mum"))
    yatay(fig, m["eql"], m["i_eq1"], m["i_sw"] + 1, renk=ALTIN, w=1.6); not_(fig, m["i_eq1"], m["eql"] - 0.08, "EQL / Asya low — SSL", renk=ALTIN, ok=False, boyut=10)
    daire(fig, m["i_sw"], d.l[m["i_sw"]] + 0.08, r_y=0.12)
    not_(fig, m["i_sw"], d.l[m["i_sw"]], "① <b>sweep</b>: fitil 102.00, gövde 102.30<br>(bias bullish → SSL sweep aradık)", renk=ALTIN, ax=-110, ay=40)
    yatay(fig, m["ref"], m["i_ref"], m["i_mss"] + 1, renk=BORDO, dash="dash", w=1.6)
    not_(fig, m["i_mss"], d.c[m["i_mss"]], f"③ <b>MSS</b>: 15m governing swing high (ITH, fitil {m['ref']:.2f})<br>gövdeyle kırıldı (displacement 3 mum, FVG bıraktı)", renk=TEAL, ax=-80, ay=-50)
    not_(fig, m["i_ref"], m["ref"] + 0.04, "ITH (iki yanında daha alçak STH'ler)", renk=BORDO, ok=False, boyut=9)
    f = m["fvg"]; kutu(fig, f["i"], n - 1, f["alt"], f["ust"], MOR, a=0.2); not_(fig, f["i"] + 2, f["ust"], f"② FVG {f['alt']:.2f}–{f['ust']:.2f}", renk=MOR, ok=False, boyut=10, xanchor="left", ay=-12)
    kutu(fig, m["i_sw"], n - 1, m["ob"][0], m["ob"][1], MAVI, a=0.24); not_(fig, m["i_sw"] + 2, m["ob"][0], f"OB {m['ob'][0]:.2f}–{m['ob'][1]:.2f} (sweep mumu = son kırmızı)", renk=MAVI, ok=False, boyut=10, xanchor="left", ay=12)
    not_(fig, 2, 103.65, "kill zone içinde miyiz? ✓ (Londra / NY AM)", renk=GRI, ok=False, boyut=10, xanchor="left")
    lejant(fig, "FVG", MOR); lejant(fig, "OB", MAVI); lejant_cizgi(fig, "SSL (EQL)", ALTIN, "solid"); lejant_cizgi(fig, "MSS seviyesi", BORDO)
    duzen(fig, "Şekil 31 — Giriş modeli, aşama 2 (15m): sweep → displacement → MSS, FVG ve OB işaretlenir (şematik örnek)",
          "Henüz giriş yok: sweep tek başına giriş değildir; MSS sonrası geri çekilme beklenir", x_baslik="15m mum sırası")
    kaydet(fig, "31_giris_modeli_2_sweep_mss")


def g19_giris_3_giris_sl_tp():
    df = _ltf(); m = _ltf_meta(df); n = len(df)
    fig = go.Figure(mum_izi(df, ad="15m/5m mum"))
    L, H = m["L"], m["H"]; r = H - L
    sev = fib_ciz(fig, L, H, m["i_sw"], n + 4, yon="bull", etiket_x=n + 4.2, kisa=True)
    f = m["fvg"]; kutu(fig, f["i"], n - 1, f["alt"], f["ust"], MOR, a=0.2)
    kutu(fig, m["i_sw"], n - 1, m["ob"][0], m["ob"][1], MAVI, a=0.22)
    giris = (f["alt"] + f["ust"]) / 2
    sl = L - 0.10; tp1 = sev[-0.27]; tp2 = sev[-0.62]
    i_g = m["i_g"]
    # kutular
    kutu(fig, i_g, m["i_t2"] + 1, sl, giris, BORDO, a=0.22, cizgi=0)
    kutu(fig, i_g, m["i_t1"] + 1, giris, tp1, TEAL, a=0.22, cizgi=0)
    kutu(fig, m["i_t1"] + 1, m["i_t2"] + 1, giris, tp2, TEAL, a=0.14, cizgi=0)
    yatay(fig, giris, i_g, m["i_t2"] + 1, renk=MUREKKEP, dash="solid", w=1.4); yatay(fig, sl, i_g, m["i_t2"] + 1, renk=BORDO, dash="solid", w=1.4)
    yatay(fig, tp1, i_g, m["i_t2"] + 1, renk=TEAL, dash="solid", w=1.2); yatay(fig, tp2, i_g, m["i_t2"] + 1, renk=TEAL, dash="solid", w=1.4)
    R = giris - sl
    not_(fig, i_g, giris, f"<b>GİRİŞ</b> limit {giris:.2f} = FVG CE ∩ OTE (0.62–0.79)<br>OB open {m['ob'][1]:.2f} yedek", renk=MUREKKEP, ax=-170, ay=95)
    not_(fig, i_g + 2, sl, f"<b>SL</b> {sl:.2f} — sweep fitili 102.00 + 0.10 tampon (1R = {R:.2f})", renk=BORDO, ok=False, boyut=10, xanchor="left", ay=12)
    not_(fig, m["i_t1"], tp1, f"<b>TP1</b> {tp1:.2f} = fib −0.27 → {(tp1-giris)/R:.1f}R (%50 kapat, SL→BE)", renk=TEAL, ax=-120, ay=-30)
    not_(fig, m["i_t2"], tp2, f"<b>TP2</b> {tp2:.2f} = fib −0.62 ≈ karşı likidite (BSL) → {(tp2-giris)/R:.1f}R", renk=TEAL, ax=-140, ay=-35)
    daire(fig, m["i_sw"], L + 0.08, r_y=0.12); not_(fig, m["i_sw"] - 1, L - 0.02, "sweep low = fib 1.0", renk=ALTIN, ok=False, boyut=9, yanchor="top", xanchor="right")
    not_(fig, m["i_mss"], H + 0.05, "MSS high = fib 0", renk=ALTIN, ok=False, boyut=9)
    lejant(fig, "FVG", MOR); lejant(fig, "OB", MAVI); lejant(fig, "OTE bandı", ALTIN, a=0.16); lejant(fig, "kâr kutusu", TEAL); lejant(fig, "risk kutusu", BORDO)
    fig.update_yaxes(range=[L - 0.35, tp2 + 0.4])
    duzen(fig, "Şekil 32 — Giriş modeli, aşama 3: OTE ∩ FVG'ye limit, SL sweep ötesi, TP1/TP2 ve R:R kutuları (şematik örnek)",
          "Fib: sweep low (1.0) → MSS high (0). Giriş FVG CE'sinde; SL yapıdan, pozisyon büyüklüğü SL'den türetilir", x_baslik="15m/5m mum sırası")
    kaydet(fig, "32_giris_modeli_3_giris_sl_tp")


def g46_mtf_panel():
    dh = _htf(); dl = _ltf(); m = _ltf_meta(dl)
    n2 = m["i_mss"] + 2
    d2 = dl.iloc[:n2].reset_index(drop=True)
    # okunabilirlik: üç zaman dilimi alt alta (tek sütun) — okuma sırası H4 → 15m → 5m/1m
    fig = make_subplots(rows=3, cols=1, subplot_titles=("H4 — bias, dealing range, DOL", "15m — sweep + MSS, FVG/OB", "5m/1m — OTE/FVG'ye dönüş, giriş / SL / TP"), vertical_spacing=0.07)
    fig.add_trace(mum_izi(dh, ad="H4"), row=1, col=1); fig.add_trace(mum_izi(d2, ad="15m"), row=2, col=1); fig.add_trace(mum_izi(dl, ad="5m/1m"), row=3, col=1)
    # H4
    nh = len(dh); i_L = int(dh.index[dh.lab.str.startswith("dealing range low")][0]); i_H = int(dh.index[dh.lab.str.startswith("dealing range high")][0])
    L, H = dh.l[i_L - 1:i_L + 2].min(), dh.h[i_H - 1:i_H + 2].max(); eq = (L + H) / 2
    kutu(fig, i_L, nh, eq, H, BORDO, a=0.07, cizgi=0, row=1, col=1); kutu(fig, i_L, nh, L, eq, TEAL, a=0.07, cizgi=0, row=1, col=1)
    yatay(fig, eq, i_L, nh, renk=GRI, dash="dash", row=1, col=1); yatay(fig, H, i_H, nh, renk=ALTIN, w=1.5, row=1, col=1)
    not_(fig, nh - 1, H, "DOL: BSL", renk=ALTIN, ok=False, boyut=10, xanchor="right", ay=-12, row=1, col=1)
    not_(fig, nh - 1, dh.c[nh - 1], "discount ✓ bias bullish ✓", renk=TEAL, ax=-60, ay=40, row=1, col=1)
    # 15m
    yatay(fig, m["eql"], m["i_eq1"], m["i_sw"] + 1, renk=ALTIN, w=1.5, row=2, col=1); daire(fig, m["i_sw"], d2.l[m["i_sw"]] + 0.08, r_y=0.12, row=2, col=1)
    not_(fig, m["i_sw"], d2.l[m["i_sw"]], "sweep", renk=ALTIN, ax=-40, ay=35, row=2, col=1)
    yatay(fig, m["ref"], m["i_ref"], m["i_mss"] + 1, renk=BORDO, dash="dash", row=2, col=1); not_(fig, m["i_mss"], d2.c[m["i_mss"]], "MSS", renk=TEAL, ax=-40, ay=-35, row=2, col=1)
    f = m["fvg"]; kutu(fig, f["i"], n2 - 1, f["alt"], f["ust"], MOR, a=0.2, row=2, col=1); kutu(fig, m["i_sw"], n2 - 1, m["ob"][0], m["ob"][1], MAVI, a=0.24, row=2, col=1)
    # 5m
    nl = len(dl); giris = (f["alt"] + f["ust"]) / 2; sl = m["L"] - 0.10; r = m["H"] - m["L"]; tp1 = m["H"] + 0.27 * r; tp2 = m["H"] + 0.62 * r
    kutu(fig, f["i"], nl - 1, f["alt"], f["ust"], MOR, a=0.2, row=3, col=1); kutu(fig, m["i_sw"], nl - 1, m["ob"][0], m["ob"][1], MAVI, a=0.22, row=3, col=1)
    y62, y79 = m["H"] - 0.62 * r, m["H"] - 0.79 * r; kutu(fig, m["i_sw"], nl - 1, y79, y62, ALTIN, a=0.16, cizgi=0, row=3, col=1)
    kutu(fig, m["i_g"], nl - 1, sl, giris, BORDO, a=0.2, cizgi=0, row=3, col=1); kutu(fig, m["i_g"], nl - 1, giris, tp2, TEAL, a=0.16, cizgi=0, row=3, col=1)
    yatay(fig, tp1, m["i_g"], nl - 1, renk=TEAL, dash="dot", row=3, col=1)
    not_(fig, m["i_g"], giris, "giriş", renk=MUREKKEP, ax=-40, ay=30, row=3, col=1); not_(fig, m["i_g"] + 1, sl, "SL", renk=BORDO, ok=False, boyut=10, xanchor="left", ay=10, row=3, col=1)
    not_(fig, m["i_t1"], tp1, "TP1", renk=TEAL, ok=False, boyut=10, ay=-10, row=3, col=1); not_(fig, m["i_t2"], tp2, "TP2", renk=TEAL, ok=False, boyut=10, ay=-10, row=3, col=1)
    lejant(fig, "FVG", MOR); lejant(fig, "OB", MAVI); lejant(fig, "OTE", ALTIN, a=0.16); lejant(fig, "premium/discount", GRI, a=0.1)
    duzen(fig, "Şekil 46 — Çoklu zaman dilimi akışı: H4 → 15m → 5m/1m aynı işlemin üç katmanı (şematik örnek)",
          "Kural: LTF'ye ancak HTF olay olduysa inilir; swing tier'ı yapı grafiğinde, kırılım kalitesi icra grafiğinde okunur", x_baslik="",
          h=1200, legend_y=-0.07)
    kaydet(fig, "46_mtf_panel")


# =====================================================================================
# 20 — Silver Bullet (NY AM 10:00–11:00), 5 dk
# =====================================================================================
def g36_silver_bullet():
    s = Seri(20, baslangic=100.2, birim=0.05)
    s.bacak(100.6, 3, gurultu=0.6); s.mum(s.son, 100.82, s.son - 0.05, 100.7, "pencere öncesi high 100.82 (BSL)")  # 09:45
    s.bacak(100.45, 3, gurultu=0.6)                                # → 10:00
    s.bacak(100.7, 2, gurultu=0.4)                                 # 10:00-10:05
    s.mum(s.son, 100.97, s.son - 0.05, 100.72, "SWEEP: fitil 100.97 > 100.82, gövde altında")   # 10:10
    s.mum(100.72, 100.75, 100.48, 100.52, "M1"); s.mum(100.52, 100.55, 99.95, 100.02, "M2 displacement — MSS: 100.45 altı"); s.mum(100.02, 100.30, 99.85, 99.95, "M3")
    s.bacak(99.75, 2, gurultu=0.4)                                 # 10:35
    s.mum(s.son, 100.44, s.son - 0.02, 100.15, "FVG'nin %50'sine dönüş → limit doldu")
    s.bacak(99.9, 2); s.bacak(99.3, 3); s.bacak(98.92, 3, lab="hedef: seans low / SSL 98.9")
    df = s.df(); n = len(df)
    zaman = pd.date_range("2025-07-16 09:30", periods=n, freq="5min")
    fig = go.Figure(mum_izi(df, x=zaman, ad="5 dk mum"))
    t0, t1 = pd.Timestamp("2025-07-16 10:00"), pd.Timestamp("2025-07-16 11:00")
    fig.add_vrect(x0=t0, x1=t1, fillcolor=rgba(ALTIN, 0.14), line_width=0, layer="below", annotation_text="Silver Bullet NY AM 10:00–11:00 (17:00–18:00 TSİ yaz)", annotation_position="top left", annotation_font=dict(size=10, color=ALTIN))
    i_h = int(df.index[df.lab.str.startswith("pencere")][0]); i_sw = int(df.index[df.lab.str.startswith("SWEEP")][0]); i_m1 = int(df.index[df.lab == "M1"][0])
    i_g = int(df.index[df.lab.str.startswith("FVG'nin")][0]); i_t = int(df.index[df.lab.str.startswith("hedef")][0])
    yatay(fig, df.h[i_h], zaman[i_h], zaman[i_sw], renk=ALTIN, w=1.5); not_(fig, zaman[i_h], df.h[i_h] + 0.05, "pencere öncesi likidite haritası: BSL", renk=ALTIN, ok=False, boyut=10)
    daire(fig, zaman[i_sw], df.h[i_sw] - 0.05, r_x=pd.Timedelta(minutes=3), r_y=0.1)
    not_(fig, zaman[i_sw], df.h[i_sw], "① sweep pencere İÇİNDE", renk=ALTIN, ax=60, ay=-30)
    f = [f for f in fvg_bul(df) if f["tip"] == "SIBI" and f["i"] == i_m1][0]
    kutu(fig, zaman[i_m1], zaman[n - 1], f["alt"], f["ust"], MOR, a=0.2)
    ce = (f["alt"] + f["ust"]) / 2; yatay(fig, ce, zaman[i_m1], zaman[n - 1], renk=MOR, dash="dash")
    not_(fig, zaman[i_m1 + 1], df.c[i_m1 + 1], "② displacement + FVG (pencere içinde oluştu) + MSS", renk=BORDO, ax=90, ay=30)
    sl = df.h[i_m1] + 0.05; hedef = 98.9; giris = ce; R = sl - giris   # SL: FVG'yi yaratan üçlünün ucu (M1 high) + tampon
    sl_muh = df.h[i_sw] + 0.05                                        # muhafazakâr alternatif: sweep ucu
    yatay(fig, giris, zaman[i_g], zaman[n - 1], renk=MUREKKEP, dash="solid"); yatay(fig, sl, zaman[i_g], zaman[n - 1], renk=BORDO, dash="solid"); yatay(fig, hedef, zaman[i_g], zaman[n - 1], renk=TEAL, dash="solid")
    yatay(fig, sl_muh, zaman[i_g], zaman[n - 1], renk=BORDO, dash="dot", w=1.0)
    kutu(fig, zaman[i_g], zaman[n - 1], giris, sl, BORDO, a=0.2, cizgi=0); kutu(fig, zaman[i_g], zaman[n - 1], hedef, giris, TEAL, a=0.18, cizgi=0)
    not_(fig, zaman[i_g], giris, f"③ giriş limit = FVG %50 ({giris:.2f})", renk=MUREKKEP, ax=70, ay=-30)
    not_(fig, zaman[i_g], sl, f"SL {sl:.2f}: FVG'yi yaratan üçlünün ucu (M1 high {df.h[i_m1]:.2f}) + 0.05 tampon (1R = {R:.2f})", renk=BORDO, ok=False, boyut=10, xanchor="left", ay=-12)
    not_(fig, zaman[i_g], sl_muh, f"muhafazakâr alternatif: sweep ucu {df.h[i_sw]:.2f} + tampon = {sl_muh:.2f} → {(giris-hedef)/(sl_muh-giris):.1f}R", renk=BORDO, ok=False, boyut=9, xanchor="left", ay=-12)
    not_(fig, zaman[i_t], hedef, f"④ hedef: sonraki likidite (seans low) {hedef:.2f} → {(giris-hedef)/R:.1f}R", renk=TEAL, ax=-120, ay=30)
    tv = list(pd.date_range("2025-07-16 09:30", "2025-07-16 11:30", freq="15min"))
    fig.update_xaxes(tickvals=tv, ticktext=[f"{t:%H:%M} NY<br>{(t + pd.Timedelta(hours=7)):%H:%M} TSİ" for t in tv], tickfont=dict(size=10))
    lejant(fig, "FVG (SIBI)", MOR); lejant(fig, "Silver Bullet penceresi", ALTIN, a=0.3)
    duzen(fig, "Şekil 36 — Silver Bullet: 10:00–11:00 NY penceresinde sweep → FVG → %50 limit (şematik örnek, bearish)",
          "Pencereden önce likidite haritası; sweep ve FVG pencere içinde; SL FVG üçlüsünün ucu + tampon (muhafazakâr: sweep ucu); hedef sonraki havuz (~1:3)", x_baslik="saat (NY / TSİ, yaz)")
    kaydet(fig, "36_silver_bullet")


# =====================================================================================
# 21 — Pozisyon yönetimi: kısmi kâr, BE, structure trailing
# =====================================================================================
def g43_pozisyon_yonetimi():
    s = Seri(21, baslangic=102.62, birim=0.06)
    giris, sl0, T1, T2 = 102.57, 101.90, 103.97, 104.51
    s.bacak(102.57, 3, gurultu=0.4, lab="giriş doldu 102.57")
    s.bacak(102.75, 2); s.bacak(102.5, 2, gurultu=0.4); s.bacak(103.3, 3); s.bacak(103.05, 2, gurultu=0.4)
    s.bacak(104.05, 3, lab="TP1 103.97 alındı"); s.bacak(103.5, 3, lab="HL1 ≈103.5"); s.bacak(104.35, 3, lab="BOS: 104.05 üstü kapanış → SL HL1 altına")
    s.bacak(104.15, 2, gurultu=0.4, lab="HL2 ≈104.15"); s.bacak(104.7, 3, lab="TP2 104.51 alındı; BOS → SL HL2 altına"); s.bacak(105.1, 2); s.bacak(104.6, 2, lab="HL3 ≈104.6"); s.bacak(105.5, 3, lab="BOS → SL HL3 altına")
    s.bacak(105.0, 2, gurultu=0.4); s.mum(s.son, s.son + 0.05, 104.42, 104.47, "runner trailing stop'ta çıktı")
    s.bacak(104.9, 2)
    df = s.df(); n = len(df)
    def idx(p): return int(df.index[df.lab.str.startswith(p)][0])
    i_g = idx("giriş"); i_t1 = idx("TP1"); i_hl1 = idx("HL1"); i_b1 = idx("BOS: 104.05"); i_hl2 = idx("HL2"); i_t2 = idx("TP2"); i_hl3 = idx("HL3"); i_b3 = idx("BOS → SL HL3"); i_out = idx("runner")
    hl1 = df.l[i_hl1 - 1:i_hl1 + 2].min(); hl2 = df.l[i_hl2 - 1:i_hl2 + 2].min(); hl3 = df.l[i_hl3 - 1:i_hl3 + 2].min()
    fig = go.Figure(mum_izi(df, ad="5m/15m mum"))
    R = giris - sl0
    # SL merdiveni
    adim = [(i_g, i_t1, sl0, "SL₀ 101.90 (sweep altı) — risk 1R"), (i_t1, i_b1, giris, f"SL₁ = BE {giris:.2f} (TP1'de %50 kapatıldı)"),
            (i_b1, i_t2, hl1 - 0.05, f"SL₂ {hl1-0.05:.2f} = HL1 altı (BOS onayı ile)"), (i_t2, i_b3, hl2 - 0.05, f"SL₃ {hl2-0.05:.2f} = HL2 altı (TP2'de %25 daha kapatıldı)"),
            (i_b3, i_out, hl3 - 0.05, f"SL₄ {hl3-0.05:.2f} = HL3 altı → runner burada çıktı")]
    for k, (x0, x1, y, ad) in enumerate(adim):
        yatay(fig, y, x0, x1, renk=BORDO, dash="solid", w=2.2)
        if k > 0:
            fig.add_shape(type="line", x0=x0, x1=x0, y0=adim[k - 1][2], y1=y, line=dict(color=BORDO, width=1.2, dash="dot"))
        not_(fig, x0 + 0.3, y, ad, renk=BORDO, ok=False, boyut=9, xanchor="left", ay=11)
    yatay(fig, giris, i_g, n - 1, renk=MUREKKEP, dash="dash"); not_(fig, i_g, giris, f"giriş {giris:.2f} (%100 pozisyon)", renk=MUREKKEP, ax=-60, ay=40)
    yatay(fig, T1, i_g, i_t1 + 1, renk=TEAL, dash="dot"); yatay(fig, T2, i_g, i_t2 + 1, renk=TEAL, dash="dot")
    not_(fig, i_t1, T1, f"<b>TP1</b> {T1:.2f} = −0.27 (≈{(T1-giris)/R:.1f}R): %50 kapat → SL BE'ye<br>(BE, T1'den ÖNCE değil)", renk=TEAL, ax=-110, ay=-45)
    not_(fig, i_t2, T2, f"<b>TP2</b> {T2:.2f} = −0.62 / BSL (≈{(T2-giris)/R:.1f}R): %25 kapat,<br>%25 runner structure trailing ile", renk=TEAL, ax=-80, ay=-45)
    for i, y, ad in ((i_hl1, hl1, "HL1"), (i_hl2, hl2, "HL2"), (i_hl3, hl3, "HL3")):
        fig.add_trace(go.Scatter(x=[i], y=[y - 0.06], mode="markers+text", text=[ad], textposition="bottom center", marker=dict(symbol="triangle-up", size=9, color=TEAL), textfont=dict(size=10, color=TEAL), showlegend=False))
    for i, ad in ((i_b1, "BOS"), (i_t2, "BOS"), (i_b3, "BOS")):
        not_(fig, i, df.h[i] + 0.04, ad, renk=TEAL, ok=False, boyut=9)
    cikis = hl3 - 0.05
    not_(fig, i_out, df.l[i_out], f"runner çıkışı {cikis:.2f} (≈{(cikis-giris)/R:.1f}R)", renk=BORDO, ax=40, ay=40)
    top = 0.5 * (T1 - giris) / R + 0.25 * (T2 - giris) / R + 0.25 * (cikis - giris) / R
    not_(fig, 1, 105.6, f"toplam sonuç ≈ +{top:.1f}R (0.5×TP1 + 0.25×TP2 + 0.25×runner); trailing tamponu fitil için", renk=GRI, ok=False, boyut=10, xanchor="left")
    lejant_cizgi(fig, "stop merdiveni (structure trailing)", BORDO, "solid"); lejant_cizgi(fig, "hedefler", TEAL, "dot")
    fig.update_yaxes(range=[101.7, 105.8])
    duzen(fig, "Şekil 43 — Pozisyon yönetimi adım adım: kısmi kâr, BE ve structure trailing (şematik örnek)",
          "Her onaylı yeni HL (gövde kapanışlı BOS sonrası) → SL bir önceki HL'nin altına; kural: T1'den önce BE yok, erken trailing yok", x_baslik="mum sırası (girişten itibaren)")
    kaydet(fig, "43_pozisyon_yonetimi")


# =====================================================================================
# 22 — Geçersizleşme: kaybeden trade
# =====================================================================================
def g22_gecersizlesme():
    s = Seri(22, baslangic=102.9, birim=0.06)
    s.bacak(102.75, 3, gurultu=0.5); s.mum(s.son, s.son + 0.03, 102.0, 102.3, "sweep 102.00 (SL referansı)")
    s.mum(102.30, 102.44, 102.28, 102.42, "d1"); s.mum(102.42, 103.02, 102.40, 103.00, "d2 (FVG)"); s.mum(103.00, 103.55, 102.70, 103.50, "d3 MSS")
    s.bacak(103.3, 2, gurultu=0.4); s.bacak(102.9, 2); s.mum(102.9, 102.92, 102.45, 102.6, "giriş doldu FVG CE 102.57")
    s.bacak(102.75, 2, gurultu=0.4); s.bacak(102.6, 1, gurultu=0.3)
    s.mum(102.6, 102.63, 102.25, 102.52, "LTF minör dip: fitil 102.25 (FVG alt kenarı fitille görüldü, gövde içeride — dolum, geçersizleşme değil)")
    s.bacak(102.8, 2, gurultu=0.3)
    s.mum(102.75, 102.78, 102.28, 102.32, "gövde FVG'nin ALTINDA kapandı → IFVG (uyarı 1)")
    s.mum(102.32, 102.4, 102.05, 102.1, "LTF minör dip gövdeyle kırıldı → ters MSS (uyarı 2)")
    s.mum(102.1, 102.15, 101.8, 101.85, "SL 101.90 tetiklendi (−1R)")
    s.bacak(101.4, 3); s.bacak(101.0, 3)
    df = s.df(); n = len(df)
    def idx(p): return int(df.index[df.lab.str.startswith(p)][0])
    i_sw = idx("sweep"); i_d1 = idx("d1"); i_g = idx("giriş"); i_md = idx("LTF minör"); i_if = idx("gövde FVG"); i_ms = idx("LTF minör dip gövde"); i_sl = idx("SL 101.90")
    f = [f for f in fvg_bul(df) if f["tip"] == "BISI" and f["i"] == i_d1][0]
    giris, sl = (f["alt"] + f["ust"]) / 2, 101.90; R = giris - sl
    fig = go.Figure(mum_izi(df, ad="5m mum"))
    kutu(fig, i_d1, i_if, f["alt"], f["ust"], MOR, a=0.2); kutu(fig, i_if, n - 1, f["alt"], f["ust"], BORDO, a=0.2)
    kutu(fig, i_g, i_sl + 1, sl, giris, BORDO, a=0.2, cizgi=0)
    yatay(fig, giris, i_g, i_sl + 1, renk=MUREKKEP, dash="solid"); yatay(fig, sl, i_g, i_sl + 1, renk=BORDO, dash="solid", w=1.6)
    not_(fig, i_g, giris, f"giriş {giris:.2f} (FVG CE), SL {sl:.2f} — kurulum Şekil 32 ile aynı", renk=MUREKKEP, ax=-120, ay=-45)
    md = df.l[i_md - 1:i_md + 2].min(); yatay(fig, md, i_md, i_ms + 1, renk=GRI, dash="dot")
    not_(fig, i_if, df.c[i_if], f"<b>uyarı 1</b>: giriş FVG'si gövdeyle kapatıldı (IFVG)<br>→ kural: SL'i bekleme, kapat (≈−{(giris-df.c[i_if])/R:.1f}R)", renk=BORDO, ax=-170, ay=95)
    not_(fig, i_ms, df.c[i_ms], f"<b>uyarı 2</b>: LTF minör dip ({md:.2f}) gövdeyle kırıldı<br>= ters yönde MSS", renk=BORDO, ax=120, ay=-70)
    not_(fig, i_sl, sl, "SL tetiklendi: −1R (bekleyen için)", renk=BORDO, ax=70, ay=35)
    daire(fig, i_sw, df.l[i_sw] + 0.08, r_y=0.12); not_(fig, i_sw, df.l[i_sw], "sweep low 102.00 — SL bunun altında", renk=ALTIN, ax=-40, ay=40)
    not_(fig, n - 6, 103.55, "sonrası: fiyat düşmeye devam → 'geçerli MSS başarısız oldu' → yeniden girme yok,<br>HTF okuma sorgulanır; günlük kayıp limitine bak (2 stop → dur)", renk=GRI, ok=False, boyut=10, xanchor="right")
    lejant(fig, "giriş FVG'si", MOR); lejant(fig, "IFVG (geçersizleşme)", BORDO); lejant(fig, "risk kutusu (1R)", BORDO, a=0.2)
    duzen(fig, "Şekil 44 — Geçersizleşme: kaybeden bir işlem ve erken çıkış sinyalleri (şematik örnek)",
          "Aynı kurulum, ters sonuç: (1) FVG gövdeyle kapatıldı (IFVG), (2) ters MSS, (3) SL. Yapısal geçersizleşmede SL beklenmez", x_baslik="5m mum sırası")
    kaydet(fig, "44_gecersizlesme_kaybeden_trade")


# =====================================================================================
# 24 — PD array ailesi: rejection block, propulsion block, volume imbalance, BPR
# =====================================================================================
def g24_pd_array_ailesi():
    # okunabilirlik: dört panel alt alta (tek sütun) — okuma sırası (a) → (b) → (c) → (d)
    fig = make_subplots(rows=4, cols=1, subplot_titles=("(a) Rejection Block — fitil bölgesi", "(b) Propulsion Block — OB'yi test edip itki başlatan mum",
                                                        "(c) Volume Imbalance — gövde boşluğu (fitiller örtüşür)", "(d) Balanced Price Range — zıt iki FVG'nin örtüşmesi"),
                        vertical_spacing=0.06)
    # (a) RB bearish
    a = Seri(241); a.bacak(102.5, 4); a.bacak(103.4, 3, gurultu=0.5); a.mum(a.son, 104.6, a.son - 0.05, 103.5, "swing high mumu: uzun üst fitil (sweep)")
    a.bacak(102.2, 3); a.bacak(103.7, 3, gurultu=0.4); a.mum(103.7, 104.3, 103.6, 103.65, "RB retest (fitil bölgesine giriş)"); a.bacak(102.0, 3); a.bacak(101.0, 3)
    da = a.df(); i = int(da.index[da.lab.str.startswith("swing high")][0]); n = len(da)
    fig.add_trace(mum_izi(da, ad="Mum"), row=1, col=1)
    kutu(fig, i, n - 1, max(da.o[i], da.c[i]), da.h[i], TURUNCU, a=0.22, row=1, col=1)
    not_(fig, i, da.h[i], "RB (bearish): gövde üstü → fitil ucu<br>stop: fitil ucunun hemen ötesi", renk=TURUNCU, ax=-80, ay=-35, row=1, col=1)
    j = int(da.index[da.lab.str.startswith("RB retest")][0]); not_(fig, j, da.h[j], "retest → short", renk=TURUNCU, ax=50, ay=-30, row=1, col=1)
    # (b) PB
    b = Seri(242); b.bacak(103.5, 3); b.bacak(101.0, 4, gurultu=0.5); b.mum(b.son, b.son + 0.05, 100.3, 100.7, "OB mumu"); b.mum(100.7, 102.0, 100.65, 101.9, "d"); b.mum(101.9, 103.2, 101.85, 103.1, "d")
    b.bacak(103.8, 2); b.bacak(101.6, 3, gurultu=0.4); b.mum(101.6, 101.65, 100.85, 101.45, "PB: OB'ye fitille dokundu, itki başladı"); b.mum(101.45, 102.7, 101.4, 102.6, "d"); b.bacak(104.0, 3)
    b.bacak(102.4, 3); b.mum(102.4, 102.45, 101.4, 101.9, "PB retest → giriş"); b.bacak(104.5, 3)
    db = b.df(); n = len(db); io = int(db.index[db.lab == "OB mumu"][0]); ip = int(db.index[db.lab.str.startswith("PB:")][0]); ir = int(db.index[db.lab.str.startswith("PB retest")][0])
    fig.add_trace(mum_izi(db, ad="Mum", gorunur=False), row=2, col=1)
    kutu(fig, io, n - 1, db.c[io], db.o[io], MAVI, a=0.22, row=2, col=1); not_(fig, io + 1, db.o[io], "OB", renk=MAVI, ok=False, boyut=10, xanchor="left", ay=-10, row=2, col=1)
    kutu(fig, ip, n - 1, min(db.o[ip], db.c[ip]), max(db.o[ip], db.c[ip]), MOR, a=0.3, row=2, col=1)
    not_(fig, ip, db.l[ip], "PB: OB'ye dokunup itki başlatan mumun gövdesi<br>(daha hassas ikinci giriş bölgesi)", renk=MOR, ax=-40, ay=45, row=2, col=1)
    not_(fig, ir, db.l[ir], "PB retest → giriş, SL OB altı", renk=MOR, ax=50, ay=35, row=2, col=1)
    # (c) VI
    c = Seri(243); c.bacak(101.0, 5, gurultu=0.5); c.mum(c.son, 101.4, c.son - 0.1, 101.3, "M1"); c.mum(101.55, 102.6, 101.35, 102.5, "M2: open > close(M1), fitiller örtüşür"); c.bacak(103.2, 3); c.bacak(101.5, 3, lab="VI'ya dönüş"); c.bacak(103.5, 3)
    dc = c.df(); n = len(dc); i1 = int(dc.index[dc.lab == "M1"][0])
    fig.add_trace(mum_izi(dc, ad="Mum", gorunur=False), row=3, col=1)
    kutu(fig, i1, n - 1, dc.c[i1], dc.o[i1 + 1], GRI, a=0.3, row=3, col=1)
    not_(fig, i1 + 1, dc.o[i1 + 1], f"VI: close(M1) {dc.c[i1]:.2f} → open(M2) {dc.o[i1+1]:.2f}<br>gövdeler arasında boşluk, fitiller örtüşür (FVG değil)", renk=GRI, ax=90, ay=-40, row=3, col=1)
    # (d) BPR
    d = Seri(244); d.bacak(103.0, 4, gurultu=0.5); d.mum(d.son, 103.2, 102.85, 102.95, "b1"); d.mum(102.95, 103.0, 101.5, 101.6, "b2 bearish displacement"); d.mum(101.6, 102.2, 101.2, 101.4, "b3")
    d.bacak(100.9, 3, gurultu=0.5); d.mum(d.son, d.son + 0.05, 100.6, 100.95, "u1"); d.mum(100.95, 102.9, 100.9, 102.8, "u2 bullish displacement"); d.mum(102.8, 103.6, 102.55, 103.5, "u3"); d.bacak(104.3, 3)
    d.bacak(102.4, 3, lab="BPR retest"); d.bacak(104.8, 4)
    dd = d.df(); n = len(dd); ib = int(dd.index[dd.lab == "b1"][0]); iu = int(dd.index[dd.lab == "u1"][0])
    fb = [f for f in fvg_bul(dd) if f["i"] == ib][0]; fu = [f for f in fvg_bul(dd) if f["i"] == iu][0]
    fig.add_trace(mum_izi(dd, ad="Mum", gorunur=False), row=4, col=1)
    kutu(fig, ib, n - 1, fb["alt"], fb["ust"], BORDO, a=0.12, row=4, col=1); kutu(fig, iu, n - 1, fu["alt"], fu["ust"], TEAL, a=0.12, row=4, col=1)
    alt, ust = max(fb["alt"], fu["alt"]), min(fb["ust"], fu["ust"])
    kutu(fig, iu, n - 1, alt, ust, MOR, a=0.4, row=4, col=1); yatay(fig, (alt + ust) / 2, iu, n - 1, renk=MOR, dash="dash", row=4, col=1)
    not_(fig, ib + 1, fb["ust"], "bearish FVG (SIBI) — önce", renk=BORDO, ok=False, boyut=9, xanchor="left", ay=-10, row=4, col=1)
    not_(fig, iu + 1, fu["alt"], "bullish FVG (BISI) — sonra", renk=TEAL, ok=False, boyut=9, xanchor="left", ay=12, row=4, col=1)
    not_(fig, iu + 4, (alt + ust) / 2, f"BPR = örtüşme {alt:.2f}–{ust:.2f}, yön = sonraki FVG (bullish)<br>giriş örtüşme kenarı / CE; gövdeyle karşıya geçiş = geçersiz", renk=MOR, ax=60, ay=-45, row=4, col=1)
    ir = int(dd.index[dd.lab.str.startswith("BPR retest")][0]); not_(fig, ir, dd.l[ir], "BPR retest → long", renk=MOR, ax=40, ay=35, row=4, col=1)
    lejant(fig, "rejection block", TURUNCU); lejant(fig, "order block", MAVI); lejant(fig, "propulsion block / BPR", MOR); lejant(fig, "volume imbalance", GRI, a=0.3)
    duzen(fig, "Şekil 47 — PD array ailesinin geri kalanı: RB, PB, VI ve BPR (şematik örnek)", "Güç sıralaması (öznel, ICT derlemesi): BPR ≈ breaker+FVG > FVG ≈ OB+FVG > OB > IFVG > MB > RB > VI",
          h=1540, x_baslik="", legend_y=-0.05)
    for r_, c_ in ((1, 1), (2, 1), (3, 1), (4, 1)):
        fig.update_xaxes(rangeslider_visible=False, row=r_, col=c_)
    kaydet(fig, "47_pd_array_ailesi_rb_pb_vi_bpr")


# =====================================================================================
# GERÇEK VERİ — yfinance
# =====================================================================================
# Gerçek veri grafiklerinin tarih aralığı PİNLİDİR: script her çalıştığında aynı pencere çekilir,
# böylece MDX'teki sayılar (BOS/CHoCH sayısı, dealing range seviyeleri) grafiğe sadık kalır.
# Güncellemek için bu sabitleri değiştirip MDX'teki ilgili paragrafları da yenileyin (ozet.json'a bakın).
GERCEK_PENCERE = {
    "EURUSD=X": ("2026-07-20", "2026-08-19"),   # 1h — son 260 bar kullanılır
    "GC=F":     ("2026-06-19", "2026-08-19"),   # 1h — son 220 bar
    "BTC-USD":  ("2025-11-19", "2026-08-19"),   # 1d — son 200 bar
}
OZET: dict = {}


def veri_cek(ticker: str, period: str, interval: str) -> pd.DataFrame | None:
    try:
        import yfinance as yf
        bas, bit = GERCEK_PENCERE.get(ticker, (None, None))
        if bas:
            raw = yf.download(ticker, start=bas, end=bit, interval=interval, progress=False, auto_adjust=False)
        else:
            raw = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    except Exception as e:  # noqa
        RAPOR.append(f"yfinance hata {ticker} {interval}: {e}")
        return None
    if raw is None or len(raw) < 60:
        RAPOR.append(f"yfinance yetersiz veri {ticker} {interval}: {0 if raw is None else len(raw)} bar")
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0] for c in raw.columns]
    df = pd.DataFrame(dict(o=raw["Open"].values, h=raw["High"].values, l=raw["Low"].values, c=raw["Close"].values))
    ts = pd.to_datetime(raw.index)
    if getattr(ts, "tz", None) is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    df["ts"] = ts
    df = df.dropna().reset_index(drop=True)
    df["lab"] = ""
    return df


def zaman_ekseni(fig, df, adet=10, fmt="%d %b"):
    n = len(df); adimlar = list(range(0, n, max(1, n // adet)))
    fig.update_xaxes(tickvals=adimlar, ticktext=[df.ts[i].strftime(fmt) for i in adimlar], tickangle=0, tickfont=dict(size=10))


def hover_ts(df, fmt="%Y-%m-%d %H:%M"):
    return [f"{t:{fmt}}" for t in df.ts]


def gercek_1_eurusd_yapi():
    df = veri_cek("EURUSD=X", "30d", "1h")
    if df is None:
        return
    df = df.iloc[-260:].reset_index(drop=True); n = len(df)
    olay, sh, sl = yapi_olaylari(df, k=3)
    et = swing_etiketle(df, sh, sl)
    fig = go.Figure(mum_izi(df, ad="EURUSD 1h", hover_ek=hover_ts(df)))
    swing_isaretle(fig, df, sh, sl, et, k=3)
    ondalik = 4
    for o in olay:
        if o["tip"] in ("BOS", "CHoCH"):
            renk = TEAL if o["yon"] == "up" else BORDO
            yatay(fig, o["seviye"], o["ref"], o["i"], renk=renk, dash="solid" if o["tip"] == "BOS" else "dash", w=1.4)
            not_(fig, o["i"], o["seviye"], o["tip"], renk=renk, ok=False, boyut=9, ay=-10 if o["yon"] == "up" else 10, bg=None)
        elif o["tip"] == "sweep":
            y = df.h[o["i"]] if o["yon"] == "up" else df.l[o["i"]]
            daire(fig, o["i"], y, r_x=1.2, r_y=(df.h.max() - df.l.min()) * 0.012)
    lejant_cizgi(fig, "BOS (gövde kapanışıyla, trend yönünde)", TEAL, "solid"); lejant_cizgi(fig, "CHoCH (gövde kapanışıyla, trend aleyhine)", BORDO)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(symbol="circle-open", size=12, color=ALTIN, line_width=2), name="sweep (fitil ötede, gövde içeride)"))
    zaman_ekseni(fig, df)
    d0, d1 = df.ts[0].strftime("%d %b %Y"), df.ts[n - 1].strftime("%d %b %Y")
    duzen(fig, f"Şekil 48 — Gerçek veri — EURUSD, 1 saatlik, {d0} – {d1}: mekanik yapı tespiti",
          "Kural: 7-mum (k=3) fraktal swing; onaylı son swing'in close ile aşılması → trend yönünde BOS / aleyhine CHoCH; fitil aşımı + gövde içeride → sweep. Yalnızca mekanik; bağlam (kill zone, HTF bias) yok",
          y_baslik="EUR/USD", x_baslik="tarih (UTC; hover'da saat)")
    fig.update_yaxes(tickformat=f".{ondalik}f")
    kaydet(fig, "48_gercek_eurusd_1h_yapi")
    RAPOR.append(f"EURUSD 1h: {n} bar, {len(sh)} swing high, {len(sl)} swing low, olaylar: " + ", ".join(f"{o['tip']}" for o in olay))
    OZET.update(eurusd_bar=n, eurusd_olaylar=[o["tip"] for o in olay], eurusd_bos=sum(o["tip"] == "BOS" for o in olay),
                eurusd_choch=sum(o["tip"] == "CHoCH" for o in olay), eurusd_sweep=sum(o["tip"] == "sweep" for o in olay), eurusd_tarih=f"{d0} – {d1}")


def gercek_2_gold_fvg_ob():
    df = veri_cek("GC=F", "60d", "1h")
    if df is None:
        return
    df = df.iloc[-220:].reset_index(drop=True); n = len(df)
    a = atr(df, 14)
    fvgs = [f for f in fvg_bul(df) if (f["ust"] - f["alt"]) >= 0.5 * a[f["i"] + 1]]
    olay, sh, sl = yapi_olaylari(df, k=3)
    fig = go.Figure(mum_izi(df, ad="Altın (GC=F) 1h", hover_ek=hover_ts(df)))
    # FVG: dolana kadar uzat (karşı kenar gövdeyle geçilince biter)
    say = 0
    for f in fvgs[-14:]:
        bit = n - 1; durum = "fresh"
        for j in range(f["i"] + 3, n):
            if f["tip"] == "BISI" and min(df.o[j], df.c[j]) < f["alt"]:
                bit = j; durum = "inverted"; break
            if f["tip"] == "SIBI" and max(df.o[j], df.c[j]) > f["ust"]:
                bit = j; durum = "inverted"; break
        kutu(fig, f["i"], bit, f["alt"], f["ust"], MOR if durum == "fresh" else GRI, a=0.22 if durum == "fresh" else 0.12)
        say += 1
    # OB: her BOS/CHoCH için kırılım bacağındaki son zıt renkli mum
    obs = 0
    kirilimlar = [o for o in olay if o["tip"] in ("BOS", "CHoCH")][-10:]
    for o in kirilimlar:
        i = o["i"]; aday = None
        for j in range(i - 1, max(o["ref"], i - 10) - 1, -1):
            if (o["yon"] == "up" and df.c[j] < df.o[j]) or (o["yon"] == "down" and df.c[j] > df.o[j]):
                aday = j; break
        if aday is None:
            continue
        y0, y1 = sorted([df.o[aday], df.c[aday]])
        bit = n - 1
        for j in range(i + 1, n):
            if (o["yon"] == "up" and min(df.o[j], df.c[j]) < y0) or (o["yon"] == "down" and max(df.o[j], df.c[j]) > y1):
                bit = j; break
        taze = bit == n - 1
        kutu(fig, aday, bit, y0, y1, MAVI if taze else GRI, a=0.22 if taze else 0.10)
        renk = TEAL if o["yon"] == "up" else BORDO
        yatay(fig, o["seviye"], o["ref"], i, renk=renk, dash="solid" if o["tip"] == "BOS" else "dash", w=1.2)
        not_(fig, i, o["seviye"], o["tip"], renk=renk, ok=False, boyut=9, ay=-10 if o["yon"] == "up" else 10)
        obs += 1
    lejant(fig, "FVG (fresh — gövdeyle kapatılmamış)", MOR); lejant(fig, "FVG (inverted — gövdeyle geçildi)", GRI, a=0.12); lejant(fig, "OB (kırılım bacağının son zıt mumu) — fresh", MAVI); lejant(fig, "OB — gövdeyle geçildi (mitigated/breaker adayı)", GRI, a=0.10)
    lejant_cizgi(fig, "BOS", TEAL, "solid"); lejant_cizgi(fig, "CHoCH", BORDO)
    zaman_ekseni(fig, df)
    d0, d1 = df.ts[0].strftime("%d %b %Y"), df.ts[n - 1].strftime("%d %b %Y")
    duzen(fig, f"Şekil 49 — Gerçek veri — Altın (GC=F), 1 saatlik, {d0} – {d1}: mekanik FVG ve OB tespiti",
          "Kural: 3-mum FVG, boyut ≥ 0,5×ATR(14); OB = gövde-kapanışlı kırılımdan önceki son zıt renkli mumun gövdesi; kutular gövdeyle geçilince biter (inversion/mitigation). Sweep/kill zone filtresi yok — çoğu kutu 'aday'dır",
          y_baslik="USD/ons", x_baslik="tarih (UTC; hover'da saat)")
    kaydet(fig, "49_gercek_altin_1h_fvg_ob")
    RAPOR.append(f"GC=F 1h: {n} bar, {len(fvgs)} FVG (≥0.5 ATR, son 14 çizildi), {obs} OB (son 10 kırılım), olaylar: " + ", ".join(o['tip'] for o in olay))
    OZET.update(gold_bar=n, gold_fvg_toplam=len(fvgs), gold_fvg_cizilen=say, gold_ob=obs, gold_tarih=f"{d0} – {d1}")


def gercek_3_btc_eqh_dealing():
    df = veri_cek("BTC-USD", "9mo", "1d")
    if df is None:
        return
    df = df.iloc[-200:].reset_index(drop=True); n = len(df)
    a = atr(df, 14)
    sh, sl = swingler(df, 2)
    et = swing_etiketle(df, sh, sl)
    fig = go.Figure(mum_izi(df, ad="BTC-USD günlük", hover_ek=hover_ts(df, "%Y-%m-%d")))
    swing_isaretle(fig, df, sh, sl, et, k=2)
    # eşit tepeler / dipler: iki swing high'ın seviyesi ≤ 0.15 ATR farkla
    esit = []
    for grp, seri, tip in ((sh, df.h, "EQH"), (sl, df.l, "EQL")):
        for x in range(len(grp)):
            for y in range(x + 1, len(grp)):
                i, j = grp[x], grp[y]
                if abs(seri[i] - seri[j]) <= 0.15 * a[j] and 2 < j - i < 60:
                    esit.append((i, j, (seri[i] + seri[j]) / 2, tip))
    # aynı seviyenin tekrarları (üçlü/dörtlü eşit tepe) tek çizgiye indirgenir; son 4 EQH + son 4 EQL çizilir
    def tekil(tip):
        out = []
        for e in sorted([e for e in esit if e[3] == tip], key=lambda e: e[1]):
            if all(abs(e[2] - k[2]) > 0.15 * a[e[1]] for k in out):
                out.append(e)
        return out
    esit_h = tekil("EQH")[-4:]; esit_l = tekil("EQL")[-4:]
    secili = sorted(esit_h + esit_l, key=lambda e: e[1])
    say_sw = 0; say_run = 0
    for i, j, y, tip in secili:
        # süpürüldü mü? (fitil ötede, gövde içeride) — sonraki 40 mumda
        sw = None; run = None
        for k in range(j + 1, min(n, j + 40)):
            if tip == "EQH" and df.h[k] > y:
                if df.c[k] < y: sw = k
                else: run = k
                break
            if tip == "EQL" and df.l[k] < y:
                if df.c[k] > y: sw = k
                else: run = k
                break
        bit = sw if sw is not None else (run if run is not None else min(n - 1, j + 40))
        yatay(fig, y, i, bit, renk=ALTIN, w=1.6)
        not_(fig, i, y, tip, renk=ALTIN, ok=False, boyut=9, ay=-10 if tip == "EQH" else 10, xanchor="right")
        if sw is not None:
            say_sw += 1
            daire(fig, sw, df.h[sw] if tip == "EQH" else df.l[sw], r_x=1.5, r_y=(df.h.max() - df.l.min()) * 0.012)
            fig.add_annotation(x=sw, y=y, text="✕", showarrow=False, font=dict(size=16, color=ALTIN))
        elif run is not None:
            say_run += 1
            not_(fig, run, y, "run", renk=BORDO if tip == "EQL" else TEAL, ok=False, boyut=9, ay=12 if tip == "EQL" else -12)
    # dealing range: son ITH/ITL çifti
    ith, itl = orta_swingler(df, sh, sl)
    if ith and itl:
        iH, iL = ith[-1], itl[-1]
        H, L = df.h[iH], df.l[iL]; eq = (H + L) / 2; x0 = min(iH, iL)
        kutu(fig, x0, n + 4, eq, H, BORDO, a=0.06, cizgi=0); kutu(fig, x0, n + 4, L, eq, TEAL, a=0.06, cizgi=0)
        yatay(fig, eq, x0, n + 4, renk=GRI, dash="dash")
        not_(fig, n + 4, eq, f"EQ {eq:,.0f}", renk=GRI, ok=False, boyut=10, xanchor="left")
        not_(fig, n + 4, H, f"ITH {H:,.0f}", renk=BORDO, ok=False, boyut=10, xanchor="left"); not_(fig, n + 4, L, f"ITL {L:,.0f}", renk=TEAL, ok=False, boyut=10, xanchor="left")
        durum = "premium" if df.c[n - 1] > eq else "discount"
        not_(fig, n - 1, df.c[n - 1], f"son kapanış {durum}'ta", renk=BORDO if durum == "premium" else TEAL, ax=-60, ay=-30 if durum == "premium" else 30)
        RAPOR.append(f"BTC-USD: dealing range ITL {L:,.0f} – ITH {H:,.0f}, EQ {eq:,.0f}, son kapanış {durum}")
        OZET.update(btc_ith=round(float(H)), btc_itl=round(float(L)), btc_eq=round(float(eq)), btc_durum=durum)
    lejant_cizgi(fig, "eşit tepe/dip (≤ 0,15 ATR)", ALTIN, "solid"); lejant(fig, "premium (son ITH/ITL aralığı)", BORDO, a=0.1); lejant(fig, "discount", TEAL, a=0.1)
    zaman_ekseni(fig, df, fmt="%d %b %y")
    d0, d1 = df.ts[0].strftime("%d %b %Y"), df.ts[n - 1].strftime("%d %b %Y")
    duzen(fig, f"Şekil 50 — Gerçek veri — BTC-USD, günlük, {d0} – {d1}: eşit tepe/dip likiditesi ve dealing range",
          "Kural: 5-mum swing; iki swing seviyesi farkı ≤ 0,15×ATR(14) → EQH/EQL (aynı seviyenin tekrarları tek çizgi; son 4 EQH + 4 EQL); sonraki 40 günde fitil ötede + gövde içeride → sweep (✕), gövde ötede → run; etiketsiz = 40 günde test edilmedi. Dealing range = son ITH/ITL",
          y_baslik="USD", x_baslik="tarih")
    kaydet(fig, "50_gercek_btc_gunluk_eqh_dealing_range")
    RAPOR.append(f"BTC-USD günlük: {n} bar, {len(esit)} eşit tepe/dip çifti ({len(esit_h)} EQH + {len(esit_l)} EQL çizildi; {say_sw} sweep, {say_run} run)")
    OZET.update(btc_bar=n, btc_esit_toplam=len(esit), btc_eqh_cizilen=len(esit_h), btc_eql_cizilen=len(esit_l), btc_sweep=say_sw, btc_run=say_run,
                btc_tarih=f"{df.ts[0]:%d %b %Y} – {df.ts[n - 1]:%d %b %Y}")


# =====================================================================================
def main():
    print("SMC grafik seti →", CIKTI)
    for f in (g01_swing_yapi, g02_bos, g04_choch_mss, g05_internal_vs_swing, g05_dealing_range_ote, g06_eqh_eql,
              g07_sweep_vs_run, g11_inducement, g09_trendline, g10_fvg, g11_ifvg, g12_order_block, g13_breaker,
              g14_mitigation, g15_po3, g16_kill_zones, g27_haftalik_profil, g17_giris_1_htf, g18_giris_2_sweep_mss, g19_giris_3_giris_sl_tp,
              g36_silver_bullet, g43_pozisyon_yonetimi, g22_gecersizlesme, g46_mtf_panel, g24_pd_array_ailesi):
        f()
    if "--sentetik" not in sys.argv:
        for f in (gercek_1_eurusd_yapi, gercek_2_gold_fvg_ob, gercek_3_btc_eqh_dealing):
            try:
                f()
            except Exception as e:  # noqa
                RAPOR.append(f"{f.__name__} başarısız: {e!r}")
    if OZET:
        import json
        (CIKTI / "ozet.json").write_text(json.dumps(OZET, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  ✓ ozet.json (gerçek veri sayıları — MDX metniyle karşılaştırın)")
    print("\nÜretilen dosyalar:")
    for u in URETILEN:
        print(" ", u)
    if RAPOR:
        print("\nRapor / gerçek veri notları:")
        for r in RAPOR:
            print(" -", r)


if __name__ == "__main__":
    main()
