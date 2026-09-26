import { error } from '@sveltejs/kit';
import { raids } from '$lib/mock/data';
import type { EntryGenerator, PageLoad } from './$types';

export const entries: EntryGenerator = () => raids.map((r) => ({ id: r.id }));

export const load: PageLoad = ({ params }) => {
  const raid = raids.find((r) => r.id === params.id);
  if (!raid) error(404, 'Raid not found');
  return { raid };
};
