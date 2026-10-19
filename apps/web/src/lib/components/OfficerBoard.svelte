<script lang="ts">
  import {
    LANES,
    NOTES_LIMIT,
    TITLE_LIMIT,
    boardError,
    dueLabel,
    moved,
    neighbourLane,
    type Assignee,
    type BoardBackend,
    type BoardCard,
    type BoardLane,
    type LaneId
  } from '$lib/officer-board';

  // The officers' task board for one raid night (docs/officer-board.md). The Raid page shows it to that night's
  // officers only; the API checks the permission (manage_officer_board) on every call.
  let { backend, day, dayName }: { backend: BoardBackend; day: string; dayName: string } = $props();

  let lanes = $state<BoardLane[]>([]);
  let assignees = $state<Assignee[]>([]);
  let loaded = $state(false);
  let loadError = $state('');
  let message = $state('');
  let failed = $state(false);
  let busy = $state(false);

  // The add form.
  let title = $state('');
  let assignee = $state<number | ''>('');
  let due = $state('');

  // The card being edited, and its draft.
  let editing = $state<number | null>(null);
  let draft = $state({ title: '', notes: '', assignee: '' as number | '', due: '' });
  let confirmRemove = $state(false);

  // Dragging: the card in hand and where it would land.
  let dragged = $state<number | null>(null);
  let dropAt = $state<{ lane: LaneId; position: number } | null>(null);

  const laneName = (id: LaneId) => LANES.find((l) => l.id === id)?.name ?? id;
  const total = $derived(lanes.reduce((n, l) => n + l.cards.length, 0));

  async function load() {
    try {
      const board = await backend.board(day);
      lanes = board.lanes;
      assignees = board.assignees;
      loadError = '';
    } catch (e) {
      loadError = boardError(e);
    } finally {
      loaded = true;
    }
  }
  $effect(() => {
    void day;
    editing = null;
    message = '';
    load();
  });

  function say(text: string, error = false) {
    message = text;
    failed = error;
  }

  async function attempt(action: () => Promise<void>) {
    busy = true;
    try {
      await action();
    } catch (e) {
      say(boardError(e), true);
      await load();
    } finally {
      busy = false;
    }
  }

  function add(event: SubmitEvent) {
    event.preventDefault();
    const text = title.trim();
    if (!text) return;
    attempt(async () => {
      const card = await backend.add(day, {
        title: text,
        assignee_member_id: assignee === '' ? null : assignee,
        due_on: due || null
      });
      lanes = lanes.map((l) => (l.id === card.lane ? { ...l, cards: [...l.cards, card] } : l));
      title = '';
      due = '';
      assignee = '';
      say(`Added “${card.title}” to To do.`);
    });
  }

  function move(card: BoardCard, lane: LaneId, position: number) {
    const before = lanes;
    lanes = moved(lanes, card.id, lane, position);
    attempt(async () => {
      try {
        lanes = await backend.move(day, card.id, lane, position);
      } catch (e) {
        lanes = before;
        throw e;
      }
      say(lane === card.lane ? `Moved “${card.title}”.` : `Moved “${card.title}” to ${laneName(lane)}.`);
    });
  }

  function step(card: BoardCard, direction: -1 | 1) {
    const lane = neighbourLane(card.lane, direction);
    if (lane) move(card, lane, lanes.find((l) => l.id === lane)?.cards.length ?? 0);
  }

  function shift(card: BoardCard, by: -1 | 1) {
    const index = lanes.find((l) => l.id === card.lane)?.cards.findIndex((c) => c.id === card.id) ?? -1;
    if (index >= 0) move(card, card.lane, index + by);
  }

  function edit(card: BoardCard) {
    editing = card.id;
    confirmRemove = false;
    draft = { title: card.title, notes: card.notes, assignee: card.assignee_member_id ?? '', due: card.due_on ?? '' };
  }

  function save(event: SubmitEvent, card: BoardCard) {
    event.preventDefault();
    attempt(async () => {
      const updated = await backend.edit(day, card.id, {
        title: draft.title.trim(),
        notes: draft.notes,
        assignee_member_id: draft.assignee === '' ? null : draft.assignee,
        due_on: draft.due || null
      });
      lanes = lanes.map((l) => ({ ...l, cards: l.cards.map((c) => (c.id === card.id ? updated : c)) }));
      editing = null;
      say(`Saved “${updated.title}”.`);
    });
  }

  function remove(card: BoardCard) {
    if (!confirmRemove) {
      confirmRemove = true;
      return;
    }
    attempt(async () => {
      await backend.remove(day, card.id);
      lanes = lanes.map((l) => ({ ...l, cards: l.cards.filter((c) => c.id !== card.id) }));
      editing = null;
      say(`Removed “${card.title}”.`);
    });
  }

  // Drag and drop is a shortcut; the arrows and the card's editor do the same from the keyboard.
  function over(event: DragEvent, lane: LaneId, position: number) {
    if (dragged === null) return;
    event.preventDefault();
    dropAt = { lane, position };
  }

  function drop(event: DragEvent) {
    event.preventDefault();
    const card = lanes.flatMap((l) => l.cards).find((c) => c.id === dragged);
    const target = dropAt;
    dragged = null;
    dropAt = null;
    if (!card || !target) return;
    const from = lanes.find((l) => l.id === card.lane)?.cards.findIndex((c) => c.id === card.id) ?? -1;
    // Dropping lower in its own lane: the card's own slot closes up first.
    const position = target.lane === card.lane && from >= 0 && from < target.position ? target.position - 1 : target.position;
    if (target.lane === card.lane && position === from) return;
    move(card, target.lane, position);
  }
