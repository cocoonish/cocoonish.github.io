#!/usr/bin/env python3
"""Türkiye Piyasa Tarihi — 1854–2001 arkı · UZUN UFUK grafik seti.

Tek komut:  python3 site/tools/ders_grafik/tarih_grafikler_derin.py
Çıktı:      site/public/arastirma/turkiye-piyasa-tarihi/DNN_ad.html

Bu modül `tarih_grafikler.py`'yi BOZMAZ; oradan yalnız yardımcıları (palet, düzen,
kaydet, dikey, not_) ödünç alır ve kendi figürlerini üretir. Dosya adları geçici
`DNN_` önekiyle yazılır; yazım aşamasında şekil numaraları belge sırasına göre
kesinleşince dosya adları / MDX `no` / metin atıfları BİRLİKTE güncellenir.

Kurallar (ders standardı):
  · Sentetik seri YOK. Seriler ya EVDS önbelleğinden (_tarih/*.csv) ya da
    kaynağı grafiğin altyazısında AÇIKÇA yazılı tarihsel tablolardan gelir.
  · Tarihsel tablolar bu dosyada elle kodlanmıştır; her tablonun üstünde kaynak
    künyesi vardır ve künye grafiğin altyazısına da basılır.
  · Kaynaklar çelişiyorsa İKİSİ DE çizilir ve "kaynaklar ayrışıyor" etiketlenir.
  · Paneller ALT ALTA: make_subplots(rows=N, cols=1). Yan yana panel yok.
  · Pencereler PİNLİ → çıktı deterministik.

Ev stili son rötuşu:
  cd site && python3 tools/plotly_stil.py public/arastirma/turkiye-piyasa-tarihi/*.html
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import tarih_veri as tv
from tarih_grafikler import (  # yardımcılar — mevcut ev stili
    ALTIN, BANT, BORDO, GRI, MAVI, MOR, MUREKKEP, TEAL, TURUNCU, YESIL,
    CIKTI, cizgi, dikey, duzen, endeksle, kes, not_, panel_basliklari, rgba,
    sifir_cizgisi, sutun,
)

warnings.filterwarnings("ignore")

BURASI = Path(__file__).resolve().parent
ONB = BURASI / "_tarih"

URETILEN: list[tuple[str, str, str]] = []
ATLANAN: list[str] = []


def tr(x: float, ond: int = 1) -> str:
    """Türkçe sayı biçimi: binlik ayracı NOKTA, ondalık ayracı VİRGÜL.

    Python'ın `{:,.1f}` çıktısı (4,018.6) İngilizce ayraçlar kullanır; yalnızca
    `.replace(",", ".")` demek ondalık noktayı da binlik ayracına çevirip
    "%4.018.6" gibi okunamaz metinler üretiyordu. İki ayraç birlikte takas edilir."""
    return f"{x:,.{ond}f}".replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")


def kaydet(fig, ad: str, baslik: str, pencere: str):
    panel_basliklari(fig)
    yol = CIKTI / f"{ad}.html"
    fig.write_html(str(yol), include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    URETILEN.append((yol.name, baslik, pencere))
    print(f"  ✓ {yol.name}")


# ======================================================================
#  VERİ KATMANI — EVDS önbelleği (_tarih/) + arşiv çekimleri
# ======================================================================
_C: dict[str, object] = {}


def _oku(dosya: str, tarih_kol: str = "dt") -> pd.DataFrame:
    d = pd.read_csv(ONB / dosya)
    if tarih_kol not in d.columns:                       # 'Tarih' biçimli arşiv CSV'si
        kol = [c for c in d.columns if c.lower().startswith("tarih")][0]
        t = d[kol].astype(str).str.strip()
        if t.str.match(r"^\d{4}-\d{1,2}$").all():
            d["dt"] = pd.to_datetime(t + "-01", errors="coerce")
        else:
            d["dt"] = pd.to_datetime(t, dayfirst=True, errors="coerce")
    else:
        d["dt"] = pd.to_datetime(d[tarih_kol])
    return d.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)


def S(ad: str) -> pd.DataFrame:
    """tarih_veri.py TARİF'indeki EVDS serisi (önbellekli)."""
    if ad not in _C:
        _C[ad] = tv.seri(ad).set_index("dt")
    return _C[ad]                                        # type: ignore[return-value]


def E(ad: str, seriler: list[str], bas: str, bit: str, adim: int = 10) -> pd.DataFrame:
    """TARİF dışı EVDS serisi — _tarih/ altına önbelleklenir."""
    k = f"E::{ad}"
    if k not in _C:
        _C[k] = tv.evds(ad, seriler, bas, bit, adim).set_index("dt")
    return _C[k]                                         # type: ignore[return-value]


# ---------------------------------------------------------------- kur
# 1946–1949: EVDS dışı. Kaynak: Tuna, S. (2007) — 7 Eylül 1946 devalüasyonu;
# TCMB açıklaması (Cumhuriyet, 8 Eylül 1946): 1 USD alış 130 kuruş → 280 kuruş,
# satış 282,80 kuruş; 9 Eylül 1946'dan itibaren dövizlerde prim uygulaması bitti.
KUR_1946 = pd.Series(
    {pd.Timestamp("1946-01-01"): 1.30, pd.Timestamp("1946-09-08"): 1.30,
     pd.Timestamp("1946-09-09"): 2.80, pd.Timestamp("1949-12-31"): 2.80})


def kur_uzun() -> pd.Series:
    """USD/TRY resmî alış kuru, YENİ TL cinsinden, 02.01.1950 → 21.08.2026.

    İki EVDS parçası eklemlenir: arşiv günlük seri (1950-01-02 → 1989-12-31,
    eski TL — 1e6'ya bölünerek yeni TL'ye çevrilir) ve TP.DK.USD.A.YTL
    (1990-01-02 →). Eklem noktası doğrulanmıştır: 31.12.1989 = 2.311,37 eski TL
    ve 02.01.1990 = 0,00231137 yeni TL — aynı sayı.
    1 YTL = 1.000.000 eski TL (2005 sıfır atma).
    """
    if "kur_uzun" not in _C:
        eski = _oku("usd_1950_1989.csv").set_index("dt")["eskiTL"].dropna() / 1e6
        yeni = _oku("kur.csv").set_index("dt")["DK.USD.A.YTL"].dropna()
        _C["kur_uzun"] = pd.concat([eski.loc[:"1989-12-31"],
                                    yeni.loc["1990-01-01":]]).sort_index()
    return _C["kur_uzun"]                                # type: ignore[return-value]


# ------------------------------------------------------------ fiyat düzeyi
def fiyat_endeksi() -> pd.Series:
    """Eklemlenmiş aylık fiyat düzeyi endeksi, 1963-01 = 100.

    1963-01 → 1967-12  İstanbul Toptan Eşya Fiyat Endeksi (EVDS TP.FG.T63)
    1968-01 → 1986-12  İTO Toptan Eşya Fiyat Endeksi, 1968=100 (TP.FG.C01)
    1987-01 → 2003-12  TÜFE 1987=100 (TP.FG.A01)
    2004-01 → 2005-12  TÜFE 2003=100 (TP.FG.J0)
    2006-01 →          TÜFE 2025=100 (TP.TUKFIY2025.GENEL)

    UYARI: 1987 öncesi TOPTAN EŞYA endeksidir — Türkiye'de aylık tüketici fiyat
    endeksi bu tarihten önce EVDS'te yoktur. Eklemleme oran (zincirleme) ile
    yapılır; seviyeler değil, YÜZDE DEĞİŞİMLER karşılaştırılabilir.
    """
    if "fiyat" in _C:
        return _C["fiyat"]                               # type: ignore[return-value]
    p63 = _oku("tefe63_ham.csv").set_index("dt")["TP_FG_T63"].dropna()
    pito = _oku("v80_ito_tefe.csv").set_index("dt")["FG_C01"].dropna()
    p87 = _oku("tufe87.csv").set_index("dt")["FG.A01"].dropna()
    p03 = _oku("tufe03.csv").set_index("dt")["FG.J0"].dropna()
    p25 = _oku("tufe25.csv").set_index("dt")["TUKFIY2025.GENEL"].dropna()

    parcalar = [("1963-01-01", "1967-12-01", p63),
                ("1968-01-01", "1986-12-01", pito),
                ("1987-01-01", "2003-12-01", p87),
                ("2004-01-01", "2005-12-01", p03),
                ("2006-01-01", "2026-12-01", p25)]
    out = None
    for bas, bit, s in parcalar:
        parca = s.loc[bas:bit]
        if out is None:
            out = 100 * parca / parca.iloc[0]
        else:
            # zincirleme: önceki parçanın son ayı ile bu parçanın ilk ayı hizalanır
            onceki_ay = out.index[-1]
            koprü = s.loc[:onceki_ay]
            olcek = out.iloc[-1] / koprü.iloc[-1] if len(koprü) else out.iloc[-1] / parca.iloc[0]
            out = pd.concat([out, parca * olcek])
    _C["fiyat"] = out.sort_index()
    return out


def enflasyon_yoy() -> pd.Series:
    p = fiyat_endeksi()
    return (100 * (p / p.shift(12) - 1)).dropna()


# ------------------------------------------------------------------ faiz
def gecelik(kol: str = "PY.P06.ON") -> pd.Series:
    return _oku("gecelik.csv").set_index("dt")[kol].dropna()


def mevduat_azami_12a() -> pd.Series:
    """Azami TL mevduat faizi — 12 ay (EVDS TP.FA.F07), aylık, 04.1984 – 12.1996.

    Bu dönemde mevduat faizi İDARİ TAVANDIR; bankaların fiilen ödediği faiz değil,
    izin verilen üst sınırdır. Reel getiri hesabı bu yüzden ÜST SINIRIN reel
    karşılığıdır — gerçek tasarrufçu getirisi bunun altındadır.
    """
    return _oku("v80_mevfaiz_tavan.csv").set_index("dt")["FA_F07"].dropna()


def mevduat_akim_12a() -> pd.Series:
    """Yeni açılan 6 aya kadar vadeli TL mevduata uygulanan ağırlıklı ortalama
    faiz (EVDS TP.TRY.MT06), haftalıktan ay ortalamasına — 2002-01 →."""
    s = S("mevfaiz_akim")["TRY.MT06"].dropna()
    return s.resample("MS").mean().dropna()


def fisher(i: pd.Series, pi: pd.Series) -> pd.Series:
    ort = i.dropna().index.intersection(pi.dropna().index)
    return (((1 + i.loc[ort] / 100) / (1 + pi.loc[ort] / 100) - 1) * 100).dropna()


