#!/usr/bin/env python3
"""Harmonik Patternler dersi — grafik seti üretici.

Kullanım:
    python3 site/tools/ders_grafik/harmonik_grafikler.py            # tüm grafikler
    python3 site/tools/ders_grafik/harmonik_grafikler.py --yenile   # gerçek veriyi yeniden indir

Çıktı: site/public/arastirma/harmonik-patternler/*.html  (Plotly, plotly.js CDN'den)

İki tür veri:
  (a) SENTETİK / ŞEMATİK OHLC — her kavramı ders kitabı netliğinde göstermek için
      kurgulanmış seriler (sabit seed, deterministik). Başlıklarda "şematik örnek".
  (b) GERÇEK VERİ — yfinance (XU100.IS, BTC-USD, GC=F, EURUSD=X). İlk çalıştırmada
      indirilir ve _veri/ altına CSV olarak önbelleğe alınır; sonraki çalıştırmalar
      önbelleği kullanır (deterministik). --yenile ile yeniden indirilir. İndirme
      başarısız olur ve önbellek yoksa o grafik ATLANIR ve raporlanır — sahte
      "gerçek" veri üretilmez.
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

KOK = Path(__file__).resolve().parents[3]  # repo kökü
CIKTI = KOK / "site" / "public" / "arastirma" / "harmonik-patternler"
VERI = Path(__file__).resolve().parent / "_veri"
CIKTI.mkdir(parents=True, exist_ok=True)
VERI.mkdir(parents=True, exist_ok=True)

YENILE = "--yenile" in sys.argv

# ---------------------------------------------------------------- palet
R = dict(
    up="#0f766e",     # yükseliş teal
    dn="#7f1d1d",     # düşüş bordo
    lik="#b45309",    # likidite / sweep altın
    ob="#1d4ed8",     # order block mavi
    fvg="#6d28d9",    # FVG mor
    prz="#ea580c",    # PRZ turuncu
    fib="#6b7280",    # fib gri
    ink="#211b12",
    yesil="#15803d",
    kirmizi="#b91c1c",
    mavi="#2563eb",
    gri="#9ca3af",
)
def rgba(hex_, a):
    h = hex_.lstrip("#")
    r_, g_, b_ = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r_},{g_},{b_},{a})"

PHI = (1 + 5 ** 0.5) / 2
URETILEN: list[str] = []
RAPOR: list[str] = []


# ---------------------------------------------------------------- sentetik mum üretimi
def mumlar(anchors, seed=1, gurultu=0.10, fitil=0.5):
    """anchors: [(bar, fiyat), ...] artan bar sırasıyla. Her bacak, iki uç arasında
    kalan (uçlar dahil, aşılmayan) gerçekçi mumlarla doldurulur; uç bar'ın ekstremi
    tam olarak verilen fiyata eşittir. Deterministik (seed)."""
    rng = np.random.default_rng(seed)
    n = anchors[-1][0] + 1
    O = np.full(n, np.nan); H = O.copy(); L = O.copy(); C = O.copy()
    i0, p0 = anchors[0]
    O[i0] = p0; C[i0] = p0; H[i0] = p0; L[i0] = p0
    prev_close = p0
    for (ia, pa), (ib, pb) in zip(anchors[:-1], anchors[1:]):
        m = ib - ia
        if m <= 0:
            continue
        leg = pb - pa
        lo, hi = min(pa, pb), max(pa, pb)
        eps = 0.015 * abs(leg) if leg != 0 else 0.0
        t = np.linspace(0, 1, m + 1)[1:]
        # köprü gürültüsü (uçlarda sıfır)
        w = np.cumsum(rng.normal(0, 1, m))
        w = w - t * w[-1]
        w = w / (np.abs(w).max() + 1e-9)
        # hafif "ivme" (başta yavaş sonda hızlı ya da tersi) — deterministik varyasyon
        egri = t ** rng.uniform(0.8, 1.25)
        path = pa + leg * egri + w * gurultu * abs(leg) * rng.uniform(0.6, 1.4)
        if leg != 0:
            path[:-1] = np.clip(path[:-1], lo + eps, hi - eps)
        path[-1] = pb
        adim = abs(leg) / m if leg != 0 else 0.002 * abs(pa)
        for j in range(m):
            i = ia + 1 + j
            o = prev_close
            c = path[j]
            body_hi, body_lo = max(o, c), min(o, c)
            wu = adim * fitil * rng.uniform(0.1, 1.6)
            wd = adim * fitil * rng.uniform(0.1, 1.6)
            h = body_hi + wu
            l = body_lo - wd
            if leg != 0 and j < m - 1:
                h = min(h, hi - eps); l = max(l, lo + eps)
                c = min(max(c, lo + eps), hi - eps)
            if j == m - 1 and leg != 0:
                # uç bar: ekstrem tam fiyat, kapanış hafif içeride
                if leg > 0:
                    h = pb; c = pb - adim * rng.uniform(0.15, 0.6); l = min(l, c - adim * 0.1)
                    l = max(l, lo + eps)
                else:
                    l = pb; c = pb + adim * rng.uniform(0.15, 0.6); h = max(h, c + adim * 0.1)
                    h = min(h, hi - eps)
            O[i], H[i], L[i], C[i] = o, max(h, o, c), min(l, o, c), c
            prev_close = c
    df = pd.DataFrame(dict(Open=O, High=H, Low=L, Close=C))
    df = df.ffill()
    return df


def rsi(close, n=14):
    d = np.diff(close, prepend=close[0])
    up = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    au = pd.Series(up).ewm(alpha=1 / n, adjust=False).mean().values
    ad = pd.Series(dn).ewm(alpha=1 / n, adjust=False).mean().values
    rs = au / (ad + 1e-12)
    return 100 - 100 / (1 + rs)


def atr(df, n=14):
    h, l, c = df.High.values, df.Low.values, df.Close.values
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().values


# ---------------------------------------------------------------- çizim yardımcıları
def temel_layout(fig, baslik, yukseklik=560, alt_baslik=None, lejant=False):
    fig.update_layout(
        showlegend=lejant,
        title=dict(text=baslik + (f"<br><sup>{alt_baslik}</sup>" if alt_baslik else ""),
                   x=0.01, xanchor="left"),
        paper_bgcolor="white", plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="top", y=-0.08, x=0),
        margin=dict(l=60, r=90, t=80, b=90),
        height=yukseklik, hovermode="x unified",
        xaxis_rangeslider_visible=False,
        font=dict(color=R["ink"]),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#efe9dc", zeroline=False, rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="#efe9dc", zeroline=False)
    return fig


def mum_iz(df, ad="Fiyat", etiketler=None, x=None, showlegend=False):
    if x is None:
        x = list(range(len(df)))
    text = None
    if etiketler:
        text = [""] * len(df)
        for i, t in etiketler.items():
            if 0 <= i < len(df):
                text[i] = t
    return go.Candlestick(
        x=x, open=df.Open, high=df.High, low=df.Low, close=df.Close, name=ad,
        increasing=dict(line=dict(color=R["up"], width=1), fillcolor=R["up"]),
        decreasing=dict(line=dict(color=R["dn"], width=1), fillcolor=R["dn"]),
        text=text, hovertext=text, showlegend=showlegend,
        whiskerwidth=0.4,
    )


def yatay(fig, y, x0, x1, metin, renk=None, dash="dash", w=1.2, konum="right", row=None, col=None,
          font=11, ysh=0):
    renk = renk or R["fib"]
    kw = dict(row=row, col=col) if row else {}
    fig.add_shape(type="line", x0=x0, x1=x1, y0=y, y1=y, line=dict(color=renk, width=w, dash=dash), **kw)
    if metin:
        fig.add_annotation(x=x1 if konum == "right" else x0, y=y, text=metin, showarrow=False,
                           xanchor="left" if konum == "right" else "right", yanchor="middle",
                           font=dict(size=font, color=renk), xshift=4 if konum == "right" else -4,
                           yshift=ysh, **kw)


def kutu(fig, x0, x1, y0, y1, renk, alfa=0.18, metin=None, konum="top", kenar=1, row=None, col=None,
         font=11, metin_renk=None):
    kw = dict(row=row, col=col) if row else {}
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=min(y0, y1), y1=max(y0, y1),
                  fillcolor=rgba(renk, alfa), line=dict(color=renk, width=kenar), layer="below", **kw)
    if metin:
        yy = max(y0, y1) if konum in ("top", "top-in") else min(y0, y1)
        if konum == "mid":
            yy = (y0 + y1) / 2
        fig.add_annotation(x=x0, y=yy, text=metin, showarrow=False, xanchor="left",
                           yanchor="bottom" if konum == "top" else ("top" if konum in ("bottom", "top-in") else "middle"),
                           font=dict(size=font, color=metin_renk or renk), xshift=3, **kw)


def ok(fig, x, y, metin, ax=0, ay=-45, renk=None, font=11, row=None, col=None, ok_boyu=1.4, arkaplan=True,
       xanchor="center"):
    renk = renk or R["ink"]
    kw = dict(row=row, col=col) if row else {}
    fig.add_annotation(x=x, y=y, text=metin, showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=ok_boyu,
                       arrowcolor=renk, ax=ax, ay=ay, font=dict(size=font, color=renk),
                       bgcolor="rgba(255,255,255,0.85)" if arkaplan else None,
                       bordercolor=renk if arkaplan else None, borderwidth=0.6 if arkaplan else 0,
                       borderpad=2, xanchor=xanchor, **kw)


def not_kutusu(fig, metin, x=0.99, y=0.98, renk=None, font=11, xanchor="right", yanchor="top", row=None, col=None):
    renk = renk or R["ink"]
    kw = dict(row=row, col=col) if row else {}
    if row:
        fig.add_annotation(xref="x domain", yref="y domain", x=x, y=y, text=metin, showarrow=False,
                           xanchor=xanchor, yanchor=yanchor, align="left", font=dict(size=font, color=renk),
                           bgcolor="rgba(255,255,255,0.92)", bordercolor="#d8cfba", borderwidth=1, borderpad=5, **kw)
    else:
        fig.add_annotation(xref="paper", yref="paper", x=x, y=y, text=metin, showarrow=False,
                           xanchor=xanchor, yanchor=yanchor, align="left", font=dict(size=font, color=renk),
                           bgcolor="rgba(255,255,255,0.92)", bordercolor="#d8cfba", borderwidth=1, borderpad=5)


def zigzag_iz(pts, ad="XABCD", renk=None, w=2.2, harfler=None, dash=None, showlegend=True, row=None, col=None,
              fig=None, yon_ofset=None):
    """pts: [(x, y), ...]; harfler: ["X","A",...] noktalara yazılır."""
    renk = renk or R["ink"]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    kw = dict(row=row, col=col) if row else {}
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=ad,
                             line=dict(color=renk, width=w, dash=dash),
                             marker=dict(size=7, color="white", line=dict(color=renk, width=2)),
                             hoverinfo="skip", showlegend=showlegend), **kw)
    if harfler:
        for k, (x, y) in enumerate(pts):
            if k >= len(harfler) or not harfler[k]:
                continue
            # tepe mi dip mi: komşulara göre
            komsu = [ys[j] for j in (k - 1, k + 1) if 0 <= j < len(ys)]
            tepe = all(y >= c for c in komsu) if komsu else True
            fig.add_annotation(x=x, y=y, text=f"<b>{harfler[k]}</b>", showarrow=False,
                               yshift=14 if tepe else -14, font=dict(size=14, color=renk),
                               bgcolor="rgba(255,255,255,0.8)", **kw)


def bacak_etiketi(fig, p1, p2, metin, renk=None, font=11, row=None, col=None, xsh=0, ysh=0):
    """iki nokta arasındaki bacağın ortasına oran etiketi."""
    renk = renk or R["ink"]
    kw = dict(row=row, col=col) if row else {}
    fig.add_annotation(x=(p1[0] + p2[0]) / 2, y=(p1[1] + p2[1]) / 2, text=metin, showarrow=False,
                       font=dict(size=font, color=renk), bgcolor="rgba(255,255,255,0.9)",
                       bordercolor=renk, borderwidth=0.6, borderpad=2, xshift=xsh, yshift=ysh, **kw)


def rr_kutulari(fig, x0, x1, giris, stop, hedef, metin_h="TP", metin_s="SL", row=None, col=None, alfa=0.16):
    """giriş–hedef yeşil, giriş–stop kırmızı kutu; R:R hesaplı etiket."""
    kw = dict(row=row, col=col) if row else {}
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=min(giris, hedef), y1=max(giris, hedef),
                  fillcolor=rgba(R["yesil"], alfa), line=dict(color=R["yesil"], width=1), layer="below", **kw)
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=min(giris, stop), y1=max(giris, stop),
                  fillcolor=rgba(R["kirmizi"], alfa), line=dict(color=R["kirmizi"], width=1), layer="below", **kw)
    rr = abs(hedef - giris) / max(abs(giris - stop), 1e-9)
    fig.add_annotation(x=x1, y=hedef, text=f"{metin_h}  R:R {rr:.1f}", showarrow=False, xanchor="left",
                       font=dict(size=11, color=R["yesil"]), xshift=4, **kw)
    fig.add_annotation(x=x1, y=stop, text=f"{metin_s}", showarrow=False, xanchor="left",
                       font=dict(size=11, color=R["kirmizi"]), xshift=4, **kw)


def prz_cizgileri(fig, prz, x0, x1, row=None, col=None, font=10, fmt="{:.2f}"):
    """PRZ içindeki seviyeleri noktalı çizgi + kademeli (üst üste binmeyen) etiketle çizer."""
    sirali = sorted(prz.items(), key=lambda kv: kv[1])
    k = len(sirali)
    for i, (ad, y) in enumerate(sirali):
        ysh = (i - (k - 1) / 2) * 13
        yatay(fig, y, x0, x1, f"{ad} → {fmt.format(y)}", renk=R["prz"], dash="dot", w=1, row=row, col=col, font=font, ysh=ysh)


def _alt_baslik_kir(fig, esik=24, font=12):
    """make_subplots alt panel başlıklarını sitede (~800 px iframe) çakışmasın diye
    kırar: 3+ sütunlu figürlerde uzun başlıklar en yakın boşluktan iki satıra bölünür
    ve fontları küçültülür. Alt başlıklar make_subplots'un ürettiği ilk N annotation'dır
    (yanchor='bottom', xref '... domain'); kullanıcı annotation'larına dokunulmaz."""
    try:
        cols = max((int(str(ax.anchor or "y").lstrip("y") or 1)) for ax in fig.select_xaxes()) if list(fig.select_xaxes()) else 1
    except Exception:
        cols = 1
    for a in fig.layout.annotations:
        xref = str(getattr(a, "xref", ""))
        if getattr(a, "yanchor", None) != "bottom" or not (xref.endswith("domain") or xref == "paper"):
            continue
        if xref == "paper" and (getattr(a, "y", 0) or 0) < 0.97:
            continue   # paper-referanslı ama üstte olmayan: kullanıcı notu
        t = a.text or ""
        if cols >= 3 or len(t) > 40:
            a.font = a.font or {}
            a.font.size = font
        if cols >= 3 and len(t) > esik and "<br>" not in t:
            k = t.rfind(" ", 0, max(esik, len(t) // 2 + 4))
            if k > 8:
                a.text = t[:k] + "<br>" + t[k + 1:]
    m = fig.layout.margin
    if m is not None and (m.r or 0) < 110:
        fig.update_layout(margin=dict(r=110))


def kaydet(fig, ad):
    _alt_baslik_kir(fig)
    yol = CIKTI / f"{ad}.html"
    fig.write_html(str(yol), include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    URETILEN.append(str(yol))
    print("yazıldı:", yol.name)


def lvl(a, x, r):
    """A'dan X yönüne r oranı: retracement (r<1) ve extension (r>1) aynı formül."""
    return a - r * (a - x)


# ---------------------------------------------------------------- XABCD kurgu
def xabcd_kur(rB, rC, dXA, yon="bull", X=100.0, xa=20.0, on=8, nXA=18, nAB=11, nBC=9, nCD=14, son=10,
              seed=1, sonrasi=None, gurultu=0.10):
    """Tam oranlarla XABCD noktaları + sentetik mumlar. yon='bull': X dip, A tepe.
    sonrasi: D sonrası ek anchor listesi [(bar_ofset, fiyat_katsayısı(AD bacağının oranı)), ...]"""
    s = 1 if yon == "bull" else -1
    A = X + s * xa
    B = lvl(A, X, rB)
    C = B + (A - B) * rC
    D = lvl(A, X, dXA)
    bX, bA, bB, bC, bD = on, on + nXA, on + nXA + nAB, on + nXA + nAB + nBC, on + nXA + nAB + nBC + nCD
    pre = X - s * xa * 0.35  # X öncesi tersten gelen küçük hareket
    anchors = [(0, pre + s * xa * 0.12), (int(on * 0.45), pre), (bX, X), (bA, A), (bB, B), (bC, C), (bD, D)]
    if sonrasi:
        for ofs, k in sonrasi:
            anchors.append((bD + ofs, D + k * (A - D)))
    else:
        anchors.append((bD + son, D + 0.45 * (A - D)))
    df = mumlar(anchors, seed=seed, gurultu=gurultu)
    pts = dict(X=(bX, X), A=(bA, A), B=(bB, B), C=(bC, C), D=(bD, D))
    return df, pts


def xabcd_ciz(fig, pts, df, rB, rC, dXA, prz_seviyeleri, gecersizlik=None, row=None, col=None,
              baslik_pat="", etiketler=True, abcd_k=None, bc_r=None, x_son=None, showlegend=True,
              prz_metin="PRZ", ekstra_notlar=None):
    """Mumların üstüne XABCD, bacak oran etiketleri, PRZ kutusu, geçersizlik çizgisi."""
    X, A, B, C, D = pts["X"], pts["A"], pts["B"], pts["C"], pts["D"]
    x_son = x_son if x_son is not None else len(df) - 1
    zigzag_iz([X, A, B, C, D], harfler=["X", "A", "B", "C", "D"], fig=fig, row=row, col=col,
              ad="XABCD", showlegend=showlegend)
    if etiketler:
        bacak_etiketi(fig, A, B, f"B = {rB:.3f} XA", row=row, col=col, xsh=-26, ysh=-16)
        bacak_etiketi(fig, B, C, f"C = {rC:.3f} AB", row=row, col=col, xsh=26, ysh=16)
        cd_txt = f"D = {dXA:.3f} XA"
        if bc_r:
            cd_txt += f"<br>{bc_r:.3f} BC"
        if abcd_k:
            cd_txt += f"<br>AB=CD ×{abcd_k:.2f}"
        bacak_etiketi(fig, C, D, cd_txt, row=row, col=col)
    # PRZ
    lo, hi = min(prz_seviyeleri.values()), max(prz_seviyeleri.values())
    kutu(fig, C[0], x_son, lo, hi, R["prz"], alfa=0.18, metin=prz_metin, konum="top", row=row, col=col)
    prz_cizgileri(fig, prz_seviyeleri, C[0], x_son, row=row, col=col)
    if gecersizlik is not None:
        yatay(fig, gecersizlik[1], X[0], x_son, gecersizlik[0], renk=R["kirmizi"], dash="dash", w=1.4,
              row=row, col=col)
    if ekstra_notlar:
        for (x, y, t, ax, ay, renk) in ekstra_notlar:
            ok(fig, x, y, t, ax=ax, ay=ay, renk=renk, row=row, col=col)
    # sağdaki etiketler için pay; annotation metinleri autorange'i şişirmesin
    kw = dict(row=row, col=col) if row else {}
    fig.update_xaxes(range=[0, x_son * 1.34], **kw)


# ================================================================ GRAFİKLER
# ---------------------------------------------------------------- 01 fib türetimi
def g01_fib_turetim():
    # yerleşim: dar makale sütununda yan yana iki panel daralıyordu → ALT ALTA
    fig = make_subplots(rows=2, cols=1, row_heights=[0.42, 0.58], vertical_spacing=0.10,
                        subplot_titles=("Ardışık Fibonacci oranı F(n+1)/F(n) → φ",
                                        "Harmonik oran ailesi: türetim zinciri"))
    F = [1, 1]
    for _ in range(14):
        F.append(F[-1] + F[-2])
    oranlar = [F[i + 1] / F[i] for i in range(len(F) - 1)]
    fig.add_trace(go.Scatter(x=list(range(1, len(oranlar) + 1)), y=oranlar, mode="lines+markers+text",
                             text=[f"{F[i+1]}/{F[i]}" if i < 8 else "" for i in range(len(oranlar))], textposition="top center",
                             textfont=dict(size=9), name="F(n+1)/F(n)", line=dict(color=R["up"]),
                             marker=dict(size=6)), row=1, col=1)
    fig.add_hline(y=PHI, line=dict(color=R["lik"], dash="dash"), row=1, col=1)
    fig.add_annotation(x=len(oranlar), y=PHI, text=f"φ = {PHI:.6f}", showarrow=False, yshift=-12, xanchor="right",
                       font=dict(color=R["lik"], size=11), row=1, col=1)
    fig.update_yaxes(range=[0.9, 2.2], title="oran", row=1, col=1)
    fig.update_xaxes(title="n", row=1, col=1)

    # alt panel: sıralı oran ekseni (eşit aralıklı) + kategori satırları
    satirlar = {
        "Birincil": [(0.618, "1/φ"), (1.618, "φ")],
        "Karekök zinciri": [(0.786, "√0.618"), (0.886, "√0.786"), (1.128, "√1.272<br>= 1/0.886"), (1.272, "√1.618<br>= 1/0.786")],
        "Kare / tümleyen": [(0.236, "1/φ³"), (0.382, "1/φ²<br>= 1−0.618"), (2.618, "φ²<br>= 1/0.382"), (3.618, "φ²+1")],
        "Fibonacci DIŞI": [(0.5, "1/2<br>(Gartley 1935)"), (0.707, "√0.5"), (1.414, "√2"), (2.0, "2"), (2.236, "√5"), (3.14, "π")],
    }
    tum = sorted({v for lst in satirlar.values() for v, _ in lst})
    pos = {v: i for i, v in enumerate(tum)}
    ysatir = {ad: k for k, ad in enumerate(reversed(list(satirlar.keys())))}
    renkler = {"Birincil": R["up"], "Karekök zinciri": R["mavi"], "Kare / tümleyen": R["fvg"], "Fibonacci DIŞI": R["gri"]}
    for ad, lst in satirlar.items():
        xs = [pos[v] for v, _ in lst]; ts = [d for _, d in lst]
        fig.add_trace(go.Scatter(x=xs, y=[ysatir[ad]] * len(xs), mode="markers+text", text=ts,
                                 textposition="top center", textfont=dict(size=9, color=renkler[ad]),
                                 marker=dict(size=12, color=renkler[ad], symbol="diamond"), name=ad,
                                 customdata=[v for v, _ in lst],
                                 hovertemplate="%{customdata}: %{text}<extra></extra>"), row=2, col=1)
    for a, b, y in [(0.382, 0.618, ysatir["Kare / tümleyen"] - 0.3), (0.618, 0.786, ysatir["Karekök zinciri"] - 0.3),
                    (0.786, 0.886, ysatir["Karekök zinciri"] - 0.3), (1.128, 1.272, ysatir["Karekök zinciri"] - 0.3),
                    (1.272, 1.618, ysatir["Karekök zinciri"] - 0.3), (1.618, 2.618, ysatir["Kare / tümleyen"] - 0.3)]:
        fig.add_annotation(x=pos[b], y=y, ax=pos[a], ay=y, xref="x2", yref="y2", axref="x2", ayref="y2", showarrow=True,
                           arrowhead=2, arrowcolor=R["fib"], arrowwidth=1.2, text="")
    fig.add_annotation(xref="x2 domain", yref="y2 domain", x=0.5, y=-0.2, showarrow=False, align="center",
                       text="Zincir: 0.382 →√→ 0.618 →√→ 0.786 →√→ 0.886   ve tersleri:   1.128 ← 1.272 ← 1.618 ← 2.618"
                            "<br>Gri satır: 0.5, 0.707, 1.414, 2.0, 2.236, 3.14 Fibonacci dizisinden GELMEZ — Carney'nin ampirik eklemeleri",
                       font=dict(size=10.5, color=R["ink"]))
    fig.update_yaxes(tickvals=list(ysatir.values()), ticktext=list(ysatir.keys()), range=[-0.6, 3.9], row=2, col=1)
    fig.update_xaxes(title="oran (eşit aralıklı, değere göre sıralı)", tickvals=list(pos.values()),
                     ticktext=[f"{v:g}" for v in tum], range=[-0.6, len(tum) - 0.4], row=2, col=1)
    temel_layout(fig, "Şekil 01 — Fibonacci'den harmonik oranlara: her sayı nereden geliyor?", 780, lejant=True)
    fig.update_layout(hovermode="closest", margin=dict(b=130))
    kaydet(fig, "01_fib_turetim")


# ---------------------------------------------------------------- 02/03/04 fib araçları
def _xa_ornek(seed=2):
    # sadece X→A impuls + B düzeltmesi 0.618'e; sonra C'ye toparlanma (retracement/extension gösterimi için)
    return xabcd_kur(0.618, 0.786, 0.786, seed=seed)


def g02_retracement():
    df, p = _xa_ornek()
    n = p["B"][0] + 4
    df = df.iloc[:n + 1]
    X, A, B = p["X"], p["A"], p["B"]
    fig = go.Figure(mum_iz(df, etiketler={X[0]: "X", A[0]: "A", B[0]: "B"}))
    zigzag_iz([X, A, B], harfler=["X", "A", "B"], fig=fig, ad="X→A→B")
    for r in (0.382, 0.5, 0.618, 0.786, 0.886):
        y = lvl(A[1], X[1], r)
        yatay(fig, y, X[0], n + 6, f"{r:.3f} XA → {y:.2f}", renk=R["fib"] if r != 0.618 else R["up"],
              w=1 if r != 0.618 else 2)
    yatay(fig, A[1], X[0], n + 6, "0.0 (A)", renk=R["gri"], dash="solid", w=1)
    yatay(fig, X[1], X[0], n + 6, "1.0 (X)", renk=R["gri"], dash="solid", w=1)
    fig.add_trace(go.Scatter(x=[B[0]], y=[B[1]], mode="markers", marker=dict(size=22, color="rgba(0,0,0,0)",
                             line=dict(color=R["up"], width=3)), name="B = 0.618 XA", hoverinfo="skip"))
    ok(fig, B[0], B[1], "B tam 0.618'de durdu<br>→ Gartley/Crab adayı", ax=70, ay=45, renk=R["up"])
    ok(fig, (X[0] + A[0]) / 2, lvl(A[1], X[1], 0.5), "Fib aracı: X'ten A'ya sürüklenir<br>(2 nokta, içeri)",
       ax=-90, ay=-40, renk=R["fib"])
    fig.add_annotation(x=A[0], y=A[1], ax=X[0], ay=X[1], xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowcolor=R["lik"], arrowwidth=2, text="", opacity=0.7)
    not_kutusu(fig, "Retracement: r = |A−B| / |A−X|<br>Seviye = A − r·(A−X)<br>0 < r < 1", x=0.01, y=0.02,
               xanchor="left", yanchor="bottom")
    temel_layout(fig, "Şekil 02 — Fibonacci retracement: XA bacağının içine düzeltme (şematik örnek)", 540,
                 "İki noktalı çizim; B'nin hangi seviyede durduğu pattern'i sınıflandırır")
    fig.update_yaxes(title="fiyat")
    kaydet(fig, "02_fib_retracement")


def g03_extension():
    df, p = _xa_ornek()
    n = p["B"][0] + 4
    df = df.iloc[:n + 1]
    X, A, B = p["X"], p["A"], p["B"]
    fig = go.Figure(mum_iz(df, etiketler={X[0]: "X", A[0]: "A", B[0]: "B"}))
    zigzag_iz([X, A, B], harfler=["X", "A", "B"], fig=fig, ad="X→A→B")
    yatay(fig, A[1], X[0], n + 6, "0.0 (A)", renk=R["gri"], dash="solid", w=1)
    yatay(fig, X[1], X[0], n + 6, "1.0 (X) — retracement biter, extension başlar", renk=R["kirmizi"], dash="solid", w=1.4)
    for r, ad, renk in [(0.786, "0.786 XA — Gartley D", R["fib"]), (0.886, "0.886 XA — Bat D", R["fib"]),
                        (1.13, "1.13 XA — Alt Bat D", R["mavi"]), (1.272, "1.272 XA — Butterfly D", R["fvg"]),
                        (1.618, "1.618 XA — Crab / Deep Crab D", R["dn"])]:
        y = lvl(A[1], X[1], r)
        yatay(fig, y, X[0], n + 6, f"{ad} → {y:.2f}", renk=renk, w=1.6 if r > 1 else 1)
    kutu(fig, X[0], n + 6, lvl(A[1], X[1], 1.0), lvl(A[1], X[1], 1.7), R["lik"], alfa=0.07,
         metin="X'in ötesi = X altındaki stop havuzu (extension pattern'lerinde süpürülür)", konum="bottom",
         metin_renk=R["lik"])
    ok(fig, (X[0] + A[0]) / 2 + 3, lvl(A[1], X[1], 1.13), "Aynı X→A aracı, r > 1 satırları:<br>1.13 / 1.27 / 1.618",
       ax=90, ay=30, renk=R["mavi"])
    not_kutusu(fig, "Extension: aynı iki nokta, r > 1<br>Seviye = A − r·(A−X)  → X'in altına çıkar", x=0.99, y=0.98)
    temel_layout(fig, "Şekil 03 — Fibonacci extension: aynı XA aracında 1'in ötesi (şematik örnek)", 560,
                 "Butterfly/Crab/Alt Bat'in D noktası X'in ötesindedir; stop mantığı da bu yüzden farklıdır")
    fig.update_yaxes(title="fiyat", range=[lvl(A[1], X[1], 1.75), A[1] + 2])
    kaydet(fig, "03_fib_extension")


def g04_projection():
    df, p = xabcd_kur(0.618, 0.786, 0.786, seed=3)
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    n = C[0] + 3
    df = df.iloc[:n + 1]
    x1 = D[0] + 8
    fig = go.Figure(mum_iz(df, etiketler={X[0]: "X", A[0]: "A", B[0]: "B", C[0]: "C"}))
    zigzag_iz([X, A, B, C], harfler=["X", "A", "B", "C"], fig=fig, ad="X→A→B→C")
    # BC projeksiyonları
    for k, renk in [(1.272, R["mavi"]), (1.618, R["mavi"]), (2.0, R["fvg"]), (2.24, R["fvg"]), (2.618, R["dn"]),
                    (3.14, R["dn"]), (3.618, R["dn"])]:
        y = C[1] - k * (C[1] - B[1])
        yatay(fig, y, C[0], x1, f"{k:.3f} BC → {y:.2f}", renk=renk, w=1.2)
    # AB=CD kopyası
    fig.add_annotation(x=B[0], y=B[1], ax=A[0], ay=A[1], xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                       arrowhead=3, arrowwidth=2.5, arrowcolor=R["lik"], text="")
    bacak_etiketi(fig, A, B, "|AB| ölçüsü", renk=R["lik"], xsh=-40)
    for k, dash in [(1.0, "solid"), (1.272, "dash"), (1.618, "dot")]:
        d = C[1] - k * (A[1] - B[1])
        fig.add_annotation(x=C[0] + 6, y=d, ax=C[0] + 6, ay=C[1], xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowwidth=2.5 if k == 1 else 1.4, arrowcolor=R["lik"], text="")
        fig.add_annotation(x=C[0] + 6, y=d, text=f"CD = {k:.3f}·AB → {d:.2f}", showarrow=False, xanchor="left",
                           xshift=6, font=dict(size=10.5, color=R["lik"]), bgcolor="rgba(255,255,255,0.85)")
    ok(fig, C[0], C[1], "Projeksiyon 3 nokta:<br>B'ye tıkla → C'ye tıkla → C'den ileri at", ax=-40, ay=-70, renk=R["mavi"])
    yatay(fig, X[1], X[0], x1, "X", renk=R["gri"], dash="solid", w=1)
    not_kutusu(fig, "BC projeksiyonu: D = C − k·(C−B), k ∈ {1.27, 1.618, 2.0, 2.24, 2.618, 3.14, 3.618}"
                    "<br>AB=CD: D = C − k·(A−B), k ∈ {1.0, 1.27, 1.618}"
                    "<br>Hafıza: retracement 2 nokta içeri · extension 2 nokta dışarı · projection 3 nokta (ölç-taşı)",
               x=0.01, y=0.02, xanchor="left", yanchor="bottom")
    temel_layout(fig, "Şekil 04 — Projeksiyon: BC bacağı C'den ileri atılır; AB ölçüsü C'den kopyalanır (şematik örnek)", 600,
                 "Aynı yapıda üçüncü araç: bir bacağın uzunluğu BAŞKA bir noktadan taşınır")
    fig.update_yaxes(title="fiyat", range=[C[1] - 3.7 * (C[1] - B[1]) - 1, A[1] + 2])
    kaydet(fig, "04_fib_projeksiyon_abcd")


# ---------------------------------------------------------------- 05 AB=CD üç varyant
def g05_abcd():
    # yerleşim: üç varyant yan yana daralıyordu → ALT ALTA (okuma sırası: eşit → 1.272 → 1.618)
    fig = make_subplots(rows=3, cols=1, shared_yaxes=False, vertical_spacing=0.07,
                        subplot_titles=("CD = 1.0·AB (eşit)", "CD = 1.272·AB (alternatif)", "CD = 1.618·AB (alternatif)"))
    for row, (k, rC, nCD, seed) in enumerate([(1.0, 0.618, 15, 11), (1.272, 0.786, 17, 12), (1.618, 0.786, 20, 13)], start=1):
        A = 120.0; B = 100.0; C = B + rC * (A - B); D = C - k * (A - B)
        bA, bB, bC, bD = 6, 21, 21 + 12, 21 + 12 + nCD
        anchors = [(0, A - 6), (bA, A), (bB, B), (bC, C), (bD, D), (bD + 10, D + 0.4 * (C - D))]
        df = mumlar(anchors, seed=seed)
        fig.add_trace(mum_iz(df, etiketler={bA: "A", bB: "B", bC: "C", bD: "D"}), row=row, col=1)
        zigzag_iz([(bA, A), (bB, B), (bC, C), (bD, D)], harfler=["A", "B", "C", "D"], fig=fig, row=row, col=1,
                  showlegend=(row == 1))
        bacak_etiketi(fig, (bB, B), (bC, C), f"C = {rC:.3f} AB", row=row, col=1)
        bacak_etiketi(fig, (bC, C), (bD, D), f"CD = {k:.3f}·AB<br>{(C-D)/(C-B):.2f} BC", row=row, col=1)
        # zaman simetrisi
        fig.add_annotation(x=bA, y=A + 2.6, text=f"AB: {bB-bA} bar", showarrow=False, font=dict(size=10, color=R["mavi"]),
                           xanchor="left", row=row, col=1)
        fig.add_shape(type="line", x0=bA, x1=bB, y0=A + 1.2, y1=A + 1.2, line=dict(color=R["mavi"], width=1.5), row=row, col=1)
        fig.add_annotation(x=bD, y=A + 2.6, text=f"CD: {bD-bC} bar · t_CD/t_AB = {(bD-bC)/(bB-bA):.2f}",
                           showarrow=False, font=dict(size=10, color=R["mavi"]), xanchor="right", row=row, col=1)
        fig.add_shape(type="line", x0=bC, x1=bD, y0=A + 1.2, y1=A + 1.2, line=dict(color=R["mavi"], width=1.5), row=row, col=1)
        fig.update_yaxes(range=[D - 2.5, A + 4.5], row=row, col=1)
        # PRZ = D ± küçük band; hedefler
        yatay(fig, D, bC, bD + 10, f"D → {D:.2f}", renk=R["prz"], w=1.6, row=row, col=1, font=10)
        yatay(fig, D + 0.382 * (C - D), bD, bD + 10, "T1 0.382", renk=R["yesil"], row=row, col=1, font=10)
        yatay(fig, D + 0.618 * (C - D), bD, bD + 10, "T2 0.618", renk=R["yesil"], row=row, col=1, font=10)
        fig.update_xaxes(row=row, col=1)
    for r_ in (1, 2, 3):
        fig.update_yaxes(title="fiyat", row=r_, col=1)
    not_kutusu(fig, "Kural: t_CD / t_AB ∈ [0.618, 1.618] kabul; simetri bozuksa yapı zayıf (Pesavento — istatistiksel doğrulaması yok)",
               x=0.5, y=-0.03, xanchor="center", yanchor="top")
    temel_layout(fig, "Şekil 05 — AB=CD ve alternatifleri: eşit, 1.272 ve 1.618 (şematik örnek)", 1200,
                 "C, AB'nin 0.618–0.786 düzeltmesi; CD, AB'nin katı; zaman simetrisi bar sayısıyla ölçülür")
    fig.update_layout(margin=dict(b=120))
    kaydet(fig, "05_abcd_varyantlar")


# ---------------------------------------------------------------- pattern şablonları
def _prz_hesapla(p, oranlar):
    """oranlar: dict(xa=r, bc=k veya None, abcd=k veya None) → {etiket: seviye}"""
    X, A, B, C = p["X"][1], p["A"][1], p["B"][1], p["C"][1]
    out = {}
    out[f"{oranlar['xa']:.3f} XA"] = lvl(A, X, oranlar["xa"])
    if oranlar.get("bc"):
        out[f"{oranlar['bc']:.3f} BC"] = C - oranlar["bc"] * (C - B)
    if oranlar.get("abcd"):
        out[f"AB=CD ×{oranlar['abcd']:.2f}"] = C - oranlar["abcd"] * (A - B)
    return out


PATTERNLER = {
    # ad: (rB, rC, dXA, bc, abcd, geçersizlik oranı(XA), açıklama)
    "Gartley": dict(rB=0.618, rC=0.786, dXA=0.786, bc=1.272, abcd=1.0, gec=1.0,
                    aciklama="B tam 0.618 (kritik) · D 0.786 XA, X aşılmaz · AB=CD eşit · PRZ dar"),
    "Bat": dict(rB=0.50, rC=0.50, dXA=0.886, bc=2.618, abcd=1.272, gec=1.0,
                aciklama="B 0.382–0.50 · D 0.886 XA (X'e çok yakın ama üstünde) → en küçük stop · BC ≥ 1.618"),
    "AltBat": dict(rB=0.382, rC=0.886, dXA=1.13, bc=3.14, abcd=None, gec=1.27,
                   aciklama="B ≤ 0.382 · 0.886 kırıldı → 1.13 XA'ya uzadı (X ihlali) · BC ≥ 2.0"),
    "Butterfly": dict(rB=0.786, rC=0.618, dXA=1.272, bc=2.0, abcd=1.272, gec=1.618,
                      aciklama="B zorunlu 0.786 · D 1.27 XA (X'in ötesi) · alt. 1.27 AB=CD ile çakışır · stop 1.618 XA"),
    "Crab": dict(rB=0.618, rC=0.618, dXA=1.618, bc=3.618, abcd=None, gec=2.0,
                 aciklama="B ≤ 0.618 · D 1.618 XA (tanımlayıcı) · BC 2.618/3.14/3.618 · en keskin dönüş, stop 2.0 XA"),
    "DeepCrab": dict(rB=0.886, rC=0.50, dXA=1.618, bc=2.618, abcd=1.272, gec=2.0,
                     aciklama="B 0.886 (derin) · D 1.618 XA · hem B hem X ihlal edilir · 1.27 AB=CD tipik"),
}


def _sablon(fig, ad, yon, row, col, seed, showlegend, ek_bc=None):
    P = PATTERNLER[ad]
    df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], yon=yon, seed=seed, son=16)
    fig.add_trace(mum_iz(df, etiketler={p[k][0]: k for k in "XABCD"}), row=row, col=col)
    prz = _prz_hesapla(p, dict(xa=P["dXA"], bc=P["bc"], abcd=P["abcd"]))
    if ek_bc:
        for k in ek_bc:
            prz[f"{k:.3f} BC"] = p["C"][1] - k * (p["C"][1] - p["B"][1])
    gec_y = lvl(p["A"][1], p["X"][1], P["gec"])
    gec_txt = f"geçersizlik {P['gec']:.3f} XA" if P["gec"] != 1.0 else "geçersizlik = X (1.0 XA)"
    xabcd_ciz(fig, p, df, P["rB"], P["rC"], P["dXA"], prz, gecersizlik=(gec_txt, gec_y), row=row, col=col,
              abcd_k=P["abcd"], bc_r=P["bc"], showlegend=showlegend)
    fig.update_xaxes(row=row, col=col)
    return df, p, prz


def g_pattern_cifti(no, ad, dosya, baslik):
    P = PATTERNLER[ad]
    # yerleşim: bullish/bearish yan yana daralıyordu → ALT ALTA (üst: bullish, alt: bearish)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=(f"Bullish {ad} (M şekli)", f"Bearish {ad} (W şekli)"))
    _sablon(fig, ad, "bull", 1, 1, seed=20 + no, showlegend=True)
    _sablon(fig, ad, "bear", 2, 1, seed=40 + no, showlegend=False)
    for r_ in (1, 2):
        fig.update_yaxes(title="fiyat", row=r_, col=1)
    not_kutusu(fig, P["aciklama"], x=0.5, y=-0.05, xanchor="center", yanchor="top")
    temel_layout(fig, f"Şekil {no:02d} — {baslik} (şematik örnek)", 860,
                 "Bacak etiketleri gerçek oranlar; PRZ = XA seviyesi + BC projeksiyonu + AB=CD yakınsaması")
    fig.update_layout(margin=dict(b=120))
    kaydet(fig, dosya)


def g08_altbat():
    # yerleşim: iki aşama yan yana daralıyordu → ALT ALTA (üst: Bat kurgusu, alt: Alt Bat)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=("Bat kurgusu: 0.886 XA'da PRZ (B = 0.382)", "0.886 kırıldı → 1.13 XA'ya uzadı: Alternate Bat"))
    # sol: B=0.382, fiyat 0.886'ya kadar; PRZ orada
    df, p = xabcd_kur(0.382, 0.886, 0.886, seed=31, son=6, sonrasi=[(4, -0.02), (7, 0.05)])
    # sağ: aynı yapı ama D 1.13
    df2, p2 = xabcd_kur(0.382, 0.886, 1.13, seed=32, son=16, nCD=24)
    fig.add_trace(mum_iz(df, etiketler={p[k][0]: k for k in "XABCD"}), row=1, col=1)
    fig.add_trace(mum_iz(df2, etiketler={p2[k][0]: k for k in "XABCD"}), row=2, col=1)
    prz1 = _prz_hesapla(p, dict(xa=0.886, bc=2.618, abcd=None))
    xabcd_ciz(fig, p, df, 0.382, 0.886, 0.886, prz1, gecersizlik=("X (1.0 XA) — Bat stop'u", lvl(p["A"][1], p["X"][1], 1.0)),
              row=1, col=1, bc_r=2.618, showlegend=True, prz_metin="Bat PRZ (0.886)")
    ok(fig, p["D"][0] + 4, df.Low.iloc[p["D"][0] + 4], "PRZ tuttu mu? Hayır →<br>fiyat X'e sarkıyor", ax=40, ay=60,
       renk=R["kirmizi"], row=1, col=1)
    prz2 = _prz_hesapla(p2, dict(xa=1.13, bc=3.14, abcd=None))
    xabcd_ciz(fig, p2, df2, 0.382, 0.886, 1.13, prz2, gecersizlik=("geçersizlik 1.272 XA", lvl(p2["A"][1], p2["X"][1], 1.272)),
              row=2, col=1, bc_r=3.14, showlegend=False, prz_metin="Alt Bat PRZ (1.13)")
    yatay(fig, lvl(p2["A"][1], p2["X"][1], 0.886), p2["C"][0], len(df2) - 1, "0.886 XA (Bat seviyesi — kırıldı)",
          renk=R["gri"], dash="dot", row=2, col=1)
    yatay(fig, p2["X"][1], p2["X"][0], len(df2) - 1, "X — ihlal edildi (Alt Bat'ta beklenir)", renk=R["lik"], dash="dash",
          row=2, col=1)
    ok(fig, p2["D"][0], p2["D"][1], "1.13 XA: Carney bunu 'whipsaw'dan<br>kaçınmak için ayrı pattern yaptı",
       ax=60, ay=60, renk=R["mavi"], row=2, col=1)
    for r_ in (1, 2):
        fig.update_yaxes(title="fiyat", row=r_, col=1)
    not_kutusu(fig, PATTERNLER["AltBat"]["aciklama"] + " · Karar: B ≤ 0.382 ise 0.886'da agresif girme, 1.13'ü de PRZ'ye kat",
               x=0.5, y=-0.05, xanchor="center", yanchor="top")
    temel_layout(fig, "Şekil 08 — Alternate Bat: Bat'in 0.886'sı kırılınca 1.13 XA'ya uzayan yapı (şematik örnek)", 860,
                 "Aynı X-A-B-C; tek fark D'nin X'i geçmesi — geçersizlik de 1.272 XA'ya kayar")
    fig.update_layout(margin=dict(b=120))
    kaydet(fig, "08_alt_bat")


def g11_deep_crab():
    # yerleşim: Crab/Deep Crab yan yana daralıyordu → ALT ALTA (üst: Crab, alt: Deep Crab)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=("Bullish Crab (B = 0.618)", "Bullish Deep Crab (B = 0.886)"))
    _sablon(fig, "Crab", "bull", 1, 1, seed=51, showlegend=True, ek_bc=[3.14])
    df, p, prz = _sablon(fig, "DeepCrab", "bull", 2, 1, seed=52, showlegend=False, ek_bc=[2.24])
    ok(fig, p["B"][0], p["B"][1], "B ihlali: düzeltme<br>0.886'ya kadar<br>(Crab'de ≤ 0.618)", ax=-75, ay=55, renk=R["lik"], row=2, col=1)
    ok(fig, p["D"][0] - 3, p["X"][1], "X ihlali: CD bacağı<br>X'i sert geçer", ax=-95, ay=60, renk=R["lik"], row=2, col=1)
    for r_ in (1, 2):
        fig.update_yaxes(title="fiyat", row=r_, col=1)
    not_kutusu(fig, "Crab: " + PATTERNLER["Crab"]["aciklama"] + "<br>Deep Crab: " + PATTERNLER["DeepCrab"]["aciklama"],
               x=0.5, y=-0.05, xanchor="center", yanchor="top")
    temel_layout(fig, "Şekil 11 — Crab ve Deep Crab alt alta: aynı 1.618 XA, farklı B (şematik örnek)", 860,
                 "İkisinde de D = 1.618 XA; BC projeksiyonu 2.24–3.618; stop 2.0 XA'nın ötesi")
    fig.update_layout(margin=dict(b=120))
    kaydet(fig, "11_crab_deep_crab")


def g12_shark_50():
    # 0=0, X=1, A=0.5, B=1.065 (1.13 XA), C=-0.065 (2.0 AB ext; 1.065 of 0X), D=0.5 (0.5 BC = reciprocal AB=CD)
    base, xa = 100.0, 20.0
    O_ = base; X_ = base + xa; A_ = base + 0.5 * xa; B_ = A_ + 1.13 * (X_ - A_); C_ = B_ - 2.0 * (B_ - A_)
    D_ = C_ + 0.5 * (B_ - C_)
    b0, bX, bA, bB, bC, bD = 8, 30, 44, 62, 88, 106
    anchors = [(0, O_ + 0.2 * xa), (b0, O_), (bX, X_), (bA, A_), (bB, B_), (bC, C_), (bD, D_), (bD + 12, D_ - 0.3 * (D_ - C_))]
    df = mumlar(anchors, seed=61)
    # yerleşim: iki yapı yan yana daralıyordu → ALT ALTA (üst: Shark, alt: 5-0)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=("Shark: 0-X-A-B-C (B, X'i geçer; C = 0.886–1.13 · 0X)",
                                        "Aynı yapı → 5-0: D = 0.50 BC ve reciprocal AB=CD"))
    d1 = df.iloc[:bC + 6]
    fig.add_trace(mum_iz(d1, etiketler={b0: "0", bX: "X", bA: "A", bB: "B", bC: "C"}), row=1, col=1)
    zigzag_iz([(b0, O_), (bX, X_), (bA, A_), (bB, B_), (bC, C_)], harfler=["0", "X", "A", "B", "C"], fig=fig, row=1, col=1)
    bacak_etiketi(fig, (bA, A_), (bB, B_), f"B = {(B_-A_)/(X_-A_):.2f} XA ext (1.13–1.618)", row=1, col=1)
    bacak_etiketi(fig, (bB, B_), (bC, C_), f"C = {(B_-C_)/(B_-A_):.2f} AB ext (1.618–2.24)<br>C = {(X_-C_)/(X_-O_):.3f} · 0X (0.886–1.13)",
                  row=1, col=1)
    prz_lo, prz_hi = lvl(X_, O_, 1.13), lvl(X_, O_, 0.886)
    kutu(fig, bB, bC + 6, prz_lo, prz_hi, R["prz"], metin=None, row=1, col=1)
    fig.add_annotation(x=bB, y=prz_hi, text="Shark PRZ:<br>0.886–1.13 · 0X", showarrow=False, xanchor="right", yanchor="bottom",
                       xshift=-4, font=dict(size=10, color=R["prz"]), row=1, col=1)
    yatay(fig, prz_hi, bB, bC + 6, "0.886 · 0X", renk=R["prz"], dash="dot", row=1, col=1, font=10, ysh=6)
    yatay(fig, prz_lo, bB, bC + 6, "1.13 · 0X", renk=R["prz"], dash="dot", row=1, col=1, font=10, ysh=-6)
    yatay(fig, B_ - 1.618 * (B_ - A_), bB, bC + 6, "1.618 AB", renk=R["prz"], dash="dot", row=1, col=1, font=10, ysh=6)
    yatay(fig, B_ - 2.24 * (B_ - A_), bB, bC + 6, "2.24 AB", renk=R["prz"], dash="dot", row=1, col=1, font=10, ysh=-6)
    yatay(fig, X_, bX, bC + 6, "X (X'i geçen B = tuzak kırılım)", renk=R["lik"], dash="dash", row=1, col=1, font=10)
    yatay(fig, prz_lo - 0.08 * xa, bB, bC + 6, "stop: 1.13 · 0X ötesi", renk=R["kirmizi"], row=1, col=1, font=10, ysh=-8)
    ok(fig, bB, B_, "B = 1.13 XA, X'in üstüne çıktı: klasik etikette<br>C'nin A'yı geçmesine denk ihlal — Shark'ta tanım", ax=-40, ay=-45, renk=R["lik"], row=1, col=1)
    # sağ: 5-0
    fig.add_trace(mum_iz(df, etiketler={b0: "0", bX: "X", bA: "A", bB: "B", bC: "C", bD: "D"}), row=2, col=1)
    zigzag_iz([(b0, O_), (bX, X_), (bA, A_), (bB, B_), (bC, C_), (bD, D_)], harfler=["0", "X", "A", "B", "C", "D"], fig=fig,
              row=2, col=1, showlegend=False)
    yatay(fig, D_, bC, bD + 12, f"0.50 BC → {D_:.2f}", renk=R["prz"], w=1.6, row=2, col=1, font=10, ysh=-8)
    kutu(fig, bC, bD + 12, D_ - 0.15, D_ + 0.15, R["prz"], metin="5-0 PRZ", konum="top", row=2, col=1)
    # reciprocal AB=CD: AB uzunluğu C'den yukarı
    fig.add_annotation(x=bB, y=B_, ax=bA, ay=A_, xref="x2", yref="y2", axref="x2", ayref="y2", showarrow=True, arrowhead=3,
                       arrowwidth=2, arrowcolor=R["lik"], text="")
    fig.add_annotation(x=bC + 4, y=C_ + (B_ - A_), ax=bC + 4, ay=C_, xref="x2", yref="y2", axref="x2", ayref="y2", showarrow=True,
                       arrowhead=3, arrowwidth=2, arrowcolor=R["lik"], text="")
    fig.add_annotation(x=bD + 12, y=C_ + (B_ - A_), text=f"reciprocal AB=CD (C+|AB|) → {C_ + (B_-A_):.2f}", showarrow=False,
                       xanchor="left", xshift=4, yshift=12, font=dict(size=10, color=R["lik"]), row=2, col=1)
    yatay(fig, C_ - 0.06 * xa, bC, bD + 12, "stop: C'nin altı", renk=R["kirmizi"], row=2, col=1, font=10)
    yatay(fig, C_ + 0.382 * (D_ - C_), bD, bD + 12, "hedef alt: 0.382 CD", renk=R["yesil"], row=2, col=1, font=10)
    ok(fig, bD, D_, "5-0'da PRZ trendin ilk geri çekilmesidir;<br>işlem yönü: C→D bacağına KARŞI (burada short)",
       ax=-150, ay=-95, renk=R["dn"], row=2, col=1)
    for r_ in (1, 2):
        fig.update_yaxes(title="fiyat", row=r_, col=1)
    fig.update_xaxes(range=[0, bC + 34], row=1, col=1); fig.update_xaxes(range=[0, bD + 62], row=2, col=1)
    not_kutusu(fig, "Shark (Carney 2011): 0X/XA için oran verilmez; B = XA'nın 1.13–1.618 ext (X'i geçer, ≤ 1.618); C = AB'nin 1.618–2.24 ext ve 0X'in 0.886–1.13'ü"
                    "<br>5-0 (Carney 2007): Shark'ın C'sinden sonra D = BC'nin 0.50 düzeltmesi; CD = AB (reciprocal). Klasik M/W çerçevesinin dışındadır.",
               x=0.5, y=-0.05, xanchor="center", yanchor="top")
    temel_layout(fig, "Şekil 12 — Shark ve 5-0: klasik XABCD dışındaki iki yapı (şematik örnek)", 900,
                 "Üstte: Shark PRZ'si C'de. Altta: aynı yapının devamı — 5-0 tamamlanışı D'de")
    fig.update_layout(margin=dict(b=130))
    kaydet(fig, "12_shark_5_0")


