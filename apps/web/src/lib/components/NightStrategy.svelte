<script lang="ts">
  import { base } from '$app/paths';
  import { addedLine, docOptions, hubStrategy, strategyError, type Library, type NightStrategy } from '$lib/strategy';
  import { previewStrategy } from '$lib/preview/strategy-fake';
  import DocPicker from './DocPicker.svelte';

  // The Raid page's strategy (docs/strategy.md): the Google Docs the night pins for its raiders, in order. The night's
  // officers pin them here, from the docs officers add to each raid on the officers' Strategy page.
  // `dusk` paints the band dark, so it alternates with the bands around it on the page.
  let { day, name, officer = false, dusk = false }: { day: string; name: string; officer?: boolean; dusk?: boolean } =
    $props();

  const backend = __PREVIEW__ ? previewStrategy : hubStrategy();
  let night = $state<NightStrategy | null>(null);
  let library = $state<Library | null>(null);
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
    // Only the night's officers pin its docs, so only they need every raid's docs.
    if (officer && !library)
      backend.library().then(
        (l) => (library = l),
        () => (problem = 'Could not load the raids’ docs to pin from; try again later.')
      );
  });

  async function pin(picked: string[]): Promise<boolean> {
    // The night this pin is for: the viewer may switch nights before the answer comes back.
    const pinning = day;
    saving = true;
    problem = '';
    try {
      const answer = await backend.setNight(pinning, picked.map(Number));
      if (pinning === day) night = answer;
      return true;
    } catch (err) {
      if (pinning === day) problem = strategyError(err);
      return false;
    } finally {
      saving = false;
    }
  }

  const options = $derived(library ? docOptions(library) : []);
</script>

<section class="band" class:dusk aria-labelledby="strategy-h">
  <div class="head">
    <h2 id="strategy-h">Strategy</h2>
    {#if night?.docs.length}
      <p>The strategy docs {name}’s officers pinned for tonight’s raids. They open in Google Drive.</p>
    {:else if night}
      <p>{name}’s officers have not pinned a strategy doc yet.</p>
    {/if}
  </div>
  {#if failed}
    <p class="err" role="alert">Could not load the night’s strategy; try again later.</p>
  {:else if night === null}
    <p class="muted" role="status">Loading…</p>
  {:else if night.docs.length}
    <ul class="docs">
      {#each night.docs as d (d.doc.id)}
        <li class="doc">
          <a class="medal" href={d.doc.url} target="_blank" rel="noopener noreferrer">Open the {d.raid.short} strategy</a>
          <p>
            <strong>{d.doc.title}</strong>
            <span class="muted">{d.raid.name} · {addedLine(d.doc)}</span>
          </p>
        </li>
      {/each}
    </ul>
  {/if}
  {#if officer && night}
    <div class="pick">
      <span class="label" aria-hidden="true">Docs pinned for {name}</span>
      <DocPicker
        label="Docs pinned for {name}"
        {options}
        chosen={night.docs.map((d) => String(d.doc.id))}
        disabled={saving || !library}
        onchange={pin}
      />
      <a href="{base}/officers/strategy/">Add docs to a raid</a>
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