# ======================================================================
#  REJİM BANTLARI — kur rejimi (1946 → bugün)
# ======================================================================
# Kaynaklar: TCMB, "Dünden Bugüne Türkiye Cumhuriyet Merkez Bankası";
# TCMB Kâğıt Paranın Tarihçesi; Tuna (2007); FRUS 1958–60 X/2 belge 322 (1958
# çoklu kur); EVDS TP.DK.USD.A.YTL basamakları (1960-08-22, 1970-08-10,
# 1971-12-23, 1980-01-25); 32 sayılı Karar (11.08.1989); 2000 programı ve
# 22.02.2001 dalgalı kura geçiş.
REJIM = [
    ("1946-09-09", "1958-08-03", "sabit parite 2,80", "#0f766e"),
    ("1958-08-03", "1960-08-22", "çoklu kur (fiilî deval.)", "#b45309"),
    ("1960-08-22", "1980-01-25", "ayarlanabilir sabit kur", "#1d4ed8"),
    ("1980-01-25", "1981-05-01", "24 Ocak: büyük adımlar", "#ea580c"),
    ("1981-05-01", "1989-08-11", "sürünen kur (günlük ilan)", "#6d28d9"),
    ("1989-08-11", "1994-01-26", "32 sayılı Karar: sermaye serbest", "#15803d"),
    ("1994-01-26", "1999-12-22", "kriz sonrası yönetimli kur", "#7f1d1d"),
    ("1999-12-22", "2001-02-22", "kur çıpası + genişleyen bant", "#b45309"),
    ("2001-02-22", "2026-08-21", "dalgalı kur", "#0f766e"),
]

# Uzun ufuk grafiklerinde etiketlenecek kırılmalar
OLAY = [
    ("1946-09-09", "09.09.1946 — prim sistemi kalktı, 1,30 → 2,80"),
    ("1958-08-03", "03.08.1958 — fiilî devalüasyon (çoklu kur)"),
    ("1960-08-22", "22.08.1960 — resmî parite 2,80 → 9,00"),
    ("1970-08-10", "10.08.1970 — 9,00 → 14,85"),
    ("1980-01-25", "25.01.1980 — 24 Ocak Kararları, 35 → 70"),
    ("1981-05-01", "05.1981 — günlük kur ilanı başladı"),
    ("1989-08-11", "11.08.1989 — 32 sayılı Karar"),
    ("1994-01-26", "26.01.1994 — devalüasyon"),
    ("1999-12-22", "22.12.1999 — kur çıpalı program"),
    ("2001-02-22", "22.02.2001 — dalgalı kura geçiş"),
    ("2018-08-10", "10.08.2018"),
    ("2021-09-23", "23.09.2021 — indirim serisi"),
    ("2023-06-22", "22.06.2023 — dönüş"),
]


def rejim_bantlari(fig, bas, bit, satir_sayisi=1, etiket_satiri=1, a=0.085):
    bas_, bit_ = pd.Timestamp(bas), pd.Timestamp(bit)
    for b, e, ad, renk in REJIM:
        b_, e_ = pd.Timestamp(b), pd.Timestamp(e)
        if e_ < bas_ or b_ > bit_:
            continue
        b_, e_ = max(b_, bas_), min(e_, bit_)
        for r in range(1, satir_sayisi + 1):
            if r == etiket_satiri:
                fig.add_vrect(x0=b_, x1=e_, fillcolor=rgba(renk, a), line_width=0,
                              layer="below", row=r, col=1,
                              annotation_text=ad, annotation_position="top left",
                              annotation=dict(font=dict(size=8.5, color=renk),
                                              textangle=-90, xanchor="left",
                                              yanchor="top"))
            else:
                fig.add_vrect(x0=b_, x1=e_, fillcolor=rgba(renk, a), line_width=0,
                              layer="below", row=r, col=1)


# ======================================================================
#  TARİHSEL TABLOLAR — elle kodlandı, kaynak künyesi her tablonun üstünde
# ======================================================================

# T1 · Gümrük tarifesi (%). Kaynak: Pamuk, Ş., "150. Yılında Baltalimanı Ticaret
# Antlaşması", s.30–31. Not: kaynak metninin PDF çıktısında 1860–61 indiriminin
# hangi vergide olduğu konusunda içsel tutarsızlık vardır; içsel tutarlı okuma
# %12 → %1 indiriminin İHRACAT vergisinde olduğudur (aşağıdaki tablo bu okumadır).
T_TARIFE = pd.DataFrame({
    "yil":      [1830, 1838, 1861, 1905, 1908, 1914],
    "ihracat":  [3,    12,   1,    1,    1,    1],
    "ithalat":  [3,    5,    8,    11,   15,   15],
})

# T2 · Osmanlı istikrazları 1854–1874. Kaynak: Eldem, V. (1970), s.160–161;
# Dikmen (2005), Tablo 2 üzerinden. Birim: milyon Fransız frangı.
# 1863 için kaynak iki emisyon kuru verir (%68 ve %72); tabloda ele geçen /
# nominal = 142/200 = %71,0 kullanılmıştır ve grafikte not düşülür.
T_ISTIKRAZ = pd.DataFrame({
    "etiket":  ["1854", "1855", "1858", "1860", "1862", "1863", "1865",
                "1865 (umumi)", "1869", "1870–72", "1871", "1872", "1873", "1874"],
    "nominal": [75.0, 125.0, 125.0, 50.0, 200.0, 200.0, 150.0,
                909.1, 555.6, 792.0, 143.5, 278.2, 694.4, 1000.0],
    "gelen":   [60.0, 125.0, 95.0, 31.8, 136.0, 142.0, 99.0,
                454.5, 388.1, 254.4, 104.0, 273.9, 414.2, 435.0],
    "fiyat":   [80.0, 100.0, 76.0, 63.5, 68.0, 71.0, 66.0,
                50.0, 61.0, 32.125, 73.0, 98.5, 59.5, 43.5],
})

# T3 · Dış borç stokunun kilometre taşları. Birim: milyon (altın) Osmanlı lirası.
# Kaynak: Arslan, İ. (2015), Journal of History Studies 7/4 (Yeniay ve Eldem'den);
# Dikmen (2005) s.143–150; TDV İslâm Ansiklopedisi, "Düyûn-ı Umûmiyye".
# 1881 öncesi/sonrası için kaynaklar AYRIŞIR — üç/iki değer de tabloda tutulur.
T_STOK = pd.DataFrame({
    "etiket": ["1854\nilk istikraz", "1874\n20 yıl toplamı", "1875\nmoratoryum",
               "1881\nMuharrem sonrası", "1914\nsavaş başı", "1918\nsavaş sonu",
               "1918+\nİtilaf düzenlemesi", "1925\nLozan (Türkiye payı)",
               "1928\nParis Sözleşmesi", "1933\nParis (yeniden yapılandırma)",
               "1954\nödeme tamam"],
    "deger":  [3.30, 238.77, 238.77, 106.44, 153.70, 303.70, 161.85, 105.56,
               107.53, 8.58, 0.0],
})
# 1881 kaynak ayrışması (öncesi → sonrası), milyon OL
T_MUHARREM = pd.DataFrame({
    "kaynak":  ["Yeniay / Arslan (2015)", "TDV İslâm Ansiklopedisi", "Dikmen (2005)"],
    "oncesi":  [238.77, 219.94, 252.80],
    "sonrasi": [106.44, 125.25, np.nan],
})

# T4 · Borç servisi ve gelir kesitleri. Kaynak: Kıray, E. (1993), s.145
# (Dikmen 2005'ten); Dikmen (2005) s.147 oranları; Pamuk aktarımı (1875).
# SEYREK SERİ: yalnız kaynaklı yıllar noktalanır, ara yıllar UYDURULMAZ.
T_SERVIS = pd.DataFrame({
    "yil":   [1865, 1874, 1875],
    "oran":  [25.0, 57.0, 60.0],           # borç faizi / hükümet geliri, %
    "not_":  ["1865'ten itibaren alarm eşiği (%25)",
              "1874: faiz/hükümet geliri %57 · faiz/ihracat %66",
              "1875: yıllık anapara+faiz 11 mn £, gelir 18 mn £ → %60"],
})

# T5 · Düyun-u Umumiye'nin devlet gelirleri içindeki payı, 1911/12 mali yılı.
# Kaynak: İnce, M., "Devlet Borçlanması", s.65 → Dikmen (2005), Tablo 5.
# Birim: bin altın Osmanlı lirası.
T_DUYUN = pd.DataFrame({
    "kalem":   ["Vasıtasız vergiler", "Damga vergisi", "Vasıtalı vergiler",
                "İnhisarlar (tekeller)", "TOPLAM"],
    "toplam":  [16230, 1451, 5512, 2697, 25890],
    "du":      [3728, 574, 1714, 2146, 8162],
})
T_DUYUN["pay"] = 100 * T_DUYUN["du"] / T_DUYUN["toplam"]

# T6 · Lozan borcunun ödeme takvimi (13 Haziran 1928 Paris Sözleşmesi).
# Kaynak: Arslan, İ. (2015). Birim: altın lira / yıl.
# NOT: bu tablo HENÜZ BİR FİGÜRDE KULLANILMIYOR. Yazım aşamasında "1929 taksidi
# ödenmedi → 1/3 oranında ödeme → 1933'te %92 kesinti" anlatısı için ayrı bir panel
# istenirse hazır duruyor (planlanan taksit vs fiilen ödenen).
T_TAKSIT = pd.DataFrame({
    "bas":    [1929, 1936, 1942, 1947, 1952],
    "bit":    [1936, 1942, 1947, 1952, 1955],
    "taksit": [2_000_000, 2_380_000, 2_780_000, 3_180_000, 3_400_000],
})