def g13_cypher():
    base, xa = 100.0, 20.0
    X_ = base; A_ = X_ + xa; B_ = lvl(A_, X_, 0.5); C_ = X_ + 1.272 * xa; D_ = C_ - 0.786 * (C_ - X_)
    bX, bA, bB, bC, bD = 10, 34, 50, 74, 100
    anchors = [(0, X_ + 0.3 * xa), (bX, X_), (bA, A_), (bB, B_), (bC, C_), (bD, D_), (bD + 14, D_ + 0.5 * (C_ - D_))]
    df = mumlar(anchors, seed=71)
    fig = go.Figure(mum_iz(df, etiketler={bX: "X", bA: "A", bB: "B", bC: "C", bD: "D"}))
    pts = [(bX, X_), (bA, A_), (bB, B_), (bC, C_), (bD, D_)]
    zigzag_iz(pts, harfler=["X", "A", "B", "C", "D"], fig=fig)
    bacak_etiketi(fig, pts[1], pts[2], "B = 0.500 XA (0.382–0.618)")
    bacak_etiketi(fig, pts[2], pts[3], "C = 1.272 XA ext (1.272–1.414)<br>C, A'nın ÜSTÜNDE")
    bacak_etiketi(fig, pts[3], pts[4], "D = 0.786 XC")
    # XC fib
    x1 = bD + 14
    for r in (0.382, 0.5, 0.618, 0.786):
        y = C_ - r * (C_ - X_)
        yatay(fig, y, bC, x1, f"{r:.3f} XC → {y:.2f}", renk=R["up"] if r == 0.786 else R["fib"], w=2.2 if r == 0.786 else 1)
    kutu(fig, bC, x1, D_ - 0.02 * xa, D_ + 0.03 * xa, R["prz"], metin="Cypher PRZ (0.786 XC)", konum="top")
    yatay(fig, X_ - 0.04 * xa, bX, x1, "stop: X'in ötesi", renk=R["kirmizi"])
    yatay(fig, A_, bA, x1, "A (klasik pattern'de C burayı geçemezdi)", renk=R["lik"], dash="dot")
    # XA'dan yanlış çizim uyarısı
    y_yanlis = lvl(A_, X_, 0.786)
    yatay(fig, y_yanlis, bC, x1, "0.786 XA — YANLIŞ referans (Cypher XC'den ölçülür)", renk=R["gri"], dash="dashdot")
    fig.add_annotation(x=bC, y=C_, ax=bX, ay=X_, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3,
                       arrowwidth=2, arrowcolor=R["up"], text="", opacity=0.6)
    ok(fig, bX + 0.3 * (bC - bX), X_ + 0.3 * (C_ - X_), "Fib aracı X→C çekilir (XA değil)", ax=-10, ay=-110, renk=R["up"])
    ok(fig, bC, C_, "C, A'yı geçti = tuzak kırılım (failed breakout);<br>kırılım alıcılarının stop'ları D'yi besler", ax=90, ay=-40, renk=R["lik"])
    for r, t in ((0.382, "T1"), (0.618, "T2")):
        yatay(fig, D_ + r * (C_ - D_), bD, x1, f"{t} = {r} CD", renk=R["yesil"], font=10, ysh=9)
    fig.update_xaxes(range=[0, x1 + 42])
    temel_layout(fig, "Şekil 13 — Cypher: C, A'yı geçer; D, XA'dan değil XC'den ölçülür (şematik örnek)", 580,
                 "Darren Oglesbee (topluluk) — Carney kataloğunda yoktur; kural: B 0.382–0.618 XA, C 1.272–1.414 XA, D 0.786 XC")
    fig.update_yaxes(title="fiyat")
    kaydet(fig, "13_cypher")


