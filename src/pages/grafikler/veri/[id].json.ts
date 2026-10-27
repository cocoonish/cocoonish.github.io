/* Seri sayfasının KIYAS serisini taşıyan uç nokta: /grafikler/veri/<id>.json.
   Sayfa kendi serisini gömülü taşır; kıyas için seçilen ikinci seri buradan
   istenir. Yalnız çözülebilen seriler üretilir (lib/grafikVeri). */
import type { APIRoute } from 'astro';
import { seriler } from '../../../lib/grafikVeri';

export function getStaticPaths() {
  return seriler()
    .filter((s) => !s.sorun)
    .map((s) => ({ params: { id: s.id } }));
}

export const GET: APIRoute = ({ params }) => {
  const s = seriler().find((x) => x.id === params.id)!;
  return new Response(JSON.stringify({ t: s.seri.t, v: s.seri.v }), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
