/**
 * The officers' character claims panel (ADMIN_GUIDE.md "Approve character claims"): a member claims a character on Me,
 * and unless its name matches their server nickname it waits for an officer. Each raid night's officers see the claims
 * of members whose night Toad role puts them on that night; the global tier also sees claims from members on no night.
 * The hub's routes are /api/days/{day}/claims (a night) and /api/admin/claims (no night, global officers only); this
 * module only shapes them.
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

/** Where the panel reads and decides: the hub, or the preview's sample claims. `day` null is the no-night list. */
export interface ClaimsBackend {
  queue(day: string | null): Promise<QueuedClaim[]>;
  approve(day: string | null, id: number): Promise<Claim>;
  reject(day: string | null, id: number, reason: string): Promise<Claim>;
}

const base = (day: string | null) => (day === null ? '/api/admin/claims' : `/api/days/${encodeURIComponent(day)}/claims`);

export function hubClaims(f: Fetch = fetch): ClaimsBackend {
  return {
    queue: (day) => call<QueuedClaim[]>(f, base(day)),
    approve: (day, id) => call<Claim>(f, `${base(day)}/${encodeURIComponent(id)}/approve`, { method: 'POST' }),
    reject: (day, id, reason) =>
      call<Claim>(f, `${base(day)}/${encodeURIComponent(id)}/reject`, { method: 'POST', body: JSON.stringify({ reason }) })
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
      return 'That claim is gone; the member may have withdrawn it. The list has been refreshed.';
    case 409:
      return 'Another officer has already decided that claim. The list has been refreshed.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
