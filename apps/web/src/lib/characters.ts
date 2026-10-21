/**
 * A member's character page on Me (wcl_app.character_pages in lgriffin/warcraftlogs_project, contract in its
 * guides/character_pages.md): each raid's headline number for the role played against the raid's median for that
 * role, the character's lineage, personal bests and a chart per role. Numbers arrive formatted (`display`), so the
 * only arithmetic here is how far a raid sat from its median.
 */

import { call, type Fetch } from './api';
import type { ChartPayload } from './charts';

export type Role = 'healer' | 'tank' | 'melee' | 'ranged';

export interface CharacterRaid {
  report_id: string;
  title: string;
  zone: string;
  raid_date: string;
  /** 0 is Monday; null when the date cannot be read. */
  weekday: number | null;
  role: Role;
  /** "Healing", "Damage" or "Damage taken". */
  metric: string;
  value: number;
  display: string;
  /** The median of everyone in the raid in the same role; null when unknown. */
  median: number | null;
  median_display: string;
  /** Place in the role (1 is the most) and how many played it; 0 when unknown, and always for tanks. */
  rank: number;
  of: number;
  /** Overheal % for a healer, mitigation % for a tank. */
  percent: number | null;
}

/** wcl_app.lineage Spread: a number's lowest, mean and highest across the character's raids. */
export interface Spread {
  name: string;
  min: number;
  mean: number;
  max: number;
  raids: number;
  total: number;
  /** The role whose raids the spread covers; "" for every raid. */
  role: string;
  raids_used: number;
}

export interface PersonalBest {
  metric: string;
  role: string;
  value: number;
  display: string;
  report_id: string;
  raid_date: string;
}

export interface CharacterPage {
  version: number;
  name: string;
  player_class: string;
  raids: number;
  first_raid: string | null;
  last_raid: string | null;
  role_counts: Record<string, number>;
  /** Newest first. */
  recent: CharacterRaid[];
  metrics: Spread[];
  casts: Spread[];
  consumables: Spread[];
  bests: PersonalBest[];
  charts: ChartPayload[];
}

export interface MyCharacterPage {
  /** Null until the worker has published. */
  generated_at: string | null;
  /** Null when none of the member's characters has raided with the guild. */
  page: CharacterPage | null;
  matched_by: 'chosen' | 'claim' | 'nickname' | null;
  /** The characters looked for, best first. */
  looked_for: string[];
  /** The member's characters that have a page, best first: their main leads. */
  characters: string[];
  /** Their main character, whether or not it has a page; null before they hold an approved claim. Older hubs omit it. */
  main?: string | null;
}

/** REQ-HUB-ME-004: below this many raids, Me says the history is building instead of drawing trend lines. */
export const MIN_TREND_RAIDS = 3;

export const ROLE_NAMES: Record<Role, string> = { healer: 'Healer', tank: 'Tank', melee: 'Melee', ranged: 'Ranged' };

/** The member's main character's page, or `name`'s when it is one of theirs. */
export const myCharacterPage = (name: string | null = null, f: Fetch = fetch) =>
  call<MyCharacterPage>(f, `/api/me/character-page${name ? `?name=${encodeURIComponent(name)}` : ''}`);

/** Whether the page has enough raids for trend lines. */
export const showTrends = (page: CharacterPage): boolean => page.raids >= MIN_TREND_RAIDS;

/**
 * How far the raid sat from its median, in whole percent ("+12%", "-3%"); "" when there is no median. For a tank
 * less damage taken reads as better, so `better` says which way is good rather than the sign.
 */
export function vsMedian(raid: CharacterRaid): { label: string; better: boolean } | null {
  if (raid.median === null || raid.median <= 0) return null;
  const diff = Math.round(((raid.value - raid.median) / raid.median) * 100);
  return { label: `${diff >= 0 ? '+' : ''}${diff}%`, better: raid.role === 'tank' ? diff <= 0 : diff >= 0 };
}

/** "3rd of 6" for a raid's place in its role; "" when unknown. */
export function placeLabel(raid: CharacterRaid): string {
  if (!raid.rank || !raid.of) return '';
  const n = raid.rank;
  const teen = n % 100 >= 11 && n % 100 <= 13;
  const suffix = teen ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th';
  return `${n}${suffix} of ${raid.of}`;
}

/** "Healer 12 · Ranged 3", most played first. */
export function rolesLabel(counts: Record<string, number>): string {
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([role, n]) => `${ROLE_NAMES[role as Role] ?? role} ${n}`)
    .join(' · ');
}

/** The lineage's 1-or-0 per raid metric (wcl_app.lineage.FLASK_METRIC): its mean is the share of raids. */
export const FLASK_METRIC = 'Flask or elixir pair';

/** A Spread number as the analyzer writes them (12.3M, 4.5K, 950), a percentage metric with its %, and the flask
 * metric as the share of raids. */
export function spreadValue(spread: Spread, value: number): string {
  if (spread.name === FLASK_METRIC) return `${Math.round(value * 100)}%`;
  if (spread.name.endsWith('%')) return `${value.toFixed(1)}%`;
  const abs = Math.abs(value);
  for (const [size, suffix] of [[1_000_000_000, 'B'], [1_000_000, 'M'], [1_000, 'K']] as const) {
    if (abs >= size) return `${(value / size).toFixed(1)}${suffix}`;
  }
  return Math.round(value).toLocaleString('en-GB');
}

/** A member's own line on a raid's log page: which of their characters was in it, and how that raid went. */
export interface MyRaidLine {
  name: string;
  raid: CharacterRaid;
}

/** How many of a member's other characters the log page looks through after their main. */
export const RAID_LINE_LOOKUPS = 3;

/**
 * Find the member's character in the raid `report`: their main's page first, then up to RAID_LINE_LOOKUPS of their
 * other characters. Null when none of them was there, or the pages are not published yet.
 */
export async function myRaidLine(
  report: string,
  load: (name: string | null) => Promise<MyCharacterPage>
): Promise<MyRaidLine | null> {
  const first = await load(null);
  const found = (mine: MyCharacterPage) => {
    const raid = mine.page?.recent.find((r) => r.report_id === report);
    return raid && mine.page ? { name: mine.page.name, raid } : null;
  };
  const hit = found(first);
  if (hit || !first.page) return hit;
  for (const name of first.characters.filter((n) => n !== first.page?.name).slice(0, RAID_LINE_LOOKUPS)) {
    const line = found(await load(name));
    if (line) return line;
  }
  return null;
}
