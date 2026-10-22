/**
 * A brand-new preview member's setup, in the browser only, so /setup works on GitHub Pages with no hub behind it.
 * Claims of the sample characters wait for an officer (none decides them here); everything resets on reload.
 */
import { ApiError, type Claim } from '$lib/api';
import { claimableCharacters } from '$lib/mock/data';
import type { DeclaredCharacter, SetupBackend, SetupState } from '$lib/setup';

let claims: Claim[] = [];
let declared: DeclaredCharacter[] = [];
let mainId: number | null = null;
let done = false;
let next = 1;

const fold = (s: string) => s.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
const mainOpen = () => !claims.some((c) => c.status === 'approved');

function claimOf(characterId: number): Claim {
  const c = claimableCharacters.find((m) => m.id === characterId);
  if (!c) throw new ApiError(404, 'Unknown character');
  if (claims.some((x) => x.character_id === characterId)) throw new ApiError(409, 'Character already claimed');
  const claim: Claim = { id: next++, member_id: 7, character_id: c.id, character_name: c.name, raid_day_id: 'wed', status: 'pending', reason: null };
  claims = [...claims, claim];
  return claim;
}

export const previewSetup: SetupBackend = {
  async state(): Promise<SetupState> {
    const named = claims.find((c) => c.character_id === mainId);
    const kept = declared.find((d) => d.main);
    return {
      done,
      main: named ? { name: named.character_name, status: 'pending' } : kept ? { name: kept.name, status: 'not_in_logs' } : null,
      declared,
      main_open: mainOpen()
    };
  },
  async claims() {
    return claims;
  },
  async search(query) {
    const q = fold(query);
    return claimableCharacters.filter((c) => fold(c.name).includes(q));
  },
  async claim(characterId) {
    return claimOf(characterId);
  },
  async unclaim(claimId) {
    claims = claims.filter((c) => c.id !== claimId);
  },
  async declare(name, wowClass, main) {
    const known = claimableCharacters.find((c) => fold(c.name) === fold(name));
    if (known) {
      const claim = claimOf(known.id);
      if (main) mainId = known.id;
      return { claim, declared: null };
    }
    if (declared.some((d) => fold(d.name) === fold(name))) throw new ApiError(409, 'Already named');
    if (main) declared = declared.map((d) => ({ ...d, main: false }));
    const row = { id: next++, name, wow_class: wowClass, main };
    declared = [...declared, row];
    return { claim: null, declared: row };
  },
  async drop(id) {
    declared = declared.filter((d) => d.id !== id);
  },
  async setMain(characterId) {
    mainId = characterId;
    declared = declared.map((d) => ({ ...d, main: false }));
  },
  async finish() {
    done = true;
  }
};
