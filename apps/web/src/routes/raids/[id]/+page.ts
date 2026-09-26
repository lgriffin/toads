import { error } from '@sveltejs/kit';
import { raids } from '$lib/mock/data';
import type { EntryGenerator, PageLoad } from './$types';

export const entries: EntryGenerator = () => raids.map((r) => ({ id: r.id }));

// Only the static preview has raid pages until the API serves analysed raids.
export const load: PageLoad = ({ params }) => {
  if (!__PREVIEW__) error(404, 'Raid not found');
  const raid = raids.find((r) => r.id === params.id);
  if (!raid) error(404, 'Raid not found');
  return { raid };
};
