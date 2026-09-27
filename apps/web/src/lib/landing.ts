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
  realm: 'Spineshatter EU',
  game: 'TBC Classic',
  tagline: 'A friendly, steady raiding guild. Two nights a week, no drama, lots of frogs.',
  schedule: 'Wednesday and Sunday, 19:30 to 23:00 server time',
  who: [
    'Toads started as a handful of levelling friends on Spineshatter who kept ending up in the same dungeon groups. By the Dark Portal we had enough people for Karazhan, and by Gruul we had two raid teams.',
    'Each raid night has its own team and officers, and plenty of people raid both. We clear content steadily and learn fights together.'
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

/** What members get once they sign in; the landing page lists it so visitors know what is behind the login. */
export const MEMBER_FEATURES: readonly string[] = [
  'A home page you arrange yourself: next raid, your performance, raid totals, posts and more',
  'Every raid log with the analyzer’s breakdown of consumes, buffs and deaths',
  'Your own performance against the guild median for your role',
  'The guild bank, highlight reels and officer posts'
];