def g14_three_drives():
    P0 = 120.0
    d1 = P0 - 16.0                        # drive 1
    cA = d1 + 0.618 * (P0 - d1)           # düzeltme A
    d2 = cA - 1.272 * (cA - d1)           # drive 2 = 1.272 · düzeltme A
    cB = d2 + 0.618 * (cA - d2)           # düzeltme B
    d3 = cB - 1.272 * (cB - d2)           # drive 3
    b = [4, 22, 34, 52, 64, 82]
    anchors = [(0, P0 - 3), (b[0], P0), (b[1], d1), (b[2], cA), (b[3], d2), (b[4], cB), (b[5], d3), (b[5] + 16, d3 + 0.7 * (cB - d3))]
    df = mumlar(anchors, seed=81)
    fig = go.Figure(mum_iz(df, etiketler={b[1]: "Drive 1", b[3]: "Drive 2", b[5]: "Drive 3", b[2]: "Düzeltme A", b[4]: "Düzeltme B"}))
    pts = [(b[0], P0), (b[1], d1), (b[2], cA), (b[3], d2), (b[4], cB), (b[5], d3)]
    zigzag_iz(pts, harfler=["", "1", "A", "2", "B", "3"], fig=fig, ad="Three Drives")
    bacak_etiketi(fig, pts[1], pts[2], "düzeltme A = 0.618 · drive 1")
    bacak_etiketi(fig, pts[2], pts[3], "drive 2 = 1.272 · düzeltme A")
    bacak_etiketi(fig, pts[3], pts[4], "düzeltme B = 0.618 · drive 2")
    bacak_etiketi(fig, pts[4], pts[5], "drive 3 = 1.272 · düzeltme B")
    x1 = b[5] + 16
    yatay(fig, d3, b[4], x1, f"1.272 proj → {d3:.2f}", renk=R["prz"], w=1.6)
    yatay(fig, cB - 1.618 * (cB - d2), b[4], x1, f"1.618 proj → {cB - 1.618*(cB-d2):.2f} (alternatif)", renk=R["prz"], dash="dot")
    kutu(fig, b[4], x1, d3 - 0.6, d3 + 0.4, R["prz"], metin="PRZ (drive 3)", konum="bottom")
    # zaman simetrisi
    for (i, j, t) in [(b[1], b[3], f"drive1→2: {b[3]-b[1]} bar"), (b[3], b[5], f"drive2→3: {b[5]-b[3]} bar")]:
        fig.add_shape(type="line", x0=i, x1=j, y0=P0 + 1.5, y1=P0 + 1.5, line=dict(color=R["mavi"], width=1.5))
        fig.add_annotation(x=(i + j) / 2, y=P0 + 2.4, text=t, showarrow=False, font=dict(size=10, color=R["mavi"]))
    yatay(fig, d3 - 1.0, b[5], x1, "stop: drive 3'ün altı", renk=R["kirmizi"])
    yatay(fig, d3 + 0.618 * (cB - d3), b[5], x1, "hedef 1: 0.618 · son bacak", renk=R["yesil"], font=10)
    yatay(fig, cA, b[5], x1, "hedef 2: düzeltme A tepesi", renk=R["yesil"], font=10)
    ok(fig, b[5], d3, "Üçüncü sürüş: hacim/momentum genelde zayıflar;<br>simetri (fiyat + zaman) bozuksa yapı zayıf", ax=70, ay=60, renk=R["ink"])
    temel_layout(fig, "Şekil 14 — Three Drives: üç simetrik sürüş, 0.618 düzeltme, 1.272 projeksiyon (şematik örnek)", 560,
                 "Prechter → Pesavento/Carney; drive'lar 1.13/1.27/1.618 kabul; düzeltmeler 0.618 (0.786 tolere)")
    fig.update_yaxes(title="fiyat")
    kaydet(fig, "14_three_drives")


