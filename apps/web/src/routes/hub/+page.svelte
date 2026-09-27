<script lang="ts">
  import { onMount } from 'svelte';
  import { ApiError, getSession, raidTrend, type Session } from '$lib/api';
  import RaidTotals from '$lib/components/RaidTotals.svelte';
  import Hub from '$lib/preview/Hub.svelte';
  import { sheetsError, type RaidHeadline } from '$lib/sheets';

  type State =
    | { kind: 'loading' }
    | { kind: 'signed-out' }
    | { kind: 'error'; message: string }
    | { kind: 'ready'; session: Session; raids: RaidHeadline[] };

  let view = $state<State>({ kind: 'loading' });

  // Every failure lands in the page as a message; nothing here throws to the error page.
  onMount(async () => {
    if (__PREVIEW__) return;
    try {
      const session = await getSession();
      if (!session) {
        view = { kind: 'signed-out' };
        return;
      }
      view = { kind: 'ready', session, raids: await raidTrend() };
    } catch (e) {
      view = e instanceof ApiError && e.status === 401 ? { kind: 'signed-out' } : { kind: 'error', message: sheetsError(e) };
    }
  });
</script>

<svelte:head><title>Hub · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Hub />
{:else if view.kind === 'ready'}
  <h1>Your night, {view.session.display_name}</h1>
  <RaidTotals raids={view.raids} />
{:else}
  <h1>Toads Hub</h1>
  {#if view.kind === 'loading'}
    <p class="muted" role="status">Loading raid totals…</p>
  {:else if view.kind === 'signed-out'}
    <section class="card" aria-labelledby="signin-h">
      <h2 id="signin-h">Members only</h2>
      <p>Sign in with Discord to see the guild's raid totals.</p>
      <a class="btn primary" href="/auth/login" data-sveltekit-reload>Log in with Discord</a>
    </section>
  {:else}
    <p class="err" role="alert">{view.message}</p>
  {/if}
{/if}
