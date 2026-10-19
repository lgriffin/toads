<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { applicationError, call, getSession, sendApplication } from '$lib/api';
  import { toApiBody, type ApplicationInput } from '$lib/application';
  import type { RecruitmentNeed } from '$lib/community';
  import { needFromApi, type ApiNeed } from '$lib/community-api';
  import { needs as sampleNeeds } from '$lib/mock/community';
  import { previewSession } from '$lib/preview/session.svelte';
  import Recruit from '$lib/Recruit.svelte';

  // The preview has no API: its pretend sign-in counts as being in the Discord, and nothing is sent.
  let apiSignedIn = $state<boolean | null>(null);
  let apiNeeds = $state<RecruitmentNeed[]>([]);
  const signedIn = $derived(__PREVIEW__ ? previewSession.role !== null : apiSignedIn);
  const needs = $derived(__PREVIEW__ ? sampleNeeds : apiNeeds);

  onMount(async () => {
    if (__PREVIEW__) return;
    const [session, open] = await Promise.all([
      getSession().catch(() => null),
      call<ApiNeed[]>(fetch, '/api/public/recruitment').catch(() => [] as ApiNeed[])
    ]);
    apiSignedIn = session !== null;
    apiNeeds = open.map(needFromApi);
  });

  async function send(input: ApplicationInput): Promise<{ status: string }> {
    if (__PREVIEW__) return { status: 'interviewing' };
    try {
      return await sendApplication(toApiBody(input));
    } catch (e) {
      throw applicationError(e);
    }
  }
</script>

<svelte:head><title>Apply · Toads</title></svelte:head>

<Recruit {signedIn} {needs} {send} loginHref={__PREVIEW__ ? `${base}/login/` : '/auth/login?next=recruit'} />
