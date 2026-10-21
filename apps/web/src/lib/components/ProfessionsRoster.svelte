<script lang="ts">
  import {
    NOTE_LIMIT,
    PROFESSIONS,
    describe,
    professionName,
    professionsError,
    withProfession,
    type Crafter,
    type MemberProfessions,
    type ProfessionsBackend
  } from '$lib/professions';

  // One raid night's members and their professions, or (day null) every member who lists one, which only global
  // officers and super admins see. An officer names a member the guild's crafter for a profession they list, with a
  // note on what to send them, and can take it back. The API checks the viewer runs this night; this card only shows
  // itself to them. `oncrafters` hands the guild-wide crafters list to the page after every load and change.
  let {
    backend,
    day,
    title,
    oncrafters
  }: {
    backend: ProfessionsBackend;
    day: string | null;
    title: string;
    oncrafters?: (crafters: Crafter[]) => void;
  } = $props();

  let members = $state<MemberProfessions[] | null>(null);
  let loadError = $state('');
  let filter = $state('');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);
  // The profession being named, as "memberId:profession", with its note.
  let naming = $state<string | null>(null);
  let note = $state('');

  const shown = $derived(members ? withProfession(members, filter) : []);
  const listed = $derived(members ? members.filter((m) => m.professions.length).length : 0);

  let latest = 0;
  async function load() {
    const ask = ++latest;
    try {
      const o = await backend.overview(day);
      if (ask !== latest) return;
      [members, loadError] = [o.members, ''];
      oncrafters?.(o.crafters);
    } catch (e) {
      if (ask === latest) loadError = professionsError(e);
    }
  }

  $effect(() => {
    load();
  });

  const key = (m: MemberProfessions, profession: string) => `${m.member_id}:${profession}`;
  const isNamed = (m: MemberProfessions, profession: string) => m.crafter_for.some((n) => n.profession === profession);

  async function act(action: () => Promise<unknown>, done: string) {
    busy = true;
    try {
      await action();
      message = done;
      failed = false;
      naming = null;
      note = '';
    } catch (e) {
      message = professionsError(e);
      failed = true;
    } finally {
      await load();
      busy = false;
    }
  }

  const name = (m: MemberProfessions, profession: string) =>
    act(
      () => backend.name(day, profession, m.member_id, note),
      `${m.name} is now a guild ${professionName(profession)} crafter.`
    );
  const unname = (m: MemberProfessions, profession: string) =>
    act(
      () => backend.unname(day, profession, m.member_id),
      `${m.name} is no longer a guild ${professionName(profession)} crafter.`
    );

  function startNaming(m: MemberProfessions, profession: string) {
    naming = key(m, profession);
    note = '';
  }
</script>

<section class="card roster" aria-label={title}>
  <header>
    <h2>{title}</h2>
    {#if members?.length}
      <p class="muted count">{listed} of {members.length} {members.length === 1 ? 'member lists' : 'members list'} professions</p>
    {/if}
  </header>

  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
  {:else if !members}
    <p class="muted" role="status">Loading…</p>
  {:else if !members.length}
    <p class="muted">Nobody here yet.</p>
  {:else}
    <label class="filter">
      Profession
      <select bind:value={filter}>
        <option value="">Everyone</option>
        {#each PROFESSIONS as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
      </select>
    </label>
    {#if !shown.length}
      <p class="muted">Nobody here lists {professionName(filter)}.</p>
    {/if}
    <ul class="members">
      {#each shown as m (m.member_id)}
        <li>
          <span class="who">{m.name}</span>
          {#if !m.professions.length}
            <span class="muted">No professions on Me yet</span>
          {:else}
            <ul class="held">
              {#each m.professions as h (h.profession)}
                <li class:named={isNamed(m, h.profession)}>
                  <span>{describe(h)}</span>
                  {#if isNamed(m, h.profession)}
                    <span class="tag">Guild crafter</span>
                    <button class="link" type="button" disabled={busy} onclick={() => unname(m, h.profession)}>Remove</button>
                  {:else if naming === key(m, h.profession)}
                    <form
                      class="naming"
                      onsubmit={(e) => {
                        e.preventDefault();
                        name(m, h.profession);
                      }}
                    >
                      <label>
                        <span class="sr-only">What to send them</span>
                        <input bind:value={note} maxlength={NOTE_LIMIT} placeholder="What to send them, e.g. flasks" disabled={busy} />
                      </label>
                      <button class="btn primary" type="submit" disabled={busy}>Name</button>
                      <button class="btn" type="button" disabled={busy} onclick={() => (naming = null)}>Cancel</button>
                    </form>
                  {:else}
                    <button class="link" type="button" disabled={busy} onclick={() => startNaming(m, h.profession)}>
                      Name guild crafter
                    </button>
                  {/if}
                </li>
              {/each}
            </ul>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
  {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
</section>

<style>
  .roster { display: grid; gap: 0.75rem; align-content: start; }
  header { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 0.25rem 1rem; }
  h2, .count { margin: 0; }
  .filter { display: flex; align-items: center; gap: 0.5rem; font-size: 0.95rem; }
  .members { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; }
  .members > li { display: grid; gap: 0.3rem; padding-bottom: 0.6rem; border-bottom: 1px solid var(--line); }
  .members > li:last-child { border-bottom: 0; }
  .who { font-weight: 600; }
  .held { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.3rem; }
  .held li { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem 0.6rem; }
  .held li.named > span:first-child { font-weight: 600; }
  .tag {
    padding: 0.05rem 0.45rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    background: color-mix(in srgb, var(--accent) 22%, var(--bg));
  }
  .link {
    padding: 0;
    border: 0;
    background: none;
    color: var(--accent);
    font: inherit;
    font-size: 0.9rem;
    text-decoration: underline;
    cursor: pointer;
  }
  .link:disabled { opacity: 0.55; cursor: not-allowed; }
  .naming { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; width: 100%; }
  .naming label { flex: 1 1 12rem; }
  .naming input { width: 100%; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>
