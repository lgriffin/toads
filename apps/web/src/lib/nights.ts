/**
 * The guild's raid nights, in week order. The hub's real list is config/raid_days.yaml, which reaches the web app as
 * the session's `day_names`; this list is what the web app knows without it: each night's toad, its name for an older
 * hub that sends no names, the preview's sample nights, and the nights the site's own words name. Add a night here and
 * in config, and it shows up everywhere.
 */
export interface RaidNight {
  /** The raid day's id in config/raid_days.yaml and in URLs such as /api/days/thu/... */
  id: string;
  name: string;
  /** The night's toad under static/logos/, without `.svg`. */
  toad: string;
}

export const RAID_NIGHTS: readonly RaidNight[] = [
  { id: 'wed', name: 'Wednesday', toad: 'days/wednesday-toad' },
  { id: 'thu', name: 'Thursday', toad: 'days/thursday-toad' },
  { id: 'sun', name: 'Sunday', toad: 'days/sunday-toad' }
];

export const NIGHT_IDS: readonly string[] = RAID_NIGHTS.map((n) => n.id);

/** Each night's name by id. */
export const NIGHT_NAMES: Readonly<Record<string, string>> = Object.fromEntries(RAID_NIGHTS.map((n) => [n.id, n.name]));

/** "a", "a and b", "a, b and c". */
export function inWords(items: readonly string[]): string {
  return items.length < 2 ? (items[0] ?? '') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}

/** "Wednesday, Thursday and Sunday". */
export const NIGHTS_IN_WORDS = inWords(RAID_NIGHTS.map((n) => n.name));

/** "Wednesday, Thursday or Sunday". */
export const NIGHTS_OR = NIGHTS_IN_WORDS.replace(/ and (?!.* and )/, ' or ');

const NUMBERS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven'];

/** "three", for copy such as "three 40-man teams". */
export const TEAM_COUNT = NUMBERS[RAID_NIGHTS.length] ?? `${RAID_NIGHTS.length}`;

/** A night by its config id or its name ("thu" or "Thursday"), whatever the case. */
export function raidNight(idOrName: string): RaidNight | undefined {
  const key = idOrName.trim().toLowerCase();
  return RAID_NIGHTS.find((n) => n.id === key || n.name.toLowerCase() === key);
}
