/**
 * Sample community data for the static preview: the guild story, recruitment, posts, applications, highlights and
 * spotlights. Shapes follow the shared design (camelCase mirrors of the API's JSON, see $lib/community).
 */
import type { Application, Highlight, Post, PublicStory, RecruitmentNeed, Spotlight, Viewer } from '../community';
import { progressionFromRaids } from '../progression';
import { raids } from './data';

/** The preview visitor: Hopscotch raids Wednesday and Sunday and is a Wednesday officer. */
export const viewer: Viewer = {
  name: 'Hopscotch',
  signedIn: true,
  raidDays: ['Wednesday', 'Sunday'],
  officerDays: ['Wednesday'],
  globalOfficer: false
};

// Each night's officers list their own needs (Officers > Recruitment). Thursday lists no tanks, so the homepage shows
// its tanks as full for now.
export const needs: RecruitmentNeed[] = [
  { className: 'Warrior', spec: 'Protection', role: 'Tank', priority: 'high', raidDays: ['Sunday'] },
  { className: 'Shaman', spec: 'Restoration', role: 'Healer', priority: 'high', raidDays: ['Wednesday'] },
  { className: 'Shaman', spec: 'Restoration', role: 'Healer', priority: 'medium', raidDays: ['Sunday'] },
  { className: 'Priest', spec: 'Shadow', role: 'Ranged', priority: 'medium', raidDays: ['Wednesday'] },
  { className: 'Hunter', spec: 'Beast Mastery', role: 'Ranged', priority: 'medium', raidDays: ['Thursday'] },
  { className: 'Paladin', spec: 'Holy', role: 'Healer', priority: 'low', raidDays: ['Sunday'] },
  { className: 'Druid', spec: 'Guardian', role: 'Tank', priority: 'medium', raidDays: ['Wednesday'] },
  { className: 'Rogue', spec: 'Combat', role: 'Melee', priority: 'low', raidDays: ['Thursday'] }
];

export const posts: Post[] = [
  {
    id: 'p-welcome',
    title: 'New to the pond? Start here',
    body: 'Welcome, tadpoles.\n\nRaids are Wednesday, Thursday and Sunday from 21:00 server time. Invites go out at 20:45.\nSign up on the Hub before 19:00 on raid day so the raid leader can balance groups.',
    authorName: 'Ribbitz',
    origin: 'hub',
    visibility: 'public',
    raidDay: null,
    status: 'published',
    pinned: true,
    publishToDiscord: true,
    discordMessageId: '1287645500112345678',
    editedSinceReview: false,
    createdAt: '2026-09-01T12:00:00Z',
    publishedAt: '2026-09-01T12:00:00Z'
  },
  {
    id: 'p-vashj',
    title: 'Vashj prep night',
    body: 'Bring fire resist for Hydross swaps and a stack of Flasks of Relentless Assault.\nTainted core runners, check #tactics before Wednesday.',
    authorName: 'Hopscotch',
    origin: 'hub',
    visibility: 'raid_day',
    raidDay: 'Wednesday',
    status: 'published',
    pinned: false,
    publishToDiscord: true,
    discordMessageId: '1288891200223456789',
    editedSinceReview: false,
    createdAt: '2026-09-25T20:12:00Z',
    publishedAt: '2026-09-25T20:12:00Z'
  },
  {
    id: 'p-bank',
    title: 'Bank requests open for Wednesday',
    body: 'Wednesday bank is restocked with Super Mana Potions and Elixirs of Major Agility. Request through the Bank page.',
    authorName: 'Croakley',
    origin: 'discord',
    visibility: 'guild',
    raidDay: null,
    status: 'published',
    pinned: false,
    publishToDiscord: false,
    discordMessageId: '1287902200334567890',
    editedSinceReview: false,
    createdAt: '2026-09-23T09:40:00Z',
    publishedAt: '2026-09-23T10:05:00Z'
  },
  {
    id: 'p-alar',
    title: "Al'ar down in one pull",
    body: 'Clean phase two, nobody ate a flame patch. Kael next week: read the weapon phase notes.',
    authorName: 'Greenmantle',
    origin: 'discord',
    visibility: 'public',
    raidDay: null,
    status: 'published',
    pinned: false,
    publishToDiscord: false,
    discordMessageId: '1286610000445678901',
    editedSinceReview: false,
    createdAt: '2026-09-20T22:10:00Z',
    publishedAt: '2026-09-21T08:30:00Z'
  },
  {
    id: 'p-sunday-kael',
    title: 'Sunday: Kael assignments',
    body: 'Weapon phase assignments are pinned in #sunday-raid.\nMind control breakers: Fenwick and Reedbeard.',
    authorName: 'Ribbitz',
    origin: 'hub',
    visibility: 'raid_day',
    raidDay: 'Sunday',
    status: 'published',
    pinned: false,
    publishToDiscord: true,
    discordMessageId: '1288900000556789012',
    editedSinceReview: false,
    createdAt: '2026-09-24T19:00:00Z',
    publishedAt: '2026-09-24T19:00:00Z'
  },
  {
    id: 'p-discord-lurker',
    title: 'Lurker spout tip',
    body: 'If you are on the outer platform, jump in the water as soon as the spout starts.\nWorks every time.',
    authorName: 'Bogwalker',
    origin: 'discord',
    visibility: 'guild',
    raidDay: null,
    status: 'pending_review',
    pinned: false,
    publishToDiscord: false,
    discordMessageId: '1289001100667890123',
    editedSinceReview: false,
    createdAt: '2026-09-25T21:44:00Z',
    publishedAt: null
  },
  {
    id: 'p-discord-recruit',
    title: 'Looking for a Sunday tank',
    body: 'We have room for one more Protection Warrior on Sunday.\nPoint anyone keen at the Recruit page.',
    authorName: 'Wartsworth',
    origin: 'discord',
    visibility: 'public',
    raidDay: null,
    status: 'pending_review',
    pinned: false,
    publishToDiscord: false,
    discordMessageId: '1289012200778901234',
    editedSinceReview: true,
    createdAt: '2026-09-26T09:15:00Z',
    publishedAt: null
  },
  {
    id: 'p-draft',
    title: 'Loot council notes',
    body: 'Draft, not ready yet.',
    authorName: 'Hopscotch',
    origin: 'hub',
    visibility: 'guild',
    raidDay: null,
    status: 'draft',
    pinned: false,
    publishToDiscord: false,
    discordMessageId: null,
    editedSinceReview: false,
    createdAt: '2026-09-26T11:00:00Z',
    publishedAt: null
  }
];

