/**
 * Officer grants (docs/admin.md "Officer grants"): a super admin makes one Discord member an officer of a raid night,
 * or of every night (a global officer), on top of their Discord roles. Nothing here makes anyone a super admin; those
 * are named in the hub's configuration alone. The hub's routes are under /api/admin/officer-grants and only super
 * admins may call them (manage_officer_grants).
 */
import { ApiError, call, type Fetch } from './api';

export interface DiscordMember {
  /** A string: Discord ids are past the largest integer a browser holds exactly. */
  discord_user_id: string;
  username: string;
  display_name: string;
}

export interface OfficerGrant extends DiscordMember {
  id: number;
  /** null: every night, a global officer. */
  raid_day: string | null;
  granted_by_name: string | null;
  granted_at: string;
}

export interface RaidDay {
  id: string;
  name: string;
}

export interface OfficerGrants {
  grants: OfficerGrant[];
  raid_days: RaidDay[];
}

/** What the admin desk talks to: the hub, or the preview's in-browser fake. */
export interface OfficerGrantBackend {
  load(): Promise<OfficerGrants>;
  search(q: string): Promise<DiscordMember[]>;
  grant(discordUserId: string, raidDay: string | null): Promise<OfficerGrant>;
  revoke(id: number): Promise<void>;
}

const BASE = '/api/admin/officer-grants';

export function hubOfficerGrants(f: Fetch = fetch): OfficerGrantBackend {
  return {
    load: () => call<OfficerGrants>(f, BASE),
    search: (q) => call<DiscordMember[]>(f, `${BASE}/discord-members?q=${encodeURIComponent(q)}`),
    grant: (id, raidDay) =>
      call<OfficerGrant>(f, BASE, { method: 'POST', body: JSON.stringify({ discord_user_id: id, raid_day: raidDay }) }),
    revoke: (id) => call<void>(f, `${BASE}/${id}`, { method: 'DELETE' })
  };
}

/** What a grant makes its holder, in words: "Sunday officer" or "Global officer". */
export function grantLabel(raidDay: string | null, days: readonly RaidDay[]): string {
  if (raidDay === null) return 'Global officer';
  return `${days.find((d) => d.id === raidDay)?.name ?? raidDay} officer`;
}

/** The same inside a sentence: "a Sunday officer" or "a global officer". */
export function grantPhrase(raidDay: string | null, days: readonly RaidDay[]): string {
  return raidDay === null ? 'a global officer' : `a ${grantLabel(raidDay, days)}`;
}

/** The grants grouped by member, members in the order they were first granted. */
export function byMember(grants: readonly OfficerGrant[]): { member: DiscordMember; grants: OfficerGrant[] }[] {
  const groups = new Map<string, { member: DiscordMember; grants: OfficerGrant[] }>();
  for (const g of grants) {
    const group = groups.get(g.discord_user_id);
    if (group) group.grants.push(g);
    else groups.set(g.discord_user_id, { member: g, grants: [g] });
  }
  return [...groups.values()];
}

/** Whether a member already holds this grant: the desk greys the button out. */
export function holds(grants: readonly OfficerGrant[], discordUserId: string, raidDay: string | null): boolean {
  return grants.some((g) => g.discord_user_id === discordUserId && g.raid_day === raidDay);
}

/** What to tell a super admin when a grant call fails. */
export function officerGrantError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to change officer grants.';
    case 403:
      return 'Only super admins grant officer powers.';
    case 503:
      return 'Discord is not answering; try again shortly.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