# ======================================================================
#  D01 — Uzun ufuk kur
# ======================================================================
def d01():
    bas, bit = "1946-01-01", "2026-08-21"
    # ESKİ TL ile çizilir (yeni TL'de eksen 0,0000028 – 47,86 arasına yayılıyor ve
    # tikler mikro önekiyle okunmaz hâle geliyor). Eski TL, dönemin kendi birimidir:
    # 1946'da 2,80 lira, bugün 47,9 milyon lira. 1 YTL = 1.000.000 eski TL (2005).
    k = kes(kur_uzun(), "1950-01-01", bit) * 1e6

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.10,
        subplot_titles=(
            "1 ABD doları kaç TL? — resmî alış kuru, ESKİ TL, LOGARİTMİK eksen "
            "(bugünkü TL = eski TL ÷ 1.000.000). Gölgeli bantlar kur rejimini gösterir",
            "Yıl sonundan yıl sonuna USD/TRY değişimi (%) — sabit kur rejiminde "
            "yıllarca sıfır, ayarlama geldiğinde tek adımda"))

    # 1946–1949 EVDS dışı basamak (kesik çizgi + kaynak notu)
    fig.add_trace(go.Scatter(x=KUR_1946.index, y=KUR_1946.values,
                             name="1946–1949 (EVDS dışı · kaynak: Tuna 2007)",
                             mode="lines", line=dict(color=GRI, width=1.6, dash="dot",
                                                     shape="hv"),
                             hovertemplate="%{y:.2f} eski TL<extra>EVDS dışı</extra>"),
                  row=1, col=1)
    cizgi(fig, k, "USD/TRY resmî alış (EVDS TP.DK.USD.A.YTL, eski TL)", TEAL,
          row=1, w=1.7)

    yil_son = k.resample("YE").last()
    deg = (100 * (yil_son / yil_son.shift(1) - 1)).dropna()
    deg.index = deg.index.year
    renkler = [BORDO if v > 50 else (TURUNCU if v > 1 else
               (rgba(GRI, 0.55) if abs(v) <= 1 else YESIL)) for v in deg.values]
    sutun(fig, deg, "yıllık % değişim", TURUNCU, row=2, renkler=renkler, birim="%")
    sifir_cizgisi(fig, row=2)

    rejim_bantlari(fig, "1946-01-01", bit, satir_sayisi=1, etiket_satiri=1)

    for t, etiket in OLAY:
        if pd.Timestamp(t) < pd.Timestamp("1946-01-01"):
            continue
        if etiket.count("—") == 0:                      # kısa etiketler atlanır
            continue
        dikey(fig, t, "", row=1, renk=rgba(MUREKKEP, 0.45), dash="dot")

    # seviye anotasyonları — hepsi seriden okunuyor
    for t, bicim, ay in [("1960-08-22", "22.08.1960: 2,80 → 9,00", 46),
                         ("1970-08-10", "10.08.1970: 9,00 → 14,85", -34),
                         ("1980-01-25", "25.01.1980: 35 → 70 (24 Ocak)", 52),
                         ("1994-04-07", "07.04.1994 zirve: 39.853", -36),
                         ("2001-02-22", "22.02.2001: dalgalı kura geçiş", 54)]:
        ts = pd.Timestamp(t)
        yakin = k.loc[:ts]
        if not len(yakin):
            continue
        not_(fig, ts, np.log10(yakin.iloc[-1]), bicim, row=1, ay=ay, boyut=9.5,
             renk=MUREKKEP)
    son = k.dropna().index[-1]
    not_(fig, son, np.log10(k.loc[son]),
         (f"{son.strftime('%d.%m.%Y')}: {tr(k.loc[son], 0)} eski TL "
          f"= {tr(k.loc[son] / 1e6, 2)} TL"),
         row=1, ay=-34, boyut=10, xanchor="right", renk=TEAL)

    fig.update_yaxes(type="log", title_text="eski TL (log)", row=1,
                     tickvals=[1, 10, 100, 1e3, 1e4, 1e5, 1e6, 1e7],
                     ticktext=["1", "10", "100", "1.000", "10.000", "100.000",
                               "1 milyon", "10 milyon"])
    fig.update_yaxes(title_text="%", row=2)
    fig.update_xaxes(title_text="tarih", row=1,
                     range=[pd.Timestamp("1946-01-01"), pd.Timestamp(bit)])
    fig.update_xaxes(title_text="yıl", row=2, dtick=5)
    duzen(fig, "Seksen yılda bir milyon kat: TL/USD'nin uzun ufku",
          "1946 – 21.08.2026", 900,
          alt="EVDS TP.DK.USD.A.YTL (arşiv günlük seri 02.01.1950'de başlar) · "
              "1946–1949 basamağı EVDS dışıdır: TCMB açıklaması, Cumhuriyet 8.9.1946 "
              "→ Tuna (2007) s.97 · rejim bantları: TCMB 'Dünden Bugüne TCMB', "
              "FRUS 1958–60 X/2 blg.322, 32 sayılı Karar")
    kaydet(fig, "D01_uzun_ufuk_kur", "TL/USD'nin uzun ufku ve kur rejimleri",
           "1946 → 2026-08")


# ======================================================================
#  D02 — Uzun ufuk enflasyon
# ======================================================================
def d02():
    bas, bit = "1964-01-01", "2026-08-21"
    pi = kes(enflasyon_yoy(), bas, bit)
    p = kes(fiyat_endeksi(), bas, bit)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.085,
        subplot_titles=(
            "Yıllık enflasyon (%) — 1964–1986 toptan eşya, 1987'den itibaren TÜFE "
            "(eklemlenmiş). Gölgeli bantlar kur rejimini gösterir",
            "Fiyat düzeyi, 1963-01 = 100, LOGARİTMİK — eğimin kendisi enflasyondur"))

    cizgi(fig, pi, "yıllık enflasyon (%)", ALTIN, row=1, w=1.7)
    fig.add_hline(y=0, line=dict(color=rgba(MUREKKEP, 0.5), width=1.2), row=1, col=1)
    for e in (25, 50, 100):
        fig.add_hline(y=e, line=dict(color=rgba(GRI, 0.45), width=1, dash="dot"),
                      row=1, col=1)
    cizgi(fig, p, "fiyat düzeyi (1963-01 = 100)", BORDO, row=2, w=1.7)

    rejim_bantlari(fig, bas, bit, satir_sayisi=2, etiket_satiri=1)

    # zirveler seriden okunur — elle sayı girilmez
    for pencere, etiket in [(("1994-01-01", "1995-06-30"), "1994–95"),
                            (("2001-01-01", "2002-06-30"), "2001–02"),
                            (("1980-01-01", "1981-06-30"), "1980"),
                            (("2022-01-01", "2023-12-31"), "2022"),
                            (("2024-01-01", "2024-12-31"), "2024")]:
        alt = kes(pi, *pencere)
        if not len(alt):
            continue
        t = alt.idxmax()
        not_(fig, t, alt.max(),
             f"{etiket} zirve: %{tr(alt.max(), 1)}",
             row=1, ay=-32, boyut=9.5)
    dip = kes(pi, "2004-01-01", "2019-12-31")
    if len(dip):
        t = dip.idxmin()
        not_(fig, t, dip.min(), f"{t.strftime('%m.%Y')} dip: %{tr(dip.min(), 1)}",
             row=1, ay=44, boyut=9.5, renk=YESIL)

    kat = p.iloc[-1] / p.iloc[0]
    not_(fig, p.index[-1], np.log10(p.iloc[-1]),
         f"1963'ten bu yana fiyat düzeyi ×{tr(kat, 0)}",
         row=2, ay=-30, boyut=10, xanchor="right", renk=BORDO)

    fig.update_yaxes(title_text="%", row=1)
    fig.update_yaxes(type="log", title_text="endeks (log)", row=2)
    fig.update_xaxes(title_text="tarih", row=2)
    duzen(fig, "Enflasyonun altmış yılı: iki zirve, bir plato, bir dönüş",
          "01.1964 – 08.2026", 900,
          alt="EVDS TP.FG.T63 (İstanbul TEFE, 1963–67) · TP.FG.C01 (İTO TEFE 1968=100, "
              "1968–86) · TP.FG.A01 (TÜFE 1987=100) · TP.FG.J0 (TÜFE 2003=100) · "
              "TP.TUKFIY2025.GENEL — oran zincirlemesiyle eklemlendi; 1987 öncesi "
              "TOPTAN EŞYA endeksidir, tüketici endeksiyle birebir karşılaştırılamaz")
    kaydet(fig, "D02_uzun_ufuk_enflasyon", "Yıllık enflasyon ve fiyat düzeyi, 1964–2026",
           "1964-01 → 2026-08")


# ======================================================================
#  D03 — Reel getirinin uzun ufku ve mali baskınlık
# ======================================================================
def d03():
    bas, bit = "1985-01-01", "2026-08-21"
    pi = enflasyon_yoy()

    tavan = mevduat_azami_12a()                          # 1984-04 → 1996-12
    akim = mevduat_akim_12a()                            # 2002-01 →
    reel_tavan = kes(fisher(tavan, pi), bas, "1996-12-31")
    reel_akim = kes(fisher(akim, pi), "2002-01-01", bit)
    g = gecelik().resample("MS").mean()
    reel_on = kes(fisher(g, pi), "1990-01-01", bit)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        subplot_titles=(
            "Nominal: azami 12 ay TL mevduat faizi (1984–96, İDARİ TAVAN) · yeni açılan "
            "mevduat faizi (2002→) · gecelik para piyasası faizi — yanında yıllık enflasyon",
            "Ex-post REEL mevduat faizi (%, Fisher: (1+i)/(1+π)−1) — negatif bölge, "
            "tasarrufun enflasyona vergi ödediği dönemdir",
            "Mali baskınlığın muhasebe kaydı: TCMB'nin Hazine'den alacakları / Emisyon "
            "(EVDS TP.AB.A05 / TP.AB.A17, iş günü)"))

    cizgi(fig, kes(tavan, bas, "1996-12-31"), "azami mevduat faizi, 12 ay (%)", MOR, row=1, w=1.6)
    cizgi(fig, kes(akim, "2002-01-01", bit), "yeni mevduat faizi, ≤6 ay (%)", MAVI, row=1, w=1.6)
    cizgi(fig, kes(g, "1990-01-01", bit), "gecelik faiz, ay ort. (%)", BORDO, row=1, w=1.2)
    cizgi(fig, kes(pi, bas, bit), "yıllık enflasyon (%)", ALTIN, row=1, w=1.8, dash="dot")

    fig.add_trace(go.Scatter(x=reel_tavan.index, y=reel_tavan.values,
                             name="reel mevduat faizi — tavan (1985–96)", mode="lines",
                             line=dict(color=MOR, width=1.9), fill="tozeroy",
                             fillcolor=rgba(MOR, 0.15),
                             hovertemplate="%{y:.1f}%<extra>reel (tavan)</extra>"),
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=reel_akim.index, y=reel_akim.values,
                             name="reel mevduat faizi — akım (2002→)", mode="lines",
                             line=dict(color=MAVI, width=1.9), fill="tozeroy",
                             fillcolor=rgba(MAVI, 0.15),
                             hovertemplate="%{y:.1f}%<extra>reel (akım)</extra>"),
                  row=2, col=1)
    cizgi(fig, reel_on.clip(-70, 70), "reel gecelik faiz (%, ±%70'te kırpıldı)",
          BORDO, row=2, w=1.0, dash="dot")
    sifir_cizgisi(fig, row=2)

    ab = _oku("v80_ab.csv").set_index("dt")
    oran = (ab["AB_A05"] / ab["AB_A17"]).dropna()
    cizgi(fig, kes(oran, "1985-01-01", "1996-12-31"),
          "Hazine alacakları / Emisyon (kat)", TURUNCU, row=3, w=1.7)
    fig.add_hline(y=1.0, line=dict(color=rgba(MUREKKEP, 0.5), width=1.2, dash="dash"),
                  row=3, col=1)
    zirve = kes(oran, "1993-01-01", "1995-12-31")
    if len(zirve):
        t = zirve.idxmax()
        not_(fig, t, zirve.max(), f"{t.strftime('%m.%Y')} zirve: {tr(zirve.max(), 2)}×",
             row=3, ay=-30, boyut=9.5, renk=TURUNCU)
    # Panelin 1997 sonrası boşluğu VERİ EKSİKLİĞİ değil, kurumsal sonucun kendisidir:
    # kanal üç aşamada kapatıldı. Boşluk, üç dikey çizgi ve bir kutuyla anlatılıyor.
    for tarih, etiket in [
            ("1994-04-21", "21.04.1994 — Hazine'nin TCMB kaynağı kullanımına SINIR"),
            ("1997-01-01", "1997 — TCMB–Hazine protokolü: 1998'den itibaren avans YOK"),
            ("2001-04-25", "25.04.2001 — 4651 s.K.: avans ve birincil piyasadan "
                           "alım YASAK")]:
        dikey(fig, tarih, etiket, row=3, renk=BORDO, boyut=8.2)
    fig.add_annotation(x=pd.Timestamp("2004-01-01"), y=2.6, xanchor="left",
                       yanchor="top", align="left", showarrow=False,
                       text="Bu paneldeki seri <b>12.1996'da biter</b>. Boşluk veri "
                            "eksikliği değildir: mali baskınlık kanalı üç aşamada "
                            "kapatıldı<br>(1994 sınır → 1997 protokol → 2001 kanun). "
                            "Kaynak: TCMB, <i>Dünden Bugüne TCMB</i>, ss. 11, 13.<br>"
                            "2001 sonrası analitik bilanço kalemleri yeniden "
                            "tanımlandığı için aynı oran doğrudan sürdürülmemiştir.",
                       font=dict(size=9.5, color=MUREKKEP),
                       bgcolor="rgba(255,255,255,0.86)", bordercolor=rgba(GRI, 0.4),
                       borderwidth=0.8, borderpad=4, row=3, col=1)

    rejim_bantlari(fig, bas, bit, satir_sayisi=2, etiket_satiri=1)

    fig.update_yaxes(type="log", title_text="% (log)", row=1)
    fig.update_yaxes(title_text="%", row=2, range=[-72, 72])
    fig.update_yaxes(title_text="kat", row=3)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Tasarrufun reel getirisi ve mali baskınlık: kırk yılın tek ekranı",
          "01.1985 – 08.2026", 1180,
          alt="EVDS TP.FA.F07 (azami mevduat faizi, 1984-04→1996-12) · TP.TRY.MT06 "
              "(yeni açılan mevduat, haftalıktan ay ort.) · TP.PY.P06.ON · "
              "TP.AB.A05 / TP.AB.A17 (analitik bilanço, iş günü) · enflasyon: D02 "
              "eklemlenmiş endeksi · 1984–96 mevduat faizi İDARİ TAVANDIR, fiilî "
              "ödenen faiz değildir")
    kaydet(fig, "D03_reel_getiri_mali_baskinlik",
           "Reel mevduat getirisi ve mali baskınlık, 1985–2026", "1985-01 → 2026-08")


