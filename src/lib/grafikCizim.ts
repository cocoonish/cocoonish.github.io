/* ─────────────────────────────────────────────────────────────
   Grafikler bölümü — seri sayfasının çizgi grafiği (tarayıcıda, kütüphanesiz).

   Plotly kullanılmaz: tek eksenli bir zaman serisi için 4,6 MB'lık bir
   kütüphane gerekmez ve ev stilinin (kâğıt zemin, mürekkep, bordo vurgu)
   kendisi burada tek yerden yazılır. Kurallar:
   · TEK EKSEN. İki seri yalnız aynı birimde aynı eksende kıyaslanır (sayfa
     yalnız o serileri kıyas listesine koyar); çift eksen yoktur.
   · İpucu önce DEĞERİ, sonra tarihi yazar; artı imli dikey çizgi en yakın
     gözleme oturur. Klavyeyle de gezilir (ok tuşları, Home/End).
   · Sayı biçimi lib/bicim'den gelir; burada sayı biçimlenmez.
   · Etiketler textContent ile yazılır (seri adları HTML değildir).
   ───────────────────────────────────────────────────────────── */
import { AYLAR_TR, olcuYaz } from './bicim';
import { tarihEtiketi, type Frekans, type Seri } from './grafikDonusum';

export interface CizimSerisi {
  ad: string;
  seri: Seri;
  renk: string;
}

export interface CizimAyar {
  birim: string;
  ondalik: number;
  isaretli: boolean;          // dönüşüm (fark/değişim) — artıya "+" konur
  frekans: Frekans;
}

const NS = 'http://www.w3.org/2000/svg';
const AY_KISA = AYLAR_TR.map((a) => a.slice(0, 3));

function el<K extends keyof SVGElementTagNameMap>(ad: K, nit: Record<string, string | number>): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, ad);
  for (const [k, v] of Object.entries(nit)) e.setAttribute(k, String(v));
  return e;
}

function ms(t: string): number {
  return Date.UTC(+t.slice(0, 4), +t.slice(5, 7) - 1, +t.slice(8, 10));
}

/** "Güzel" eksen adımları: 1, 2, 2,5, 5 × 10^k. */
function guzelAdimlar(min: number, max: number, hedef: number): number[] {
  if (!(max > min)) {
    const p = Math.abs(min) || 1;
    min -= p * 0.05;
    max += p * 0.05;
  }
  const kaba = (max - min) / Math.max(1, hedef);
  const us = 10 ** Math.floor(Math.log10(kaba));
  const adim = [1, 2, 2.5, 5, 10].map((k) => k * us).find((a) => a >= kaba) ?? 10 * us;
  const bas = Math.floor(min / adim) * adim;
  const out: number[] = [];
  for (let v = bas; v <= max + adim * 1e-9; v += adim) out.push(Number(v.toPrecision(12)));
  if (out[out.length - 1] < max) out.push(Number((out[out.length - 1] + adim).toPrecision(12)));
  return out;
}

function adimOndalik(adimlar: number[]): number {
  if (adimlar.length < 2) return 0;
  const a = Math.abs(adimlar[1] - adimlar[0]);
  return a >= 1 ? 0 : Math.min(4, Math.ceil(-Math.log10(a) + 1e-9));
}

/** Zaman ekseni işaretleri: aralığa göre yıl, çeyrek ya da ay. */
function zamanIsaretleri(t0: number, t1: number, genislik: number): { x: number; etiket: string }[] {
  const yil = (t1 - t0) / (365.25 * 864e5);
  const azami = Math.max(2, Math.floor(genislik / 70));
  const d0 = new Date(t0);
  const out: { x: number; etiket: string }[] = [];
  if (yil > 2.5) {
    const adim = [1, 2, 5, 10].find((a) => yil / a <= azami) ?? 10;
    let y = Math.ceil(d0.getUTCFullYear() / adim) * adim;
    for (; Date.UTC(y, 0, 1) <= t1; y += adim) {
      const x = Date.UTC(y, 0, 1);
      if (x >= t0) out.push({ x, etiket: String(y) });
    }
    return out;
  }
  const aylar = yil * 12;
  const adim = [1, 2, 3, 6, 12].find((a) => aylar / a <= azami) ?? 12;
  let y = d0.getUTCFullYear();
  let m = d0.getUTCMonth() + 1;
  m = Math.ceil(m / adim) * adim;
  for (;;) {
    while (m >= 12) { m -= 12; y += 1; }
    const x = Date.UTC(y, m, 1);
    if (x > t1) break;
    if (x >= t0) out.push({ x, etiket: m === 0 ? String(y) : `${AY_KISA[m]} ${String(y).slice(2)}` });
    m += adim;
  }
  return out;
}

