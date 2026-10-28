/* ─────────────────────────────────────────────────────────────
   Grafikler bölümü — seri ve hazır grafik sayfasının TARAYICI tarafı.

   İki sayfa (tek seri · hazır grafik) aynı denetimleri taşır: dönem,
   gösterim (düzey · yıllık · aylık), tablo, CSV. Tek seri sayfasında ayrıca
   aynı birim ve türden bir seriyle kıyas vardır. İki kopya bir gün iki ayrı
   CSV ya da iki ayrı dönüşüm yazardı; davranış burada tek yerde durur.

   Sayfa verisi `<script type="application/json" id="seri-veri">` içinde
   gelir; bütün seriler AYNI birim ve AYNI türdedir (tek eksen, tek dönüşüm
   birimi — kataloğun ve sayfa sınavı 30'un sözleşmesi).

   TEK İSTİSNA kıyastır ve kuralı bozmaz: seviye bir seri BAŞKA birimdeki bir
   seviyeyle kıyaslanabilir, ama yalnız birimsiz bir gösterimde (yüzde değişim
   ya da 100'e endeks). Böyle bir kıyas seçildiğinde "Düzey" düğmesi kapanır;
   iki birim hiçbir anda aynı eksende düzey olarak çizilmez.
   ───────────────────────────────────────────────────────────── */
import { olcuYaz } from './bicim';
import {
  degisimOndalik, donustur, donusumBirimi, endeksle, kes, tarihEtiketi,
  type Donusum, type Frekans, type Seri, type Tur,
} from './grafikDonusum';
import { imRengi, ZamanGrafigi } from './grafikCizim';
import type { Olay } from './grafikOlay';

/* Seri renkleri SIRAYLA atanır ve serinin kendisine bağlıdır (sırasına değil).
   Kâğıt zeminde (#f5f0e6) bütün çiftlerle doğrulandı (dataviz denetleyicisi,
   --pairs all): açıklık bandı ve doygunluk tabanı geçiyor, kontrast ≥ 3:1,
   normal görüşte en yakın çift ΔE 17,1. Renk körlüğünde en yakın çift (hardal ↔
   yeşil) ΔE 7,6 — 6–8 bandı yalnız ikinci kodlamayla meşru, o yüzden üçüncü ve
   sonraki seriler kesikli çizilir ve lejant her zaman görünür. Sitenin
   --claret/--teal çifti renk körlüğünde 7,9'da kalıyordu. */
export const RENK = ['#9e2a3a', '#2a78d6', '#a86f00', '#16875f', '#d1608f'];
export const kesikMi = (i: number) => i >= 2;

export interface SayfaSerisi { id: string; ad: string; frekans: Frekans; t: string[]; v: number[]; hedefYil?: boolean }
export interface SayfaVeri {
  id: string;
  birim: string;
  tur: Tur;
  ondalik: number;
  seriler: SayfaSerisi[];
  kiyaslar?: { id: string; ad: string; frekans: Frekans; birim: string; hedefYil?: boolean }[];
  /** PPK faiz değişiklikleri (lib/grafikOlay); yalnız kararla aynı düzlemdeki serilerde. */
  olaylar?: Olay[];
  /** Olay denetiminin etiketi ("PPK faiz kararları" · "Kapanış tanımı geçişi"). */
  olayAdi?: string;
}

