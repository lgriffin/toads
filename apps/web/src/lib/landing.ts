/**
 * The public landing page's copy: who the guild is and what it stands for. It is site text, not data, so the same
 * words show in the static preview and on the live hub. Officers edit it here, in a PR.
 */

import { NIGHTS_IN_WORDS, TEAM_COUNT } from './nights';
import { FOREVER_LAUNCH, FOREVER_LIVE } from './launch';

export interface Value {
  title: string;
  body: string;
}

export const LANDING = {
  guild: 'Toads',
  tagline: 'A very social guild that locks in on raid night, on the EU PvP side of WoW Forever. Horde, one big pond.',
  /** The line under the tagline; `recruitLink` follows it as a link to the recruitment page. */
  recruitLine: 'The ultimate semi-hardcore guild. Are you small, green and angry?',
  recruitLink: 'Sign up today.',
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

/**
 * The words around the homepage's recruiting section. What each night is recruiting is not site text: each night's
 * officers pick it on Officers > Recruitment (lib/recruiting.ts).
 */
export const RECRUITING_COPY = {
  intro: 'Each raid night recruits for itself. Pick a night to see what its officers are looking for.',
  full: 'Full for now. This changes when a spot opens.',
  open: 'These are the primary specs the officers want first.',
  unavailable: 'We could not load what each night is recruiting just now. Ask us in Discord.',
  social:
    'Not after a raid spot? Poke any member of Toads in game for a social invite and come to the pond: everyone is welcome.'
};

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
