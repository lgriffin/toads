<script lang="ts">
  import {
    NOTE_LIMIT,
    absenceError,
    dayName,
    isoDate,
    monthGrid,
    nightLabel,
    rangeLabel,
    weekdayOf,
    type Absence,
    type AbsencesBackend,
    type RaidDays
  } from '$lib/absences';

  // A member's calendar: their teams' raid nights month by month, the nights they have said they will miss, and the
  // form to add one. The API checks the member is on the team they report for.
  let { backend, raidDays }: { backend: AbsencesBackend; raidDays: RaidDays } = $props();

  const today = isoDate(new Date());
  const now = new Date();
  // This month and the next eleven: absences are booked up to a year ahead.
  let offset = $state(0);
  const shown = $derived(new Date(now.getFullYear(), now.getMonth() + offset, 1));
  const monthName = $derived(shown.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' }));

  let mine = $state<Absence[]>([]);
  let loadError = $state('');
  let team = $state('');
  let first = $state(today);
  let last = $state(today);
  let note = $state('');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);
  let firstInput = $state<HTMLInputElement | null>(null);

  const teams = $derived(raidDays.teams.map((id) => ({ id, name: dayName(id, raidDays.names), weekday: weekdayOf(dayName(id, raidDays.names)) })));
  const weeks = $derived(monthGrid(shown.getFullYear(), shown.getMonth(), today, teams, mine));
  const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  // The form opens on the next raid night of the member's first team, so a single night is one click away.
  $effect(() => {
    if (team || !teams.length) return;
    team = teams[0].id;
    const next = nextNight(teams[0].weekday);
    first = next;
    last = next;
  });

  function nextNight(weekday: number | null): string {
    if (weekday === null) return today;
    return isoDate(new Date(now.getFullYear(), now.getMonth(), now.getDate() + ((weekday - now.getDay() + 7) % 7)));
  }

  async function load() {
    try {
      mine = await backend.mine();
      loadError = '';
    } catch (e) {
      loadError = absenceError(e);
    }
  }
  $effect(() => {
    load();
  });

  function pick(date: string, raid: string) {
    team = raid;
    first = date;
    last = date;
    message = '';
    firstInput?.focus();
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!team) return;
    busy = true;
    try {
      const a = await backend.report(team, {
        first_date: first,
        ...(last && last !== first ? { last_date: last } : {}),
        ...(note.trim() ? { note: note.trim() } : {})
      });
      const n = a.nights.length;
      message = `Done. ${dayName(a.raid_day, raidDays.names)}'s officers can see you will miss ${n === 1 ? 'that night' : `${n} nights`}.`;
      failed = false;
      note = '';
      await load();
    } catch (e) {
      message = absenceError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }

  async function cancel(a: Absence) {
    try {
      await backend.cancel(a.id);
      message = `Cancelled your absence for ${rangeLabel(a)}.`;
      failed = false;
      await load();
    } catch (e) {
      message = absenceError(e);
      failed = true;
    }
  }

  function cellLabel(d: (typeof weeks)[number][number]): string {
    const parts = [nightLabel(d.date)];
    if (d.raids.length) parts.push(`${d.raids.map((r) => dayName(r, raidDays.names)).join(' and ')} raid`);
    if (d.away.length) parts.push('you are away');
    return parts.join(', ');
  }
</script>

