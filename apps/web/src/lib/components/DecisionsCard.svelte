<script lang="ts">
  import { ApiError } from '$lib/api';
  import { STATUS_LABELS } from '$lib/recruitment';
  import {
    NOTE_LIMIT,
    consequence,
    decisionError,
    noteAuthor,
    outcome,
    rolesLine,
    when,
    type Decision,
    type DecisionBackend,
    type DecisionBoard,
    type DecisionCard
  } from '$lib/decisions';

  // One raid night's Decisions panel: who is waiting on the night's officers, their notes, and reject or accept. The
  // API checks that the viewer runs this night (manage_recruitment for the day); this card only shows itself to them.
  let { backend, day, night }: { backend: DecisionBackend; day: string; night: string } = $props();

  let board = $state<DecisionBoard | null>(null);
  let loadError = $state('');
  let drafts = $state<Record<number, string>>({});
  let confirming = $state<{ id: number; decision: Decision } | null>(null);
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  async function load() {
    try {
      board = await backend.board(day);
      loadError = '';
    } catch (e) {
      loadError = decisionError(e);
    }
  }

  $effect(() => {
    load();
  });

  async function act(action: () => Promise<unknown>, done: string) {
    busy = true;
    try {
      await action();
      await load();
      message = done;
      failed = false;
    } catch (e) {
      message = decisionError(e);
      failed = true;
      // Another officer may have decided it first: show the board as it is now, keeping the reason above.
      if (e instanceof ApiError && (e.status === 404 || e.status === 409)) await load();
    } finally {
      busy = false;
    }
  }

  function addNote(event: SubmitEvent, card: DecisionCard) {
    event.preventDefault();
    const id = card.application.id;
    const body = (drafts[id] ?? '').trim();
    if (!body) return;
    act(async () => {
      await backend.note(day, id, body);
      // Keep anything typed while the note was on its way.
      if ((drafts[id] ?? '').trim() === body) drafts[id] = '';
    }, `Note added to ${card.application.character_name}.`);
  }

  function decide(card: DecisionCard, decision: Decision) {
    const name = card.application.character_name;
    confirming = null;
    act(
      () => backend.decide(day, card.application.id, decision),
      decision === 'accept' ? `${name} is accepted for ${night}.` : `${name} is rejected.`
    );
  }
</script>

