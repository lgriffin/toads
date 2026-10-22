<script lang="ts">
  import { base } from '$app/paths';
  import { hubStrategy, pinnedLine, strategyError, type NightStrategy, type Raid } from '$lib/strategy';
  import { PREVIEW_RAIDS, previewStrategy } from '$lib/preview/strategy-fake';

  // The Raid page's strategy (docs/strategy.md): the raid the night is running and the Google Doc pinned to that raid.
  // The night's officers pick the raid here; officers pin the docs on the officers' Strategy page.
  // `dusk` paints the band dark, so it alternates with the bands around it on the page.
  let { day, name, officer = false, dusk = false }: { day: string; name: string; officer?: boolean; dusk?: boolean } =
    $props();

  const backend = __PREVIEW__ ? previewStrategy : hubStrategy();
  let night = $state<NightStrategy | null>(null);
  let raids = $state<Raid[]>(__PREVIEW__ ? PREVIEW_RAIDS : []);
  let failed = $state(false);
  let saving = $state(false);
  let problem = $state('');

  $effect(() => {
    const showing = day;
    night = null;
    failed = false;
    problem = '';
    backend.night(showing).then(
      (n) => {
        if (showing === day) night = n;
      },
      () => {
        if (showing === day) failed = true;
      }
    );
  });
  $effect(() => {
    // Only the night's officers pick its raid, so only they need the raid list.
    if (officer && !raids.length) backend.library().then((l) => (raids = l.raids.map((r) => r.raid)), () => {});
  });

  async function choose(e: Event) {
    const value = (e.currentTarget as HTMLSelectElement).value;
    saving = true;
    problem = '';
    try {
      night = await backend.setNight(day, value || null);
    } catch (err) {
      problem = strategyError(err);
    } finally {
      saving = false;
    }
  }
</script>

<section class="band" class:dusk aria-labelledby="strategy-h">
  <div class="head">
    <h2 id="strategy-h">Strategy</h2>
    {#if night?.raid}
      <p>{name} is running {night.raid.name}. The officers keep one strategy doc per raid in Google Drive.</p>
    {:else if night}
      <p>{name}’s officers have not said which raid the night is running yet.</p>
    {/if}
  </div>
  {#if failed}
    <p class="err" role="alert">Could not load the night’s strategy; try again later.</p>
  {:else if night === null}
    <p class="muted" role="status">Loading…</p>
  {:else if night.raid && night.pinned}
    <div class="doc">
      <a class="medal" href={night.pinned.url} target="_blank" rel="noopener noreferrer">
        Open the {night.raid.short} strategy
      </a>
      <p>
        <strong>{night.pinned.title}</strong>
        <span class="muted">{pinnedLine(night.pinned)} · opens in Google Drive</span>
      </p>
    </div>
  {:else if night.raid}
    <p class="muted">No strategy doc is pinned for {night.raid.name} yet.</p>
  {/if}
  {#if officer && night}
    <div class="pick">
      <label for="night-raid-{day}">Raid {name} is running</label>
      <select id="night-raid-{day}" value={night.raid?.id ?? ''} disabled={saving || !raids.length} onchange={choose}>
        <option value="">Not decided yet</option>
        {#each raids as r (r.id)}
          <option value={r.id}>{r.short}: {r.name}</option>
        {/each}
      </select>
      <a href="{base}/officers/strategy/">Strategy docs for every raid</a>
    </div>
    {#if problem}<p class="err" role="alert">{problem}</p>{/if}
  {/if}
</section>

<style>
  .doc { display: grid; gap: 0.6rem; justify-items: start; }
  .doc p { margin: 0; display: grid; gap: 0.1rem; }
  .pick { display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; align-items: center; }
  .pick label { font-weight: 700; }
  .pick select { font: inherit; padding: 0.35rem 0.5rem; border-radius: 6px; max-width: 100%; }
</style>