/** Sıralı dizide x'e en yakın gözlemin sırası. */
function enYakin(xs: number[], x: number): number {
  let lo = 0;
  let hi = xs.length - 1;
  while (hi - lo > 1) {
    const orta = (lo + hi) >> 1;
    if (xs[orta] <= x) lo = orta; else hi = orta;
  }
  return Math.abs(xs[hi] - x) < Math.abs(xs[lo] - x) ? hi : lo;
}

export class ZamanGrafigi {
  private kap: HTMLElement;
  private ipucu: HTMLElement;
  private seriler: CizimSerisi[] = [];
  private ayar: CizimAyar = { birim: '', ondalik: 1, isaretli: false, frekans: 'gunluk' };
  private secili = -1;
  private gozlem: ResizeObserver;

  constructor(kap: HTMLElement, ipucu: HTMLElement) {
    this.kap = kap;
    this.ipucu = ipucu;
    this.gozlem = new ResizeObserver(() => this.ciz());
    this.gozlem.observe(kap);
    kap.addEventListener('keydown', (e) => this.tus(e));
    kap.addEventListener('blur', () => this.gizle());
  }

  goster(seriler: CizimSerisi[], ayar: CizimAyar): void {
    this.seriler = seriler.filter((s) => s.seri.t.length > 0);
    this.ayar = ayar;
    this.secili = -1;
    this.ciz();
  }

  private yaz(v: number): string {
    return olcuYaz(v, this.ayar.birim, this.ayar.ondalik, this.ayar.isaretli);
  }

  // Çizim ölçüleri — bir çizimde hesaplanıp ipucuna aktarılır.
  private olcu: {
    sol: number; sag: number; ust: number; alt: number; g: number; h: number;
    x: (t: number) => number; y: (v: number) => number; xs: number[][]; svg: SVGSVGElement;
    cizgi: SVGLineElement; noktalar: SVGCircleElement[];
  } | null = null;

