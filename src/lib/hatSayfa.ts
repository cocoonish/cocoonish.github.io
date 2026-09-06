/* ─────────────────────────────────────────────────────────────
   Bir hattın OKURA görünen adı ve sayfası.

   Bülten kaynak notları ("… · veri 21.08.2026") eskiden hattın slug'ını
   doğrudan `/projeler/<slug>/` adresine çeviriyordu ve adı da o panonun
   başlığından okuyordu. İkisi de HER HATTIN BİR PANOSU OLDUĞUNU varsayıyor.
   Varsayım tuttuğu sürece görünmez: panosu olmayan bir hat çıktığında bağ
   404 verir, ad da okura slug basar — ve koşu yeşil biter.

   Sözleşme şudur: bir hattın sayfası, o hattın `ozet.json`unu OKUYAN
   sayfadır. Bunu bir listeden değil `<Deger proje="<slug>">` çağrısından
   türetiyoruz (bkz. CLAUDE.md "bir denetimin KAPSAMI denetimin parçasıdır"):
     1) panosu varsa pano,
     2) yoksa o hattı okuyan EN YENİ analiz yazısı,
     3) hiçbiri yoksa bağ HİÇ kurulmaz — 404 veren bir bağ, bağsız bir
        addan kötüdür.

   Ad da aynı sırayla çözülür ve son çare slug DEĞİL, ölçüm katmanının
   kaydettiği `hat_ad`dır (bulten/ayar.HAT_ADI, tek tanım).
   ───────────────────────────────────────────────────────────── */
import { getCollection } from 'astro:content';

export interface HatSayfa {
  /** Panonun başlığı; analizden çözülen hatlarda boş (ad kayıttan gelir). */
  ad?: string;
  href: string;
}

/** slug → { ad?, href } — panosu olmayan hat analizine, o da yoksa listeye girmez. */
export async function hatSayfalari(): Promise<Record<string, HatSayfa>> {
  const out: Record<string, HatSayfa> = {};
  for (const p of await getCollection('projeler')) {
    out[p.id] = { ad: p.data.title, href: `/projeler/${p.id}/` };
  }
  // Yeniden eskiye: bir hattı birden çok yazı okuyorsa en yenisi kazanır.
  const analizler = (await getCollection('analiz')).sort(
    (a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf() || b.id.localeCompare(a.id),
  );
  for (const y of analizler) {
    for (const m of (y.body ?? '').matchAll(/\bproje="([a-z0-9-]+)"/g)) {
      if (!out[m[1]]) out[m[1]] = { href: `/analiz/${y.id}/` };
    }
  }
  return out;
}
