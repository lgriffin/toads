<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { call, getSession } from '$lib/api';
  import type { RecruitmentNeed } from '$lib/community';
  import { needFromApi, type ApiNeed } from '$lib/community-api';
  import Landing from '$lib/Landing.svelte';
  import { previewPublicNeeds } from '$lib/preview/needs-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import { RAID_NIGHTS } from '$lib/nights';
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
  // Each night's recruitment needs, as its officers set them on Officers > Recruitment. The preview's come from its
  // in-browser sample, which its officers' page changes too.
  let needs = $state<RecruitmentNeed[] | null>(__PREVIEW__ ? previewPublicNeeds() : null);
  let needsFailed = $state(false);
  let nights = $state(RAID_NIGHTS.map(({ id, name }) => ({ id, name })));
  onMount(async () => {
    if (__PREVIEW__) return;
    const [session, open, offered] = await Promise.all([
      getSession().catch(() => null),
      call<ApiNeed[]>(fetch, '/api/public/recruitment').catch(() => null),
      call<{ id: string; name: string }[]>(fetch, '/api/public/raid-nights').catch(() => [])
    ]);
    apiMember = session?.display_name ?? null;
    needsFailed = open === null;
    needs = (open ?? []).map(needFromApi);
    if (offered.length) nights = offered;
  });
</script>

<svelte:head><title>toads · Horde PvP guild, EU, WoW Forever</title></svelte:head>

<Landing {member} {pulse} {needs} {needsFailed} {nights} loginHref={__PREVIEW__ ? `${base}/login/` : '/auth/login'} />
