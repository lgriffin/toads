<script lang="ts">
  import { replaceState } from '$app/navigation';
  import { onMount } from 'svelte';
  import { ApiError, getSession, type Session } from '$lib/api';
  import ReferenceView from '$lib/components/ReferenceView.svelte';
  import Reference from '$lib/preview/Reference.svelte';
  import {
    comparisonKey,
    deleteReference,
    disconnectReferenceLogin,
    getComparison,
    getReferenceOverview,
    hasPendingJobs,
    importReference,
    loginNotice,
    pickDay,
    referenceError,
    requestComparison,
    setReferenceLabel,
    startReferenceLogin,
    type ComparisonResponse,
    type ReferenceActions,
    type ReferenceJob,
    type ReferenceOverview
  } from '$lib/reference';

  const POLL_MS = 4000;

  type View =
    | { kind: 'loading' }
    | { kind: 'signed-out' }
    | { kind: 'not-officer' }
    | { kind: 'error'; message: string }
    | { kind: 'ready'; session: Session };

  let view = $state<View>({ kind: 'loading' });
  let day = $state('');
  let overview = $state<ReferenceOverview | null>(null);
  let comparison = $state<ComparisonResponse | null>(null);
  let openKey = $state<string | null>(null);
  let busy = $state(false);
  let message = $state('');
  let error = $state('');

  let pending = $derived(overview ? hasPendingJobs(overview.jobs) : false);

  function fail(e: unknown) {
    if (e instanceof ApiError && e.status === 401) view = { kind: 'signed-out' };
    else if (e instanceof ApiError && e.status === 403) view = { kind: 'not-officer' };
    else error = referenceError(e);
  }

  /** Loads the open comparison when it is built and newer than the one shown. */
  async function syncComparison() {
    if (!overview || !openKey) return;
    const entry = overview.comparisons.find((c) => comparisonKey(c.guild_report, c.reference_report) === openKey);
    if (!entry || (comparison && comparison.generated_at >= entry.generated_at)) return;
    const loaded = await getComparison(day, entry.guild_report, entry.reference_report);
    if (loaded && comparisonKey(entry.guild_report, entry.reference_report) === openKey) comparison = loaded;
  }

  // Bumped by every refresh and write; a response only lands while its number is still the latest, so a slow,
  // older overview can never replace a newer one (and hide a job that was just queued).
  let overviewSeq = 0;

  async function refresh() {
    if (!day) return;
    const seq = ++overviewSeq;
    const requestedDay = day;
    try {
      const next = await getReferenceOverview(requestedDay);
      if (seq !== overviewSeq || requestedDay !== day) return;
      overview = next;
      await syncComparison();
    } catch (e) {
      fail(e);
    }
  }

  // Poll while the worker has queued or running jobs; stop as soon as none are left.
  $effect(() => {
    if (!pending) return;
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  });

  /** Runs a write; a returned job goes to the top of the list at once so polling starts. */
  async function write(action: () => Promise<ReferenceJob | void>, done: string): Promise<boolean> {
    busy = true;
    error = '';
    message = '';
    overviewSeq += 1;
    try {
      const job = await action();
      if (job && overview) overview = { ...overview, jobs: [job, ...overview.jobs.filter((j) => j.id !== job.id)] };
      message = done;
      await refresh();
      return true;
    } catch (e) {
      fail(e);
      return false;
    } finally {
      busy = false;
    }
  }

  const actions: ReferenceActions = {
    async connect() {
      busy = true;
      error = '';
      try {
        const { authorize_url } = await startReferenceLogin(day);
        if (!/^https:\/\//.test(authorize_url)) throw new Error('unexpected login address');
        window.location.href = authorize_url;
        return true;
      } catch (e) {
        fail(e);
        busy = false;
        return false;
      }
    },
    disconnect: () => write(() => disconnectReferenceLogin(day), 'Disconnected the Warcraft Logs login.'),
    importReport: (report, label) =>
      write(() => importReference(day, report, label), 'Import queued; it appears under References when done.'),
    relabel: (report, label) => write(() => setReferenceLabel(day, report, label), 'Label change queued.'),
    remove: (report) => write(() => deleteReference(day, report), 'Delete queued.'),
    async compare(guildReport, referenceReport) {
      openKey = comparisonKey(guildReport, referenceReport);
      comparison = null;
      return write(
        () => requestComparison(day, guildReport, referenceReport),
        'Comparison queued; it opens below when built.'
      );
    },
    async open(guildReport, referenceReport) {
      const key = comparisonKey(guildReport, referenceReport);
      openKey = key;
      comparison = null;
      error = '';
      message = 'Loading the comparison…';
      try {
        const loaded = await getComparison(day, guildReport, referenceReport);
        // The officer may have opened another comparison while this one loaded; theirs wins.
        if (openKey !== key) return false;
        comparison = loaded;
        message = loaded ? '' : 'That comparison is not built yet; compare the two raids to build it.';
        return loaded !== null;
      } catch (e) {
        if (openKey !== key) return false;
        message = '';
        fail(e);
        return false;
      }
    }
  };

  async function switchDay(next: string) {
    day = next;
    overview = null;
    comparison = null;
    openKey = null;
    message = '';
    error = '';
    const url = new URL(window.location.href);
    url.searchParams.set('day', next);
    url.searchParams.delete('login');
    replaceState(url, {});
    await refresh();
  }

  onMount(async () => {
    if (__PREVIEW__) return;
    const url = new URL(window.location.href);
    try {
      const session = await getSession();
      if (!session) {
        view = { kind: 'signed-out' };
        return;
      }
      const picked = pickDay(session, url.searchParams.get('day'));
      if (!picked) {
        view = { kind: 'not-officer' };
        return;
      }
      view = { kind: 'ready', session };
      message = loginNotice(url.searchParams.get('login'));
      if (url.searchParams.has('login')) {
        // Drop the one-time notice from the address so a reload does not repeat it.
        url.searchParams.delete('login');
        replaceState(url, {});
      }
      day = picked;
      await refresh();
    } catch (e) {
      view = e instanceof ApiError && e.status === 401 ? { kind: 'signed-out' } : { kind: 'error', message: referenceError(e) };
    }
  });
</script>

<svelte:head><title>Reference comparison · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Reference />
{:else}
  <h1>Reference comparison</h1>
  {#if view.kind === 'loading'}
    <p class="muted" role="status">Loading…</p>
  {:else if view.kind === 'signed-out'}
    <section class="card" aria-labelledby="signin-h">
      <h2 id="signin-h">Members only</h2>
      <p>Sign in with Discord to open the officer tools.</p>
      <a class="btn primary" href="/auth/login" data-sveltekit-reload>Log in with Discord</a>
    </section>
  {:else if view.kind === 'not-officer'}
    <p>Reference comparisons are for officers only.</p>
  {:else if view.kind === 'error'}
    <p class="err" role="alert">{view.message}</p>
  {:else}
    <p class="muted">Compare one of our raids with another guild's, boss by boss and class by class.</p>
    {#if view.session.officer_days.length > 1}
      <div class="field day">
        <label for="ref-day">Raid day</label>
        <select id="ref-day" value={day} onchange={(e) => switchDay(e.currentTarget.value)} disabled={busy}>
          {#each view.session.officer_days as d}<option value={d}>{d}</option>{/each}
        </select>
      </div>
    {/if}
    {#if overview}
      <ReferenceView {overview} {comparison} {openKey} {busy} {message} {error} {actions} />
    {:else if error}
      <p class="err" role="alert">{error}</p>
    {:else}
      <p class="muted" role="status">Loading…</p>
    {/if}
  {/if}
{/if}

<style>
  .day { max-width: 16rem; margin-bottom: 1rem; }
</style>
