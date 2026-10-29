/**
 * The public landing page's copy: who the guild is and what it stands for. It is site text, not data, so the same
 * words show in the static preview and on the live hub. Officers edit it here, in a PR.
 */

import { CLASSES, CLASS_SPECS } from './application';
import type { Role } from './mock/data';
import { NIGHTS_IN_WORDS, TEAM_COUNT } from './nights';
import { FOREVER_LAUNCH, FOREVER_LIVE } from './launch';

export interface Value {
  title: string;
  body: string;
}

export const LANDING = {
  guild: 'Toads',
  tagline: 'A very social guild that locks in on raid night, on the EU PvP side of WoW Forever. Horde, one big pond.',
  schedule: `${TEAM_COUNT} 40-man teams, ${NIGHTS_IN_WORDS}, 21:00 to midnight server time`,
  who: [
    'We are a very social guild that locks into raiding with a focus on speed and execution. We don’t stack classes: we bring a balanced raid group, and our players step up with consumes and the level of play we expect. We have done this from Classic Fresh to TBC, and now Forever awaits us.',
    'Now we are taking the whole pond to World of Warcraft: Forever. Horde, PvP, EU: the same people, the same habits, a new continent to be unreasonably smug about.'
  ],
  values: [
    {
      title: 'People before parses',
      body: 'We want players who turn up, prepare and help each other. A bad night is something we fix together, not a reason to blame someone.'
    },
    {
      title: 'Prepared, not sweaty',
      body: 'Consumes, gear and tactics are expected on raid night, and the hub shows everyone the same numbers. You raid one night a week with your group; raiding with both is your choice.'
    },
    {
      title: 'Boring, fair loot',
      body: 'Our Loot Council looks at each role and weighs the mega drops across the whole raid. Every call is made in the open, with each raid day’s loot tables public on thatsmybis.com.'
    },
    {
      title: 'Open doors',
      body: 'Anyone can apply, and every applicant gets a private interview room with the officers on Discord. Trials are told where they stand.'
    }
  ] satisfies Value[]
};

export interface Recruiting {
  id: 'healer' | 'damage' | 'tank';
  title: string;
  open: boolean;
  /** One line under the status. */
  note: string;
  /** Classes (with the specs that fill the role) we are looking for; empty when the role is full. */
  classes: { name: string; specs: string[] }[];
}

/** The roles of a spec list in the order the page shows them. */
function classesFor(roles: readonly Role[]): { name: string; specs: string[] }[] {
  return CLASSES.map((name) => ({
    name,
    specs: Object.entries(CLASS_SPECS[name])
      .filter(([, r]) => r.some((x) => roles.includes(x)))
      .map(([spec]) => spec)
  })).filter((c) => c.specs.length > 0);
}

/**
 * What we are recruiting right now. Officers change `open` here, in a PR, when a role fills or a spot comes up. The
 * classes follow application.ts, so the page and the application form always agree on who can fill a role.
 */
export const RECRUITING: readonly Recruiting[] = [
  {
    id: 'healer',
    title: 'Healers',
    open: true,
    note: 'We are recruiting healers. Every class that heals is welcome.',
    classes: classesFor(['Healer'])
  },
  {
    id: 'damage',
    title: 'Damage',
    open: true,
    note: 'We are recruiting damage dealers, melee and ranged, of every class.',
    classes: classesFor(['Melee', 'Ranged'])
  },
  {
    id: 'tank',
    title: 'Tanks',
    open: false,
    note: 'Full for now. This page changes when a spot opens.',
    classes: []
  }
];

export const SOCIAL = {
  title: 'More pond than raid',
  intro:
    'We run multiple raid groups, each aiming to clear all the relevant content in one night, and only stretching to two when it is new, challenging content. We come zoned in to make that happen. The rest of the pond is Discord: tactics, jokes, highlight reels and the odd world PvP dogpile.',
  points: [
    { title: 'Always someone about', body: 'Discord is where the guild lives between raids, from gearing questions to who is up for a dungeon run.' },
    { title: 'Seen and celebrated', body: 'Officers publish highlight reels and member spotlights to the hub and Discord, with the member’s say-so.' },
    { title: 'Looked after', body: 'Every applicant gets a private interview room with the officers, and trials are told where they stand.' }
  ]
};

export interface Home {
  /** Also the id of the section. */
  id: 'forever' | 'tbc';
  title: string;
  status: string;
  /** Faction and mode, as the guild plays it. */
  line: string;
  body: string;
  logo: { src: string; alt: string };
}

/**
 * Where the guild plays. The official logos are Blizzard's: download them from the press kit (see
 * https://blizzard.gamespress.com/World-of-Warcraft-Forever-Classic) and save them under apps/web/static/brand/ with
 * the file names below. Until they are there the section shows the game's name only.
 */
export const HOMES: readonly Home[] = [
  {
    id: 'forever',
    title: 'World of Warcraft: Forever',
    status: FOREVER_LIVE ? `Live since ${FOREVER_LAUNCH.label}` : `Launching ${FOREVER_LAUNCH.label}`,
    line: 'Horde · PvP · EU',
    body: `Our new home. We are rolling together on the PvP side in the EU region, raiding as a guild and defending the pond in the open world. ${
      FOREVER_LIVE ? 'Come and find us, and tell us who you are bringing.' : 'Reserve your names early and tell us who you are bringing.'
    }`,
    logo: { src: 'brand/wow-forever.png', alt: 'World of Warcraft: Forever' }
  },
  {
    id: 'tbc',
    title: 'Burning Crusade Classic',
    status: 'Active now',
    line: 'Alliance · Spineshatter · EU',
    body: 'The first pond is still full. Our Alliance team keeps raiding TBC Classic on Spineshatter, and its raids, logs and bank are what the hub was built for.',
    logo: {
      src: 'brand/tbc-anniversary.png',
      alt: 'World of Warcraft: Burning Crusade Classic Anniversary Edition'
    }
  }
];

