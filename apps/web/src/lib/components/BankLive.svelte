<script lang="ts">
  import { onMount } from 'svelte';
  import { ApiError } from '$lib/api';
  import {
    bankError,
    bankTime,
    bestSource,
    cancelRequest,
    captureRange,
    createRequest,
    filterItems,
    freshnessClass,
    freshnessLabel,
    getBankMe,
    getInventory,
    getReplica,
    isOpen,
    listSources,
    myRequests,
    newKey,
    observationAge,
    requestStatusLabel,
    slotsInOrder,
    staleCurrent,
    waitlistOffer,
    type BankMe,
    type BankRequest,
    type BankSource,
    type Inventory,
    type NewRequest,
    type Replica
  } from '$lib/bank';
  import BankOfficer from './BankOfficer.svelte';

  type View =
    | { kind: 'loading' }
    | { kind: 'signed-out' }
    | { kind: 'off' }
    | { kind: 'error'; message: string }
    | { kind: 'ready' };

  let view = $state<View>({ kind: 'loading' });
  let me = $state<BankMe | null>(null);
  let sources = $state<BankSource[]>([]);
  let inventory = $state<Inventory>({ range: null, items: [] });
  let mine = $state<BankRequest[]>([]);
  let replica = $state<Replica | null>(null);
  let replicaSource = $state('');
  let search = $state('');
  let now = $state(Date.now());
  let notice = $state('');
  let busy = $state(false);

  // The request form. A key per submission: a retry after a lost answer is not a second request.
  let itemId = $state<number | null>(null);
  let sourceId = $state('');
  let quantity = $state(1);
  let character = $state('');
  let note = $state('');
  let formKey = newKey();
  let offer = $state<{ body: NewRequest; available: number } | null>(null);

  let shown = $derived(filterItems(inventory.items, search));
  let chosen = $derived(inventory.items.find((i) => i.itemId === itemId) ?? null);
  let sourceName = $derived(new Map(sources.map((s) => [s.id, s.name])));
  let officerDay = $derived(me?.officer_days[0] ?? null);

  function fail(e: unknown) {
    if (e instanceof ApiError && e.status === 401) view = { kind: 'signed-out' };
    else notice = bankError(e);
  }

  async function refresh() {
    now = Date.now();
    [sources, inventory, mine] = await Promise.all([listSources(), getInventory(), myRequests()]);
    if (!replicaSource && sources.length) replicaSource = sources[0].id;
    if (replicaSource) replica = await getReplica(replicaSource);
  }

  async function load() {
    try {
      me = await getBankMe();
      if (!me.configured) {
        view = { kind: 'off' };
        return;
      }
      await refresh();
      view = { kind: 'ready' };
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) view = { kind: 'signed-out' };
      else view = { kind: 'error', message: bankError(e) };
    }
  }

  onMount(load);

  function pick(id: number, jump = false) {
    itemId = id;
    const item = inventory.items.find((i) => i.itemId === id);
    sourceId = (item && bestSource(item)?.sourceId) || '';
    offer = null;
    if (jump) document.getElementById('req-item')?.focus();
  }

  async function send(body: NewRequest) {
    busy = true;
    notice = '';
    try {
      const created = await createRequest(body, formKey);
      formKey = newKey();
      offer = null;
      notice = `Request for ${created.quantity} × ${created.itemName}: ${requestStatusLabel(created).toLowerCase()}.`;
      quantity = 1;
      note = '';
      await refresh();
    } catch (e) {
      formKey = newKey();
      const available = waitlistOffer(e);
      if (available !== null) offer = { body, available };
      fail(e);
    } finally {
      busy = false;
    }
  }

  function submit(event: SubmitEvent) {
    event.preventDefault();
    if (itemId === null || !sourceId) return;
    send({ sourceId, itemId, quantity, character: character.trim(), note: note.trim() || undefined });
  }

  async function cancel(r: BankRequest) {
    busy = true;
    notice = '';
    try {
      await cancelRequest(r, newKey());
      await refresh();
    } catch (e) {
      const current = staleCurrent(e);
      if (current) mine = mine.map((m) => (m.id === current.id ? current : m));
      fail(e);
    } finally {
      busy = false;
    }
  }

  async function showReplica() {
    if (!replicaSource) return;
    try {
      replica = await getReplica(replicaSource);
    } catch (e) {
      fail(e);
    }
  }
