/* ─────────────────────────────────────────────────────────────
   Araştırma derslerini gruplanmış ve ölçülmüş hâlde toplar.
   Hem /arastirma/ listesi hem de ana sayfa aynı kaynağı kullanır;
   böylece iki yerde iki farklı hikâye anlatılmaz.
   ───────────────────────────────────────────────────────────── */
import { getCollection } from 'astro:content';
import { olc, olcumSatiri, sureYaz, type DersOlcum } from './ders';
import { DIGER_GRUP, GRUPLAR, grupBul, grupIciSira, type DersGrubu } from './dersGruplari';

export interface DersKaydi {
  slug: string;
  href: string;
  data: {
    title: string;
    description: string;
    ozet?: string;
    tags: string[];
    durum: 'aktif' | 'taslak' | 'arsiv';
    seviye?: 'giris' | 'orta' | 'ileri';
    onkosul: string[];
    pubDate: Date;
    updatedDate?: Date;
  };
  olcum: DersOlcum;
  /** "43 dk okuma · 12 bölüm · 1 hesap aracı · 6 pratik · 17 alıştırma" */
  olcuMetni: string;
  grup: DersGrubu;
  onkosullar: { href: string; title: string }[];
}

export interface DersGrupKaydi {
  grup: DersGrubu;
  dersler: DersKaydi[];
  toplamDakika: number;
  toplamSure: string;
}

export interface DersToplami {
  ders: number;
  dakika: number;
  sure: string;
  grafik: number;
  arac: number;
  pratik: number;
  alistirma: number;
  kelime: number;
}

const arsivSonda = (a: { data: { durum: string } }, b: { data: { durum: string } }) =>
  (a.data.durum === 'arsiv' ? 1 : 0) - (b.data.durum === 'arsiv' ? 1 : 0);

export async function dersleriTopla(): Promise<{
  dersler: DersKaydi[];
  gruplar: DersGrupKaydi[];
  toplam: DersToplami;
}> {
  const ham = await getCollection('arastirma');

  const baslikHaritasi = new Map(ham.map((e) => [e.id, e.data.title]));

  const dersler: DersKaydi[] = ham.map((e) => ({
    slug: e.id,
    href: `/arastirma/${e.id}/`,
    data: e.data as DersKaydi['data'],
    olcum: olc(e.body),
    olcuMetni: olcumSatiri(olc(e.body)).join(' · '),
    grup: grupBul(e.id, e.data.tags),
    onkosullar: (e.data.onkosul ?? [])
      .filter((s: string) => baslikHaritasi.has(s))
      .map((s: string) => ({ href: `/arastirma/${s}/`, title: baslikHaritasi.get(s)! })),
  }));

  // Grup sırası config'teki sıra; her grup içinde okuma sırası.
  const gruplar: DersGrupKaydi[] = [...GRUPLAR, DIGER_GRUP]
    .map((grup) => {
      const icerik = dersler
        .filter((d) => d.grup.id === grup.id)
        .sort((a, b) => a.data.pubDate.valueOf() - b.data.pubDate.valueOf())
        .sort((a, b) => grupIciSira(grup, a.slug) - grupIciSira(grup, b.slug))
        .sort(arsivSonda);
      const toplamDakika = icerik.reduce((t, d) => t + d.olcum.dakika, 0);
      return { grup, dersler: icerik, toplamDakika, toplamSure: sureYaz(toplamDakika) };
    })
    .filter((g) => g.dersler.length > 0);

  const dakika = dersler.reduce((t, d) => t + d.olcum.dakika, 0);
  const toplam: DersToplami = {
    ders: dersler.length,
    dakika,
    sure: sureYaz(dakika),
    grafik: dersler.reduce((t, d) => t + d.olcum.grafik, 0),
    arac: dersler.reduce((t, d) => t + d.olcum.arac, 0),
    pratik: dersler.reduce((t, d) => t + d.olcum.pratik, 0),
    alistirma: dersler.reduce((t, d) => t + d.olcum.alistirma, 0),
    kelime: dersler.reduce((t, d) => t + d.olcum.kelime, 0),
  };

  // Ana sayfa için düz liste: en yeni önce, arşiv sonda.
  const duzListe = [...dersler]
    .sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf())
    .sort(arsivSonda);

  return { dersler: duzListe, gruplar, toplam };
}