# ======================================================================
#  D04 — Kriz karşılaştırma paneli (DERSİN OMURGASI)
# ======================================================================
KRIZ = [
    ("1993-12-31", "1994 · t₀ = 31.12.1993 (kriz öncesi son iş günü)", BORDO),
    ("2001-02-16", "2001 · t₀ = 16.02.2001 (kriz öncesi son Cuma)", MOR),
    ("2018-08-09", "2018 · t₀ = 09.08.2018 (kriz öncesi son iş günü)", TURUNCU),
    ("2021-09-23", "2021 · t₀ = 23.09.2021 (indirim serisinin ilk günü)", TEAL),
]
UFUK = 250      # iş günü


def _hizala(s: pd.Series, t0: str, n: int = UFUK, endeks=True) -> pd.Series:
    """t₀'dan itibaren n GÖZLEM (iş günü) — t=0'da 100'e endeksli."""
    t = pd.Timestamp(t0)
    onceki = s.loc[:t]
    if not len(onceki):
        return pd.Series(dtype=float)
    taban = onceki.iloc[-1]
    ileri = s.loc[t:].iloc[:n + 1]
    out = (100 * ileri / taban) if endeks else ileri
    out.index = range(len(out))
    return out


def d04():
    k = kur_uzun()
    g = gecelik()
    bist = _oku("bist.csv").set_index("dt")["MK.F.BILESIK"].dropna()
    bist_usd = (bist / k.reindex(bist.index).ffill()).dropna()

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.065,
        subplot_titles=(
            "USD/TRY — t₀ = 100, LOGARİTMİK. Aynı ölçekte dört kriz",
            "Bankalararası gecelik faiz (%, ağırlıklı ortalama) — LOGARİTMİK, "
            "seviye olarak (endekslenmemiş)",
            "BIST-100, DOLAR bazında — t₀ = 100, logaritmik"))

    for t0, ad, renk in KRIZ:
        for row, seri, endeks in ((1, k, True), (2, g, False), (3, bist_usd, True)):
            s = _hizala(seri, t0, endeks=endeks)
            if not len(s):
                ATLANAN.append(f"D04 — {ad}: panel {row} için veri yok")
                continue
            fig.add_trace(go.Scatter(
                x=s.index, y=s.values, name=ad, mode="lines",
                line=dict(color=renk, width=1.9),
                showlegend=(row == 1),
                hovertemplate="t+%{x} → %{y:.1f}<extra>" + ad.split(" ·")[0] + "</extra>"),
                row=row, col=1)

    for row in (1, 3):
        fig.add_hline(y=100, line=dict(color=rgba(MUREKKEP, 0.5), width=1.2),
                      row=row, col=1)
    for row in (1, 2, 3):
        fig.add_vline(x=0, line=dict(color=rgba(MUREKKEP, 0.45), width=1.2, dash="dash"),
                      row=row, col=1)

    # her krizin 250. gündeki kur seviyesi — seriden okunur
    for t0, ad, renk in KRIZ:
        s = _hizala(k, t0)
        if not len(s):
            continue
        son = s.index[-1]
        not_(fig, son, np.log10(s.iloc[-1]),
             f"{ad.split(' ·')[0]}: t+{son} → {tr(s.iloc[-1], 0)}",
             row=1, ay=-16, boyut=9.5, renk=renk, xanchor="right")

    fig.update_yaxes(type="log", title_text="endeks (t₀ = 100, log)", row=1)
    fig.update_yaxes(type="log", title_text="% (log)", row=2)
    fig.update_yaxes(type="log", title_text="endeks (t₀ = 100, log)", row=3)
    fig.update_xaxes(title_text="t₀'dan sonraki iş günü sayısı", row=3, dtick=25)
    duzen(fig, "Dört kriz, tek ölçek: 1994 · 2001 · 2018 · 2021",
          "her epizot kendi t₀'ından 250 iş günü", 1150,
          alt="EVDS TP.DK.USD.A.YTL (arşiv seri 1950'den) · TP.PY.P06.ON · "
              "TP.MK.F.BILESIK · dolar bazlı BIST = endeks ÷ aynı günün USD/TRY'si · "
              "t₀ seçimleri lejantta yazılıdır ve tartışmaya açıktır: farklı t₀ "
              "eğrilerin başlangıç eğimini değiştirir, sıralamasını değiştirmez",
          legend_y=-0.055)
    kaydet(fig, "D04_kriz_karsilastirma",
           "Dört krizin t₀ hizalı karşılaştırması (kur · gecelik faiz · BIST-USD)",
           "t₀ + 250 iş günü")


# ======================================================================
#  D05 — Kur ne zaman "fiyat" oldu?
# ======================================================================
def d05():
    bas, bit = "1950-01-01", "1996-12-31"
    k = kes(kur_uzun(), bas, bit) * 1e6                  # eski TL — dönemin birimi
    degisti = (k.diff() != 0) & k.diff().notna()
    sayim = degisti.groupby(degisti.index.year).sum()
    gozlem = k.groupby(k.index.year).count()
    pi = kes(enflasyon_yoy(), "1964-01-01", bit)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=False, vertical_spacing=0.085,
        subplot_titles=(
            "USD/TRY resmî alış kuru, ESKİ TL, logaritmik — basamaklar açıkça görünür",
            "Yıl içinde kurun DEĞİŞTİĞİ gün sayısı — rejim değişimi tek bakışta "
            "(gri: o yıl kaydedilen toplam gözlem sayısı)",
            "Yıllık enflasyon (%) — kur sabitken fiyatlar durmadı"))

    cizgi(fig, k, "USD/TRY (eski TL)", TEAL, row=1, w=1.7)
    sutun(fig, gozlem, "yıl içi gözlem sayısı", rgba(GRI, 0.35), row=2, birim=" gün")
    sutun(fig, sayim, "kurun değiştiği gün sayısı", TURUNCU, row=2, birim=" gün")
    cizgi(fig, pi, "yıllık enflasyon (%)", ALTIN, row=3, w=1.7)
    fig.add_hline(y=0, line=dict(color=rgba(MUREKKEP, 0.5), width=1.2), row=3, col=1)

    # Etiketler dönüşümlü iki yükseklikte: yan yana düşen olaylarda (1979/1980/1981
    # ve 1989/1994) tek hizada yazıldıklarında birbirinin üstüne biniyorlardı.
    for i, (t_, etiket) in enumerate([
            ("1958-08-03", "03.08.1958 — fiilî devalüasyon, çoklu kur "
                           "(ithalat 9,00; ihracat 4,90/5,60/9,00)"),
            ("1960-08-22", "22.08.1960 — resmî parite birleşti: 2,80 → 9,00"),
            ("1970-08-10", "10.08.1970 — 9,00 → 14,85"),
            ("1971-12-23", "23.12.1971 — Smithsonian: TL/USD DÜŞTÜ"),
            ("1979-06-12", "12.06.1979 — 26,50 → 35,00"),
            ("1980-01-25", "25.01.1980 — 24 Ocak: 35,00 → 70,00"),
            ("1981-05-01", "05.1981 — günlük kur ilanı"),
            ("1989-08-11", "11.08.1989 — 32 sayılı Karar"),
            ("1994-01-26", "26.01.1994 — devalüasyon")]):
        dikey(fig, t_, etiket, row=1, renk=BORDO, boyut=8.2,
              y_konum=1.0 if i % 2 == 0 else 0.62)

    ilk_yil = int(sayim[sayim > 100].index.min()) if (sayim > 100).any() else None
    if ilk_yil:
        not_(fig, ilk_yil, sayim.loc[ilk_yil],
             f"{ilk_yil}: {int(sayim.loc[ilk_yil])} gün — kur artık bir fiyat",
             row=2, ay=-34, boyut=10, renk=TURUNCU)
    sifir_yillar = sayim.loc[:1959]
    fig.add_annotation(x=1954, y=max(gozlem.max() * 0.75, 1), xref="x2", yref="y2",
                       text=f"1950–1959: kur {int(sifir_yillar.sum())} gün değişti",
                       showarrow=False, font=dict(size=10, color=GRI),
                       row=2, col=1)

    fig.update_yaxes(type="log", title_text="eski TL (log)", row=1,
                     tickvals=[1, 10, 100, 1e3, 1e4, 1e5],
                     ticktext=["1", "10", "100", "1.000", "10.000", "100.000"])
    fig.update_yaxes(title_text="gün", row=2)
    fig.update_yaxes(title_text="%", row=3)
    fig.update_xaxes(title_text="tarih", row=1)
    fig.update_xaxes(title_text="yıl", row=2, dtick=5)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Kur ne zaman bir fiyat oldu? 1950–1996",
          "02.01.1950 – 31.12.1996", 1150,
          alt="EVDS TP.DK.USD.A.YTL (arşiv günlük seri) · 'değiştiği gün' = kotasyonun "
              "bir önceki gözlemden farklı olduğu gün · 1958 çoklu kur bilgisi: FRUS "
              "1958–60 X/2 blg.322 · enflasyon: D02 eklemlenmiş endeksi (1964'ten)")
    kaydet(fig, "D05_kur_fiyat_oldugu_gun", "Kur ne zaman fiyat oldu? 1950–1996",
           "1950-01 → 1996-12")


