import { PREVIEW_RAID_IDS } from '$lib/preview/logs-fake';
import type { EntryGenerator, PageLoad } from './$types';

export const entries: EntryGenerator = () => PREVIEW_RAID_IDS.map((id) => ({ id }));

export const load: PageLoad = ({ params }) => ({ report: params.id });