def g15_hiyerarsi():
    df, p = _xa_ornek(seed=91)
    n = p["A"][0] + 3
    df = df.iloc[:n + 1]
    X, A = p["X"], p["A"]
    x1 = n + 40
    fig = go.Figure(mum_iz(df, etiketler={X[0]: "X", A[0]: "A"}))
    zigzag_iz([X, A], harfler=["X", "A"], fig=fig, ad="XA impulsu")
    yatay(fig, A[1], X[0], x1, "A (0.0)", renk=R["gri"], dash="solid")
    yatay(fig, X[1], X[0], x1, "X (1.0) — retracement / extension sınırı", renk=R["kirmizi"], dash="solid", w=1.6)
    # B seviyeleri (sol yarı)
    xm = n + 18
    kutu(fig, n + 1, xm, lvl(A[1], X[1], 0.30), lvl(A[1], X[1], 0.95), R["mavi"], alfa=0.05, metin="B nerede durdu?", konum="top")
    for r, t in [(0.382, "0.382 → Bat / Alt Bat"), (0.5, "0.500 → Bat"), (0.618, "0.618 → Gartley / Crab"),
                 (0.786, "0.786 → Butterfly"), (0.886, "0.886 → Deep Crab")]:
        y = lvl(A[1], X[1], r)
        fig.add_shape(type="line", x0=n + 1, x1=xm, y0=y, y1=y, line=dict(color=R["mavi"], width=1.5, dash="dash"))
        fig.add_annotation(x=n + 2, y=y, text=t, showarrow=False, xanchor="left", yshift=8, font=dict(size=10.5, color=R["mavi"]))
    # D seviyeleri (sağ yarı)
    kutu(fig, xm + 2, x1, lvl(A[1], X[1], 0.75), lvl(A[1], X[1], 1.70), R["prz"], alfa=0.05, metin="D nerede tamamlanır?", konum="top")
    for r, t, renk in [(0.786, "0.786 XA → Gartley (retracement)", R["prz"]), (0.886, "0.886 XA → Bat (retracement)", R["prz"]),
                       (1.13, "1.13 XA → Alt Bat (extension)", R["dn"]), (1.272, "1.272 XA → Butterfly (extension)", R["dn"]),
                       (1.618, "1.618 XA → Crab / Deep Crab (extension)", R["dn"])]:
        y = lvl(A[1], X[1], r)
        fig.add_shape(type="line", x0=xm + 2, x1=x1, y0=y, y1=y, line=dict(color=renk, width=1.8, dash="dash"))
        fig.add_annotation(x=xm + 3, y=y, text=t, showarrow=False, xanchor="left", yshift=8, font=dict(size=10.5, color=renk))
    kutu(fig, xm + 2, x1, lvl(A[1], X[1], 1.0), lvl(A[1], X[1], 1.70), R["lik"], alfa=0.06,
         metin="X'in ötesi: extension pattern'leri —<br>X altındaki likidite süpürülür", konum="mid", metin_renk=R["lik"])
    not_kutusu(fig, "Ayrım kuralları (Carney): B=0.618→Gartley (D 0.786) · B≤0.50→Bat (D 0.886) · B≤0.382 & 0.886 kırıldı→Alt Bat (1.13)"
                    "<br>B=0.786→Butterfly (D 1.27) · B≤0.618 & BC≥2.618→Crab (1.618) · B=0.886→Deep Crab (1.618)"
                    "<br>Retracement pattern'leri (D<X): sık, sığ dönüş · Extension pattern'leri (D>X): nadir, sert dönüş",
               x=0.99, y=0.98, xanchor="right", yanchor="top", font=10.5)
    temel_layout(fig, "Şekil 15 — Tek bakışta hiyerarşi: aynı XA üzerinde tüm B ve D seviyeleri (şematik örnek)", 620,
                 "Sol bant: B'nin durduğu yer pattern'i sınıflandırır · Sağ bant: D'nin beklenen yeri")
    fig.update_yaxes(title="fiyat", range=[lvl(A[1], X[1], 1.78), A[1] + 2.5]); fig.update_xaxes(range=[0, x1 + 14])
    kaydet(fig, "15_hiyerarsi_ayrim")


def g16_prz_insa():
    P = PATTERNLER["Gartley"]
    df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=101, son=6)
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    n = C[0] + 2
    # yerleşim: üç adım yan yana daralıyordu → ALT ALTA (okuma sırası ①→②→③)
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.06,
                        subplot_titles=("① XA seviyesi: 0.786 XA", "② + BC projeksiyonu: 1.272 BC", "③ + AB=CD → PRZ bandı"))
    x1 = D[0] + 7
    l_xa = lvl(A[1], X[1], 0.786); l_bc = C[1] - 1.272 * (C[1] - B[1]); l_cd = C[1] - 1.0 * (A[1] - B[1])
    for row in (1, 2, 3):
        d_ = df.iloc[:n + 1] if row < 3 else df
        fig.add_trace(mum_iz(d_, etiketler={p[k][0]: k for k in "XABCD"}), row=row, col=1)
        pts = [X, A, B, C] if row < 3 else [X, A, B, C, D]
        zigzag_iz(pts, harfler=list("XABCD")[:len(pts)], fig=fig, row=row, col=1, showlegend=(row == 1))
        yatay(fig, l_xa, X[0], x1, f"0.786 XA<br>{l_xa:.2f}", renk=R["prz"], w=2.4, dash="solid", row=row, col=1, font=10,
              ysh=-14 if row > 1 else 0)
        yatay(fig, X[1], X[0], x1, "X (stop ref.)", renk=R["kirmizi"], row=row, col=1, font=10)
        if row >= 2:
            yatay(fig, l_bc, C[0], x1, f"1.272 BC<br>{l_bc:.2f}", renk=R["mavi"], w=1.8, row=row, col=1, font=10, ysh=14)
            fig.add_annotation(x=C[0], y=C[1], ax=B[0], ay=B[1], xref=f"x{row}", yref=f"y{row}", axref=f"x{row}", ayref=f"y{row}",
                               showarrow=True, arrowhead=3, arrowwidth=2, arrowcolor=R["mavi"], text="")
        if row == 3:
            yatay(fig, l_cd, C[0], x1, f"AB=CD ×1.0<br>{l_cd:.2f}", renk=R["lik"], w=1.5, dash="dot", row=row, col=1, font=10, ysh=40)
            fig.add_annotation(x=B[0], y=B[1], ax=A[0], ay=A[1], xref="x3", yref="y3", axref="x3", ayref="y3",
                               showarrow=True, arrowhead=3, arrowwidth=2, arrowcolor=R["lik"], text="")
            lo, hi = min(l_xa, l_bc, l_cd), max(l_xa, l_bc, l_cd)
            kutu(fig, C[0], x1, lo, hi, R["prz"], alfa=0.22, metin=None, row=3, col=1)
            not_kutusu(fig, f"PRZ = {lo:.2f}–{hi:.2f}<br>genişlik {100*(hi-lo)/(A[1]-X[1]):.1f}% XA → sıkı", x=0.04, y=0.05,
                       xanchor="left", yanchor="bottom", renk=R["prz"], row=3, col=1, font=10.5)
            ok(fig, D[0], D[1], "D: PRZ'nin<br>tümünü test etti", ax=-40, ay=60, renk=R["prz"], row=3, col=1)
        fig.update_xaxes(range=[0, x1 + 16], row=row, col=1)
    # dikey yerleşimde shared_yaxes yerine matches: üç panel aynı fiyat ölçeğinde kalır
    for r_ in (1, 2, 3):
        fig.update_yaxes(title="fiyat", row=r_, col=1)
    for r_ in (2, 3):
        fig.update_yaxes(matches="y", row=r_, col=1)
    not_kutusu(fig, "PRZ = [min(D_i), max(D_i)] — üç bağımsız hesap aynı banda düşüyorsa 'yakınsama'. Sıkı: ≤ %3–5 XA · Geniş: > %8 XA."
                    "<br>1.618 BC alınsaydı seviye çok aşağıda kalırdı → BC oranı seçimi PRZ'yi belirler; iki hesabın çakıştığı yer esas alınır.",
               x=0.5, y=-0.034, xanchor="center", yanchor="top")
    temel_layout(fig, "Şekil 16 — PRZ inşası adım adım: XA seviyesi + BC projeksiyonu + AB=CD yakınsaması (şematik örnek, Gartley)", 1200,
                 "PRZ tek çizgi değil, bir bölgedir; sol kenar C'nin zamanı")
    kaydet(fig, "16_prz_insa")


# ---------------------------------------------------------------- yönetim serisi (ortak Bat kurgusu)
def _yonetim_seri(seed=201, senaryo="tip2"):
    """Bullish Bat; D sonrası: T-bar (PRZ'nin altına fitil), dönüş, T1'e tepki, PRZ retest (HL), T2, A."""
    P = PATTERNLER["Bat"]
    df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=seed, son=0)
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    AD = A[1] - D[1]
    if senaryo == "tip1":
        sonrasi = [(0, 0), (1, -0.02), (10, 0.40), (18, 0.10), (26, 0.34), (36, 0.62)]
    else:
        sonrasi = [(0, 0), (1, -0.02), (10, 0.40), (19, 0.03), (30, 0.66), (40, 0.55), (52, 1.02)]
    anchors = [(0, df.Close.iloc[0])]
    # yeniden kur: xabcd_kur ile aynı anchor mantığı, D sonrası eklerle
    df2, p2 = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=seed, sonrasi=[(o if o > 0 else 1, k) for o, k in sonrasi[1:]])
    return df2, p2


