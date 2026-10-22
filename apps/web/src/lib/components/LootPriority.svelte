<script lang="ts">
  import {
    LINE_LIMIT,
    MIN_QUERY,
    NOTE_LIMIT,
    itemFacts,
    lootError,
    ordinal,
    qualityName,
    shifted,
    wowheadItem,
    type CatalogueItem,
    type LootBackend,
    type LootEntry,
    type RosterMember
  } from '$lib/loot';

  // One raid night's loot priority (docs/loot.md): the big-ticket items its officers decide on, who is first, second
  // and third in line for each, and who has received theirs. Shown to that night's officers only; the API checks the
  // permission (manage_loot) on every call.
  let { backend, day, dayName }: { backend: LootBackend; day: string; dayName: string } = $props();

  let items = $state<LootEntry[]>([]);
  let roster = $state<RosterMember[]>([]);
  let catalogue = $state('');
  let loaded = $state(false);
  let loadError = $state('');
  let message = $state('');
  let failed = $state(false);
  let busy = $state(false);

  // Item search.
  let query = $state('');
  let results = $state<CatalogueItem[]>([]);
  let searching = $state(false);
  let searched = $state('');

  // Per item: the member picked to join its line, the note being edited, and a pending removal.
  let picks = $state<Record<number, number | ''>>({});
  let editingNote = $state<number | null>(null);
  let noteDraft = $state('');
  let confirmRemove = $state<number | null>(null);

  const onList = $derived(new Set(items.map((e) => e.item_id)));

  async function load() {
    const night = day;
    try {
      const loot = await backend.loot(night);
      if (night !== day) return;
      items = loot.items;
      roster = loot.roster;
      catalogue = loot.catalogue;
      loadError = '';
    } catch (e) {
      if (night !== day) return;
      items = [];
      loadError = lootError(e);
    } finally {
      if (night === day) loaded = true;
    }
  }
  $effect(() => {
    void day;
    items = [];
    roster = [];
    loaded = false;
    loadError = '';
    message = '';
    query = '';
    results = [];
    load();
  });

  // Search as the officer types, a moment after they stop; a late answer for an older query is dropped.
  let timer: ReturnType<typeof setTimeout> | undefined;
  function typed() {
    clearTimeout(timer);
    const q = query.trim();
    if (q.length < MIN_QUERY) {
      results = [];
      searched = '';
      return;
    }
    timer = setTimeout(() => search(q), 250);
  }
  async function search(q: string) {
    const night = day;
    searching = true;
    try {
      const found = await backend.search(night, q);
      if (night === day && q === query.trim()) {
        results = found;
        searched = q;
      }
    } catch (e) {
      if (night === day) say(lootError(e), true);
    } finally {
      searching = false;
    }
  }

  function say(text: string, error = false) {
    message = text;
    failed = error;
  }

  /** Runs a change against the night shown now; `still()` turns false once the page has switched nights. */
  async function attempt(action: (still: () => boolean) => Promise<void>) {
    const night = day;
    const still = () => night === day;
    busy = true;
    try {
      await action(still);
    } catch (e) {
      if (!still()) return;
      say(lootError(e), true);
      await load();
    } finally {
      busy = false;
    }
  }

  const put = (updated: LootEntry) => (items = items.map((e) => (e.id === updated.id ? updated : e)));

  function add(item: CatalogueItem) {
    attempt(async (still) => {
      const entry = await backend.add(day, item.id);
      if (!still()) return;
      items = [...items, entry];
      say(`Added ${entry.item_name}. Now put ${dayName}’s raiders in line for it.`);
    });
  }

  function line(entry: LootEntry, ids: number[], done: string) {
    attempt(async (still) => {
      const updated = await backend.line(day, entry.id, ids);
      if (!still()) return;
      put(updated);
      say(done);
    });
  }

  const ids = (entry: LootEntry) => entry.recipients.map((r) => r.member_id);

  function join(entry: LootEntry) {
    const member = picks[entry.id];
    if (member === '' || member === undefined) return;
    const name = roster.find((m) => m.member_id === member)?.name ?? 'them';
    picks[entry.id] = '';
    line(entry, [...ids(entry), member], `Put ${name} ${ordinal(entry.recipients.length + 1)} in line for ${entry.item_name}.`);
  }

  function received(entry: LootEntry, memberId: number, name: string, yes: boolean) {
    attempt(async (still) => {
      const updated = await backend.received(day, entry.id, memberId, yes);
      if (!still()) return;
      put(updated);
      say(yes ? `${name} has ${entry.item_name}.` : `${name} is waiting for ${entry.item_name} again.`);
    });
  }

  function editNote(entry: LootEntry) {
    editingNote = entry.id;
    noteDraft = entry.note;
  }

  function saveNote(event: SubmitEvent, entry: LootEntry) {
    event.preventDefault();
    attempt(async (still) => {
      const updated = await backend.note(day, entry.id, noteDraft);
      if (!still()) return;
      put(updated);
      editingNote = null;
      say(`Saved the note on ${entry.item_name}.`);
    });
  }

  function remove(entry: LootEntry) {
    if (confirmRemove !== entry.id) {
      confirmRemove = entry.id;
      return;
    }
    attempt(async (still) => {
      await backend.remove(day, entry.id);
      if (!still()) return;
      items = items.filter((e) => e.id !== entry.id);
      confirmRemove = null;
      say(`Took ${entry.item_name} off the list.`);
    });
  }

  const available = (entry: LootEntry) => roster.filter((m) => !entry.recipients.some((r) => r.member_id === m.member_id));