# ======================================================================
#  D06 — Gecelik faizin uzun ufku
# ======================================================================
def d06():
    bas, bit = "1990-01-01", "2026-08-21"
    ao = kes(gecelik("PY.P06.ON"), bas, bit)
    enY_g = kes(gecelik("PY.P05.ON"), bas, bit)
    enD_g = kes(gecelik("PY.P04.ON"), bas, bit)
    hac_g = kes(gecelik("PY.P03.ON"), bas, bit)
    # Zarf ve hacim HAFTALIK özetlenir: 36 yıllık günlük seri dört iz hâlinde
    # ~1 MB'lık bir veri bloğu üretiyordu. Ağırlıklı ortalama günlük kalır
    # (mesajın taşıyıcısı o); zarf haftanın uç değerleriyle çizilir — uç değer
    # KAYBOLMAZ, yalnız ara günler seyreltilir.
    enY = enY_g.resample("W").max().dropna()
    enD = enD_g.resample("W").min().dropna()
    hac = hac_g.resample("W").mean().dropna()

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        subplot_titles=(
            "Bankalararası gecelik faiz — ağırlıklı ortalama ve gün içi menzil "
            "(en düşük–en yüksek gerçekleşen işlem), LOGARİTMİK",
            "Gün içi menzil (en yüksek ÷ en düşük, kat) — stresin saf ölçüsü",
            "Gecelik işlem hacmi (bin TL, hafta ortalaması, logaritmik) — fiyat fırlarken miktar ne yaptı?"))

    fig.add_trace(go.Scatter(x=enY.index, y=enY.values,
                             name="en yüksek işlem faizi (%, hafta maks.)",
                             mode="lines", line=dict(color=rgba(BORDO, 0.32), width=0.9),
                             hovertemplate="%{y:.1f}%<extra>en yüksek</extra>"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=enD.index, y=enD.values,
                             name="en düşük işlem faizi (%, hafta min.)",
                             mode="lines", line=dict(color=rgba(MAVI, 0.32), width=0.9),
                             hovertemplate="%{y:.1f}%<extra>en düşük</extra>"),
                  row=1, col=1)
    cizgi(fig, ao, "ağırlıklı ortalama (%, günlük)", BORDO, row=1, w=1.4)

    # menzil GÜNLÜK hesaplanır (gün içi stresin ölçüsü), sonra haftanın maksimumu alınır
    menzil = (enY_g / enD_g.replace(0, np.nan)).dropna().resample("W").max().dropna()
    cizgi(fig, menzil, "gün içi menzil, hafta maks. (kat)", MOR, row=2, w=1.0)
    fig.add_hline(y=1, line=dict(color=rgba(MUREKKEP, 0.45), width=1.1), row=2, col=1)
    cizgi(fig, hac, "gecelik işlem hacmi (bin TL, hafta ort.)", TEAL, row=3, w=1.2)

    # Etiket sayısı bilinçli olarak DAR tutuldu: altı epizot yan yana yazıldığında
    # 1994–2001 bölgesinde hepsi üst üste biniyordu. Kalanlar hover'da okunur.
    for pencere, ad, ay in [(("1994-01-01", "1994-06-30"), "1994", -30),
                            (("2001-02-01", "2001-04-30"), "Şubat 2001", -64),
                            (("2019-03-01", "2019-04-30"), "Mart 2019", -34),
                            (("2023-06-01", "2024-06-30"), "2023–24 sıkılaşma", -34)]:
        alt_ao = kes(ao, *pencere)
        alt_yk = kes(enY, *pencere)
        if not len(alt_ao):
            continue
        tz = alt_ao.idxmax()
        metin = f"{ad} — AO zirve %{tr(alt_ao.max(), 1)}"
        if len(alt_yk):
            metin += f" · en yüksek %{tr(alt_yk.max(), 0)}"
        not_(fig, tz, np.log10(max(alt_ao.max(), 1e-6)), metin, row=1,
             ay=ay, boyut=9.5)

    fig.add_annotation(
        x=pd.Timestamp("2026-06-01"), y=np.log10(1.6), xanchor="right", yanchor="bottom",
        text="Mart 2019'da asıl sıkışma <b>offshore (Londra) TL swap</b> faizindeydi; "
             "o oran EVDS'te YOKTUR — bu grafikte yalnız yurt içi gecelik faiz görünür.",
        showarrow=False, align="right", font=dict(size=9.5, color=GRI),
        bgcolor="rgba(255,255,255,0.86)", bordercolor=rgba(GRI, 0.35),
        borderwidth=0.8, borderpad=3, row=1, col=1)
    fig.add_annotation(
        x=pd.Timestamp("1990-06-01"), y=np.log10(2.2e3), xanchor="left", yanchor="bottom",
        text="Alt panel <b>NOMİNAL</b> TL hacmidir; 1990'lardaki yükselişin büyük kısmı "
             "fiyat düzeyi artışıdır, reel işlem hacmi değil.",
        showarrow=False, align="left", font=dict(size=9.5, color=GRI),
        bgcolor="rgba(255,255,255,0.86)", bordercolor=rgba(GRI, 0.35),
        borderwidth=0.8, borderpad=3, row=3, col=1)

    fig.update_yaxes(type="log", title_text="% (log)", row=1)
    fig.update_yaxes(type="log", title_text="kat (log)", row=2)
    fig.update_yaxes(type="log", title_text="bin TL (log)", row=3)
    # Pencere PİNLİ: otomatik menzil, sağdaki metin kutusu yüzünden 2040'a
    # kadar açılıyordu.
    for r in (1, 2, 3):
        fig.update_xaxes(range=[pd.Timestamp(bas), pd.Timestamp(bit)], row=r)
    fig.update_xaxes(title_text="tarih", row=3)
    duzen(fig, "Gecelik faizin otuz altı yılı: %6.200'den negatif reel plato'ya",
          "02.01.1990 – 21.08.2026", 1150,
          alt="EVDS TP.PY.P06.ON (ağırlıklı ortalama) · TP.PY.P05.ON (en yüksek) · "
              "TP.PY.P04.ON (en düşük) · TP.PY.P03.ON (hacim) — hepsi iş günü, "
              "02.01.1990'dan itibaren · ağırlıklı ortalama GÜNLÜK; zarf ve hacim "
              "HAFTALIK özetlendi (hafta maks./min./ort.) — uç değerler korunur")
    kaydet(fig, "D06_gecelik_faiz_uzun_ufuk",
           "Gecelik faiz, gün içi menzil ve hacim, 1990–2026", "1990-01 → 2026-08")


# ======================================================================
#  D07 — Osmanlı istikrazları: nominal, ele geçen, ihraç fiyatı
# ======================================================================
def d07():
    t = T_ISTIKRAZ
    # KATEGORİ EKSENİ KULLANILMIYOR: etiketlerin çoğu ("1854", "1874") sayıya
    # benziyor ve plotly bunları koordinata çevirip bütün çubukları tek noktaya
    # yığıyor (autotypenumbers="strict" annotation koordinatlarını kurtarmıyor).
    # Çözüm: x = 0…13 tamsayı konumları, etiketler tickvals/ticktext ile basılır.
    x = list(range(len(t)))
    etiket = t["etiket"].tolist()

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.11,
        subplot_titles=(
            "İstikrazların nominal tutarı ve FİİLEN ELE GEÇEN tutar (milyon Fransız frangı)",
            "İhraç (emisyon) fiyatı, nominalin yüzdesi — piyasanın kredi riskini "
            "fiyatladığı yer burasıdır"))

    fig.add_trace(go.Bar(x=x, y=t["nominal"], name="nominal anapara",
                         marker=dict(color=rgba(GRI, 0.50), line=dict(width=0)),
                         width=0.72, customdata=etiket,
                         hovertemplate="%{y:.1f} mn frank<extra>%{customdata} · nominal</extra>"),
                  row=1, col=1)
    fig.add_trace(go.Bar(x=x, y=t["gelen"], name="fiilen ele geçen",
                         marker=dict(color=BORDO, line=dict(width=0)),
                         width=0.42, customdata=etiket,
                         hovertemplate="%{y:.1f} mn frank<extra>%{customdata} · ele geçen</extra>"),
                  row=1, col=1)
    fig.update_layout(barmode="overlay")

    fig.add_trace(go.Scatter(x=x, y=t["fiyat"], name="ihraç fiyatı (%)",
                             mode="lines+markers+text",
                             line=dict(color=TEAL, width=2.2),
                             marker=dict(size=8, color=TEAL),
                             text=[tr(v, 1) for v in t["fiyat"]],
                             textposition="top center", textfont=dict(size=9.5),
                             customdata=etiket,
                             hovertemplate="%{y:.1f}%<extra>%{customdata}</extra>"),
                  row=2, col=1)
    for e, dash, ad in [(100, "dash", "başabaş (100)"),
                        (56.8, "dot", "20 yılın ortalaması: %56,8")]:
        fig.add_hline(y=e, line=dict(color=rgba(MUREKKEP, 0.5), width=1.2, dash=dash),
                      row=2, col=1,
                      annotation_text=ad, annotation_position="top left",
                      annotation=dict(font=dict(size=9, color=GRI)))

    i70 = etiket.index("1870–72")
    i74 = etiket.index("1874")
    fig.add_annotation(x=i70, y=32.125, text="%32,1 — nominalin üçte biri kadar nakit",
                       showarrow=True, arrowhead=2, ax=-58, ay=-34,
                       font=dict(size=9.5, color=BORDO), row=2, col=1)
    fig.add_annotation(x=i74, y=43.5, text="1874: %43,5 — moratoryumdan bir yıl önce",
                       showarrow=True, arrowhead=2, ax=-46, ay=-40,
                       font=dict(size=9.5, color=BORDO), row=2, col=1)
    fig.add_annotation(
        x=0, y=980, xanchor="left", yanchor="top", showarrow=False, align="left",
        text=("20 yılın toplamı: nominal <b>5.298,7</b> mn frank → ele geçen "
              "<b>3.012,9</b> mn frank (%56,8)<br>"
              "Osmanlı lirası karşılığı: 238,77 mn OL nominal → 127,12 mn OL "
              "ele geçen (%53,2)<br>"
              "1863 için kaynak iki emisyon kuru verir (%68 ve %72); grafikte "
              "ele geçen/nominal = %71,0 kullanıldı"),
        font=dict(size=9.5, color=MUREKKEP), bgcolor="rgba(255,255,255,0.88)",
        bordercolor=rgba(GRI, 0.4), borderwidth=0.8, borderpad=4, row=1, col=1)

    fig.update_yaxes(title_text="milyon frank", row=1, range=[0, 1080])
    fig.update_yaxes(title_text="%", row=2, range=[20, 118])
    for r in (1, 2):
        fig.update_xaxes(tickmode="array", tickvals=x, ticktext=etiket,
                         range=[-0.7, len(x) - 0.3], tickangle=-40,
                         zeroline=False, tickfont=dict(size=10), row=r)
    fig.update_xaxes(title_text="istikraz yılı", row=2)
    duzen(fig, "Kupon pazarlığa açıktır, iskonto değildir: Osmanlı istikrazları 1854–1874",
          "1854 – 1874 (15 ya da 16 istikraz — kaynaklar ayrışıyor)", 880,
          alt="KAYNAK: Eldem, V. (1970), s.160–161 ve s.260–262; Dikmen (2005) Tablo 1–2 "
              "(Yeniay'dan); Arslan, İ. (2015), Journal of History Studies 7/4 · "
              "EVDS'te bu dönem için seri YOKTUR — tablo elle kodlanmıştır")
    kaydet(fig, "D07_osmanli_istikrazlari",
           "Osmanlı istikrazları: nominal, ele geçen, ihraç fiyatı", "1854 → 1874")


