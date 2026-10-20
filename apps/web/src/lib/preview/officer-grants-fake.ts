/**
 * The preview's officer grants: a few sample Discord members to search, and grants kept in the browser only, so the
 * admin page works on GitHub Pages with no hub behind it. Changes last until the page reloads.
 */
import { ApiError } from '$lib/api';
import type { DiscordMember, OfficerGrant, OfficerGrantBackend, RaidDay } from '$lib/officer-grants';

const MEMBERS: DiscordMember[] = [
  ['301', '_gallagher', 'Gallagher'],
  ['303', 'hopscotch', 'Hopscotch'],
  ['304', 'lilypadd', 'Lilypadd'],
  ['305', 'ribbit', 'Ribbit'],
  ['306', 'tadpole', 'Tadpole']
].map(([discord_user_id, username, display_name]) => ({ discord_user_id, username, display_name }));

const DAYS: RaidDay[] = [
  { id: 'wed', name: 'Wednesday' },
  { id: 'thu', name: 'Thursday' },
  { id: 'sun', name: 'Sunday' }
];

export function previewOfficerGrants(): OfficerGrantBackend {
  let next = 2;
  let grants: OfficerGrant[] = [
    { id: 1, ...MEMBERS[2], raid_day: 'sun', granted_by_name: 'Hadur', granted_at: '2026-10-19T18:00:00Z' }
  ];
  return {
    load: async () => ({ grants: [...grants], raid_days: DAYS }),
    search: async (q) => {
      const query = q.trim().toLowerCase();
      return MEMBERS.filter((m) => m.username.startsWith(query) || m.display_name.toLowerCase().startsWith(query));
    },
    grant: async (id, raidDay) => {
      const who = MEMBERS.find((m) => m.discord_user_id === id);
      if (!who) throw new ApiError(422, 'They are not in the Toads Discord');
      const held = grants.find((g) => g.discord_user_id === id && g.raid_day === raidDay);
      if (held) return held;
      const made = { id: next++, ...who, raid_day: raidDay, granted_by_name: 'You', granted_at: new Date().toISOString() };
      grants = [...grants, made];
      return made;
    },
    revoke: async (id) => {
      if (!grants.some((g) => g.id === id)) throw new ApiError(404, 'No such officer grant');
      grants = grants.filter((g) => g.id !== id);
    }
  };
}
