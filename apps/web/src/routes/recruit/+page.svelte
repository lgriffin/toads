<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { applicationError, call, getSession, myApplications, sendApplication } from '$lib/api';
  import { roomState, toApiBody, type ApplicationInput, type RaidNight, type RoomState } from '$lib/application';
  import type { RecruitmentNeed } from '$lib/community';
  import { needFromApi, type ApiNeed } from '$lib/community-api';
  import { needs as sampleNeeds } from '$lib/mock/community';
  import { RAID_NIGHTS } from '$lib/nights';
  import { previewSession } from '$lib/preview/session.svelte';
  import Recruit from '$lib/Recruit.svelte';

  // The preview has no API: its pretend sign-in counts as being in the Discord, and nothing is sent.
  let apiSignedIn = $state<boolean | null>(null);
  let apiNeeds = $state<RecruitmentNeed[]>([]);
  let apiNights = $state<RaidNight[]>([]);
  const signedIn = $derived(__PREVIEW__ ? previewSession.role !== null : apiSignedIn);
  const needs = $derived(__PREVIEW__ ? sampleNeeds : apiNeeds);
  const nights = $derived(__PREVIEW__ ? [...RAID_NIGHTS] : apiNights);

  onMount(async () => {
    if (__PREVIEW__) return;
    const [session, open, offered] = await Promise.all([
      getSession().catch(() => null),
      call<ApiNeed[]>(fetch, '/api/public/recruitment').catch(() => [] as ApiNeed[]),
      // An older hub has no nights to offer; the form then leaves the night out.
      call<RaidNight[]>(fetch, '/api/public/raid-nights').catch(() => [] as RaidNight[])
    ]);
    apiSignedIn = session !== null;
    apiNeeds = open.map(needFromApi);
    apiNights = offered;
  });

  async function send(input: ApplicationInput): Promise<{ id: number; status: string }> {
    if (__PREVIEW__) return { id: 0, status: 'interviewing' };
    try {
      return await sendApplication(toApiBody(input));
    } catch (e) {
      throw applicationError(e);
    }
  }

  async function room(id: number): Promise<RoomState> {
    if (__PREVIEW__) return { kind: 'opening' };
    return roomState(await myApplications(), id);
  }
</script>

<svelte:head><title>Apply · Toads</title></svelte:head>

<Recruit {signedIn} {needs} {nights} {send} {room} loginHref={__PREVIEW__ ? `${base}/login/` : '/auth/login?next=recruit'} />