/**
 * How a Toads raid night works: the model behind the hub's numbers, shown to visitors before they apply. Each pillar
 * says what we expect, how it is measured and what a member sees once signed in. Officers edit it here, in a PR.
 */
export interface Pillar {
  /** Also the anchor on /how-we-raid. */
  id: 'prep' | 'flasks' | 'consumes' | 'speed' | 'loot' | 'standard';
  title: string;
  approach: string;
  measure: string;
  youSee: string;
}


/** The full write-up on /how-we-raid. */
export const MODEL: readonly Pillar[] = [
  {
    id: 'prep',
    title: 'Prep',
    approach:
      'Arrive enchanted, gemmed and repaired, with your addons up to date and your role for the raid understood. Flasks, elixirs, potions and every other consume are expected, and expected to be used in volume.',
    measure: 'The CBA raid sheet’s gear check counts missing enchants and gems for every raid.',
    youSee: 'The raid’s gear check in the raid totals on the hub.'
  },
  {
    id: 'flasks',
    title: 'Flasks and elixirs',
    approach:
      'A flask, or a battle and guardian elixir pair, on every progression pull. The guild bank will aim to support the team, especially early in Forever; as we mature, this should become less of a challenge.',
    measure: 'The CBA raid sheet records buff consumable uptime on bosses and flags anyone under 80%.',
    youSee: 'The raid’s consumable uptime on the hub, and a bank request for anything you are short of.'
  },
  {
    id: 'consumes',
    title: 'Consumes',
    approach:
      'Potions on cooldown, runes for mana users, and sappers, oils and scrolls wherever a fight allows them. Professions play a large part: as a raid group we may all opt for one profession, as with Engineering in Classic Fresh.',
    measure: 'The analyzer counts every use from the combat log; the raid sheets total them per raid.',
    youSee: 'The raid’s consumable totals on the hub.'
  },
  {
    id: 'speed',
    title: 'Speed',
    approach:
      'Clean pulls and short breaks. Understand the trash pulls and your role in keeping them quick. Speed is what pushes us as a group to progress at pace and challenge ourselves.',
    measure: 'Clear times per zone from the CBA raid sheet, and each raid’s length from the analyzer.',
    youSee: 'Each raid’s clear times in the raid totals on the hub.'
  },
  {
    id: 'loot',
    title: 'Loot Council',
    approach:
      'We have a Loot Council to keep loot distribution fair across the whole group. It looks at each role, and weighs the mega drops across the whole raid.',
    measure: 'Attendance, performance, consumes and guild presence.',
    youSee: 'Each raid day’s loot tables, public on thatsmybis.com, so everyone knows the drop order.'
  },
  {
    id: 'standard',
    title: 'Measured against ourselves',
    approach:
      'There is no number to hit. Each role is compared week on week with its own average over the four raided weeks before it, to help the whole group and to help you as a player. We don’t chase parses, but we support and encourage those who want to, and our composition and consumes will back them.',
    measure: 'The analyzer’s numbers per raid and per character, week on week, and each player’s role number in every raid.',
    youSee: 'The week-on-week charts and your performance against the median for your role, both on the hub.'
  }
];

export interface HomePillar {
  /** The /how-we-raid anchor it links to. */
  id: Pillar['id'];
  title: string;
  summary: string;
}

/** The homepage's short version: a line each, linking to the full write-up. */
export const HOME_PILLARS: readonly HomePillar[] = [
  { id: 'prep', title: 'Prep', summary: 'Enchanted, repaired, addons up to date and your role for the raid understood.' },
  {
    id: 'flasks',
    title: 'Flasks and consumes',
    summary: 'A flask or elixir pair on every progression pull, potions on cooldown and every consume used in volume.'
  },
  { id: 'speed', title: 'Speed', summary: 'Understand the trash pulls and your role in helping us clear fast.' },
  {
    id: 'standard',
    title: 'Measured against ourselves',
    summary: 'Each week against our own last four raids. No targets.'
  }
];

/** How the raid teams work, on /how-we-raid. */
export const RAID_TEAMS: readonly string[] = [
  `We are aiming for ${TEAM_COUNT} 40-man raiding teams, one each on ${NIGHTS_IN_WORDS}. All the teams work as one to support each other, with alts helping out where possible to cover life events.`,
  `We do not expect 100% attendance. We recognise life happens, and with ${TEAM_COUNT} raid teams we can bench and rotate as needed.`,
  'Discord provides our support, our tactics and our strategy, and our raid leaders on the night drive it home.'
];

export interface AppTile {
  title: string;
  body: string;
}

/** The three things every raider gets once they sign in. */
export const MEMBER_APPS: readonly AppTile[] = [
  {
    title: 'Raid analyzer',
    body: 'Raid totals and week-on-week charts on the hub, and your number against the median for your role. Every log broken down in the Windows app.'
  },
  { title: 'Guild bank', body: 'Browse what the bank holds and request flasks, potions and mats for raid night.' },
  { title: 'Discord', body: 'Raid times, officer posts, highlight reels and the bank bot, joined up with the hub.' }
];
