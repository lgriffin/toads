<script lang="ts">
  import { base } from '$app/paths';
  import type { MemberEntry } from '$lib/api';
  import { AWARDABLE, awardError, awardable, monthLabel, type AwardOut, type AwardsBackend } from '$lib/awards';

  // The global officers' awards desk: give a member an award, and see or take back the guild's recent ones. The API
  // checks the permission (manage_awards); this page only hides the desk from everyone else.
  let { backend }: { backend: AwardsBackend } = $props();

  let members = $state<MemberEntry[]>([]);
  let wall = $state<AwardOut[]>([]);
  let loadError = $state('');
  let memberId = $state<number | ''>('');
  let awardId = $state('');
  let period = $state(new Date().toISOString().slice(0, 7));
  let note = $state('');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  const chosen = $derived(awardable(awardId));
  const GROUPS = [
    { kind: 'milestone', label: 'Milestones and history' },
    { kind: 'achievement', label: 'Achievements' },
    { kind: 'title', label: 'Titles' }
  ] as const;

  async function load() {
    try {
      [members, wall] = await Promise.all([backend.members(), backend.wall()]);
      loadError = '';
    } catch (e) {
      loadError = awardError(e);
    }
  }
  $effect(() => {
    load();
  });

  async function give(event: SubmitEvent) {
    event.preventDefault();
    if (memberId === '' || !chosen) return;
    busy = true;
    try {
      const a = await backend.give({
        member_id: memberId,
        award_id: chosen.id,
        ...(chosen.monthly ? { period } : {}),
        ...(note.trim() ? { note: note.trim() } : {})
      });
      message = `${a.member_name} now holds ${a.name}.`;
      failed = false;
      note = '';
      wall = await backend.wall();
    } catch (e) {
      message = awardError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }

  async function takeBack(a: AwardOut) {
    busy = true;
    try {
      await backend.takeBack(a.id);
      message = `Took ${a.name} back from ${a.member_name}.`;
      failed = false;
      wall = await backend.wall();
    } catch (e) {
      message = awardError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }
</script>

<section class="card desk" aria-labelledby="awards-desk-h">
  <h2 id="awards-desk-h">Awards</h2>
  <p class="muted">Give a member a milestone, an achievement or a title. Their toad shows on their Me page.</p>

  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
  {:else}
    <form onsubmit={give}>
      <div class="field">
        <label for="award-member">Member</label>
        <select id="award-member" bind:value={memberId} required>
          <option value="" disabled>Choose a member</option>
          {#each members as m (m.member_id)}<option value={m.member_id}>{m.display_name}</option>{/each}
        </select>
      </div>
      <div class="field">
        <label for="award-id">Award</label>
        <select id="award-id" bind:value={awardId} required>
          <option value="" disabled>Choose an award</option>
          {#each GROUPS as g (g.kind)}
            <optgroup label={g.label}>
              {#each AWARDABLE.filter((a) => a.kind === g.kind) as a (a.id)}<option value={a.id}>{a.name}</option>{/each}
            </optgroup>
          {/each}
        </select>
      </div>
      {#if chosen?.monthly}
        <div class="field">
          <label for="award-month">Month</label>
          <input id="award-month" type="month" bind:value={period} required />
        </div>
      {/if}
      <div class="field wide">
        <label for="award-note">Note <span class="hint">(optional, shown with the award)</span></label>
        <input id="award-note" maxlength="200" bind:value={note} />
      </div>
      {#if chosen}
        <img class="preview-badge" src="{base}/logos/{chosen.file}-badge.svg" alt="" width="72" height="86" />
      {/if}
      <button class="btn primary" type="submit" disabled={busy || memberId === '' || !chosen}>Give award</button>
    </form>
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}

    <h3>Recently given</h3>
    {#if wall.length === 0}
      <p class="muted">Nobody holds an award yet.</p>
    {:else}
      <ul class="wall">
        {#each wall.slice(0, 20) as a (a.id)}
          {@const art = awardable(a.award_id)}
          <li>
            {#if art}<img src="{base}/logos/{art.file}.svg" alt="" width="40" height="35" loading="lazy" />{/if}
            <span><strong>{a.member_name}</strong> · {a.name}{a.period ? `, ${monthLabel(a.period)}` : ''}</span>
            <button type="button" class="btn" disabled={busy} onclick={() => takeBack(a)}>
              Take back<span class="sr-only"> {a.name} from {a.member_name}</span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</section>

<style>
  .desk { display: grid; gap: 0.75rem; }
  .desk h2, .desk h3 { margin: 0; }
  form { display: flex; flex-wrap: wrap; gap: 0.75rem 1rem; align-items: flex-end; }
  .field { min-width: 12rem; }
  .field.wide { flex: 1 1 16rem; }
  .preview-badge { width: 4.5rem; height: auto; }
  .wall { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.25rem; }
  .wall li { display: flex; align-items: center; gap: 0.6rem; padding: 0.35rem 0; border-bottom: 1px solid var(--line); }
  .wall li span { flex: 1; }
  .wall img { width: 2.5rem; height: auto; }
</style>
