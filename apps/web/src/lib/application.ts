/**
 * Recruit form: six questions and nothing personal (no age, email or real name).
 * The API re-validates everything and checks the applicant is still in the Toads Discord; this gives field-level
 * feedback before they send.
 */
import type { Role } from './mock/data';

export const ROLES: readonly Role[] = ['Tank', 'Healer', 'Melee', 'Ranged'];

/** Where applicants join the guild's Discord before they apply. The interview room opens there. */
export const DISCORD_INVITE = 'https://discord.gg/toads';

/** TBC Classic specs and the roles each can fill. */
export const CLASS_SPECS: Readonly<Record<string, Readonly<Record<string, readonly Role[]>>>> = {
  Druid: { Balance: ['Ranged'], Feral: ['Tank', 'Melee'], Restoration: ['Healer'] },
  Hunter: { 'Beast Mastery': ['Ranged'], Marksmanship: ['Ranged'], Survival: ['Ranged'] },
  Mage: { Arcane: ['Ranged'], Fire: ['Ranged'], Frost: ['Ranged'] },
  Paladin: { Holy: ['Healer'], Protection: ['Tank'], Retribution: ['Melee'] },
  Priest: { Discipline: ['Healer'], Holy: ['Healer'], Shadow: ['Ranged'] },
  Rogue: { Assassination: ['Melee'], Combat: ['Melee'], Subtlety: ['Melee'] },
  Shaman: { Elemental: ['Ranged'], Enhancement: ['Melee'], Restoration: ['Healer'] },
  Warlock: { Affliction: ['Ranged'], Demonology: ['Ranged'], Destruction: ['Ranged'] },
  Warrior: { Arms: ['Melee'], Fury: ['Melee'], Protection: ['Tank'] }
};

export const CLASSES = Object.keys(CLASS_SPECS);

/** A signed-out visitor's answers wait in this tab (sessionStorage) while they sign in with Discord. */
export const RECRUIT_DRAFT_KEY = 'toads:recruit-draft';

/** Signing out forgets the draft, so the next person at this browser tab doesn't see it. */
export function forgetRecruitDraft(): void {
  try {
    sessionStorage.removeItem(RECRUIT_DRAFT_KEY);
  } catch {
    // no storage, so no draft
  }
}

export const APPLICATION_LIMITS = { whyToads: 1000 } as const;

export interface ApplicationInput {
  characterName: string;
  className: string;
  primaryRole: string;
  /** Empty: no secondary role. */
  secondaryRole: string;
  whyToads: string;
  /** The raid night they apply for (a raid day id); its officers' interview panel meets them. */
  raidDay: string;
}

/** A night the recruit page offers, from GET /api/public/raid-nights. */
export interface RaidNight {
  id: string;
  name: string;
}

export type ApplicationField = keyof ApplicationInput;
export type ApplicationErrors = Partial<Record<ApplicationField, string>>;

export const EMPTY_APPLICATION: ApplicationInput = {
  characterName: '',
  className: '',
  primaryRole: '',
  secondaryRole: '',
  whyToads: '',
  raidDay: ''
};

/** Letters only (accented letters included), 2 to 12 of them, like the in-game rule. */
const NAME = /^\p{L}{2,12}$/u;

export function normaliseName(name: string): string {
  return name.trim().normalize('NFC');
}

/** The roles some spec of this class can raid as, in ROLES order. */
export function rolesForClass(className: string): Role[] {
  const specs = Object.hasOwn(CLASS_SPECS, className) ? CLASS_SPECS[className] : {};
  const roles = new Set(Object.values(specs).flat());
  return ROLES.filter((r) => roles.has(r));
}

/** "Tank, Melee or Healer" */
function orList(items: readonly string[]): string {
  return items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} or ${items.at(-1)}`;
}

function roleError(className: string, role: string): string | undefined {
  if (!ROLES.includes(role as Role)) return 'Pick a role from the list.';
  const fits = rolesForClass(className);
  if (fits.length && !fits.includes(role as Role)) return `${className}s raid as ${orList(fits)}.`;
  return undefined;
}

/** "Wednesday, Thursday and Sunday": the nights on offer, for the recruit page's copy. */
export function nightsList(nights: readonly RaidNight[]): string {
  const names = nights.map((n) => n.name);
  return names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`;
}

/** `nights` are the raid day ids on offer; with none (an older hub), the night is not asked. */
export function validateApplication(input: ApplicationInput, nights: readonly string[] = []): ApplicationErrors {
  const e: ApplicationErrors = {};
  const name = normaliseName(input.characterName ?? '');
  if (!name) e.characterName = 'Enter your main character’s name.';
  else if (!NAME.test(name)) e.characterName = 'Character names are 2 to 12 letters, with no digits or spaces.';

  if (!input.className) e.className = 'Pick your class.';
  else if (!Object.hasOwn(CLASS_SPECS, input.className)) e.className = 'Pick a class from the list.';

  if (!input.primaryRole) e.primaryRole = 'Pick the role you most want to raid as.';
  else {
    const err = roleError(input.className, input.primaryRole);
    if (err) e.primaryRole = err;
  }

  if (input.secondaryRole) {
    const err = roleError(input.className, input.secondaryRole);
    if (err) e.secondaryRole = err;
    else if (input.secondaryRole === input.primaryRole) e.secondaryRole = 'Pick a different role, or “No second role”.';
  }

  if (nights.length && !nights.includes(input.raidDay)) e.raidDay = 'Pick the night you want to raid.';

  const why = (input.whyToads ?? '').trim();
  if (!why) e.whyToads = 'Tell us a little about why you want to join.';
  else if (why.length > APPLICATION_LIMITS.whyToads) e.whyToads = `Keep this to ${APPLICATION_LIMITS.whyToads} characters.`;
  return e;
}

/** The body POST /api/applications takes. */
export function toApiBody(input: ApplicationInput) {
  return {
    character_name: normaliseName(input.characterName),
    class_name: input.className,
    role: input.primaryRole,
    secondary_role: input.secondaryRole || null,
    why_toads: input.whyToads.trim(),
    raid_days: input.raidDay ? [input.raidDay] : []
  };
}
