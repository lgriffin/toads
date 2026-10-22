/** The preview's strategy docs: samples in the browser only, so the Strategy page and Raid page work on GitHub Pages. */
import { ApiError } from "$lib/api";
import { PREVIEW_DAY_NAMES } from "./absences-fake";
import {
  docProblem,
  type Library,
  type NightStrategy,
  type Raid,
  type StrategyBackend,
  type StrategyDoc,
} from "$lib/strategy";

export const PREVIEW_RAIDS: Raid[] = [
  { id: "mc", short: "MC", name: "Molten Core" },
  { id: "bwl", short: "BWL", name: "Blackwing Lair" },
  { id: "zg", short: "ZG", name: "Zul'Gurub" },
  { id: "aq20", short: "AQ20", name: "Ruins of Ahn'Qiraj" },
  { id: "aq40", short: "AQ40", name: "Temple of Ahn'Qiraj" },
  { id: "naxx", short: "Naxx", name: "Naxxramas" },
  { id: "tbd", short: "TBD", name: "Another raid (to be decided)" },
];

// The docs a raid holds at most, as the hub keeps them.
const DOC_LIMIT = 20;
let nextId = 1;
const doc = (
  raid: string,
  title: string,
  url: string,
  daysAgo: number,
): StrategyDoc => ({
  id: nextId++,
  raid,
  title,
  url,
  added_by: "Hopscotch",
  added_at: new Date(Date.now() - daysAgo * 86_400_000).toISOString(),
});
// Newest first, as the API keeps them.
let docs: StrategyDoc[] = [
  doc(
    "bwl",
    "BWL full clear",
    "https://docs.google.com/document/d/preview-bwl-v2",
    2,
  ),
  doc(
    "mc",
    "Sunday MC (fast clear)",
    "https://docs.google.com/document/d/preview-mc-sun",
    4,
  ),
  doc(
    "zg",
    "Zul'Gurub strategy",
    "https://docs.google.com/document/d/preview-zg",
    6,
  ),
  doc(
    "mc",
    "Molten Core strategy",
    "https://docs.google.com/document/d/preview-mc",
    9,
  ),
  doc(
    "bwl",
    "BWL first week",
    "https://docs.google.com/document/d/preview-bwl-v1",
    20,
  ),
];
const byTitle = (title: string) => docs.find((d) => d.title === title)?.id ?? 0;
// Wednesday runs ZG then BWL; Sunday keeps its own Molten Core doc.
const nights: Record<string, number[]> = {
  wed: [byTitle("Zul'Gurub strategy"), byTitle("BWL full clear")],
  sun: [byTitle("Sunday MC (fast clear)")],
};
const dayNames = PREVIEW_DAY_NAMES;

function library(): Library {
  const pinning = (id: number) =>
    Object.keys(dayNames).filter((day) => (nights[day] ?? []).includes(id));
  return {
    raids: PREVIEW_RAIDS.map((raid) => ({
      raid,
      docs: docs
        .filter((d) => d.raid === raid.id)
        .map((d) => ({ ...d, nights: pinning(d.id) })),
    })),
    nights: Object.entries(dayNames).map(([raid_day, name]) => ({
      raid_day,
      name,
      docs: [...(nights[raid_day] ?? [])],
    })),
  };
}

function nightOf(day: string): NightStrategy {
  return {
    raid_day: day,
    docs: (nights[day] ?? []).flatMap((id) =>
      docs
        .filter((d) => d.id === id)
        .flatMap((d) =>
          PREVIEW_RAIDS.filter((r) => r.id === d.raid).map((raid) => ({
            raid,
            doc: d,
          })),
        ),
    ),
  };
}

export const previewStrategy: StrategyBackend = {
  library: async () => library(),
  add: async (raid, url, title) => {
    const problem = docProblem(url, title);
    const known = PREVIEW_RAIDS.find((r) => r.id === raid);
    if (problem || !known)
      throw new ApiError(422, problem ?? "Pick one of the raids");
    if (docs.filter((d) => d.raid === raid).length >= DOC_LIMIT)
      throw new ApiError(
        422,
        `${known.short} has ${DOC_LIMIT} docs; take an old one down first`,
      );
    const added = doc(
      raid,
      title.trim().split(/\s+/).join(" ") || `${known.name} strategy`,
      url.trim(),
      0,
    );
    docs = [added, ...docs];
    return added;
  },
  remove: async (id, through) => {
    if (!docs.some((d) => d.id === id))
      throw new ApiError(404, "No such strategy doc");
    if (
      through !== null &&
      Object.entries(nights).some(
        ([day, ids]) => day !== through && ids.includes(id),
      )
    )
      throw new ApiError(
        409,
        "Another night pins this doc; its officers or a global officer can take it down",
      );
    docs = docs.filter((d) => d.id !== id);
    for (const day of Object.keys(nights))
      nights[day] = nights[day].filter((d) => d !== id);
  },
  night: async (day) => nightOf(day),
  setNight: async (day, ids) => {
    if (ids.some((id) => !docs.some((d) => d.id === id)))
      throw new ApiError(
        422,
        "Pick from the docs listed; one may have been taken down",
      );
    nights[day] = [...new Set(ids)];
    return nightOf(day);
  },
};
