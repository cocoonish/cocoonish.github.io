import { getCollection } from 'astro:content';

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
  return new Response(JSON.stringify([...analizler, ...projeler, ...arastirmalar]), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
