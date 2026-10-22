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

const KEEP = 6;
let nextId = 1;
const doc = (
  raid: string,
  raid_day: string | null,
  title: string,
  url: string,
  daysAgo: number,
): StrategyDoc => ({
  id: nextId++,
  raid,
  raid_day,
  title,
  url,
  added_by: "Hopscotch",
  added_at: new Date(Date.now() - daysAgo * 86_400_000).toISOString(),
});
// Newest first, as the API keeps them. Sunday keeps its own Molten Core doc; Wednesday runs ZG then BWL.
let docs: StrategyDoc[] = [
  doc(
    "bwl",
    null,
    "BWL full clear",
    "https://docs.google.com/document/d/preview-bwl-v2",
    2,
  ),
  doc(
    "mc",
    "sun",
    "Sunday MC (fast clear)",
    "https://docs.google.com/document/d/preview-mc-sun",
    4,
  ),
  doc(
    "zg",
    null,
    "Zul'Gurub strategy",
    "https://docs.google.com/document/d/preview-zg",
    6,
  ),
  doc(
    "mc",
    null,
    "Molten Core strategy",
    "https://docs.google.com/document/d/preview-mc",
    9,
  ),
  doc(
    "bwl",
    null,
    "BWL first week",
    "https://docs.google.com/document/d/preview-bwl-v1",
    20,
  ),
];
const nights: Record<string, string[]> = { wed: ["zg", "bwl"], sun: ["mc"] };
const dayNames = PREVIEW_DAY_NAMES;
const dayOrder = Object.keys(dayNames);

function library(): Library {
  return {
    raids: PREVIEW_RAIDS.map((raid) => {
      const mine = docs.filter((d) => d.raid === raid.id);
      const places = [...new Set(mine.map((d) => d.raid_day))].sort(
        (a, b) =>
          (a === null ? -1 : dayOrder.indexOf(a)) -
          (b === null ? -1 : dayOrder.indexOf(b)),
      );
      return {
        raid,
        slots: places.map((day) => {
          const here = mine.filter((d) => d.raid_day === day);
          return {
            raid_day: day,
            name: day === null ? "Every night" : (dayNames[day] ?? day),
            pinned: here[0],
            replaced: here.slice(1),
          };
        }),
      };
    }),
    nights: Object.entries(dayNames).map(([raid_day, name]) => ({
      raid_day,
      name,
      raids: [...(nights[raid_day] ?? [])],
    })),
  };
}

function nightOf(day: string): NightStrategy {
  const raids = (nights[day] ?? []).flatMap((id) =>
    PREVIEW_RAIDS.filter((r) => r.id === id),
  );
  return {
    raid_day: day,
    raids: raids.map((raid) => ({
      raid,
      pinned:
        docs.find((d) => d.raid === raid.id && d.raid_day === day) ??
        docs.find((d) => d.raid === raid.id && d.raid_day === null) ??
        null,
    })),
  };
}

export const previewStrategy: StrategyBackend = {
  library: async () => library(),
  pin: async (raid, url, title, { night }) => {
    const problem = docProblem(url, title);
    const known = PREVIEW_RAIDS.find((r) => r.id === raid);
    if (problem || !known)
      throw new ApiError(422, problem ?? "Pick one of the raids");
    const added = doc(
      raid,
      night,
      title.trim().split(/\s+/).join(" ") || `${known.name} strategy`,
      url.trim(),
      0,
    );
    const kept = [
      added,
      ...docs.filter((d) => d.raid === raid && d.raid_day === night),
    ].slice(0, KEEP);
    docs = [
      added,
      ...docs.filter(
        (d) => d.raid !== raid || d.raid_day !== night || kept.includes(d),
      ),
    ];
    // A doc pinned for one night adds its raid to that night, as the hub does.
    if (night !== null && !(nights[night] ?? []).includes(raid))
      nights[night] = [...(nights[night] ?? []), raid];
    return added;
  },
  remove: async (id, through) => {
    const gone = docs.find((d) => d.id === id);
    if (
      !gone ||
      (through !== null && gone.raid_day !== null && gone.raid_day !== through)
    )
      throw new ApiError(404, "No such strategy doc");
    docs = docs.filter((d) => d.id !== id);
  },
  night: async (day) => nightOf(day),
  setNight: async (day, raids) => {
    if (raids.some((r) => !PREVIEW_RAIDS.some((p) => p.id === r)))
      throw new ApiError(422, "Pick from the raids listed");
    nights[day] = [...new Set(raids)];
    return nightOf(day);
  },
};