# ======================================================================
#  D08 — Borç stokunun yüz yılı ve iki kesinti
# ======================================================================
def d08():
    t = T_STOK
    x = list(range(len(t)))
    etiket = t["etiket"].tolist()
    renkler = []
    for e in etiket:
        if "Muharrem" in e or "1933" in e or "1954" in e:
            renkler.append(YESIL)                        # kesinti / kapanış
        elif "1875" in e or "1918\nsavaş sonu" in e:
            renkler.append(BORDO)                        # temerrüt / zirve
        else:
            renkler.append(TEAL)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=False, vertical_spacing=0.13,
        row_heights=[0.42, 0.30, 0.28],
        subplot_titles=(
            "Dış borç stokunun kilometre taşları (milyon altın Osmanlı lirası) — "
            "yüz yıllık merdiven",
            "1881 Muharrem Kararnamesi borcu ne kadar indirdi? KAYNAKLAR AYRIŞIYOR",
            "Borç faizinin hükümet gelirine oranı (%) — SEYREK SERİ: yalnız kaynaklı "
            "yıllar noktalanmıştır, ara yıllar uydurulmamıştır"))

    fig.add_trace(go.Bar(x=x, y=t["deger"], name="dış borç stoku (mn OL)",
                         marker=dict(color=renkler, line=dict(width=0)), width=0.62,
                         text=[tr(v, 2) if v else "0" for v in t["deger"]],
                         textposition="outside", textfont=dict(size=9.5),
                         customdata=etiket,
                         hovertemplate="%{y:.2f} mn OL<extra>%{customdata}</extra>"),
                  row=1, col=1)

    m = T_MUHARREM
    xm = list(range(len(m)))
    fig.add_trace(go.Bar(x=[v - 0.19 for v in xm], y=m["oncesi"], name="Kararname ÖNCESİ",
                         marker=dict(color=rgba(GRI, 0.6), line=dict(width=0)), width=0.34,
                         text=[tr(v, 2) for v in m["oncesi"]],
                         textposition="outside", textfont=dict(size=9.5),
                         customdata=m["kaynak"],
                         hovertemplate="%{y:.2f} mn OL<extra>%{customdata} · öncesi</extra>"),
                  row=2, col=1)
    fig.add_trace(go.Bar(x=[v + 0.19 for v in xm], y=m["sonrasi"].fillna(0),
                         name="Kararname SONRASI",
                         marker=dict(color=YESIL, line=dict(width=0)), width=0.34,
                         text=[("kaynakta yok" if pd.isna(v) else tr(v, 2))
                               for v in m["sonrasi"]],
                         textposition="outside", textfont=dict(size=9.5),
                         customdata=m["kaynak"],
                         hovertemplate="%{y:.2f} mn OL<extra>%{customdata} · sonrası</extra>"),
                  row=2, col=1)

    sv = T_SERVIS
    fig.add_trace(go.Scatter(x=sv["yil"], y=sv["oran"],
                             name="borç faizi / hükümet geliri (%)",
                             mode="lines+markers+text",
                             line=dict(color=BORDO, width=1.6, dash="dash"),
                             marker=dict(size=11, color=BORDO),
                             text=[f"%{v:.0f}" for v in sv["oran"]],
                             textposition="top center", textfont=dict(size=10),
                             customdata=sv["not_"],
                             hovertemplate="%{y:.0f}%<extra>%{customdata}</extra>"),
                  row=3, col=1)
    fig.add_hline(y=25, line=dict(color=rgba(GRI, 0.6), width=1.1, dash="dot"),
                  row=3, col=1, annotation_text="1865'ten itibaren alarm eşiği (%25)",
                  annotation_position="bottom right",
                  annotation=dict(font=dict(size=9, color=GRI)))

    i33 = etiket.index([e for e in etiket if "1933" in e][0])
    i18 = etiket.index([e for e in etiket if "1918\nsavaş sonu" in e][0])
    fig.add_annotation(x=i33, y=8.58, text="107,53 → 8,58 mn OL · <b>%92,0 kesinti</b>",
                       showarrow=True, arrowhead=2, ax=-6, ay=-96, xanchor="right",
                       font=dict(size=10, color=YESIL), row=1, col=1)
    fig.add_annotation(x=i18, y=303.7,
                       text="savaşta 153,7 → 303,7; İtilaf düzenlemesiyle 161,85",
                       showarrow=True, arrowhead=2, ax=-20, ay=-34,
                       font=dict(size=9.5, color=BORDO), row=1, col=1)
    fig.add_annotation(
        x=1864.7, y=76, showarrow=False, xanchor="left", yanchor="top", align="left",
        font=dict(size=9.5, color=GRI),
        text="1874 kesiti (Kıray 1993, s.145): ihracat 19 mn £ · kısa vadeli borç "
             "16 mn £ · hükümet geliri 22,5 mn £<br>faiz/ihracat %66 · faiz/hükümet "
             "geliri %57 — 1875'te yıllık anapara+faiz 11 mn £'ye karşı gelir 18 mn £ "
             "(Pamuk aktarımı)",
        row=3, col=1)

    fig.update_layout(barmode="overlay")
    fig.update_yaxes(title_text="milyon OL", row=1, range=[0, 375])
    fig.update_yaxes(title_text="milyon OL", row=2, range=[0, 310])
    fig.update_yaxes(title_text="%", row=3, range=[0, 88])
    fig.update_xaxes(tickmode="array", tickvals=x, ticktext=etiket, zeroline=False,
                     range=[-0.7, len(x) - 0.3], tickangle=-32,
                     tickfont=dict(size=8.8), row=1)
    fig.update_xaxes(tickmode="array", tickvals=xm, ticktext=m["kaynak"].tolist(),
                     range=[-0.6, len(xm) - 0.4], zeroline=False,
                     tickfont=dict(size=10), row=2)
    fig.update_xaxes(title_text="yıl", row=3, dtick=2, range=[1863.5, 1876.5])
    duzen(fig, "Bir borcun yüz yılı: 1854'te 3,3 milyon, 1954'te sıfır",
          "1854 – 1954", 1220,
          alt="KAYNAK: Arslan, İ. (2015), Journal of History Studies 7/4 (Yeniay ve "
              "Eldem'den); Dikmen (2005) s.143–150; TDV İslâm Ansiklopedisi "
              "'Düyûn-ı Umûmiyye'; Kıray (1993) s.145 · 1881 için üç kaynak üç ayrı "
              "büyüklük verir (kapsam farkı: gecikmiş faizler, iç borcun sayılıp "
              "sayılmaması, parite kabulü) — tek bir rakam 'doğru' diye seçilmemiştir")
    kaydet(fig, "D08_borc_stoku_yuz_yil",
           "Osmanlı/TC dış borç stoku 1854–1954 ve iki kesinti", "1854 → 1954")


