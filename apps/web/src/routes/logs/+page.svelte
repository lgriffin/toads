<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import { hubLogs } from '$lib/logs';
  import { previewLogs } from '$lib/preview/logs-fake';
  import { previewSession } from '$lib/preview/session.svelte';
  import LogsIndex from '$lib/components/LogsIndex.svelte';

  const backend = __PREVIEW__ ? previewLogs(() => previewSession.role) : hubLogs;
  const ready = $derived(__PREVIEW__ ? previewSession.ready : true);
</script>

<svelte:head><title>Logs · Toads</title></svelte:head>

<div class="logs">
  <h1>Logs</h1>
  <p class="lede muted">
    Every raid the guild has logged, with the analyser's breakdown. Pick the nights to compare: Wednesday, Sunday, or any
    other day the toads raided.
  </p>
  {#if ready}
    {#key previewSession.role}
      <LogsIndex {backend} />
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
</style>
