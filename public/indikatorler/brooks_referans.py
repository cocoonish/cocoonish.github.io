#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks · Fiyat Hareketi — Pine indikatörünün PYTHON REPLİKASYONU.

Bu dosya, TradingView'de koşan iki Pine betiğinin AYNI kurallarını Python'da
yazar. Amacı işlem yapmak değil; kuralları **okunur** ve **sınanabilir**
kılmak. Pine bilmeyen biri buradan ne olup bittiğini görür, Pine bilen biri
iki dosyayı yan yana koyup satır satır karşılaştırabilir.

Tek başına koşar, ağa çıkmaz, kütüphane istemez:

    python3 brooks_referans.py            # kendi kendini sınar ve örnek basar

──────────────────────────────────────────────────────────────────────────
NASIL OKUNUR — Pine'dan Python'a
──────────────────────────────────────────────────────────────────────────

Tek bir şeyi anlarsanız gerisi kendiliğinden gelir: **bir Pine betiği baştan
sona bir DÖNGÜNÜN GÖVDESİDİR.** Yazdığınız her satır, grafikteki her bar için
bir kez, soldan sağa koşar. Pine o döngüyü gizler; Python göstermek zorunda.
Aşağıdaki her satır bu tek farkın bir sonucudur.

    Pine                          Python (bu dosya)         Dikkat
    ─────────────────────────────────────────────────────────────────────
    close                         s.c[i]                    i = döngü barı
    close[1]                      s.c[i - 1]                [1] = bir bar önce
    high[2]                       s.h[i - 2]
    var int ai = 0                döngü DIŞINDA ai = 0      var yalnız ilk
                                                            barda atanır,
                                                            sonra taşınır
    ai := 1                       ai = 1                    := yeniden atama;
                                                            Pine'da = yeni
                                                            değişken demek
    ta.ema(close, 20)             ema(s.c, 20)              ilk 19 bar None;
                                                            20. bar SMA ile
                                                            tohumlanır
    ta.highest(close[1], 8)       max(s.c[i-8 : i])         pencere i-1'de
                                                            BİTER, i yok
    ta.lowest(low[1], 5)          min(s.l[i-5 : i])
    math.sum(x ? 1 : 0, 10)       sum(...  i-9 .. i)        pencere i'yi İÇERİR
    na(x)                         x is None
    barstate.islast               i == len(s) - 1
    label.new / plotshape         döndürülen sözlük         çizim yok, ölçüm var
    alertcondition               —                          ölçüm karşılığı yok

**İki pencere sınırı neden farklı.** `ta.highest(close[1], 8)` ifadesinde
argüman zaten `close[1]`, yani pencere bir bar geriden başlar ve şimdiki barı
İÇERMEZ — "kapanışım son sekiz barın kapanışını aştı mı" sorusu ancak böyle
sorulabilir, yoksa bar kendini aşmaya çalışır. `math.sum` ise şimdiki barı
sayar: "son on barın kaçı ortalamanın üstünde" sorusunda bugün de bir bardır.
Bu ikisini karıştırmak sessiz bir bir-bar kaymasıdır ve hiçbir yerde hata
vermez.

**`var` neden önemli.** Pine'da `var` ile açılan değişken tek kalıcı durumdur;
geri kalan her şey o barda baştan hesaplanır. Always-in yönü, gap bar sayacı
ve bar sayımı bu yüzden `var`dır. Python'da karşılığı döngüden önce tanımlanıp
döngü içinde güncellenen değişkendir. Bir kuralı Pine'dan taşırken sorulacak
ilk soru budur: bu değer her barda sıfırlanır mı, yoksa taşınır mı?

**Geleceğe bakmama.** Her iki dilde de kural aynıdır: bir hesap YALNIZ
kapanmış barlardan kurulur. Pine'da bunu betiğin yapısı büyük ölçüde dayatır;
Python'da `i`'den büyük hiçbir indeks kullanmayarak siz dayatırsınız. Bu
dosyanın kapısı bunu SÖZ olarak değil ÖLÇÜM olarak sınıyor
(`gelecege_bakma_sinamasi`): seri `i`'de kırpıldığında `i`'deki bütün çıktılar
birebir aynı kalmalı. Bir kural bir gün geleceğe bakarsa o sınama düşer.

──────────────────────────────────────────────────────────────────────────
EŞİKLER TEK KAYNAKTAN
──────────────────────────────────────────────────────────────────────────

Aşağıdaki sabitlerin hiçbiri burada SEÇİLMEDİ; hepsi dersin kendi sayısal
sabitler tablosundan gelir ve Pine dosyalarının `input` varsayılanlarıyla
birebir aynıdır. İki uygulama bir gün sessizce ayrışabilir — o yüzden depoda
koşarken `pine_ile_karsilastir()` ikisini karşılaştırır ve ayrışmayı ENGEL
sayar. Bu dosya tek başına indirildiğinde sabitler aşağıdaki değerlerdir.
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from pathlib import Path

# ── Eşikler: dersin sayısal sabitler tablosundan ────────────────────────────
SABIT_FH: dict[str, float | int] = {
    # Bölüm 1 · bar sınıfı
    "trendGovde": 0.50,     # trend barı: gövde ≥ menzilin %50'si
    "gucluGovde": 0.75,     # güçlü trend barı: gövde ≥ menzilin %75'i
    "dojiGovde": 0.10,      # doji: gövde ≤ menzilin %10'u
    # Bölüm 7 · hareketli ortalama
    "maUzunluk": 20,        # 20 barlık EMA
    "gapEsik": 20,          # ortalamaya dokunmayan ≥ 20 ardışık bar
    "yonPencere": 10,       # yön filtresi penceresi
    "yonEsik": 7,           # son 10 barın 7'si → karşı yön yasağı
    # Bölüm 2 · sinyal barı
    "kapanisPenc": 8,       # kapanış son ~8 barın kapanışını çeviriyor
    "ucPenc": 5,            # uç son ~5 barın ucunu çeviriyor
    "ortusmeEsik": 0.75,    # %75 üstü örtüşme → iki barlık dönüş oku
    # Bölüm 1.3 · trendleşme ve göreli gövde
    "trendlesmeEsik": 3,    # trendleşen kapanış/zirve/dip: ≥ 3 bar
    # Bölüm 1.10b · çevirme sayacı eşikleri
    "cevirmeSiradan": 3,    # < 3 → bar sıradan
    "cevirmeRejim": 5,      # > 5 → bar bir REJİM İDDİASI
    "cevirmeKirilim": 15,   # > 15 → dersin en üst kademesi (hükmü sınandı, bkz. cevirme_kademesi)
    # Bölüm 2.6 · tükeniş barı bağlamı
    "tukenisTrendBar": 10,  # "10 veya daha fazla bar süren bir trendin içinde"
    # Bölüm 2.9 · ikinci giriş ilkesinin momentum eşiği
    "momentumBar": 6,       # "altı bar boyunca boğa kapanışı yok"
    # Bölüm 8A.6 · beş bar iptal kuralı
    "iptalKapanis": 5,      # eski ucun ötesinde ≥ 5 KAPANIŞ → dönüş arayışı iptal
    # Bölüm 4 · bant kenarı paketi (Kurulumlar.bant_kenari) — rejim panosuyla aynı pencere
    "pencere": 70,
}

# ── Tanım seçimleri: ders bir SAYI VERMİYOR ───────────────────────────────
#
# Aşağıdakiler dersin eşikleri DEĞİL. Ders bu kuralları sözle kurar
# ("kabaca eşit", "belirgin altında", "neredeyse aynı") ve sayı vermez. Bir
# indikatör sayı olmadan karar veremez, o yüzden bir tanım seçmek zorunda —
# ama seçtiğini SAYMAZ: bu tablo ayrı durur ki okur hangi sayının dersten,
# hangisinin bizden geldiğini karıştırmasın. Hepsi girdi olarak açıktır.
TANIM: dict[str, float | int] = {
    "esitGovdeOran": 0.50,   # iki barlık dönüşte "kabaca eşit gövde"
    "kucukBarOran": 0.50,    # küçük bar: menzil < son N barın ortalamasının bu katı
    "tukenisOran": 2.00,     # tükeniş barı: menzil > son N barın ortalamasının bu katı
    "mikroTolerans": 0.05,   # mikro çift dip/tepe: "neredeyse aynı" — menzilin payı
    "cevirmeTavan": 100,     # çevirme sayacı tarama tavanı; ölçülen p99 tam burada — sayı SANSÜRLÜ
    "medyanPencere": 10,     # göreli gövde gücü penceresi (ders: "son 5–10 bar")
}

SABIT_RP: dict[str, float | int] = {
    # Bölüm 4.2 · yatay bant tanı listesi
    "pencere": 70,          # dersin Şekil 30'undaki bant tam 70 bar
    "maUzunluk": 20,
    "ortusmeEsik": 0.50,    # madde 10: bir öncekiyle %50+ örtüşen bar
    "ortusmePay": 0.50,     # bant işareti (Şekil 30'da ölçülen: 0,725)
    "dojiGovde": 0.10,
    "dojiPay": 0.25,        # bant işareti (Şekil 30'da ölçülen: 0,314)
    "kesismeEsik": 5,       # bant işareti (Şekil 30'da ölçülen: 17)
    "netEsik": 0.50,        # bant işareti (Şekil 30'da ölçülen: 0,037)
    "diziEsik": 3,          # madde 8: üç-dört ardışık trend barı ENDER
    # Bölüm 4.9 · barbwire
    "bwBar": 3,             # "üç veya daha fazla bar büyük ölçüde örtüşüyorsa"
    "bwOrtaPay": 0.50,      # "ortadaki barın menzilinin %50'sinden fazlası komşularında"
    "bwDoji": 1,            # "en az biri çok küçük gövdeli (doji)"
    # GÖRELİ EŞİK — dersin değil, ÖLÇÜMÜN getirdiği sabitler (bkz. olcu_goreli)
    "tarihce": 280,         # her ölçü kendi son 280 barlık değerine göre sıralanır (5 dk'da ~1 gün)
    "goreliPay": 0.60,      # ölçü tarihçesinin %60'ından "daha bantlı" ise işaret
}


