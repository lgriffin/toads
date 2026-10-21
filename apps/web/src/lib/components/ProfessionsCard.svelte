<script lang="ts">
  import { onMount } from 'svelte';
  import {
    MAX_SKILL,
    PROFESSIONS,
    getMyProfessions,
    professionName,
    professionsError,
    saveMyProfessions,
    type HeldProfession,
    type MyProfessions
  } from '$lib/professions';

  // The professions a member has. Officers see them for their raid night and name some members the guild's crafters
  // for a profession, the people the guild sends its top end recipes to; a member named so sees it here.
  let { preview = null }: { preview?: MyProfessions | null } = $props();

  let loaded = $state(__PREVIEW__);
  let saved = $state<MyProfessions>({ professions: [], crafter_for: [] });
  // One entry per picked profession, by id; skill is kept as typed text so an empty box means "not given".
  let picked = $state<Record<string, { skill: string; specialisation: string }>>({});
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  const primary = PROFESSIONS.filter((p) => !p.secondary);
  const secondary = PROFESSIONS.filter((p) => p.secondary);
  const chosen = $derived(PROFESSIONS.filter((p) => p.id in picked));
  const named = $derived(new Set(saved.crafter_for.map((n) => n.profession)));

  function asEntries(): HeldProfession[] {
    return chosen.map((p) => {
      const skill = Number.parseInt(picked[p.id].skill, 10);
      return {
        profession: p.id,
        skill: Number.isFinite(skill) ? skill : null,
        specialisation: picked[p.id].specialisation || null
      };
    });
  }

  const changed = $derived(JSON.stringify(asEntries()) !== JSON.stringify(saved.professions));
  const badSkill = $derived(asEntries().some((e) => e.skill !== null && (e.skill < 1 || e.skill > MAX_SKILL)));

  function show(m: MyProfessions) {
    saved = { ...m, professions: m.professions.map((h) => ({ ...h })) };
    picked = Object.fromEntries(
      m.professions.map((h) => [h.profession, { skill: h.skill?.toString() ?? '', specialisation: h.specialisation ?? '' }])
    );
  }

  function toggle(id: string) {
    if (id in picked) {
      const { [id]: _, ...rest } = picked;
      picked = rest;
    } else {
      picked = { ...picked, [id]: { skill: '', specialisation: '' } };
    }
  }

  onMount(async () => {
    if (__PREVIEW__) {
      if (preview) show(preview);
      return;
    }
    try {
      show(await getMyProfessions());
    } catch (e) {
      message = professionsError(e);
      failed = true;
    } finally {
      loaded = true;
    }
  });

  async function save(event: SubmitEvent) {
    event.preventDefault();
    busy = true;
    try {
      const entries = asEntries();
      const next: MyProfessions = __PREVIEW__
        ? {
            professions: entries,
            crafter_for: saved.crafter_for.filter((n) => entries.some((e) => e.profession === n.profession)),
            unnamed: saved.crafter_for.map((n) => n.profession).filter((p) => !entries.some((e) => e.profession === p))
          }
        : await saveMyProfessions(entries);
      show(next);
      const lost = next.unnamed ?? [];
      message = lost.length
        ? `Saved. You are no longer the guild’s ${lost.map(professionName).join(' or ')} crafter.`
        : 'Saved. Your officers can see your professions.';
      failed = false;
    } catch (e) {
      message = professionsError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }
</script>

<section class="card professions" aria-labelledby="professions-h">
  <h2 id="professions-h">Your professions</h2>
  <p class="muted lede">
    Pick the professions you have, on your main or your alts. Officers see them, and name the guild’s crafters for top end
    recipes from them.
  </p>

  {#if !loaded}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if saved.crafter_for.length}
      <ul class="named" aria-label="Guild crafter">
        {#each saved.crafter_for as n (n.profession)}
          <li>
            <strong>Guild {professionName(n.profession)} crafter</strong>{#if n.note}: {n.note}{/if}
            {#if n.designated_by}<span class="muted"> · named by {n.designated_by}</span>{/if}
          </li>
        {/each}
      </ul>
    {/if}
    <form onsubmit={save}>
      <fieldset disabled={busy}>
        <legend>Professions</legend>
        <div class="chips">
          {#each primary as p (p.id)}
            <label class="chip" class:picked={p.id in picked}>
              <input type="checkbox" checked={p.id in picked} onchange={() => toggle(p.id)} />
              {p.name}
            </label>
          {/each}
        </div>
      </fieldset>
      <fieldset disabled={busy}>
        <legend>Secondary skills</legend>
        <div class="chips">
          {#each secondary as p (p.id)}
            <label class="chip" class:picked={p.id in picked}>
              <input type="checkbox" checked={p.id in picked} onchange={() => toggle(p.id)} />
              {p.name}
            </label>
          {/each}
        </div>
      </fieldset>

      {#if chosen.length}
        <ul class="details">
          {#each chosen as p (p.id)}
            <li>
              <span class="name">
                {p.name}
                {#if named.has(p.id)}<span class="tag">Guild crafter</span>{/if}
              </span>
              <label>
                Skill <span class="hint">optional</span>
                <input
                  type="number"
                  inputmode="numeric"
                  min="1"
                  max={MAX_SKILL}
                  placeholder={String(MAX_SKILL)}
                  bind:value={picked[p.id].skill}
                  disabled={busy}
                />
              </label>
              {#if p.specialisations.length}
                <label>
                  Specialisation
                  <select bind:value={picked[p.id].specialisation} disabled={busy}>
                    <option value="">None</option>
                    {#each p.specialisations as [id, name] (id)}<option value={id}>{name}</option>{/each}
                  </select>
                </label>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}

      <div class="actions">
        <button class="btn primary" type="submit" disabled={busy || !changed || badSkill}>Save my professions</button>
        {#if badSkill}<span class="err">Skill runs from 1 to {MAX_SKILL}.</span>{/if}
      </div>
    </form>
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
  {/if}
</section>

<style>
  .professions { display: grid; gap: 0.9rem; margin-block: 1rem; }
  .professions h2 { margin: 0; }
  .lede { margin: 0; max-width: 62ch; }
  .named {
    margin: 0;
    padding: 0.6rem 0.8rem;
    list-style: none;
    border-left: 3px solid var(--accent);
    border-radius: 4px;
    background: color-mix(in srgb, var(--accent) 10%, var(--bg));
    display: grid;
    gap: 0.25rem;
  }
  form { display: grid; gap: 1rem; }
  fieldset { border: 0; margin: 0; padding: 0; min-width: 0; }
  legend { padding: 0; margin-bottom: 0.45rem; }
  .chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .chip {
    position: relative;
    padding: 0.35rem 0.8rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--bg);
    font-size: 0.9rem;
    cursor: pointer;
  }
  .chip:hover { border-color: var(--muted); }
  .chip.picked { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 16%, var(--bg)); }
  .chip:has(input:focus-visible) { outline: 2px solid var(--accent); outline-offset: 2px; }
  .chip input { position: absolute; opacity: 0; pointer-events: none; }
  fieldset:disabled .chip { opacity: 0.55; cursor: not-allowed; }
  .details { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; }
  .details li {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 0.5rem 1rem;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid var(--line);
  }
  .details .name { min-width: 9rem; font-weight: 600; align-self: center; }
  .details label { display: grid; gap: 0.2rem; font-size: 0.9rem; }
  .details input { width: 6rem; }
  .tag {
    margin-left: 0.4rem;
    padding: 0.05rem 0.45rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    background: color-mix(in srgb, var(--accent) 22%, var(--bg));
  }
  .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem; }
</style>
