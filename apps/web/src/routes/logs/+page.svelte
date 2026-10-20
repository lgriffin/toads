<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { defaultNight, hubLogs, logNights, type LogNight } from '$lib/logs';
  import { previewLogs, previewViewer } from '$lib/preview/logs-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import LogsIndex from '$lib/components/LogsIndex.svelte';
  import NightGlance from '$lib/components/NightGlance.svelte';
  import NightTabs from '$lib/components/NightTabs.svelte';

  const backend = __PREVIEW__ ? previewLogs(() => previewSession.role) : hubLogs;

  type Viewer = Pick<Session, 'raid_days' | 'global_officer' | 'super_admin' | 'day_names'>;
  let viewer = $state<Viewer | null>(null);
  // undefined until the viewer is known, then the night of their Toad badge, or null for every raid.
  let night = $state<string | null | undefined>(undefined);
  let weekdays = $state<number[]>([]);
  // Each raid night's weekday as the API resolves it; empty until read (or when it cannot be), which leaves Every raid.
  let nightDays = $state<Record<string, number> | null>(null);

  onMount(() => {
    backend.nights().then(
      (n) => (nightDays = n),
      () => (nightDays = {})
    );
  });

  onMount(async () => {
    if (__PREVIEW__) return;
    try {
      viewer = await getSession();
    } catch {
      viewer = null;
    }
    // The page is behind sign-in; an unreadable session still shows every raid rather than nothing.
    viewer ??= { raid_days: [], global_officer: false, day_names: undefined };
  });

  // The preview's pretend sign-in can change view; each view opens on its own night.
  $effect(() => {
    if (!__PREVIEW__ || !previewSession.ready) return;
    viewer = previewViewer(previewSession.role);
    night = undefined;
  });

  const nights: LogNight[] = $derived(logNights(nightDays ?? {}, viewer?.day_names));

  // Pick the starting night once, when the viewer and the nights are first known; the tabs change it after that.
  $effect(() => {
    if (viewer && nightDays && night === undefined) pick(defaultNight(viewer, nights));
  });

  function pick(id: string | null) {
    night = id;
    const w = nights.find((n) => n.id === id)?.weekday;
    weekdays = w === undefined ? [] : [w];
  }

  const label = $derived(nights.find((n) => n.id === night)?.name ?? 'Every raid');
</script>

<svelte:head><title>Logs · Toads</title></svelte:head>

<div class="logs">
  <h1>Logs</h1>
  <p class="lede muted">
    Every raid the guild has logged, with the analyser's breakdown. Logs opens on your raid night; pick another night,
    or every raid, to compare.
  </p>
  {#if night !== undefined}
    {#key previewSession.role}
      <div class="tabs">
        <NightTabs {nights} value={night} onpick={pick} />
      </div>
      {#key night}
        <NightGlance {backend} {night} {label} />
      {/key}
      <LogsIndex {backend} bind:weekdays />
    {/key}
  {:else}
    <p class="muted" role="status">Loading…</p>
  {/if}
</div>

<style>
  .logs { font-family: 'Alegreya Sans', system-ui, sans-serif; font-size: 1.05rem; }
  .logs :global(h2) { font-family: 'Cinzel', Georgia, serif; font-weight: 600; color: var(--bronze-hi); letter-spacing: 0.03em; }
  h1 { font-family: 'Cinzel', Georgia, serif; color: var(--bronze-hi); letter-spacing: 0.04em; }
  .lede { margin: -0.5rem 0 1.25rem; max-width: 62ch; }
  .tabs { margin-bottom: 1.25rem; }
</style>
