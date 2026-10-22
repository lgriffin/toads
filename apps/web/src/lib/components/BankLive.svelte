<script lang="ts">
  import { scrollable } from '$lib/scrollable';
  import { onMount } from 'svelte';
  import { ApiError } from '$lib/api';
  import {
    bankDays,
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
    listSources,
    myRequests,
    keyFor,
    newKey,
    outcomeKnown,
    observationAge,
    requestStatusLabel,
    slotsInOrder,
    staleCurrent,
    waitlistOffer,
    type BankMe,
    type BankRequest,
    type BankSource,
    type Inventory,
    type KeyedSend,
    type NewRequest,
    type Replica
  } from '$lib/bank';
  import { bankDeskError, MAX_QUANTITY, type BankDeskBackend, type BankRequest as DeskRequest } from '$lib/bank-desk';
  import { myRequestRows, stockMatches, stockedItem } from '$lib/bank-mine';
  import { shortDate } from '$lib/format';
  import BankCounter from './BankCounter.svelte';
  import BankGrants from './BankGrants.svelte';
  import BankOfficer from './BankOfficer.svelte';
  import BankRedeem from './BankRedeem.svelte';

  type View =
    | { kind: 'loading' }
    | { kind: 'signed-out' }
    | { kind: 'off' }
    | { kind: 'error'; message: string }
    | { kind: 'ready' };

  // The hub's request desk (docs/bank-desk.md): it takes what the bank's stock list does not hold, so a member has one
  // way to ask and one list of their requests whichever service answers. `onAsked` tells the officers' desk on the same
  // page that a desk request came in.
  let { desk, onAsked }: { desk: BankDeskBackend; onAsked?: () => void } = $props();

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

  let deskMine = $state<DeskRequest[]>([]);
  let deskError = $state('');

  // The ask form. A stocked item goes to ToadsBank, set aside at once; anything else goes to the desk for an officer.
  // A key per stock submission: a retry after a lost answer is not a second request.
  let itemText = $state('');
  // The item id an inventory row's Ask picked, or the member chose when two stocked items share a name.
  let picked = $state<number | null>(null);
  let sourcePick = $state('');
  let quantity = $state(1);
  let character = $state('');
  let note = $state('');
  // The last submission whose outcome is unknown, so a retry of the same form reuses its key.
  let pending: KeyedSend | null = null;
  let offer = $state<{ body: NewRequest; available: number } | null>(null);

  let shown = $derived(filterItems(inventory.items, search));
  let matches = $derived(stockMatches(inventory.items, itemText));
  let chosen = $derived(stockedItem(inventory.items, itemText, picked));
  // Two stocked items share the typed name and none is picked: the member says which, never the desk.
  let twins = $derived(!chosen && matches.length > 1);
  // ToadsBank's requests are only known once the stock loaded, or when the bank is off (there are none).
  let stockKnown = $derived(view.kind === 'ready' || view.kind === 'off');
  let sourceId = $derived(
    chosen ? (chosen.sources.some((s) => s.sourceId === sourcePick) ? sourcePick : (bestSource(chosen)?.sourceId ?? '')) : ''
  );
  let sourceName = $derived(new Map(sources.map((s) => [s.id, s.name])));
  let rows = $derived(myRequestRows(mine, deskMine, (id) => sourceName.get(id) ?? id));
  let canAsk = $derived(
    !busy && !twins && !!itemText.trim() && quantity >= 1 && quantity <= (chosen ? 10000 : MAX_QUANTITY) && (!chosen || (!!sourceId && !!character.trim()))
  );
  let days = $derived(me ? bankDays(me) : { imports: [], manage: [], all: [] });
  let officerDay = $derived(days.all[0] ?? null);

  function fail(e: unknown) {
    if (e instanceof ApiError && e.status === 401) view = { kind: 'signed-out' };
    else notice = bankError(e);
  }

  async function loadDeskMine() {
    try {
      deskMine = await desk.mine();
      deskError = '';
    } catch (e) {
      deskError = bankDeskError(e);
    }
  }

  async function refresh() {
    now = Date.now();
    void loadDeskMine();
    [sources, inventory, mine] = await Promise.all([listSources(), getInventory(), myRequests()]);
    if (!replicaSource && sources.length) replicaSource = sources[0].id;
    if (replicaSource) replica = await getReplica(replicaSource);
  }

  async function load() {
    try {
      me = await getBankMe();
      if (!me.configured) {
        view = { kind: 'off' };
        await loadDeskMine();
        return;
      }
      await refresh();
      view = { kind: 'ready' };
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) view = { kind: 'signed-out' };
      else {
        view = { kind: 'error', message: bankError(e) };
        await loadDeskMine();
      }
    }
  }

  onMount(load);

  /** For the officers' desk on the same page: an answer there changes one of these rows. */
  export function reloadDeskMine() {
    return loadDeskMine();
  }

  /** After a redemption: the member's standing changed, so the import and queue days may have too. */
  async function reloadMe() {
    try {
      me = await getBankMe();
      await refresh();
    } catch (e) {
      fail(e);
    }
  }

  function pick(id: number) {
    const item = inventory.items.find((i) => i.itemId === id);
    if (!item) return;
    itemText = item.name;
    picked = item.itemId;
    sourcePick = bestSource(item)?.sourceId ?? '';
    offer = null;
    document.getElementById('req-item')?.focus();
  }

  async function send(body: NewRequest) {
    busy = true;
    notice = '';
    try {
      const attempt = keyFor(pending, body);
      pending = attempt;
      const created = await createRequest(body, attempt.key);
      pending = null;
      offer = null;
      notice = `Request for ${created.quantity} × ${created.itemName}: ${requestStatusLabel(created).toLowerCase()}.`;
      [itemText, quantity, note, picked] = ['', 1, '', null];
      await refresh();
    } catch (e) {
      if (outcomeKnown(e)) pending = null;
      const available = waitlistOffer(e);
      if (available !== null) offer = { body, available };
      fail(e);
    } finally {
      busy = false;
    }
  }

  async function askDesk(item: string, n: number) {
    busy = true;
    notice = '';
    try {
      await desk.ask(item, n);
      notice = `Asked for ${item} x${n}. An officer will answer, and the Toad Bot will DM you.`;
      [itemText, quantity, note, picked] = ['', 1, '', null];
      onAsked?.();
      await loadDeskMine();
    } catch (e) {
      notice = bankDeskError(e);
    } finally {
      busy = false;
    }
  }

  function submit(event: SubmitEvent) {
    event.preventDefault();
    const typed = itemText.trim().split(/\s+/).join(' ');
    if (!typed) return;
    if (twins) return;
    if (!chosen) {
      askDesk(typed, quantity);
      return;
    }
    if (!sourceId) return;
    send({ sourceId, itemId: chosen.itemId, quantity, character: character.trim(), note: note.trim() || undefined });
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

{#snippet askAndMine()}
  <section class="card" aria-labelledby="request-h">
    <h2 id="request-h">Ask the bank</h2>
    <form class="form" onsubmit={submit}>
      <div class="field wide">
        <label for="req-item">Item</label>
        <input
          id="req-item"
          list="req-items"
          maxlength="100"
          autocomplete="off"
          placeholder="Flask of Relentless Assault"
          aria-describedby="req-how"
          bind:value={itemText}
          oninput={() => (offer = null)}
        />
        <datalist id="req-items">
          {#each filterItems(inventory.items, '') as item (item.itemId)}<option value={item.name}></option>{/each}
        </datalist>
        <p id="req-how" class="muted small how">
          {#if twins}
            The bank holds more than one item by this name. Pick which one below.
          {:else if chosen}
            The bank holds this: {chosen.available} free to ask for. It is set aside for you as soon as you ask.
          {:else if itemText.trim()}
            Not in the bank's stock list, so an officer will read it and the Toad Bot will DM you the answer.
          {:else}
            Pick something the bank holds, or type anything else and an officer will answer.
          {/if}
        </p>
      </div>
      {#if twins}
        <div class="field">
          <label for="req-which">Which one</label>
          <select id="req-which" required onchange={(e) => (picked = Number(e.currentTarget.value) || null)}>
            <option value="">Choose…</option>
            {#each matches as m (m.itemId)}
              <option value={m.itemId}>{m.name} (item {m.itemId}, {m.available} free)</option>
            {/each}
          </select>
        </div>
      {/if}
      <div class="field">
        <label for="req-qty">How many</label>
        <input id="req-qty" type="number" min="1" max={chosen ? 10000 : MAX_QUANTITY} required bind:value={quantity} />
      </div>
      {#if chosen}
        <div class="field">
          <label for="req-char">For character</label>
          <input id="req-char" required maxlength="24" autocomplete="off" bind:value={character} />
        </div>
        {#if chosen.sources.length > 1}
          <div class="field">
            <label for="req-source">From bank</label>
            <select id="req-source" required value={sourceId} onchange={(e) => (sourcePick = e.currentTarget.value)}>
              {#each chosen.sources as s (s.sourceId)}
                <option value={s.sourceId}>{sourceName.get(s.sourceId) ?? s.sourceId} ({s.available} free)</option>
              {/each}
            </select>
          </div>
        {/if}
        <div class="field wide">
          <label for="req-note">Note <span class="muted">(optional)</span></label>
          <input id="req-note" maxlength="200" bind:value={note} />
        </div>
      {/if}
      <div class="actions">
        <button class="btn primary" type="submit" disabled={!canAsk}>Ask the bank</button>
      </div>
    </form>
    {#if offer}
      <div class="offer" role="alert">
        <p>Only {offer.available} free. You can join the waitlist instead; it holds nothing until stock comes in.</p>
        <button class="btn" type="button" disabled={busy} onclick={() => offer && send({ ...offer.body, waitlist: true })}>
          Join the waitlist
        </button>
      </div>
    {/if}
  </section>

  <section class="card" aria-labelledby="mine-h">
    <h2 id="mine-h">Your requests</h2>
    {#if deskError}
      <p class="warn" role="alert">
        Some of your requests did not load: {deskError}
        <button class="btn small" type="button" onclick={loadDeskMine}>Try again</button>
      </p>
    {/if}
    {#if !stockKnown}
      <p class="warn">Your requests for the bank's stock did not load, so only the others show here.</p>
    {/if}
    {#if rows.length === 0 && stockKnown && !deskError}
      <p class="muted">You have not asked the bank for anything yet.</p>
    {:else if rows.length === 0}
      <p class="muted">Nothing to show yet.</p>
    {:else}
      <div class="scroll" use:scrollable>
        <table class="mine">
          <thead>
            <tr><th scope="col">Asked</th><th scope="col">What</th><th scope="col">Answer</th><th scope="col"><span class="sr-only">Actions</span></th></tr>
          </thead>
          <tbody>
            {#each rows as r (r.key)}
              <tr>
                <td class="nowrap">{shortDate(new Date(r.at).toISOString())}</td>
                <td>{r.what}{#if r.detail}<span class="muted small block">{r.detail}</span>{/if}</td>
                <td>
                  <span class="status {r.tone}">{r.status}</span>
                  {#if r.said}<span class="said block">“{r.said}”</span>{/if}
                  {#if r.dm}<span class="small block" class:bad={r.dmFailed} class:muted={!r.dmFailed}>{r.dm}</span>{/if}
                </td>
                <td>
                  {#if r.cancel}
                    {@const req = r.cancel}
                    <button class="btn small danger" type="button" disabled={busy} onclick={() => cancel(req)}>Cancel<span class="sr-only"> request for {req.itemName}</span></button>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
{/snippet}

{#if view.kind === 'loading'}
  <p class="muted" role="status">Loading the bank…</p>
{:else if view.kind === 'signed-out'}
  <p>Sign in with Discord to see the guild bank. <a href="/auth/login" data-sveltekit-reload>Log in</a></p>
{:else if view.kind === 'off' || view.kind === 'error'}
  {#if view.kind === 'off'}
    <p class="muted">The bank's stock is not on the hub yet. Ask for anything below and an officer will answer.</p>
  {:else}
    <p class="warn" role="alert">
      The bank's stock did not load: {view.message} You can still ask below.
      <button class="btn small" type="button" onclick={load}>Try again</button>
    </p>
  {/if}
  <p class="notice" role="status" aria-live="polite">{notice}</p>
  {@render askAndMine()}
{:else}
  <BankCounter formId="req-item" />
  <p class="notice" role="status" aria-live="polite">{notice}</p>

  {@render askAndMine()}

  <section class="card" aria-labelledby="inventory-h">
    <h2 id="inventory-h">Inventory</h2>
    <p class="muted">{captureRange(inventory.range, now)}</p>
    <div class="field search">
      <label for="bank-search">Search items</label>
      <input id="bank-search" type="search" bind:value={search} autocomplete="off" />
    </div>
    <div class="scroll" use:scrollable>
      <table>
        <caption class="sr-only">Every item across the banks you can see, each bank counted once</caption>
        <thead>
          <tr>
            <th scope="col">Item</th>
            <th scope="col" class="num">In the bank</th>
            {#if officerDay}
              <th scope="col" class="num">Pending out</th>
              <th scope="col" class="num">Raid held</th>
              <th scope="col" class="num">Reserved</th>
            {/if}
            <th scope="col" class="num">Free to ask for</th>
            <th scope="col"><span class="sr-only">Request</span></th>
          </tr>
        </thead>
        <tbody>
          {#each shown as item (item.itemId)}
            <tr>
              <th scope="row">{item.name}</th>
              <td class="num">{item.observed}</td>
              {#if officerDay}
                <td class="num">{item.pendingOutgoing}</td>
                <td class="num">{item.raidHeld}</td>
                <td class="num">{item.directReserved}</td>
              {/if}
              <td class="num"><strong>{item.available}</strong></td>
              <td><button class="btn small" type="button" onclick={() => pick(item.itemId)}>Ask<span class="sr-only"> for {item.name}</span></button></td>
            </tr>
          {:else}
            <tr><td colspan={officerDay ? 7 : 4} class="muted">{search ? 'Nothing matches that search.' : 'The bank is empty.'}</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="card" aria-labelledby="sources-h">
    <h2 id="sources-h">Banks</h2>
    {#if sources.length === 0}
      <p class="muted">No bank has been registered yet.</p>
    {:else}
      <div class="scroll" use:scrollable>
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
            <div class="scroll" use:scrollable>
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
    <BankOfficer day={officerDay} days={days.all} importDays={days.imports} manageDays={days.manage} onchange={refresh} />
  {/if}

  {#if me}
    <BankRedeem onredeemed={reloadMe} />
  {/if}

  {#if me?.sees_grants || me?.manages_grants}
    <BankGrants
      days={me.officer_days}
      manage={me.manages_grants ?? false}
      breakGlass={me.break_glass ?? false}
      breakGlassAdmin={me.break_glass_admin ?? null}
    />
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
  .how { margin: 0.25rem 0 0; }
  .small { font-size: 0.85rem; }
  .block { display: block; }
  .nowrap { white-space: nowrap; }
  .said { font-style: italic; max-width: 40ch; }
  .status { font-weight: 600; }
  .status.ok { color: var(--accent); }
  .status.bad { color: var(--bad-text); }
  .status.wait { color: var(--warn); }
  td { vertical-align: top; }
  .offer { margin-top: 0.75rem; padding: 0.75rem; border: 1px solid var(--warn); border-radius: 6px; }
  .offer p { margin-top: 0; }
  :global(.btn.small) { padding: 0.25rem 0.6rem; font-size: 0.85rem; }
  .tab { border-top: 1px solid var(--line); padding: 0.5rem 0; }
  .tab summary { cursor: pointer; }
  th[scope='row'] { color: var(--text); font-weight: 400; }
</style>
