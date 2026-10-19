import { getContext, setContext } from 'svelte';
import type { MemberFacts } from './toads';

/**
 * The signed-in member's toad facts, loaded once by the root layout (session, awards, role badges) and read by pages
 * such as /me, so a page shows exactly the toads the header does without fetching them again.
 */
export type MeFacts = MemberFacts & { name: string };

const KEY = Symbol('toads:me');

export function setMe(read: () => MeFacts): void {
  setContext(KEY, read);
}

/** The signed-in member's facts; empty outside the root layout. */
export function getMe(): () => MeFacts {
  return getContext<(() => MeFacts) | undefined>(KEY) ?? (() => ({ name: '' }));
}
