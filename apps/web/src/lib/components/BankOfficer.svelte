<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import { ApiError } from '$lib/api';
  import {
    acceptImport,
    addParts,
    bankError,
    bankTime,
    manageRequest,
    newKey,
    openImport,
    previewImport,
    progressLabel,
    receiptLabel,
    requestQueue,
    requestStatusLabel,
    staleCurrent,
    type BankRequest,
    type ImportPreview,
    type ImportProgress,
    type ManagerAction
  } from '$lib/bank';

  // Officer powers are scoped to a raid day: the queue and imports go through one of the officer's days.
  let { day, days, onchange }: { day: string; days: string[]; onchange: () => Promise<void> } = $props();

  let chosenDay = $state(untrack(() => day));
  let queue = $state<BankRequest[]>([]);
  let message = $state('');
  let busy = $state(false);
  let deliver = $state<Record<string, number>>({});

  let importId = $state<string | null>(null);
  let paste = $state('');
  let progress = $state<ImportProgress | null>(null);
  let preview = $state<ImportPreview | null>(null);
  let receipt = $state('');

  async function loadQueue() {
    try {
      queue = await requestQueue(chosenDay);
    } catch (e) {
      message = bankError(e);
    }
  }

  onMount(loadQueue);

  async function act(r: BankRequest, action: ManagerAction) {
    busy = true;
    message = '';
    try {
      const extra = action === 'deliveries' ? { quantity: deliver[r.id] ?? r.outstanding } : {};
      // A fresh key per click (the buttons are disabled while one is in flight); the revision guards the rest.
      await manageRequest(chosenDay, r, action, extra, newKey());
      await Promise.all([loadQueue(), onchange()]);
    } catch (e) {
      const current = staleCurrent(e);
      if (current) queue = queue.map((q) => (q.id === current.id ? current : q));
      message = bankError(e);
    } finally {
      busy = false;
    }
  }

  async function addPaste(event: SubmitEvent) {
    event.preventDefault();
    const text = paste.trim();
    if (!text) return;
    busy = true;
    message = '';
    receipt = '';
    try {
      if (importId === null) importId = (await openImport(chosenDay, newKey())).id;
      try {
        progress = await addParts(chosenDay, importId, text, newKey());
      } catch (e) {
        // The session expired (30 minutes) or the bank forgot it: start a new one with the same paste.
        if (!(e instanceof ApiError) || !['import_expired', 'not_found'].includes(e.code ?? '')) throw e;
        importId = (await openImport(chosenDay, newKey())).id;
        progress = await addParts(chosenDay, importId, text, newKey());
      }
      paste = '';
      preview = progress.complete ? await previewImport(chosenDay, importId) : null;
    } catch (e) {
      message = bankError(e);
    } finally {
      busy = false;
    }
  }

  async function accept() {
    if (importId === null) return;
    busy = true;
    message = '';
    try {
      receipt = receiptLabel(await acceptImport(chosenDay, importId, `accept:${importId}`));
      discard();
      await onchange();
    } catch (e) {
      message = bankError(e);
    } finally {
      busy = false;
    }
  }

  function discard() {
    importId = null;
    progress = null;
    preview = null;
  }
</script>

