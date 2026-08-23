#!/usr/bin/env python3
"""Plotly HTML çıktılarına site ev stilini uygular (v3).

Ham Plotly HTML'leri iframe içinde dağınık görünür (başlık/lejant çakışması,
sabit boyut, uyumsuz eksen renkleri). Bu araç HTML'in sonuna bir "restyle"
script'i enjekte eder: sayfa yüklenince Plotly.relayout ile ev stili uygulanır.
Kaynak verinin/formüllerin olduğu kısma dokunulmaz. İşlem idempotenttir ve
sürüm yükseltmelerinde eski blok söküp yenisi takılır.

Kullanım:
  python3 site/tools/plotly_stil.py --hepsi     # projeler + dersler altındaki tüm HTML'ler
  python3 site/tools/plotly_stil.py --projeler  # yalnız proje grafikleri
  python3 site/tools/plotly_stil.py --dersler   # yalnız ders grafikleri
  python3 site/tools/plotly_stil.py dosya.html …
"""

import re
import sys
from pathlib import Path

ISARET = "<!-- tto-ev-stili -->"

EV_STILI = """
<!-- tto-ev-stili -->
<style>
  /* Çok panelli figürlerde (3+ sütun) dar iframe'de sağdaki etiket kutuları
     kırpılıyordu. Çözüm: grafiğe alt sınır genişlik verip taşmayı YATAY KAYDIRMAYA
     çevirmek — kırpmak yerine kaydırmak. Sınır aşağıdaki script'te panel sayısına
     göre belirlenir (tek panelli grafikler etkilenmez, %100 kalır). */
  html, body { margin: 0; padding: 0; height: 100%; background: #ffffff; overflow-x: auto; }
  /* Yükseklik: normalde iframe'i doldurur (100vh). Ama figürün TASARIM yüksekliği
     viewport'tan büyükse (alt alta dizilmiş çok panelli grafikler, 1000-2300 px)
     100vh onu EZİYORDU — "Tam ekran" bağlantısıyla açıldığında altı üstü sıkışık
     bir görüntü çıkıyordu. Script aşağıda gd.layout.height'ı okuyup gerekirse
     .tto-uzun ile sabit yüksekliğe geçiriyor; sayfa dikey kayar. */
  .plotly-graph-div { width: 100% !important; height: 100vh !important; }
  body.tto-uzun .plotly-graph-div { height: var(--tto-yukseklik) !important; }
  body.tto-genis .plotly-graph-div { min-width: var(--tto-min-genislik, 100%); }
  .modebar { opacity: 0.25; transition: opacity .2s; }
  .modebar:hover { opacity: 1; }
  .modebar-btn--logomark, .modebar-btn[data-title="Produced with Plotly.js"] { display: none !important; }
</style>
<script>
(function () {
  function genislikSiniri(gd) {
    // Kaç sütunlu subplot? xaxis/xaxis2/... domainlerinin sol kenarlarının sayısı.
    var sol = {};
    Object.keys(gd.layout).forEach(function (k) {
      if (/^xaxis\d*$/.test(k) && gd.layout[k] && gd.layout[k].domain) {
        sol[gd.layout[k].domain[0].toFixed(3)] = 1;
      }
    });
    var sutun = Math.max(1, Object.keys(sol).length);
    // Toplam panel sayısı: kaç ayrı x ekseni var (2x2 ızgara = 4 panel, 2 sütun).
    var panel = Object.keys(gd.layout).filter(function (k) {
      return /^xaxis\d*$/.test(k) && gd.layout[k] && gd.layout[k].domain;
    }).length;
    if (sutun >= 4) return 1220;
    if (sutun === 3) return 1020;
    if (sutun >= 2 && panel >= 4) return 1000;  // 2x2 ızgara: panel başına ~480px, kutular sığar
    return 0;                     // tek sütunlu (alt alta) ya da çift panelli: %100 genişlik yeter
  }

  function uygula() {
    var gd = document.querySelector('.plotly-graph-div');
    if (!gd || !window.Plotly || !gd.layout) { setTimeout(uygula, 120); return; }
    // Tasarım yüksekliği viewport'u aşıyorsa figürü ezme, sayfayı kaydır.
    var tasarimY = (gd.layout && gd.layout.height) || 0;
    if (tasarimY && tasarimY > window.innerHeight + 20) {
      document.body.classList.add('tto-uzun');
      document.body.style.setProperty('--tto-yukseklik', tasarimY + 'px');
    }
    // Alt başlıklı (title'da <br><sup>…) figürlerde İLK satırın panel başlığı
    // (y≈1) başlığın altına giriyordu: üst marj iki satırlık başlık + panel
    // başlığı için yetmiyor. Gerekirse marj büyütülür (yalnız çok satırlı
    // subplot figürlerinde; tek panelli grafiklerde panel başlığı yoktur).
    var minG = genislikSiniri(gd);
    if (minG) {
      document.body.classList.add('tto-genis');
      document.body.style.setProperty('--tto-min-genislik', minG + 'px');
    }
    var mevcut = gd.layout.title && gd.layout.title.text ? gd.layout.title.text : null;
    var guncelle = {
      autosize: true,
      'font.family': "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
      'font.size': 12.5,
      'font.color': '#211b12',
      paper_bgcolor: '#ffffff',
      plot_bgcolor: '#ffffff',
      'title.x': 0.01,
      'title.xanchor': 'left',
      'title.font.size': 15,
      'title.font.color': '#211b12',
      // lejant her zaman grafiğin ALTINDA — başlıkla çakışma imkânsız
      'legend.orientation': 'h',
      'legend.yanchor': 'top',
      'legend.y': -0.1,
      'legend.xanchor': 'left',
      'legend.x': 0,
      'legend.font.size': 11,
      'legend.bgcolor': 'rgba(255,255,255,0)',
      'margin.t': mevcut ? 92 : 36,
      'margin.r': 64,
      'margin.b': 110,
      'margin.l': 64,
      'hoverlabel.bgcolor': '#211b12',
      'hoverlabel.bordercolor': '#211b12',
      'hoverlabel.font.color': '#f5f0e6',
      'hoverlabel.font.size': 12
    };
    // otomatik renk ataması alan izler için ev paleti (açıkça renklendirilmiş
    // izler etkilenmez)
    guncelle['colorway'] = ['#1d5c5c', '#8e1f2f', '#9a7327', '#2f4b7c',
                           '#665191', '#a05195', '#d45087', '#7a9e7e'];
    // tüm eksenlere (subplot dahil) uyumlu ızgara/kenar/yazı stili
    Object.keys(gd.layout).forEach(function (k) {
      if (/^[xy]axis\\d*$/.test(k)) {
        guncelle[k + '.gridcolor'] = '#efe9dc';
        guncelle[k + '.zerolinecolor'] = '#cfc4ab';
        guncelle[k + '.linecolor'] = '#d8cfba';
        guncelle[k + '.tickfont.size'] = 11;
        guncelle[k + '.tickfont.color'] = '#6b6355';
        guncelle[k + '.title.font.size'] = 12;
        guncelle[k + '.title.font.color'] = '#211b12';
        guncelle[k + '.automargin'] = true;
      }
    });
    // kalabalık kategori eksenlerinde tik seyreltme — her etiketi basmak
    // grafiği okunmaz yapar; ~14 tikte tut, hafif eğ
    var fl = gd._fullLayout || {};
    Object.keys(fl).forEach(function (k) {
      if (/^xaxis\\d*$/.test(k) && fl[k] && fl[k]._categories &&
          fl[k]._categories.length > 24) {
        var ad = k.replace('axis', 'axis'); // layout anahtarı aynı
        guncelle[ad + '.tickmode'] = 'auto';
        guncelle[ad + '.nticks'] = 14;
        guncelle[ad + '.tickangle'] = -40;
      }
    });
    var bas = (gd.layout.title && gd.layout.title.text) || '';
    var ustBaslik = (gd.layout.annotations || []).some(function (a) {
      return a.yanchor === 'bottom' && a.yref === 'paper' && a.y >= 0.98;
    });
    var altSatir = (bas.match(/<br>/g) || []).length;
    var gerekenT = 92 + 26 * altSatir + (ustBaslik ? 26 : 0);
    if (ustBaslik && altSatir && (gd.layout.margin || {}).t < gerekenT) {
      guncelle['margin.t'] = gerekenT;
    }
    Plotly.relayout(gd, guncelle);
    window.addEventListener('resize', function () { Plotly.Plots.resize(gd); });
    Plotly.Plots.resize(gd);
  }
  if (document.readyState === 'complete') uygula();
  else window.addEventListener('load', uygula);
})();
</script>
"""


