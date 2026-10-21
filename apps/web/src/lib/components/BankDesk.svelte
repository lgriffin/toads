<script lang="ts">
  import {
    askedBefore,
    bankDeskError,
    ITEM_LIMIT,
    MAX_QUANTITY,
    MESSAGE_LIMIT,
    noticeLabel,
    pendingCount,
    shown,
    sourceLabel,
    STATUS_LABEL,
    type BankDeskBackend,
    type BankRequest,
    type DeskFilter,
    type Verdict
  } from '$lib/bank-desk';
  import { shortDate } from '$lib/format';

  // The bank request desk (docs/bank-desk.md): what members asked for with the Toad Bot's /bankrequest or here, for
  // officers to approve or deny with a message the Toad Bot DMs back. Everyone sees their own requests and can ask
  // here too. The API checks every permission (manage_bank on the route's raid day); this desk only shows itself.
  // `own` false leaves out the member's own requests and the ask form, for the bank page, where the member asks and
  // reads their requests once for both the desk and the bank's stock (BankLive); everyone else then sees nothing here.
  let { backend, own = true }: { backend: BankDeskBackend; own?: boolean } = $props();

  let day = $state<string | null>(null);
  let rows = $state<BankRequest[]>([]);
  let mine = $state<BankRequest[]>([]);
  let loaded = $state(false);
  // Kept apart, so a failed officer list never hides the member's own requests or the ask form.
  let deskError = $state('');
  let mineError = $state('');
  let filter = $state<DeskFilter>('pending');
  let answering = $state<number | null>(null);
  let note = $state('');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);
  let historyOf = $state<{ id: string; name: string; rows: BankRequest[] } | null>(null);
  let item = $state('');
  let quantity = $state(1);

  const listed = $derived(shown(rows, filter));
  const waiting = $derived(pendingCount(rows));
  const counts = $derived(askedBefore(rows));

  async function loadDesk() {
    try {
      const days = await backend.manageDays();
      day = days[0] ?? null;
      rows = day ? await backend.incoming(day) : [];
      deskError = '';
    } catch (e) {
      deskError = bankDeskError(e);
    }
  }

  async function loadMine() {
    try {
      mine = await backend.mine();
      mineError = '';
    } catch (e) {
      mineError = bankDeskError(e);
    }
  }

  /** Both lists; each keeps its own error, shown beside a retry. */
  async function refresh() {
    await Promise.all([loadDesk(), own ? loadMine() : null]);
  }

  async function load() {
    await refresh();
    loaded = true;
  }
  $effect(() => {
    load();
  });

  function open(r: BankRequest) {
    answering = answering === r.id ? null : r.id;
    note = '';
  }

  async function act(action: () => Promise<unknown>, done: string): Promise<boolean> {
    busy = true;
    try {
      await action();
      message = done;
      failed = false;
    } catch (e) {
      message = bankDeskError(e);
      failed = true;
    }
    await refresh();
    try {
      if (historyOf && day) historyOf = { ...historyOf, rows: await backend.history(day, historyOf.id) };
    } catch (e) {
      message += ` Their history could not be refreshed: ${bankDeskError(e)}`;
    }
    busy = false;
    return !failed;
  }

  async function answer(r: BankRequest, verdict: Verdict) {
    const d = day;
    if (!d) return;
    const word = verdict === 'approve' ? 'Approved' : 'Denied';
    const sent = await act(
      () => backend.answer(d, r.id, verdict, note),
      `${word} ${r.requester_name}’s ${r.item} x${r.quantity}. The Toad Bot will DM them.`
    );
    if (sent) [answering, note] = [null, ''];
  }

  async function showHistory(r: BankRequest) {
    if (!day) return;
    if (historyOf?.id === r.discord_user_id) {
      historyOf = null;
      return;
    }
    try {
      historyOf = { id: r.discord_user_id, name: r.requester_name, rows: await backend.history(day, r.discord_user_id) };
    } catch (e) {
      message = bankDeskError(e);
      failed = true;
    }
  }

  async function ask(event: SubmitEvent) {
    event.preventDefault();
    const what = item.trim();
    if (!what) return;
    const n = quantity;
    if (await act(() => backend.ask(what, n), `Asked for ${what} x${n}. You will hear back by DM from the Toad Bot.`)) {
      [item, quantity] = ['', 1];
    }
  }
</script>

