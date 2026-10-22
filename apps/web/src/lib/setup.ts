/**
 * The first sign-in setup on /setup (docs/setup.md): a trial or raider names their main, their specs and their alts,
 * and sign-in sends them here until they finish. Anyone can rerun it from the account menu. Characters the guild's
 * logs know become claims; one the logs have not seen is named by name and class until it raids with us.
 */
import {
  ApiError,
  call,
  createClaim,
  listClaims,
  searchCharacters,
  unclaim,
  type CharacterMatch,
  type Claim,
  type Fetch
} from './api';

export interface DeclaredCharacter {
  id: number;
  name: string;
  /** A class id from the comp catalogue ($lib/comp CLASSES). */
  wow_class: string;
  main: boolean;
}

export type MainStatus = 'approved' | 'pending' | 'not_in_logs';

export interface SetupState {
  done: boolean;
  /** Their main now, else the claim they named main, else a named main the logs have not seen. */
  main: { name: string; status: MainStatus } | null;
  /** Characters named that the guild's logs have not seen yet, oldest first. */
  declared: DeclaredCharacter[];
  /** True while they may still name their first main here; after that the main changes by a main swap on Me. */
  main_open: boolean;
}

export interface Declared {
  claim: Claim | null;
  declared: DeclaredCharacter | null;
}

/** Where the setup page reads and writes: the hub, or the preview's sample member. */
export interface SetupBackend {
  state(): Promise<SetupState>;
  claims(): Promise<Claim[]>;
  search(query: string): Promise<CharacterMatch[]>;
  claim(characterId: number): Promise<Claim>;
  unclaim(claimId: number): Promise<void>;
  declare(name: string, wowClass: string, main: boolean): Promise<Declared>;
  drop(id: number): Promise<void>;
  setMain(characterId: number): Promise<void>;
  finish(): Promise<void>;
}

export function hubSetup(f: Fetch = fetch): SetupBackend {
  return {
    state: () => call<SetupState>(f, '/api/me/setup'),
    claims: () => listClaims(f),
    search: (query) => searchCharacters(query, f),
    claim: (characterId) => createClaim(characterId, f),
    unclaim: (claimId) => unclaim(claimId, f),
    declare: (name, wowClass, main) =>
      call<Declared>(f, '/api/me/setup/characters', {
        method: 'POST',
        body: JSON.stringify({ name, wow_class: wowClass, main })
      }),
    drop: (id) => call<void>(f, `/api/me/setup/characters/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    setMain: (characterId) =>
      call<void>(f, '/api/me/setup/main', { method: 'POST', body: JSON.stringify({ character_id: characterId }) }),
    finish: () => call<void>(f, '/api/me/setup/done', { method: 'POST' })
  };
}

/**
 * The welcome at the top of the page, from Gally (_gallagher) and the officers. Officers edit the wording here, in
 * a PR; the pond, never anything else.
 */
export const WELCOME = {
  heading: 'Welcome to the Pond',
  body: [
    'Thanks for logging in. Before you hop in, let’s get some info about you.',
    'Tell us your main, the specs you play, any alts and your professions, so we know who’s who on raid night, the officers can seat you in the right spot and the guild knows who can craft what.'
  ],
  signoff: 'Gally and the officers'
} as const;

export interface Alt {
  key: string;
  name: string;
  /** What the officers have done with it, in plain words. */
  status: string;
  /** Claims are unclaimed through /api/claims; named characters are dropped through the setup route. */
  claim?: Claim;
  declared?: DeclaredCharacter;
}

const fold = (name: string) => name.normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase();

/** The member's alts: every live claim and named character that is not the main. */
export function altsOf(claims: readonly Claim[], state: SetupState): Alt[] {
  const main = state.main ? fold(state.main.name) : null;
  const claimed = claims
    .filter((c) => c.status !== 'rejected' && fold(c.character_name) !== main)
    .map<Alt>((c) => ({
      key: `claim-${c.id}`,
      name: c.character_name,
      status: c.status === 'approved' ? 'Approved' : 'Waiting for an officer',
      claim: c
    }));
  const named = state.declared
    .filter((d) => !d.main)
    .map<Alt>((d) => ({ key: `named-${d.id}`, name: d.name, status: 'Waiting for its first logged raid', declared: d }));
  return [...claimed, ...named];
}

export const MAIN_STATUS: Record<MainStatus, string> = {
  approved: 'Your main',
  pending: 'Your main, waiting for an officer to approve the claim',
  not_in_logs: 'Your main, waiting for its first logged raid with the guild'
};

/** What to tell a member when a setup call fails. */
export function setupError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in with Discord to set up your profile.';
    case 403:
      return 'Setup needs a trial or raider role on a raid night.';
    case 404:
      return 'Claim that character first.';
    case 409:
      return e.message === 'Already named'
        ? 'You have already named that character.'
        : e.message === 'Ask your officers to swap your main'
          ? 'You already have an approved main. Ask for a main swap on Me to change it.'
          : 'Someone already holds or is waiting on that character. Ask an officer if it is yours.';
    case 422:
      return 'Pick a class and a name of at least two letters.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
