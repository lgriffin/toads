/**
 * The preview's role badges: sample Discord roles and ties in the browser only, so the admin page works on GitHub
 * Pages with no hub behind it. Changes last until the page reloads.
 */
import { ApiError } from '$lib/api';
import { roleBadge, type DiscordRole, type RoleBadgeLink, type RoleBadgesBackend, ROLE_BADGES } from '$lib/role-badges';

const ROLES: DiscordRole[] = [
  { id: '1100000000000000001', name: 'Guild Master', colour: '#e0b04f' },
  { id: '1100000000000000002', name: 'Officer', colour: '#3fd6c8' },
  { id: '1100000000000000003', name: 'Wednesday Toads', colour: '#5aa9ff' },
  { id: '1100000000000000004', name: 'Sunday Toads', colour: '#ef8a45' },
  { id: '1100000000000000005', name: 'Tank', colour: '#4f7fd6' },
  { id: '1100000000000000006', name: 'Healer', colour: '#3fbf72' },
  { id: '1100000000000000007', name: 'DPS', colour: '#d9503f' },
  { id: '1100000000000000008', name: 'Trial', colour: null }
];

let links: RoleBadgeLink[] = [
  ['1100000000000000003', 'wednesday-toad'],
  ['1100000000000000004', 'sunday-toad'],
  ['1100000000000000006', 'healer']
].map(([role, badge]) => ({
  discord_role_id: role,
  role_name: ROLES.find((r) => r.id === role)?.name ?? '',
  badge: roleBadge(badge)!,
  added_at: '2026-10-19T18:00:00Z'
}));

/** The preview visitor's badges: they hold the Wednesday and Healer roles. */
export const PREVIEW_ROLE_BADGES = ['wednesday-toad', 'healer'];

export const previewRoleBadges: RoleBadgesBackend = {
  async load() {
    return { badges: [...ROLE_BADGES], links: [...links], roles: ROLES };
  },
  async tie(discordRoleId, badgeId) {
    const badge = roleBadge(badgeId);
    const role = ROLES.find((r) => r.id === discordRoleId);
    if (!badge) throw new ApiError(422, 'Unknown badge');
    if (!role) throw new ApiError(422, 'That role is not in the Toads server');
    if (links.some((l) => l.discord_role_id === discordRoleId && l.badge.id === badgeId)) {
      throw new ApiError(409, `That role already earns ${badge.name}`);
    }
    const link = {
      discord_role_id: role.id,
      role_name: role.name,
      badge,
      added_at: new Date().toISOString()
    };
    links = [...links, link];
    return link;
  },
  async untie(discordRoleId, badgeId) {
    const kept = links.filter((l) => !(l.discord_role_id === discordRoleId && l.badge.id === badgeId));
    if (kept.length === links.length) throw new ApiError(404, 'That role does not earn that badge');
    links = kept;
  }
};
