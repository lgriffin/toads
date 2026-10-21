<script lang="ts">
  import { scrollable } from '$lib/scrollable';
  import { myRaidLine, placeLabel, ROLE_NAMES, vsMedian, type MyCharacterPage, type MyRaidLine } from '$lib/characters';
  import { base } from '$app/paths';
  import { compactNumber, durationLabel } from '$lib/reference';
  import {
    RAID_TABS,
    logsError,
    perSecond,
    raidDateLabel,
    raidLength,
    tabsFor,
    weekdayName,
    type LogsBackend,
    type RaidTab,
    type RaidView
  } from '$lib/logs';

  // One raid's analysis, a section per tab of the desktop raid view. Officers of the raid's night (and global
  // officers) get every section; everyone else gets the raid's shape and each boss's totals (docs/logs.md).
  let {
    backend,
    report,
    day,
    mine = null
  }: {
    backend: LogsBackend;
    report: string;
    day: string | null;
    /** The signed-in member's character pages, for their own line on this raid; null leaves it out. */
    mine?: ((name: string | null) => Promise<MyCharacterPage>) | null;
  } = $props();

  let line = $state<MyRaidLine | null>(null);
  $effect(() => {
    if (!mine) return;
    // Best effort: without the member's pages the log still reads, just without their own line.
    myRaidLine(report, mine).then(
      (l) => (line = l),
      () => (line = null)
    );
  });
  const lineVs = $derived(line ? vsMedian(line.raid) : null);

  let view = $state<RaidView | null>(null);
  let error = $state('');
  let picked = $state<RaidTab>('encounters');

  $effect(() => {
    backend.raid(report, day).then(
      (v) => (view = v),
      (e) => (error = logsError(e))
    );
  });

  const tabs = $derived(view?.full ? tabsFor(view.page) : []);
  const tab = $derived(tabs.includes(picked) ? picked : (tabs[0] ?? 'encounters'));
  const label = (id: RaidTab) => RAID_TABS.find((t) => t.id === id)?.label ?? id;
  const ROLES = ['tanks', 'healers', 'melee', 'ranged'] as const;
  const pct = (n: number | null | undefined) => (n === null || n === undefined ? '—' : `${n.toFixed(1)}%`);
</script>

