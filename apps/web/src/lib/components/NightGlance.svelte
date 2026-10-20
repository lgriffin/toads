<script lang="ts">
  import AnalyzerWidget from '$lib/components/AnalyzerWidget.svelte';
  import { ANALYZER_WIDGETS, catalogueTitle, isWide } from '$lib/home';
  import { PAGE_VERSION, widgetById, type AnalyzerPage } from '$lib/home-payload';
  import { logsError, type LogsBackend } from '$lib/logs';

  // The analyzer's raid widgets (last raid, recent raids, top damage, weekly healing, ...) built from one raid night's
  // raids, or from every raid when `night` is null. They used to sit on the hub home with every night mixed together; now only Logs draws them.
  // `dayOf`: the night each raid opens under when the viewer is one of its officers, so raid links open its full
  // analysis.
  let {
    backend,
    night,
    label,
    dayOf = () => null
  }: { backend: LogsBackend; night: string | null; label: string; dayOf?: (report: string) => string | null } =
    $props();

  let page = $state<AnalyzerPage | null>(null);
  let error = $state('');

  $effect(() => {
    backend.widgets(night).then(
      (p) => (page = p),
      (e) => (error = logsError(e))
    );
  });

  // In the hub's order; the API leaves out what this viewer may not see (the roster's badges for members).
  const ids = $derived(ANALYZER_WIDGETS.filter((w) => page?.widgets.some((p) => p.id === w.id)).map((w) => w.id));
</script>

<section class="glance" aria-labelledby="glance-h">
  <h2 id="glance-h">{label} at a glance</h2>
  {#if error}
    <p class="card bad" role="alert">{error}</p>
  {:else if !page}
    <p class="muted" role="status">Loading…</p>
  {:else if page.version !== PAGE_VERSION}
    <p class="muted">This hub cannot draw the analyzer's newer page yet.</p>
  {:else if !page.generated_at}
    <p class="card muted">
      {night ? 'This night’s numbers show' : 'These show'} once the worker has analysed the guild’s raids; it rebuilds
      them within the hour.
    </p>
  {:else}
    <div class="grid">
      {#each ids as id (id)}
        <div class="slot" class:wide={isWide(id)} data-widget={id}>
          <AnalyzerWidget
            widget={widgetById(page, id)}
            title={catalogueTitle(id)}
            missing="Nothing logged for this yet."
            {dayOf}
          />
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .glance { margin-bottom: 1.25rem; }
  h2 { margin: 0 0 0.6rem; }
  /* minmax(0, 1fr) and min-width: 0 let wide tables scroll inside their card instead of widening the page. */
  .slot { display: grid; grid-template-columns: minmax(0, 1fr); min-width: 0; }
  .slot > :global(*) { min-width: 0; }
  .slot.wide { grid-column: 1 / -1; }
</style>
