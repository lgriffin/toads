<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession } from '$lib/api';
  import Landing from '$lib/Landing.svelte';
  import { previewSession } from '$lib/preview/session.svelte';
  import { story } from '$lib/mock/community';
  import { previewNextRaid, previewNow } from '$lib/mock/hub';
  import { sheetTrend } from '$lib/mock/sheets';
  import type { GuildPulse } from '$lib/pulse';

  // The public front door. Signed-in members get a link to their hub instead of the login button.
  // The preview starts signed out and signs in on its own /login page.
  let apiMember = $state<string | null>(null);
  let member = $derived(__PREVIEW__ ? (previewSession.role ? 'Hopscotch' : null) : apiMember);
  // The guild pulse needs a public summary the API does not serve yet, so only the preview draws it, from sample data.
  const pulse: GuildPulse | null = __PREVIEW__
    ? { next: previewNextRaid, now: previewNow, progression: story.progression, trend: sheetTrend }
    : null;
  onMount(async () => {
    if (!__PREVIEW__) apiMember = (await getSession().catch(() => null))?.display_name ?? null;
  });
</script>

<svelte:head><title>Toads · Spineshatter EU</title></svelte:head>

<Landing {member} {pulse} loginHref={__PREVIEW__ ? `${base}/login/` : '/auth/login'} />