# ── Ölçü sözleşmesi: her Python ölçüsünün Pine karşılığı ────────────────────
#
# Eşik kapısı (pine_ile_karsilastir) İKİ UYGULAMANIN EŞİKLERİNİ karşılaştırır —
# ama bir ölçü YENİ BİR EŞİK GETİRMİYORSA o kapı onu hiç göremez. "Yalnızca
# gövdeler ii" tam böyleydi: mevcut girdilerle çalışıyor, kendi eşiği yok.
# Pine'a taşınmasaydı hiçbir kapı ötmezdi ve sayfadaki kod, sayfadaki
# açıklamayı karşılamazdı.
#
# Bu yüzden sözleşme ADIYLA yazılır: her ölçünün Pine'daki karşılık değişkeni
# burada ilan edilir ve kapı İKİ YÖNLÜ sorar —
#   (a) Python'da ilan edilmemiş bir ölçü var mı,
#   (b) ilan edilen her ad .pine dosyasında gerçekten ATANIYOR mu.
# Liste elle tutulan bir kapsam listesi DEĞİL: kapı, sınıfın bütün genel
# metotlarını dolaşıp burada karşılığı olmayanı ENGEL sayar.
PINE_KARSILIGI: dict[str, str] = {
    # Bölüm 1 · bar anatomisi
    "menzil": "menzil",
    "govde": "govde",
    "govde_orani": "govdeOran",
    "orta_nokta": "ortaNokta",
    "alt_kuyruk": "altKuyruk",
    "ust_kuyruk": "ustKuyruk",
    "sinif": "trendBari",
    "guclu_boga": "gucluBoga",
    "guclu_ayi": "gucluAyi",
    "ic_bar": "icBar",
    "dis_bar": "disBar",
    "kapanis_yeri": "kapanisYeri",
    "ters_iki_kapanis": "tersIkiKapanis",
    "tirasli": "tirasAd",
    "cevirme": "cevirmeKap",
    "cevirme_kademesi": "cevirmeKademe",
    "trendlesme": "diziKapanis",
    "govde_gucu": "govdeGuclu",
    "govde_boslugu": "govdeBosluk",
    # Bölüm 2 · sinyal barı ve kalıplar
    "ortusme": "ortusme",
    "donus_bari": "bogaDonus",
    "nitelikler": "n1Boga",
    "kalite": "kaliteBoga",
    "orta_nokta_olcutu": "ortaNoktaBoga",
    "iki_barlik_donus": "ikiBarAd",
    "bar_boyu": "barBoyuAd",
    "mikro_cift": "mikroCift",
    "kalip": "kalipAd",
    "kirilim_modu": "kalipTepe",
    "govde_ii": "govdeIcBar",
    "momentum_yoklugu": "momentumYok",
    # Bölüm 3 · 6 · 7 · 8A · 12
    "mikro_kanal": "mikroKanal",
    "bar_sayimi": "hEtiket",
    "bar_sayaci": "hSayac",
    "ma_dokundu": "maDokundu",
    "gap_sayaci": "gapSayac",
    "yon_filtresi": "yalnizAl",
    "always_in": "flipLong",
    "iptal_kurali": "iptalAd",
    # Bölüm 4.9 · rejim panosu
    "barbwire": "barbwire",
    "olcu_goreli": "siraOrtusme",
    # Kurulumlar (Bölüm 2 · 6 · 11 emir paketleri) — fiyat paneli dosyasında
    "donus": "kurBoga",
    "ikinci_giris": "ikinciBoga",
    "kirilim": "kalipTepe",
    "basarisiz_donus": "basarisizBoga",
    "bant_kenari": "bantBoga",
}

# Pine'da karşılığı OLMAYAN ve olmaması GEREKEN metotlar, gerekçesiyle.
# Gerekçe yazılmazsa bir sonraki oturum unutulmuş bir ölçü ile bilinçli bir
# muafiyeti ayırt edemez.
PINE_DISI: dict[str, str] = {
    "durum": "Pine'da tablo hücreleri; tek bir değişkeni yok",
    "kirp": "yalnız geleceğe bakma sınamasının aracı",
    "olcu": "rejim panosunun karşılığı ayrı dosyada, ayrı kapıda",
    "bar_sayimi_eski": "15.09.2026'ya kadarki sayaç; Pine'dan kaldırıldı, yalnız "
                       "eski kusurun büyüklüğünü ölçmek için duruyor (kendini_sina ⑧)",
    "_sayim_makinesi": "iç durum makinesi; okura giden üç görünümü bar_sayimi · "
                       "bar_sayaci · bar_sayaci_ham",
    "_paket": "Kurulumlar'ın iç yardımcısı: uç ± tick paketi",
    "BANT_YONU": "sınıf sabiti — beş ölçünün hangi tarafının bant olduğu; Pine'da "
                 "aynı bilgi i1–i5 karşılaştırmalarının yönünde",
    "bar_sayaci_ham": "Pine `hSayac`ı tavansız TUTAR ama kutuya min(hSayac,4) "
                      "basar; ham değer okura hiçbir yerde gösterilmez. Burada "
                      "yalnız 'etiket dörtte durdu, sayaç sürüyor' iddiasını "
                      "ÖLÇMEK için var — tavanlı diziyle bakan biri üç barda da "
                      "4 görür ve iddiayı kendi eliyle çürütür.",
}


_INPUT = re.compile(
    r"^\s*(?P<ad>\w+)\s*=\s*input\.(?P<tip>float|int|bool)\(\s*(?P<deger>[^,]+?)\s*,", re.M
)


def pine_sabitleri(yol: Path) -> dict[str, float | int | bool]:
    """Bir `.pine` dosyasının `input` varsayılanlarını okur."""
    out: dict[str, float | int | bool] = {}
    for m in _INPUT.finditer(yol.read_text(encoding="utf-8")):
        ham, tip = m.group("deger"), m.group("tip")
        out[m.group("ad")] = (ham.strip() == "true") if tip == "bool" else (
            int(ham) if tip == "int" else float(ham)
        )
    return out


def olcu_kapsami(pine_fh: Path, pine_rp: Path) -> list[str]:
    """Her Python ölçüsünün Pine'da bir karşılığı var mı — İKİ YÖNLÜ.

    Eşik kapısının göremediği kusuru kapatır: yeni bir eşik getirmeyen bir
    ölçü, Pine'a taşınmadan da eşik karşılaştırmasını geçer.

    KAPSAM SINIFTAN TÜRER. Ölçüt bir zamanlar TEK Pine dosyası alıyordu ve
    bütün ilanları ona karşı sınıyordu; `RejimPanosu`nun bir ölçüsü Pine
    karşılığını ilan ettiği anda, karşılığı öbür dosyada olduğu için ölçüt
    DÜŞÜYORDU. Yani rejim panosunun hiçbir ölçüsü karşılık ilan EDEMİYORDU
    ve tek çıkış yolu onu muafiyete yazmaktı — denetimin kendi kapsamı,
    ölçtüğü sözleşmeyi daraltıyordu. Artık her sınıf KENDİ dosyasına karşı
    sınanıyor."""
    # Kurulumlar da fiyat paneli dosyasına karşı sınanır: dersin emir paketleri
    # Pine'da çizilmiyorsa sayfadaki kod sayfadaki açıklamayı karşılamaz.
    kaynak = {FiyatPaneli: pine_fh, RejimPanosu: pine_rp, Kurulumlar: pine_fh}
    metin = {s: y.read_text(encoding="utf-8") for s, y in kaynak.items()}
    eksik: list[str] = []

    for sinif, yol in kaynak.items():
        for ad in vars(sinif):
            if ad.startswith("_"):
                continue
            # (a) Sınıfın her genel metodu ya ilan edilmiş ya muaf olmalı.
            if ad not in PINE_KARSILIGI and ad not in PINE_DISI:
                eksik.append(f"ölçü '{sinif.__name__}.{ad}' ne Pine karşılığı ne muafiyeti "
                             f"ilan etmiş — PINE_KARSILIGI ya da PINE_DISI'na yazılmalı")
                continue
            # (b) İlan edilen Pine adı O SINIFIN dosyasında ATANIYOR mu.
            pine_ad = PINE_KARSILIGI.get(ad)
            if pine_ad and not re.search(
                    r"^\s*(?:var\s+\w+\s+)?" + re.escape(pine_ad) + r"\s*(?::?=)",
                    metin[sinif], re.M):
                eksik.append(f"'{ad}' için ilan edilen Pine değişkeni '{pine_ad}' "
                             f"{yol.name} içinde atanmıyor — ölçü taşınmamış olabilir")

    # (c) İlan edilen ama HİÇBİR sınıfta karşılığı olmayan giriş: ölçü
    # silinmiş ama ilanı kalmış olabilir; ilan da bir sözleşmedir.
    tanimli = {a for s in kaynak for a in vars(s) if not a.startswith("_")}
    for py_ad in PINE_KARSILIGI:
        if py_ad not in tanimli:
            eksik.append(f"PINE_KARSILIGI'nda '{py_ad}' ilan edilmiş ama böyle bir "
                         "ölçü yok — silinen bir ölçünün ilanı kalmış olabilir")
    return eksik


def pine_ile_karsilastir(pine_fh: Path, pine_rp: Path) -> list[str]:
    """İki uygulamanın eşikleri AYRIŞMIŞ mı. Boş liste = ayrışma yok.

    Aynı kuralın iki uygulaması bir gün sessizce ayrışır; ayrışma ancak
    sorulursa görünür. Burada soruluyor."""
    ayrik: list[str] = []
    # Tanım seçimleri de karşılaştırılır: ders vermediği için SEÇTİĞİMİZ bir
    # sayının iki uygulamada farklı olması, dersten gelen bir eşiğin
    # ayrışmasından daha sinsidir — kimse onu bir yerde aramaz.
    fh_beyan = dict(SABIT_FH, **TANIM)
    for ad, yol, beyan in (("fiyat paneli", pine_fh, fh_beyan), ("rejim panosu", pine_rp, SABIT_RP)):
        p = pine_sabitleri(yol)
        for k, v in beyan.items():
            if k not in p:
                ayrik.append(f"{ad}: '{k}' Python'da var, Pine'da YOK")
            elif abs(float(p[k]) - float(v)) > 1e-9:
                ayrik.append(f"{ad}: '{k}' Pine {p[k]} ≠ Python {v}")
        for k in p:
            if k not in beyan and k not in ("aiZemin", "sinyalGoster", "sayimGoster",
                                            "maGoster", "kalipGoster", "asgariKalite",
                                            "kurulumGoster", "seviyeGoster", "ucgenGoster",
                                            "gapGoster"):
                ayrik.append(f"{ad}: '{k}' Pine'da var, Python'da YOK")
    return ayrik


# ── Seri: Pine'ın open/high/low/close dizileri ──────────────────────────────
@dataclass(frozen=True)
class Seri:
    """Kapanmış barlar. Pine'da bunlar `open`, `high`, `low`, `close`."""

    o: list[float]
    h: list[float]
    l: list[float]
    c: list[float]
    zaman: list[str] | None = None

    def __len__(self) -> int:
        return len(self.c)

    def kirp(self, n: int) -> "Seri":
        """İlk n barı tutar. Geleceğe bakma sınaması bunu kullanır."""
        return Seri(self.o[:n], self.h[:n], self.l[:n], self.c[:n],
                    None if self.zaman is None else self.zaman[:n])


# ── Pine gösterge fonksiyonlarının karşılıkları ─────────────────────────────
def ema(x: list[float], n: int) -> list[float | None]:
    """`ta.ema(close, n)`. İlk n−1 bar `na`; n'inci bar SMA ile tohumlanır."""
    a = 2.0 / (n + 1.0)
    out: list[float | None] = [None] * len(x)
    if len(x) < n:
        return out
    out[n - 1] = sum(x[:n]) / n
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]           # type: ignore[operator]
    return out


def en_yuksek(x: list[float], i: int, n: int) -> float:
    """`ta.highest(x[1], n)` — pencere i−1'de BİTER, şimdiki barı içermez.

    İLK BARDA PENCERE BOŞTUR ve Pine orada `na` döner; `na` ile yapılan her
    karşılaştırma `false`'tur. Python'da bunun birebir karşılığı `nan`:
    `x > nan` da `x < nan` de False. Boş pencerede istisna fırlatmak
    İKİ YÖNDE de yanlış olurdu — replikasyon Pine'dan ayrışır ve dosyayı
    kendi indirip koşturan okur, üretim yolunda hiç görünmeyen bir çökmeyle
    karşılaşır. Ölçülemeyen bir pencere boş bırakılır, uydurulmaz."""
    return max(x[max(0, i - n): i], default=math.nan)


