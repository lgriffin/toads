<script lang="ts">
  import { characterQuery, MIN_CHARACTER_QUERY, type CharacterMatch } from '$lib/api';
  import { CLASSES } from '$lib/comp';

  // One setup step's character picker: search the guild's logs by name and pick a match, or, when the character has
  // not raided with us yet, name it with its class. `id` keeps the step's fields apart from the other picker's.
  let {
    id,
    action,
    heldAction,
    busy = false,
    mine = new Set<number>(),
    search,
    onpick,
    onname
  }: {
    id: string;
    /** The pick button's words, such as "This is my main". */
    action: string;
    /** The button's words for a character the member already holds; without it, those say "Yours". */
    heldAction?: string;
    busy?: boolean;
    /** Characters the member already holds or is waiting on. */
    mine?: ReadonlySet<number>;
    search: (query: string) => Promise<CharacterMatch[]>;
    onpick: (character: CharacterMatch) => void;
    /** Resolves true once saved; the form keeps what was typed until then. */
    onname: (name: string, wowClass: string) => Promise<boolean>;
  } = $props();

  let query = $state('');
  let matches = $state<CharacterMatch[]>([]);
  let searched = $state('');
  let searchFailed = $state(false);
  let naming = $state(false);
  let name = $state('');
  let wowClass = $state('');
  let timer: ReturnType<typeof setTimeout> | undefined;

  function oninput() {
    clearTimeout(timer);
    const q = characterQuery(query);
    if (q === searched && !searchFailed) return;
    matches = [];
    searched = '';
    searchFailed = false;
    if (q.length < MIN_CHARACTER_QUERY) return;
    timer = setTimeout(async () => {
      let found: CharacterMatch[] = [];
      let failed = false;
      try {
        found = await search(q);
      } catch {
        failed = true;
      }
      if (characterQuery(query) !== q) return;
      matches = found;
      searchFailed = failed;
      searched = q;
    }, 250);
  }

  function startNaming() {
    naming = true;
    name = characterQuery(query);
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    const n = characterQuery(name);
    if (n.length < MIN_CHARACTER_QUERY || !wowClass) return;
    if (!(await onname(n, wowClass))) return;
    naming = false;
    name = '';
    wowClass = '';
    query = '';
    matches = [];
    searched = '';
  }
</script>

<div class="picker">
  <div class="field">
    <label for="{id}-search">Character name</label>
    <input id="{id}-search" type="search" autocomplete="off" placeholder="e.g. Hopscotch" bind:value={query} {oninput} disabled={busy} />
  </div>
  {#if searchFailed}
    <p class="warn" role="status">Search isn't answering; try again, or name it below.</p>
  {:else if query.trim().length > 0 && query.trim().length < MIN_CHARACTER_QUERY}
    <p class="muted">Keep typing: at least {MIN_CHARACTER_QUERY} letters.</p>
  {:else if searched && matches.length === 0}
    <p class="muted" role="status">“{searched}” hasn't raided with the guild yet. Add it by name and class below.</p>
  {:else if matches.length > 0}
    <ul class="matches">
      {#each matches as m (m.id)}
        <li>
          <span>{m.name}{#if m.player_class}<span class="muted"> · {m.player_class}</span>{/if}</span>
          {#if mine.has(m.id) && heldAction}
            <button type="button" class="btn primary" disabled={busy} onclick={() => onpick(m)}>{heldAction}</button>
          {:else if mine.has(m.id)}
            <span class="muted">Yours</span>
          {:else}
            <button type="button" class="btn primary" disabled={busy} onclick={() => onpick(m)}>{action}</button>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}

  {#if naming}
    <form class="name" onsubmit={submit}>
      <div class="field">
        <label for="{id}-name">Name in game</label>
        <input id="{id}-name" autocomplete="off" maxlength="64" bind:value={name} disabled={busy} required />
      </div>
      <div class="field">
        <label for="{id}-class">Class</label>
        <select id="{id}-class" bind:value={wowClass} disabled={busy} required>
          <option value="" disabled>Pick a class</option>
          {#each CLASSES as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
        </select>
      </div>
      <div class="actions">
        <button class="btn primary" type="submit" disabled={busy || characterQuery(name).length < MIN_CHARACTER_QUERY || !wowClass}>Add it</button>
        <button class="btn" type="button" onclick={() => (naming = false)}>Cancel</button>
      </div>
    </form>
  {:else}
    <p class="new">
      <button type="button" class="link" disabled={busy} onclick={startNaming}>Not in the list? Add it by name and class</button>
      <span class="hint">for a new character, or one that hasn't raided with us yet</span>
    </p>
  {/if}
</div>

<style>
  .picker { display: grid; gap: 0.6rem; }
  .picker p { margin: 0; }
  .matches { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.25rem; }
  .matches li { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; padding: 0.25rem 0; flex-wrap: wrap; }
  .name { display: grid; gap: 0.6rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr)); align-items: end; }
  .actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .new { display: flex; flex-wrap: wrap; gap: 0.25rem 0.5rem; align-items: baseline; }
  .link { background: none; border: 0; padding: 0; color: var(--accent); font: inherit; text-decoration: underline; cursor: pointer; min-height: 2.75rem; }
  .link:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
