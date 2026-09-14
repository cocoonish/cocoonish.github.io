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


def pine_ile_karsilastir(pine_fh: Path, pine_rp: Path) -> list[str]:
    """İki uygulamanın eşikleri AYRIŞMIŞ mı. Boş liste = ayrışma yok.

    Aynı kuralın iki uygulaması bir gün sessizce ayrışır; ayrışma ancak
    sorulursa görünür. Burada soruluyor."""
    ayrik: list[str] = []
    for ad, yol, beyan in (("fiyat paneli", pine_fh, SABIT_FH), ("rejim panosu", pine_rp, SABIT_RP)):
        p = pine_sabitleri(yol)
        for k, v in beyan.items():
            if k not in p:
                ayrik.append(f"{ad}: '{k}' Python'da var, Pine'da YOK")
            elif abs(float(p[k]) - float(v)) > 1e-9:
                ayrik.append(f"{ad}: '{k}' Pine {p[k]} ≠ Python {v}")
        for k in p:
            if k not in beyan and k not in ("barBoya", "aiZemin", "sinyalGoster",
                                            "sayimGoster", "maGoster", "asgariKalite"):
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
    """`ta.highest(x[1], n)` — pencere i−1'de BİTER, şimdiki barı içermez."""
    return max(x[max(0, i - n): i])


def en_dusuk(x: list[float], i: int, n: int) -> float:
    """`ta.lowest(x[1], n)` — aynı sınır."""
    return min(x[max(0, i - n): i])


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

    def __init__(self, s: Seri, sabit: dict | None = None):
        self.s = s
        self.k = dict(SABIT_FH, **(sabit or {}))
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
    def bar_sayimi(self) -> list[str]:
        """H1–H4 / L1–L4. Pine'daki `var int hSayac`/`lSayac` karşılığı.

        Rejim filtresi dersten: boğa trendinde `low` sayılmaz, ayıda `high`.
        DIŞARIDA KALAN: ders 'high 1 ile high 2 arasında en az küçücük bir
        trend çizgisi kırılımı olmalı' der; trend çizgisi çizmek bir yorum
        işidir. Sayaç onu SORMAZ — bu yüzden sayaç bir kurulum değil sayaçtır."""
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
            "gap_bar": gap[i],
            "bar_sayimi": self.bar_sayimi()[i] or "—",
            "bar_sinifi": self.sinif(i),
            "ortusme": round(self.ortusme(i), 6),
            "ic_bar": self.ic_bar(i),
            "dis_bar": self.dis_bar(i),
            "donus_boga": self.donus_bari(i, True),
            "donus_ayi": self.donus_bari(i, False),
            "nitelik_boga": self.nitelikler(i, True),
            "nitelik_ayi": self.nitelikler(i, False),
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
            "isaret": isaret, "n": n,
            "rejim": "BANT" if n >= 4 else "trend" if n <= 1 else "ara",
        }


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
    for i in range(bas, len(s), adim):
        tam = FiyatPaneli(s).durum(i)
        kirpik = FiyatPaneli(s.kirp(i + 1)).durum(i)
        if tam != kirpik:
            hata.append(f"fiyat paneli i={i}: tam {tam} ≠ kırpık {kirpik}")
        a = RejimPanosu(s).olcu(i)
        b = RejimPanosu(s.kirp(i + 1)).olcu(i)
        if a != b:
            hata.append(f"rejim panosu i={i}: tam {a} ≠ kırpık {b}")
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

    # ⑦ GELECEĞE BAKMA: seri kırpılınca geçmiş çıktılar değişmemeli.
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
    print("sınama · 7 madde GEÇTİ (geleceğe bakma dahil)")

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
