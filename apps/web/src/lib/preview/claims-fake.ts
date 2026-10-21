/**
 * The preview's pending character claims: sample claims in the browser only, so the officers' claims panel works on
 * GitHub Pages with no hub behind it. Decisions last until the page reloads.
 */
import { ApiError, type Claim } from '$lib/api';
import type { ClaimsBackend, QueuedClaim } from '$lib/officer-claims';

let claims: QueuedClaim[] = [
  ['Toadstool', 'Puddles', ['wed']],
  ['Lilypadd', 'Lily', ['wed', 'sun']],
  ['Bramblewick', 'Bram', ['thu']],
  ['Pondweed', 'Weedy', ['sun']],
  ['Marshmallow', 'Newcomer', []]
].map(([character_name, member_name, nights], i) => ({
  id: i + 1,
  member_id: 100 + i,
  character_id: 500 + i,
  character_name: character_name as string,
  raid_day_id: (nights as string[])[0] ?? null,
  status: 'pending',
  reason: null,
  member_name: member_name as string,
  nights: nights as string[]
}));

function take(day: string | null, id: number): QueuedClaim {
  const found = claims.find((c) => c.id === id);
  if (!found) throw new ApiError(404, 'No such claim');
  if (day !== null && !found.nights.includes(day)) throw new ApiError(403, 'Forbidden');
  claims = claims.filter((c) => c.id !== id);
  return found;
}

export const previewClaims: ClaimsBackend = {
  async queue(day) {
    return claims.filter((c) => (day === null ? c.nights.length === 0 : c.nights.includes(day)));
  },
  async approve(day, id): Promise<Claim> {
    return { ...take(day, id), status: 'approved' };
  },
  async reject(day, id, reason): Promise<Claim> {
    if (!reason.trim()) throw new ApiError(422, 'A rejection needs a reason');
    return { ...take(day, id), status: 'rejected', reason };
  }
};