BANNER = re.compile(r"plotly\.js v(\d+\.\d+\.\d+)")


def cdnlestir(metin: str) -> tuple[str, bool]:
    """Gömülü plotly.js bloğunu (>1MB script) sürümü korunmuş CDN etiketiyle değiştirir.

    DİKKAT — blok yalnız plotly.js BANNER'ı ("plotly.js vX.Y.Z") taşıyorsa değiştirilir.
    Eski koşul "1 MB'tan büyük + içinde 'Plotly' geçiyor" idi; uzun günlük serilerle
    üretilen figürlerde `Plotly.newPlot(...)` VERİ bloğu da 1 MB'ı aşabiliyor ve
    grafiğin bütün verisi sessizce siliniyordu (dosya ~7 KB'a düşüyor, sayfa boş
    çıkıyor). Banner koşulu bu sınıfı kapatır: gömülü kütüphane bundle'larının
    hepsinde banner vardır, veri bloklarında yoktur."""
    en_buyuk = None
    for m in re.finditer(r"<script[^>]*>", metin):
        kapanis = metin.find("</script>", m.end())
        if kapanis < 0:
            continue
        bas = metin[m.end():m.end() + 200_000]
        if kapanis - m.end() > 1_000_000 and BANNER.search(bas):
            en_buyuk = (m.start(), kapanis + len("</script>"))
            break
    if not en_buyuk:
        return metin, False
    govde = metin[en_buyuk[0]:en_buyuk[1]]
    # plotly.js'in KENDİ sürümü banner'dadır ("plotly.js vX.Y.Z");
    # version:"..." deseni Python paket sürümünü yakalayabilir — kullanma.
    surum_m = BANNER.search(govde)
    surum = surum_m.group(1) if surum_m else "3.3.0"
    etiket = f'<script src="https://cdn.plot.ly/plotly-{surum}.min.js" charset="utf-8"></script>'
    return metin[:en_buyuk[0]] + etiket + metin[en_buyuk[1]:], True


