<script lang="ts">
  import {
    PANEL_LIMIT,
    notOnPanel,
    panelError,
    whoInterviews,
    type InterviewPanel,
    type Interviewer,
    type PanelBackend
  } from '$lib/interview-panels';

  // One raid night's interview panel: who is on it, and a search of the Toads Discord to add someone. The API checks
  // that the viewer runs this night (manage_recruitment for the day); this card only shows itself to them.
  let { backend, day, night }: { backend: PanelBackend; day: string; night: string } = $props();

  let panel = $state<InterviewPanel | null>(null);
  let loadError = $state('');
  let query = $state('');
  let found = $state<Interviewer[]>([]);
  let searched = $state('');
  let searching = $state(false);
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  const choices = $derived(panel ? notOnPanel(found, panel.interviewers) : []);
  const full = $derived(!!panel && panel.interviewers.length >= PANEL_LIMIT);

  $effect(() => {
    backend
      .panel(day)
      .then((p) => {
        panel = p;
        loadError = '';
      })
      .catch((e) => (loadError = panelError(e)));
  });

  async function search(event: SubmitEvent) {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;
    searching = true;
    try {
      found = await backend.search(day, q);
      searched = q;
      message = '';
    } catch (e) {
      message = panelError(e);
      failed = true;
    } finally {
      searching = false;
    }
  }

  async function change(action: () => Promise<InterviewPanel>, done: string, clearSearch = false) {
    busy = true;
    try {
      panel = await action();
      message = done;
      failed = false;
      if (clearSearch) [query, found, searched] = ['', [], ''];
    } catch (e) {
      message = panelError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }

  const add = (who: Interviewer) =>
    change(
      () => backend.add(day, who.discord_user_id),
      `${who.display_name} now interviews ${night} applicants.`,
      true
    );
  const remove = (who: Interviewer) =>
    change(() => backend.remove(day, who.discord_user_id), `${who.display_name} is off the ${night} panel.`);
</script>

<section class="card panel" aria-labelledby="panel-{day}-h">
  <h2 id="panel-{day}-h">{night} interview panel</h2>
  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
  {:else if !panel}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if panel.interviewers.length}
      <ul class="people">
        {#each panel.interviewers as who (who.discord_user_id)}
          <li>
            <span><strong>{who.display_name}</strong> <span class="muted">@{who.username}</span></span>
            <button type="button" class="btn" disabled={busy} onclick={() => remove(who)}>
              Remove<span class="sr-only"> {who.display_name} from the {night} panel</span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
    <p class="muted">{whoInterviews(panel, night)}</p>

    <form class="find" onsubmit={search}>
      <div class="field">
        <label for="panel-{day}-q">Add someone from the Toads Discord</label>
        <input
          id="panel-{day}-q"
          type="search"
          maxlength="32"
          autocomplete="off"
          spellcheck="false"
          placeholder="Username or nickname"
          bind:value={query}
          disabled={full}
        />
      </div>
      <button class="btn" type="submit" disabled={searching || full || !query.trim()} aria-busy={searching}>
        {searching ? 'Searching…' : 'Find'}
      </button>
    </form>
    {#if full}
      <p class="muted">The panel is full at {PANEL_LIMIT}. Remove someone to add another.</p>
    {:else if searched}
      {#if choices.length}
        <ul class="people found" aria-label="Discord members matching {searched}">
          {#each choices as who (who.discord_user_id)}
            <li>
              <span><strong>{who.display_name}</strong> <span class="muted">@{who.username}</span></span>
              <button type="button" class="btn primary" disabled={busy} onclick={() => add(who)}>
                Add<span class="sr-only"> {who.display_name} to the {night} panel</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="muted">Nobody else in the Toads Discord has a name starting “{searched}”.</p>
      {/if}
    {/if}
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
  {/if}
</section>

<style>
  .panel { display: grid; gap: 0.75rem; align-content: start; }
  .panel h2, .panel p { margin: 0; }
  .people { list-style: none; margin: 0; padding: 0; display: grid; }
  .people li {
    display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.75rem; padding: 0.4rem 0;
    border-bottom: 1px solid var(--line);
  }
  .people li > span { flex: 1 1 10rem; min-width: 0; overflow-wrap: anywhere; }
  .find { display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; align-items: flex-end; }
  .find .field { flex: 1 1 14rem; }
</style>
