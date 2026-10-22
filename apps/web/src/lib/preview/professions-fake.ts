/**
 * The preview's professions: a few sample members and the guild's crafters, kept in the browser only, so the officers'
 * Professions page works on GitHub Pages with no hub behind it. Changes last until the page reloads.
 */
import { ApiError } from '$lib/api';
import type { Crafter, MemberProfessions, MyProfessions, NightCrafter, ProfessionsBackend } from '$lib/professions';

const AT = '2026-10-19T18:00:00Z';

/** Hopscotch's own professions on the preview's Me, named the guild's alchemist. */
export const previewMyProfessions: MyProfessions = {
  professions: [
    { profession: 'alchemy', skill: 300, specialisation: null },
    { profession: 'herbalism', skill: 300, specialisation: null },
    { profession: 'cooking', skill: 300, specialisation: null }
  ],
  crafter_for: [{ profession: 'alchemy', note: 'Flasks and Arcanite transmutes', designated_by: 'Hadur', designated_at: AT }]
};

const MEMBERS: (MemberProfessions & { nights: string[] })[] = [
  { member_id: 1, name: 'Hopscotch', nights: ['wed'], professions: previewMyProfessions.professions, crafter_for: [] },
  {
    member_id: 2,
    name: 'Lilypadd',
    nights: ['wed'],
    professions: [
      { profession: 'tailoring', skill: 300, specialisation: null },
      { profession: 'enchanting', skill: 300, specialisation: null }
    ],
    crafter_for: []
  },
  {
    member_id: 3,
    name: 'Ribbit',
    nights: ['sun'],
    professions: [
      { profession: 'blacksmithing', skill: 300, specialisation: 'hammersmith' },
      { profession: 'mining', skill: 300, specialisation: null }
    ],
    crafter_for: []
  },
  { member_id: 4, name: 'Tadpole', nights: ['wed', 'sun'], professions: [], crafter_for: [] }
];

export function previewProfessions(): ProfessionsBackend {
  let crafters: Crafter[] = [
    {
      profession: 'alchemy',
      member_id: 1,
      member_name: 'Hopscotch',
      skill: 300,
      specialisation: null,
      note: 'Flasks and Arcanite transmutes',
      designated_by: 'Hadur',
      designated_at: AT
    }
  ];
  const withNames = (m: MemberProfessions): MemberProfessions => ({
    member_id: m.member_id,
    name: m.name,
    professions: m.professions,
    crafter_for: crafters
      .filter((c) => c.member_id === m.member_id)
      .map((c) => ({ profession: c.profession, note: c.note, designated_by: c.designated_by, designated_at: c.designated_at }))
  });
  const reach = (day: string | null, memberId: number) => {
    const m = MEMBERS.find((x) => x.member_id === memberId);
    if (!m || (day !== null && !m.nights.includes(day))) throw new ApiError(404, 'They are not on this raid night');
    return m;
  };
  return {
    overview: async (day) => ({
      members: MEMBERS.filter((m) => (day === null ? m.professions.length : m.nights.includes(day))).map(withNames),
      crafters: [...crafters]
    }),
    name: async (day, profession, memberId, note) => {
      const m = reach(day, memberId);
      const held = m.professions.find((h) => h.profession === profession);
      if (!held) throw new ApiError(422, 'They do not list that profession on Me');
      const made: Crafter = {
        profession,
        member_id: m.member_id,
        member_name: m.name,
        skill: held.skill,
        specialisation: held.specialisation,
        note: note.trim() || null,
        designated_by: 'You',
        designated_at: new Date().toISOString()
      };
      crafters = [...crafters.filter((c) => !(c.profession === profession && c.member_id === memberId)), made];
      return made;
    },
    unname: async (day, profession, memberId) => {
      reach(day, memberId);
      if (!crafters.some((c) => c.profession === profession && c.member_id === memberId)) {
        throw new ApiError(404, 'They are not named for that profession');
      }
      crafters = crafters.filter((c) => !(c.profession === profession && c.member_id === memberId));
    }
  };
}

/** The Raid page's guild crafters for a night in the preview: Wednesday has two, Sunday one. */
export function previewNightCrafters(day: string): NightCrafter[] {
  const all: (NightCrafter & { night: string })[] = [
    { night: 'wed', profession: 'alchemy', member_id: 1, member_name: 'Hopscotch', skill: 300, specialisation: null, note: 'Flasks and transmutes' },
    { night: 'wed', profession: 'tailoring', member_id: 2, member_name: 'Lilypadd', skill: 300, specialisation: null, note: null },
    { night: 'sun', profession: 'blacksmithing', member_id: 3, member_name: 'Ribbit', skill: 300, specialisation: 'weaponsmith', note: 'Send Arcanite' }
  ];
  return all.filter((c) => c.night === day).map(({ night: _, ...c }) => c);
}
