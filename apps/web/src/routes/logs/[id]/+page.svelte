<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import { onMount } from 'svelte';
  import { base } from '$app/paths';
  import { hubLogs } from '$lib/logs';
  import { previewLogs } from '$lib/preview/logs-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import RaidLog from '$lib/components/RaidLog.svelte';

  let { data } = $props();
  const backend = __PREVIEW__ ? previewLogs(() => previewSession.role) : hubLogs;
  // The raid day a raid-day officer reads the full analysis under (the list's link carries it); the API checks it.
  let day = $state<string | null | undefined>(undefined);
  onMount(() => {
    day = new URLSearchParams(window.location.search).get('day');
  });
  const ready = $derived(day !== undefined && (__PREVIEW__ ? previewSession.ready : true));
</script>

<svelte:head><title>Raid log · Toads</title></svelte:head>

<div class="raid-log">
  <p class="back"><a href="{base}/logs/">← Logs</a></p>
  {#if ready}
    {#key `${data.report}|${day}|${previewSession.role}`}
      <RaidLog {backend} report={data.report} day={day ?? null} />
    {/key}
  {:else}
    <p class="muted" role="status">Loading…</p>
  {/if}
</div>

<style>
  .raid-log { font-family: 'Alegreya Sans', system-ui, sans-serif; font-size: 1.05rem; }
  .raid-log :global(h1) { font-family: 'Cinzel', Georgia, serif; color: var(--bronze-hi); letter-spacing: 0.04em; }
  .raid-log :global(h2) { font-family: 'Cinzel', Georgia, serif; font-weight: 600; color: var(--bronze-hi); letter-spacing: 0.03em; }
  .back { margin: 0 0 0.5rem; }
</style>