# ======================================================================
#  D09 — Gümrük tarifesi ve Düyun-u Umumiye'nin gelir payı
# ======================================================================
def d09():
    t = T_TARIFE
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.13,
        subplot_titles=(
            "Gümrük tarifesi (%) — 1838 Balta Limanı ve sonrası. BASAMAK çizgi: "
            "değerler bir sonraki değişikliğe kadar geçerlidir",
            "Düyun-u Umumiye İdaresi'nin devlet gelirleri içindeki payı, 1911/12 mali yılı "
            "(bin altın OL)"))

    for kol, ad, renk in [("ihracat", "ihracat gümrük oranı (%)", BORDO),
                          ("ithalat", "ithalat gümrük oranı (%)", TEAL)]:
        fig.add_trace(go.Scatter(x=t["yil"], y=t[kol], name=ad, mode="lines+markers",
                                 line=dict(color=renk, width=2.2, shape="hv"),
                                 marker=dict(size=7, color=renk),
                                 hovertemplate="%{y}%<extra>" + ad + "</extra>"),
                      row=1, col=1)
    for yil, etiket in [(1838, "16.08.1838 — Balta Limanı"),
                        (1854, "1854 — ilk dış borç"),
                        (1861, "1860–61 — tarife revizyonu"),
                        (1875, "1875 — moratoryum"),
                        (1908, "1908 — ithalat %15"),
                        (1914, "1914 — antlaşma fiilen bir kenara")]:
        fig.add_shape(type="line", x0=yil, x1=yil, y0=0, y1=1, yref="y domain",
                      line=dict(color=rgba(MUREKKEP, 0.45), width=1.1, dash="dot"),
                      row=1, col=1)
        fig.add_annotation(x=yil, y=1.0, yref="y domain", yanchor="top", xanchor="left",
                           text=" " + etiket, showarrow=False, textangle=-90,
                           font=dict(size=8.5, color=GRI), row=1, col=1)

    # TOPLAM satırı çubuklardan ÇIKARILDI: bileşenlerin on katı olduğu için ekseni
    # eziyor ve kalemler okunmaz hâle geliyordu; toplam metin kutusunda verilir.
    d = T_DUYUN[T_DUYUN["kalem"] != "TOPLAM"].reset_index(drop=True)
    top = T_DUYUN[T_DUYUN["kalem"] == "TOPLAM"].iloc[0]
    fig.add_trace(go.Bar(y=d["kalem"], x=d["du"], name="Düyun-u Umumiye'ye ayrılan",
                         orientation="h", marker=dict(color=BORDO, line=dict(width=0)),
                         text=[f"%{tr(p, 1)}" for p in d["pay"]], textposition="inside",
                         textfont=dict(size=10, color="#ffffff"),
                         hovertemplate="%{x:,.0f} bin OL<extra>D.U.</extra>"),
                  row=2, col=1)
    fig.add_trace(go.Bar(y=d["kalem"], x=d["toplam"] - d["du"], name="devlete kalan",
                         orientation="h", marker=dict(color=rgba(GRI, 0.45),
                                                      line=dict(width=0)),
                         hovertemplate="%{x:,.0f} bin OL<extra>devlete kalan</extra>"),
                  row=2, col=1)
    fig.update_layout(barmode="stack")
    fig.add_annotation(x=float(d.loc[d["kalem"] == "İnhisarlar (tekeller)", "du"].iloc[0]),
                       y="İnhisarlar (tekeller)",
                       text="tekel gelirlerinin <b>%79,5</b>'i İdare'ye",
                       showarrow=True, arrowhead=2, ax=118, ay=0,
                       font=dict(size=9.5, color=BORDO), row=2, col=1)
    fig.add_annotation(x=float(T_DUYUN["toplam"].max()) * 0.99, y=-0.42,
                       xanchor="right", yanchor="bottom", showarrow=False, align="right",
                       text=(f"<b>TOPLAM 1911/12:</b> {tr(top['toplam'], 0)} bin OL "
                             f"gelirin {tr(top['du'], 0)}'i İdare'ye → "
                             f"<b>%{tr(top['pay'], 1)}</b>"),
                       font=dict(size=10, color=MUREKKEP),
                       bgcolor="rgba(255,255,255,0.88)", bordercolor=rgba(GRI, 0.4),
                       borderwidth=0.8, borderpad=4, row=2, col=1)

    fig.update_yaxes(title_text="%", row=1, range=[0, 17])
    fig.update_xaxes(title_text="yıl", row=1, range=[1828, 1918], dtick=10)
    fig.update_xaxes(title_text="bin altın Osmanlı lirası", row=2)
    fig.update_yaxes(autorange="reversed", row=2)
    duzen(fig, "Araç setinin daralması: tarife egemenliği ve gelirin temliki",
          "1830 – 1914", 900,
          alt="KAYNAK (üst): Pamuk, Ş., '150. Yılında Baltalimanı Ticaret Antlaşması', "
              "s.30–31 — kaynak metninde 1860–61 indiriminin hangi vergide olduğu "
              "konusunda içsel tutarsızlık vardır; grafik, %12 → %1 indiriminin "
              "İHRACAT vergisinde olduğu okumasını izler · KAYNAK (alt): İnce, "
              "'Devlet Borçlanması' s.65 → Dikmen (2005) Tablo 5")
    kaydet(fig, "D09_tarife_ve_duyun",
           "Gümrük tarifesi 1830–1914 ve Düyun-u Umumiye'nin gelir payı", "1830 → 1914")


# ======================================================================
#  D10 — Rejim zaman çizelgesi 1854–2026
# ======================================================================
# Kaynaklar: TCMB 'Kâğıt Paranın Tarihçesi' ve 'Dünden Bugüne TCMB'; 1567 sayılı
# TPKK Kanunu (20.02.1930); 1715 s.K. (11.06.1930, RG 30.06.1930); 1211 s.K. (1970);
# 32 sayılı Karar (11.08.1989); 4651 s.K. (25.04.2001); Arslan (2015); Dikmen (2005);
# TDV 'Düyûn-ı Umûmiyye'; FRUS 1958–60 X/2 blg.322; Tuna (2007).
ZAMAN_CIZELGESI = [
    # (satır, başlangıç yılı, bitiş yılı, etiket, renk)
    ("Kur rejimi", 1854, 1915, "madenî para + Osmanlı Bankası banknotu (altına çevrilebilir)", TEAL),
    ("Kur rejimi", 1915, 1946, "evrak-ı nakdiye → TC banknotu; kontrol + kliring", MOR),
    ("Kur rejimi", 1946, 1958, "sabit parite 2,80 (Bretton Woods)", TEAL),
    ("Kur rejimi", 1958, 1960, "çoklu kur (fiilî devalüasyon)", ALTIN),
    ("Kur rejimi", 1960, 1980, "ayarlanabilir sabit kur (9,00 → 14,85 → 14,00)", MAVI),
    ("Kur rejimi", 1980, 1981, "24 Ocak: büyük adımlar", TURUNCU),
    ("Kur rejimi", 1981, 1989, "sürünen kur — günlük kur ilanı", MOR),
    ("Kur rejimi", 1989, 1999, "yönetimli kur, sermaye hesabı açık", YESIL),
    ("Kur rejimi", 1999, 2001, "kur çıpası + genişleyen bant", ALTIN),
    ("Kur rejimi", 2001, 2026, "dalgalı kur", TEAL),

    ("Para otoritesi", 1840, 1863, "kaime — hükümetin faizli kâğıdı", BORDO),
    ("Para otoritesi", 1863, 1931, "Osmanlı Bankası: 30 yıllık banknot imtiyazı", MOR),
    ("Para otoritesi", 1876, 1878, "taahhüt delindi: 93 Harbi kaimesi", BORDO),
    ("Para otoritesi", 1931, 1970, "TCMB (1715 s.K., A/B/C/D hisseli AŞ)", TEAL),
    ("Para otoritesi", 1970, 2001, "1211 s.K. — Hazine'ye kısa vadeli avans", ALTIN),
    ("Para otoritesi", 2001, 2026, "fiyat istikrarı temel amaç · avans YASAK", YESIL),

    ("Para politikası çerçevesi", 1990, 1999, "parasal büyüklük hedefleri (para programı)", MAVI),
    ("Para politikası çerçevesi", 1999, 2001, "yarı para kurulu: Net İç Varlıklar tavanı", ALTIN),
    ("Para politikası çerçevesi", 2002, 2005, "örtük enflasyon hedeflemesi", TEAL),
    ("Para politikası çerçevesi", 2006, 2010, "açık enflasyon hedeflemesi", YESIL),
    ("Para politikası çerçevesi", 2010, 2018, "faiz koridoru + ROM", MOR),
    ("Para politikası çerçevesi", 2018, 2021, "tek fiyatlı politika faizi (aralıklı)", TURUNCU),
    ("Para politikası çerçevesi", 2021, 2023, "faiz indirimi + geniş makroihtiyati set", BORDO),
    ("Para politikası çerçevesi", 2023, 2026, "sadeleşme, sıkılaşma, dezenflasyon programı", YESIL),

    ("Dış ticaret / sermaye", 1838, 1914, "Balta Limanı: tarife egemenliği ortak", BORDO),
    ("Dış ticaret / sermaye", 1881, 1923, "Düyun-u Umumiye: gelirin temliki", BORDO),
    ("Dış ticaret / sermaye", 1930, 1980, "1567 s. TPKK: kambiyo kontrolü + kliring", MOR),
    ("Dış ticaret / sermaye", 1980, 1989, "24 Ocak → dışa açılma, ihracata teşvik", TURUNCU),
    ("Dış ticaret / sermaye", 1989, 2026, "32 sayılı Karar: sermaye hesabı açık (hâlâ)", YESIL),
]

# Kriz / temerrüt / rejim kırılması işaretleri (yıl, etiket)
KRIZ_ISARET = [
    (1875, "Ramazan Kararnamesi — moratoryum"),
    (1881, "Muharrem Kararnamesi — kesinti"),
    (1903, "Tevhid-i Düyun — takas (B %70, C %42, D %37)"),
    (1929, "Buhran — taksit ödenmedi"),
    (1933, "Paris: %92 kesinti"),
    (1946, "ilk devalüasyon (1,30 → 2,80)"),
    (1958, "IMF programı, çoklu kur"),
    (1970, "devalüasyon (9,00 → 14,85)"),
    (1978, "ödemeler dengesi krizi, DÇM"),
    (1980, "24 Ocak Kararları"),
    (1982, "Bankerler krizi"),
    (1994, "5 Nisan Kararları"),
    (2000, "Kasım 2000 likidite krizi"),
    (2001, "Şubat 2001 — dalgalı kura geçiş"),
    (2008, "küresel kriz"),
    (2018, "Ağustos 2018"),
    (2021, "Aralık 2021"),
]


