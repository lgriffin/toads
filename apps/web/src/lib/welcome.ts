/**
 * The first sign-in checklist on /welcome: what a new member does once, in order, to get the most from the hub. Each
 * step links to the page that does it. Officers edit the wording here, in a PR.
 */
export interface WelcomeStep {
  id: string;
  title: string;
  body: string;
  /** A hub path (under the base path) or an outside https link. */
  href: string;
  action: string;
}

/** Where raiders download the analyzer's Windows app (built by lgriffin/warcraftlogs_project on each version tag). */
export const ANALYZER_RELEASES = 'https://github.com/lgriffin/warcraftlogs_project/releases/latest';

export const WELCOME_STEPS: readonly WelcomeStep[] = [
  {
    id: 'character',
    title: 'Claim your characters',
    body: 'Tell the hub which characters are yours, so your performance and badges follow you. Officers approve claims.',
    href: '/me/claim',
    action: 'Claim a character'
  },
  {
    id: 'name',
    title: 'Choose the name we show',
    body: 'Your Discord nickname or a claimed character. You can also add your own Warcraft Logs key here.',
    href: '/me/settings',
    action: 'Open settings'
  },
  {
    id: 'model',
    title: 'Read how we raid',
    body: 'Prep, flasks and elixirs, consumes, speed and badges: what we expect on raid night and how it is measured.',
    href: '/how-we-raid',
    action: 'How we raid'
  },
  {
    id: 'bank',
    title: 'Meet the guild bank',
    body: 'See what the bank holds and request flasks and potions before raid night, here or with /bank in Discord.',
    href: '/bank',
    action: 'Open the bank'
  },
  {
    id: 'apps',
    title: 'Get the apps',
    body: 'The analyzer’s Windows app breaks down any log on your own machine. Your raid night’s officers share the strategy and role sheets from Google Drive in Discord.',
    href: ANALYZER_RELEASES,
    action: 'Download the analyzer'
  },
  {
    id: 'toolkit',
    title: 'See what you can do',
    body: 'Everything your role opens across the analyzer, the bank and Discord, and how to get more.',
    href: '/toolkit',
    action: 'Your toolkit'
  }
];

export function isOutside(href: string): boolean {
  return href.startsWith('https://');
}