</script>

<h1>Guild bank</h1>

{#if view.kind === 'loading'}
  <p class="muted" role="status">Loading the bank…</p>
{:else if view.kind === 'signed-out'}
  <p>Sign in with Discord to see the guild bank. <a href="/auth/login" data-sveltekit-reload>Log in</a></p>
{:else if view.kind === 'off'}
  <p class="muted">The guild bank is not set up on the hub yet.</p>
{:else if view.kind === 'error'}
  <p class="warn" role="alert">{view.message}</p>
  <button class="btn" type="button" onclick={load}>Try again</button>
{:else}
  <p class="notice" role="status" aria-live="polite">{notice}</p>

  <section class="card" aria-labelledby="sources-h">
    <h2 id="sources-h">Banks</h2>
    {#if sources.length === 0}
      <p class="muted">No bank has been registered yet.</p>
    {:else}
      <div class="scroll">
        <table>
          <thead>
            <tr><th scope="col">Bank</th><th scope="col">Freshness</th><th scope="col">Last captured</th><th scope="col">Realm</th></tr>
          </thead>
          <tbody>
            {#each sources as s (s.id)}
              <tr>
                <td>{s.name}{#if s.audience === 'officers'} <span class="pill">Officers</span>{/if}</td>
                <td class={freshnessClass(s.freshness)}>{freshnessLabel(s.freshness)}</td>
                <td>
                  {#if s.lastObservedAt}{observationAge(s.lastObservedAt, now)} <span class="muted">({bankTime(s.lastObservedAt)})</span>{:else}never{/if}
                </td>
                <td class="muted">{s.realm} {s.region}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>

  <section class="card" aria-labelledby="inventory-h">
    <h2 id="inventory-h">Inventory</h2>
    <p class="muted">{captureRange(inventory.range, now)}</p>
    <div class="field search">
      <label for="bank-search">Search items</label>
      <input id="bank-search" type="search" bind:value={search} autocomplete="off" />
    </div>
    <div class="scroll">
      <table>
        <caption class="sr-only">Every item across the banks you can see, each bank counted once</caption>
        <thead>
          <tr>
            <th scope="col">Item</th>
            <th scope="col" class="num">Observed</th>
            <th scope="col" class="num">Pending out</th>
            <th scope="col" class="num">Raid held</th>
            <th scope="col" class="num">Reserved</th>
            <th scope="col" class="num">Available</th>
            <th scope="col"><span class="sr-only">Request</span></th>
          </tr>
        </thead>
        <tbody>
          {#each shown as item (item.itemId)}
            <tr>
              <th scope="row">{item.name}</th>
              <td class="num">{item.observed}</td>
              <td class="num">{item.pendingOutgoing}</td>
              <td class="num">{item.raidHeld}</td>
              <td class="num">{item.directReserved}</td>
              <td class="num"><strong>{item.available}</strong></td>
              <td><button class="btn small" type="button" onclick={() => pick(item.itemId, true)}>Request<span class="sr-only"> {item.name}</span></button></td>
            </tr>
          {:else}
            <tr><td colspan="7" class="muted">{search ? 'Nothing matches that search.' : 'The bank is empty.'}</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="card" aria-labelledby="request-h">
    <h2 id="request-h">Request an item</h2>
    <form class="form" onsubmit={submit}>
      <div class="field">
        <label for="req-item">Item</label>
        <select id="req-item" required value={itemId ?? ''} onchange={(e) => pick(Number(e.currentTarget.value))}>
          <option value="" disabled>Choose an item</option>
          {#each filterItems(inventory.items, '') as item (item.itemId)}
            <option value={item.itemId}>{item.name} ({item.available} available)</option>
          {/each}
        </select>
      </div>
      <div class="field">
        <label for="req-source">From bank</label>
        <select id="req-source" required bind:value={sourceId} disabled={!chosen}>
          {#each chosen?.sources ?? [] as s (s.sourceId)}
            <option value={s.sourceId}>{sourceName.get(s.sourceId) ?? s.sourceId} ({s.available} available)</option>
          {/each}
        </select>
      </div>
      <div class="field">
        <label for="req-qty">Quantity</label>
        <input id="req-qty" type="number" min="1" max="10000" required bind:value={quantity} />
      </div>
      <div class="field">
        <label for="req-char">For character</label>
        <input id="req-char" required maxlength="24" autocomplete="off" bind:value={character} />
      </div>
      <div class="field wide">
        <label for="req-note">Note <span class="muted">(optional)</span></label>
        <input id="req-note" maxlength="200" bind:value={note} />
      </div>
      <div class="actions">
        <button class="btn primary" type="submit" disabled={busy || !chosen}>Request</button>
      </div>
    </form>
    {#if offer}
      <div class="offer" role="alert">
        <p>Only {offer.available} available. You can join the waitlist instead; it holds nothing until stock comes in.</p>
        <button class="btn" type="button" disabled={busy} onclick={() => offer && send({ ...offer.body, waitlist: true })}>
          Join the waitlist
        </button>
      </div>
    {/if}
  </section>

  <section class="card" aria-labelledby="mine-h">
    <h2 id="mine-h">My requests</h2>
    {#if mine.length === 0}
      <p class="muted">You have not asked the bank for anything yet.</p>
    {:else}
      <div class="scroll">
        <table>
          <thead>
            <tr><th scope="col">Item</th><th scope="col">For</th><th scope="col">Bank</th><th scope="col">Status</th><th scope="col"><span class="sr-only">Actions</span></th></tr>
          </thead>
          <tbody>
            {#each mine as r (r.id)}
              <tr>
                <td>{r.quantity} × {r.itemName}</td>
                <td>{r.character}</td>
                <td class="muted">{sourceName.get(r.sourceId) ?? r.sourceId}</td>
                <td>{requestStatusLabel(r)}{#if r.managerNote}<span class="muted"> · {r.managerNote}</span>{/if}</td>
                <td>
                  {#if isOpen(r)}
                    <button class="btn small danger" type="button" disabled={busy} onclick={() => cancel(r)}>Cancel<span class="sr-only"> request for {r.itemName}</span></button>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>

  <section class="card" aria-labelledby="replica-h">
    <h2 id="replica-h">Bank tabs</h2>
    <div class="field search">
      <label for="replica-source">Bank</label>
      <select id="replica-source" bind:value={replicaSource} onchange={showReplica}>
        {#each sources as s (s.id)}<option value={s.id}>{s.name}</option>{/each}
      </select>
    </div>
    {#if replica}
      {#each replica.tabs as tab (tab.index)}
        <details class="tab" open={tab.index === replica.tabs[0]?.index}>
          <summary>
            Tab {tab.index}{tab.name ? `: ${tab.name}` : ''}
            <span class="muted">
              · {tab.status === 'observed' ? `${tab.slots.length} of ${tab.capacity ?? '?'} slots` : 'not readable at the last capture'}
              {#if tab.observedAt}· captured {observationAge(tab.observedAt, now)}{/if}
            </span>
          </summary>
          {#if tab.slots.length}
            <div class="scroll">
              <table>
                <thead><tr><th scope="col" class="num">Slot</th><th scope="col">Item</th><th scope="col" class="num">Count</th></tr></thead>
                <tbody>
                  {#each slotsInOrder(tab.slots) as slot (slot.slot)}
                    <tr><td class="num">{slot.slot}</td><td>{slot.name ?? `Item ${slot.itemId}`}</td><td class="num">{slot.count}</td></tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </details>
      {/each}
    {/if}
  </section>

  {#if me && officerDay}
    <BankOfficer day={officerDay} days={me.officer_days} onchange={refresh} />
  {/if}
{/if}

<style>
  /* Screen-reader-only text is absolutely positioned: keep it inside the table's scroll box. */
  .scroll { position: relative; }
  section { margin-bottom: 1rem; }
  .notice:empty { display: none; }
  .search { max-width: 20rem; margin-bottom: 0.75rem; }
  .form { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr)); align-items: end; }
  .form .wide { grid-column: 1 / -1; }
  .actions { display: flex; gap: 0.5rem; }
  .offer { margin-top: 0.75rem; padding: 0.75rem; border: 1px solid var(--warn); border-radius: 6px; }
  .offer p { margin-top: 0; }
  :global(.btn.small) { padding: 0.25rem 0.6rem; font-size: 0.85rem; }
  .tab { border-top: 1px solid var(--line); padding: 0.5rem 0; }
  .tab summary { cursor: pointer; }
  th[scope='row'] { color: var(--text); font-weight: 400; }
</style>