  private ciz(): void {
    const g = Math.max(280, this.kap.clientWidth);
    const h = g < 560 ? 280 : 400;
    this.kap.replaceChildren();
    this.olcu = null;
    if (!this.seriler.length) {
      const p = document.createElement('p');
      p.className = 'grafik-bos';
      p.textContent = 'Bu dönemde ölçülebilen gözlem yok.';
      this.kap.append(p);
      return;
    }
    const tum = this.seriler.flatMap((s) => s.seri.v);
    const xs = this.seriler.map((s) => s.seri.t.map(ms));
    const t0 = Math.min(...xs.map((a) => a[0]));
    const t1 = Math.max(...xs.map((a) => a[a.length - 1]));
    let vmin = Math.min(...tum);
    let vmax = Math.max(...tum);
    // Değişim ve fark serilerinde sıfır çizgisi görünür olmalı.
    if (this.ayar.isaretli) { vmin = Math.min(vmin, 0); vmax = Math.max(vmax, 0); }
    const adimlar = guzelAdimlar(vmin, vmax, h < 300 ? 4 : 6);
    const ymin = adimlar[0];
    const ymax = adimlar[adimlar.length - 1];
    const eksenOnd = adimOndalik(adimlar);
    const etiketler = adimlar.map((v) => olcuYaz(v, this.ayar.birim === '%' ? '%' : '', eksenOnd));
    const sol = 8 + Math.max(...etiketler.map((e) => e.length)) * 7.2;
    const sag = 14;
    const ust = 12;
    const alt = 28;
    const x = (t: number) => sol + ((t - t0) / Math.max(1, t1 - t0)) * (g - sol - sag);
    const y = (v: number) => ust + (1 - (v - ymin) / (ymax - ymin || 1)) * (h - ust - alt);

    const svg = el('svg', { viewBox: `0 0 ${g} ${h}`, width: g, height: h, 'aria-hidden': 'true' });
    const izgara = el('g', { class: 'izgara' });
    adimlar.forEach((v, i) => {
      izgara.append(el('line', { x1: sol, x2: g - sag, y1: y(v), y2: y(v), class: v === 0 ? 'sifir' : '' }));
      const yz = el('text', { x: sol - 8, y: y(v) + 4, 'text-anchor': 'end', class: 'eksen-yazi' });
      yz.textContent = etiketler[i];
      izgara.append(yz);
    });
    for (const is of zamanIsaretleri(t0, t1, g - sol - sag)) {
      izgara.append(el('line', { x1: x(is.x), x2: x(is.x), y1: h - alt, y2: h - alt + 5, class: 'isaret' }));
      const xz = el('text', { x: x(is.x), y: h - alt + 19, 'text-anchor': 'middle', class: 'eksen-yazi' });
      xz.textContent = is.etiket;
      izgara.append(xz);
    }
    izgara.append(el('line', { x1: sol, x2: g - sag, y1: h - alt, y2: h - alt, class: 'taban' }));
    svg.append(izgara);

    this.seriler.forEach((s, k) => {
      let d = '';
      s.seri.t.forEach((_, i) => {
        d += `${i ? 'L' : 'M'}${x(xs[k][i]).toFixed(1)},${y(s.seri.v[i]).toFixed(1)}`;
      });
      svg.append(el('path', { d, fill: 'none', stroke: s.renk, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
    });

    const cizgi = el('line', { y1: ust, y2: h - alt, class: 'arti', visibility: 'hidden' });
    svg.append(cizgi);
    const noktalar = this.seriler.map((s) => {
      const c = el('circle', { r: 4.5, fill: s.renk, stroke: 'var(--paper)', 'stroke-width': 2, visibility: 'hidden' });
      svg.append(c);
      return c;
    });
    // Dokunma hedefi çizgiden geniş: çizim alanının tamamı.
    const alan = el('rect', { x: sol, y: ust, width: g - sol - sag, height: h - ust - alt, fill: 'transparent' });
    alan.addEventListener('pointermove', (e) => {
      const r = svg.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * g;
      const t = t0 + ((px - sol) / (g - sol - sag)) * (t1 - t0);
      this.isaretle(enYakin(xs[0], t));
    });
    alan.addEventListener('pointerleave', () => this.gizle());
    svg.append(alan);
    this.kap.append(svg);
    this.olcu = { sol, sag, ust, alt, g, h, x, y, xs, svg, cizgi, noktalar };
  }

  private isaretle(i: number): void {
    const o = this.olcu;
    if (!o) return;
    const ana = this.seriler[0];
    i = Math.max(0, Math.min(ana.seri.t.length - 1, i));
    this.secili = i;
    const t = o.xs[0][i];
    const px = o.x(t);
    o.cizgi.setAttribute('x1', String(px));
    o.cizgi.setAttribute('x2', String(px));
    o.cizgi.setAttribute('visibility', 'visible');
    this.ipucu.replaceChildren();
    this.seriler.forEach((s, k) => {
      const j = k === 0 ? i : enYakin(o.xs[k], t);
      // Kıyas serisinin en yakın gözlemi başka bir günse (frekans farkı) o günü ayrıca yaz.
      const ayniGun = Math.abs(o.xs[k][j] - t) < 864e5 * 2;
      const nokta = o.noktalar[k];
      nokta.setAttribute('cx', String(o.x(o.xs[k][j])));
      nokta.setAttribute('cy', String(o.y(s.seri.v[j])));
      nokta.setAttribute('visibility', 'visible');
      const satir = document.createElement('div');
      satir.className = 'ipucu-satir';
      const im = document.createElement('span');
      im.className = 'ipucu-im';
      im.style.background = s.renk;
      const deger = document.createElement('strong');
      deger.textContent = this.yaz(s.seri.v[j]);
      satir.append(im, deger);
      if (this.seriler.length > 1) {
        const ad = document.createElement('span');
        ad.className = 'ipucu-ad';
        ad.textContent = ayniGun ? s.ad : `${s.ad} · ${tarihEtiketi(s.seri.t[j], this.ayar.frekans)}`;
        satir.append(ad);
      }
      this.ipucu.append(satir);
    });
    const tarih = document.createElement('div');
    tarih.className = 'ipucu-tarih';
    tarih.textContent = tarihEtiketi(ana.seri.t[i], this.ayar.frekans);
    this.ipucu.append(tarih);
    this.ipucu.hidden = false;
    // Konum: çizginin sağında, sığmazsa solunda.
    const oran = this.kap.clientWidth / o.g;
    const gx = px * oran;
    const w = this.ipucu.offsetWidth;
    const sol = gx + 14 + w > this.kap.clientWidth ? gx - 14 - w : gx + 14;
    this.ipucu.style.left = `${Math.max(0, sol)}px`;
    this.ipucu.style.top = `${o.ust * oran}px`;
  }

  private gizle(): void {
    const o = this.olcu;
    this.ipucu.hidden = true;
    if (!o) return;
    o.cizgi.setAttribute('visibility', 'hidden');
    o.noktalar.forEach((n) => n.setAttribute('visibility', 'hidden'));
  }

  private tus(e: KeyboardEvent): void {
    if (!this.seriler.length) return;
    const n = this.seriler[0].seri.t.length;
    const adim = e.shiftKey ? 10 : 1;
    let i = this.secili < 0 ? n - 1 : this.secili;
    if (e.key === 'ArrowLeft') i -= adim;
    else if (e.key === 'ArrowRight') i += adim;
    else if (e.key === 'Home') i = 0;
    else if (e.key === 'End') i = n - 1;
    else return;
    e.preventDefault();
    this.isaretle(i);
  }
}