def isle(yol: Path) -> str:
    metin = yol.read_text(encoding="utf-8", errors="ignore")
    if "plotly" not in metin.lower():
        return "atlandı (plotly değil)"
    metin, kucultuldu = cdnlestir(metin)
    yeni_mi = ISARET not in metin
    # eski enjeksiyon bloğunu sök (işaretten bloğun son </script>'ine kadar)
    if not yeni_mi:
        metin = re.sub(
            re.escape(ISARET) + r"[\s\S]*?</script>\s*", "", metin, count=1
        )
    if "</body>" in metin:
        metin = metin.replace("</body>", EV_STILI + "\n</body>", 1)
    else:
        metin += EV_STILI
    yol.write_text(metin, encoding="utf-8")
    ek = " + cdn'e küçültüldü" if kucultuldu else ""
    return ("stillendi" if yeni_mi else "güncellendi (v3)") + ek


def main():
    argv = sys.argv[1:]
    # --hepsi ESKİDEN yalnız public/projeler altını tarıyordu; ders grafikleri
    # public/arastirma altında olduğu için sessizce kapsam dışında kalıyordu.
    # Brooks dersinin 94 figürü bu yüzden ev stiline girmemişti (yol elle verilerek
    # kurtarıldı). Artık iki kök de taranır.
    kokler = [Path(__file__).resolve().parents[1] / "public" / "projeler",
              Path(__file__).resolve().parents[1] / "public" / "arastirma"]
    if not argv or argv[0] == "--hepsi":
        dosyalar = sorted(y for k in kokler if k.exists() for y in k.rglob("*.html"))
    elif argv[0] == "--projeler":
        dosyalar = sorted(kokler[0].rglob("*.html"))
    elif argv[0] == "--dersler":
        dosyalar = sorted(kokler[1].rglob("*.html"))
    else:
        dosyalar = [Path(a) for a in argv]
    for d in dosyalar:
        print(f"{d.name:36s} {isle(d)}")


if __name__ == "__main__":
    main()