{#if !teams.length}
  <section class="card empty" aria-labelledby="noteam-h">
    <h2 id="noteam-h">No raid team yet</h2>
    <p>
      Absences are for the raid teams you are on. Once the officers give you a raid night's role in Discord, its nights
      show here and you can tell them when you cannot make it.
    </p>
  </section>
{:else}
  <div class="layout">
    <section class="month card" aria-labelledby="month-h">
      <div class="month-head">
        <button class="btn" type="button" onclick={() => (offset -= 1)} disabled={offset === 0} aria-label="Previous month">‹</button>
        <h2 id="month-h" aria-live="polite">{monthName}</h2>
        <button class="btn" type="button" onclick={() => (offset += 1)} disabled={offset >= 11} aria-label="Next month">›</button>
      </div>
      <table class="grid-month">
        <thead>
          <tr>{#each WEEKDAYS as w}<th scope="col">{w}</th>{/each}</tr>
        </thead>
        <tbody>
          {#each weeks as week, i (i)}
            <tr>
              {#each week as d (d.date)}
                <td class:out={!d.inMonth} class:past={d.past} class:raid={d.inMonth && d.raids.length > 0} class:away={d.inMonth && d.away.length > 0} class:today={d.date === today}>
                  {#if !d.inMonth}
                    <span class="cell" aria-hidden="true"></span>
                  {:else if d.raids.length && !d.past}
                    <button type="button" class="cell" aria-label="{cellLabel(d)}. Report an absence" onclick={() => pick(d.date, d.raids[0])}>
                      <span class="num">{d.day}</span>
                      <span class="tag">{d.away.length ? 'Away' : d.raids.map((r) => dayName(r, raidDays.names).slice(0, 3)).join(' ')}</span>
                    </button>
                  {:else}
                    <span class="cell" aria-label={cellLabel(d)}>
                      <span class="num">{d.day}</span>
                      {#if d.raids.length}<span class="tag">{d.away.length ? 'Away' : dayName(d.raids[0], raidDays.names).slice(0, 3)}</span>{/if}
                    </span>
                  {/if}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
      <p class="hint key">
        <span><span class="swatch raid"></span> your raid nights</span>
        <span><span class="swatch away"></span> nights you will miss</span>
        <span>Pick a raid night to report it.</span>
      </p>
    </section>

    <form class="card report" onsubmit={submit} aria-labelledby="report-h">
      <h2 id="report-h">Can't make it?</h2>
      <p class="muted">Tell your officers in one go, for one night or a holiday.</p>
      {#if teams.length > 1}
        <div class="field">
          <label for="abs-team">Raid team</label>
          <select id="abs-team" bind:value={team}>
            {#each teams as t (t.id)}<option value={t.id}>{t.name}</option>{/each}
          </select>
        </div>
      {:else}
        <p class="team">Raid team: <strong>{teams[0].name}</strong></p>
      {/if}
      <div class="dates">
        <div class="field">
          <label for="abs-first">From</label>
          <input id="abs-first" type="date" min={today} bind:value={first} bind:this={firstInput} required />
        </div>
        <div class="field">
          <label for="abs-last">To</label>
          <input id="abs-last" type="date" min={first || today} bind:value={last} />
        </div>
      </div>
      <div class="field">
        <label for="abs-note">Note for the officers <span class="hint">(optional)</span></label>
        <textarea id="abs-note" rows="2" maxlength={NOTE_LIMIT} bind:value={note} placeholder="Working late, on holiday…"></textarea>
      </div>
      <button class="btn primary" type="submit" disabled={busy || !first}>{busy ? 'Saving…' : 'Report absence'}</button>
      {#if message}<p class={failed ? 'err' : 'ok'} role={failed ? 'alert' : 'status'}>{message}</p>{/if}
    </form>
  </div>

  <section class="card" aria-labelledby="mine-h">
    <h2 id="mine-h">Your upcoming absences</h2>
    {#if loadError}
      <p class="err" role="alert">{loadError}</p>
    {:else if !mine.length}
      <p class="muted">None. Your officers expect you on every raid night.</p>
    {:else}
      <ul class="mine">
        {#each mine as a (a.id)}
          <li>
            <div>
              <strong>{dayName(a.raid_day, raidDays.names)}</strong> · {rangeLabel(a)}
              <span class="muted">({a.nights.length} {a.nights.length === 1 ? 'raid night' : 'raid nights'})</span>
              {#if a.note}<span class="note">{a.note}</span>{/if}
            </div>
            <button class="btn danger" type="button" onclick={() => cancel(a)} aria-label="Cancel your absence for {rangeLabel(a)}">Cancel</button>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
{/if}

<style>
  .layout { display: grid; gap: 1rem; grid-template-columns: minmax(0, 1fr); }
  @media (min-width: 56rem) { .layout { grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); align-items: start; } }
  .card { display: grid; gap: 0.75rem; }
  .layout + .card { margin-top: 1rem; }
  .empty { max-width: 40rem; }
  .month-head { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 0.5rem; }
  .month-head h2 { text-align: center; }
  .month-head .btn { padding: 0.25rem 0.7rem; font-size: 1.2rem; line-height: 1; }
  .grid-month { table-layout: fixed; }
  .grid-month th { text-align: center; font-size: 0.8rem; padding: 0.3rem 0; }
  .grid-month td { padding: 2px; border: 0; text-align: center; vertical-align: top; }
  .cell {
    display: grid;
    justify-items: center;
    gap: 0.1rem;
    width: 100%;
    min-height: 3.1rem;
    padding: 0.35rem 0.1rem;
    border-radius: 6px;
    border: 1px solid transparent;
    background: none;
    color: inherit;
    font: inherit;
    box-sizing: border-box;
  }
  button.cell { cursor: pointer; }
  .num { font-variant-numeric: tabular-nums; }
  .tag { font-size: 0.7rem; letter-spacing: 0.04em; text-transform: uppercase; }
  .past .num, .past .tag { color: var(--muted); }
  .past.raid .cell { background: none; border-style: dashed; }
  .today .num { color: var(--teal); font-weight: 700; }
  .raid .cell { background: rgb(217 168 90 / 0.14); border-color: rgb(217 168 90 / 0.45); }
  .raid .tag { color: var(--bronze-hi); }
  .away .cell { background: rgb(224 106 95 / 0.16); border-color: rgb(224 106 95 / 0.6); }
  .away .tag { color: #f0a39c; }
  button.cell:hover { border-color: var(--teal); }
  .key { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem 1rem; margin: 0; }
  .key > span { display: inline-flex; align-items: center; gap: 0.35rem; }
  .swatch { display: inline-block; width: 0.8rem; height: 0.8rem; border-radius: 3px; }
  .swatch.raid { background: rgb(217 168 90 / 0.45); }
  .swatch.away { background: rgb(224 106 95 / 0.6); }
  .card h2 { margin: 0; font-family: 'Cinzel', Georgia, serif; font-weight: 600; color: var(--bronze-hi); letter-spacing: 0.03em; }
  .report p { margin: 0; }
  .dates { display: grid; gap: 0.75rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .report .btn { justify-self: start; }
  .mine { list-style: none; margin: 0; padding: 0; }
  .mine li {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem 1rem;
    padding: 0.6rem 0;
    border-top: 1px solid var(--line);
  }
  .note { display: block; color: var(--muted); font-size: 0.92em; }
</style>
