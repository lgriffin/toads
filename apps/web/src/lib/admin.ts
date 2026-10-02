/**
 * The super admin console's map of the hub's moving parts: where each integration is set up and what keeps it fresh.
 * It explains and links; the settings themselves live in the environment (ADMIN_GUIDE.md) and the hub's own pages.
 */
export interface Integration {
  title: string;
  body: string;
  /** A hub path (under the base path) or an outside https link. */
  href: string;
  action: string;
}

export const ADMIN_GUIDE = 'https://github.com/lgriffin/toads/blob/main/ADMIN_GUIDE.md';

export const INTEGRATIONS: readonly Integration[] = [
  {
    title: 'Warcraft Logs',
    body: 'The guild’s Warcraft Logs login feeds reference comparisons. Members may add their own key to spread the load.',
    href: '/officers/reference',
    action: 'Reference comparison'
  },
  {
    title: 'Discord bots',
    body: 'Toad Bot, the bank bot and the relay each run from their own spec and token, and talk to the hub through the bot bridge.',
    href: ADMIN_GUIDE,
    action: 'Bot settings in the admin guide'
  },
  {
    title: 'Guild bank',
    body: 'ToadsBank holds the stock and requests. Grants and officer tokens below decide who helps run it.',
    href: '/bank',
    action: 'Open the bank'
  },
  {
    title: 'Google Drive',
    body: 'Officers keep raid strategy and role sheets in Google Drive and share them in Discord. The hub does not link them yet.',
    href: ADMIN_GUIDE,
    action: 'Admin guide'
  }
];

export interface Job {
  name: string;
  what: string;
  every: string;
}

/** The scheduler's jobs (services/worker, toads-worker schedule) and their default intervals. */
export const JOBS: readonly Job[] = [
  { name: 'publish-home', what: 'Analyzer widgets on the hub home', every: '30 minutes' },
  { name: 'publish-performance', what: 'Each member’s number against the role median', every: '30 minutes' },
  { name: 'publish-badges', what: 'Toads badges', every: '30 minutes' },
  { name: 'publish-reference', what: 'Reference raid lists and comparisons', every: '30 minutes' },
  { name: 'import-sheets', what: 'The CBA and RPB raid sheets', every: '6 hours' }
];