export function grafikSayfasiKur(): void {
  const veri = JSON.parse(document.getElementById('seri-veri')!.textContent!) as SayfaVeri;
  const kap = document.querySelector<HTMLElement>('[data-cizim]')!;
  const ipucu = document.querySelector<HTMLElement>('[data-ipucu]')!;
  const grafik = new ZamanGrafigi(kap, ipucu);
  const durum = document.querySelector<HTMLElement>('[data-durum]')!;
  const lejant = document.querySelector<HTMLElement>('[data-lejant]')!;
  const birimYazi = document.querySelector<HTMLElement>('[data-birim]')!;
  const tabloKap = document.querySelector<HTMLElement>('[data-tablo-kap]')!;
  const tabloGovde = document.querySelector<HTMLElement>('[data-tablo-govde]')!;
  const tabloDugme = document.querySelector<HTMLButtonElement>('[data-tablo]')!;
  const kiyasSec = document.querySelector<HTMLSelectElement>('[data-kiyas]');
  const anaFrekans = veri.seriler[0].frekans;

  let donem: number | null = (() => {
    const b = document.querySelector<HTMLButtonElement>('[data-donem][aria-pressed="true"]');
    return b && b.dataset.donem ? +b.dataset.donem : null;
  })();
  let donusum: Donusum = 'duzey';
  let kiyas: (SayfaSerisi & { birim: string }) | null = null;
  let taban: string | null = null;
  const duzeyDugme = document.querySelector<HTMLButtonElement>('[data-donusum="duzey"]');
  const endeksDugme = document.querySelector<HTMLButtonElement>('[data-donusum="endeks"]');
  const birimFarkli = () => !!kiyas && kiyas.birim !== veri.birim;
  const olaySec = document.querySelector<HTMLInputElement>('[data-olay]');
  const onbellek = new Map<string, Seri>();
  tabloKap.hidden = true;

  // Dönem başı, serilerin EN GEÇ biten gözleminden geriye sayılır: hazır grafikte bir
  // serinin erken bitmesi ötekilerin penceresini kısaltmamalı.
  function basGun(liste: SayfaSerisi[]): string | null {
    if (donem === null) return null;
    const son = liste.reduce((m, s) => (s.t.length && s.t[s.t.length - 1] > m ? s.t[s.t.length - 1] : m), '');
    if (!son) return null;
    const y = +son.slice(0, 4);
    const ay = +son.slice(5, 7) - 1 - donem;
    const gun = Math.min(+son.slice(8, 10), new Date(Date.UTC(y, ay + 1, 0)).getUTCDate());
    return new Date(Date.UTC(y, ay, gun)).toISOString().slice(0, 10);
  }

  function gorunen(): { ad: string; seri: Seri; frekans: Frekans; hedefYil: boolean }[] {
    const liste = kiyas ? [...veri.seriler, kiyas] : veri.seriler;
    const bas = basGun(liste);
    const g = liste.map((s) => ({ ad: s.ad, frekans: s.frekans, seri: kes(donustur(s, veri.tur, s.frekans, donusum, !!s.hedefYil), bas), hedefYil: !!s.hedefYil }));
    taban = null;
    if (donusum !== 'endeks') return g;
    const e = endeksle(g.map((x) => x.seri));
    taban = e.taban;
    return g.map((x, i) => ({ ...x, seri: e.seriler[i] }));
  }

  const ondalik = () => (donusum === 'duzey' ? veri.ondalik : donusum === 'endeks' ? 1 : degisimOndalik(veri.tur, veri.ondalik));
  const birim = () => donusumBirimi(veri.tur, veri.birim, donusum);
  const isaretli = () => donusum === 'yillik' || donusum === 'aylik';
  const yaz = (v: number) => olcuYaz(v, birim(), ondalik(), isaretli());
  const birimEtiketi = () => {
    if (donusum === 'endeks') return taban ? `100 = ${tarihEtiketi(taban, anaFrekans)}` : '100\'e endeksli';
    const b = birim();
    return b === '%' ? 'yüzde' : b;
  };

  function yenile() {
    const g = gorunen();
    const b = birim();
    birimYazi.textContent = birimEtiketi();
    grafik.goster(
      g.map((x, i) => ({ ad: x.ad, seri: x.seri, renk: RENK[i], kesik: kesikMi(i), yilKopuk: x.hedefYil })),
      { birim: b, ondalik: ondalik(), isaretli: isaretli(), frekans: anaFrekans,
        referans: donusum === 'endeks' ? 100 : undefined,
        olaylar: olaySec?.checked ? veri.olaylar : undefined },
    );
    if (duzeyDugme) {
      duzeyDugme.disabled = birimFarkli();
      duzeyDugme.title = birimFarkli() ? 'Farklı birimdeki iki seri düzey olarak aynı eksende çizilmez' : '';
    }
    lejant.replaceChildren();
    lejant.hidden = g.length < 2;
    g.forEach((x, i) => {
      const li = document.createElement('li');
      const im = document.createElement('span');
      im.className = 'lejant-im';
      im.style.background = imRengi(RENK[i], kesikMi(i));
      const ad = document.createElement('span');
      ad.textContent = x.ad;
      li.append(im, ad);
      lejant.append(li);
    });
    const dolu = g.filter((x) => x.seri.t.length);
    if (dolu.length) {
      const ilk = dolu.reduce((m, x) => (x.seri.t[0] < m ? x.seri.t[0] : m), dolu[0].seri.t[0]);
      const son = dolu.reduce((m, x) => (x.seri.t[x.seri.t.length - 1] > m ? x.seri.t[x.seri.t.length - 1] : m), '');
      const n = dolu.reduce((m, x) => Math.max(m, x.seri.t.length), 0);
      durum.textContent = `${tarihEtiketi(ilk, anaFrekans)} – ${tarihEtiketi(son, anaFrekans)} · ${n} gözlem`;
    } else {
      durum.textContent = '';
    }
    if (!tabloKap.hidden) tabloyuKur();
  }

  /** Bütün serilerin gözlem günlerinin birleşimi, yeniden eskiye; boş hücre "—". */
  function satirlar(): { t: string; v: (number | undefined)[] }[] {
    const g = gorunen();
    const haritalar = g.map((x) => new Map(x.seri.t.map((t, i) => [t, x.seri.v[i]])));
    const gunler = [...new Set(g.flatMap((x) => x.seri.t))].sort().reverse();
    return gunler.map((t) => ({ t, v: haritalar.map((h) => h.get(t)) }));
  }

  function tabloyuKur() {
    const g = gorunen();
    const thead = tabloKap.querySelector('thead tr')!;
    thead.replaceChildren();
    for (const ad of ['Tarih', ...g.map((x) => x.ad)]) {
      const th = document.createElement('th');
      th.scope = 'col';
      th.textContent = ad;
      thead.append(th);
    }
    tabloGovde.replaceChildren();
    const s = satirlar();
    for (const r of s) {
      const tr = document.createElement('tr');
      for (const h of [tarihEtiketi(r.t, anaFrekans), ...r.v.map((v) => (v === undefined ? '—' : yaz(v)))]) {
        const td = document.createElement('td');
        td.textContent = h;
        tr.append(td);
      }
      tabloGovde.append(tr);
    }
    tabloKap.querySelector('caption')!.textContent = `${s.length} gözlem günü, yeniden eskiye`;
  }

  function sec(secici: string, b: HTMLButtonElement) {
    for (const x of document.querySelectorAll<HTMLButtonElement>(secici)) x.setAttribute('aria-pressed', String(x === b));
  }

  for (const b of document.querySelectorAll<HTMLButtonElement>('[data-donem]')) {
    b.addEventListener('click', () => {
      donem = b.dataset.donem ? +b.dataset.donem : null;
      sec('[data-donem]', b);
      yenile();
    });
  }
  for (const b of document.querySelectorAll<HTMLButtonElement>('[data-donusum]')) {
    b.addEventListener('click', () => {
      donusum = b.dataset.donusum as Donusum;
      sec('[data-donusum]', b);
      yenile();
    });
  }
  kiyasSec?.addEventListener('change', async () => {
    const id = kiyasSec.value;
    if (!id) { kiyas = null; yenile(); return; }
    const k = (veri.kiyaslar ?? []).find((x) => x.id === id)!;
    try {
      let s = onbellek.get(id);
      if (!s) {
        const r = await fetch(`/grafikler/veri/${id}.json`);
        if (!r.ok) throw new Error(String(r.status));
        s = (await r.json()) as Seri;
        onbellek.set(id, s);
      }
      kiyas = { ...k, t: s.t, v: s.v };
      // Başka birimdeki seviye düzey olarak aynı eksene konmaz: gösterim 100'e endekse geçer.
      if (birimFarkli() && donusum === 'duzey' && endeksDugme) {
        donusum = 'endeks';
        sec('[data-donusum]', endeksDugme);
      }
    } catch {
      kiyas = null;
      kiyasSec.value = '';
      durum.textContent = 'Kıyas serisi yüklenemedi.';
      return;
    }
    yenile();
  });
  olaySec?.addEventListener('change', () => yenile());
  tabloDugme.addEventListener('click', () => {
    tabloKap.hidden = !tabloKap.hidden;
    tabloDugme.setAttribute('aria-expanded', String(!tabloKap.hidden));
    if (!tabloKap.hidden) tabloyuKur();
  });
  document.querySelector<HTMLButtonElement>('[data-csv]')!.addEventListener('click', () => {
    // Elektronik tablo dostu: noktalı virgül ayraç, ondalık virgül, ISO tarih, eskiden yeniye.
    const g = gorunen();
    const sayi = (v: number | undefined) => (v === undefined ? '' : String(v).replace('.', ','));
    const etiket = donusum === 'endeks' ? birimEtiketi() : birim() || 'düzey';
    const out = [['Tarih', ...g.map((x) => `${x.ad} (${etiket})`)].join(';')];
    for (const r of satirlar().reverse()) out.push([r.t, ...r.v.map(sayi)].join(';'));
    const blob = new Blob(['﻿' + out.join('\r\n')], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${veri.id}${donusum === 'duzey' ? '' : `-${donusum}`}.csv`;
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  });

  yenile();
}
