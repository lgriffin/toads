<script lang="ts">
  import { base } from '$app/paths';
  import {
    CATEGORY_LABEL,
    CLASSES,
    RAID_SIZES,
    ROLES,
    classCounts,
    classOf,
    clear,
    compError,
    coverage,
    dayLabel,
    emptySlots,
    groupBuffs,
    groupCount,
    matches,
    otherSpec,
    place,
    resize,
    roleCounts,
    seatFor,
    specLabel,
    specOf,
    specsOfClass,
    swap,
    toSlots,
    type CompBackend,
    type Coverage,
    type PoolEntry,
    type Role,
    type SavedComp,
    type Scope,
    type Seat,
    type Slots
  } from '$lib/comp';

  // The officers' comp builder. "Any comp" seats specs with no names, to try a composition and see its buffs; the
  // roster switch seats that raid night's members by the specs they set on Me. Drag a spec or a member onto a seat,
  // drag seats onto each other to swap them, or tap one then the other where dragging is awkward. The API checks the
  // permission (build_comps, scoped to the raid night); this page only hides the builder from everyone else.
  // `initial` is the night to open on, such as the one a night's officer section linked from, when it is one of `days`.
  let { backend, days, initial = '' }: { backend: CompBackend; days: string[]; initial?: string } = $props();

  type Mode = 'any' | 'roster';
  // What is being placed: a spec or a member from the palette, or a seat being moved.
  type Pick = { kind: 'spec'; spec: string } | { kind: 'member'; entry: PoolEntry } | { kind: 'seat'; index: number };

  let day = $state('');
  let mode = $state<Mode>('any');
  let slots = $state<Slots>(emptySlots(40));
  let pool = $state<PoolEntry[]>([]);
  let poolError = $state('');
  let saved = $state<SavedComp[]>([]);
  let current = $state<SavedComp | null>(null);
  let name = $state('');
  let message = $state('');
  let failed = $state(false);
  let busy = $state(false);
  let picked = $state<Pick | null>(null);
  let over = $state<number | null>(null);

  let filterClass = $state('');
  let filterSpec = $state('');
  let filterRole = $state<Role | ''>('');
  let query = $state('');

  $effect(() => {
    if (!day && days.length) day = days.includes(initial) ? initial : days[0];
  });

  const size = $derived(slots.length);
  const cover = $derived(coverage(slots));
  const roles = $derived(roleCounts(slots));
  const classes = $derived(classCounts(slots));
  const filled = $derived(slots.filter(Boolean).length);
  const filter = $derived({
    wowClass: filterClass || undefined,
    spec: filterSpec || undefined,
    role: filterRole || undefined,
    query
  });
  const seated = $derived(new Set(slots.flatMap((s) => (s?.memberId ? [s.memberId] : []))));
  const withSpecs = $derived(pool.filter((e) => e.wow_class));
  const shown = $derived(withSpecs.filter((e) => matches(e, filter)));
  const unset = $derived(pool.filter((e) => !e.wow_class));
  const groups = $derived(Array.from({ length: groupCount(size) }, (_, g) => g));

  async function loadDay(d: string) {
    poolError = '';
    try {
      const [p, s] = await Promise.all([backend.pool(d), backend.comps(d)]);
      // A slower answer for a night the officer has since switched away from is dropped.
      if (d !== day) return;
      [pool, saved] = [p, s];
    } catch (e) {
      if (d !== day) return;
      pool = [];
      saved = [];
      poolError = compError(e);
    }
  }
  $effect(() => {
    if (day) loadDay(day);
  });

  function say(text: string, error = false) {
    message = text;
    failed = error;
  }

  function setSize(n: number) {
    const lost = slots.slice(n).filter(Boolean).length;
    slots = resize(slots, n);
    if (lost) say(`${lost} seat${lost === 1 ? '' : 's'} beyond ${n} came off the comp.`);
  }

  function fill(index: number, p: Pick) {
    if (p.kind === 'seat') {
      if (p.index !== index) slots = swap(slots, p.index, index);
    } else if (p.kind === 'spec') {
      slots = place(slots, index, { spec: p.spec, memberId: null });
    } else {
      const seat = seatFor(p.entry, filter);
      if (seat) slots = place(slots, index, seat);
    }
  }

  // ---------------------------------------------------------------- tap to place

  const same = (a: Pick | null, b: Pick) =>
    !!a &&
    a.kind === b.kind &&
    ((a.kind === 'spec' && b.kind === 'spec' && a.spec === b.spec) ||
      (a.kind === 'member' && b.kind === 'member' && a.entry.member_id === b.entry.member_id) ||
      (a.kind === 'seat' && b.kind === 'seat' && a.index === b.index));

  function pick(p: Pick) {
    picked = same(picked, p) ? null : p;
  }

  function tapSeat(index: number) {
    if (picked) {
      fill(index, picked);
      // Keep a spec picked, so a row of the same spec is a few taps; members and seats are placed once.
      if (picked.kind !== 'spec') picked = null;
    } else if (slots[index]) {
      picked = { kind: 'seat', index };
    }
  }

  function onKey(event: KeyboardEvent) {
    if (event.key === 'Escape') picked = null;
  }

  // ---------------------------------------------------------------- drag and drop

  let dragging: Pick | null = null;

  function dragStart(event: DragEvent, p: Pick) {
    dragging = p;
    event.dataTransfer?.setData('text/plain', p.kind);
    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
  }

  function dragEnd() {
    dragging = null;
    over = null;
  }

  function dragOver(event: DragEvent, index: number) {
    if (!dragging) return;
    event.preventDefault();
    over = index;
  }

  function drop(event: DragEvent, index: number) {
    event.preventDefault();
    if (dragging) fill(index, dragging);
    dragEnd();
  }

  // A seat dragged back to the palette leaves the comp.
  function dropOnPalette(event: DragEvent) {
    event.preventDefault();
    if (dragging?.kind === 'seat') slots = clear(slots, dragging.index);
    dragEnd();
  }

  function paletteOver(event: DragEvent) {
    if (dragging?.kind === 'seat') event.preventDefault();
  }

  function switchSpec(index: number) {
    const seat = slots[index];
    const other = seat && otherSpec(seat, pool);
    if (seat && other) slots = place(slots, index, { ...seat, spec: other });
  }

  // ---------------------------------------------------------------- saved comps

  function load(c: SavedComp) {
    slots = toSlots(c);
    current = c;
    name = c.name;
    if (c.slots.some((s) => s?.member_id)) mode = 'roster';
    say(`Loaded ${c.name}.`);
  }

  function startNew() {
    slots = emptySlots(size);
    current = null;
    name = '';
    picked = null;
    say('');
  }

  async function save(asNew: boolean) {
    const id = asNew || !current ? null : current.id;
    const d = day;
    busy = true;
    try {
      const c = await backend.save(d, id, name, slots);
      if (d !== day) return;
      current = c;
      saved = [...saved.filter((s) => s.id !== c.id), c].sort((a, b) => a.name.localeCompare(b.name));
      say(`Locked in ${c.name} for ${dayLabel(day)}.`);
    } catch (e) {
      say(compError(e), true);
    } finally {
      busy = false;
    }
  }

  async function remove(c: SavedComp) {
    const d = day;
    busy = true;
    try {
      await backend.remove(d, c.id);
      if (d !== day) return;
      saved = saved.filter((s) => s.id !== c.id);
      if (current?.id === c.id) current = null;
      say(`Deleted ${c.name}.`);
    } catch (e) {
      say(compError(e), true);
    } finally {
      busy = false;
    }
  }

  function changeDay(d: string) {
    day = d;
    current = null;
  }

  // ---------------------------------------------------------------- reading the comp

  const SCOPES: { id: Scope; title: string }[] = [
    { id: 'raid', title: 'Raid buffs' },
    { id: 'party', title: 'Party buffs' },
    { id: 'target', title: 'Debuffs and single target' }
  ];

  const byScope = (scope: Scope) => cover.filter((c) => c.buff.scope === scope);

  function whoBrings(c: Coverage): string {
    const counts = new Map<string, number>();
    for (const i of c.seats) {
      const cls = classOf(specOf(slots[i]?.spec)?.wowClass)?.name ?? '';
      counts.set(cls, (counts.get(cls) ?? 0) + 1);
    }
    const who = [...counts].map(([cls, n]) => (n > 1 ? `${cls} ×${n}` : cls)).join(', ');
    return c.buff.scope === 'party' ? `${who} · group${c.groups.length > 1 ? 's' : ''} ${c.groups.map((g) => g + 1).join(', ')}` : who;
  }

  function couldBring(c: Coverage): string {
    return c.buff.providers
      .map((p) => {
        const cls = classOf(p.wowClass)?.name ?? p.wowClass;
        const how = p.spec ? specOf(p.spec)?.name : p.via;
        return how ? `${cls} (${how})` : cls;
      })
      .join(' or ');
  }

  const seatTitle = (s: Seat) => `${specLabel(s.spec)}${s.memberName ? `, ${s.memberName}` : ''}`;
  const colour = (spec: string | null | undefined) => classOf(specOf(spec)?.wowClass)?.colour ?? 'var(--line)';
  const pickedLabel = $derived(
    !picked
      ? ''
      : picked.kind === 'spec'
        ? specLabel(picked.spec)
        : picked.kind === 'member'
          ? picked.entry.name
          : slots[picked.index]
            ? seatTitle(slots[picked.index]!)
            : ''
  );
