/**
 * Role badges (docs/role-badges.md): badge toads members earn from the Discord roles they hold, such as the Wednesday
 * Toad, the Thursday Toad, the Sunday Toad, each night's Officer, Tank and Healer. A super admin ties each badge to a server role on the admin page; the hub
 * checks the roles. services/api/tests/test_role_badges.py fails if the hub's catalogue and this list drift apart.
 */
import { call, ApiError, type Fetch } from './api';

export interface RoleBadge {
  id: string;
  name: string;
  /** The artwork under static/logos/, without `.svg`; `-badge.svg` is the ringed badge. */
  file: string;
}

/** Every badge a super admin can tie to a role, in the hub's catalogue order. */
export const ROLE_BADGES: readonly RoleBadge[] = [
  { id: 'wednesday-toad', name: 'Wednesday Toad', file: 'days/wednesday-toad' },
  { id: 'thursday-toad', name: 'Thursday Toad', file: 'days/thursday-toad' },
  { id: 'sunday-toad', name: 'Sunday Toad', file: 'days/sunday-toad' },
  { id: 'wednesday-officer', name: 'Wednesday Officer', file: 'ranks/officer' },
  { id: 'thursday-officer', name: 'Thursday Officer', file: 'ranks/officer' },
  { id: 'sunday-officer', name: 'Sunday Officer', file: 'ranks/officer' },
  { id: 'tank', name: 'Tank', file: 'roles/tank' },
  { id: 'healer', name: 'Healer', file: 'roles/healer' },
  { id: 'damage', name: 'Damage', file: 'roles/damage' },
  { id: 'druid', name: 'Druid', file: 'classes/druid' },
  { id: 'hunter', name: 'Hunter', file: 'classes/hunter' },
  { id: 'mage', name: 'Mage', file: 'classes/mage' },
  { id: 'paladin', name: 'Paladin', file: 'classes/paladin' },
  { id: 'priest', name: 'Priest', file: 'classes/priest' },
  { id: 'rogue', name: 'Rogue', file: 'classes/rogue' },
  { id: 'shaman', name: 'Shaman', file: 'classes/shaman' },
  { id: 'warlock', name: 'Warlock', file: 'classes/warlock' },
  { id: 'warrior', name: 'Warrior', file: 'classes/warrior' }
];

/** How the admin page groups the catalogue. */
export const ROLE_BADGE_GROUPS: readonly {
  label: string;
  ids: readonly string[];
}[] = [
  { label: 'Raid nights', ids: ROLE_BADGES.filter((b) => b.file.startsWith('days/')).map((b) => b.id) },
  { label: 'Raid night officers', ids: ROLE_BADGES.filter((b) => b.id.endsWith('-officer')).map((b) => b.id) },
  { label: 'Raid roles', ids: ['tank', 'healer', 'damage'] },
  { label: 'Classes', ids: ROLE_BADGES.filter((b) => b.file.startsWith('classes/')).map((b) => b.id) }
];

const BY_ID = new Map(ROLE_BADGES.map((b) => [b.id, b]));

export function roleBadge(id: string): RoleBadge | undefined {
  return BY_ID.get(id);
}

/** A Discord role a member can hold. Ids are strings: they exceed Number.MAX_SAFE_INTEGER. */
export interface DiscordRole {
  id: string;
  name: string;
  /** "#rrggbb", or null for a role without a colour. */
  colour: string | null;
}

export interface RoleBadgeLink {
  discord_role_id: string;
  role_name: string;
  badge: RoleBadge;
  added_at: string;
}

/** GET /api/admin/role-badges. `roles` is null while Discord is not answering. */
export interface RoleBadgesAdmin {
  badges: RoleBadge[];
  links: RoleBadgeLink[];
  roles: DiscordRole[] | null;
}

/** Sent on window after a tie changes, so the header and greeting fetch the viewer's badges again. */
export const ROLE_BADGES_CHANGED = 'toads:role-badges-changed';

export const myRoleBadges = (f: Fetch = fetch) => call<RoleBadge[]>(f, '/api/me/role-badges');

/** Where the admin page reads and writes: the hub, or the preview's sample data. */
export interface RoleBadgesBackend {
  load(): Promise<RoleBadgesAdmin>;
  tie(discordRoleId: string, badgeId: string): Promise<RoleBadgeLink>;
  untie(discordRoleId: string, badgeId: string): Promise<void>;
}

export const hubRoleBadges = (f: Fetch = fetch): RoleBadgesBackend => ({
  load: () => call<RoleBadgesAdmin>(f, '/api/admin/role-badges'),
  tie: (discordRoleId, badgeId) =>
    call<RoleBadgeLink>(f, '/api/admin/role-badges', {
      method: 'POST',
      body: JSON.stringify({
        discord_role_id: discordRoleId,
        badge_id: badgeId
      })
    }),
  untie: (discordRoleId, badgeId) =>
    call<void>(f, `/api/admin/role-badges/${encodeURIComponent(discordRoleId)}/${encodeURIComponent(badgeId)}`, {
      method: 'DELETE'
    })
});

/** The roles tied to each badge, in catalogue order, for the admin page's list. */
export function linksByBadge(links: readonly RoleBadgeLink[]): { badge: RoleBadge; roles: RoleBadgeLink[] }[] {
  return ROLE_BADGES.map((badge) => ({
    badge,
    roles: links.filter((l) => l.badge.id === badge.id)
  })).filter((g) => g.roles.length > 0);
}

/** What to tell a super admin when tying or untying fails. */
export function roleBadgeError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  if (e.status === 401) return 'Sign in with Discord first.';
  if (e.status === 403) return 'Only super admins tie badges to Discord roles.';
  if (e.status === 503) return 'Discord is not answering just now; try again in a minute.';
  return e.message || 'Something went wrong; try again.';
}