</script>

<section class="loot" aria-labelledby="loot-h-{day}">
  <div class="head">
    <h2 id="loot-h-{day}">Loot priority</h2>
    <p class="muted">
      The big-ticket items {dayName}’s officers decide on, and who is first, second and third in line for each. Mark someone
      received and the next one in line is up. Only {dayName} officers see it.
    </p>
  </div>

  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
    <button class="btn" type="button" onclick={() => load()}>Try again</button>
  {:else if !loaded}
    <p class="muted" role="status">Loading the loot list…</p>
  {:else}
    <div class="search" role="search">
      <label for="loot-q-{day}">Find an item</label>
      <input
        id="loot-q-{day}"
        type="search"
        bind:value={query}
        oninput={typed}
        placeholder="Thunderfury, Head of Onyxia…"
        autocomplete="off"
        maxlength="80"
      />
      {#if searching}<p class="muted small" role="status">Searching…</p>{/if}
      {#if searched && !searching}
        {#if results.length === 0}
          <p class="muted small" role="status">No items match “{searched}”.</p>
        {:else}
          <ul class="results" aria-label="Items matching {searched}">
            {#each results as item (item.id)}
              <li>
                <span class="item q{item.quality}">
                  <a href={wowheadItem(item.id)} target="_blank" rel="noopener noreferrer">{item.name}</a>
                  <span class="facts">
                    {[qualityName(item.quality), itemFacts(item), `id ${item.id}`].filter(Boolean).join(' · ')}{#if item.flavour === 'Vanilla'}
                      · Classic data{/if}
                  </span>
                </span>
                <button class="btn" type="button" disabled={busy || onList.has(item.id)} onclick={() => add(item)}>
                  {onList.has(item.id) ? 'On the list' : 'Add'}<span class="sr-only">: {item.name}</span>
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      {/if}
    </div>

    <p class="status" class:err={failed} class:ok={!failed && message} role="status">{message}</p>

    {#if items.length === 0}
      <p class="muted empty">No items on {dayName}’s list yet. Find the first big-ticket item above.</p>
    {/if}

    <ul class="entries">
      {#each items as entry (entry.id)}
        <li class="entry">
          <div class="top">
            <span class="item q{entry.quality}">
              <a href={wowheadItem(entry.item_id)} target="_blank" rel="noopener noreferrer">{entry.item_name}</a>
              <span class="facts">{[qualityName(entry.quality), itemFacts(entry)].filter(Boolean).join(' · ')}</span>
            </span>
            <button class="btn danger small" type="button" disabled={busy} onclick={() => remove(entry)}>
              {confirmRemove === entry.id ? 'Take off for good' : 'Take off'}<span class="sr-only">: {entry.item_name}</span>
            </button>
          </div>

          {#if editingNote === entry.id}
            <form class="note-form" onsubmit={(e) => saveNote(e, entry)} aria-label="Note on {entry.item_name}">
              <label for="loot-note-{entry.id}">Note</label>
              <textarea id="loot-note-{entry.id}" rows="2" bind:value={noteDraft} maxlength={NOTE_LIMIT}></textarea>
              <div class="row">
                <button class="btn primary small" type="submit" disabled={busy}>Save note</button>
                <button class="btn small" type="button" onclick={() => (editingNote = null)}>Cancel</button>
              </div>
            </form>
          {:else}
            <p class="note">
              {#if entry.note}{entry.note}{/if}
              <button class="link" type="button" onclick={() => editNote(entry)}>
                {entry.note ? 'Edit note' : 'Add a note'}<span class="sr-only">: {entry.item_name}</span>
              </button>
            </p>
          {/if}

          {#if entry.recipients.length === 0}
            <p class="muted small">Nobody in line yet.</p>
          {:else}
            <ol class="line" aria-label="In line for {entry.item_name}">
              {#each entry.recipients as r, i (r.member_id)}
                <li class:got={r.received_at} class:up={r.next_up}>
                  <span class="rank">{ordinal(r.rank)}</span>
                  <span class="who">{r.name || 'Former member'}</span>
                  {#if r.next_up}<span class="tag">Next up</span>{/if}
                  {#if r.received_at}<span class="tag done">Received</span>{/if}
                  <span class="spacer"></span>
                  <button
                    class="step"
                    type="button"
                    disabled={busy}
                    onclick={() => received(entry, r.member_id, r.name || 'They', !r.received_at)}
                  >
                    {r.received_at ? 'Undo received' : 'Mark received'}<span class="sr-only">: {r.name}</span>
                  </button>
                  <button
                    class="step"
                    type="button"
                    disabled={busy || i === 0}
                    onclick={() => line(entry, shifted(ids(entry), r.member_id, -1), `Moved ${r.name} up for ${entry.item_name}.`)}
                    aria-label="Move {r.name} up"
                  >↑</button>
                  <button
                    class="step"
                    type="button"
                    disabled={busy || i === entry.recipients.length - 1}
                    onclick={() => line(entry, shifted(ids(entry), r.member_id, 1), `Moved ${r.name} down for ${entry.item_name}.`)}
                    aria-label="Move {r.name} down"
                  >↓</button>
                  <button
                    class="step"
                    type="button"
                    disabled={busy}
                    onclick={() =>
                      line(
                        entry,
                        ids(entry).filter((m) => m !== r.member_id),
                        `Took ${r.name || 'them'} out of line for ${entry.item_name}.`
                      )}
                    aria-label="Take {r.name} out of line"
                  >✕</button>
                </li>
              {/each}
            </ol>
          {/if}

          {#if entry.recipients.length < LINE_LIMIT}
            <div class="join">
              <label class="sr-only" for="loot-join-{entry.id}">Add to the line for {entry.item_name}</label>
              <select id="loot-join-{entry.id}" bind:value={picks[entry.id]}>
                <option value="">{ordinal(entry.recipients.length + 1)} in line…</option>
                {#each available(entry) as m (m.member_id)}<option value={m.member_id}>{m.name}</option>{/each}
              </select>
              <button
                class="btn small"
                type="button"
                disabled={busy || picks[entry.id] === '' || picks[entry.id] === undefined}
                onclick={() => join(entry)}>Add to line</button
              >
            </div>
          {/if}
        </li>
      {/each}
    </ul>

    {#if roster.length === 0}
      <p class="muted small">Nobody holds {dayName}’s raid role yet, so there is nobody to put in line.</p>
    {/if}
    {#if catalogue}<p class="muted small source">Item data: {catalogue}. Links open Wowhead.</p>{/if}
  {/if}
</section>

<style>
  .loot { display: grid; gap: 1rem; }
  .head { display: grid; gap: 0.25rem; }
  .head h2 { margin: 0; font-family: 'Cinzel', Georgia, serif; font-size: 1.3rem; color: var(--bronze-hi); letter-spacing: 0.03em; }
  .head p { margin: 0; max-width: 62ch; }
  .search { display: grid; gap: 0.4rem; max-width: 40rem; }
  .search input { width: 100%; }
  .small { font-size: 0.85rem; margin: 0; }
  .status { margin: 0; min-height: 1.2em; font-size: 0.9rem; }
  .empty { margin: 0; }
  ul, ol { list-style: none; margin: 0; padding: 0; }
  .results { display: grid; gap: 0.35rem; max-height: 22rem; overflow-y: auto; }
  .results li, .top {
    display: flex;
    gap: 0.6rem;
    align-items: center;
    justify-content: space-between;
  }
  .results li { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 0.45rem 0.6rem; }
  .item { display: grid; gap: 0.1rem; min-width: 0; }
  .item a { font-weight: 700; text-decoration: none; overflow-wrap: anywhere; color: var(--cream); }
  .item a:hover { text-decoration: underline; }
  /* The game's quality colours, blended toward the text colour so they read on both themes. */
  .q2 a { color: color-mix(in srgb, #1eff00 55%, var(--cream)); }
  .q3 a { color: color-mix(in srgb, #0070dd 70%, var(--cream)); }
  .q4 a { color: color-mix(in srgb, #a335ee 75%, var(--cream)); }
  .q5 a, .q6 a { color: color-mix(in srgb, #ff8000 75%, var(--cream)); }
  .facts { font-size: 0.8rem; color: var(--muted); }
  .entries { display: grid; gap: 0.8rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); align-items: start; }
  .entry {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 0.8rem;
    display: grid;
    gap: 0.6rem;
  }
  .note { margin: 0; font-size: 0.88rem; white-space: pre-line; display: flex; flex-wrap: wrap; gap: 0.25rem 0.6rem; }
  .note-form { display: grid; gap: 0.35rem; }
  .note-form textarea { width: 100%; }
  .row, .join { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
  .join select { flex: 1 1 10rem; min-width: 0; }
  .line { display: grid; gap: 0.3rem; }
  .line li {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 0.5rem;
    align-items: center;
    padding: 0.35rem 0.5rem;
    border-radius: 6px;
    background: color-mix(in srgb, var(--ink) 45%, transparent);
  }
  .line li.up { outline: 1px solid color-mix(in srgb, var(--teal) 60%, transparent); }
  .line li.got .who { color: var(--muted); text-decoration: line-through; }
  .rank { font-variant-numeric: tabular-nums; font-weight: 700; color: var(--bronze-hi); min-width: 2.4rem; }
  .who { color: var(--cream); }
  .tag { font-size: 0.75rem; padding: 0.05rem 0.45rem; border-radius: 999px; background: color-mix(in srgb, var(--teal) 25%, transparent); color: var(--cream); }
  .tag.done { background: color-mix(in srgb, var(--muted) 25%, transparent); }
  .spacer { flex: 1; }
  .step {
    background: none;
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--muted);
    font: inherit;
    font-size: 0.8rem;
    padding: 0.15rem 0.6rem;
    cursor: pointer;
  }
  .step:hover:not(:disabled) { border-color: var(--teal); color: var(--cream); }
  .step:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn.small { padding: 0.3rem 0.65rem; font-size: 0.85rem; }
  .link { background: none; border: 0; padding: 0; color: var(--teal); font: inherit; font-size: 0.85rem; cursor: pointer; text-decoration: underline; }
  .source { margin-top: 0.25rem; }
</style>