<section class="card decisions" aria-label="{night} decisions">
  <h3>{night}</h3>
  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
  {:else if !board}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if board.waiting.length === 0}
      <p class="muted">No one is waiting on a decision for {night}.</p>
    {:else}
      <ol class="applicants">
        {#each board.waiting as card (card.application.id)}
          {@const app = card.application}
          <li>
            <article aria-labelledby="app-{day}-{app.id}">
              <header>
                <h4 id="app-{day}-{app.id}">{app.character_name}</h4>
                <span class="pill">{STATUS_LABELS[app.status]}</span>
              </header>
              <p class="meta">
                {app.class_name} · {rolesLine(app)}
                <span class="muted">· {app.applicant_name} on Discord · applied {when(app.created_at)}</span>
              </p>
              {#if app.why_toads}<blockquote>{app.why_toads}</blockquote>{/if}
              {#if app.interview_room_url || app.logs_url}
                <p class="links">
                  {#if app.interview_room_url}
                    <a href={app.interview_room_url} target="_blank" rel="noopener noreferrer">Interview room</a>
                  {/if}
                  {#if app.logs_url}<a href={app.logs_url} target="_blank" rel="noopener noreferrer">Logs</a>{/if}
                </p>
              {/if}
              {#if app.interview_room_error}
                <p class="warn">No interview room: {app.interview_room_error}</p>
              {/if}

              <h5 class="sr-only">Officers’ notes on {app.character_name}</h5>
              {#if card.notes.length}
                <ul class="notes">
                  {#each card.notes as note (note.id)}
                    <li>
                      <p class="by"><strong>{noteAuthor(note)}</strong> <span class="muted">{when(note.at)}</span></p>
                      <p class="body">{note.body}</p>
                    </li>
                  {/each}
                </ul>
              {:else}
                <p class="muted">No notes yet.</p>
              {/if}
              <form class="note" onsubmit={(e) => addNote(e, card)}>
                <label class="sr-only" for="note-{day}-{app.id}">Note on {app.character_name}</label>
                <textarea
                  id="note-{day}-{app.id}"
                  rows="2"
                  maxlength={NOTE_LIMIT}
                  placeholder="Add a note for the other officers"
                  bind:value={drafts[app.id]}
                ></textarea>
                <button class="btn" type="submit" disabled={busy || !(drafts[app.id] ?? '').trim()}>Add note</button>
              </form>

              {#if confirming?.id === app.id}
                {@const decision = confirming.decision}
                <div class="confirm" role="group" aria-label="Confirm the decision on {app.character_name}">
                  <p>{consequence(decision, app, night)}</p>
                  <div class="actions">
                    <button
                      type="button"
                      class="btn {decision === 'reject' ? 'danger' : 'primary'}"
                      disabled={busy}
                      onclick={() => decide(card, decision)}
                    >
                      {decision === 'reject' ? `Reject ${app.character_name}` : `Accept ${app.character_name}`}
                    </button>
                    <button type="button" class="btn" disabled={busy} onclick={() => (confirming = null)}>Cancel</button>
                  </div>
                </div>
              {:else}
                <div class="actions">
                  <button
                    type="button"
                    class="btn danger"
                    disabled={busy}
                    onclick={() => (confirming = { id: app.id, decision: 'reject' })}
                  >
                    Reject<span class="sr-only"> {app.character_name}</span>
                  </button>
                  <button
                    type="button"
                    class="btn primary"
                    disabled={busy}
                    onclick={() => (confirming = { id: app.id, decision: 'accept' })}
                  >
                    Accept<span class="sr-only"> {app.character_name}</span>
                  </button>
                </div>
              {/if}
            </article>
          </li>
        {/each}
      </ol>
    {/if}
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}

    {#if board.decided.length}
      <details class="decided">
        <summary>Decided in the last two weeks ({board.decided.length})</summary>
        <ul>
          {#each board.decided as card (card.application.id)}
            {@const app = card.application}
            <li>
              <p>
                <strong>{app.character_name}</strong>
                <span class={app.status === 'accepted' ? 'ok' : 'muted'}>{outcome(app.status)}</span>
                {#if card.decided_at}<span class="muted">· {when(card.decided_at)}</span>{/if}
              </p>
              {#each card.notes.filter((n) => n.author_name === null) as note (note.id)}
                <p class="muted bot">{noteAuthor(note)}: {note.body}</p>
              {/each}
            </li>
          {/each}
        </ul>
      </details>
    {/if}
  {/if}
</section>

<style>
  .decisions { display: grid; gap: 0.75rem; align-content: start; }
  .decisions h3, .decisions p { margin: 0; }
  .applicants, .notes, .decided ul { list-style: none; margin: 0; padding: 0; display: grid; }
  .applicants { gap: 0; }
  .applicants > li { padding: 0.9rem 0; border-top: 1px solid var(--line); }
  .applicants > li:first-child { border-top: 0; padding-top: 0.25rem; }
  article { display: grid; gap: 0.5rem; }
  header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.25rem 0.6rem; }
  h4 { margin: 0; font-size: 1.05rem; overflow-wrap: anywhere; }
  blockquote {
    margin: 0; padding: 0.1rem 0 0.1rem 0.75rem; border-left: 2px solid var(--line);
    white-space: pre-line; overflow-wrap: anywhere;
  }
  .links { display: flex; flex-wrap: wrap; gap: 0.25rem 1rem; }
  .notes { gap: 0.4rem; }
  .notes li { padding: 0.45rem 0.6rem; border-radius: 6px; background: rgb(255 255 255 / 0.04); }
  .notes .by { font-size: 0.85rem; }
  .notes .body { white-space: pre-line; overflow-wrap: anywhere; }
  .note { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: flex-end; }
  .note textarea { flex: 1 1 14rem; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .confirm { display: grid; gap: 0.5rem; padding: 0.6rem; border: 1px solid var(--line); border-radius: 6px; }
  .decided summary { cursor: pointer; }
  .decided ul { gap: 0.4rem; margin-top: 0.5rem; }
  .decided p { overflow-wrap: anywhere; }
  .bot { font-size: 0.85rem; }
</style>