{#snippet answerOf(r: BankRequest, own = false)}
  <span class="status {r.status}">{STATUS_LABEL[r.status]}</span>
  {#if r.decided_by_name}<span class="muted small">by {r.decided_by_name}{r.decided_at ? `, ${shortDate(r.decided_at)}` : ''}</span>{/if}
  {#if r.officer_message}<span class="said">“{r.officer_message}”</span>{/if}
  {#if r.notice}<span class="small" class:bad={r.notice === 'failed'} class:muted={r.notice !== 'failed'}>{noticeLabel(r, own)}</span>{/if}
{/snippet}

{#if own || !loaded || day || deskError}
<section class="card desk" aria-labelledby="bank-desk-h">
  <div class="head">
    <h2 id="bank-desk-h">Bank requests</h2>
    {#if day}<span class="pill">{waiting} waiting</span>{/if}
  </div>
  <p class="muted lede">
    {#if own}
      Ask the guild bank with <code>/bankrequest</code> in Discord, giving the item and how many, or below.
      {#if day}Officers answer here; the Toad Bot DMs each member the answer and your message.{/if}
    {:else}
      What members asked for with <code>/bankrequest</code> in Discord, or here for something the bank's stock list does
      not hold. Answer here; the Toad Bot DMs each member the answer and your message.
    {/if}
  </p>

  {#if !loaded}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if deskError}
      <p class="err retry" role="alert">
        The request list did not load: {deskError}
        <button type="button" class="btn small" onclick={loadDesk}>Try again</button>
      </p>
    {:else if day}
      <div class="filters" role="group" aria-label="Show">
        <button type="button" class="btn small" aria-pressed={filter === 'pending'} onclick={() => (filter = 'pending')}>
          Waiting ({waiting})
        </button>
        <button type="button" class="btn small" aria-pressed={filter === 'all'} onclick={() => (filter = 'all')}>
          Every request ({rows.length})
        </button>
      </div>

      {#if listed.length}
        <!-- Focusable so keyboard users can scroll the table when it is wider than the card. -->
        <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
        <div class="scroll" tabindex="0" role="group" aria-label="Bank requests table">
          <table aria-labelledby="bank-desk-h">
            <thead>
              <tr>
                <th scope="col">Asked</th>
                <th scope="col">Member</th>
                <th scope="col">Item</th>
                <th scope="col">Answer</th>
              </tr>
            </thead>
            <tbody>
              {#each listed as r (r.id)}
                {@const c = counts.get(r.discord_user_id)}
                <tr>
                  <td>
                    <span class="nowrap">{shortDate(r.created_at)}</span>
                    <span class="muted small">#{r.id} · {sourceLabel(r.source)}</span>
                  </td>
                  <td>
                    <button
                      type="button"
                      class="link"
                      aria-expanded={historyOf?.id === r.discord_user_id}
                      onclick={() => showHistory(r)}
                    >
                      {r.requester_name}<span class="sr-only">: show their requests</span>
                    </button>
                    {#if c && c.asked > 1}<span class="muted small">{c.asked} asks, {c.approved} approved</span>{/if}
                  </td>
                  <td><strong>{r.item}</strong> <span class="qty">x{r.quantity}</span></td>
                  <td class="answer">
                    {#if r.status === 'pending'}
                      <button
                        type="button"
                        class="btn small primary"
                        aria-expanded={answering === r.id}
                        disabled={busy}
                        onclick={() => open(r)}
                      >
                        Answer<span class="sr-only"> {r.requester_name}’s request for {r.item}</span>
                      </button>
                    {:else}
                      {@render answerOf(r)}
                    {/if}
                  </td>
                </tr>
                {#if answering === r.id}
                  <tr class="answering">
                    <td colspan="4">
                      <div class="field">
                        <label for="bank-desk-note-{r.id}">Message to {r.requester_name} (optional)</label>
                        <textarea
                          id="bank-desk-note-{r.id}"
                          rows="2"
                          maxlength={MESSAGE_LIMIT}
                          placeholder="Grab it from Gail after the raid"
                          bind:value={note}
                        ></textarea>
                      </div>
                      <div class="actions">
                        <button type="button" class="btn primary" disabled={busy} onclick={() => answer(r, 'approve')}>
                          Approve
                        </button>
                        <button type="button" class="btn danger" disabled={busy} onclick={() => answer(r, 'deny')}>
                          Deny
                        </button>
                        <button type="button" class="btn" disabled={busy} onclick={() => (answering = null)}>Cancel</button>
                      </div>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <p class="muted">{filter === 'pending' ? 'Nothing waiting. Every request has an answer.' : 'Nobody has asked the bank for anything yet.'}</p>
      {/if}

      {#if historyOf}
        <div class="history" aria-labelledby="bank-desk-history-h">
          <h3 id="bank-desk-history-h">{historyOf.name}’s requests</h3>
          {@render list(historyOf.rows)}
          <button type="button" class="btn small" onclick={() => (historyOf = null)}>Close</button>
        </div>
      {/if}
    {/if}

    {#if own}
    <div class="own">
      <h3>Your requests</h3>
      {#if mineError}
        <p class="err retry" role="alert">
          Your requests did not load: {mineError}
          <button type="button" class="btn small" onclick={loadMine}>Try again</button>
        </p>
      {:else if mine.length}{@render list(mine, true)}{:else}<p class="muted">You have not asked the bank for anything yet.</p>{/if}
      <form class="ask" onsubmit={ask}>
        <div class="field grow">
          <label for="bank-desk-item">Item</label>
          <input id="bank-desk-item" maxlength={ITEM_LIMIT} autocomplete="off" placeholder="Flask of Relentless Assault" bind:value={item} />
        </div>
        <div class="field">
          <label for="bank-desk-qty">How many</label>
          <input id="bank-desk-qty" type="number" min="1" max={MAX_QUANTITY} bind:value={quantity} />
        </div>
        <button class="btn" type="submit" disabled={busy || !item.trim() || !(quantity >= 1 && quantity <= MAX_QUANTITY)}>
          Ask the bank
        </button>
      </form>
    </div>
    {/if}

    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
  {/if}
</section>
{/if}

{#snippet list(items: BankRequest[], own = false)}
  <ul class="asks">
    {#each items as r (r.id)}
      <li>
        <span><strong>{r.item}</strong> x{r.quantity} <span class="muted small">{shortDate(r.created_at)} · {sourceLabel(r.source)}</span></span>
        <span class="said-line">{@render answerOf(r, own)}</span>
      </li>
    {/each}
  </ul>
{/snippet}

<style>
  .desk { display: grid; gap: 0.75rem; align-content: start; }
  .desk h2, .desk h3, .desk p { margin: 0; }
  .head { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.75rem; }
  .lede { max-width: 66ch; }
  .filters, .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .btn.small { padding: 0.3rem 0.65rem; font-size: 0.85rem; }
  .btn[aria-pressed='true'] { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 16%, var(--surface)); }
  .scroll { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; min-width: 34rem; }
  td { vertical-align: top; }
  td > span, .answer > span, .said-line > span { display: block; }
  .nowrap { white-space: nowrap; }
  .small { font-size: 0.8rem; }
  .qty { font-variant-numeric: tabular-nums; }
  .link { background: none; border: 0; padding: 0; font: inherit; color: var(--accent); cursor: pointer; text-align: left; }
  .link:hover { text-decoration: underline; }
  .status { font-weight: 600; }
  .status.approved { color: var(--accent); }
  .status.denied { color: var(--bad-text); }
  .status.pending { color: var(--warn); }
  .said { font-style: italic; max-width: 40ch; }
  .answering td { background: color-mix(in srgb, var(--accent) 6%, var(--surface)); }
  .answering .field { margin-bottom: 0.5rem; }
  .history, .own { display: grid; gap: 0.5rem; padding-top: 0.75rem; border-top: 1px solid var(--line); }
  .history .btn { justify-self: start; }
  .asks { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
  .asks li { display: grid; gap: 0.15rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--line); }
  .said-line { display: flex; flex-wrap: wrap; gap: 0.15rem 0.6rem; align-items: baseline; }
  .said-line > span { display: inline; }
  .ask { display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; align-items: flex-end; }
  .ask .grow { flex: 1 1 14rem; }
  .retry { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
  .ask input[type='number'] { width: 6rem; }
  /* On a phone each request is a small card, so Answer is never scrolled off the side. */
  @media (max-width: 40rem) {
    table { min-width: 0; }
    thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); }
    tbody, tr, td { display: block; }
    tbody tr { padding: 0.6rem 0; border-bottom: 1px solid var(--line); }
    td { border: 0; padding: 0.15rem 0; }
    .answering { padding-top: 0; }
  }
</style>