export const applications: Application[] = [
  {
    id: 'app-1',
    memberId: 'm-501',
    applicantName: 'Mireborn',
    characterName: 'Mireborn',
    className: 'Warrior',
    spec: 'Protection',
    role: 'Tank',
    secondaryRole: 'Melee',
    whyToads: 'My old guild stopped raiding after Gruul. A friend in yours says Sundays are calm, prepared and fun.',
    raidDays: ['Sunday'],
    experience: 'Main tanked Karazhan and Gruul on a Firemaw EU guild. Off-tank experience in SSC up to Leotheras.',
    availability: 'Sundays from 19:00; Wednesdays some weeks.',
    logsUrl: 'https://classic.warcraftlogs.com/character/eu/spineshatter/mireborn',
    status: 'applied',
    interviewChannelId: null,
    events: [{ at: '2026-09-25T17:20:00Z', actorName: 'Mireborn', from: null, to: 'applied', note: 'Applied on the Hub' }],
    createdAt: '2026-09-25T17:20:00Z'
  },
  {
    id: 'app-2',
    memberId: 'm-502',
    applicantName: 'Duckweed',
    characterName: 'Duckweed',
    className: 'Shaman',
    spec: 'Restoration',
    role: 'Healer',
    secondaryRole: null,
    whyToads: 'I want a guild that pushes SSC without the shouting. Your recruitment post read like that.',
    raidDays: [],
    experience: 'Healed all of T4 and SSC to Vashj.\nComfortable on tank healing or raid chain heal.',
    availability: 'Either night.',
    logsUrl: null,
    status: 'interviewing',
    interviewChannelId: 'interview-duckweed',
    events: [
      { at: '2026-09-21T10:02:00Z', actorName: 'Duckweed', from: null, to: 'applied', note: 'Applied on the Hub' },
      {
        at: '2026-09-21T18:30:00Z',
        actorName: 'Hopscotch',
        from: 'applied',
        to: 'interviewing',
        note: 'Opened #interview-duckweed'
      }
    ],
    createdAt: '2026-09-21T10:02:00Z'
  },
  {
    id: 'app-3',
    memberId: 'm-503',
    applicantName: 'Pollywog',
    characterName: 'Pollywög',
    className: 'Priest',
    spec: 'Shadow',
    role: 'Ranged',
    raidDays: ['Wednesday'],
    experience: 'Shadow priest since launch. Kara on farm.',
    availability: 'Wednesdays.',
    logsUrl: 'https://fresh.warcraftlogs.com/character/eu/spineshatter/pollywog',
    status: 'trial_offered',
    interviewChannelId: 'interview-pollywog',
    events: [
      { at: '2026-09-14T09:00:00Z', actorName: 'Pollywog', from: null, to: 'applied', note: 'Applied on the Hub' },
      {
        at: '2026-09-14T20:10:00Z',
        actorName: 'Hopscotch',
        from: 'applied',
        to: 'interviewing',
        note: 'Opened #interview-pollywog'
      },
      {
        at: '2026-09-18T21:00:00Z',
        actorName: 'Hopscotch',
        from: 'interviewing',
        to: 'trial_offered',
        note: 'Trial raid on Wednesday 1 October'
      }
    ],
    createdAt: '2026-09-14T09:00:00Z'
  },
  {
    id: 'app-4',
    memberId: 'm-504',
    applicantName: 'Swampy',
    characterName: 'Swampfang',
    className: 'Hunter',
    spec: 'Survival',
    role: 'Ranged',
    raidDays: ['Wednesday'],
    experience: 'Fresh 70.',
    availability: 'Wednesdays.',
    logsUrl: null,
    status: 'declined',
    interviewChannelId: 'interview-swampfang',
    events: [
      { at: '2026-09-08T12:00:00Z', actorName: 'Swampy', from: null, to: 'applied', note: 'Applied on the Hub' },
      {
        at: '2026-09-09T19:00:00Z',
        actorName: 'Hopscotch',
        from: 'applied',
        to: 'interviewing',
        note: 'Opened #interview-swampfang'
      },
      {
        at: '2026-09-12T19:00:00Z',
        actorName: 'Hopscotch',
        from: 'interviewing',
        to: 'declined',
        note: 'Not attuned yet; invited to re-apply after Karazhan. Room locked.'
      }
    ],
    createdAt: '2026-09-08T12:00:00Z'
  }
];