def g17_prz_teyit_rsi():
    # CD bacağını iki aşamalı kurgula: sert düşüş → küçük toparlanma → yavaş yeni dip (D) → RSI uyumsuzluğu
    P = PATTERNLER["Bat"]
    X, xa = 100.0, 20.0
    A = X + xa; B = lvl(A, X, 0.5); C = B + 0.5 * (A - B); D = lvl(A, X, 0.886)
    D0 = D + 0.9
    bX, bA, bB, bC = 12, 40, 56, 68
    bD0, bD = 74, 101
    # CD bacağı: sert ilk düşüş (D0) → dalgalı, yavaş yeni dip (D) → RSI uyumsuzluğu
    anchors = [(0, X + 2.5), (5, X - 7), (bX, X), (bA, A), (bB, B), (bC, C), (bD0, D0), (81, D0 + 5.2), (85, D0 + 2.6),
               (89, D0 + 4.2), (93, D0 + 1.2), (96, D0 + 2.4), (bD, D),
               (bD + 1, D - 0.3), (bD + 12, D + 0.40 * (A - D)), (bD + 20, D + 0.55 * (A - D))]
    df = mumlar(anchors, seed=111, gurultu=0.10)
    # T-bar: D barı PRZ altına fitil, kapanış PRZ içinde; ertesi bar engulfing yükseliş
    prz = {"0.886 XA": lvl(A, X, 0.886), "2.618 BC": C - 2.618 * (C - B), "AB=CD ×1.27": C - 1.272 * (A - B)}
    lo, hi = min(prz.values()), max(prz.values())
    df.loc[bD, "Low"] = lo - 0.25; df.loc[bD, "Close"] = lo + 0.35; df.loc[bD, "Open"] = hi + 0.1
    df.loc[bD + 1, "Open"] = lo + 0.3; df.loc[bD + 1, "Close"] = hi + 0.9; df.loc[bD + 1, "High"] = hi + 1.1; df.loc[bD + 1, "Low"] = lo + 0.05
    r = rsi(df.Close.values); r[:14] = np.nan  # ısınma dönemi gösterilmez
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.04)
    fig.add_trace(mum_iz(df, etiketler={bX: "X", bA: "A", bB: "B", bC: "C", bD0: "ilk dip", bD: "D / T-bar", bD + 1: "dönüş mumu (engulfing)"}), row=1, col=1)
    zigzag_iz([(bX, X), (bA, A), (bB, B), (bC, C), (bD, D)], harfler=list("XABCD"), fig=fig, row=1, col=1)
    x1 = len(df) - 1
    kutu(fig, bC, x1, lo, hi, R["prz"], metin="PRZ", konum="top", row=1, col=1)
    prz_cizgileri(fig, prz, bC, x1, row=1, col=1)
    yatay(fig, X, bX, x1, "X — geçersizlik", renk=R["kirmizi"], row=1, col=1, font=10, ysh=-30)
    a14 = atr(df)[bD]
    stop = df.Low.iloc[bD] - 0.5 * a14
    yatay(fig, stop, bD - 2, x1, f"stop = T-bar dibi − 0.5·ATR → {stop:.2f}", renk=R["kirmizi"], dash="dash", w=1.6, row=1, col=1, font=10, ysh=-17)
    giris = df.Close.iloc[bD + 1]
    yatay(fig, giris, bD + 1, x1, f"giriş: dönüş mumu kapanışı → {giris:.2f}", renk=R["up"], dash="solid", w=1.6, row=1, col=1, font=10, ysh=18)
    fig.update_xaxes(range=[0, x1 + 40])
    ok(fig, bD, df.Low.iloc[bD], "T-bar: PRZ'nin TÜM sayılarını test etti,<br>fitil altta, kapanış PRZ içinde", ax=-90, ay=55, renk=R["prz"], row=1, col=1)
    ok(fig, bD + 1, df.Close.iloc[bD + 1], "teyit ①: yükseliş engulfing", ax=70, ay=-30, renk=R["up"], row=1, col=1)
    # RSI
    fig.add_trace(go.Scatter(x=list(range(len(df))), y=r, mode="lines", name="RSI(14)", line=dict(color=R["fvg"], width=1.6)), row=2, col=1)
    fig.add_hline(y=30, line=dict(color=R["gri"], dash="dot"), row=2, col=1)
    fig.add_hline(y=70, line=dict(color=R["gri"], dash="dot"), row=2, col=1)
    fig.add_trace(go.Scatter(x=[bD0, bD], y=[r[bD0], r[bD]], mode="lines+markers", name="RSI uyumsuzluğu",
                             line=dict(color=R["lik"], width=2.5), marker=dict(size=8, color=R["lik"])), row=2, col=1)
    fig.add_trace(go.Scatter(x=[bD0, bD], y=[df.Low.iloc[bD0], df.Low.iloc[bD]], mode="lines", name="fiyat: daha düşük dip",
                             line=dict(color=R["lik"], width=2.5, dash="dot"), showlegend=False), row=1, col=1)
    ok(fig, bD, r[bD], f"teyit ②: fiyat daha düşük dip ({df.Low.iloc[bD]:.2f} < {df.Low.iloc[bD0]:.2f}),<br>RSI daha yüksek dip ({r[bD]:.0f} > {r[bD0]:.0f}) → momentum tükeniyor",
       ax=-40, ay=-45, renk=R["lik"], row=2, col=1)
    fig.update_yaxes(title="fiyat", row=1, col=1); fig.update_yaxes(title="RSI", range=[0, 100], row=2, col=1)
    fig.update_xaxes(row=2, col=1)
    not_kutusu(fig, "Karar ağacı: PRZ'ye girdi → T-bar tümünü test etti mi? → kapanış PRZ içinde mi? → teyit (dönüş mumu / LTF CHoCH / RSI uyumsuzluğu) → GİRİŞ<br>"
                    "Onaysız 'D'ye geldi diye' girmek en yaygın hata; stop PRZ'nin İÇİNE konmaz (T-bar süpürür).",
               x=0.5, y=-0.11, xanchor="center", yanchor="top")
    temel_layout(fig, "Şekil 17 — PRZ'de teyit: T-bar, dönüş mumu ve RSI uyumsuzluğu (şematik örnek, bullish Bat)", 680)
    fig.update_layout(margin=dict(b=120))
    kaydet(fig, "17_prz_teyit_rsi")


def g18_giris_stop_hedef():
    df, p = _yonetim_seri(seed=121, senaryo="tip2")
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    prz = _prz_hesapla(p, dict(xa=0.886, bc=2.618, abcd=1.272))
    lo, hi = min(prz.values()), max(prz.values())
    n = D[0] + 3
    df = df.iloc[:n + 1]
    x1 = n + 22
    fig = go.Figure(mum_iz(df, etiketler={p[k][0]: k for k in "XABCD"}))
    zigzag_iz([X, A, B, C, D], harfler=list("XABCD"), fig=fig)
    kutu(fig, C[0], x1, lo, hi, R["prz"], metin="PRZ", konum="bottom")
    prz_cizgileri(fig, prz, C[0], x1)
    giris = (lo + hi) / 2 + 0.6
    stop = X[1] - 0.6
    AD = A[1] - giris
    T1 = giris + 0.382 * (A[1] - D[1]); T2 = giris + 0.618 * (A[1] - D[1]); T3 = A[1]
    # T1/T2 D'den ölçülür: T = D + r·(A−D)
    T1 = D[1] + 0.382 * (A[1] - D[1]); T2 = D[1] + 0.618 * (A[1] - D[1])
    x_k0, x_k1 = D[0] + 4, x1
    rr_kutulari(fig, x_k0, x_k1, giris, stop, T1, metin_h=f"T1 = 0.382 AD → {T1:.2f}", metin_s=f"SL = X − tampon → {stop:.2f}")
    kutu(fig, x_k0, x_k1, T1, T2, R["yesil"], alfa=0.08, metin=f"T2 = 0.618 AD → {T2:.2f}   R:R {(T2-giris)/(giris-stop):.1f}", konum="top", metin_renk=R["yesil"])
    kutu(fig, x_k0, x_k1, T2, T3, R["yesil"], alfa=0.04, metin=f"T3 = A → {T3:.2f}   R:R {(T3-giris)/(giris-stop):.1f}", konum="top", metin_renk=R["yesil"])
    yatay(fig, giris, x_k0, x_k1, f"giriş → {giris:.2f}", renk=R["up"], dash="solid", w=1.8, konum="left", ysh=13)
    yatay(fig, C[1], x_k0, x_k1, f"ara hedef: C → {C[1]:.2f}", renk=R["gri"], dash="dot", font=10)
    yatay(fig, B[1], x_k0, x_k1, f"ara hedef: B → {B[1]:.2f}", renk=R["gri"], dash="dot", font=10)
    fig.add_annotation(x=x_k0, y=A[1], ax=x_k0, ay=D[1], xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3,
                       arrowwidth=1.5, arrowcolor=R["ink"], text="")
    fig.add_annotation(x=x_k0, y=(A[1] + D[1]) / 2, text="AD bacağı<br>(hedef ölçüsü)", showarrow=False, xanchor="right", xshift=-4,
                       font=dict(size=10, color=R["ink"]))
    risk = giris - stop
    not_kutusu(fig, f"Sayılar: giriş {giris:.2f} · stop {stop:.2f} · risk {risk:.2f}<br>"
                    f"T1 = D + 0.382·(A−D) = {T1:.2f} → R:R {(T1-giris)/risk:.1f}<br>"
                    f"T2 = D + 0.618·(A−D) = {T2:.2f} → R:R {(T2-giris)/risk:.1f}<br>"
                    f"T3 = A = {T3:.2f} → R:R {(T3-giris)/risk:.1f}<br>"
                    "Bulkowski (bull, 'mükemmel' Bat): B'ye ulaşma %98 civarı, C'ye ~%59, A'ya %58 →<br>hedefler bu olasılık merdivenine göre kademelenir",
               x=0.01, y=0.98, xanchor="left", yanchor="top", font=10.5)
    temel_layout(fig, "Şekil 18 — Giriş / stop / hedef kutuları: T1 = 0.382 AD, T2 = 0.618 AD, T3 = A; stop X'in ötesi (şematik örnek, Bat)", 620,
                 "Yeşil kutu = ödül, kırmızı kutu = risk; R:R işlem açılmadan ÖNCE bilinir — harmoniklerin asıl faydası bu")
    fig.update_yaxes(title="fiyat", range=[stop - 1.5, A[1] + 8]); fig.update_xaxes(range=[0, x1 + 16])
    kaydet(fig, "18_giris_stop_hedef")


def g19_giris_turleri():
    df, p = _yonetim_seri(seed=131, senaryo="tip2")
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    prz = _prz_hesapla(p, dict(xa=0.886, bc=2.618, abcd=1.272))
    lo, hi = min(prz.values()), max(prz.values())
    # T-bar ve engulfing kurgusu
    df.loc[D[0], "Low"] = lo - 0.2; df.loc[D[0], "Close"] = lo + 0.3; df.loc[D[0], "Open"] = hi + 0.2
    df.loc[D[0] + 1, "Open"] = lo + 0.25; df.loc[D[0] + 1, "Close"] = hi + 0.8; df.loc[D[0] + 1, "High"] = hi + 1.0; df.loc[D[0] + 1, "Low"] = lo + 0.05
    n = D[0] + 22
    d_ = df.iloc[:n + 1]
    x1 = n + 4
    fig = go.Figure(mum_iz(d_, etiketler={p[k][0]: k for k in "XABCD"} | {D[0]: "T-bar", D[0] + 1: "engulfing"}))
    zigzag_iz([X, A, B, C, D], harfler=list("XABCD"), fig=fig)
    kutu(fig, C[0], x1, lo, hi, R["prz"], metin="PRZ", konum="bottom")
    prz_cizgileri(fig, prz, C[0], x1)
    orta = (lo + hi) / 2
    # 1) limit
    fig.add_trace(go.Scatter(x=[D[0] - 3], y=[orta], mode="markers", marker=dict(symbol="triangle-right", size=14, color=R["mavi"]),
                             name="limit giriş"))
    ok(fig, D[0] - 3, orta, "① Limit (blind) giriş: PRZ ortası,<br>emir önceden bekler", ax=-40, ay=-60, renk=R["mavi"])
    yatay(fig, orta, D[0] - 3, x1, f"limit → {orta:.2f}", renk=R["mavi"], dash="dash", font=10, ysh=27)
    # 2) teyitli
    e2 = df.Close.iloc[D[0] + 1]
    fig.add_trace(go.Scatter(x=[D[0] + 1], y=[e2], mode="markers", marker=dict(symbol="triangle-up", size=14, color=R["up"]),
                             name="teyitli giriş"))
    ok(fig, D[0] + 1, e2, f"② Teyitli piyasa girişi: engulfing kapanışı → {e2:.2f}<br>(varsayılan yöntem)", ax=90, ay=-50, renk=R["up"])
    # 3) ölçekli
    e3a = hi
    fig.add_trace(go.Scatter(x=[D[0] - 1, D[0] + 1], y=[e3a, e2], mode="markers", marker=dict(symbol="triangle-up-open", size=12, color=R["lik"], line=dict(width=2)),
                             name="ölçekli giriş (%40 + %60)"))
    ort = 0.4 * e3a + 0.6 * e2
    yatay(fig, ort, D[0] - 1, x1, f"③ ölçekli: %40@{e3a:.2f} + %60@{e2:.2f} → ort. {ort:.2f}", renk=R["lik"], dash="dashdot", font=10, ysh=41)
    # 4) Type II retest
    seg = df.iloc[D[0] + 8:n + 1]
    ri = int(seg.Low.idxmin())
    fig.add_trace(go.Scatter(x=[ri], y=[df.Low.iloc[ri]], mode="markers", marker=dict(symbol="triangle-up", size=14, color=R["fvg"]), name="Type II retest girişi"))
    ok(fig, ri, df.Low.iloc[ri], "④ Type II retest girişi: ilk tepkiden sonra PRZ'ye<br>ikinci dokunuş (higher low) → en dar stop", ax=-10, ay=-90, renk=R["fvg"])
    stop = df.Low.iloc[D[0]] - 0.5 * atr(df)[D[0]]
    yatay(fig, stop, D[0] - 3, x1, f"ortak stop: T-bar dibi − 0.5·ATR → {stop:.2f}", renk=R["kirmizi"], w=1.6, font=10, ysh=-14)
    yatay(fig, X[1], X[0], x1, "X", renk=R["gri"], dash="dot", font=10)
    not_kutusu(fig, "Limit: sadece sıkı PRZ + HTF konfluens + trend yönünde (Carney'nin erken uygulaması) · Teyitli: varsayılan<br>"
                    "Ölçekli: PRZ genişse; ortalama giriş PRZ ortasına yakın · Type II: retest mumunun kapanışıyla, en yüksek R:R<br>"
                    "Kural: giriş türü ne olursa olsun stop PRZ'nin içinde olamaz; büyüklük = risk / (E − S)",
               x=0.01, y=0.98, xanchor="left", yanchor="top", font=10.5)
    temel_layout(fig, "Şekil 19 — Dört giriş türü aynı PRZ üzerinde: limit, teyitli, ölçekli, Type II retest (şematik örnek)", 640, lejant=True)
    fig.update_yaxes(title="fiyat", range=[stop - 1.5, C[1] + 1.5]); fig.update_xaxes(range=[B[0] - 4, x1 + 34])
    kaydet(fig, "19_giris_turleri")


def g20_stop_yerlesimi():
    # yerleşim: 2x2 ızgarada paneller daralıyordu → ALT ALTA (satır satır okuma sırası:
    # Gartley → Bat → Butterfly → Crab)
    fig = make_subplots(rows=4, cols=1, vertical_spacing=0.06,
                        subplot_titles=("Gartley — geçersizlik: X (1.0 XA); dar seçenek 0.886 XA", "Bat — geçersizlik: X (1.0 XA) → en dar stop",
                                        "Butterfly — geçersizlik: 1.618 XA", "Crab — geçersizlik: 2.0 XA"))
    conf = [("Gartley", 1, 1, 1.0), ("Bat", 2, 1, 1.0), ("Butterfly", 3, 1, 1.618), ("Crab", 4, 1, 2.0)]
    ozet = []
    for k, (ad, row, col, gec) in enumerate(conf):
        P = PATTERNLER[ad]
        df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=141 + k, son=14)
        X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
        fig.add_trace(mum_iz(df, etiketler={p[q][0]: q for q in "XABCD"}), row=row, col=col)
        zigzag_iz([X, A, B, C, D], harfler=list("XABCD"), fig=fig, row=row, col=col, showlegend=(k == 0))
        prz = _prz_hesapla(p, dict(xa=P["dXA"], bc=P["bc"], abcd=P["abcd"]))
        lo, hi = min(prz.values()), max(prz.values())
        x1 = len(df) - 1
        kutu(fig, C[0], x1, lo, hi, R["prz"], metin="PRZ", konum="bottom", row=row, col=col)
        gy = lvl(A[1], X[1], gec)
        a14 = atr(df)[D[0]]
        stop = gy - 0.75 * a14
        giris = D[1] + 0.03 * (A[1] - X[1])
        T1 = D[1] + 0.382 * (A[1] - D[1]); T2 = D[1] + 0.618 * (A[1] - D[1])
        yatay(fig, gy, X[0], x1, f"geçersizlik {gec:.3f} XA → {gy:.2f}", renk=R["kirmizi"], dash="dash", row=row, col=col, font=10)
        yatay(fig, stop, X[0], x1, f"stop = geçersizlik − 0.75·ATR → {stop:.2f}", renk=R["kirmizi"], dash="solid", w=1.6, row=row, col=col, font=10)
        rr_kutulari(fig, D[0] + 2, x1, giris, stop, T1, metin_h=f"T1 {T1:.2f}", metin_s="", row=row, col=col)
        yatay(fig, T2, D[0] + 2, x1, f"T2 {T2:.2f}  R:R {(T2-giris)/(giris-stop):.1f}", renk=R["yesil"], dash="dot", row=row, col=col, font=10)
        yatay(fig, giris, D[0] + 2, x1, f"E {giris:.2f}", renk=R["up"], dash="solid", row=row, col=col, font=10, konum="left", ysh=9)
        if ad in ("Butterfly", "Crab"):
            yatay(fig, X[1], X[0], x1, "X — burada stop YANLIŞ (zaten aşılır)", renk=R["gri"], dash="dot", row=row, col=col, font=10, ysh=-12)
        if ad == "Gartley":
            g886 = lvl(A[1], X[1], 0.886)
            yatay(fig, g886, X[0], x1, f"0.886 XA → {g886:.2f}: dar stop seçeneği (Bat'e evrilme sınırı); risk {giris - (g886 - 0.75 * a14):.1f}",
                  renk=R["gri"], dash="dot", row=row, col=col, font=10, ysh=10)
        ozet.append(f"{ad}: E {giris:.1f} / S {stop:.1f} / risk {giris-stop:.1f} / T1 R:R {(T1-giris)/(giris-stop):.1f} / T2 R:R {(T2-giris)/(giris-stop):.1f}")
        fig.update_xaxes(row=row, col=col)
    for r_ in (1, 2, 3, 4):
        fig.update_yaxes(title="fiyat", row=r_, col=1)
    not_kutusu(fig, " · ".join(ozet[:2]) + "<br>" + " · ".join(ozet[2:]) + "<br>Aynı XA (20 birim), stop = geçersizlik − 0.75 ATR, giriş PRZ üst kenarı + 0.03 XA: Bat en dar stop; Gartley X yerine 0.886'ya stop koyarsa Bat'e yaklaşır; Crab/Butterfly'da stop uzun → pozisyon küçültülür (risk = %0.5–1 hesap; büyüklük = risk/(E−S))",
               x=0.5, y=-0.031, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, "Şekil 20 — Stop yerleşimi pattern'e göre: geçersizlik seviyesi + ATR tamponu ve R:R (şematik örnek)", 1540,
                 "Retracement pattern'lerinde stop X'in ötesi; extension pattern'lerinde PRZ'nin en uzak sayısının ötesi (1.618 / 2.0 XA)")
    fig.update_layout(margin=dict(b=150))
    kaydet(fig, "20_stop_yerlesimi")