</script>

<svelte:window onkeydown={onKey} />

<section class="builder" aria-labelledby="comp-h">
  <header class="top">
    <h1 id="comp-h">Raid comp builder</h1>
    <div class="controls">
      {#if days.length > 1}
        <div class="field">
          <label for="comp-day">Raid night</label>
          <select id="comp-day" value={day} disabled={busy} onchange={(e) => changeDay(e.currentTarget.value)}>
            {#each days as d (d)}<option value={d}>{dayLabel(d)}</option>{/each}
          </select>
        </div>
      {/if}
      <div class="seg" role="group" aria-label="Raid size">
        {#each RAID_SIZES as n (n)}
          <button type="button" aria-pressed={size === n} onclick={() => setSize(n)}>{n}</button>
        {/each}
      </div>
      <div class="seg" role="group" aria-label="What to seat">
        <button type="button" aria-pressed={mode === 'any'} onclick={() => (mode = 'any')}>Any comp</button>
        <button type="button" aria-pressed={mode === 'roster'} onclick={() => (mode = 'roster')}>
          {day ? `${dayLabel(day)} roster` : 'Roster'}
        </button>
      </div>
    </div>
  </header>

  <p class="muted lede">
    {#if mode === 'any'}
      Drag specs onto the groups to try a composition and see the buffs it brings. No names, so any comp can be built.
    {:else}
      Everyone on {dayLabel(day)}'s roster, by the specs they set on Me. Filter for a spec to find who plays it as a
      primary or a secondary, then drag them into a group.
    {/if}
    On a phone, tap a spec or a member, then tap the seat.
  </p>

  <div class="layout">
    <!-- The palette: specs in "any comp", the raid night's members in roster mode. A seat dropped here leaves the comp. -->
    <aside class="palette card" aria-label={mode === 'any' ? 'Specs' : 'Roster'} ondragover={paletteOver} ondrop={dropOnPalette}>
      {#if mode === 'any'}
        <ul class="classes">
          {#each CLASSES as c (c.id)}
            <li style="--class: {c.colour}">
              <img src="{base}/logos/classes/{c.id}.svg" alt="" width="32" height="28" loading="lazy" />
              <span class="cname">{c.name}</span>
              <div class="specs">
                {#each specsOfClass(c.id) as s (s.id)}
                  <button
                    type="button"
                    class="spec"
                    draggable="true"
                    aria-pressed={same(picked, { kind: 'spec', spec: s.id })}
                    ondragstart={(e) => dragStart(e, { kind: 'spec', spec: s.id })}
                    ondragend={dragEnd}
                    onclick={() => pick({ kind: 'spec', spec: s.id })}
                  >
                    {s.name}<span class="sr-only"> {c.name}</span>
                  </button>
                {/each}
              </div>
            </li>
          {/each}
        </ul>
      {:else}
        <div class="filters">
          <div class="field">
            <label for="comp-q">Name</label>
            <input id="comp-q" type="search" placeholder="Search the roster" bind:value={query} />
          </div>
          <div class="field">
            <label for="comp-class">Class</label>
            <select
              id="comp-class"
              bind:value={filterClass}
              onchange={() => {
                if (filterSpec && specOf(filterSpec)?.wowClass !== filterClass) filterSpec = '';
              }}
            >
              <option value="">Every class</option>
              {#each CLASSES as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
            </select>
          </div>
          <div class="field">
            <label for="comp-spec">Spec</label>
            <select id="comp-spec" bind:value={filterSpec}>
              <option value="">Every spec</option>
              {#each CLASSES.filter((c) => !filterClass || c.id === filterClass) as c (c.id)}
                <optgroup label={c.name}>
                  {#each specsOfClass(c.id) as s (s.id)}<option value={s.id}>{s.name} {c.name}</option>{/each}
                </optgroup>
              {/each}
            </select>
          </div>
          <div class="seg roles" role="group" aria-label="Role">
            <button type="button" aria-pressed={filterRole === ''} onclick={() => (filterRole = '')}>All</button>
            {#each ROLES as r (r.id)}
              <button type="button" aria-pressed={filterRole === r.id} onclick={() => (filterRole = r.id)}>{r.label}</button>
            {/each}
          </div>
        </div>

        {#if poolError}
          <p class="err" role="alert">{poolError}</p>
        {:else if pool.length === 0}
          <p class="muted">
            Nobody is on {dayLabel(day)}'s roster yet. Members join it when they sign in to the hub with that night's
            Discord role.
          </p>
        {:else}
          <p class="hint" role="status">{shown.length} of {withSpecs.length} with specs set</p>
          <ul class="members">
            {#each shown as e (e.member_id)}
              <li>
                <button
                  type="button"
                  class="member"
                  class:seated={seated.has(e.member_id)}
                  style="--class: {classOf(e.wow_class)?.colour}"
                  draggable="true"
                  aria-pressed={same(picked, { kind: 'member', entry: e })}
                  ondragstart={(ev) => dragStart(ev, { kind: 'member', entry: e })}
                  ondragend={dragEnd}
                  onclick={() => pick({ kind: 'member', entry: e })}
                >
                  <span class="mname">{e.name}</span>
                  <span class="mspecs">
                    {specOf(e.primary)?.name}{#if e.secondary}<span class="sep"> / </span>{specOf(e.secondary)?.name}{/if}
                    {classOf(e.wow_class)?.name}
                  </span>
                  {#if seated.has(e.member_id)}<span class="pill">Seated</span>{/if}
                </button>
              </li>
            {:else}
              <li class="muted">Nobody on the roster matches.</li>
            {/each}
          </ul>
          {#if unset.length}
            <details class="unset">
              <summary>{unset.length} without specs yet</summary>
              <p class="hint">They can set them on the Me page.</p>
              <ul>{#each unset as e (e.member_id)}<li>{e.name}</li>{/each}</ul>
            </details>
          {/if}
        {/if}
      {/if}
    </aside>

    <div class="raid">
      <p class="placing" role="status" aria-live="polite">
        {#if picked}
          Placing <strong>{pickedLabel}</strong>: tap a seat{picked.kind === 'seat' ? ' to swap' : ''}, or press Escape.
          <button type="button" class="btn small" onclick={() => (picked = null)}>Cancel</button>
        {:else}
          {filled} of {size} seats filled
        {/if}
      </p>
      <div class="groups">
        {#each groups as g (g)}
          {@const buffs = groupBuffs(cover, g)}
          <section class="group card" aria-label="Group {g + 1}">
            <h2>Group {g + 1}</h2>
            <ol>
              {#each slots.slice(g * 5, g * 5 + 5) as seat, i (g * 5 + i)}
                {@const index = g * 5 + i}
                <li
                  class="seat"
                  class:filled={!!seat}
                  class:over={over === index}
                  class:moving={picked?.kind === 'seat' && picked.index === index}
                  style="--class: {colour(seat?.spec)}"
                  ondragover={(e) => dragOver(e, index)}
                  ondragleave={() => (over = over === index ? null : over)}
                  ondrop={(e) => drop(e, index)}
                >
                  <button
                    type="button"
                    class="seat-main"
                    class:has-toad={!!seat}
                    draggable={!!seat}
                    ondragstart={(e) => dragStart(e, { kind: 'seat', index })}
                    ondragend={dragEnd}
                    onclick={() => tapSeat(index)}
                  >
                    {#if seat}
                      <img src="{base}/logos/classes/{specOf(seat.spec)?.wowClass}.svg" alt="" width="28" height="25" />
                      <span class="sspec">{specLabel(seat.spec)}</span>
                      {#if seat.memberName}<span class="sname">{seat.memberName}</span>{/if}
                    {:else}
                      <span class="empty">Empty seat<span class="sr-only"> {index + 1}</span></span>
                    {/if}
                  </button>
                  {#if seat}
                    {#if seat.memberId && otherSpec(seat, pool)}
                      <button type="button" class="icon" title="Switch to {specOf(otherSpec(seat, pool))?.name}" onclick={() => switchSpec(index)}>
                        ⇄<span class="sr-only"> switch {seat.memberName} to {specOf(otherSpec(seat, pool))?.name}</span>
                      </button>
                    {/if}
                    <button type="button" class="icon" title="Remove" onclick={() => (slots = clear(slots, index))}>
                      ×<span class="sr-only"> remove {seatTitle(seat)}</span>
                    </button>
                  {/if}
                </li>
              {/each}
            </ol>
            {#if buffs.length}
              <ul class="gbuffs" aria-label="Group {g + 1} party buffs">
                {#each buffs as b (b.id)}<li>{b.name}</li>{/each}
              </ul>
            {/if}
          </section>
        {/each}
      </div>
    </div>

    <aside class="summary" aria-label="What this comp brings">
      <section class="card">
        <h2>Roles</h2>
        <dl class="roles-dl">
          {#each ROLES as r (r.id)}<div><dt>{r.label}</dt><dd>{roles[r.id]}</dd></div>{/each}
        </dl>
        {#if classes.length}
          <ul class="ccount">
            {#each classes as c (c.wowClass.id)}
              <li style="--class: {c.wowClass.colour}"><span class="dot" aria-hidden="true"></span>{c.wowClass.name} {c.count}</li>
            {/each}
          </ul>
        {/if}
      </section>

      {#each SCOPES as scope (scope.id)}
        {@const rows = byScope(scope.id)}
        <section class="card buffs">
          <h2>{scope.title} <span class="hint">{rows.filter((r) => r.seats.length).length} of {rows.length}</span></h2>
          <ul>
            {#each rows as c (c.buff.id)}
              <li class:missing={!c.seats.length}>
                <span class="bname">{c.buff.name}</span>
                <span class="bcat">{CATEGORY_LABEL[c.buff.category]}</span>
                <span class="bwho">{c.seats.length ? whoBrings(c) : `Needs ${couldBring(c)}`}</span>
                {#if c.buff.note && c.seats.length}<span class="bnote">{c.buff.note}</span>{/if}
              </li>
            {/each}
          </ul>
        </section>
      {/each}
    </aside>
  </div>

  <section class="card saved" aria-labelledby="saved-h">
    <h2 id="saved-h">Lock in for {dayLabel(day)}</h2>
    <form
      class="save"
      onsubmit={(e) => {
        e.preventDefault();
        save(false);
      }}
    >
      <div class="field">
        <label for="comp-name">Comp name</label>
        <input id="comp-name" maxlength="80" placeholder="Molten Core, week 1" bind:value={name} required />
      </div>
      <button class="btn primary" type="submit" disabled={busy || !name.trim()}>{current ? `Save ${current.name}` : 'Lock in'}</button>
      {#if current}
        <button class="btn" type="button" disabled={busy || !name.trim()} onclick={() => save(true)}>Save as new</button>
      {/if}
      <button class="btn" type="button" disabled={busy} onclick={startNew}>Start over</button>
    </form>
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
    {#if saved.length}
      <ul class="list">
        {#each saved as c (c.id)}
          <li class:current={current?.id === c.id}>
            <div>
              <strong>{c.name}</strong>
              <span class="hint">{c.size}-player · {c.slots.filter(Boolean).length} seated{c.updated_by ? ` · ${c.updated_by}` : ''}</span>
            </div>
            <button class="btn small" type="button" disabled={busy} onclick={() => load(c)}>Open<span class="sr-only"> {c.name}</span></button>
            <button class="btn small danger" type="button" disabled={busy} onclick={() => remove(c)}>Delete<span class="sr-only"> {c.name}</span></button>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="muted">No comps locked in for {dayLabel(day)} yet.</p>
    {/if}
  </section>
</section>

<style>
  .builder { display: grid; gap: 1rem; }
  .top { display: flex; flex-wrap: wrap; align-items: end; justify-content: space-between; gap: 0.75rem 1.5rem; }
  .top h1 { margin: 0; }
  .controls { display: flex; flex-wrap: wrap; align-items: end; gap: 0.75rem; }
  .lede { margin: 0; max-width: 72ch; }
  h2 { margin: 0 0 0.5rem; font-size: 1rem; }

  .seg { display: inline-flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
  .seg button {
    background: var(--bg);
    color: var(--text);
    border: 0;
    border-right: 1px solid var(--line);
    padding: 0.4rem 0.75rem;
    font: inherit;
    font-size: 0.9rem;
    cursor: pointer;
  }
  .seg button:last-child { border-right: 0; }
  .seg button[aria-pressed='true'] { background: color-mix(in srgb, var(--accent) 22%, var(--bg)); font-weight: 600; }
  .seg.roles { flex-wrap: wrap; }

  .layout { display: grid; gap: 1rem; grid-template-columns: minmax(0, 1fr); align-items: start; }
  @media (min-width: 60rem) { .layout { grid-template-columns: 16rem minmax(0, 1fr); } .summary { grid-column: 1 / -1; } }
  @media (min-width: 88rem) { .layout { grid-template-columns: 16rem minmax(0, 1fr) 20rem; } .summary { grid-column: auto; } }

  .palette { display: grid; gap: 0.75rem; align-content: start; }
  @media (min-width: 60rem) { .palette { position: sticky; top: 1rem; max-height: calc(100vh - 2rem); overflow-y: auto; } }
  .classes, .members, .unset ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; }
  .classes li { display: grid; grid-template-columns: 2rem minmax(0, 1fr); gap: 0.15rem 0.5rem; align-items: center; }
  .classes img { width: 2rem; height: auto; grid-row: span 2; }
  .cname { color: var(--class); font-weight: 600; font-size: 0.9rem; }
  .specs { display: flex; flex-wrap: wrap; gap: 0.3rem; }
  .spec, .member {
    font: inherit;
    color: var(--text);
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: 6px;
    cursor: grab;
    touch-action: manipulation;
  }
  .spec { padding: 0.25rem 0.5rem; font-size: 0.82rem; }
  .spec:hover, .member:hover { border-color: var(--muted); }
  .mname::before {
    content: '';
    display: inline-block;
    width: 0.55rem;
    height: 0.55rem;
    border-radius: 50%;
    background: var(--class);
    margin-right: 0.4rem;
  }
  .spec[aria-pressed='true'], .member[aria-pressed='true'] {
    background: color-mix(in srgb, var(--class) 22%, var(--bg));
    border-color: var(--class);
  }
  .filters { display: grid; gap: 0.5rem; }
  .member { width: 100%; text-align: left; padding: 0.4rem 0.55rem; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 0 0.5rem; }
  .member.seated { opacity: 0.6; }
  .mname { font-weight: 600; }
  .mspecs { grid-column: 1; font-size: 0.8rem; color: var(--muted); }
  .member .pill { grid-row: 1 / span 2; grid-column: 2; align-self: center; }
  .unset summary { cursor: pointer; color: var(--muted); font-size: 0.9rem; }
  .unset ul { gap: 0.2rem; font-size: 0.9rem; }

  .placing { margin: 0 0 0.5rem; min-height: 2rem; display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; color: var(--muted); }
  .groups { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr)); }
  .group { padding: 0.75rem; }
  .group ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.3rem; }
  .seat {
    display: flex;
    align-items: stretch;
    min-height: 2.6rem;
    border: 1px dashed var(--line);
    border-radius: 6px;
    background: var(--bg);
    transition: border-color 120ms ease-out, background-color 120ms ease-out;
  }
  .seat.filled { border-style: solid; border-color: color-mix(in srgb, var(--class) 45%, var(--line)); background: color-mix(in srgb, var(--class) 9%, var(--bg)); }
  .seat-main.has-toad { grid-template-columns: 1.75rem minmax(0, 1fr); column-gap: 0.45rem; }
  .seat-main img { grid-row: span 2; width: 1.75rem; height: auto; align-self: center; }
  .seat.over { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 16%, var(--bg)); }
  .seat.moving { outline: 2px solid var(--accent); outline-offset: 1px; }
  .seat-main {
    flex: 1;
    min-width: 0;
    display: grid;
    align-content: center;
    text-align: left;
    padding: 0.25rem 0.5rem;
    background: none;
    border: 0;
    color: var(--text);
    font: inherit;
    cursor: pointer;
  }
  .seat.filled .seat-main { cursor: grab; }
  .sspec { font-size: 0.88rem; font-weight: 600; }
  .sname { font-size: 0.8rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .empty { font-size: 0.82rem; color: var(--muted); }
  .icon {
    background: none;
    border: 0;
    color: var(--muted);
    font-size: 1.05rem;
    width: 2.25rem;
    cursor: pointer;
    border-radius: 6px;
  }
  .icon:hover { color: var(--text); background: color-mix(in srgb, var(--text) 8%, transparent); }
  .gbuffs { list-style: none; margin: 0.5rem 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.25rem; }
  .gbuffs li { font-size: 0.72rem; padding: 0.1rem 0.4rem; border-radius: 999px; background: var(--line); }

  .summary { display: grid; gap: 0.75rem; align-content: start; }
  @media (min-width: 60rem) and (max-width: 87.99rem) { .summary { grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); } }
  .roles-dl { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; margin: 0; }
  .roles-dl div { display: grid; }
  .roles-dl dt { font-size: 0.78rem; color: var(--muted); }
  .roles-dl dd { margin: 0; font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; }
  .ccount { list-style: none; margin: 0.75rem 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.3rem 0.75rem; font-size: 0.85rem; }
  .dot { display: inline-block; width: 0.55rem; height: 0.55rem; border-radius: 50%; background: var(--class); margin-right: 0.3rem; }
  .buffs ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.45rem; }
  .buffs li { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 0 0.5rem; font-size: 0.85rem; }
  .bname { font-weight: 600; }
  .bcat { font-size: 0.72rem; color: var(--muted); }
  .bwho, .bnote { grid-column: 1 / -1; font-size: 0.78rem; color: var(--accent); }
  .bnote { color: var(--warn); }
  .buffs li.missing .bname { color: var(--muted); font-weight: 500; }
  .buffs li.missing .bwho { color: var(--muted); }

  .saved { display: grid; gap: 0.75rem; }
  .saved h2 { margin: 0; }
  .save { display: flex; flex-wrap: wrap; align-items: end; gap: 0.6rem; }
  .save .field { flex: 1 1 14rem; max-width: 24rem; }
  .list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.4rem; }
  .list li { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; padding: 0.45rem 0.6rem; border: 1px solid var(--line); border-radius: 6px; }
  .list li div { flex: 1 1 12rem; display: grid; }
  .list li.current { border-color: var(--accent); }
  .btn.small { padding: 0.2rem 0.55rem; font-size: 0.82rem; }
  @media (prefers-reduced-motion: reduce) { .seat { transition: none; } }
</style>