def en_dusuk(x: list[float], i: int, n: int) -> float:
    """`ta.lowest(x[1], n)` — aynı sınır, aynı `na` sözleşmesi."""
    return min(x[max(0, i - n): i], default=math.nan)


def pencere_toplam(kosul, i: int, n: int) -> int:
    """`math.sum(kosul ? 1 : 0, n)` — pencere şimdiki barı İÇERİR."""
    return sum(1 for j in range(max(0, i - n + 1), i + 1) if kosul(j))


# ═══════════════════════════════════════════════════════════════════════════
#  FİYAT PANELİ — brooks-fiyat-hareketi.pine karşılığı
# ═══════════════════════════════════════════════════════════════════════════
class FiyatPaneli:
    """Pine betiğinin bar bar koşan gövdesi, açık döngüyle.

    Pine'da her satır her bar için bir kez koşar. Burada her satır bir
    METOTTUR ve `i` argümanını alır; `always_in`, `gap_sayaci` ve `bar_sayimi`
    gibi KALICI durum taşıyanlar ise bütün seriyi bir kez dolaşır — çünkü
    Pine'daki karşılıkları `var` ile açılmıştır."""

    def __init__(self, s: Seri, sabit: dict | None = None, tanim: dict | None = None):
        self.s = s
        self.k = dict(SABIT_FH, **(sabit or {}))
        self.t = dict(TANIM, **(tanim or {}))
        self.ema = ema(s.c, int(self.k["maUzunluk"]))

    # ── Bölüm 1 · Bar anatomisi ────────────────────────────────────────────
    def menzil(self, i: int) -> float:
        return self.s.h[i] - self.s.l[i]

    def govde(self, i: int) -> float:
        return abs(self.s.c[i] - self.s.o[i])

    def govde_orani(self, i: int) -> float:
        m = self.menzil(i)
        return self.govde(i) / m if m > 0 else 0.0

    def orta_nokta(self, i: int) -> float:
        return (self.s.h[i] + self.s.l[i]) / 2

    def alt_kuyruk(self, i: int) -> float:
        return min(self.s.o[i], self.s.c[i]) - self.s.l[i]

    def ust_kuyruk(self, i: int) -> float:
        return self.s.h[i] - max(self.s.o[i], self.s.c[i])

    def sinif(self, i: int) -> str:
        """Dersin sabitler tablosu: trend ≥ %50, güçlüsü ~%75+, doji %0–10."""
        g = self.govde_orani(i)
        if g >= self.k["gucluGovde"]:
            return "güçlü trend"
        if g >= self.k["trendGovde"]:
            return "trend"
        if g <= self.k["dojiGovde"]:
            return "doji"
        return "ara"

    def guclu_boga(self, i: int) -> bool:
        return self.govde_orani(i) >= self.k["gucluGovde"] and self.s.c[i] > self.s.o[i]

    def guclu_ayi(self, i: int) -> bool:
        return self.govde_orani(i) >= self.k["gucluGovde"] and self.s.c[i] < self.s.o[i]

    def ic_bar(self, i: int) -> bool:
        return i > 0 and self.s.h[i] <= self.s.h[i - 1] and self.s.l[i] >= self.s.l[i - 1]

    def dis_bar(self, i: int) -> bool:
        return i > 0 and self.s.h[i] >= self.s.h[i - 1] and self.s.l[i] <= self.s.l[i - 1]

    # ── Bölüm 2.3 · Örtüşme ────────────────────────────────────────────────
    def ortusme(self, i: int) -> float:
        """İki barın kesişiminin ÖNCEKİ barın menziline oranı."""
        if i == 0:
            return 0.0
        onceki = self.s.h[i - 1] - self.s.l[i - 1]
        if onceki <= 0:
            return 0.0
        kesisim = min(self.s.h[i], self.s.h[i - 1]) - max(self.s.l[i], self.s.l[i - 1])
        return max(0.0, kesisim) / onceki

    # ── Bölüm 12 · Always-in ───────────────────────────────────────────────
    def always_in(self) -> tuple[list[int], list[int], list[int]]:
        """Pine'daki `var int ai` — kalıcı durum, seriyi bir kez dolaşır.

        Üç parçalı kural: (1) aynı yönde iki ardışık GÜÇLÜ trend barı,
        (2) ikinci barın kapanış yönü doğru, (3) takip barının ölçütü bir
        YOKLUK — short'a dönüşte boğa kapanışı OLMAMASI, long'da ayı
        kapanışı OLMAMASI.

        Döner: (her barda yön, dönüş barları, ONAYLANMAYAN diziler).
        Üçüncüsü kuralın seçiciliğini ölçer."""
        ai, yon, donus, onaysiz = 0, [], [], []
        for i in range(len(self.s)):
            onceki = ai
            iki_boga = i >= 3 and self.guclu_boga(i - 1) and self.guclu_boga(i - 2)
            iki_ayi = i >= 3 and self.guclu_ayi(i - 1) and self.guclu_ayi(i - 2)
            if iki_boga and self.s.c[i] >= self.s.o[i]:
                ai = 1
            elif iki_ayi and self.s.c[i] <= self.s.o[i]:
                ai = -1
            elif iki_boga or iki_ayi:
                onaysiz.append(i)
            yon.append(ai)
            if ai != onceki and i > 0:
                donus.append(i)
        return yon, donus, onaysiz

    # ── Bölüm 2.2 · Sinyal barı ve canlı kalite ────────────────────────────
    def donus_bari(self, i: int, boga: bool) -> bool:
        """Asgari koşul: kapanış ya açılışın ya orta noktanın ötesinde."""
        orta = self.orta_nokta(i)
        if boga:
            return self.s.c[i] > self.s.o[i] or self.s.c[i] > orta
        return self.s.c[i] < self.s.o[i] or self.s.c[i] < orta

    def nitelikler(self, i: int, boga: bool) -> dict[str, bool]:
        """Dersin BEŞ ideal niteliğinden kapanmış bardan hesaplanabilen DÖRDÜ.

        Beşincisi — sinyalden SONRAKİ barın doji iç bar olmaması — bir sonraki
        bara bakar. Dersin cümlesi: 'Kalite skoru gerçek zamanda hiçbir zaman
        beş üzerinden beş olmaz.' O yüzden burada DÖRT nitelik var; beşinciyi
        eklemek indikatörü geleceğe baktırmak olurdu."""
        s, k = self.s, self.k
        m, alt, ust = self.menzil(i), self.alt_kuyruk(i), self.ust_kuyruk(i)
        kp, up, esik = int(k["kapanisPenc"]), int(k["ucPenc"]), k["ortusmeEsik"]
        if boga:
            n1 = s.o[i] <= s.c[i - 1] and s.c[i] > s.o[i] and s.c[i] > s.c[i - 1]
            n2 = m > 0 and m / 3 <= alt <= m / 2 and ust <= m * 0.15
            n5 = s.c[i] > en_yuksek(s.c, i, kp) and s.h[i] > en_yuksek(s.h, i, up)
        else:
            n1 = s.o[i] >= s.c[i - 1] and s.c[i] < s.o[i] and s.c[i] < s.c[i - 1]
            n2 = m > 0 and m / 3 <= ust <= m / 2 and alt <= m * 0.15
            n5 = s.c[i] < en_dusuk(s.c, i, kp) and s.l[i] < en_dusuk(s.l, i, up)
        return {"n1": n1, "n2": n2, "n3": self.ortusme(i) <= esik, "n5": n5}

    def kalite(self, i: int, boga: bool) -> int:
        """Canlı kalite: 0–4. Tavanı DÖRTTÜR ve bu bir seçim değil, kısıt."""
        return sum(self.nitelikler(i, boga).values())

    # ── Bölüm 7 · Hareketli ortalama ───────────────────────────────────────
    def ma_dokundu(self, i: int) -> bool:
        e = self.ema[i]
        return e is not None and self.s.l[i] <= e <= self.s.h[i]

    def gap_sayaci(self) -> list[int]:
        """Pine'daki `var int gapSayac` — ortalamaya dokunmayan ardışık bar."""
        out, sayac = [], 0
        for i in range(len(self.s)):
            sayac = 0 if self.ma_dokundu(i) else sayac + 1
            out.append(sayac)
        return out

    def ters_iki_kapanis(self, i: int) -> bool:
        """İki ardışık kapanış always-in yönünün TERSİNDE, ortalamaya göre.

        Pine'daki satır BİREBİR şöyle:
            (aiLong and close < ema and close[1] < ema) or
            (aiShort and close > ema and close[1] > ema)
        Dikkat — `close[1] < ema` ÖNCEKİ kapanışı BUGÜNKÜ ortalamayla kıyaslar
        (Pine'da `ema` indekssiz yazıldığında şimdiki bardır). Burada o yazım
        aynen korunuyor: bu dosya Pine'ın REPLİKASYONUDUR, düzeltilmiş hâli
        değil. İkisi ayrışırsa ölçü kapısı düşer ve hangisinin doğru olduğu
        ayrı bir karardır.

        Ders bunu bir TEŞHİS olarak kullanır: trendin karakteri değişmiş
        olabilir. Bir kurulum üretmez, bu yüzden kutuda uyarı olarak durur."""
        if i < 1:
            return False
        yon, _, _ = self.always_in()
        e = self.ema[i]
        if e is None or self.ema[i - 1] is None:
            return False
        c0, c1 = self.s.c[i], self.s.c[i - 1]
        if yon[i] == 1:
            return c0 < e and c1 < e
        if yon[i] == -1:
            return c0 > e and c1 > e
        return False

    def yon_filtresi(self, i: int) -> str:
        """Son 10 barın 7'si ortalamanın bir yanındaysa KARŞI yön yasaktır.

        Bu bir sinyal değil bir YASAKTIR: indikatör o yönde etiket basmaz."""
        pen, esik = int(self.k["yonPencere"]), int(self.k["yonEsik"])
        if i + 1 < pen or any(self.ema[j] is None for j in range(i - pen + 1, i + 1)):
            return "serbest"
        ust = pencere_toplam(lambda j: self.s.c[j] > self.ema[j], i, pen)   # type: ignore[operator]
        alt = pencere_toplam(lambda j: self.s.c[j] < self.ema[j], i, pen)   # type: ignore[operator]
        if ust >= esik:
            return "yalnız AL"
        if alt >= esik:
            return "yalnız SAT"
        return "serbest"

    # ── Bölüm 6 · Bar sayımı ───────────────────────────────────────────────
    def bar_sayimi_eski(self) -> list[str]:
        """15.09.2026'ya kadarki sayaç — ARTIK PINE'DA YOK, yalnız farkı ölçmek
        için duruyor: zirvesi öncekini aşan HER barı sayıyordu, iki ardışık
        yükselen bar H1·H2 oluyordu ve 1.297 etiketin %88'i tavan H4'tü.
        Dersin sayımı `bar_sayimi`de; kendini_sina ⑧ ikisinin farkını sınar."""
        yon, _, _ = self.always_in()
        h = l = 0
        gc_zirve = gc_dip = None
        out: list[str] = []
        for i in range(len(self.s)):
            if i > 0 and yon[i] != yon[i - 1]:
                h = l = 0
                gc_zirve = gc_dip = None
            etiket = ""
            if yon[i] == 1:
                if gc_zirve is None or self.s.h[i] > gc_zirve:
                    gc_zirve, h = self.s.h[i], 0
                elif i > 0 and self.s.h[i] > self.s.h[i - 1]:
                    h += 1
                    etiket = f"H{min(h, 4)}"
            elif yon[i] == -1:
                if gc_dip is None or self.s.l[i] < gc_dip:
                    gc_dip, l = self.s.l[i], 0
                elif i > 0 and self.s.l[i] < self.s.l[i - 1]:
                    l += 1
                    etiket = f"L{min(l, 4)}"
            out.append(etiket)
        return out

    def _sayim_makinesi(self) -> list[tuple[int, int, str]]:
        """Bölüm 6.4'ün sayımı, Pine `hSayac`/`lSayac`/`hEtiket` ile aynı durum
        makinesi. Döner: her bar için (h, l, etiket).

        Ders sayımı BACAKLA kurar: high 1 geri çekilmede zirvesi öncekini aşan
        ilk bar; geri çekilme SÜRERSE (zirvesi öncekini aşmayan bir bar daha
        gelirse) ve yeniden bir bar öncekini aşarsa o bar high 2. Yani iki
        sayım arasında en az bir "aşamayan" bar olmalı. Yeni bir trend
        zirvesi sayımı sıfırlar; always-in dönüşü de. Rejim filtresi dersten:
        boğa trendinde low sayılmaz, ayıda high.

        Ölçüldü (15.09.2026, 13 seri): eski sayaç zirvesi öncekini aşan HER
        barı sayıyordu — iki ardışık yükselen bar H1·H2 oluyor, 1.297
        etiketin %88'i tavan H4'e düşüyordu (`bar_sayimi_eski`).

        DIŞARIDA KALAN, dersin kendi cümlesiyle: 'high 1 ile high 2 arasında
        en az küçücük bir trend çizgisi kırılımı olmalıdır' — çizgi çizmek
        yorum işidir ve sayaç onu sormaz."""
        yon, _, _ = self.always_in()
        h = l = 0
        gc_zirve = gc_dip = None
        bekle_h = bekle_l = False        # sonraki sayım için araya "aşamayan" bar gerekiyor mu
        out: list[tuple[int, int, str]] = []
        for i in range(len(self.s)):
            if i > 0 and yon[i] != yon[i - 1]:
                h = l = 0
                gc_zirve = gc_dip = None
                bekle_h = bekle_l = False
            etiket = ""
            if yon[i] == 1:
                if gc_zirve is None or self.s.h[i] > gc_zirve:
                    gc_zirve, h, bekle_h = self.s.h[i], 0, False
                elif i > 0 and self.s.h[i] > self.s.h[i - 1]:
                    if not bekle_h:
                        h += 1
                        bekle_h = True
                        etiket = f"H{min(h, 4)}"
                else:
                    bekle_h = False
            elif yon[i] == -1:
                if gc_dip is None or self.s.l[i] < gc_dip:
                    gc_dip, l, bekle_l = self.s.l[i], 0, False
                elif i > 0 and self.s.l[i] < self.s.l[i - 1]:
                    if not bekle_l:
                        l += 1
                        bekle_l = True
                        etiket = f"L{min(l, 4)}"
                else:
                    bekle_l = False
            out.append((h if yon[i] == 1 else 0, l if yon[i] == -1 else 0, etiket))
        return out

    def bar_sayimi(self) -> list[str]:
        """Grafikteki ETİKET (Pine `hEtiket`/`lEtiket`): yalnız sayım barında
        dolu ("H1"…"H4", "L1"…"L4"), gerisi ""."""
        return [e for _, _, e in self._sayim_makinesi()]

    def bar_sayaci(self) -> list[str]:
        """Pine'daki durum kutusunun bastığı SAYAÇ — etiket değil.

        `bar_sayimi` grafikteki ETİKETİN eşidir ve yalnız sayım barında
        doludur. Kutu ise always-in'in yönü varken HER barda sayacın o anki
        değerini yazar:
            aiLong ? "H"+min(hSayac,4) : aiShort ? "L"+min(lSayac,4) : "—"
        İki ölçü ayrı isimlerle durur, çünkü ikisi de Pine'da ayrı ayrı var
        ve ikisi de okura ayrı yerde görünüyor."""
        yon, _, _ = self.always_in()
        return [f"H{min(h, 4)}" if yon[i] == 1 else f"L{min(l, 4)}" if yon[i] == -1 else "—"
                for i, (h, l, _) in enumerate(self._sayim_makinesi())]

    def bar_sayaci_ham(self) -> list[int]:
        """`hSayac`/`lSayac`ın TAVANSIZ hâli — işaretli (boğa +, ayı −).

        Pine sayacı tavansız TUTAR ama kutuya `min(hSayac, 4)` basar; "etiket
        dörtte durdu ama sayaç sürüyor" iddiası ancak tavansız değerle
        ÖLÇÜLEBİLİR."""
        yon, _, _ = self.always_in()
        return [h if yon[i] == 1 else -l if yon[i] == -1 else 0
                for i, (h, l, _) in enumerate(self._sayim_makinesi())]

    # ── Bölüm 1.2 · Kapanışın menzil içindeki yeri ─────────────────────────
    def kapanis_yeri(self, i: int) -> float:
        """(kapanış − dip) / menzil. Ders: 'gövdenin büyüklüğünden bile daha
        bilgi verici — çünkü kapanış, mücadelenin nihai skorudur.' %50 berabere."""
        m = self.menzil(i)
        return (self.s.c[i] - self.s.l[i]) / m if m > 0 else 0.5

    # ── Bölüm 1.1 · Tıraşlı bar ────────────────────────────────────────────
    def tirasli(self, i: int, tick: float = 0.0) -> str:
        """Kuyruğu olmayan uç. Ders §2.6: 'Tepede bir tick kuyruk … hâlâ
        güçlüdür' — o yüzden ölçü tam sıfır değil, BİR TİCK toleranslı.
        Tick verilmezse tam sıfır aranır (sentetik seride tick yoktur)."""
        ust, alt = self.ust_kuyruk(i) <= tick, self.alt_kuyruk(i) <= tick
        return "marubozu" if (ust and alt) else "tıraşlı tepe" if ust else "tıraşlı dip" if alt else ""

    # ── Bölüm 1.10b · Çevirme sayaçları ────────────────────────────────────
    def cevirme(self, i: int) -> dict[str, int]:
        """Bu bar KAÇ önceki barın kapanışını ve ucunu tersine çevirdi.

        Ders: 'barın kapanış seviyesinden geriye doğru bakın ve o çizginin
        altında kalan kapanış sayısını sayın.' Sayım ARDIŞIKTIR — ilk
        aşılamayan barda durur; toplam sayım bir pencere seçimi isterdi ve
        ders pencere vermiyor. Uç sayacı ile kapanış sayacı AYRI tutulur;
        ders ikincisinin daha ağır bastığını söyler: 'Bir seviyeyi kuyrukla
        aşan bar reddedilmiştir; kapanışla aşan bar o emirleri tüketmiştir.'"""
        s, tavan = self.s, int(self.t["cevirmeTavan"])
        boga = s.c[i] > s.o[i]
        kap = uc = 0
        for j in range(i - 1, max(-1, i - 1 - tavan), -1):
            if (s.c[i] > s.c[j]) if boga else (s.c[i] < s.c[j]):
                kap += 1
            else:
                break
        for j in range(i - 1, max(-1, i - 1 - tavan), -1):
            if (s.c[i] > s.h[j]) if boga else (s.c[i] < s.l[j]):
                uc += 1
            else:
                break
        return {"kapanis": kap, "uc": uc}

    def cevirme_kademesi(self, i: int) -> str:
        """Sayacın kademesi — dersin sayılarıyla, dersin HÜKMÜ OLMADAN.

        Ders üç kademe verir (< 3 sıradan · > 5 rejim iddiası · > 15 büyük
        olasılıkla always-in yönünü çeviren kırılım) ve üçüncüsü SINANDI.
        4.314 gerçek bar üzerinde ölçüldü:

          · Sayaç gerçekten sinyal taşıyor: always-in dönüşünün onaylandığı
            barlarda medyan 30, bütün barlarda 3; >15 payı %55'e karşı %24,3.
          · Ama HÜKÜM olarak tutmuyor: '>15' diyen 1.047 barın yalnız 11'i
            gerçekten dönüş barı — kesinlik %1,05, taban oran %0,46. Yani
            ihtimali iki katına çıkarıyor ve orada bırakıyor.

        Sebep ölçünün kendisinde: ardışık geriye tarama, güçlü bir trendde
        her yeni uç kapanışında trendin başına kadar sayar; ölçü "dönüşü"
        değil "trendin uzunluğunu" ölçmeye başlar. Bu yüzden üçüncü kademe
        SONUCUYLA değil BÜYÜKLÜĞÜYLE adlandırılır: sayı basılır, hüküm
        basılmaz. Dersin eşikleri 5 dakikalık barda kalibre; buradaki ölçüm
        1 saatlik, 4 saatlik ve günlük barlardan — kademe o ölçekte
        tutuyor olabilir, bu veri onu söyleyemez."""
        n = self.cevirme(i)["kapanis"]
        if n > self.k["cevirmeKirilim"]:
            return "çok güçlü çevirme"
        if n > self.k["cevirmeRejim"]:
            return "rejim iddiası"
        return "sıradan" if n < self.k["cevirmeSiradan"] else "ara"

    # ── Bölüm 1.3 · Trendleşme ─────────────────────────────────────────────
    def trendlesme(self, i: int) -> dict[str, int]:
        """Ardışık kaç barda kapanış / zirve / dip aynı yöne gidiyor.
        Dersin asgari eşiği ÜÇ; üçünde de aynı."""
        s = self.s
        out = {}
        for ad, dizi in (("kapanis", s.c), ("zirve", s.h), ("dip", s.l)):
            yukari = asagi = 0
            for j in range(i, 0, -1):
                if dizi[j] > dizi[j - 1]:
                    yukari += 1
                else:
                    break
            for j in range(i, 0, -1):
                if dizi[j] < dizi[j - 1]:
                    asagi += 1
                else:
                    break
            out[ad] = yukari if yukari >= asagi else -asagi
        return out

    # ── Bölüm 1.3 · Göreli gövde gücü ──────────────────────────────────────
    def govde_gucu(self, i: int) -> bool:
        """Ders: 'Bir gövde, son 5–10 barın MEDYAN gövdesi kadar veya daha
        büyükse güçlüdür.' Mutlak gövde eşiği kullanılmaz; ölçü göreceli."""
        n = int(self.t["medyanPencere"])
        if i < n:
            return False
        onceki = sorted(self.govde(j) for j in range(i - n, i))
        return self.govde(i) >= onceki[len(onceki) // 2]

    # ── Bölüm 1.6 · Gövde boşluğu ──────────────────────────────────────────
    def govde_boslugu(self, i: int) -> int:
        """Boğa trendinde açılış, önceki barın KAPANIŞININ üstünde.
        Kuyruklar örtüşebilir; ölçülen şey gövdelerdir. İkili: 1 · −1 · 0."""
        if i == 0:
            return 0
        return 1 if self.s.o[i] > self.s.c[i - 1] else -1 if self.s.o[i] < self.s.c[i - 1] else 0

    # ── Bölüm 1.8 · 2.5 · İç/dış bar kalıpları ve kırılım modu ─────────────
    def kalip(self, i: int) -> str:
        """ii · iii · ioi · oio · oo. Dersin ortak dili: 'Bu dört kalıbın
        hepsi aynı şeyi söyler: KALIP BİR YATAY BANTTIR. Yön bilinmez.'
        Bu yüzden çıktı yön değil, KIRILIM MODUDUR: iki tarafa da emir."""
        ic = lambda j: j > 0 and self.ic_bar(j)
        dis = lambda j: j > 0 and self.dis_bar(j)
        if i >= 3 and ic(i) and ic(i - 1) and ic(i - 2):
            return "iii"
        if i >= 3 and ic(i) and dis(i - 1) and ic(i - 2):
            return "ioi"
        if i >= 3 and dis(i) and ic(i - 1) and dis(i - 2):
            return "oio"
        if i >= 2 and ic(i) and ic(i - 1):
            return "ii"
        if i >= 2 and dis(i) and dis(i - 1) and self.menzil(i) > self.menzil(i - 1):
            return "oo"
        return ""

    def govde_ii(self, i: int) -> bool:
        """"Yalnızca gövdeler ii": kuyruklar yok sayılır, ikinci gövde
        birincinin içindedir. Ders bunu ii'nin "daha az güvenilir bir
        çeşidi" diye adlandırır — o yüzden ayrı bir ad taşır, ii sayılmaz."""
        if i < 1 or self.ic_bar(i):
            return False
        ust, alt = max(self.s.o[i], self.s.c[i]), min(self.s.o[i], self.s.c[i])
        oust, oalt = max(self.s.o[i - 1], self.s.c[i - 1]), min(self.s.o[i - 1], self.s.c[i - 1])
        return ust <= oust and alt >= oalt

    def momentum_yoklugu(self, i: int) -> int:
        """Kaç bardır boğa (ya da ayı) kapanışı YOK.

        Dersin ikinci giriş ilkesindeki eşik: "Günün yeni dibinde ilk alış
        girişi ama ALTI BAR boyunca boğa kapanışı yok → ikinci alış girişini
        bekleyin." Pozitif = boğa kapanışı yok, negatif = ayı kapanışı yok.

        Dersin bu ölçüyü kullandığı KURULUM (ikinci giriş) indikatörde YOK:
        "ilk giriş oldu mu" sorusu bir kurulum takibi ister ve o bir yorum
        işidir. Ölçünün kendisi saf."""
        boga = ayi = 0
        for j in range(i, -1, -1):
            if self.s.c[j] > self.s.o[j]:
                break
            boga += 1
        for j in range(i, -1, -1):
            if self.s.c[j] < self.s.o[j]:
                break
            ayi += 1
        return boga if boga >= ayi else -ayi

    def kirilim_modu(self, i: int) -> dict | None:
        """Kalıbın üstüne alış stop, altına satış stop; biri tetiklenince
        öbürü iptal. Stop, dolmamış olan karşı emirdir."""
        k = self.kalip(i)
        if not k:
            return None
        n = 3 if k in ("iii", "ioi", "oio") else 2
        tepe = max(self.s.h[i - n + 1: i + 1])
        dip = min(self.s.l[i - n + 1: i + 1])
        return {"kalip": k, "alis_stop": tepe, "satis_stop": dip, "yukseklik": tepe - dip}

    # ── Bölüm 2.3 · Orta nokta ölçütü ──────────────────────────────────────
    def orta_nokta_olcutu(self, i: int, boga: bool) -> bool:
        """Örtüşme kuralının ADI OLAN hâli; sabitler tablosunda böyle geçer:
        'Sinyal barında örtüşme kuralı — kapanış, önceki barın ORTA
        NOKTASININ ötesinde.' Dersin Şekil 15'i iki paneli tam buradan
        ayırır: kabul edilen bar orta noktanın üstünde, reddedilen altında
        kapanıyor. %75'lik örtüşme eşiği AYRI bir ölçüttür ve 'iki barlık
        dönüş oku' der; bu ise barın kabul/ret sınırıdır."""
        if i == 0:
            return False
        orta = (self.s.h[i - 1] + self.s.l[i - 1]) / 2
        return self.s.c[i] > orta if boga else self.s.c[i] < orta

    # ── Bölüm 2.4 · İki barlık dönüş ───────────────────────────────────────
    def iki_barlik_donus(self, i: int) -> str:
        """'Yaklaşık aynı boyda, zıt yönlü iki trend barı.' Giriş HER İKİ
        barın ötesine konur — dibi önceki barın bir tick üstünde olan bir
        ayı dönüş barı sık sık ayı tuzağıdır.

        'Kabaca eşit' bir TANIM SEÇİMİDİR; ders sayı vermez."""
        if i < 1:
            return ""
        tb = lambda j: self.govde_orani(j) >= self.k["trendGovde"]
        if not (tb(i) and tb(i - 1)):
            return ""
        a, b = self.s.c[i - 1] - self.s.o[i - 1], self.s.c[i] - self.s.o[i]
        if a * b >= 0:
            return ""
        buyuk, kucuk = max(abs(a), abs(b)), min(abs(a), abs(b))
        if buyuk <= 0 or kucuk / buyuk < self.t["esitGovdeOran"]:
            return ""
        return "iki barlık dönüş (boğa)" if b > 0 else "iki barlık dönüş (ayı)"

    # ── Bölüm 2.6 · Küçük bar · tükeniş barı · mikro çift dip/tepe ─────────
    def bar_boyu(self, i: int) -> str:
        """Küçük bar ve tükeniş barı. İkisinin de ölçüsü GÖRECELİdir; oranlar
        tanım seçimidir, dersin verdiği tek sayı tükenişin BAĞLAMIDIR:
        '10 veya daha fazla bar süren bir trendin içinde alışılmadık
        büyüklükte bir bar.'"""
        n = int(self.t["medyanPencere"])
        if i < n:
            return ""
        ort = sum(self.menzil(j) for j in range(i - n, i)) / n
        if ort <= 0:
            return ""
        if self.menzil(i) < ort * self.t["kucukBarOran"]:
            return "küçük bar"
        if self.menzil(i) > ort * self.t["tukenisOran"]:
            tr = self.trendlesme(i)
            uzun = abs(tr["kapanis"]) >= self.k["tukenisTrendBar"]
            return "tükeniş barı" if uzun else "alışılmadık büyük bar"
        return ""

    def mikro_cift(self, i: int) -> str:
        """'Ardışık veya neredeyse ardışık, dipleri (veya tepeleri) aynı ya
        da neredeyse aynı olan barlar.' Dersin uyarısı kodda DEĞİL sayfada:
        bu kalıbın bağlama göre İKİ TAMAMEN ZIT anlamı vardır — ayı spike'ı
        içinde tek barlık bayrak (devam), başka her yerde dönüş. İndikatör
        kalıbı gösterir, hükmü vermez.

        'Neredeyse aynı' bir TANIM SEÇİMİDİR; ders sayı vermez."""
        if i < 1:
            return ""
        tol = self.menzil(i) * self.t["mikroTolerans"]
        if tol <= 0:
            return ""
        if abs(self.s.l[i] - self.s.l[i - 1]) <= tol:
            return "mikro çift dip"
        if abs(self.s.h[i] - self.s.h[i - 1]) <= tol:
            return "mikro çift tepe"
        return ""

    # ── Bölüm 3.8 · Mikro kanal ────────────────────────────────────────────
    def mikro_kanal(self, i: int) -> int:
        """Geri çekilmesiz ardışık bar sayısı: boğa mikro kanalında hiçbir
        barın dibi bir öncekinin altına inmez. Pozitif = boğa, negatif = ayı."""
        s = self.s
        yukari = asagi = 0
        for j in range(i, 0, -1):
            if s.l[j] >= s.l[j - 1]:
                yukari += 1
            else:
                break
        for j in range(i, 0, -1):
            if s.h[j] <= s.h[j - 1]:
                asagi += 1
            else:
                break
        return yukari if yukari >= asagi else -asagi

    # ── Bölüm 8A.6 · Beş bar iptal kuralı ──────────────────────────────────
    def iptal_kurali(self, i: int) -> dict:
        """'Eski ucun ötesinde ≥ 5 KAPANIŞ' → dönüş arayışı iptal edilir.
        Eşik bir ÜST SINIRDIR: geçmek kurulumu öldürür. Ölçü kapanışla
        yapılır, uçla değil — ucun aşılması bir deneme, kapanışın aşılması
        bir sonuçtur."""
        n = int(self.k["iptalKapanis"])
        if i < n:
            return {"boga": 0, "ayi": 0, "iptal": ""}
        onceki_tepe = max(self.s.h[max(0, i - 40): i - n + 1] or [self.s.h[i]])
        onceki_dip = min(self.s.l[max(0, i - 40): i - n + 1] or [self.s.l[i]])
        ust = sum(1 for j in range(i - n + 1, i + 1) if self.s.c[j] > onceki_tepe)
        alt = sum(1 for j in range(i - n + 1, i + 1) if self.s.c[j] < onceki_dip)
        return {"boga": ust, "ayi": alt,
                "iptal": "ayı dönüşü arayışı iptal" if ust >= n
                else "boğa dönüşü arayışı iptal" if alt >= n else ""}

    # ── Durum kutusu — Pine'daki sağ üst tablo ─────────────────────────────
    def durum(self, i: int) -> dict:
        """Barın BÜTÜN çıktıları. Geleceğe bakma sınaması bunu karşılaştırır.

        Kalite, dönüş barı koşuluna BAĞLANMADAN raporlanır: koşula bağlansaydı
        dönüş barı olmayan barlarda niteliklerdeki bir sızıntı görünmez kalır
        ve sınama onu kaçırırdı. Bir kapının ölçtüğü şeyi daraltmak, kapıyı
        kapatmanın sessiz biçimidir."""
        yon, _, _ = self.always_in()
        gap = self.gap_sayaci()
        return {
            "always_in": {1: "LONG", -1: "SHORT", 0: "—"}[yon[i]],
            "yon_filtresi": self.yon_filtresi(i),
            "ters_iki_kapanis": self.ters_iki_kapanis(i),
            "gap_bar": gap[i],
            "bar_sayimi": self.bar_sayimi()[i] or "—",
            "bar_sayaci": self.bar_sayaci()[i],
            "bar_sinifi": self.sinif(i),
            "ortusme": round(self.ortusme(i), 6),
            "ic_bar": self.ic_bar(i),
            "dis_bar": self.dis_bar(i),
            "donus_boga": self.donus_bari(i, True),
            "donus_ayi": self.donus_bari(i, False),
            "nitelik_boga": self.nitelikler(i, True),
            "nitelik_ayi": self.nitelikler(i, False),
            "kapanis_yeri": round(self.kapanis_yeri(i), 3),
            "tirasli": self.tirasli(i),
            "cevirme": self.cevirme(i),
            "cevirme_kademesi": self.cevirme_kademesi(i),
            "trendlesme": self.trendlesme(i),
            "govde_gucu": self.govde_gucu(i),
            "govde_boslugu": self.govde_boslugu(i),
            "kalip": self.kalip(i),
            "govde_ii": self.govde_ii(i),
            "momentum_yoklugu": self.momentum_yoklugu(i),
            "orta_nokta_boga": self.orta_nokta_olcutu(i, True),
            "orta_nokta_ayi": self.orta_nokta_olcutu(i, False),
            "iki_barlik": self.iki_barlik_donus(i),
            "bar_boyu": self.bar_boyu(i),
            "mikro_cift": self.mikro_cift(i),
            "mikro_kanal": self.mikro_kanal(i),
            "iptal": self.iptal_kurali(i),
        }


# ═══════════════════════════════════════════════════════════════════════════
#  ALT PANEL — brooks-rejim-panosu.pine karşılığı
# ═══════════════════════════════════════════════════════════════════════════
class RejimPanosu:
    """Yatay bant tanı listesinin ÖLÇÜLEBİLİR beş maddesi.

    Neden bant tarafında sayaç var, trend tarafında yok: ders iki listeye
    farklı davranır. Güçlü trend listesi için 'Maddeler eşit ağırlıklı
    değildir ve sayılmaz; okunur' der; bant listesi için 'Beş veya daha fazla
    madde işaretliyse…' diyerek sayıyı KENDİSİ kullanır."""

    def __init__(self, s: Seri, sabit: dict | None = None):
        self.s = s
        self.k = dict(SABIT_RP, **(sabit or {}))
        self.pencere = int(self.k["pencere"])
        self.ema = ema(s.c, int(self.k["maUzunluk"]))

    def _govde(self, j: int) -> float:
        m = self.s.h[j] - self.s.l[j]
        return abs(self.s.c[j] - self.s.o[j]) / m if m > 0 else 0.0

    def _ortusme(self, j: int) -> float:
        if j == 0:
            return 0.0
        onceki = self.s.h[j - 1] - self.s.l[j - 1]
        if onceki <= 0:
            return 0.0
        return max(0.0, min(self.s.h[j], self.s.h[j - 1]) - max(self.s.l[j], self.s.l[j - 1])) / onceki

    def barbwire(self, i: int) -> dict:
        """Bölüm 4.9 · barbwire — rejim panosunun DOKUZUNCU satırı.

        SABIT_RP bu üç sabiti (bwBar · bwOrtaPay · bwDoji) taşıyordu ve
        onları kullanan hiçbir kod YOKTU: Pine ölçüyü hesaplayıp kutuya
        basıyor, replikasyon hiç hesaplamıyordu — "iki uygulama sessizce
        ayrıştı" kusurunun bir eşi. 4.548 barın 563'ünde (%12,4) VAR.

        Ölçü ORTADAKİ bara bakar (Pine'da `[1]`), komşuları `[2]` ve `[0]`:
        ortadaki barın menzilinin yarıdan fazlası her iki komşusunun da
        içindeyse ve üç barın en az biri doji ise barbwire.

        Bant SAYISINA GİRMEZ ve bu bir seçim değil dersin hükmü: barbwire
        bir rejim ölçüsü değil, tekil bir bar kalıbıdır."""
        s = self.s
        if i < 2:
            return {"var": False, "oran": 0.0}
        orta = s.h[i - 1] - s.l[i - 1]
        kes_once = min(s.h[i - 1], s.h[i - 2]) - max(s.l[i - 1], s.l[i - 2])
        kes_sonra = min(s.h[i - 1], s.h[i]) - max(s.l[i - 1], s.l[i])
        ortusuyor = (orta > 0
                     and max(0.0, kes_once) / orta > self.k["bwOrtaPay"]
                     and max(0.0, kes_sonra) / orta > self.k["bwOrtaPay"])
        bw_bar = int(self.k["bwBar"])
        doji = sum(1 for j in range(max(0, i - bw_bar + 1), i + 1)
                   if self._govde(j) <= self.k["dojiGovde"])
        return {"var": bool(ortusuyor and doji >= int(self.k["bwDoji"])),
                "oran": (max(0.0, min(kes_once, kes_sonra)) / orta) if orta > 0 else 0.0}

    def olcu(self, i: int) -> dict | None:
        """Beş ölçü + kaçının bant tarafında olduğu. Pencere dolmadıysa None."""
        s, k, w = self.s, self.k, self.pencere
        if i + 1 < w or self.ema[i] is None or self.ema[i - w + 1] is None:
            return None
        pen = range(i - w + 1, i + 1)

        ortusme_oran = sum(1 for j in pen if self._ortusme(j) >= k["ortusmeEsik"]) / w
        doji_oran = sum(1 for j in pen if self._govde(j) <= k["dojiGovde"]) / w
        kesisme = sum(
            1 for j in pen
            if self.ema[j] is not None and self.ema[j - 1] is not None
            and ((s.c[j] > self.ema[j] and s.c[j - 1] <= self.ema[j - 1])
                 or (s.c[j] < self.ema[j] and s.c[j - 1] >= self.ema[j - 1]))
        )
        aralik = max(s.h[j] for j in pen) - min(s.l[j] for j in pen)
        net_aralik = abs(s.c[i] - s.c[i - w + 1]) / aralik if aralik > 0 else 0.0

        dizi = azami = yon = 0
        for j in pen:
            trend = self._govde(j) >= 0.50
            bu = 1 if (trend and s.c[j] > s.o[j]) else -1 if (trend and s.c[j] < s.o[j]) else 0
            dizi = dizi + 1 if (bu != 0 and bu == yon) else (1 if bu != 0 else 0)
            yon = bu
            azami = max(azami, dizi)

        isaret = {
            "ortusme": ortusme_oran >= k["ortusmePay"],
            "doji": doji_oran >= k["dojiPay"],
            "kesisme": kesisme >= int(k["kesismeEsik"]),
            "net": net_aralik <= k["netEsik"],
            "dizi": azami < int(k["diziEsik"]),
        }
        n = sum(isaret.values())
        return {
            "ortusme_oran": round(ortusme_oran, 3), "doji_oran": round(doji_oran, 3),
            "kesisme": kesisme, "net_aralik": round(net_aralik, 3), "azami_dizi": azami,
            "barbwire": self.barbwire(i),
            "isaret": isaret, "n": n,
            "rejim": "BANT" if n >= 4 else "trend" if n <= 1 else "ara",
        }

    # Beş ölçünün YÖNÜ: hangi taraf "bant". Göreli eşik bu tabloyu okur.
    BANT_YONU = {"ortusme_oran": "ge", "doji_oran": "ge", "kesisme": "ge",
                 "net_aralik": "le", "azami_dizi": "le"}

    def _ham(self, i: int) -> dict | None:
        """`olcu`nun önbelleği: göreli sıra 280 barlık tarihçe ister ve her
        bar için tarihçeyi yeniden hesaplamak O(pencere × tarihçe) olurdu."""
        if not hasattr(self, "_ham_onbellek"):
            self._ham_onbellek: dict[int, dict | None] = {}
        if i not in self._ham_onbellek:
            self._ham_onbellek[i] = self.olcu(i)
        return self._ham_onbellek[i]

    def olcu_goreli(self, i: int) -> dict | None:
        """Aynı beş ölçü, eşik KENDİ TARİHÇESİNDEN.

        NEDEN. Dersin Şekil 30 eşikleri tek bir seride, tek bir günde ölçülmüş
        SEVİYELERDİR ve ölçüldü (15.09.2026): seviyeler enstrümana ve beslemeye
        göre kayıyor — örtüşme işareti 1 saatlik 13 serinin 9'unda %100 açık,
        Yahoo 5 dk EUR/USD'de %3, USD/CHF'de %100, GBP/USD'de %9; doji
        işareti 13 seride %0. Sabit bir eşik bir enstrümanda hep "bant",
        öbüründe hiç "bant" der ve ikisi de rejim ölçmez. Göreli eşik her
        ölçüyü son `tarihce` bardaki kendi değerlerine göre sıralar: ölçü
        tarihçesinin %60'ından daha bantlıysa işaret. Böylece her ölçü her
        seride ortalama %40 dolayında açık kalır ve pano "bugün, bu enstrüman
        için, son günlere göre" konuşur.

        ÖLÇÜLMÜŞ SINIR, adıyla: göreli hüküm de ileriye dönük bir şey
        SÖYLEMİYOR — 5 seri × 2 tarihçede BANT ile trend pencerelerinin ileri
        35 barlık net/aralık'ı ayrışmıyor (permütasyon p 0,19–0,94; mutlak
        hükümde de aynı). Pano bir rejim TARİFİDİR, tahmin değil; kurulum
        ailesini seçtirir, yönü ya da kenarı ilan etmez.

        Sıra Pine `ta.percentrank(x, tarihce)` sözleşmesiyle: ÖNCEKİ tarihce
        barın (i dahil değil) kaçı ≤ bugünkü değer; payda tarihce. ≤-tipi
        ölçüde (net/aralık · dizi) işaret `ta.percentrank(-x, …)` ile, yani
        kaçı ≥ bugünkü değer. Tarihçe dolmadıysa None."""
        k = self.k
        n_t = int(k["tarihce"])
        bugun = self._ham(i)
        if bugun is None or i - n_t < 0:
            return None
        gecmis = [self._ham(j) for j in range(i - n_t, i)]
        if any(g is None for g in gecmis):
            return None
        sira: dict[str, float] = {}
        isaret: dict[str, bool] = {}
        for ad, yon in self.BANT_YONU.items():
            v = bugun[ad]
            if yon == "ge":
                sira[ad] = sum(1 for g in gecmis if g[ad] <= v) / n_t     # type: ignore[index]
            else:
                sira[ad] = sum(1 for g in gecmis if g[ad] >= v) / n_t     # type: ignore[index]
            isaret[ad.split("_")[0] if ad != "azami_dizi" else "dizi"] = sira[ad] >= k["goreliPay"]
        n = sum(isaret.values())
        return {
            **{ad: bugun[ad] for ad in self.BANT_YONU},
            "sira": {ad: round(v, 3) for ad, v in sira.items()},
            "barbwire": bugun["barbwire"],
            "isaret": isaret, "n": n,
            "rejim": "BANT" if n >= 4 else "trend" if n <= 1 else "ara",
        }


# ═══════════════════════════════════════════════════════════════════════════
#  KURULUMLAR — Bölüm 2 · 6 · 11: OHLC'den kurulabilen EMİR PAKETLERİ
# ═══════════════════════════════════════════════════════════════════════════
class Kurulumlar:
    """Dersin emir paketleri, kapanmış bar i'de sorulur; ya bir EMİR döner
    ya None. Emir mekaniği (dolum, stop, hedef, yönetim) burada DEĞİL —
    site/tools/brooks_backtest.py'de; bu sınıf yalnız "hangi barda hangi
    seviyeye hangi emir" sorusunu cevaplar.

    Dört paket, dördü de dersin sayısıyla:
      · `donus`           — 2.1/11.1 standart paket: sinyal barının ucu
                            + 1 tick stop emri, karşı uç − 1 tick koruyucu
                            stop. Dönüş barı koşulu ve kalite 2.2'den.
      · `ikinci_giris`    — 2.9 + 6.4: always-in yönünde H2/L2 barı; aynı
                            paket. "İlk giriş stop yedikten sonra ikinci
                            sinyal alınır" ilkesinin bar sayımıyla
                            kurulmuş hâli.
      · `kirilim`         — 2.5: ii · iii · ioi · oio · oo — kalıbın üstüne
                            alış stop, altına satış stop; biri dolunca öbürü
                            koruyucu stop olur. YÖN BİLİNMEZ, iki taraf.
      · `basarisiz_donus` — 2.7: trend içindeki karşı dönüş barı ters
                            taraftan kırılırsa (ayı dönüş barının ÜSTÜNE
                            çıkılırsa) trend yönünde giriş; tuzağa düşen
                            karşı tarafın çıkışı yakıttır.
      · `bant_kenari`     — 4.5/4.6/4.12: BANT'ta yalnız uç üçte birde,
                            bant ≥ 3 × stop ise, hedef bandın içinde
                            kalıyorsa ve HO süzgeci izin veriyorsa; dönüş
                            barı ucundan standart paket.

    Tick zorunludur ve seriden GELMEZ: ders emirleri "bir tick ötesine"
    koyar ve tick'siz bir paket o cümleyi taşımaz."""

    def __init__(self, s: Seri, tick: float, sabit: dict | None = None,
                 tanim: dict | None = None):
        if not tick or tick <= 0:
            raise ValueError("Kurulumlar tick ister: dersin emirleri 'bir tick ötesine' konur")
        self.s, self.tick = s, float(tick)
        self.fp = FiyatPaneli(s, sabit, tanim)
        self.rp = RejimPanosu(s)
        self.ai, _, _ = self.fp.always_in()
        self.sayim = self.fp.bar_sayimi()

    def _paket(self, i: int, yon: int) -> dict:
        s, t = self.s, self.tick
        if yon == 1:
            return {"yon": 1, "giris": s.h[i] + t, "stop": s.l[i] - t}
        return {"yon": -1, "giris": s.l[i] - t, "stop": s.h[i] + t}

    def donus(self, i: int, boga: bool) -> dict | None:
        """Standart paket; kalite 2.2'den. 0 kaliteli dönüş barı da bir
        dönüş barıdır (asgari koşul), K süzgeci mekanikte uygulanır."""
        if i < 1 or not self.fp.donus_bari(i, boga):
            return None
        return dict(self._paket(i, 1 if boga else -1), kalite=self.fp.kalite(i, boga), kurulum="donus")

    def ikinci_giris(self, i: int) -> dict | None:
        """H2 (always-in long) ya da L2 (short) barı; paket aynı."""
        et = self.sayim[i]
        if et == "H2" and self.ai[i] == 1:
            return dict(self._paket(i, 1), kalite=self.fp.kalite(i, True), kurulum="ikinci")
        if et == "L2" and self.ai[i] == -1:
            return dict(self._paket(i, -1), kalite=self.fp.kalite(i, False), kurulum="ikinci")
        return None

    def kirilim(self, i: int) -> dict | None:
        """Kırılım modu: iki taraflı stop, dolmayan taraf koruyucu stop."""
        km = self.fp.kirilim_modu(i)
        if km is None:
            return None
        return {"cift": True, "alis": km["alis_stop"] + self.tick, "satis": km["satis_stop"] - self.tick,
                "kalip": km["kalip"], "kurulum": "kirilim"}

    def bant_kenari(self, i: int) -> dict | None:
        """Bölüm 4.5 · 4.6 · 4.12 — BANT içinde uçtan işlem, üç mekanik şart.

        Ders bantta ne "hiç işlem" ne "körlemesine fade" der; kararı bandın
        YÜKSEKLİĞİNE, fiyatın bant içindeki KONUMUNA ve emir tipine bağlar:
          · KONUM (4.6 s.2132–2138): alım yalnız bandın ALT üçte birinde,
            satım yalnız ÜST üçte birinde; ortada emir yok (4.1 s.1943).
            Bant = son `pencere` (70) barın yüksek/düşüğü.
          · YÜKSEKLİK (4.12 s.2533–2541): bant < 3 × stop ise DAR banttır ve
            stop emirle giriş yoktur; ≥ 3 × stop ise uçlarda çalışılır.
          · SIĞMA (4.6 s.2123): "bant 10 tick ise dibin 6 tick üstünden alım
            yok" — 1R hedef bandın içinde kalmalı: giriş + risk ≤ tavan.
          · HO SÜZGECİ (4.3 s.1992–2004): penceredeki kapanışların yarıdan
            fazlası ortalamanın ALTINDAYSA alım yok, üstündeyse satım yok.
          · YÖN SÜZGECİ SERBEST (7.5 · 4.3): son 10 barın 7'si ortalamanın
            bir yanındaysa bu bir bant değil trenddir — dersin rejim için
            verdiği tek mekanik vekil. Ölçüldü (15.09.2026, BIST 100 1 sa):
            bu şart olmadan yükselen bir trendde fiyat hep bandın üst üçte
            birindeydi ve pencerenin dokuz barı "bant kenarı" işareti
            taşıyordu — trendde fade paketi.
        Sinyal barı dönüş barıdır; ders bant uçlarında gövde rengini süzgeç
        saymaz (4.6 s.2154), o yüzden kalite şartı yok. Paket standart
        (uç ± tick). Alt panelin BANT hükmünü bu fonksiyon SORMAZ — ayar
        katmanı sorar; burada konum, yükseklik, sığma, HO ve yön süzgeci."""
        w = int(self.rp.pencere)
        if i + 1 < w or self.fp.ema[i] is None or self.fp.yon_filtresi(i) != "serbest":
            return None
        s, t = self.s, self.tick
        pen = range(i - w + 1, i + 1)
        tavan, taban = max(s.h[j] for j in pen), min(s.l[j] for j in pen)
        yuk = tavan - taban
        if yuk <= 0:
            return None
        konum = (s.c[i] - taban) / yuk
        ema_alti = sum(1 for j in pen if self.fp.ema[j] is not None and s.c[j] < self.fp.ema[j]) / w
        if konum <= 1 / 3 and self.fp.donus_bari(i, True) and ema_alti <= 0.5:
            e = self._paket(i, 1)
            risk = e["giris"] - e["stop"]
            if risk > 0 and yuk >= 3 * risk and e["giris"] + risk <= tavan:
                return dict(e, kalite=self.fp.kalite(i, True), kurulum="bant", konum=round(konum, 3),
                            bant_yukseklik=yuk)
        if konum >= 2 / 3 and self.fp.donus_bari(i, False) and (1 - ema_alti) <= 0.5:
            e = self._paket(i, -1)
            risk = e["stop"] - e["giris"]
            if risk > 0 and yuk >= 3 * risk and e["giris"] - risk >= taban:
                return dict(e, kalite=self.fp.kalite(i, False), kurulum="bant", konum=round(konum, 3),
                            bant_yukseklik=yuk)
        return None

    def basarisiz_donus(self, i: int) -> dict | None:
        """Always-in long iken AYI dönüş barı: üstüne alış stop, altına
        koruyucu stop; dolum ancak ayı tarafı ÖNCE tetiklenmediyse geçerli
        (mekanik bunu sorar: aynı barda iki uç da geçildiyse emir sayılmaz)."""
        if i < 1 or self.ai[i] == 0:
            return None
        if self.ai[i] == 1 and self.fp.donus_bari(i, False):
            return dict(self._paket(i, 1), kalite=self.fp.kalite(i, False), kurulum="basarisiz", sart_ters_uc=True)
        if self.ai[i] == -1 and self.fp.donus_bari(i, True):
            return dict(self._paket(i, -1), kalite=self.fp.kalite(i, True), kurulum="basarisiz", sart_ters_uc=True)
        return None


def tick_tahmini(s: Seri) -> float:
    """Serinin fiyat adımı: gözlenen en küçük pozitif fark, 10'un kuvvetine
    yuvarlanır (aşağı). Kaynak tick ilan etmiyorsa yedek; ilan ediyorsa o
    kullanılmalı. Yahoo 5 dk EUR/USD 5 ondalık → 0,00001."""
    import math
    fiyatlar = sorted(set(s.o + s.h + s.l + s.c))
    farklar = [b - a for a, b in zip(fiyatlar, fiyatlar[1:]) if b - a > 1e-12]
    if not farklar:
        raise ValueError("tick tahmin edilemedi: seride tek fiyat var")
    en_kucuk = min(farklar)
    return 10.0 ** math.floor(math.log10(en_kucuk) + 1e-9)


# ═══════════════════════════════════════════════════════════════════════════
#  KAPILAR — kural SÖZ olarak değil ÖLÇÜM olarak sınanır
# ═══════════════════════════════════════════════════════════════════════════
def gelecege_bakma_sinamasi(s: Seri, adim: int = 1, bas: int = 120) -> list[str]:
    """SERİYİ `i`'DE KIRP; `i`'deki her çıktı BİREBİR AYNI kalmalı.

    Bir indikatörün en sinsi kusuru geriye dönük mükemmel görünmesidir ve
    sebebi neredeyse her zaman aynıdır: bir hesap, o barda henüz var olmayan
    bir bilgiyi kullanır. Bu, "kullanmıyoruz" diye YAZILACAK bir şey değil,
    koşturularak ÖLÇÜLECEK bir şeydir. Sınama tam da onu yapar.

    Adım HER BAR (1) olmalı. Bir sızıntı yalnız BAĞLADIĞI barda görünür ve
    o barlar seyrek olabilir; yedi barda bir örnekleyen bir sürüm, bilerek
    enjekte edilmiş gerçek bir sızıntıyı KAÇIRDI. Bir kapının örneklemi de
    kapının parçasıdır."""
    hata: list[str] = []
    tick = tick_tahmini(s)
    fp_tam, rp_tam, ku_tam = FiyatPaneli(s), RejimPanosu(s), Kurulumlar(s, tick)
    sayim_tam = fp_tam.bar_sayimi()
    for i in range(bas, len(s), adim):
        kirp = s.kirp(i + 1)
        tam = fp_tam.durum(i)
        kirpik = FiyatPaneli(kirp).durum(i)
        if tam != kirpik:
            hata.append(f"fiyat paneli i={i}: tam {tam} ≠ kırpık {kirpik}")
        a = rp_tam.olcu(i)
        b = RejimPanosu(kirp).olcu(i)
        if a != b:
            hata.append(f"rejim panosu i={i}: tam {a} ≠ kırpık {b}")
        # Göreli eşik, dersin sayımı ve emir paketleri de aynı kapıdan geçer:
        # kapsam bir listeden değil, okura giden her çıktıdan türer.
        rp_k = RejimPanosu(kirp)
        if rp_tam.olcu_goreli(i) != rp_k.olcu_goreli(i):
            hata.append(f"göreli rejim i={i}: tam ≠ kırpık")
        if sayim_tam[i] != FiyatPaneli(kirp).bar_sayimi()[i]:
            hata.append(f"dersin sayımı i={i}: tam {sayim_tam[i]} ≠ kırpık")
        ku_k = Kurulumlar(kirp, tick)
        for ad, f_t, f_k in (("donus", lambda j: (ku_tam.donus(j, True), ku_tam.donus(j, False)),
                              lambda j: (ku_k.donus(j, True), ku_k.donus(j, False))),
                             ("ikinci", ku_tam.ikinci_giris, ku_k.ikinci_giris),
                             ("kirilim", ku_tam.kirilim, ku_k.kirilim),
                             ("basarisiz", ku_tam.basarisiz_donus, ku_k.basarisiz_donus),
                             ("bant", ku_tam.bant_kenari, ku_k.bant_kenari)):
            if f_t(i) != f_k(i):
                hata.append(f"kurulum '{ad}' i={i}: tam {f_t(i)} ≠ kırpık {f_k(i)}")
    return hata


def _sentetik(n: int, tohum: int = 7) -> Seri:
    """Sınama için rastgele ama TEKRARLANABİLİR barlar. Ağa çıkmaz."""
    r = random.Random(tohum)
    o = h = l = c = 100.0
    O, H, L, C = [], [], [], []
    for _ in range(n):
        o = c
        govde = r.gauss(0, 0.6)
        c = o + govde
        ust, alt = abs(r.gauss(0, 0.25)), abs(r.gauss(0, 0.25))
        h, l = max(o, c) + ust, min(o, c) - alt
        O.append(round(o, 4)); H.append(round(h, 4)); L.append(round(l, 4)); C.append(round(c, 4))
    return Seri(O, H, L, C)


def kendini_sina() -> list[str]:
    """Kuralın İLAN ETTİĞİ hâllere koşulur — sezgiye değil, kurala."""
    hata: list[str] = []

    def seri(b):
        return Seri([x[0] for x in b], [x[1] for x in b], [x[2] for x in b], [x[3] for x in b])

    # ① Always-in: iki güçlü boğa barı + takip barının boğa kapanışı → long.
    b = [(10, 10.4, 9.6, 10.0), (10, 10.4, 9.6, 10.0),
         (10.0, 11.0, 9.95, 10.95), (11.0, 12.0, 10.95, 11.95),
         (11.95, 12.2, 11.9, 12.10)]
    yon, donus, _ = FiyatPaneli(seri(b)).always_in()
    if donus != [4] or yon[4] != 1:
        hata.append(f"① long dönüşü 4. barda beklenirdi; dönüş={donus} yön={yon}")

    # ② Takip barının ölçütü bir YOKLUKTUR: ayı kapanışlı takip → dönüş YOK.
    yon2, donus2, onaysiz2 = FiyatPaneli(seri(b[:4] + [(12.10, 12.2, 11.5, 11.60)])).always_in()
    if donus2:
        hata.append(f"② ayı kapanışlı takip barı dönüş üretmemeliydi; {donus2}")
    if onaysiz2 != [4]:
        hata.append(f"② onaylanmayan dizi 4. barda sayılmalıydı; {onaysiz2}")

    # ③ Tek güçlü trend barı yetmez (ders: bağlamla yeterli olabilir — ölçülemez).
    b3 = [(10, 10.4, 9.6, 10.0)] * 3 + [(10.0, 11.0, 9.95, 10.95), (10.95, 11.1, 10.9, 11.0)]
    if FiyatPaneli(seri(b3)).always_in()[1]:
        hata.append("③ tek güçlü trend barı dönüş üretmemeliydi")

    # ③b BOŞ PENCERE: Pine `na` döner, karşılaştırma `false`'tur. Ölçüt
    #     ölçüm katmanının giriş noktasını İLK BARDAN çağırır — üretim yolu
    #     ısınma payıyla koştuğu için bu hâl orada hiç görünmez, ve
    #     görünmediği yer geçen sınavla aynı görünür.
    #     Ölçüt ÇÖKMEZ, BİLDİRİR: arıza enjekte edildiğinde (nan kaldırılınca)
    #     çıplak çağrı ValueError fırlatıyor ve ekrandaki teşhis sınamanın
    #     kendi hatası gibi görünüyordu.
    try:
        if not math.isnan(en_dusuk([1.0, 2.0], 0, 5)):
            hata.append("③b boş pencere nan vermeliydi (Pine'ın na sözleşmesi)")
        fp0 = FiyatPaneli(seri(b))
        for j in range(len(b)):
            for yonu in (True, False):
                if fp0.donus_bari(j, yonu):
                    fp0.kalite(j, yonu)
    except Exception as e:                                  # noqa: BLE001
        hata.append(f"③b ilk barlarda ölçüm çöküyor: {type(e).__name__}: {e}")

    # ④ Canlı kalite tavanı DÖRTTÜR; nitelik sayısı da dört olmalı.
    fp = FiyatPaneli(seri(b))
    if len(fp.nitelikler(3, True)) != 4:
        hata.append(f"④ nitelik sayısı 4 olmalı, {len(fp.nitelikler(3, True))} bulundu")
    if max(fp.kalite(i, True) for i in range(1, len(b))) > 4:
        hata.append("④ canlı kalite 4'ü aşamaz")

    # ⑤ Örtüşme: eşiği aşan bir bar n3 niteliğini KAYBEDER.
    b5 = [(10, 11, 9, 10.5), (10.2, 10.8, 9.2, 10.4)]
    o5 = FiyatPaneli(seri(b5)).ortusme(1)
    if not 0.79 <= o5 <= 0.81:
        hata.append(f"⑤ örtüşme 0,80 beklenirdi; {o5:.3f}")
    if FiyatPaneli(seri(b5)).nitelikler(1, True)["n3"]:
        hata.append("⑤ eşiği aşan örtüşmede n3 tutmamalıydı")

    # ⑥ Rejim: yatay-örtüşen-doji pencere BANT, tek yönlü pencere trend.
    w = int(SABIT_RP["pencere"]) + int(SABIT_RP["maUzunluk"]) + 5
    rb = RejimPanosu(seri([(10.0, 10.5, 9.5, 10.0)] * w)).olcu(w - 1)
    if rb is None or rb["rejim"] != "BANT":
        hata.append(f"⑥ yatay pencere BANT olmalıydı; {rb and rb['rejim']}")
    rt = RejimPanosu(seri([(10.0 + i, 10.9 + i, 9.95 + i, 10.85 + i) for i in range(w)])).olcu(w - 1)
    if rt is None or rt["rejim"] != "trend":
        hata.append(f"⑥ tek yönlü pencere trend olmalıydı; {rt and rt['rejim']}")

    # ⑧ DERSİN SAYIMI: iki sayım arasında "aşamayan" bir bar gerekir. Eski
    #    sayaç ardışık iki yükselen barı H1·H2 diye etiketler; ders etmez.
    b8 = [(10, 10.4, 9.6, 10.0)] * 3 + [
        (10.0, 11.0, 9.95, 10.95), (11.0, 12.0, 10.95, 11.95), (11.95, 12.2, 11.9, 12.10),   # → always-in long (5)
        (12.10, 12.5, 12.0, 12.40),    # 6: yeni zirve → sayım sıfır
        (12.40, 12.3, 12.0, 12.10),    # 7: geri çekilme (zirve aşılmadı)
        (12.10, 12.4, 12.05, 12.35),   # 8: H1
        (12.35, 12.45, 12.3, 12.42),   # 9: yine aşıyor — ders: etiket YOK · eski sayaç: H2
        (12.42, 12.4, 12.2, 12.25),    # 10: geri çekilme sürüyor
        (12.25, 12.48, 12.2, 12.45),   # 11: H2
    ]
    fp8 = FiyatPaneli(seri(b8))
    ders, eski = fp8.bar_sayimi(), fp8.bar_sayimi_eski()
    if ders[8] != "H1" or ders[9] != "" or ders[11] != "H2":
        hata.append(f"⑧ dersin sayımı H1(8) · —(9) · H2(11) beklerdi; {ders[6:]}")
    if eski[9] != "H2":
        hata.append(f"⑧ eski sayaç 9. barı H2 saymalıydı (farkın kendisi ölçülüyor); {eski[6:]}")

    # ⑨ GÖRELİ EŞİK: sıra = önceki `tarihce` değerin kaçı ≤ bugünkü (Pine
    #    percentrank sözleşmesi, bugünkü bar hariç, payda tarihçe); ≤-tipi
    #    ölçüde kaçı ≥. Ölçü değerleri doğrudan verilir.
    n_t = int(SABIT_RP["tarihce"])
    rp9 = RejimPanosu(_sentetik(n_t + 120, tohum=11))
    sabit_bar = {"barbwire": {"var": False, "oran": 0.0}, "isaret": {}, "n": 0, "rejim": "ara"}
    tarih = {j: dict(sabit_bar, ortusme_oran=j / 1000, doji_oran=0.1, kesisme=5, net_aralik=j / 1000, azami_dizi=3)
             for j in range(n_t)}
    for bugun_ort, bugun_net, bekl_ort, bekl_net in ((0.15, 0.10, False, True), (0.20, 0.20, True, False)):
        rp9._ham_onbellek = dict(tarih)
        rp9._ham_onbellek[n_t] = dict(sabit_bar, ortusme_oran=bugun_ort, doji_oran=0.1, kesisme=5,
                                      net_aralik=bugun_net, azami_dizi=3)
        g = rp9.olcu_goreli(n_t)
        if g is None or g["isaret"]["ortusme"] != bekl_ort or g["isaret"]["net"] != bekl_net:
            hata.append(f"⑨ göreli sıra: örtüşme {bugun_ort} → {bekl_ort}, net {bugun_net} → {bekl_net} beklerdi; {g and g['sira']}")
    rp9._ham_onbellek = {}
    if RejimPanosu(_sentetik(n_t + 60)).olcu_goreli(n_t - 1) is not None:
        hata.append("⑨ tarihçe dolmadan göreli hüküm verilmemeli")

    # ⑩ PAKETLER: tick'li giriş/stop; bant kenarı konum ve sığma şartları.
    ku = Kurulumlar(seri([(10, 10.4, 9.6, 10.0), (10.0, 10.5, 10.0, 10.4)]), 0.01)
    d = ku.donus(1, True)
    if not d or abs(d["giris"] - 10.51) > 1e-9 or abs(d["stop"] - 9.99) > 1e-9:
        hata.append(f"⑩ dönüş paketi giriş 10,51 · stop 9,99 beklerdi; {d}")
    kb = [(11.0, 12.0, 10.0, 11.5)] * 72 + [(10.1, 10.3, 10.0, 10.25)]           # dipte boğa dönüş barı
    bk = Kurulumlar(seri(kb), 0.01).bant_kenari(len(kb) - 1)
    if not bk or bk["yon"] != 1 or abs(bk["giris"] - 10.31) > 1e-9 or bk["konum"] > 1 / 3:
        hata.append(f"⑩ bant kenarı dipte alış paketi beklerdi; {bk}")
    ko = Kurulumlar(seri(kb[:-1] + [(11.0, 11.2, 10.9, 11.15)]), 0.01).bant_kenari(len(kb) - 1)
    if ko is not None:
        hata.append(f"⑩ bandın ortasında emir olmamalı; {ko}")
    dar = Kurulumlar(seri(kb[:-1] + [(10.1, 10.9, 10.0, 10.85)]), 0.01).bant_kenari(len(kb) - 1)   # risk 0,92 > bant/3
    if dar is not None:
        hata.append(f"⑩ bant < 3 × stop iken emir olmamalı; {dar}")
    try:
        Kurulumlar(seri(kb), 0.0)
        hata.append("⑩ tick'siz Kurulumlar hata vermeliydi")
    except ValueError:
        pass

    # ⑦ GELECEĞE BAKMA: seri kırpılınca geçmiş çıktılar değişmemeli — göreli
    #    eşik, dersin sayımı ve bütün paketler dahil.
    hata += gelecege_bakma_sinamasi(_sentetik(400))

    return hata


# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    hata = kendini_sina()
    if hata:
        print("SINAMA DÜŞTÜ:", file=sys.stderr)
        for h in hata:
            print("  ✗", h, file=sys.stderr)
        raise SystemExit(1)
    print("sınama · 10 madde GEÇTİ (geleceğe bakma dahil: göreli eşik, dersin sayımı, paketler)")

    s = _sentetik(400)
    fp, rp = FiyatPaneli(s), RejimPanosu(s)
    i = len(s) - 1
    print(f"\nson barın durumu (sentetik seri, {len(s)} bar):")
    for k, v in fp.durum(i).items():
        print(f"  {k:14s} {v}")
    o = rp.olcu(i)
    if o:
        print(f"\nrejim panosu: {o['n']}/5 → {o['rejim']}")
        for ad, tuttu in o["isaret"].items():
            print(f"  {ad:10s} {'✓' if tuttu else '—'}")