export const highlights: Highlight[] = [
  {
    id: 'h-vashj',
    title: 'Tainted core relay, Vashj phase two',
    provider: 'youtube',
    clipId: 'Tq3vN8xLp2A',
    submittedBy: 'Greenmantle',
    raidId: 'ssc-0924',
    boss: 'Lady Vashj',
    visibility: 'public',
    status: 'published',
    createdAt: '2026-09-25T08:00:00Z'
  },
  {
    id: 'h-alar',
    title: "Al'ar one-pull, from Ribbitz's stream",
    provider: 'twitch',
    clipId: 'CourageousFrogAlarPogChamp-aB3dEf9gHiJkLm',
    submittedBy: 'Ribbitz',
    raidId: 'tk-0920',
    boss: "Al'ar",
    visibility: 'public',
    status: 'published',
    createdAt: '2026-09-21T09:00:00Z'
  },
  {
    id: 'h-leo',
    title: 'Leotheras whirlwind dodge',
    provider: 'streamable',
    clipId: 'k7x2qp',
    submittedBy: 'Tadpole',
    raidId: 'ssc-0917',
    boss: 'Leotheras the Blind',
    visibility: 'guild',
    status: 'published',
    createdAt: '2026-09-18T12:00:00Z'
  },
  {
    id: 'h-morogrim',
    title: 'Murloc wave AoE',
    provider: 'youtube',
    clipId: 'Hb7_kQ2-wZ0',
    submittedBy: 'Fenwick',
    raidId: 'ssc-0924',
    boss: 'Morogrim Tidewalker',
    visibility: 'public',
    status: 'submitted',
    createdAt: '2026-09-26T07:30:00Z'
  }
];

export const spotlights: Spotlight[] = [
  {
    id: 's-bogwalker',
    memberName: 'Bogwalker',
    characterName: 'Bogwalker',
    className: 'Shaman',
    headline: 'Twenty-one kicks at Maulgar',
    body: 'Bogwalker has led our interrupt table three weeks running.\nAsk about the totem macro; there is always a totem macro.',
    writtenBy: 'Ribbitz',
    consent: 'granted',
    status: 'published',
    createdAt: '2026-09-15T12:00:00Z'
  },
  {
    id: 's-hopscotch',
    memberName: 'Hopscotch',
    characterName: 'Hopscotch',
    className: 'Rogue',
    headline: 'The kick that saved Leotheras',
    body: 'Two wipes in, Hopscotch called the inner-demon timings and kicked every Chaos Blast that mattered.',
    writtenBy: 'Croakley',
    consent: 'pending',
    status: 'draft',
    createdAt: '2026-09-25T15:00:00Z'
  }
];

export const story: PublicStory = {
  guild: 'toads',
  realm: 'Spineshatter EU',
  // The same words as services/api/src/toads_api/community/story.py; a test keeps them in step.
  tagline: 'A semi-hardcore, very social raiding guild on Spineshatter: organised, competitive and locked in on speed and execution.',
  story: [
    'toads was founded in 2019 by a core of English friends who wanted to create a guild that could progress through Classic, together. This community soon developed into a large group of players from all over the world, although with a predominately UK and Scandinavian core. The guild smashed through each iteration of Classic, growing stronger and stronger. Many IRL friendships grew from this community and after seven years together, we have strong roots and a very experienced team of officers.',
    'We are a semi-hardcore guild that appeals to players with high skill who operate on a limited timeframe. We are competitive, disciplined, well-organized and have high expectations from our players. We are very protective of our community and the guild comes first in all matters.',
    'Our guild strength has peaked in WoW Forever and we begin the game with three 40-man raid teams (Wednesday/Thursday/Sunday).',
    'toads has been a constant in the lives of our guildies for many years now and we have no intent of slowing down.'
  ],
  discordInvite: 'https://discord.gg/example',
  progression: progressionFromRaids(raids),
  needs,
  posts,
  highlights,
  spotlights
};
