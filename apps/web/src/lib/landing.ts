/**
 * The public landing page's copy: who the guild is and what it stands for. It is site text, not data, so the same
 * words show in the static preview and on the live hub. Officers edit it here, in a PR.
 */

export interface Value {
  title: string;
  body: string;
}

export const LANDING = {
  guild: 'Toads',
  tagline: 'A friendly, steady guild on the European PvP side of WoW Forever. Horde, one big pond.',
  schedule: 'Wednesday and Sunday, 19:30 to 23:00 server time',
  who: [
    'Toads started as a handful of levelling friends on Spineshatter who kept ending up in the same dungeon groups. By the Dark Portal we had enough people for Karazhan, and by Gruul we had two raid teams.',
    'Now we are taking the whole pond to World of Warcraft: Forever. Horde, PvP, Europe (EU): the same people, the same habits, a new continent to be unreasonably smug about.'
  ],
  values: [
    {
      title: 'People before parses',
      body: 'We want players who turn up, prepare and help each other. A bad night is something we fix together, not a reason to blame someone.'
    },
    {
      title: 'Prepared, not sweaty',
      body: 'Consumes, gear and tactics are expected on raid night, and the hub shows everyone the same numbers. Nobody is asked to raid more than two nights.'
    },
    {
      title: 'Boring, fair loot',
      body: 'Loot rules are written down, the same for everyone and never changed mid-tier. Officers explain every call.'
    },
    {
      title: 'Open doors',
      body: 'Anyone can apply, and every applicant gets a private interview room with the officers on Discord. Trials are told where they stand.'
    }
  ] satisfies Value[]
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
    status: 'Launching 4 November 2026',
    line: 'Horde · PvP · Europe (EU)',
    body: 'Our new home. We are rolling together on the PvP side in the European region, raiding as a guild and defending the pond in the open world. Reserve your names early and tell us who you are bringing.',
    logo: { src: 'brand/wow-forever.png', alt: 'World of Warcraft: Forever' }
  },
  {
    id: 'tbc',
    title: 'Burning Crusade Classic',
    status: 'Active now',
    line: 'Alliance · Spineshatter · Europe (EU)',
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
  id: 'prep' | 'flasks' | 'consumes' | 'speed' | 'badges' | 'standard';
  title: string;
  /** One line for the homepage card. */
  summary: string;
  approach: string;
  measure: string;
  youSee: string;
}

export const MODEL: readonly Pillar[] = [
  {
    id: 'prep',
    title: 'Prep',
    summary: 'Enchanted, gemmed, repaired and addons current before the first pull.',
    approach:
      'Arrive enchanted, gemmed and repaired, with the night’s resistance set if a fight needs it, and your addons up to date.',
    measure: 'The CBA raid sheet’s gear check counts missing enchants and gems for every raid.',
    youSee: 'The raid’s gear check in the raid totals on the hub.'
  },
  {
    id: 'flasks',
    title: 'Flasks and elixirs',
    summary: 'A flask, or a battle and guardian elixir pair, on every progression pull.',
    approach:
      'A flask, or a battle and guardian elixir pair, on every progression pull. The guild bank keeps raid stock of the common flasks, so gold is never the reason to go without.',
    measure: 'The CBA raid sheet records buff consumable uptime on bosses and flags anyone under 80%.',
    youSee: 'The raid’s consumable uptime on the hub, and a bank request for anything you are short of.'
  },
  {
    id: 'consumes',
    title: 'Consumes',
    summary: 'Potions on cooldown, runes, drums, sappers, oils and scrolls.',
    approach:
      'Potions on cooldown, runes for mana users, drums from leatherworkers, and sappers wherever a fight allows them.',
    measure: 'The analyzer counts every use from the combat log; the raid sheets total them per raid.',
    youSee: 'The raid’s consumable totals on the hub, and the badges they earn you on Me.'
  },
  {
    id: 'speed',
    title: 'Speed',
    summary: 'Clear times tracked every week, zone by zone.',
    approach: 'Clean pulls and short breaks. A faster clear is a better night for everyone.',
    measure: 'Clear times per zone from the CBA raid sheet, and each raid’s length from the analyzer.',
    youSee: 'Each raid’s clear times in the raid totals on the hub.'
  },
  {
    id: 'badges',
    title: 'Badges',
    summary: 'Ten awards for turning up and coming prepared, in four item-quality tiers.',
    approach:
      'We reward turning up and coming prepared, not topping meters. Each badge has four tiers named after item quality: Uncommon, Rare, Epic and Legendary.',
    measure: 'The analyzer counts them across every guild raid. Pug logs never count.',
    youSee: 'Your badges and how far you are from the next tier on Me. Raid leaders see the roster’s.'
  },
  {
    id: 'standard',
    title: 'Measured against ourselves',
    summary: 'Each week against our own last four. No targets.',
    approach:
      'There is no number to hit. The guild’s healing each week is compared with its own average over the four raided weeks before it, and your own number with the guild median for your role.',
    measure:
      'The analyzer’s healing per raid and per character, week on week, and each player’s role number in every raid.',
    youSee: 'The week-on-week healing charts and your performance against the role median, both on the hub.'
  }
];

export interface WeekDay {
  day: string;
  raid: boolean;
  text: string;
}

/** When each part of the model happens in a normal raid week. */
export const RAID_WEEK: readonly WeekDay[] = [
  { day: 'Mon', raid: false, text: 'Ask the guild bank for flasks and mats, on the hub or with /bank request in Discord.' },
  {
    day: 'Tue',
    raid: false,
    text: 'Officers fill bank requests and share the strategy and role sheets from Google Drive.'
  },
  { day: 'Wed', raid: true, text: 'Raid, 19:30 to 23:00. The log is analysed within half an hour of the upload.' },
  { day: 'Thu', raid: false, text: 'Badges, raid totals and your performance update on the hub.' },
  { day: 'Fri', raid: false, text: 'Officers publish posts, highlights and spotlights to the hub and Discord.' },
  { day: 'Sat', raid: false, text: 'Fix anything the gear check found before Sunday.' },
  { day: 'Sun', raid: true, text: 'Raid, 19:30 to 23:00. Same cycle.' }
];

export interface AppTile {
  title: string;
  body: string;
}

/** The three things every raider gets once they sign in. */
export const MEMBER_APPS: readonly AppTile[] = [
  {
    title: 'Raid analyzer',
    body: 'Raid totals and week-on-week charts on the hub, your number against the role median, and your badges. Every log broken down in the Windows app.'
  },
  { title: 'Guild bank', body: 'Browse what the bank holds and request flasks, potions and mats for raid night.' },
  { title: 'Discord', body: 'Raid times, officer posts, highlight reels and the bank bot, joined up with the hub.' }
];
