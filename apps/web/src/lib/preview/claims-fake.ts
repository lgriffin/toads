/**
 * The preview's pending character claims: sample claims in the browser only, so the officers' claims panel works on
 * GitHub Pages with no hub behind it, and one member asking to make an alt their main. Decisions last until the page
 * reloads.
 */
import { ApiError, type Claim } from '$lib/api';
import type { ClaimsBackend, QueuedClaim, QueuedSwap } from '$lib/officer-claims';

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

let swaps: QueuedSwap[] = [
  {
    id: 1,
    member_id: 120,
    character_id: 610,
    character_name: 'Mossfire',
    raid_day_id: 'thu',
    status: 'pending',
    reason: null,
    member_name: 'Mossy',
    current_main: 'Mossback',
    nights: ['thu']
  }
];

const onNight = (day: string | null, nights: string[]) => (day === null ? nights.length === 0 : nights.includes(day));

function takeSwap(day: string | null, id: number): QueuedSwap {
  const found = swaps.find((s) => s.id === id);
  if (!found) throw new ApiError(404, 'No such main swap');
  if (day !== null && !found.nights.includes(day)) throw new ApiError(403, 'Forbidden');
  swaps = swaps.filter((s) => s.id !== id);
  return found;
}

function take(day: string | null, id: number): QueuedClaim {
  const found = claims.find((c) => c.id === id);
  if (!found) throw new ApiError(404, 'No such claim');
  if (day !== null && !found.nights.includes(day)) throw new ApiError(403, 'Forbidden');
  claims = claims.filter((c) => c.id !== id);
  return found;
}

export const previewClaims: ClaimsBackend = {
  async queue(day) {
    return claims.filter((c) => onNight(day, c.nights));
  },
  async approve(day, id): Promise<Claim> {
    return { ...take(day, id), status: 'approved' };
  },
  async reject(day, id, reason): Promise<Claim> {
    if (!reason.trim()) throw new ApiError(422, 'A rejection needs a reason');
    return { ...take(day, id), status: 'rejected', reason };
  },
  async swaps(day) {
    return swaps.filter((s) => onNight(day, s.nights));
  },
  async approveSwap(day, id) {
    return { ...takeSwap(day, id), status: 'approved' };
  },
  async rejectSwap(day, id, reason) {
    if (!reason.trim()) throw new ApiError(422, 'A rejection needs a reason');
    return { ...takeSwap(day, id), status: 'rejected', reason };
  }
};
