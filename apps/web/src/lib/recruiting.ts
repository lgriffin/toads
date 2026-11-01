/**
 * Recruitment needs (docs/recruitment.md "Recruitment needs"): each raid night's officers list the primary specs the
 * night is recruiting, on Officers > Recruitment, and the homepage shows a visitor the night they pick. A group (tanks,
 * healers, damage) with nothing listed for the night reads "Full for now". The officers' routes are under
 * /api/days/{day}/admin and only that night's officers (and the global tier) may call them; the homepage reads every
 * night's needs at once from /api/public/recruitment.
 */
import { ApiError, call, type Fetch } from './api';
import { CLASSES, SPECS, classOf, type Spec } from './comp';
import type { NeedPriority, RecruitmentNeed } from './community';
import { raidNight } from './nights';

export interface NightNeed {
  /** The comp builder's spec id, such as "shaman-restoration". */
  spec_id: string;
  class_name: string;
  spec: string;
  role: 'Tank' | 'Healer' | 'Melee' | 'Ranged';
  priority: NeedPriority;
}

export interface NightNeeds {
  raid_day: string;
  needs: NightNeed[];
}

export interface NeedPick {
  spec_id: string;
  priority: NeedPriority;
}

export const PRIORITIES: readonly { id: NeedPriority; label: string }[] = [
  { id: 'high', label: 'High' },
  { id: 'medium', label: 'Medium' },
  { id: 'low', label: 'Low' }
];

/** What the officers' card talks to: the hub, or the preview's in-browser fake. */
export interface NeedsBackend {
  needs(day: string): Promise<NightNeeds>;
  save(day: string, picks: NeedPick[]): Promise<NightNeeds>;
}

const path = (day: string) => `/api/days/${encodeURIComponent(day)}/admin/recruitment-needs`;

export function hubNeeds(f: Fetch = fetch): NeedsBackend {
  return {
    needs: (day) => call<NightNeeds>(f, path(day)),
    save: (day, picks) => call<NightNeeds>(f, path(day), { method: 'PUT', body: JSON.stringify({ needs: picks }) })
  };
}

/** "Restoration Shaman": how players say a spec. */
export function specLabel(spec: Spec): string {
  return `${spec.name} ${classOf(spec.wowClass)?.name ?? spec.wowClass}`;
}

/** The night's list as the picks to save back. */
export const picksOf = (needs: readonly NightNeed[]): NeedPick[] =>
  needs.map((n) => ({ spec_id: n.spec_id, priority: n.priority }));

/** The specs an officer can still add, in catalogue order. */
export function specsLeft(needs: readonly NightNeed[]): Spec[] {
  const listed = new Set(needs.map((n) => n.spec_id));
  return SPECS.filter((s) => !listed.has(s.id));
}

/**
 * The spec an officer typed or picked: its full label ("Restoration Shaman", any case), or text that matches only one
 * spec left ("resto sha", "guardian"). Undefined when it matches none or several.
 */
export function findSpec(typed: string, choices: readonly Spec[]): Spec | undefined {
  const words = typed.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return undefined;
  const label = words.join(' ');
  const exact = choices.find((s) => specLabel(s).toLowerCase() === label);
  if (exact) return exact;
  const hits = choices.filter((s) => {
    const parts = specLabel(s).toLowerCase().split(' ');
    return words.every((w) => parts.some((p) => p.startsWith(w)));
  });
  return hits.length === 1 ? hits[0] : undefined;
}

/** What to tell an officer when a needs call fails. */
export function needsError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to change what this night is recruiting.';
    case 403:
      return 'Only this raid night’s officers can change what it recruits.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}

// ------------------------------------------------------------------------------------------------- the homepage

export type GroupId = 'tank' | 'healer' | 'damage';

export interface NeedGroup {
  id: GroupId;
  title: string;
  /** False when the night's officers listed nothing for the group: the homepage says "Full for now". */
  open: boolean;
  /** By class, in the order the officers listed them, each with its specs. */
  classes: { name: string; colour: string; specs: { name: string; priority: NeedPriority }[] }[];
}

const GROUPS: readonly { id: GroupId; title: string; roles: readonly RecruitmentNeed['role'][] }[] = [
  { id: 'tank', title: 'Tanks', roles: ['Tank'] },
  { id: 'healer', title: 'Healers', roles: ['Healer'] },
  { id: 'damage', title: 'Damage', roles: ['Melee', 'Ranged'] }
];

/** Whether a need is for this night. The hub sends night ids ("wed"); the preview's samples use names. */
const forNight = (need: RecruitmentNeed, night: string) =>
  need.raidDays.some((d) => (raidNight(d)?.id ?? d) === night);

/** One night's needs as the homepage's three groups. */
export function nightGroups(needs: readonly RecruitmentNeed[], night: string): NeedGroup[] {
  const tonight = needs.filter((n) => forNight(n, night));
  return GROUPS.map(({ id, title, roles }) => {
    const classes: NeedGroup['classes'] = [];
    for (const n of tonight.filter((x) => roles.includes(x.role))) {
      let c = classes.find((x) => x.name === n.className);
      if (!c) {
        const known = CLASSES.find((k) => k.name === n.className);
        c = { name: n.className, colour: known?.colour ?? 'currentColor', specs: [] };
        classes.push(c);
      }
      if (!c.specs.some((s) => s.name === n.spec)) c.specs.push({ name: n.spec, priority: n.priority });
    }
    return { id, title, open: classes.length > 0, classes };
  });
}

const WANTED: Record<GroupId, string> = { tank: 'tanks', healer: 'healers', damage: 'damage dealers' };

/** The line under the night picker: who the night wants, or that it is full. */
export function nightSummary(groups: readonly NeedGroup[], nightName: string): string {
  const open = groups.filter((g) => g.open).map((g) => WANTED[g.id]);
  if (!open.length) return `${nightName} is full for now. Apply anyway and the officers will keep you in mind.`;
  const list = open.length < 2 ? open[0] : `${open.slice(0, -1).join(', ')} and ${open[open.length - 1]}`;
  return `${nightName} is recruiting ${list}.`;
}
