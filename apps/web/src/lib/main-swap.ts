/**
 * A member's main character on Me (docs/me.md): Me opens on the main, the first character they were approved for
 * until an officer approves a swap. Making an approved alt the main is an ask that waits on the officers' claims
 * panels of the member's raid nights, like a claim (GET/POST /api/me/main, DELETE /api/me/main/request).
 */
import { ApiError, call, type ClaimStatus, type Fetch } from './api';

export interface CharacterRef {
  character_id: number;
  character_name: string;
}

export interface MainSwap {
  id: number;
  member_id: number;
  character_id: number;
  character_name: string;
  raid_day_id: string | null;
  status: ClaimStatus;
  reason: string | null;
}

export interface MyMain {
  /** Null until the member holds an approved claim. */
  main: CharacterRef | null;
  /** Their other approved characters: the ones they may ask to make their main. */
  alts: CharacterRef[];
  /** Their pending ask, or the last decided one while it is still news. */
  request: MainSwap | null;
}

/** Where Me reads and asks: the hub, or the preview's sample member. */
export interface MainBackend {
  mine(): Promise<MyMain>;
  ask(characterId: number): Promise<MainSwap>;
  withdraw(): Promise<void>;
}

export function hubMain(f: Fetch = fetch): MainBackend {
  return {
    mine: () => call<MyMain>(f, '/api/me/main'),
    ask: (characterId) =>
      call<MainSwap>(f, '/api/me/main', { method: 'POST', body: JSON.stringify({ character_id: characterId }) }),
    withdraw: () => call<void>(f, '/api/me/main/request', { method: 'DELETE' })
  };
}

const fold = (name: string) => name.normalize('NFKC').trim().toLocaleLowerCase();

/** Whether two character names are the same character, as the hub compares them. */
export const sameName = (a: string | null | undefined, b: string | null | undefined): boolean =>
  !!a && !!b && fold(a) === fold(b);

/** The dropdown's label for a character: the main says so. */
export const characterLabel = (name: string, main: string | null): string =>
  sameName(name, main) ? `${name} (main)` : name;

/** The approved alt called `name`, if it is one the member may ask for. */
export const altNamed = (mine: MyMain, name: string | null | undefined): CharacterRef | undefined =>
  mine.alts.find((a) => sameName(a.character_name, name));

/** What to tell a member when asking for a main swap fails. */
export function mainError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to change your main.';
    case 404:
      return 'That ask is gone; an officer may have decided it already.';
    case 409:
      return 'That character is already your main.';
    case 422:
      return 'Only a character an officer has approved as yours can be your main.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