def d10():
    satirlar = []
    for s, *_ in ZAMAN_CIZELGESI:
        if s not in satirlar:
            satirlar.append(s)
    satirlar = satirlar[::-1]                            # en üstte "Kur rejimi"
    X0, X1 = 1834, 2036
    DAR = 15                                             # yıl — bu genişliğin altı "dar dilim"

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.075,
        row_heights=[0.63, 0.37],
        subplot_titles=(
            "Rejim şeridi — her kutu bir dönemdir, genişliği o rejimin ömrüdür. "
            "Kutuya sığmayan dar dilimler NUMARALIDIR; anahtar aşağıdaki kutuda",
            "Kırılma işaretleri — her olay kendi satırında; elmasın yatay konumu "
            "olayın YILIDIR (aşağı indikçe sağa kayar)"))

    # Şerit go.Bar ile DEĞİL, add_shape ile çizilir: tek noktalı yatay çubuklar
    # plotly'nin grup ofsetine takılıp şeritleri birbirinin üstüne bindiriyordu.
    # DAR dilimlerin adı kutuya sığmaz; kutunun üstüne/altına yazma denendi, yoğun
    # 1999–2026 bölgesinde etiketler çakıştı. Çözüm: dar dilime NUMARA rozeti,
    # numaraların açılımı şeridin boş sol üst bölgesindeki ANAHTAR kutusunda.
    anahtar: list[str] = []
    for satir, b, e, etiket, renk in ZAMAN_CIZELGESI:
        y = satirlar.index(satir)
        fig.add_shape(type="rect", x0=b, x1=e, y0=y - 0.28, y1=y + 0.28,
                      fillcolor=rgba(renk, 0.42), line=dict(color=renk, width=1.1),
                      layer="below", row=1, col=1)
        fig.add_trace(go.Scatter(x=[(b + e) / 2], y=[y], mode="markers",
                                 marker=dict(size=1, color="rgba(0,0,0,0)"),
                                 showlegend=False,
                                 hovertemplate=f"{b}–{e}<br>{etiket}<extra>{satir}</extra>"),
                      row=1, col=1)
        if e - b >= DAR:
            fig.add_annotation(x=(b + e) / 2, y=y, text=etiket, showarrow=False,
                               font=dict(size=8.4, color=MUREKKEP), row=1, col=1)
        else:
            no = len(anahtar) + 1
            anahtar.append(f"<b>{no}</b> · {b}–{e} {etiket}")
            fig.add_annotation(x=(b + e) / 2, y=y, text=f"<b>{no}</b>", showarrow=False,
                               font=dict(size=8.6, color=MUREKKEP), row=1, col=1)

    # Anahtar kutusu: "Para politikası çerçevesi" satırının 1838–1990 aralığı boştur.
    yk = satirlar.index("Para politikası çerçevesi")
    yarim = (len(anahtar) + 1) // 2
    sol_sutun = "<br>".join(anahtar[:yarim])
    sag_sutun = "<br>".join(anahtar[yarim:])
    for x_konum, govde in ((1841, sol_sutun), (1913, sag_sutun)):
        if not govde:
            continue
        fig.add_annotation(x=x_konum, y=yk + 0.42, text=govde, showarrow=False,
                           xanchor="left", yanchor="top", align="left",
                           font=dict(size=8.0, color=MUREKKEP), row=1, col=1)
    fig.add_annotation(x=1841, y=yk + 0.52, text="dar dilimlerin anahtarı:",
                       showarrow=False, xanchor="left", yanchor="bottom",
                       font=dict(size=8.4, color=GRI), row=1, col=1)

    # Kırılma işaretleri — MERDİVEN düzeni: her olay kendi satırında. Kademeli
    # serpiştirme 1994–2021 yığılmasında çakışmayı çözemiyordu; merdivende
    # her etiketin kendi satırı olduğu için çakışma yapısal olarak imkânsızdır.
    olaylar = sorted(KRIZ_ISARET)
    n = len(olaylar)
    for i, (yil, etiket) in enumerate(olaylar):
        y = n - 1 - i                                    # en eski en üstte
        saga = yil < 1975
        fig.add_shape(type="line", x0=yil, x1=yil, y0=0, y1=1, yref="y domain",
                      line=dict(color=rgba(BORDO, 0.20), width=1), layer="below",
                      row=1, col=1)
        fig.add_shape(type="line", x0=X0, x1=yil, y0=y, y1=y,
                      line=dict(color=rgba(BORDO, 0.18), width=0.8), layer="below",
                      row=2, col=1)
        fig.add_trace(go.Scatter(x=[yil], y=[y], mode="markers", showlegend=False,
                                 marker=dict(symbol="diamond", size=7, color=BORDO),
                                 hovertemplate=f"{yil} — {etiket}<extra></extra>"),
                      row=2, col=1)
        fig.add_annotation(x=yil, y=y, text=f"<b>{yil}</b> · {etiket}", showarrow=False,
                           xanchor="left" if saga else "right", yanchor="middle",
                           xshift=7 if saga else -7,
                           font=dict(size=8.6, color=BORDO), row=2, col=1)

    fig.update_yaxes(tickmode="array", tickvals=list(range(len(satirlar))),
                     ticktext=satirlar, row=1, range=[-0.75, len(satirlar) - 0.28],
                     showgrid=False, zeroline=False, tickfont=dict(size=11))
    fig.update_yaxes(row=2, range=[-0.9, len(KRIZ_ISARET) - 0.1],
                     showticklabels=False, showgrid=False, zeroline=False)
    fig.update_xaxes(range=[X0, X1], dtick=10, zeroline=False, row=1)
    fig.update_xaxes(title_text="yıl", range=[X0, X1], dtick=10, zeroline=False, row=2)
    duzen(fig, "Yüz yetmiş yılın rejim şeridi: kur · para otoritesi · sermaye hesabı",
          "1838 – 2026", 1080,
          alt="KAYNAK: TCMB 'Kâğıt Paranın Tarihçesi' ve 'Dünden Bugüne TCMB'; 1567 s. "
              "TPKK Kanunu (20.02.1930); 1715 s.K. (11.06.1930, RG 30.06.1930); 1211 s.K. "
              "(1970); 32 sayılı Karar (11.08.1989); 4651 s.K. (25.04.2001); Arslan "
              "(2015); Dikmen (2005); TDV 'Düyûn-ı Umûmiyye'; FRUS 1958–60 X/2 blg.322; "
              "Tuna (2007) · dönem sınırları YUVARLANMIŞTIR: şerit kronoloji değil, "
              "REJİM haritasıdır")
    kaydet(fig, "D10_rejim_zaman_cizelgesi", "Rejim zaman çizelgesi 1838–2026",
           "1838 → 2026")


# ======================================================================
#  D11 — Korunma araçlarının uzun ufku (altın · döviz · fiyat düzeyi)
# ======================================================================
def d11():
    # TABAN 1963-12: altın serisi 1978 öncesinde YALNIZ ARALIK gözlemi taşır,
    # 1963-01 tabanı altın serisini tamamen NaN yapıyordu (endeksle() taban
    # tarihinden ÖNCEKİ son gözlemi arar, altında öyle bir gözlem yoktur).
    bas, bit = "1963-12-01", "2026-05-01"
    eski = _oku("altin_eski_ham.csv").set_index("dt")
    yeni = E("altin_yeni", ["TP.MK.KUL.YTL", "TP.MK.RES.YTL", "TP.MK.CUM.YTL"],
             "1990-01-01", "2026-08-21", 10)
    kul = pd.concat([eski["TP_MK_KUL_YTL"].dropna().loc[:"1989-12-31"],
                     yeni["MK.KUL.YTL"].dropna().loc["1990-01-01":]]).sort_index()
    cum = pd.concat([eski["TP_MK_CUM_YTL"].dropna().loc[:"1989-12-31"],
                     yeni["MK.CUM.YTL"].dropna().loc["1990-01-01":]]).sort_index()
    if not len(kul) or not len(cum):
        ATLANAN.append("D11 — altın serisi boş, grafik üretilmedi")
        return

    k = kur_uzun().resample("MS").last()
    p = fiyat_endeksi()
    taban = "1963-12-01"

    e_altin = endeksle(kes(kul, bas, bit), taban)
    e_cum = endeksle(kes(cum, bas, bit), taban)
    e_kur = endeksle(kes(k, bas, bit), taban)
    e_fiyat = endeksle(kes(p, bas, bit), taban)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.095,
        subplot_titles=(
            "Nominal, 1963-12 = 100, LOGARİTMİK — külçe altın (TL/gram) · Cumhuriyet "
            "altını (TL/adet) · USD/TRY · fiyat düzeyi",
            "REEL: aynı serilerin Türkiye fiyat düzeyine bölünmüş hâli (1963-12 = 100). "
            "100 çizgisinin altı, o aracın FAİZSİZ tutulduğunda enflasyonu "
            "KORUYAMADIĞI dönemdir"))

    for s, ad, renk, w in [(e_altin, "külçe altın (TL/gram)", ALTIN, 1.9),
                           (e_cum, "Cumhuriyet altını (TL/adet)", TURUNCU, 1.4),
                           (e_kur, "USD/TRY", TEAL, 1.7),
                           (e_fiyat, "fiyat düzeyi (eklemlenmiş endeks)", BORDO, 1.7)]:
        cizgi(fig, s.dropna(), ad, renk, row=1, w=w)

    for s, ad, renk, w in [((e_altin / e_fiyat * 100).dropna(), "külçe altın, reel", ALTIN, 1.9),
                           ((e_cum / e_fiyat * 100).dropna(), "Cumhuriyet altını, reel", TURUNCU, 1.4),
                           ((e_kur / e_fiyat * 100).dropna(),
                            "yastık altı USD nakit, reel (TL malları cinsinden)", TEAL, 1.7)]:
        cizgi(fig, s, ad, renk, row=2, w=w)
    fig.add_hline(y=100, line=dict(color=rgba(MUREKKEP, 0.55), width=1.4), row=2, col=1)

    rejim_bantlari(fig, bas, bit, satir_sayisi=2, etiket_satiri=1)

    reel_altin = (e_altin / e_fiyat * 100).dropna()
    if len(reel_altin):
        # DİKKAT: 2. panelin y ekseni LOGARİTMİK — anotasyon y'si log10 verilmeli.
        # Ham değer verildiğinde plotly y=1650'yi 10^1650 sayıyor ve ekseni 10^30'a
        # kadar açıyordu (grafiğin bütün çizgileri tabana yapışıyordu).
        dip = kes(reel_altin, "1970-01-01", "1990-12-31")
        if len(dip):
            td = dip.idxmin()
            not_(fig, td, np.log10(dip.min()),
                 f"{td.strftime('%m.%Y')} — reel dip: {tr(dip.min(), 0)}",
                 row=2, ay=42, boyut=9.5, renk=ALTIN)
        son = reel_altin.index[-1]
        not_(fig, son, np.log10(reel_altin.loc[son]),
             f"{son.strftime('%m.%Y')} — reel {tr(reel_altin.loc[son], 0)}",
             row=2, ay=-30, boyut=10, xanchor="right", renk=ALTIN)
        reel_kur = (e_kur / e_fiyat * 100).dropna()
        sk = reel_kur.index[-1]
        not_(fig, sk, np.log10(reel_kur.loc[sk]),
             f"{sk.strftime('%m.%Y')} — faizsiz USD nakit reel {tr(reel_kur.loc[sk], 0)}",
             row=2, ay=36, boyut=10, xanchor="right", renk=TEAL)

    fig.update_yaxes(type="log", title_text="endeks (log, 1963-12 = 100)", row=1)
    fig.update_yaxes(type="log", title_text="reel endeks (log, 1963-12 = 100)", row=2)
    fig.update_xaxes(title_text="tarih", row=2)
    duzen(fig, "Altmış üç yıl boyunca ne korudu? Altın, dolar ve fiyat düzeyi",
          "12.1963 – 05.2026", 940,
          alt="EVDS TP.MK.KUL.YTL / TP.MK.CUM.YTL (Ankara Kuyumcular Odası; 1978 "
              "öncesi yalnız ARALIK gözlemi vardır — o dönemde çizgi yıllık noktaları "
              "birleştirir) · TP.DK.USD.A.YTL · fiyat düzeyi: D02 eklemlenmiş endeksi · "
              "1963–86 toptan eşya endeksi kullanıldığı için o dönemin REEL "
              "hesapları tüketici sepetiyle birebir karşılaştırılamaz · UYARI: alt "
              "paneldeki USD çizgisi REEL KUR DEĞİLDİR — reel kur yabancı fiyat "
              "endeksini de ister; buradaki ölçü, faizsiz tutulan bir dolar nakit "
              "pozisyonunun Türkiye malları cinsinden satın alma gücüdür")
    kaydet(fig, "D11_korunma_araclari_uzun_ufuk",
           "Altın, dolar ve fiyat düzeyi — nominal ve reel, 1963–2026",
           "1963-01 → 2026-05")


# ======================================================================
FIGURLER = [d01, d02, d03, d04, d05, d06, d07, d08, d09, d10, d11]


def main():
    print(f"Çıktı: {CIKTI}")
    for f in FIGURLER:
        try:
            f()
        except Exception as e:
            import traceback
            ATLANAN.append(f"{f.__name__} — HATA: {e}")
            traceback.print_exc()
    print(f"\n{len(URETILEN)} grafik üretildi.")
    for ad, baslik, pencere in URETILEN:
        print(f"  {ad:38s} {baslik}  [{pencere}]")
    if ATLANAN:
        print("\nAtlananlar / uyarılar:")
        for s in ATLANAN:
            print("  ·", s)


if __name__ == "__main__":
    main()
