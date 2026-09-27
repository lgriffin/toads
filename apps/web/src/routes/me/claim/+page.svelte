<script lang="ts">
  import { onMount } from 'svelte';
  import { claimError, createClaim, listClaims, unclaim, type Claim } from '$lib/api';
  import ClaimFlow from '$lib/ClaimFlow.svelte';
  import { claims as mockClaims } from '$lib/mock/data';

  let claims = $state<Claim[]>(__PREVIEW__ ? [...mockClaims] : []);
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

  function onclaim(characterId: number) {
    if (__PREVIEW__) {
      const next = Math.max(0, ...claims.map((c) => c.id)) + 1;
      claims = [
        ...claims,
        { id: next, member_id: 7, character_id: characterId, character_name: `Character ${characterId}`, raid_day_id: 'wed', status: 'pending', reason: null }
      ];
      return;
    }
    run(() => createClaim(characterId));
  }

  function onunclaim(claim: Claim) {
    if (__PREVIEW__) {
      claims = claims.filter((c) => c.id !== claim.id);
      return;
    }
    run(() => unclaim(claim.id));
  }

  onMount(() => {
    if (!__PREVIEW__) run(async () => undefined);
  });
</script>

<ClaimFlow {claims} {message} {busy} {onclaim} {onunclaim} />