</script>

<section class="card board" aria-labelledby="board-h-{day}">
  <div class="head">
    <h2 id="board-h-{day}">Officers’ board</h2>
    <p class="muted">Tasks for {dayName}’s officers: who has what, and when it is due. Only {dayName} officers see it.</p>
  </div>

  {#if loadError && lanes.length === 0}
    <p class="err" role="alert">{loadError}</p>
  {:else}
    <form class="add" onsubmit={add} aria-label="Add a card">
      <div class="field grow">
        <label for="board-title-{day}">New task</label>
        <input id="board-title-{day}" bind:value={title} maxlength={TITLE_LIMIT} placeholder="Book the pug tank for Gruul" required />
      </div>
      <div class="field">
        <label for="board-who-{day}">Assign to</label>
        <select id="board-who-{day}" bind:value={assignee}>
          <option value="">Nobody yet</option>
          {#each assignees as a (a.member_id)}<option value={a.member_id}>{a.display_name}</option>{/each}
        </select>
      </div>
      <div class="field">
        <label for="board-due-{day}">Due</label>
        <input id="board-due-{day}" type="date" bind:value={due} />
      </div>
      <button class="btn primary" type="submit" disabled={busy || !title.trim()}>Add card</button>
    </form>

    <p class="status" class:err={failed} class:ok={!failed && message} role="status">{message}</p>

    {#if loaded && total === 0}
      <p class="muted empty">The board is clear. Add the first task for {dayName} above.</p>
    {/if}

    <div class="lanes">
      {#each lanes as lane (lane.id)}
        <section
          class="lane"
          class:target={dropAt?.lane === lane.id}
          aria-labelledby="lane-{day}-{lane.id}"
          ondragover={(e) => over(e, lane.id, lane.cards.length)}
          ondrop={drop}
        >
          <h3 id="lane-{day}-{lane.id}">{lane.name} <span class="count">{lane.cards.length}</span></h3>
          <ol>
            {#each lane.cards as card, i (card.id)}
              <li
                class="task"
                class:overdue={card.overdue}
                class:lifted={dragged === card.id}
                class:above={dropAt?.lane === lane.id && dropAt.position === i && dragged !== card.id}
                draggable={editing !== card.id}
                ondragstart={(e) => {
                  dragged = card.id;
                  e.dataTransfer?.setData('text/plain', String(card.id));
                }}
                ondragend={() => {
                  dragged = null;
                  dropAt = null;
                }}
                ondragover={(e) => {
                  e.stopPropagation();
                  over(e, lane.id, i);
                }}
              >
                {#if editing === card.id}
                  <form class="editor" onsubmit={(e) => save(e, card)} aria-label="Edit {card.title}">
                    <div class="field">
                      <label for="edit-title-{card.id}">Task</label>
                      <input id="edit-title-{card.id}" bind:value={draft.title} maxlength={TITLE_LIMIT} required />
                    </div>
                    <div class="field">
                      <label for="edit-notes-{card.id}">Notes</label>
                      <textarea id="edit-notes-{card.id}" rows="3" bind:value={draft.notes} maxlength={NOTES_LIMIT}></textarea>
                    </div>
                    <div class="pair">
                      <div class="field">
                        <label for="edit-who-{card.id}">Assign to</label>
                        <select id="edit-who-{card.id}" bind:value={draft.assignee}>
                          <option value="">Nobody yet</option>
                          {#each assignees as a (a.member_id)}<option value={a.member_id}>{a.display_name}</option>{/each}
                        </select>
                      </div>
                      <div class="field">
                        <label for="edit-due-{card.id}">Due</label>
                        <input id="edit-due-{card.id}" type="date" bind:value={draft.due} />
                      </div>
                    </div>
                    <div class="row">
                      <button class="btn primary" type="submit" disabled={busy || !draft.title.trim()}>Save</button>
                      <button class="btn" type="button" onclick={() => (editing = null)}>Cancel</button>
                      <span class="spacer"></span>
                      <button class="btn" type="button" disabled={busy || i === 0} onclick={() => shift(card, -1)}>Move up</button>
                      <button class="btn" type="button" disabled={busy || i === lane.cards.length - 1} onclick={() => shift(card, 1)}
                        >Move down</button
                      >
                      <button class="btn danger" type="button" disabled={busy} onclick={() => remove(card)}>
                        {confirmRemove ? 'Remove for good' : 'Remove'}
                      </button>
                    </div>
                  </form>
                {:else}
                  <button class="title" type="button" onclick={() => edit(card)} aria-label="Edit {card.title}">{card.title}</button>
                  {#if card.notes}<p class="notes">{card.notes}</p>{/if}
                  <div class="meta">
                    <span class="who" class:nobody={!card.assignee_name}>{card.assignee_name ?? 'Unassigned'}</span>
                    {#if card.due_on}
                      <span class="due">
                        {#if card.overdue}<strong>Overdue</strong> · {/if}{dueLabel(card.due_on)}
                      </span>
                    {/if}
                  </div>
                  <div class="arrows">
                    {#if neighbourLane(card.lane, -1)}
                      {@const left = neighbourLane(card.lane, -1)!}
                      <button class="btn arrow" type="button" disabled={busy} onclick={() => step(card, -1)}>
                        <span aria-hidden="true">←</span><span class="sr-only">Move {card.title} to {laneName(left)}</span>
                      </button>
                    {/if}
                    {#if neighbourLane(card.lane, 1)}
                      {@const right = neighbourLane(card.lane, 1)!}
                      <button class="btn arrow" type="button" disabled={busy} onclick={() => step(card, 1)}>
                        <span class="label" aria-hidden="true">{laneName(right)} →</span><span class="sr-only"
                          >Move {card.title} to {laneName(right)}</span
                        >
                      </button>
                    {/if}
                  </div>
                {/if}
              </li>
            {/each}
          </ol>
        </section>
      {/each}
    </div>
  {/if}
</section>

<style>
  .board { display: grid; gap: 0.9rem; }
  .head { display: grid; gap: 0.25rem; }
  .head h2 { margin: 0; font-family: 'Cinzel', Georgia, serif; color: var(--bronze-hi); letter-spacing: 0.03em; }
  .head p { margin: 0; max-width: 62ch; }
  .add { display: flex; flex-wrap: wrap; gap: 0.6rem 0.9rem; align-items: flex-end; }
  .add .grow { flex: 1 1 16rem; }
  .add .grow input { width: 100%; }
  .status { margin: 0; min-height: 1.2em; font-size: 0.9rem; }
  .empty { margin: 0; }
  .lanes { display: grid; gap: 0.9rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr)); align-items: start; }
  .lane {
    background: var(--ink);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.75rem;
    display: grid;
    gap: 0.6rem;
    min-height: 6rem;
  }
  .lane.target { border-color: var(--teal); }
  .lane h3 { margin: 0; font-size: 0.95rem; color: var(--cream); display: flex; align-items: center; gap: 0.5rem; }
  .count { font-size: 0.8rem; color: var(--muted); font-variant-numeric: tabular-nums; }
  ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
  .task {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.6rem 0.65rem;
    display: grid;
    gap: 0.35rem;
    cursor: grab;
  }
  .task.lifted { opacity: 0.5; }
  .task.above { box-shadow: 0 -3px 0 var(--teal); }
  .task.overdue { border-color: color-mix(in srgb, var(--warn) 70%, var(--line)); }
  .title {
    background: none;
    border: 0;
    padding: 0;
    color: var(--cream);
    font: inherit;
    font-weight: 600;
    text-align: left;
    cursor: pointer;
    line-height: 1.3;
  }
  .title:hover { color: var(--bronze-hi); }
  .notes { margin: 0; font-size: 0.85rem; color: var(--muted); white-space: pre-line; }
  .meta { display: flex; flex-wrap: wrap; gap: 0.25rem 0.75rem; font-size: 0.82rem; }
  .who { color: var(--teal); }
  .who.nobody { color: var(--muted); }
  .due { color: var(--muted); }
  .overdue .due { color: var(--warn); }
  .arrows { display: flex; justify-content: space-between; gap: 0.5rem; }
  .arrow { padding: 0.2rem 0.55rem; font-size: 0.8rem; }
  .arrows .arrow:only-child:not(:first-child) { margin-left: auto; }
  .editor { display: grid; gap: 0.5rem; }
  .editor input, .editor select { width: 100%; }
  .pair { display: grid; gap: 0.5rem; grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr)); }
  .row { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
  .row .btn { padding: 0.35rem 0.7rem; font-size: 0.85rem; }
  .spacer { flex: 1; }
</style>