def g21_type1_type2():
    # yerleşim: iki senaryo yan yana daralıyordu → ALT ALTA (üst: Type I, alt: Type II)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=("Type I — reaction: tepki 0.382 AD'ye, sonra PRZ'ye dönüş",
                                        "Type II — reversal: retest tutar (HL) → 0.618 AD ve A"))
    for row, sen in ((1, "tip1"), (2, "tip2")):
        df, p = _yonetim_seri(seed=151 + row, senaryo=sen)
        X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
        prz = _prz_hesapla(p, dict(xa=0.886, bc=2.618, abcd=1.272))
        lo, hi = min(prz.values()), max(prz.values())
        x1 = len(df) - 1
        fig.add_trace(mum_iz(df, etiketler={p[k][0]: k for k in "XABCD"}), row=row, col=1)
        zigzag_iz([X, A, B, C, D], harfler=list("XABCD"), fig=fig, row=row, col=1, showlegend=(row == 1))
        kutu(fig, C[0], x1, lo, hi, R["prz"], metin="PRZ", konum="bottom", row=row, col=1)
        T1 = D[1] + 0.382 * (A[1] - D[1]); T2 = D[1] + 0.618 * (A[1] - D[1])
        yatay(fig, T1, D[0], x1, f"T1 = 0.382 AD → {T1:.2f}", renk=R["yesil"], row=row, col=1, font=10)
        yatay(fig, T2, D[0], x1, f"T2 = 0.618 AD → {T2:.2f}", renk=R["yesil"], row=row, col=1, font=10)
        yatay(fig, A[1], D[0], x1, "T3 = A", renk=R["yesil"], dash="dot", row=row, col=1, font=10)
        giris = hi + 0.5
        yatay(fig, giris, D[0], x1, f"1. giriş → {giris:.2f}", renk=R["up"], dash="solid", row=row, col=1, font=10, konum="left")
        # tepki tepesi ve retest
        seg = df.iloc[D[0]:D[0] + 14]
        tepe_i = int(seg.High.idxmax()); tepe = df.High.iloc[tepe_i]
        seg2 = df.iloc[tepe_i:tepe_i + 12]
        ret_i = int(seg2.Low.idxmin()); ret = df.Low.iloc[ret_i]
        ok(fig, tepe_i, tepe, "ilk tepki: ~0.382 AD (Type I reaction)<br>→ kısmi kâr al, stop BE'ye", ax=-5, ay=-95, renk=R["yesil"], row=row, col=1)
        fig.update_xaxes(range=[0, x1 * 1.3], row=row, col=1)
        if row == 1:
            ok(fig, ret_i, ret, "PRZ'ye geri dönüş: kısmi kâr alınmadıysa buharlaşır;<br>BE stop → sıfır", ax=50, ay=45, renk=R["kirmizi"], row=row, col=1)
            yatay(fig, giris, tepe_i, x1, "stop → BE (giriş)", renk=R["kirmizi"], dash="dash", row=row, col=1, font=10)
        else:
            ok(fig, ret_i, ret, f"retest: higher low ({ret:.2f} > {D[1]:.2f}),<br>PRZ tuttu → 2. giriş (Type II), en dar stop", ax=60, ay=45, renk=R["fvg"], row=row, col=1)
            fig.add_trace(go.Scatter(x=[ret_i], y=[ret], mode="markers", marker=dict(symbol="triangle-up", size=14, color=R["fvg"]),
                                     name="Type II retest girişi", showlegend=(row == 2)), row=row, col=1)
            yatay(fig, ret - 0.6, ret_i, x1, "2. giriş stop'u: retest dibi altı", renk=R["kirmizi"], row=row, col=1, font=10)
            ok(fig, x1, df.High.iloc[x1], "A'ya uzanış = reversal", ax=-40, ay=-30, renk=R["yesil"], row=row, col=1)
        fig.update_xaxes(row=row, col=1)
    for r_ in (1, 2):
        fig.update_yaxes(title="fiyat", row=r_, col=1)
    not_kutusu(fig, "Carney: 'çoğu durum ilk testte REACTION, ikinci testte daha büyük REVERSAL üretir.' Bulkowski: A'ya tam dönüş azınlık (%33–58) → temerrüt varsayımı reaction trade.<br>"
                    "SMC karşılığı: sweep → CHoCH → OB retest; Type II retest'i 'pattern başarısız' sanıp kaçırmak tipik hata.",
               x=0.5, y=-0.05, xanchor="center", yanchor="top", font=10.5)
    temel_layout(fig, "Şekil 21 — Type I (reaction) ve Type II (reversal): aynı Bat, iki farklı devam (şematik örnek)", 860)
    fig.update_layout(margin=dict(b=120))
    kaydet(fig, "21_type1_type2")


def g22_pozisyon_yonetimi():
    df, p = _yonetim_seri(seed=161, senaryo="tip2")
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    prz = _prz_hesapla(p, dict(xa=0.886, bc=2.618, abcd=1.272))
    lo, hi = min(prz.values()), max(prz.values())
    n = len(df) - 1
    df = df.iloc[B[0] - 4:]
    off = B[0] - 4
    fig = go.Figure(mum_iz(df, x=list(range(off, off + len(df))), etiketler={p[k][0] - off: k for k in "BCD"}))
    zigzag_iz([B, C, D], harfler=["B", "C", "D"], fig=fig, ad="B-C-D")
    kutu(fig, C[0], n, lo, hi, R["prz"], metin="PRZ", konum="bottom")
    giris = hi + 0.5; stop0 = X[1] - 0.6
    T1 = D[1] + 0.382 * (A[1] - D[1]); T2 = D[1] + 0.618 * (A[1] - D[1])
    # olaylar
    xs = list(range(D[0], n + 1))
    H = df.High.values; idx0 = D[0] - off
    t1_i = next(i for i in xs if df.High.iloc[i - off] >= T1)
    t2_i = next(i for i in xs if df.High.iloc[i - off] >= T2)
    yatay(fig, giris, D[0], n, f"giriş {giris:.2f}", renk=R["up"], dash="solid", konum="left", font=10)
    yatay(fig, T1, D[0], n, f"T1 = 0.382 AD → {T1:.2f}", renk=R["yesil"], font=10)
    yatay(fig, T2, D[0], n, f"T2 = 0.618 AD → {T2:.2f}", renk=R["yesil"], font=10)
    yatay(fig, A[1], D[0], n, "T3 = A", renk=R["yesil"], dash="dot", font=10)
    # stop merdiveni
    stop_x = [D[0], t1_i]; stop_y = [stop0, stop0]
    # BE
    stop_x += [t1_i, t2_i]; stop_y += [giris, giris]
    # 0.382 trailer T2'den sonra
    hmax = df.High.iloc[t2_i - off]
    tx, ty = [], []
    for i in range(t2_i, n + 1):
        hmax = max(hmax, df.High.iloc[i - off])
        tx.append(i); ty.append(hmax - 0.382 * (hmax - D[1]))
    fig.add_trace(go.Scatter(x=stop_x, y=stop_y, mode="lines", name="stop: ilk → BE", line=dict(color=R["kirmizi"], width=2.2, shape="hv")))
    fig.add_trace(go.Scatter(x=tx, y=ty, mode="lines", name="0.382 trailer: H_max − 0.382·(H_max − D)", line=dict(color=R["kirmizi"], width=2.2, dash="dash", shape="hv")))
    # yapısal trailing: LTF HL'ler (basit: son 5 barın min'i, sadece yükselen adımlar)
    sx, sy = [], []
    cur = -np.inf
    for i in range(t2_i, n + 1):
        hl = df.Low.iloc[max(i - off - 5, 0):i - off + 1].min()
        if hl > cur:
            cur = hl
        sx.append(i); sy.append(cur - 0.2)
    fig.add_trace(go.Scatter(x=sx, y=sy, mode="lines", name="yapısal trailer: son HL'nin altı", line=dict(color=R["mavi"], width=1.8, dash="dot", shape="hv")))
    ok(fig, t1_i, T1, "① T1: %40 kapat, stop → BE", ax=-70, ay=-40, renk=R["yesil"])
    ok(fig, t2_i, T2, "② T2: %30 kapat, kalan %30 trailing'e", ax=-90, ay=-40, renk=R["yesil"])
    ok(fig, (t2_i + n) / 2, ty[len(ty) // 2], "③ iki trailer'dan UZAK olanı kullan<br>(erken sarsılmayı önler)", ax=60, ay=60, renk=R["kirmizi"])
    ok(fig, D[0], stop0, "başlangıç stop: X − tampon", ax=90, ay=25, renk=R["kirmizi"])
    # pozisyon büyüklüğü şeridi (üstte)
    fig.add_annotation(x=(D[0] + t1_i) / 2, y=A[1] - 1.3, text="%100 pozisyon", showarrow=False, font=dict(size=10, color=R["ink"]),
                       bgcolor=rgba(R["up"], 0.25))
    fig.add_annotation(x=(t1_i + t2_i) / 2, y=A[1] - 1.3, text="%60", showarrow=False, font=dict(size=10, color=R["ink"]), bgcolor=rgba(R["up"], 0.18))
    fig.add_annotation(x=(t2_i + n) / 2, y=A[1] - 1.3, text="%30 (trailing)", showarrow=False, font=dict(size=10, color=R["ink"]), bgcolor=rgba(R["up"], 0.10))
    not_kutusu(fig, "Kural seti: T1'de %33–50 kapat + stop BE · T2'de %25–33<br>kalan için 0.382 trailer (Carney) veya yapısal trailer (LTF HL altı) — daha UZAK olan<br>"
                    "Zaman stopu: T1'e 1.5×pattern süresi içinde ulaşılmadıysa küçült/kapat<br>Type I sonrası PRZ'ye dönen fiyat kalan pozisyonun stop'unu daraltır",
               x=0.01, y=0.98, xanchor="left", yanchor="top", font=10)
    temel_layout(fig, "Şekil 22 — Pozisyon yönetimi adım adım: kısmi kâr, BE ve iki trailing yöntemi (şematik örnek)", 640,
                 "Stop çizgisi merdiven gibi yükselir; hiçbir adımda geri çekilmez", lejant=True)
    fig.update_yaxes(title="fiyat", range=[stop0 - 2, A[1] + 3.5])
    kaydet(fig, "22_pozisyon_yonetimi")


def g23_basarisiz():
    P = PATTERNLER["Bat"]
    df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=171, son=0,
                      sonrasi=[(1, -0.05), (2, -0.09), (3, -0.13), (7, -0.20), (14, -0.005), (22, -0.30)])
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    prz = _prz_hesapla(p, dict(xa=0.886, bc=2.618, abcd=1.272))
    lo, hi = min(prz.values()), max(prz.values())
    n = len(df) - 1
    fig = go.Figure(mum_iz(df, etiketler={p[k][0]: k for k in "XABCD"} | {D[0] + 1: "PRZ dışı KAPANIŞ", D[0] + 2: "geri kapanmadı → geçersiz"}))
    zigzag_iz([X, A, B, C, D], harfler=list("XABCD"), fig=fig)
    kutu(fig, C[0], n, lo, hi, R["prz"], metin="PRZ (Bat 0.886)", konum="top")
    prz_cizgileri(fig, prz, C[0], n)
    yatay(fig, X[1], X[0], n, "X — geçersizlik", renk=R["kirmizi"], w=1.6, font=10)
    c1 = df.Close.iloc[D[0] + 1]; c2 = df.Close.iloc[D[0] + 2]
    ok(fig, D[0] + 1, c1, f"① mum PRZ'nin ALTINDA kapandı<br>({c1:.2f} < {lo:.2f}): uyarı (tail close)", ax=-150, ay=75, renk=R["kirmizi"])
    ok(fig, D[0] + 2, c2, "② ertesi mum PRZ içine GERİ KAPANMADI →<br>pattern geçersiz; stop çalışır (X altı)", ax=130, ay=-95, renk=R["kirmizi"])
    # PRZ rol değişimi: direnç
    ret_seg = df.iloc[D[0] + 8:D[0] + 18]
    ri = int(ret_seg.High.idxmax()); rh = df.High.iloc[ri]
    ok(fig, ri, rh, "③ PRZ rol değiştirdi: destek → direnç;<br>retest'te ters yön (short) aranır", ax=70, ay=-100, renk=R["dn"])
    fig.add_trace(go.Scatter(x=[ri], y=[rh], mode="markers", marker=dict(symbol="triangle-down", size=14, color=R["dn"]), name="ters yön girişi (retest)"))
    yatay(fig, hi + 0.5, ri, n, "ters işlem stop'u: PRZ üstü", renk=R["kirmizi"], dash="dash", font=10, ysh=32)
    yatay(fig, lvl(A[1], X[1], 1.13), C[0], n, "1.13 XA — evrilme kontrolü: Bat → Alt Bat?", renk=R["mavi"], dash="dashdot", font=10)
    fig.update_xaxes(range=[0, n + 36])
    not_kutusu(fig, "Başarısızlık tanımı (harmonicpattern.com): (i) PRZ ötesinde kararlı kapanış + (ii) izleyen mumda PRZ içine geri kapanmama. İkisi birlikte gerçekleşene dek pattern 'yaralı ama canlı'.<br>"
                    "Kontrol: Bat → Alt Bat (1.13), Butterfly 1.27 → 1.618, Gartley → Bat evrilmesi var mı? Yoksa PRZ'nin ≥1/3 retest'inde ters yön işlemi.",
               x=0.5, y=-0.09, xanchor="center", yanchor="top", font=10.5)
    temel_layout(fig, "Şekil 23 — Başarısız pattern: PRZ delinmesi, geçersizleşme ve PRZ'nin rol değişimi (şematik örnek, Bat)", 600,
                 "Stop yemek ≠ pattern geçersiz; iki koşul birlikte aranır")
    fig.update_yaxes(title="fiyat")
    kaydet(fig, "23_basarisiz_pattern")


def g24_uyari_isaretleri():
    # yerleşim: üç uyarı işareti yan yana daralıyordu → ALT ALTA (okuma sırası a → b → c)
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.07,
                        subplot_titles=("(a) PRZ'ye GAP ile giriş", "(b) Dev T-bar: > 2·ATR", "(c) PRZ'de hiç kapanış yok"))
    for row in (1, 2, 3):
        P = PATTERNLER["Gartley"]
        df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=181 + row, son=8, nCD=16,
                          sonrasi=[(1, -0.04), (8, 0.25)] if row < 3 else [(1, -0.06), (4, -0.12), (8, -0.20)])
        X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
        prz = _prz_hesapla(p, dict(xa=0.786, bc=1.272, abcd=1.0))
        lo, hi = min(prz.values()), max(prz.values())
        a14 = float(atr(df)[D[0] - 1])
        if row == 1:
            # gap: D-1 kapanışı PRZ'nin çok üstünde, D barı PRZ içinde açılır
            df.loc[D[0] - 1, ["Close", "Low"]] = [hi + 2.2, hi + 2.0]
            df.loc[D[0], ["Open", "High"]] = [hi - 0.2, hi + 0.1]
            df.loc[D[0], "Low"] = lo - 0.1; df.loc[D[0], "Close"] = lo + 0.3
            ok(fig, D[0], hi, f"boşluk: önceki kapanış {hi+2.2:.2f}<br>→ açılış {hi-0.2:.2f}<br>uyarı: teyit olmadan girme", ax=55, ay=-95, renk=R["kirmizi"], row=row, col=1)
        elif row == 2:
            df.loc[D[0], "Open"] = hi + 2.5 * a14; df.loc[D[0], "High"] = hi + 2.6 * a14
            df.loc[D[0], "Low"] = lo - 0.6 * a14; df.loc[D[0], "Close"] = lo + 0.2
            df.loc[D[0] - 1, "Close"] = hi + 2.4 * a14; df.loc[D[0] - 1, "Low"] = hi + 2.0 * a14
            ok(fig, D[0], df.Low.iloc[D[0]], f"T-bar boyu {(df.High.iloc[D[0]]-df.Low.iloc[D[0]])/a14:.1f}·ATR14 (>2) →<br>aşırı aralık; momentum PRZ'yi ezebilir", ax=-70, ay=60, renk=R["kirmizi"], row=row, col=1)
        else:
            # PRZ'ye değip kapanış vermeden geçen: D barı PRZ'nin altında kapanıyor, sonraki bar da altta
            df.loc[D[0], "Low"] = lo - 0.9; df.loc[D[0], "Close"] = lo - 0.5
            df.loc[D[0] + 1, ["Open", "Close", "High", "Low"]] = [lo - 0.5, lo - 1.4, lo - 0.3, lo - 1.6]
            ok(fig, D[0], lo - 0.5, "PRZ'ye değdi ama İÇİNDE kapanış yok →<br>PRZ 'görülmedi'; ertesi mumu bekle", ax=-60, ay=60, renk=R["kirmizi"], row=row, col=1)
        n = len(df) - 1
        fig.add_trace(mum_iz(df.iloc[B[0]:], x=list(range(B[0], n + 1)), etiketler={p[k][0] - B[0]: k for k in "BCD"}), row=row, col=1)
        zigzag_iz([B, C, D], harfler=["B", "C", "D"], fig=fig, row=row, col=1, showlegend=(row == 1))
        kutu(fig, C[0], n, lo, hi, R["prz"], metin="PRZ", konum="bottom", row=row, col=1)
        fig.update_xaxes(row=row, col=1)
    for r_ in (1, 2, 3):
        fig.update_yaxes(title="fiyat", row=r_, col=1)
    not_kutusu(fig, "Carney'nin üç PRZ uyarı işareti: gap · tail close (PRZ dışı kapanış) · aşırı fiyat aralığı; + uygulamacı eklemesi (Carney'ye ait değil): PRZ'de kapanış olmaması. Herhangi biri varsa: teyitsiz girme, pozisyonu küçült, ertesi mumu bekle.",
               x=0.5, y=-0.029, xanchor="center", yanchor="top", font=10.5)
    temel_layout(fig, "Şekil 24 — PRZ'de uyarı işaretleri: gap, dev mum, kapanışsız dokunuş (şematik örnek)", 1200)
    fig.update_layout(margin=dict(b=110))
    kaydet(fig, "24_uyari_isaretleri")


