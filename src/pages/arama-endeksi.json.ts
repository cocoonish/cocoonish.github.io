import { getCollection } from 'astro:content';
import { bultenler, teknikler } from '../lib/yayinlar';
import { duzMetin } from '../lib/bicim';
import { collections } from '../content.config';

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

// Koleksiyon → (tür, URL kökü). Kapsam koleksiyon tanımından türer: bir
// koleksiyon burada yoksa derleme DÜŞER. Önceki sürüm aynı kuralı yalnız
// yorumda taşıyordu ("yeni koleksiyon açıldığında buraya da eklenmeli") ve
// indikatör sayfaları hiç aranamıyordu.
const KOK: Record<string, { tur: string; kok: string }> = {
  projeler: { tur: 'proje', kok: 'projeler' },
  arastirma: { tur: 'arastirma', kok: 'arastirma' },
  analiz: { tur: 'analiz', kok: 'analiz' },
  indikatorler: { tur: 'indikator', kok: 'indikatorler' },
};

export async function GET() {
  const eksik = Object.keys(collections).filter((ad) => !KOK[ad]);
  if (eksik.length) throw new Error(`arama endeksi: koleksiyon eşlemesi yok — ${eksik.join(', ')}`);
  const koleksiyonKayitlari = (
    await Promise.all(
      Object.keys(collections).map(async (ad) =>
        (await getCollection(ad as keyof typeof collections)).map((e: any) => ({
          tur: KOK[ad].tur,
          url: `/${KOK[ad].kok}/${e.id}/`,
          title: e.data.title,
          description: e.data.description,
          tags: e.data.tags ?? [],
          govde: temizle(e.body ?? ''),
        })),
      ),
    )
  ).flat();
  // Bülten ve teknik sayılar da aranır: okuma yazısı, gündem ve girişin düz metni.
  // Eskiden arama yalnız üç koleksiyonu görüyordu; bültenin arşivi aranamıyordu.
  const bultenKayitlari = bultenler().map((k) => ({
    tur: 'bulten',
    url: k.href,
    title: `${k.haftalik ? 'Haftaya bakış' : 'Günlük bülten'} — ${k.trTarih}`,
    description: k.aciklama,
    tags: [k.haftalik ? 'haftaya bakış' : 'günlük'],
    // Biçim 3'te olguların TEK evi manşet ve `ozet.ne_oldu`dur; okuma onları
    // yeniden saymaz — dışarıda kalınca TMSF/ÖTV aramada hiçbir sayfa bulmuyordu.
    // Haftalık sayının sınırı ve SIRASI ayrı (01.10.2026): 6–9 bin kelimelik
    // haftaya bakış ~50 bin karakter. Okumayı senaryolardan önce koyunca rehber
    // aralığının ortasında senaryolar 12.000'in DIŞINDA kalıyordu (risk 12.111.
    // karakterde başlıyor). Senaryolar okumadan önce gelir: rehberin üst
    // uçlarında bile (manşet + 10 madde + 1.000 kelime risk) önek ~11.000
    // karakter, yani senaryoların tamamı aranır; okuma kalan payla kesilir,
    // öbür bölümler aranmaz. Endeks yılda ~300 KB büyür (günlükler aynı).
    govde: duzMetin((k.haftalik
      ? [k.b.manset, k.b.ozet?.ne_oldu, k.b.gundem?.risk, k.b.yorum,
         ...Object.entries(k.b.gundem ?? {}).filter(([id]) => id !== 'risk').map(([, v]) => v)]
      : [k.b.manset, k.b.ozet?.ne_oldu, k.b.ozet?.ne_bekleniyor, k.b.yorum,
         ...Object.values(k.b.gundem ?? {})]).filter(Boolean).join(' '))
      .slice(0, k.haftalik ? 12000 : 6000),
  }));
  const teknikKayitlari = teknikler().map((k) => ({
    tur: 'teknik',
    url: k.href,
    title: `Haftalık teknik analiz — ${k.trTarih}`,
    description: k.aciklama,
    tags: (k.t.enstrumanlar ?? []).map((e: any) => String(e.ad).toLowerCase()),
    govde: duzMetin([k.t.giris, ...(k.t.enstrumanlar ?? []).map((e: any) => e.yorum)].join(' ')).slice(0, 6000),
  }));
  return new Response(JSON.stringify([
    ...koleksiyonKayitlari.filter((k) => k.tur === 'analiz'),
    ...bultenKayitlari,
    ...teknikKayitlari,
    ...koleksiyonKayitlari.filter((k) => k.tur !== 'analiz'),
  ]), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
