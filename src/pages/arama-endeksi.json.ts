import { getCollection } from 'astro:content';
import { bultenler, teknikler } from '../lib/yayinlar';
import { duzMetin } from '../lib/bicim';

// Derleme anında tüm içerikten arama endeksi üretir (istemci tarafı arama bunu çeker).
const temizle = (kaynak: string) =>
  kaynak
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/\$\$[\s\S]*?\$\$/g, ' ')
    .replace(/\$[^$\n]*\$/g, ' ')
    .replace(/import[^\n]*\n/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[#*_>`|[\]()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 6000);

export async function GET() {
  // Koleksiyon → URL kökü. Yeni bir koleksiyon açıldığında BURAYA da eklenmeli;
  // aksi halde yazı sitede aranamaz.
  const kok: Record<string, string> = {
    proje: 'projeler',
    arastirma: 'arastirma',
    analiz: 'analiz',
  };
  const yap = (e: any, tur: 'proje' | 'arastirma' | 'analiz') => ({
    tur,
    url: `/${kok[tur]}/${e.id}/`,
    title: e.data.title,
    description: e.data.description,
    tags: e.data.tags ?? [],
    govde: temizle(e.body ?? ''),
  });
  const projeler = (await getCollection('projeler')).map((e) => yap(e, 'proje'));
  const arastirmalar = (await getCollection('arastirma')).map((e) => yap(e, 'arastirma'));
  const analizler = (await getCollection('analiz')).map((e) => yap(e, 'analiz'));
  // Bülten ve teknik sayılar da aranır: okuma yazısı, gündem ve girişin düz metni.
  // Eskiden arama yalnız üç koleksiyonu görüyordu; bültenin arşivi aranamıyordu.
  const bultenKayitlari = bultenler().map((k) => ({
    tur: 'bulten',
    url: k.href,
    title: `${k.haftalik ? 'Haftaya bakış' : 'Günlük bülten'} — ${k.trTarih}`,
    description: k.aciklama,
    tags: [k.haftalik ? 'haftaya bakış' : 'günlük'],
    govde: duzMetin([k.b.yorum, ...Object.values(k.b.gundem ?? {})].join(' ')).slice(0, 6000),
  }));
  const teknikKayitlari = teknikler().map((k) => ({
    tur: 'teknik',
    url: k.href,
    title: `Haftalık teknik analiz — ${k.trTarih}`,
    description: k.aciklama,
    tags: (k.t.enstrumanlar ?? []).map((e: any) => String(e.ad).toLowerCase()),
    govde: duzMetin([k.t.giris, ...(k.t.enstrumanlar ?? []).map((e: any) => e.yorum)].join(' ')).slice(0, 6000),
  }));
  return new Response(JSON.stringify([...analizler, ...bultenKayitlari, ...teknikKayitlari, ...projeler, ...arastirmalar]), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