def g25_olusum_asamali():
    P = PATTERNLER["Bat"]
    df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=191, son=14)
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    # yerleşim: üç aşama yan yana daralıyordu → ALT ALTA (okuma sırası ①→②→③)
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.06,
                        subplot_titles=("① X ve A oluştu: fib çiz, bekle", "② B oluştu (0.50 XA): aday D bantları", "③ C oluştu: PRZ önceden çizilir"))
    x1 = D[0] + 12
    for row, kes in ((1, A[0] + 3), (2, B[0] + 4), (3, C[0] + 3)):
        d_ = df.iloc[:kes + 1]
        fig.add_trace(mum_iz(d_, etiketler={p[k][0]: k for k in "XABCD" if p[k][0] <= kes}), row=row, col=1)
        pts = [q for q in (X, A, B, C) if q[0] <= kes]
        zigzag_iz(pts, harfler=list("XABC")[:len(pts)], fig=fig, row=row, col=1, showlegend=(row == 1))
        yatay(fig, X[1], X[0], x1, "X", renk=R["gri"], dash="solid", row=row, col=1, font=10)
        if row == 1:
            for r in (0.382, 0.5, 0.618, 0.786, 0.886):
                yatay(fig, lvl(A[1], X[1], r), X[0], x1, f"{r:.3f}", renk=R["fib"], w=1, row=row, col=1, font=10)
            for r in (1.13, 1.272, 1.618):
                yatay(fig, lvl(A[1], X[1], r), X[0], x1, f"{r:.3f}", renk=R["dn"], w=1, row=row, col=1, font=10)
            not_kutusu(fig, "Henüz pattern yok.<br>Sadece XA retracement'ları<br>(0.382–0.886) ve uzantıları<br>(1.13/1.27/1.618) çizilir.",
                       x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=1, col=1, font=10)
        elif row == 2:
            yatay(fig, B[1], A[0], x1, "B = 0.50 XA", renk=R["mavi"], w=1.6, row=row, col=1, font=10)
            for r, t, renk in [(0.886, "Bat D: 0.886 XA", R["prz"]), (1.13, "Alt Bat D: 1.13 XA", R["mavi"]), (1.618, "Crab D: 1.618 XA", R["dn"])]:
                y = lvl(A[1], X[1], r)
                kutu(fig, B[0], x1, y - 0.25, y + 0.25, renk, alfa=0.25, metin=t, konum="top", row=row, col=1, font=10)
            not_kutusu(fig, "B ≈ 0.382–0.50 → aday: Bat (0.886),<br>Alt Bat (1.13), Crab (1.618).<br>Gartley/Butterfly elendi (B ≠ 0.618/0.786).",
                       x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=2, col=1, font=10)
        else:
            prz = _prz_hesapla(p, dict(xa=0.886, bc=2.618, abcd=1.272))
            lo, hi = min(prz.values()), max(prz.values())
            kutu(fig, C[0], x1, lo, hi, R["prz"], metin="PRZ hazır", konum="top", row=3, col=1)
            prz_cizgileri(fig, prz, C[0], x1, row=3, col=1)
            yatay(fig, hi + 0.8, C[0], x1, "alarm: PRZ üst kenarı + 1 ATR (crossing down)", renk=R["lik"], dash="dashdot", row=3, col=1, font=10, ysh=24)
            kutu(fig, C[0], x1, lvl(A[1], X[1], 1.13) - 0.25, lvl(A[1], X[1], 1.13) + 0.25, R["mavi"], alfa=0.15, metin="yedek: 1.13 (Alt Bat)", konum="bottom", row=3, col=1, font=10)
            ok(fig, C[0], C[1], f"C = 0.50 AB<br>(0.382–0.886 içinde ✓,<br>A'yı aşmadı ✓)", ax=-70, ay=-70, renk=R["ink"], row=3, col=1)
            not_kutusu(fig, "CD gelişirken izle: momentum azalıyor mu,<br>t_CD ≈ t_AB mi, hacim T-bar'da sıçrıyor mu.<br>PRZ'ye 1 ATR kala LTF'ye in.",
                       x=0.03, y=0.05, xanchor="left", yanchor="bottom", row=3, col=1, font=10)
        fig.update_xaxes(range=[0, x1 + (4 if row < 3 else 34)], row=row, col=1)
    # eski shared_yaxes yerine: üç panelde de aynı fiyat aralığı
    for r_ in (1, 2, 3):
        fig.update_yaxes(title="fiyat", range=[lvl(A[1], X[1], 1.7), A[1] + 2], row=r_, col=1)
    temel_layout(fig, "Şekil 25 — Canlı tanıma: pattern oluşurken ne çizilir? X-A → B → C aşamaları (şematik örnek)", 1200,
                 "Aday haritası: B'nin durduğu yer aday D bantlarını verir; C oluşunca PRZ fiyat gelmeden hazırdır")
    kaydet(fig, "25_olusum_asamali")


def g28_smc_koprusu():
    P = PATTERNLER["Butterfly"]
    df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=201, son=0, nCD=22,
                      sonrasi=[(1, -0.02), (2, 0.06), (4, 0.16), (8, 0.045), (15, 0.42), (23, 0.66)])
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    prz = _prz_hesapla(p, dict(xa=1.272, bc=2.0, abcd=1.272))
    lo, hi = min(prz.values()), max(prz.values())
    n = len(df) - 1
    # sweep mumu: D barı X altına derin fitil (zaten D<X), kapanış PRZ üstüne
    df.loc[D[0], "Low"] = lo - 0.3; df.loc[D[0], "Close"] = hi + 0.4; df.loc[D[0], "Open"] = hi + 0.9
    df.loc[D[0] + 1, ["Open", "Close", "High", "Low"]] = [hi + 0.4, hi + 2.2, hi + 2.4, hi + 0.2]
    df.loc[D[0] + 2, ["Open", "Close", "High", "Low"]] = [hi + 2.2, hi + 3.6, hi + 3.8, hi + 2.1]
    # OB: yükseliş öncesi son düşüş mumu = D (sweep) barının kendisi; FVG: D+1 tepesi ile D+3 dibi arası boşluk
    ob_lo, ob_hi = df.Low.iloc[D[0]], df.Open.iloc[D[0]]
    df.loc[D[0] + 3, ["Open", "Close", "High", "Low"]] = [hi + 3.6, hi + 4.4, hi + 4.6, hi + 3.5]
    fvg_lo, fvg_hi = df.High.iloc[D[0] + 1], df.Low.iloc[D[0] + 3]
    fig = go.Figure(mum_iz(df, etiketler={p[k][0]: k for k in "XABCD"} | {D[0]: "D = sweep mumu = OB"}))
    zigzag_iz([X, A, B, C, D], harfler=list("XABCD"), fig=fig)
    kutu(fig, C[0], n, lo, hi, R["prz"], metin="PRZ (Butterfly 1.27 XA)", konum="bottom")
    yatay(fig, X[1], X[0], n, "X (eski dip) — altında stop havuzu", renk=R["lik"], dash="dash", w=1.8, font=10)
    kutu(fig, X[0], n, X[1] - 0.15, X[1] + 0.15, R["lik"], alfa=0.15)
    ok(fig, D[0], df.Low.iloc[D[0]], "SWEEP: X altındaki stop'lar temizlendi,<br>kapanış geri içeride = Butterfly D + T-bar", ax=-100, ay=45, renk=R["lik"])
    kutu(fig, D[0], n, ob_lo, ob_hi, R["ob"], alfa=0.18, metin="Order Block (bullish OB = D mumu)", konum="bottom", font=10)
    kutu(fig, D[0] + 2, n, fvg_lo, fvg_hi, R["fvg"], alfa=0.18, metin="FVG (D+1 tepesi ↔ D+3 dibi)", konum="top", font=10)
    # displacement + CHoCH: CD bacağının son küçük tepesi (LH) kırılınca
    seg = df.iloc[D[0] - 7:D[0]]
    lh_i = int(seg.High.idxmax()); lh = df.High.iloc[lh_i]
    yatay(fig, lh, lh_i, n, "son LH → kırılınca CHoCH", renk=R["up"], dash="dot", font=10, ysh=-11)
    kir_i = next((i for i in range(D[0], n + 1) if df.Close.iloc[i] > lh), None)
    if kir_i:
        ok(fig, kir_i, df.Close.iloc[kir_i], "CHoCH (displacement kapanışı)", ax=60, ay=-30, renk=R["up"])
    # OB retest girişi
    ret_seg = df.iloc[D[0] + 4:D[0] + 12]
    ri = int(ret_seg.Low.idxmin())
    fig.add_trace(go.Scatter(x=[ri], y=[df.Low.iloc[ri]], mode="markers", marker=dict(symbol="triangle-up", size=14, color=R["ob"]), name="giriş: OB / FVG retest"))
    ok(fig, ri, df.Low.iloc[ri], "giriş: FVG dolduruldu, OB üst kenarına dokunuş<br>(SMC dili) = Type II retest (harmonik dili)", ax=120, ay=70, renk=R["ob"])
    yatay(fig, df.Low.iloc[D[0]] - 0.4, D[0], n, "stop: sweep dibinin altı", renk=R["kirmizi"], font=10)
    yatay(fig, D[1] + 0.382 * (A[1] - D[1]), D[0], n, "T1 0.382 AD", renk=R["yesil"], font=10, ysh=8)
    yatay(fig, D[1] + 0.618 * (A[1] - D[1]), D[0], n, "T2 0.618 AD", renk=R["yesil"], font=10)
    not_kutusu(fig, "Köprü: Butterfly/Crab'in D'si (1.27–1.618 XA) = SMC'deki 'external liquidity sweep of X'. Gartley 0.786 / Bat 0.886 ise stop havuzuna YAKLAŞAN ama geçmeyen seviyeler.<br>"
                    "Harmonik PRZ 'nereyi' söyler; SMC teyidi (sweep → displacement/CHoCH → OB/FVG retest) 'ne zaman'ı söyler.",
               x=0.5, y=-0.09, xanchor="center", yanchor="top", font=10.5)
    temel_layout(fig, "Şekil 28 — SMC köprüsü: Butterfly D = likidite süpürmesi; OB, FVG, CHoCH ile giriş zamanlaması (şematik örnek)", 620)
    fig.update_yaxes(title="fiyat"); fig.update_xaxes(range=[B[0] - 4, n + 24])
    kaydet(fig, "28_smc_koprusu")


def g27_mtf_fraktal():
    """Çoklu zaman dilimi: üstte H4 Bat + PRZ; altta PRZ zaman penceresinin M15 mumları,
    içinde küçük bullish AB=CD tamamlanışı, son LH kırılımı (CHoCH) ve giriş."""
    P = PATTERNLER["Bat"]
    df, p = xabcd_kur(P["rB"], P["rC"], P["dXA"], seed=231, son=12, nCD=14,
                      sonrasi=[(1, 0.02), (3, 0.12), (6, 0.08), (12, 0.40)])
    X, A, B, C, D = p["X"], p["A"], p["B"], p["C"], p["D"]
    prz = _prz_hesapla(p, dict(xa=P["dXA"], bc=P["bc"], abcd=P["abcd"]))
    lo, hi = min(prz.values()), max(prz.values())
    n = len(df) - 1
    a14 = float(atr(df)[D[0] - 1])
    alarm = hi + 1.0 * a14
    w0, w1 = D[0] - 2, D[0] + 3   # LTF penceresi (H4 bar)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12, row_heights=[0.5, 0.5],
                        subplot_titles=("H4 — bullish Bat, PRZ önceden çizili; alarm PRZ üst kenarı + 1 ATR",
                                        "M15 — aynı PRZ'nin zaman penceresi (H4 D−2 … D+3): LTF AB=CD tamamlanışı + CHoCH = giriş"))
    # ---- üst: H4
    fig.add_trace(mum_iz(df, etiketler={p[k][0]: k for k in "XABCD"}), row=1, col=1)
    zigzag_iz([X, A, B, C, D], harfler=list("XABCD"), fig=fig, row=1, col=1)
    bacak_etiketi(fig, A, B, f"B = {P['rB']:.3f} XA", row=1, col=1, xsh=-26, ysh=-16)
    bacak_etiketi(fig, B, C, f"C = {P['rC']:.3f} AB", row=1, col=1, xsh=26, ysh=16)
    kutu(fig, C[0], n, lo, hi, R["prz"], metin=f"PRZ {lo:.2f}–{hi:.2f}", konum="bottom", row=1, col=1)
    prz_cizgileri(fig, prz, C[0], n, row=1, col=1)
    yatay(fig, alarm, C[0], n, f"alarm: PRZ üst + 1 ATR → {alarm:.2f} → LTF'ye in", renk=R["mavi"], dash="dashdot", row=1, col=1, font=10, ysh=8)
    yatay(fig, X[1], X[0], n, "geçersizlik = X", renk=R["kirmizi"], dash="dash", row=1, col=1, font=10)
    kutu(fig, w0 - 0.5, w1 + 0.5, lo - 1.2 * a14, hi + 2.2 * a14, R["ob"], alfa=0.10, metin="→ alt panel (6 H4 barı)", konum="bottom", row=1, col=1, font=10)
    # ---- alt: M15 (16 mum / H4 bar) — sentetik, aynı fiyat ölçeği
    m = 16
    st = float(df.Close.iloc[w0 - 1])
    a_, b_ = hi + 1.5 * a14, hi + 0.5 * a14
    c_ = b_ + 0.618 * (a_ - b_)
    d_ = c_ - 1.272 * (a_ - b_)                    # alternate AB=CD 1.27 → PRZ içinde
    d_ = min(max(d_, lo + 0.05 * (hi - lo)), hi - 0.05 * (hi - lo))
    bc_ltf = c_ - 1.618 * (c_ - b_)
    ba, bb, bc, bd = 14, 34, 46, 66
    anch = [(0, st), (7, st - 0.4 * (st - a_) if st > a_ else a_ - 0.2 * a14), (ba, a_), (bb, b_), (bc, c_), (bd, d_),
            (74, d_ + 0.55 * (c_ - d_)), (81, c_ + 0.35 * (a_ - c_)), (88, c_ - 0.25 * (c_ - d_)), (m * 6 - 1, a_ + 0.05 * a14)]
    ltf = mumlar(anch, seed=232, gurultu=0.08)
    nl = len(ltf) - 1
    fig.add_trace(mum_iz(ltf, etiketler={ba: "a", bb: "b", bc: "c", bd: "d = LTF D"}), row=2, col=1)
    zigzag_iz([(ba, a_), (bb, b_), (bc, c_), (bd, d_)], harfler=["a", "b", "c", "d"], fig=fig, row=2, col=1,
              renk=R["fvg"], showlegend=False, ad="LTF AB=CD")
    bacak_etiketi(fig, (bb, b_), (bc, c_), f"c = 0.618 ab", row=2, col=1, xsh=24, ysh=12, renk=R["fvg"], font=10)
    bacak_etiketi(fig, (bc, c_), (bd, d_), f"cd = 1.272 ab<br>{(c_-d_)/(c_-b_):.2f} bc", row=2, col=1, renk=R["fvg"], font=10)
    kutu(fig, 0, nl, lo, hi, R["prz"], metin="H4 PRZ (aynı fiyatlar)", konum="bottom", row=2, col=1, font=10)
    yatay(fig, bc_ltf, bc, nl, f"1.618 bc → {bc_ltf:.2f}", renk=R["fvg"], dash="dot", row=2, col=1, font=9, ysh=-7)
    yatay(fig, alarm, 0, nl, "alarm seviyesi (H4)", renk=R["mavi"], dash="dashdot", row=2, col=1, font=9, ysh=8)
    yatay(fig, c_, bc, nl, "son LH (c) → kırılınca CHoCH", renk=R["up"], dash="dot", row=2, col=1, font=10, ysh=-10)
    kir = next((i for i in range(bd + 1, nl + 1) if ltf.Close.iloc[i] > c_), None)
    a_ltf = float(atr(ltf)[bd])
    stop = min(d_, lo) - 0.5 * a_ltf   # stop PRZ içinde olamaz: PRZ altı − tampon
    yatay(fig, stop, bd, nl, f"stop: PRZ altı (≤ LTF d) − 0.5 ATR(M15) → {stop:.2f}", renk=R["kirmizi"], w=1.5, row=2, col=1, font=10, ysh=-8)
    ok(fig, bd, d_, "T-bar (H4) içinde LTF AB=CD tamamlandı:<br>PRZ 'sayı' olmaktan çıkıp 'yapı' oldu", ax=-120, ay=40, renk=R["fvg"], row=2, col=1)
    if kir is not None:
        e = float(ltf.Close.iloc[kir])
        fig.add_trace(go.Scatter(x=[kir], y=[e], mode="markers", marker=dict(symbol="triangle-up", size=14, color=R["up"]),
                                 name="giriş: CHoCH kapanışı", showlegend=False), row=2, col=1)
        ok(fig, kir, e, f"CHoCH: c'nin üstünde kapanış → GİRİŞ {e:.2f}<br>(alternatif: retest'te ikinci giriş)", ax=-25, ay=-75, renk=R["up"], row=2, col=1)
        T1 = D[1] + 0.382 * (A[1] - D[1])
        fig.add_annotation(xref="x2 domain", yref="y2 domain", x=0.99, y=0.97, text=f"T1 (H4) = 0.382 AD → {T1:.2f} ↑ panel dışı<br>risk {e-stop:.2f} → R:R T1 {(T1-e)/(e-stop):.1f}",
                           showarrow=False, xanchor="right", yanchor="top", font=dict(size=10, color=R["yesil"]),
                           bgcolor="rgba(255,255,255,0.9)", bordercolor=R["yesil"], borderwidth=0.6, borderpad=3)
    fig.update_xaxes(tickvals=[k * m for k in range(7)], ticktext=[f"H4 D{k-2:+d}" if k != 2 else "H4 D" for k in range(7)], row=2, col=1)
    fig.update_xaxes(range=[0, n * 1.3], row=1, col=1)
    fig.update_yaxes(title="fiyat", row=1, col=1); fig.update_yaxes(title="fiyat", row=2, col=1)
    not_kutusu(fig, "Akış: HTF (D1/H4) trend + büyük XA → işlem TF'sinde pattern ve PRZ → PRZ'ye 1 ATR kala LTF'ye in (alarm) → LTF'de kendi AB=CD'si / mini pattern + son LH kırılımı (CHoCH) girişi verir.<br>"
                    "LTF'de pattern ARANMAZ; LTF gürültüsü PRZ'yi geçersiz kılmaz. Stop LTF ucu − tampon ile HTF geçersizliğinden hangisi işlem planına uygunsa (dar stop = küçük risk, ama sarsılma olasılığı).",
               x=0.5, y=-0.07, xanchor="center", yanchor="top", font=10.5)
    temel_layout(fig, "Şekil 27 — Çoklu zaman dilimi (fraktal): H4 Bat PRZ'si içinde M15 AB=CD tamamlanışı ve CHoCH girişi (şematik örnek)", 900,
                 "Üst panel 'nereyi' (PRZ), alt panel 'ne zaman' (LTF yapı) sorusuna cevap verir — aynı fiyat ölçeği")
    fig.update_layout(margin=dict(b=120))
    kaydet(fig, "27_mtf_fraktal")


# ================================================================ GERÇEK VERİ
def veri_getir(ticker, period, interval):
    ad = f"{ticker.replace('=', '_').replace('^', '')}_{interval}.csv"
    yol = VERI / ad
    if yol.exists() and not YENILE:
        df = pd.read_csv(yol, index_col=0, parse_dates=True)
        return df, f"önbellek ({ad})"
    try:
        import yfinance as yf
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close"]].dropna()
        if len(df) < 100:
            raise RuntimeError("çok az veri")
        df.to_csv(yol)
        return df, "yfinance (indirildi)"
    except Exception as e:  # noqa
        RAPOR.append(f"GERÇEK VERİ ATLANDI: {ticker} {interval} — indirilemedi ({e}) ve önbellek yok")
        return None, None


