/** The preview's strategy docs: samples in the browser only, so the Strategy page and Raid page work on GitHub Pages. */
import { ApiError } from '$lib/api';
import { PREVIEW_DAY_NAMES } from './absences-fake';
import { docProblem, type Library, type Raid, type StrategyBackend, type StrategyDoc } from '$lib/strategy';

export const PREVIEW_RAIDS: Raid[] = [
  { id: 'mc', short: 'MC', name: 'Molten Core' },
  { id: 'bwl', short: 'BWL', name: 'Blackwing Lair' },
  { id: 'zg', short: 'ZG', name: "Zul'Gurub" },
  { id: 'aq20', short: 'AQ20', name: "Ruins of Ahn'Qiraj" },
  { id: 'aq40', short: 'AQ40', name: "Temple of Ahn'Qiraj" },
  { id: 'naxx', short: 'Naxx', name: 'Naxxramas' },
  { id: 'tbd', short: 'TBD', name: 'Another raid (to be decided)' }
];

let nextId = 1;
const doc = (raid: string, title: string, url: string, daysAgo: number): StrategyDoc => ({
  id: nextId++,
  raid,
  title,
  url,
  added_by: 'Hopscotch',
  added_at: new Date(Date.now() - daysAgo * 86_400_000).toISOString()
});
// Newest first, as the API keeps them.
let docs: StrategyDoc[] = [
  doc('bwl', 'BWL full clear', 'https://docs.google.com/document/d/preview-bwl-v2', 2),
  doc('mc', 'Molten Core strategy', 'https://docs.google.com/document/d/preview-mc', 9),
  doc('bwl', 'BWL first week', 'https://docs.google.com/document/d/preview-bwl-v1', 20)
];
const nights: Record<string, string> = { wed: 'bwl', sun: 'mc' };

function library(): Library {
  return {
    raids: PREVIEW_RAIDS.map((raid) => {
      const mine = docs.filter((d) => d.raid === raid.id);
      return { raid, pinned: mine[0] ?? null, replaced: mine.slice(1) };
    }),
    nights: Object.entries(PREVIEW_DAY_NAMES).map(([raid_day, name]) => ({ raid_day, name, raid: nights[raid_day] ?? null }))
  };
}

function nightOf(day: string) {
  const raid = PREVIEW_RAIDS.find((r) => r.id === nights[day]) ?? null;
  return { raid_day: day, raid, pinned: raid ? (docs.find((d) => d.raid === raid.id) ?? null) : null };
}

export const previewStrategy: StrategyBackend = {
  library: async () => library(),
  pin: async (raid, url, title) => {
    const problem = docProblem(url, title);
    const known = PREVIEW_RAIDS.find((r) => r.id === raid);
    if (problem || !known) throw new ApiError(422, problem ?? 'Pick one of the raids');
    const added = doc(raid, title.trim().split(/\s+/).join(' ') || `${known.name} strategy`, url.trim(), 0);
    docs = [added, ...docs];
    return added;
  },
  remove: async (id) => {
    if (!docs.some((d) => d.id === id)) throw new ApiError(404, 'No such strategy doc');
    docs = docs.filter((d) => d.id !== id);
  },
  night: async (day) => nightOf(day),
  setNight: async (day, raid) => {
    if (raid === null) delete nights[day];
    else nights[day] = raid;
    return nightOf(day);
  }
};
