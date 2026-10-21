/**
 * The preview member's main and alts, in the browser only, so Me's main swap works on GitHub Pages with no hub behind
 * it. An ask stays pending (no officer decides it here) until it is withdrawn or the page reloads.
 */
import { ApiError } from '$lib/api';
import type { MainBackend, MainSwap, MyMain } from '$lib/main-swap';

const main = { character_id: 1, character_name: 'Hopscotch' };
const alts = [
  { character_id: 3, character_name: 'Bogwalker' },
  { character_id: 2, character_name: 'Lilypadd' }
];
let request: MainSwap | null = null;

export const previewMain: MainBackend = {
  async mine(): Promise<MyMain> {
    return { main, alts, request };
  },
  async ask(characterId) {
    const alt = alts.find((a) => a.character_id === characterId);
    if (!alt) throw new ApiError(characterId === main.character_id ? 409 : 422, 'Not one of your alts');
    request = { id: 1, member_id: 1, ...alt, raid_day_id: 'wed', status: 'pending', reason: null };
    return request;
  },
  async withdraw() {
    if (!request) throw new ApiError(404, 'No main swap is waiting');
    request = null;
  }
};
