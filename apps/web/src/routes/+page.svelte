<script lang="ts">
  import { onMount } from 'svelte';
  import { getSession } from '$lib/api';
  import Landing from '$lib/Landing.svelte';

  // The public front door. Signed-in members get a link to their hub instead of the login button.
  let member = $state<string | null>(__PREVIEW__ ? 'Hopscotch' : null);
  onMount(async () => {
    if (!__PREVIEW__) member = (await getSession().catch(() => null))?.display_name ?? null;
  });
</script>

<svelte:head><title>Toads · Spineshatter EU</title></svelte:head>

<Landing {member} />
