import { NIGHT_IDS } from '$lib/nights';
import type { EntryGenerator, PageLoad } from './$types';

// The static preview prerenders each sample night; the real site serves any raid day in config.
export const entries: EntryGenerator = () => NIGHT_IDS.map((day) => ({ day }));

export const load: PageLoad = ({ params }) => ({ day: params.day });