{#if error}
  <p class="card bad" role="alert">{error}</p>
{:else if !view}
  <p class="muted" role="status">Loading…</p>
{:else}
  {@const s = view.page.summary}
  <header class="head">
    <h1>{s.title}</h1>
    <p class="muted">
      {raidDateLabel(s)} · {weekdayName(s.weekday)} · {s.zone} · {s.size} raiders · {raidLength(view.page.duration_ms)} ·
      <a href={s.url} rel="external noopener">Warcraft Logs</a>
    </p>
  </header>

  {#if line}
    {@const r = line.raid}
    <section class="card you" aria-labelledby="you-h">
      <h2 id="you-h">You in this raid</h2>
      <p>
        <strong>{line.name}</strong>, {ROLE_NAMES[r.role].toLowerCase()}: {r.display} {r.metric.toLowerCase()}{#if lineVs}, <span
            class:ok={lineVs.better}
            class:bad={!lineVs.better}>{lineVs.label}</span
          > against the median for the role ({r.median_display}){/if}{#if placeLabel(r)}, {placeLabel(r)}{/if}.
        <a href="{base}/me{__PREVIEW__ ? '/' : ''}">Every raid on Me</a>
      </p>
    </section>
  {/if}

  {#if !view.full}
    <section class="card">
      <h2>Raid makeup</h2>
      <div class="roles">
        {#each ROLES as role (role)}
          <div><span class="n">{view.page.composition_counts[role]}</span><span class="muted">{role}</span></div>
        {/each}
      </div>
    </section>
    <section class="card">
      <h2>Encounters</h2>
      {@render encounterTable(view.page.encounters)}
      <p class="muted small">
        Each raider's numbers are for this night's officers. Yours, against the median for your role, are on
        <a href="{base}/me">your Me page</a>.
      </p>
    </section>
  {:else}
    {@const p = view.page}
    {#if p.warnings?.length}
      <ul class="card warn">{#each p.warnings as w (w)}<li>{w}</li>{/each}</ul>
    {/if}
    <div class="tabs" role="group" aria-label="Analysis">
      {#each tabs as id (id)}
        <button type="button" aria-pressed={tab === id} onclick={() => (picked = id)}>{label(id)}</button>
      {/each}
    </div>

    <section class="card" aria-labelledby="tab-h">
      <h2 id="tab-h">{label(tab)}</h2>
      <div class="scroll" use:scrollable>
        {#if tab === 'encounters'}
          {@render encounterTable(p.encounters)}
          {#each p.encounters as e (e.encounter_id)}
            <details>
              <summary>{e.name}: every raider</summary>
              <table>
                <thead><tr><th scope="col">Raider</th><th scope="col">Role</th><th scope="col" class="num">DPS</th><th scope="col" class="num">HPS</th><th scope="col" class="num">Damage taken</th><th scope="col" class="num">Active</th></tr></thead>
                <tbody>
                  {#each e.players ?? [] as pl (pl.name)}
                    <tr><th scope="row">{pl.name} <span class="muted small">{pl.player_class}</span></th><td>{pl.role}</td><td class="num">{compactNumber(perSecond(pl.damage, e.duration_ms))}</td><td class="num">{compactNumber(perSecond(pl.healing, e.duration_ms))}</td><td class="num">{compactNumber(pl.damage_taken)}</td><td class="num">{pct(pl.active_percent)}</td></tr>
                  {/each}
                </tbody>
              </table>
            </details>
          {/each}
        {:else if tab === 'composition'}
          <div class="comp">
            {#each ROLES as role (role)}
              <div>
                <h3>{role} <span class="muted">({p.composition[role]?.length ?? 0})</span></h3>
                <ul>{#each p.composition[role] ?? [] as pl (pl.name)}<li>{pl.name} <span class="muted small">{pl.player_class}</span></li>{/each}</ul>
              </div>
            {/each}
          </div>
        {:else if tab === 'healers'}
          <table>
            <thead><tr><th scope="col">Healer</th><th scope="col" class="num">Healing</th><th scope="col" class="num">Overhealing</th><th scope="col" class="num">Overheal</th><th scope="col" class="num">Dispels</th><th scope="col" class="num">Active</th></tr></thead>
            <tbody>
              {#each p.healers as h (h.name)}
                <tr><th scope="row">{h.name} <span class="muted small">{h.player_class}</span></th><td class="num">{compactNumber(h.healing)}</td><td class="num">{compactNumber(h.overhealing)}</td><td class="num">{pct(h.overheal_percent)}</td><td class="num">{h.dispels}</td><td class="num">{pct(h.active_percent)}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else if tab === 'tanks'}
          <table>
            <thead><tr><th scope="col">Tank</th><th scope="col" class="num">Damage taken</th><th scope="col" class="num">Mitigated</th><th scope="col" class="num">Mitigation</th><th scope="col" class="num">Active</th></tr></thead>
            <tbody>
              {#each p.tanks as t (t.name)}
                <tr><th scope="row">{t.name} <span class="muted small">{t.player_class}</span></th><td class="num">{compactNumber(t.damage_taken)}</td><td class="num">{compactNumber(t.mitigated)}</td><td class="num">{pct(t.mitigation_percent)}</td><td class="num">{pct(t.active_percent)}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else if tab === 'melee' || tab === 'ranged'}
          <table>
            <thead><tr><th scope="col">Raider</th><th scope="col" class="num">Damage</th><th scope="col" class="num">Active</th></tr></thead>
            <tbody>
              {#each p[tab] as d (d.name)}
                <tr><th scope="row">{d.name} <span class="muted small">{d.player_class}</span></th><td class="num">{compactNumber(d.damage)}</td><td class="num">{pct(d.active_percent)}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else if tab === 'consumables'}
          <table>
            <thead><tr><th scope="col">Raider</th><th scope="col">Role</th>{#each p.consumable_names as c (c)}<th scope="col" class="num">{c}</th>{/each}</tr></thead>
            <tbody>
              {#each p.consumables as row (row.name)}
                <tr><th scope="row">{row.name}</th><td>{row.role}</td>{#each p.consumable_names as c (c)}<td class="num">{row.counts[c] ?? 0}</td>{/each}</tr>
              {/each}
            </tbody>
          </table>
        {:else if tab === 'boss_vs_trash'}
          <table>
            <thead><tr><th scope="col">Consumable</th><th scope="col" class="num">On bosses</th><th scope="col" class="num">On trash</th></tr></thead>
            <tbody>
              {#each p.boss_vs_trash as c (c.name)}
                <tr><th scope="row">{c.name}</th><td class="num">{c.boss}</td><td class="num">{c.trash}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else if tab === 'interrupts'}
          <table>
            <thead><tr><th scope="col">Raider</th><th scope="col">Spell</th><th scope="col" class="num">Interrupts</th></tr></thead>
            <tbody>
              {#each p.interrupts as i, n (n)}
                <tr><th scope="row">{i.name} <span class="muted small">{i.player_class}</span></th><td>{i.spell_name}</td><td class="num">{i.count}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else if tab === 'cancelled_casts'}
          <table>
            <thead><tr><th scope="col">Raider</th><th scope="col" class="num">Casts</th><th scope="col" class="num">Cancelled</th><th scope="col" class="num">Cancel rate</th></tr></thead>
            <tbody>
              {#each p.cancelled_casts as c (c.name)}
                <tr><th scope="row">{c.name} <span class="muted small">{c.player_class}</span></th><td class="num">{c.total_casts}</td><td class="num">{c.cancelled_casts}</td><td class="num">{pct(c.cancel_rate)}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else if tab === 'debuff_uptimes' || tab === 'totem_uptimes'}
          <table>
            <thead><tr><th scope="col">Spell</th><th scope="col">Fight</th><th scope="col" class="num">Uptime</th></tr></thead>
            <tbody>
              {#each p[tab] as u, n (n)}
                <tr><th scope="row">{u.spell_name}</th><td>{u.fight_name}</td><td class="num">{pct(u.uptime_percent)}</td></tr>
              {/each}
            </tbody>
          </table>
        {:else if tab === 'engineering'}
          <table>
            <thead><tr><th scope="col">Item</th><th scope="col" class="num">Users</th><th scope="col" class="num">Casts</th><th scope="col" class="num">Damage</th><th scope="col" class="num">Per cast (low / median / high)</th></tr></thead>
            <tbody>
              {#each p.engineering as e (e.name)}
                <tr><th scope="row">{e.name}</th><td class="num">{e.users}</td><td class="num">{e.total_casts}</td><td class="num">{compactNumber(e.total_damage)}</td><td class="num">{compactNumber(e.min_avg)} / {compactNumber(e.median_avg)} / {compactNumber(e.max_avg)}</td></tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </section>
  {/if}
{/if}

{#snippet encounterTable(encounters: import('$lib/logs').Encounter[])}
  {#if encounters.length}
    <table>
      <thead><tr><th scope="col">Boss</th><th scope="col" class="num">Kill time</th><th scope="col" class="num">Raid DPS</th><th scope="col" class="num">Raid HPS</th></tr></thead>
      <tbody>
        {#each encounters as e (e.encounter_id)}
          <tr><th scope="row">{e.name}</th><td class="num">{durationLabel(e.duration_ms)}</td><td class="num">{compactNumber(perSecond(e.damage, e.duration_ms))}</td><td class="num">{compactNumber(perSecond(e.healing, e.duration_ms))}</td></tr>
        {/each}
      </tbody>
    </table>
  {:else}
    <p class="muted">No boss kills in this raid.</p>
  {/if}
{/snippet}

<style>
  .you { border-color: color-mix(in srgb, var(--bronze) 45%, var(--line)); margin-bottom: 1rem; }
  .you p { margin: 0; }
  .head h1 { margin-bottom: 0.25rem; }
  .head p { margin-top: 0; }
  section + section, .tabs + section { margin-top: 1rem; }
  h2 { margin: 0 0 0.5rem; }
  h3 { margin: 0 0 0.35rem; font-size: 1rem; text-transform: capitalize; }
  .small { font-size: 0.85rem; }
  .roles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.5rem; text-align: center; }
  .roles div { display: flex; flex-direction: column; text-transform: capitalize; }
  .n { font-size: 1.6rem; font-variant-numeric: tabular-nums; }
  .comp { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 1rem; }
  .comp ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.2rem; }
  .tabs { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 1rem 0 0; }
  .tabs button {
    font: inherit;
    min-height: 2.5rem;
    padding: 0.35rem 0.85rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: color-mix(in srgb, var(--ink) 45%, transparent);
    color: var(--cream);
    cursor: pointer;
  }
  .tabs button[aria-pressed='true'] { background: var(--bronze); border-color: var(--bronze); color: var(--on-bronze); font-weight: 700; }
  .tabs button:hover:not([aria-pressed='true']) { background: color-mix(in srgb, var(--teal) 18%, transparent); }
  .tabs button:focus-visible { outline: 2px solid var(--bronze-hi); outline-offset: 2px; }
  details { margin-top: 0.5rem; }
  summary { cursor: pointer; padding: 0.4rem 0; }
  summary:focus-visible { outline: 2px solid var(--bronze-hi); outline-offset: 2px; }
  .warn { margin: 1rem 0 0; padding-left: 2rem; }
</style>
