<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession } from '$lib/api';
  import Landing from '$lib/Landing.svelte';
  import { previewSession } from '$lib/preview/session.svelte';

  // The public front door. Signed-in members get a link to their hub instead of the login button.
  // The preview starts signed out and signs in on its own /login page.
  let apiMember = $state<string | null>(null);
  let member = $derived(__PREVIEW__ ? (previewSession.role ? 'Hopscotch' : null) : apiMember);
  onMount(async () => {
    if (!__PREVIEW__) apiMember = (await getSession().catch(() => null))?.display_name ?? null;
  });
</script>

<svelte:head><title>Toads · Spineshatter EU</title></svelte:head>

<Landing {member} loginHref={__PREVIEW__ ? `${base}/login/` : '/auth/login'} />
