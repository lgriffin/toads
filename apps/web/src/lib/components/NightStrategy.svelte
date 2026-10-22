<script lang="ts">
  import { base } from '$app/paths';
  import { hubStrategy, pinnedLine, strategyError, type NightStrategy, type Raid } from '$lib/strategy';
  import { PREVIEW_RAIDS, previewStrategy } from '$lib/preview/strategy-fake';
  import RaidPicker from './RaidPicker.svelte';

  // The Raid page's strategy (docs/strategy.md): each raid the night is running, in order, with its Google Doc (the
  // night's own doc for the raid, else the every-night one). The night's officers pick its raids here; officers pin the
  // docs on the officers' Strategy page.
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
    // Only the night's officers pick its raids, so only they need the raid list.
    if (officer && !raids.length)
      backend.library().then(
        (l) => (raids = l.raids.map((r) => r.raid)),
        () => (problem = 'Could not load the raids to pick from; try again later.')
      );
  });

  async function choose(picked: string[]) {
    // The night this pick is for: the viewer may switch nights before the answer comes back.
    const picking = day;
    saving = true;
    problem = '';
    try {
      const answer = await backend.setNight(picking, picked);
      if (picking === day) night = answer;
    } catch (err) {
      if (picking === day) problem = strategyError(err);
    } finally {
      saving = false;
    }
  }

  const running = $derived(night ? night.raids.map((r) => r.raid.name) : []);
</script>

<section class="band" class:dusk aria-labelledby="strategy-h">
  <div class="head">
    <h2 id="strategy-h">Strategy</h2>
    {#if running.length}
      <p>{name} is running {running.join(' then ')}. The officers keep the strategy docs in Google Drive.</p>
    {:else if night}
      <p>{name}’s officers have not said which raids the night is running yet.</p>
    {/if}
  </div>
  {#if failed}
    <p class="err" role="alert">Could not load the night’s strategy; try again later.</p>
  {:else if night === null}
    <p class="muted" role="status">Loading…</p>
  {:else if night.raids.length}
    <ul class="docs">
      {#each night.raids as r (r.raid.id)}
        <li class="doc">
          {#if r.pinned}
            <a class="medal" href={r.pinned.url} target="_blank" rel="noopener noreferrer">
              Open the {r.raid.short} strategy
            </a>
            <p>
              <strong>{r.pinned.title}</strong>
              <span class="muted">
                {pinnedLine(r.pinned)}{r.pinned.raid_day ? ` for ${name}` : ''} · opens in Google Drive
              </span>
            </p>
          {:else}
            <p><strong>{r.raid.short}</strong> <span class="muted">No strategy doc is pinned for {r.raid.name} yet.</span></p>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
  {#if officer && night}
    <div class="pick">
      <span class="label" aria-hidden="true">Raids {name} is running</span>
      <RaidPicker
        label="Raids {name} is running"
        {raids}
        chosen={night.raids.map((r) => r.raid.id)}
        disabled={saving || !raids.length}
        onchange={choose}
      />
      <a href="{base}/officers/strategy/">Strategy docs for every raid</a>
    </div>
    {#if problem}<p class="err" role="alert">{problem}</p>{/if}
  {/if}
</section>

<style>
  .docs { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); }
  .doc { display: grid; gap: 0.6rem; justify-items: start; align-content: start; }
  .doc p { margin: 0; display: grid; gap: 0.1rem; }
  .pick { display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; align-items: flex-start; }
  .pick > .label, .pick > a { padding-top: 0.4rem; }
  .pick .label { font-weight: 700; }
</style>
