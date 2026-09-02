/* ─────────────────────────────────────────────────────────────
   X gönderisi bağları — tweet defterinin site tarafındaki aynası.

   Gönderim aracı her gönderiden sonra defteri iki yere yazar: tweet/defter.json
   (iş akışının kayıt defteri) ve site/src/data/tweet/defter.json (bu ayna).
   Ayna gerekli, çünkü public depoya yalnız site/ klasörü çıkar. Anahtar biçimi
   defterle aynı: "bulten:<tarih>", "teknik:<tarih>", "analiz:<slug>".

   Bağlantı https://x.com/i/status/<id> biçimindedir — kullanıcı adı gerekmez,
   X kendisi doğru hesaba yönlendirir.
   ───────────────────────────────────────────────────────────── */
import defter from '../data/tweet/defter.json';

// Ayna bir PROJEKSİYONDUR (gonder._ayna): yalnız kök gönderinin kimliği ve
// zamanı. İç notlar, "gönderiliyor" işaretleri ve kimliksiz tohum kayıtları
// buraya hiç yazılmaz — public depoya çıkan dosya budur.
interface Kayit { id: string; zaman?: string }

const D = defter as Record<string, Kayit>;

/** Anahtarın X gönderisi (kök tweet) — yoksa null. */
export function xBagi(anahtar: string): { url: string; zaman: string } | null {
  const k = D[anahtar];
  const id = k?.id;
  if (!id) return null;
  return { url: `https://x.com/i/status/${id}`, zaman: k?.zaman ?? '' };
}

export const xBulten = (tarih: string) => xBagi(`bulten:${tarih}`);
export const xTeknik = (tarih: string) => xBagi(`teknik:${tarih}`);
export const xAnaliz = (slug: string) => xBagi(`analiz:${slug}`);
