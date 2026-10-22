/**
 * Professions (docs/professions.md): the professions each member lists on Me, and the members officers name as the
 * guild's crafters for a profession, the people the guild sends its top end recipes to. The catalogue matches the API's
 * `toads_api.professions.catalog` (test_professions.py keeps the two in step); ids are stored, so never rename one.
 */
import { ApiError, call, type Fetch } from './api';

export interface Profession {
  id: string;
  name: string;
  /** Cooking, First Aid and Fishing: they do not count against a character's two primary professions. */
  secondary: boolean;
  /** [id, name] of the specialisations a crafter may pick. */
  specialisations: [string, string][];
}

export const MAX_SKILL = 300;
export const NOTE_LIMIT = 200;

export const PROFESSIONS: Profession[] = [
  { id: 'alchemy', name: 'Alchemy', secondary: false, specialisations: [] },
  { id: 'blacksmithing', name: 'Blacksmithing', secondary: false, specialisations: [['armorsmith', 'Armorsmith'], ['weaponsmith', 'Weaponsmith'], ['axesmith', 'Master Axesmith'], ['hammersmith', 'Master Hammersmith'], ['swordsmith', 'Master Swordsmith']] },
  { id: 'enchanting', name: 'Enchanting', secondary: false, specialisations: [] },
  { id: 'engineering', name: 'Engineering', secondary: false, specialisations: [['gnomish', 'Gnomish'], ['goblin', 'Goblin']] },
  { id: 'leatherworking', name: 'Leatherworking', secondary: false, specialisations: [['dragonscale', 'Dragonscale'], ['elemental', 'Elemental'], ['tribal', 'Tribal']] },
  { id: 'tailoring', name: 'Tailoring', secondary: false, specialisations: [] },
  { id: 'herbalism', name: 'Herbalism', secondary: false, specialisations: [] },
  { id: 'mining', name: 'Mining', secondary: false, specialisations: [] },
  { id: 'skinning', name: 'Skinning', secondary: false, specialisations: [] },
  { id: 'cooking', name: 'Cooking', secondary: true, specialisations: [] },
  { id: 'first-aid', name: 'First Aid', secondary: true, specialisations: [] },
  { id: 'fishing', name: 'Fishing', secondary: true, specialisations: [] }
];

export const professionOf = (id: string) => PROFESSIONS.find((p) => p.id === id);
export const professionName = (id: string) => professionOf(id)?.name ?? id;

export interface HeldProfession {
  profession: string;
  skill: number | null;
  specialisation: string | null;
}

export interface Named {
  profession: string;
  note: string | null;
  designated_by: string | null;
  designated_at: string;
}

export interface MyProfessions {
  professions: HeldProfession[];
  crafter_for: Named[];
  /** On a save: professions the member was a guild crafter for and dropped, so that naming went. */
  unnamed?: string[];
}

export interface MemberProfessions {
  member_id: number;
  name: string;
  professions: HeldProfession[];
  crafter_for: Named[];
}

export interface Crafter {
  profession: string;
  member_id: number;
  member_name: string;
  skill: number | null;
  specialisation: string | null;
  note: string | null;
  designated_by: string | null;
  designated_at: string;
}

/** A guild crafter as a raid night's members see them on the Raid page: without who named them. */
export type NightCrafter = Pick<Crafter, 'profession' | 'member_id' | 'member_name' | 'skill' | 'specialisation' | 'note'>;

export interface Overview {
  members: MemberProfessions[];
  crafters: Crafter[];
}

/** "Engineering 300, Gnomish": what a member's line in a list says about one profession. */
export function describe(h: Pick<HeldProfession, 'profession' | 'skill' | 'specialisation'>): string {
  const p = professionOf(h.profession);
  const spec = h.specialisation ? p?.specialisations.find(([id]) => id === h.specialisation)?.[1] : undefined;
  return [p?.name ?? h.profession, h.skill ?? '', spec ? `· ${spec}` : ''].filter((x) => x !== '').join(' ');
}

/** Members who list a profession, for an officer's filter; everyone when `profession` is empty. */
export function withProfession(members: readonly MemberProfessions[], profession: string): MemberProfessions[] {
  return profession ? members.filter((m) => m.professions.some((h) => h.profession === profession)) : [...members];
}

/** The guild's crafters grouped by profession, in catalogue order, leaving out professions with nobody named. */
export function crafterGroups<C extends Pick<Crafter, 'profession'>>(
  crafters: readonly C[]
): { profession: Profession; crafters: C[] }[] {
  return PROFESSIONS.map((profession) => ({
    profession,
    crafters: crafters.filter((c) => c.profession === profession.id)
  })).filter((g) => g.crafters.length);
}

export const getMyProfessions = (f: Fetch = fetch) => call<MyProfessions>(f, '/api/me/professions');

export const saveMyProfessions = (professions: HeldProfession[], f: Fetch = fetch) =>
  call<MyProfessions>(f, '/api/me/professions', { method: 'PUT', body: JSON.stringify({ professions }) });

/** The guild's crafters on one raid night, for its Raid page. */
export const getNightCrafters = (day: string, f: Fetch = fetch) =>
  call<NightCrafter[]>(f, `/api/days/${encodeURIComponent(day)}/crafters`);

/** The officers' page reads and names through this, so the static preview can stand in for the hub. `day` null is
 * the guild-wide view, for global officers and super admins. */
export interface ProfessionsBackend {
  overview(day: string | null): Promise<Overview>;
  name(day: string | null, profession: string, memberId: number, note: string): Promise<Crafter>;
  unname(day: string | null, profession: string, memberId: number): Promise<void>;
}

const crafterPath = (day: string | null, profession: string, memberId: number) =>
  `${day === null ? '/api/admin' : `/api/days/${encodeURIComponent(day)}`}/crafters/${encodeURIComponent(profession)}/${memberId}`;

export function hubProfessions(f: Fetch = fetch): ProfessionsBackend {
  return {
    overview: (day) =>
      call<Overview>(f, day === null ? '/api/admin/professions' : `/api/days/${encodeURIComponent(day)}/professions`),
    name: (day, profession, memberId, note) =>
      call<Crafter>(f, crafterPath(day, profession, memberId), { method: 'PUT', body: JSON.stringify({ note: note || null }) }),
    unname: (day, profession, memberId) => call<void>(f, crafterPath(day, profession, memberId), { method: 'DELETE' })
  };
}

/** What to tell someone when a professions call fails. */
export function professionsError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to carry on.';
    case 403:
      return 'Only this raid night’s officers can do that.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
