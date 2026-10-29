/**
 * Gösterge şeridinin yazım kuralları — bülten sayfası ve ana sayfa aynı şeridi basar
 * (components/GostergeSerit.astro); kural tek yerde.
 */
/** Ölçüm katmanının yazdığı hazır metin: eski sayılarda ASCII tire kalmış olabilir. */
export const eksiDuzelt = (s: unknown): string => String(s ?? '').replace(/(^|[\s(])-(?=\d)/g, '$1−');
/**
 * Gösterge farkı. BİR ORANIN FARKI PUANDIR: %31,75'ten %31,51'e inen TÜFE'nin
 * farkı 0,24 puan, %0,24 değil — %0,24'lük bir düşüş 31,75'i 31,67'ye indirirdi.
 * Şerit farkı "−%0,24" basıyordu, aynı sayfadaki olay cümlesi aynı hareketi
 * doğru olarak "puan" diye yazıyordu (ölçüm katmanında `olay.FARK_BIRIMI`).
 */
export const gostergeFark = (fark: unknown, birim: unknown, sayisal?: unknown, farkBirim?: unknown): string => {
  const f = eksiDuzelt(fark);
  const bir = String(birim ?? '').trim();
  // Sıfır fark "—" basılıyordu ve "veri yok" ile karışıyordu.
  if (!f) return sayisal === 0 ? 'değişmedi' : '—';
  // Farkı YÜZDE yazılan gösterge (kur): ölçüm katmanı `fark_birim: "%"` yazar.
  if (String(farkBirim ?? '').trim() === '%') return yuzdeMetin(f);
  if (bir === '%') return `${f} puan`;
  return bir ? `${f} ${bir}` : f;
};
// BUGÜN İLERLEMEYEN GÖSTERGE (ölçüm katmanı `bugun_yeni: false`, 01.10.2026):
// 30.09 şeridindeki 17 göstergenin 10'u bir önceki sayıdakiyle birebir aynıydı
// ve 18.09 tarihli bir fark beş sayıdır bugünün haberi gibi renkli basılıyordu.
// Değer ve kendi tarihi kalır; fark basılmaz, kart soluk. Alanı taşımayan eski
// sayılarda davranış değişmez.
export const gostergeDurgun = (g: any): boolean => g?.bugun_yeni === false;
/** Hazır yüzde metni ("21,4", "−1,2") → sözleşme: işaret önde, % sonra ("−%1,2"). */
export const yuzdeMetin = (m: unknown): string => {
  const t = eksiDuzelt(m);
  return t.startsWith('−') || t.startsWith('+') ? `${t[0]}%${t.slice(1)}` : `%${t}`;
};