def pivotlar(df, n):
    """Fraktal swing tespiti: high, sağ/sol n bardan yüksek → tepe; low için dip. Ardışık aynı tür pivotlar birleştirilir."""
    H = df.High.values; L = df.Low.values; piv = []
    for i in range(n, len(df) - n):
        if H[i] == H[i - n:i + n + 1].max():
            piv.append((i, float(H[i]), 1))
        if L[i] == L[i - n:i + n + 1].min():
            piv.append((i, float(L[i]), -1))
    piv.sort()
    out = []
    for p in piv:
        if out and out[-1][2] == p[2]:
            if (p[2] == 1 and p[1] > out[-1][1]) or (p[2] == -1 and p[1] < out[-1][1]):
                out[-1] = p
        else:
            out.append(p)
    return out


TARAMA = {  # ad: (B aralığı, C aralığı, D_XA aralığı, BC proj aralığı, geçersizlik XA)
    "Gartley": ((0.588, 0.648), (0.382, 0.886), (0.75, 0.82), (1.13, 1.70), 1.0),
    "Bat": ((0.36, 0.52), (0.382, 0.886), (0.85, 0.92), (1.60, 2.70), 1.0),
    "Butterfly": ((0.75, 0.82), (0.382, 0.886), (1.22, 1.66), (1.60, 2.70), 1.618),
    "Crab": ((0.36, 0.65), (0.382, 0.886), (1.55, 1.70), (2.50, 3.70), 2.0),
    "AltBat": ((0.30, 0.40), (0.382, 0.886), (1.10, 1.16), (2.00, 3.70), 1.272),
}


def tara(df, n):
    pv = pivotlar(df, n); res = []
    for k in range(len(pv) - 4):
        X, A, B, C, D = pv[k:k + 5]
        xa = abs(A[1] - X[1]); ab = abs(A[1] - B[1]); bc = abs(C[1] - B[1]); cd = abs(D[1] - C[1]); ad = abs(A[1] - D[1])
        if min(xa, ab, bc) <= 0:
            continue
        rB, rC, rD, rBC = ab / xa, bc / ab, ad / xa, cd / bc
        # C, A'yı aşmamalı (klasik pattern)
        if (X[2] == -1 and C[1] > A[1]) or (X[2] == 1 and C[1] < A[1]):
            continue
        for nm, (b, c, d, pr, gec) in TARAMA.items():
            if b[0] <= rB <= b[1] and c[0] <= rC <= c[1] and d[0] <= rD <= d[1] and pr[0] <= rBC <= pr[1]:
                res.append(dict(pattern=nm, yon="bull" if X[2] == -1 else "bear", X=X, A=A, B=B, C=C, D=D,
                                rB=rB, rC=rC, rD=rD, rBC=rBC, gec=gec))
    return res


def _tarih_tikleri(df, i0, i1, adet=8):
    idx = np.linspace(i0, i1, adet).astype(int)
    fmt = "%Y-%m-%d" if (df.index[1] - df.index[0]) >= pd.Timedelta("1D") else "%m-%d %H:%M"
    return list(idx), [df.index[i].strftime(fmt) for i in idx]


def _fmt(v):
    v = abs(v)
    return "{:,.0f}" if v >= 1000 else ("{:.2f}" if v >= 10 else "{:.4f}")


def gercek_ornek(no, dosya, ticker, period, interval, n, tercih, min_sonra=40, ad_goster=None):
    df, kaynak = veri_getir(ticker, period, interval)
    if df is None:
        return
    adaylar = [a for a in tara(df, n) if a["D"][0] <= len(df) - min_sonra]
    secim = [a for a in adaylar if a["pattern"] == tercih] or adaylar
    if not secim:
        RAPOR.append(f"GERÇEK VERİ: {ticker} {interval} n={n} — tarama hiçbir aday bulamadı; grafik atlandı")
        return
    a = secim[-1]  # en yeni
    X, A, B, C, D = a["X"], a["A"], a["B"], a["C"], a["D"]
    i0 = max(0, X[0] - 25); i1 = min(len(df) - 1, D[0] + min_sonra)
    d_ = df.iloc[i0:i1 + 1]
    xs = list(range(i0, i1 + 1))
    yon = a["yon"]; s = 1 if yon == "bull" else -1
    P = TARAMA[a["pattern"]]
    # PRZ: gerçekleşen XA oranı yerine pattern'in İDEAL sayıları
    ideal_xa = {"Gartley": 0.786, "Bat": 0.886, "Butterfly": 1.272, "Crab": 1.618, "AltBat": 1.13}[a["pattern"]]
    bc_secenek = [1.272, 1.618, 2.0, 2.24, 2.618, 3.14, 3.618]
    bc_r = min(bc_secenek, key=lambda k: abs(k - a["rBC"]))
    abcd_k = min([1.0, 1.272, 1.618], key=lambda k: abs(k - abs(D[1] - C[1]) / abs(A[1] - B[1])))
    prz = {f"{ideal_xa:.3f} XA": lvl(A[1], X[1], ideal_xa),
           f"{bc_r:.3f} BC": C[1] - bc_r * (C[1] - B[1]),
           f"AB=CD ×{abcd_k:.2f}": C[1] - abcd_k * (A[1] - B[1])}
    lo, hi = min(prz.values()), max(prz.values())
    xa = abs(A[1] - X[1])
    fig = go.Figure(mum_iz(d_, x=xs, etiketler={X[0] - i0: "X", A[0] - i0: "A", B[0] - i0: "B", C[0] - i0: "C", D[0] - i0: "D"}))
    pts = [(X[0], X[1]), (A[0], A[1]), (B[0], B[1]), (C[0], C[1]), (D[0], D[1])]
    zigzag_iz(pts, harfler=list("XABCD"), fig=fig)
    # zigzag pivotları (tüm pencere) ince gri
    pv = [p for p in pivotlar(df, n) if i0 <= p[0] <= i1]
    fig.add_trace(go.Scatter(x=[p[0] for p in pv], y=[p[1] for p in pv], mode="lines", name=f"zigzag pivotları (n={n})",
                             line=dict(color=R["gri"], width=1, dash="dot"), hoverinfo="skip"))
    bacak_etiketi(fig, pts[1], pts[2], f"B = {a['rB']:.3f} XA")
    bacak_etiketi(fig, pts[2], pts[3], f"C = {a['rC']:.3f} AB")
    bacak_etiketi(fig, pts[3], pts[4], f"D = {a['rD']:.3f} XA<br>{a['rBC']:.2f} BC")
    kutu(fig, C[0], i1, lo, hi, R["prz"], metin=f"PRZ (genişlik {100*(hi-lo)/xa:.1f}% XA)", konum="top" if yon == "bull" else "bottom")
    F = _fmt(D[1])
    prz_cizgileri(fig, prz, C[0], i1, fmt=F)
    gy = lvl(A[1], X[1], P[4])
    a14 = float(atr(df)[D[0]])
    stop = gy - s * 0.75 * a14
    yatay(fig, gy, X[0], i1, f"geçersizlik {P[4]:.3f} XA", renk=R["kirmizi"], dash="dash", font=10, ysh=-8 * s)
    yatay(fig, stop, X[0], i1, f"stop (∓0.75 ATR) → {F.format(stop)}", renk=R["kirmizi"], w=1.6, font=10, ysh=-8 * s)
    # sonuç: D sonrası
    T1 = D[1] + 0.382 * (A[1] - D[1]); T2 = D[1] + 0.618 * (A[1] - D[1])
    sonra = df.iloc[D[0] + 1:i1 + 1]
    if yon == "bull":
        t1_hit = bool((sonra.High >= T1).any()); t2_hit = bool((sonra.High >= T2).any())
        stop_hit = bool((sonra.Low <= stop).any())
        t1_i = int(sonra.index.get_indexer([sonra[sonra.High >= T1].index[0]])[0]) + D[0] + 1 if t1_hit else None
    else:
        t1_hit = bool((sonra.Low <= T1).any()); t2_hit = bool((sonra.Low <= T2).any())
        stop_hit = bool((sonra.High >= stop).any())
        t1_i = int(sonra.index.get_indexer([sonra[sonra.Low <= T1].index[0]])[0]) + D[0] + 1 if t1_hit else None
    stop_once = False
    if stop_hit:
        s_i = (sonra.index.get_indexer([sonra[(sonra.Low <= stop) if yon == "bull" else (sonra.High >= stop)].index[0]])[0]) + D[0] + 1
        stop_once = (t1_i is None) or (s_i < t1_i)
    yatay(fig, T1, D[0], i1, f"T1 0.382 AD → {F.format(T1)}  [{'ulaşıldı' if t1_hit else 'ulaşılmadı'}]", renk=R["yesil"], font=10)
    yatay(fig, T2, D[0], i1, f"T2 0.618 AD → {F.format(T2)}  [{'ulaşıldı' if t2_hit else 'ulaşılmadı'}]", renk=R["yesil"], font=10)
    yatay(fig, A[1], D[0], i1, "T3 = A", renk=R["yesil"], dash="dot", font=10)
    if t1_i:
        ok(fig, t1_i, T1, "T1'e ulaştı", ax=0, ay=-35 * s, renk=R["yesil"])
    sonuc = ("stop ÖNCE çalıştı" if stop_once else ("T2'ye ulaştı" if t2_hit else ("T1'e ulaştı (reaction)" if t1_hit else "T1'e ulaşmadı")))
    if not stop_once and stop_hit:
        sonuc += "; sonrasında stop seviyesi de test edildi (kısmi kâr + BE olmadan kâr geri verilirdi)"
    tv, tt = _tarih_tikleri(df, i0, i1)
    fig.update_xaxes(tickvals=tv, ticktext=tt, title="")
    ad_g = ad_goster or ticker
    baslangic = df.index[X[0]].strftime("%Y-%m-%d"); bitis = df.index[i1].strftime("%Y-%m-%d")
    not_kutusu(fig, f"Tarayıcı: fraktal pivot n={n} → ardışık 5 pivot → oran testi (B/C/D/BC bantları, tolerans ~%5–8)<br>"
                    f"Bulunan: {'bullish' if yon=='bull' else 'bearish'} {a['pattern']} · B {a['rB']:.3f} · C {a['rC']:.3f} · D {a['rD']:.3f} XA · {a['rBC']:.2f} BC<br>"
                    f"D sonrası ({len(sonra)} bar): {sonuc}. Tek örnek — kanıt değil; başarı oranı ancak sabit kurallarla çok sayıda örnekte ölçülür.<br>"
                    f"Veri kaynağı: {kaynak}",
               x=0.5, y=-0.07, xanchor="center", yanchor="top", font=10)
    temel_layout(fig, f"Şekil {no:02d} — Gerçek veri — {ad_g}, {interval}, {baslangic} → {bitis}: tarayıcının bulduğu {'bullish' if yon=='bull' else 'bearish'} {a['pattern']}", 620,
                 "Zigzag pivotları + oran toleransı; PRZ pattern'in ideal sayılarıyla çizildi, sonuç dürüstçe işaretlendi")
    fig.update_yaxes(title="fiyat")
    kaydet(fig, dosya)
    RAPOR.append(f"GERÇEK ÖRNEK {no}: {ticker} {interval} n={n} → {yon} {a['pattern']} (B {a['rB']:.3f}, C {a['rC']:.3f}, D {a['rD']:.3f} XA, BC {a['rBC']:.2f}); "
                 f"X={df.index[X[0]]}, D={df.index[D[0]]}; sonuç: {sonuc}; kaynak: {kaynak}; aday sayısı (bu ayar): {len(adaylar)}")


def g26_zigzag_hassasiyet(no=26):
    df, kaynak = veri_getir("GC=F", "730d", "1h")
    if df is None:
        return
    # pencere: n=8 taramasının bulduğu en yeni pattern'in etrafı (~450 bar)
    adaylar = [a for a in tara(df, 8) if a["D"][0] <= len(df) - 120]
    merkez = adaylar[-1]["D"][0] if adaylar else len(df) - 120
    i1 = min(len(df) - 1, merkez + 110); i0 = max(0, i1 - 450)
    d_ = df.iloc[i0:i1 + 1]; xs = list(range(i0, i1 + 1))
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        subplot_titles=[f"pivot n = {n}" for n in (5, 8, 20)])
    tv, tt = _tarih_tikleri(df, i0, i1)
    for row, n in enumerate((5, 8, 20), start=1):
        fig.add_trace(mum_iz(d_, x=xs), row=row, col=1)
        pv = [p for p in pivotlar(df, n) if i0 <= p[0] <= i1]
        fig.add_trace(go.Scatter(x=[p[0] for p in pv], y=[p[1] for p in pv], mode="lines+markers", name=f"zigzag n={n} ({len(pv)} pivot)",
                                 line=dict(color=[R["mavi"], R["fvg"], R["dn"]][row - 1], width=1.8), marker=dict(size=5)), row=row, col=1)
        bulunan = [a for a in tara(df, n) if i0 <= a["X"][0] and a["D"][0] <= i1]
        for a in bulunan:
            pts = [a[k] for k in "XABCD"]
            fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines", name=f"{a['pattern']} ({a['yon']}) n={n}",
                                     line=dict(color=R["prz"], width=3), hoverinfo="skip", showlegend=False), row=row, col=1)
            fig.add_annotation(x=a["D"][0], y=a["D"][1], text=f"{a['pattern']}<br>{a['yon']}", showarrow=True, arrowhead=2, ax=0,
                               ay=30 if a["yon"] == "bull" else -30, font=dict(size=10, color=R["prz"]), row=row, col=1)
        not_kutusu(fig, f"{len(pv)} pivot · {len(bulunan)} pattern eşleşmesi", x=0.01, y=0.95, xanchor="left", yanchor="top", row=row, col=1, font=10)
        fig.update_yaxes(title="fiyat", row=row, col=1)
    fig.update_xaxes(tickvals=tv, ticktext=tt, row=3, col=1)
    temel_layout(fig, f"Şekil {no:02d} — Gerçek veri — GC=F (altın vadeli), 1h, {df.index[i0]:%Y-%m-%d} → {df.index[i1]:%Y-%m-%d}: pivot n = 5 / 8 / 20 aynı seriyi nasıl okur?", 900,
                 "Aynı seri, üç pivot ayarı: küçük n her salınımı pivot sayar (çok aday, 'yanlış X'); büyük n yapıyı seyreltir (az/hiç aday).<br>"
                 "Zigzag son pivotu n bar SONRA teyit eder → canlıda repaint. Kural: tarayıcı = aday listesi, manuel doğrula, 'confirmed bars only'. "
                 f"Kaynak: {kaynak}", lejant=True)
    fig.update_layout(margin=dict(b=110))
    kaydet(fig, f"{no:02d}_zigzag_hassasiyet_gercek")
    RAPOR.append(f"ZİGZAG GRAFİĞİ: GC=F 1h {df.index[i0]} → {df.index[i1]} ({len(d_)} bar); kaynak {kaynak}")


def tarama_ozeti():
    """Ders Bölüm 12.1'deki sayıların kaynağı: enstrüman × interval × n → aday sayısı (tüm tara() eşleşmeleri)."""
    setler = [("1d", "2y", ["EURUSD=X", "GC=F", "BTC-USD", "XU100.IS", "USDTRY=X"]),
              ("1h", "730d", ["EURUSD=X", "BTC-USD", "GC=F"])]
    ns = (5, 6, 8, 10, 12)
    satirlar = [f"TARAMA ÖZETİ (aday sayısı; pattern bantları TARAMA sözlüğü, C A'yı aşmaz) — n = {ns}"]
    for interval, period, tickers in setler:
        for t in tickers:
            df, kaynak = veri_getir(t, period, interval)
            if df is None:
                satirlar.append(f"  {t:10s} {interval}: veri yok")
                continue
            sayilar = []
            for n in ns:
                res = tara(df, n)
                pat = ",".join(sorted({r['pattern'] for r in res})) or "-"
                sayilar.append(f"n={n}: {len(res)} [{pat}]")
            satirlar.append(f"  {t:10s} {interval} ({len(df)} bar, {kaynak}): " + " · ".join(sayilar))
    RAPOR.extend(satirlar)
    (VERI / "tarama_ozeti.txt").write_text("\n".join(satirlar))


# ================================================================ ana
def main():
    g01_fib_turetim()
    g02_retracement()
    g03_extension()
    g04_projection()
    g05_abcd()
    g_pattern_cifti(6, "Gartley", "06_gartley", "Gartley: B = 0.618, D = 0.786 XA — bullish ve bearish")
    g_pattern_cifti(7, "Bat", "07_bat", "Bat: B = 0.382–0.50, D = 0.886 XA — bullish ve bearish")
    g08_altbat()
    g_pattern_cifti(9, "Butterfly", "09_butterfly", "Butterfly: B = 0.786, D = 1.272 XA — bullish ve bearish")
    g_pattern_cifti(10, "Crab", "10_crab", "Crab: B ≤ 0.618, D = 1.618 XA — bullish ve bearish")
    g11_deep_crab()
    g12_shark_50()
    g13_cypher()
    g14_three_drives()
    g15_hiyerarsi()
    g16_prz_insa()
    g17_prz_teyit_rsi()
    g18_giris_stop_hedef()
    g19_giris_turleri()
    g20_stop_yerlesimi()
    g21_type1_type2()
    g22_pozisyon_yonetimi()
    g23_basarisiz()
    g24_uyari_isaretleri()
    g25_olusum_asamali()
    g26_zigzag_hassasiyet(26)
    g27_mtf_fraktal()
    g28_smc_koprusu()
    gercek_ornek(29, "29_gercek_xu100_gunluk", "XU100.IS", "2y", "1d", 8, "Bat", min_sonra=10, ad_goster="BIST 100 (XU100.IS)")
    gercek_ornek(30, "30_gercek_btcusd_saatlik", "BTC-USD", "730d", "1h", 8, "Bat", min_sonra=60, ad_goster="BTC-USD")
    gercek_ornek(31, "31_gercek_altin_saatlik", "GC=F", "730d", "1h", 8, "Butterfly", min_sonra=60, ad_goster="GC=F (altın vadeli)")
    gercek_ornek(32, "32_gercek_eurusd_saatlik", "EURUSD=X", "730d", "1h", 8, "Gartley", min_sonra=60, ad_goster="EUR/USD")
    tarama_ozeti()
    print("\n=== ÜRETİLEN DOSYALAR ===")
    for u in URETILEN:
        print(u)
    print("\n=== RAPOR ===")
    for r in RAPOR:
        print(r)


if __name__ == "__main__":
    main()
