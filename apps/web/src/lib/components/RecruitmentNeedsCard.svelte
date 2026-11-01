<script lang="ts">
  import { classOf, specOf } from '$lib/comp';
  import {
    PRIORITIES,
    findSpec,
    needsError,
    picksOf,
    specLabel,
    specsLeft,
    type NeedPick,
    type NeedsBackend,
    type NightNeeds
  } from '$lib/recruiting';
  import type { NeedPriority } from '$lib/community';

  // One raid night's recruitment needs: the primary specs its officers want, which the homepage shows visitors who
  // pick this night. A group with nothing listed reads "Full for now" there. The API checks that the viewer runs this
  // night (manage_recruitment for the day); this card only shows itself to them.
  let { backend, day, night }: { backend: NeedsBackend; day: string; night: string } = $props();

  let current = $state<NightNeeds | null>(null);
  let loadError = $state('');
  let typed = $state('');
  let priority = $state<NeedPriority>('medium');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  const left = $derived(current ? specsLeft(current.needs) : []);
  const match = $derived(findSpec(typed, left));

  $effect(() => {
    backend
      .needs(day)
      .then((n) => {
        current = n;
        loadError = '';
      })
      .catch((e) => (loadError = needsError(e)));
  });

  async function save(picks: NeedPick[], done: string, clear = false) {
    busy = true;
    try {
      current = await backend.save(day, picks);
      message = done;
      failed = false;
      if (clear) typed = '';
    } catch (e) {
      message = needsError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }

  function add(event: SubmitEvent) {
    event.preventDefault();
    if (!current) return;
    if (!match) {
      message = typed.trim() ? `No single spec matches “${typed.trim()}”; pick one from the list.` : 'Type or pick a spec.';
      failed = true;
      return;
    }
    const label = specLabel(match);
    save([...picksOf(current.needs), { spec_id: match.id, priority }], `${night} is now recruiting ${label}.`, true);
  }

  const label = (specId: string) => {
    const s = specOf(specId);
    return s ? specLabel(s) : specId;
  };

  function setPriority(specId: string, to: NeedPriority) {
    if (!current) return;
    const picks = picksOf(current.needs).map((p) => (p.spec_id === specId ? { ...p, priority: to } : p));
    save(picks, `${label(specId)} is now ${to} priority.`);
  }

  function remove(specId: string) {
    if (!current) return;
    save(
      picksOf(current.needs).filter((p) => p.spec_id !== specId),
      `${label(specId)} is off the ${night} list.`
    );
  }
</script>

<section class="card needs" aria-labelledby="needs-{day}-h">
  <h2 id="needs-{day}-h">{night} recruitment needs</h2>
  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
  {:else if !current}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if current.needs.length}
      <ul class="list">
        {#each current.needs as n (n.spec_id)}
          {@const s = specOf(n.spec_id)}
          <li style="--c: {classOf(s?.wowClass)?.colour ?? 'currentColor'}">
            <span class="who"><strong>{n.spec} {n.class_name}</strong> <span class="muted">{n.role}</span></span>
            <label class="sr-only" for="needs-{day}-{n.spec_id}-p">Priority for {n.spec} {n.class_name}</label>
            <select
              id="needs-{day}-{n.spec_id}-p"
              value={n.priority}
              disabled={busy}
              onchange={(e) => setPriority(n.spec_id, e.currentTarget.value as NeedPriority)}
            >
              {#each PRIORITIES as p (p.id)}<option value={p.id}>{p.label}</option>{/each}
            </select>
            <button type="button" class="btn" disabled={busy} onclick={() => remove(n.spec_id)}>
              Remove<span class="sr-only"> {n.spec} {n.class_name} from {night}</span>
            </button>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="muted">Nothing listed, so the homepage shows {night} as full for now.</p>
    {/if}

    <form class="add" onsubmit={add}>
      <div class="field">
        <label for="needs-{day}-q">Add a primary spec</label>
        <input
          id="needs-{day}-q"
          list="needs-{day}-specs"
          autocomplete="off"
          spellcheck="false"
          maxlength="40"
          placeholder="Type to search, such as resto shaman"
          bind:value={typed}
          disabled={!left.length}
        />
        <datalist id="needs-{day}-specs">
          {#each left as s (s.id)}<option value={specLabel(s)}></option>{/each}
        </datalist>
      </div>
      <div class="field prio">
        <label for="needs-{day}-prio">Priority</label>
        <select id="needs-{day}-prio" bind:value={priority}>
          {#each PRIORITIES as p (p.id)}<option value={p.id}>{p.label}</option>{/each}
        </select>
      </div>
      <button class="btn primary" type="submit" disabled={busy || !left.length || !typed.trim()}>Add</button>
    </form>
    <p class="muted small">
      Tanks, healers or damage with nothing listed show as “Full for now” to visitors who pick {night}.
    </p>
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
  {/if}
</section>

<style>
  .needs { display: grid; gap: 0.75rem; align-content: start; }
  .needs h2, .needs p { margin: 0; }
  .list { list-style: none; margin: 0; padding: 0; display: grid; }
  .list li {
    display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.75rem; padding: 0.4rem 0 0.4rem 0.6rem;
    border-bottom: 1px solid var(--line); border-left: 3px solid var(--c);
  }
  .who { flex: 1 1 10rem; min-width: 0; overflow-wrap: anywhere; }
  .add { display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; align-items: flex-end; }
  .add .field { flex: 1 1 14rem; }
  .add .prio { flex: 0 1 8rem; }
  .small { font-size: 0.85rem; }
</style>