<section class="card" aria-labelledby="officer-h">
  <h2 id="officer-h">Officers: requests and imports</h2>
  {#if days.length > 1}
    <div class="field day">
      <label for="officer-day">Acting for raid day</label>
      <select id="officer-day" bind:value={chosenDay} onchange={loadQueue}>
        {#each days as d (d)}<option value={d}>{d}</option>{/each}
      </select>
    </div>
  {/if}
  <p class="notice" role="status" aria-live="polite">{message}</p>

  <h3>Request queue</h3>
  {#if queue.length === 0}
    <p class="muted">Nothing waiting for you.</p>
  {:else}
    <div class="scroll">
      <table>
        <thead>
          <tr><th scope="col">Item</th><th scope="col">For</th><th scope="col">Status</th><th scope="col">Note</th><th scope="col"><span class="sr-only">Actions</span></th></tr>
        </thead>
        <tbody>
          {#each queue as r (r.id)}
            <tr>
              <td>{r.quantity} × {r.itemName}</td>
              <td>{r.character} <span class="muted">({r.memberName})</span></td>
              <td>{requestStatusLabel(r)}</td>
              <td class="muted">{r.note ?? ''}</td>
              <td class="acts">
                {#if r.status === 'reserved'}
                  <button class="btn small" type="button" disabled={busy} onclick={() => act(r, 'approve')}>Approve<span class="sr-only"> {r.itemName} for {r.character}</span></button>
                {/if}
                <button class="btn small danger" type="button" disabled={busy} onclick={() => act(r, 'reject')}>Reject<span class="sr-only"> {r.itemName} for {r.character}</span></button>
                {#if r.status !== 'waitlisted'}
                  <label class="sr-only" for="deliver-{r.id}">Quantity delivered for {r.itemName}</label>
                  <input id="deliver-{r.id}" class="qty" type="number" min="1" max={r.outstanding} value={deliver[r.id] ?? r.outstanding}
                    oninput={(e) => (deliver = { ...deliver, [r.id]: Number(e.currentTarget.value) })} />
                  <button class="btn small" type="button" disabled={busy} onclick={() => act(r, 'deliveries')}>Record delivery<span class="sr-only"> of {r.itemName}</span></button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  <h3>Import a bank export</h3>
  <p class="muted">
    Paste the parts the ToadsBank addon shows, in any order and over several goes. Discord code fences are fine.
  </p>
  <form onsubmit={addPaste}>
    <div class="field">
      <label for="import-paste">Export parts</label>
      <textarea id="import-paste" rows="6" spellcheck="false" bind:value={paste} disabled={busy}></textarea>
    </div>
    <p class="actions"><button class="btn" type="submit" disabled={busy || !paste.trim()}>Add parts</button></p>
  </form>
  {#if progress}<p role="status">{progressLabel(progress)}</p>{/if}
  {#if preview}
    <div class="preview">
      <p>
        {preview.matchedSource ? preview.matchedSource.name : `An unregistered bank (${preview.source.guild}, ${preview.source.realm} ${preview.source.region})`},
        captured {bankTime(preview.capturedAt)}{preview.uploader ? ` by ${preview.uploader.name}` : ''}.
      </p>
      <ul>
        {#each preview.tabs as tab (tab.index)}
          <li>Tab {tab.index}{tab.name ? ` ${tab.name}` : ''}: {tab.status === 'observed' ? `${tab.items} items in ${tab.occupied} slots` : tab.status}</li>
        {/each}
      </ul>
      {#each preview.warnings as warning}<p class="warn">{warning}</p>{/each}
      {#if !preview.stable}<p class="warn">The bank changed while it was being captured, so some counts may be off.</p>{/if}
      {#if preview.existingReceipt}<p class="muted">This snapshot was accepted before; accepting again changes nothing.</p>{/if}
      <p class="actions">
        <button class="btn primary" type="button" disabled={busy} onclick={accept}>Accept snapshot</button>
        <button class="btn" type="button" disabled={busy} onclick={discard}>Cancel</button>
      </p>
    </div>
  {/if}
  {#if receipt}<p class="ok" role="status">{receipt}</p>{/if}
</section>

<style>
  /* Screen-reader-only text is absolutely positioned: keep it inside the table's scroll box. */
  .scroll { position: relative; }
  h3 { font-size: 1rem; margin: 1rem 0 0.5rem; }
  .day { max-width: 16rem; margin-bottom: 0.5rem; }
  .notice:empty { display: none; }
  .acts { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; }
  .qty { width: 4.5rem; padding: 0.2rem 0.4rem; }
  .actions { display: flex; gap: 0.5rem; }
  .preview { border: 1px solid var(--line); border-radius: 6px; padding: 0.75rem; }
</style>
