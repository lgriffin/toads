/**
 * The officers' character claims panel (ADMIN_GUIDE.md "Approve character claims"): a member claims a character on Me,
 * and unless its name matches their server nickname it waits for an officer. Each raid night's officers see the claims
 * of members whose night Toad role puts them on that night; the global tier also sees claims from members on no night.
 * The hub's routes are /api/days/{day}/claims (a night) and /api/admin/claims (no night, global officers only); this
 * module only shapes them. A member's ask to make an approved alt their main waits on the same panels, from
 * /api/days/{day}/main-swaps and /api/admin/main-swaps.
 */
import { ApiError, call, type Claim, type Fetch } from './api';

export const REASON_LIMIT = 200;

/** A pending claim as the officers' panel lists it. */
export interface QueuedClaim extends Claim {
  /** The claimant's server nickname. */
  member_name: string;
  /** The raid nights whose officers may decide it; empty when the claimant is on no night. */
  nights: string[];
}

/** A pending ask to make one of the member's approved alts their main. */
export interface QueuedSwap {
  id: number;
  member_id: number;
  character_id: number;
  /** The alt they want as main. */
  character_name: string;
  raid_day_id: string | null;
  status: Claim['status'];
  reason: string | null;
  member_name: string;
  /** Their main now; null when it could not be worked out. */
  current_main: string | null;
  nights: string[];
}

/** Where the panel reads and decides: the hub, or the preview's sample claims. `day` null is the no-night list. */
export interface ClaimsBackend {
  queue(day: string | null): Promise<QueuedClaim[]>;
  approve(day: string | null, id: number): Promise<Claim>;
  reject(day: string | null, id: number, reason: string): Promise<Claim>;
  swaps(day: string | null): Promise<QueuedSwap[]>;
  approveSwap(day: string | null, id: number): Promise<unknown>;
  rejectSwap(day: string | null, id: number, reason: string): Promise<unknown>;
}

/** A claim or a main swap on the panel, keyed so the two kinds never collide. */
export type PanelItem = ({ kind: 'claim' } & QueuedClaim) | ({ kind: 'main' } & QueuedSwap);
export const itemKey = (i: Pick<PanelItem, 'kind' | 'id'>) => `${i.kind}-${i.id}`;

const root = (day: string | null, what: 'claims' | 'main-swaps') =>
  day === null ? `/api/admin/${what}` : `/api/days/${encodeURIComponent(day)}/${what}`;
const base = (day: string | null) => root(day, 'claims');
const swaps = (day: string | null) => root(day, 'main-swaps');
const post = (reason?: string): RequestInit =>
  reason === undefined ? { method: 'POST' } : { method: 'POST', body: JSON.stringify({ reason }) };

export function hubClaims(f: Fetch = fetch): ClaimsBackend {
  return {
    queue: (day) => call<QueuedClaim[]>(f, base(day)),
    approve: (day, id) => call<Claim>(f, `${base(day)}/${encodeURIComponent(id)}/approve`, post()),
    reject: (day, id, reason) => call<Claim>(f, `${base(day)}/${encodeURIComponent(id)}/reject`, post(reason)),
    swaps: (day) => call<QueuedSwap[]>(f, swaps(day)),
    approveSwap: (day, id) => call<unknown>(f, `${swaps(day)}/${encodeURIComponent(id)}/approve`, post()),
    rejectSwap: (day, id, reason) => call<unknown>(f, `${swaps(day)}/${encodeURIComponent(id)}/reject`, post(reason))
  };
}

/** What to tell an officer when a claims call fails. */
export function claimsError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to decide claims.';
    case 403:
      return 'Only this raid night’s officers can decide its claims.';
    case 404:
      return 'That request is gone; the member may have withdrawn it. The list has been refreshed.';
    case 409:
      return e.message === 'They no longer hold that character'
        ? 'They no longer hold that character, so it cannot be their main. The list has been refreshed.'
        : 'Another officer has already decided that request. The list has been refreshed.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
