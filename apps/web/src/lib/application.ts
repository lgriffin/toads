/**
 * Recruit form validation. We only ask what the officers need: no age, email or real name.
 * The API re-validates everything; this gives applicants field-level feedback before they send.
 */
import type { RaidDay, Role } from './mock/data';

export const ROLES: readonly Role[] = ['Tank', 'Healer', 'Melee', 'Ranged'];
export const RAID_DAYS: readonly RaidDay[] = ['Wednesday', 'Sunday'];

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

export const APPLICATION_LIMITS = { experience: 1000, availability: 300, logsUrl: 300 } as const;

export const LOGS_HOSTS: readonly string[] = [
  'warcraftlogs.com',
  'www.warcraftlogs.com',
  'classic.warcraftlogs.com',
  'fresh.warcraftlogs.com',
  'sod.warcraftlogs.com'
];

export interface ApplicationInput {
  characterName: string;
  className: string;
  spec: string;
  role: string;
  raidDays: string[];
  experience: string;
  availability: string;
  logsUrl: string;
}

export type ApplicationField = keyof ApplicationInput;
export type ApplicationErrors = Partial<Record<ApplicationField, string>>;

export const EMPTY_APPLICATION: ApplicationInput = {
  characterName: '',
  className: '',
  spec: '',
  role: '',
  raidDays: [],
  experience: '',
  availability: '',
  logsUrl: ''
};

/** Letters only (accented letters included), 2 to 12 of them, like the in-game rule. */
const NAME = /^\p{L}{2,12}$/u;

export function normaliseName(name: string): string {
  return name.trim().normalize('NFC');
}

export function isValidLogsUrl(value: string): boolean {
  if (value.length > APPLICATION_LIMITS.logsUrl) return false;
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return false;
  }
  return (
    url.protocol === 'https:' &&
    !url.port &&
    // No userinfo: the href must start with the bare https origin.
    url.href.startsWith(`https://${url.hostname}/`) &&
    LOGS_HOSTS.includes(url.hostname.toLowerCase())
  );
}

export function specsFor(className: string): string[] {
  return Object.keys(CLASS_SPECS[className] ?? {});
}

export function rolesFor(className: string, spec: string): Role[] {
  return [...(CLASS_SPECS[className]?.[spec] ?? [])];
}

export function validateApplication(input: ApplicationInput): ApplicationErrors {
  const e: ApplicationErrors = {};
  const name = normaliseName(input.characterName ?? '');
  if (!name) e.characterName = 'Enter your main character’s name.';
  else if (!NAME.test(name)) e.characterName = 'Character names are 2 to 12 letters, with no digits or spaces.';

  if (!input.className) e.className = 'Pick your class.';
  else if (!Object.hasOwn(CLASS_SPECS, input.className)) e.className = 'Pick a class from the list.';

  const specs = CLASS_SPECS[input.className];
  if (!input.spec) e.spec = 'Pick your spec.';
  else if (specs && !Object.hasOwn(specs, input.spec)) e.spec = `Pick a ${input.className} spec from the list.`;

  if (!input.role) e.role = 'Pick the role you want to raid as.';
  else if (!ROLES.includes(input.role as Role)) e.role = 'Pick a role from the list.';
  else if (specs && Object.hasOwn(specs, input.spec) && !specs[input.spec].includes(input.role as Role))
    e.role = `${input.spec} ${input.className}s raid as ${specs[input.spec].join(' or ')}.`;

  if (!Array.isArray(input.raidDays) || input.raidDays.some((d) => !RAID_DAYS.includes(d as RaidDay)))
    e.raidDays = 'Pick Wednesday, Sunday or both.';

  if ((input.experience ?? '').trim().length > APPLICATION_LIMITS.experience)
    e.experience = `Keep this to ${APPLICATION_LIMITS.experience} characters.`;
  if ((input.availability ?? '').trim().length > APPLICATION_LIMITS.availability)
    e.availability = `Keep this to ${APPLICATION_LIMITS.availability} characters.`;

  const logs = (input.logsUrl ?? '').trim();
  if (logs && !isValidLogsUrl(logs))
    e.logsUrl = 'Paste an https link to your Warcraft Logs character or report page.';
  return e;
}
