<script lang="ts">
  import { onMount } from 'svelte';
  import {
    claimError,
    createClaim,
    getSession,
    listClaims,
    searchCharacters,
    unclaim,
    type CharacterMatch,
    type Claim
  } from '$lib/api';
  import ClaimFlow from '$lib/ClaimFlow.svelte';
  import { claims as mockClaims, claimableCharacters } from '$lib/mock/data';

  let claims = $state<Claim[]>(__PREVIEW__ ? [...mockClaims] : []);
  let signedInAs = $state<string | null>(__PREVIEW__ ? 'Hopscotch' : null);
  let message = $state(__PREVIEW__ ? 'Preview: claims here are not saved.' : '');
  let busy = $state(false);

  async function run(action: () => Promise<unknown>) {
    busy = true;
    message = '';
    try {
      await action();
      claims = await listClaims();
    } catch (e) {
      message = claimError(e);
    } finally {
      busy = false;
    }
  }

  async function search(query: string): Promise<CharacterMatch[]> {
    if (__PREVIEW__) {
      const q = query.toLowerCase();
      return claimableCharacters.filter((c) => c.name.toLowerCase().includes(q));
    }
    return searchCharacters(query);
  }

  function onclaim(character: CharacterMatch) {
    if (__PREVIEW__) {
      const next = Math.max(0, ...claims.map((c) => c.id)) + 1;
      claims = [
        ...claims,
        { id: next, member_id: 7, character_id: character.id, character_name: character.name, raid_day_id: 'wed', status: 'pending', reason: null }
      ];
      return;
    }
    run(() => createClaim(character.id));
  }

  function onunclaim(claim: Claim) {
    if (__PREVIEW__) {
      claims = claims.filter((c) => c.id !== claim.id);
      return;
    }
    run(() => unclaim(claim.id));
  }

  onMount(() => {
    if (__PREVIEW__) return;
    getSession()
      .then((s) => (signedInAs = s?.display_name ?? null))
      .catch(() => undefined);
    run(async () => undefined);
  });
</script>

<ClaimFlow {claims} {signedInAs} {message} {busy} {search} {onclaim} {onunclaim} />
