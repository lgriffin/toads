/**
 * The Raid page: one raid night's home on the hub. For now it says what is coming; capabilities plug in as they are
 * built. Members see their own team's night, officers get the officer desk for the nights they run, and super admins
 * see every night and switch between them (absences.ts `raidDaysOf`).
 */
import type { RaidDays } from './absences';

/** The toad standing in the Raid page's hero for a night. */
export function dayToad(day: string): string {
  return day === 'wed' ? 'days/wednesday-toad-badge' : day === 'sun' ? 'days/sunday-toad-badge' : 'ranks/member-badge';
}

/** The night the page opens on: the viewer's own team first, then the first they run, then the first they see. */
export function defaultDay(r: RaidDays): string {
  return r.teams.find((d) => r.days.includes(d)) ?? r.officerDays.find((d) => r.days.includes(d)) ?? r.days[0] ?? '';
}

export interface Planned {
  title: string;
  body: string;
}

/** What the Raid page is being built to hold. Only what the hub is being built to do; no dates. */
export const PLANNED: readonly Planned[] = [
  {
    title: 'Your role for the night',
    body: 'Your assignment from the officers’ Drive sheet, so you know your job before the pull timer starts.'
  },
  {
    title: 'Sign-ups and the bench',
    body: 'Who is in, who is benched and who is away, gathered from Discord and the absences members add on Me.'
  },
  {
    title: 'Prep for the night',
    body: 'The bosses, the consumables we ask for and the strategy notes, in one place.'
  }
];
