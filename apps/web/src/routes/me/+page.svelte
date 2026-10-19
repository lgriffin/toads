<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { ApiError, myBadges } from '$lib/api';
  import type { MyBadges } from '$lib/badges';
  import { myAwards, titlesOf, type AwardOut } from '$lib/awards';
  import AwardsCard from '$lib/components/AwardsCard.svelte';
  import BadgesCard from '$lib/components/BadgesCard.svelte';
  import MemberToads from '$lib/components/MemberToads.svelte';
  import { getMe } from '$lib/me-context';
  import Me from '$lib/preview/Me.svelte';
  import { memberToads } from '$lib/toads';

  type Loaded = { kind: 'loading' } | { kind: 'ok'; value: MyBadges } | { kind: 'error'; message: string };
  let badges = $state<Loaded>({ kind: 'loading' });
  let awards = $state<AwardOut[] | null>(null);
  // The same toads the header shows beside the member's name, loaded once by the layout; the titles come from the
  // awards fetched here, so an award given since the layout loaded shows too.
  const me = getMe();
  const facts = $derived(awards ? { ...me(), titles: titlesOf(awards) } : me());
  const toads = $derived(memberToads(facts));

  // Every failure lands in the page as a message; nothing here throws to the error page.
  onMount(async () => {
    if (__PREVIEW__) return;
    myAwards()
      .then((a) => (awards = a))
      .catch(() => (awards = []));
    try {
      badges = { kind: 'ok', value: await myBadges() };
    } catch (e) {
      const message =
        e instanceof ApiError && e.status === 401
          ? 'Sign in with Discord to see your badges.'
          : 'Could not load your badges; try again later.';
      badges = { kind: 'error', message };
    }
  });
</script>

{#if __PREVIEW__}
  <Me />
  <p><a href="{base}/me/claim">Claim a character</a> · <a href="{base}/me/settings">Your settings</a></p>
{:else}
  <h1>Your performance <MemberToads {...facts} size={40} /></h1>
  <p>
    Claim your characters and see how each raid went for you against the guild median for your role.
    The seven charts from the build spec arrive in milestone H3.
  </p>
  {#if badges.kind === 'ok'}
    <BadgesCard mine={badges.value} />
  {:else}
    <section class="card" aria-labelledby="badges-h">
      <h2 id="badges-h">Your badges</h2>
      {#if badges.kind === 'loading'}
        <p class="muted" role="status">Loading…</p>
      {:else}
        <p class="err" role="alert">{badges.message}</p>
      {/if}
    </section>
  {/if}
  {#if awards}<AwardsCard {awards} {toads} />{/if}
  <p><a href="{base}/me/claim">Claim your characters</a> · <a href="{base}/me/settings">Your name and Warcraft Logs key</a></p>
{/if}
