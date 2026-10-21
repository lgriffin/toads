<script lang="ts">
  import { base } from '$app/paths';
  import type { Snippet } from 'svelte';
  import { characterLabel } from '$lib/main-swap';
  import {
    placeLabel,
    rolesLabel,
    showTrends,
    spreadValue,
    vsMedian,
    MIN_TREND_RAIDS,
    ROLE_NAMES,
    type MyCharacterPage,
    type Spread
  } from '$lib/characters';
  import PayloadChart from '$lib/components/PayloadChart.svelte';

  // The member's own raids, as the analyzer's character profile shows them (GET /api/me/character-page): each raid's
  // headline number against the median for the same role in that raid (REQ-HUB-ME-002), a chart per role once there
  // are enough raids (REQ-HUB-ME-004), personal bests and the character's lineage. It opens on the member's main;
  // `pick` switches to another of their characters from one dropdown (REQ-HUB-ME-006), and `main` (the main swap)
  // sits under it.
  let { mine, pick, main }: { mine: MyCharacterPage; pick?: (name: string) => void; main?: Snippet<[string]> } =
    $props();

  const page = $derived(mine.page);
  // The preview prerenders pages with trailing slashes.
  const slash = __PREVIEW__ ? '/' : '';
  const raidHref = (id: string) => `${base}/logs/${encodeURIComponent(id)}/`;
  const spreads = (list: Spread[]) => list.filter((s) => s.raids > 0);
</script>

<section class="card" aria-labelledby="character-h">
  <h2 id="character-h">Your raids</h2>
  {#if page}
    {#if mine.characters.length > 1 && pick}
      <div class="chars">
        <label for="character-pick">Character</label>
        <select id="character-pick" value={page.name} onchange={(e) => {
            pick?.(e.currentTarget.value);
            // The dropdown follows the page shown, so a switch that fails leaves both on the old character.
            e.currentTarget.value = page.name;
          }}>
          {#each mine.characters as c (c)}
            <option value={c}>{characterLabel(c, mine.main ?? null)}</option>
          {/each}
        </select>
      </div>
    {/if}
    {@render main?.(page.name)}
    <p class="muted sub">
      {page.name}, {page.player_class}: {page.raids} guild {page.raids === 1 ? 'raid' : 'raids'}{#if page.first_raid}{` since ${page.first_raid.slice(0, 10)}`}{/if}. {rolesLabel(page.role_counts)}
    </p>

    {#if showTrends(page)}
      {#each page.charts as chart (chart.id)}
        <PayloadChart {chart} />
      {/each}
    {:else}
      <p class="muted" role="status">
        Building your history. Trends show after {MIN_TREND_RAIDS} guild raids; {page.name} has {page.raids}.
      </p>
    {/if}

    {#if page.bests.length}
      <h3>Personal bests</h3>
      <ul class="bests">
        {#each page.bests as b (b.role)}
          <li>
            <strong>{b.display}</strong>
            <span class="muted small">{b.metric} as {ROLE_NAMES[b.role as keyof typeof ROLE_NAMES]?.toLowerCase() ?? b.role}</span>
            <a class="small" href={raidHref(b.report_id)}>{b.raid_date.slice(0, 10)}</a>
          </li>
        {/each}
      </ul>
    {/if}

    <h3>Raid by raid</h3>
    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">Raid</th>
            <th scope="col">Role</th>
            <th scope="col" class="num">You</th>
            <th scope="col" class="num">Role median</th>
            <th scope="col" class="num">Against it</th>
            <th scope="col" class="num">Place</th>
          </tr>
        </thead>
        <tbody>
          {#each page.recent as r (r.report_id)}
            {@const diff = vsMedian(r)}
            <tr>
              <td>
                <a href={raidHref(r.report_id)}>{r.title || r.zone}</a>
                <span class="muted small">{r.raid_date.slice(0, 10)}</span>
              </td>
              <td>{ROLE_NAMES[r.role]}</td>
              <td class="num">
                {r.display}
                <span class="muted small">{r.metric.toLowerCase()}</span>
                {#if r.percent !== null}<span class="muted small">{r.percent.toFixed(1)}% {r.role === 'tank' ? 'mitigated' : 'overheal'}</span>{/if}
              </td>
              <td class="num muted">{r.median_display}</td>
              <td class="num">{#if diff}<span class:ok={diff.better} class:bad={!diff.better}>{diff.label}</span>{/if}</td>
              <td class="num">{placeLabel(r)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if spreads(page.metrics).length}
      <h3>Across your raids</h3>
      <div class="scroll">
        <table>
          <thead><tr><th scope="col">Number</th><th scope="col" class="num">Lowest</th><th scope="col" class="num">Average</th><th scope="col" class="num">Highest</th></tr></thead>
          <tbody>
            {#each spreads(page.metrics) as s (s.name + s.role)}
              <tr>
                <td>{s.name}{#if s.role} <span class="muted small">as {ROLE_NAMES[s.role as keyof typeof ROLE_NAMES]?.toLowerCase() ?? s.role}</span>{/if}</td>
                <td class="num">{spreadValue(s, s.min)}</td>
                <td class="num">{spreadValue(s, s.mean)}</td>
                <td class="num">{spreadValue(s, s.max)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    <div class="pair">
      {#if page.casts.length}
        <div>
          <h3>Most cast</h3>
          <ul class="spreads">
            {#each page.casts as s (s.name + s.role)}
              <li><span>{s.name}</span><span class="muted small">{spreadValue(s, s.mean)} a raid</span></li>
            {/each}
          </ul>
        </div>
      {/if}
      {#if page.consumables.length}
        <div>
          <h3>Consumables</h3>
          <ul class="spreads">
            {#each page.consumables as s (s.name)}
              <li><span>{s.name}</span><span class="muted small">{spreadValue(s, s.mean)} a raid</span></li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
    <p class="muted small">Your numbers only: nobody else sees this page. Updated {mine.generated_at}.</p>
  {:else if !mine.generated_at}
    <p class="muted">Shows once the worker has read the guild’s raids.</p>
  {:else if mine.looked_for.length}
    <p class="muted">{mine.looked_for.join(', ')} {mine.looked_for.length === 1 ? 'has' : 'have'} no guild raids yet.</p>
  {:else}
    <p class="muted">Claim your characters to see your raids here.</p>
  {/if}
  {#if !page}
    {@render main?.('')}
    <a href="{base}/me/claim{slash}">Claim your characters</a>
  {/if}
</section>

<style>
  .sub { margin-top: -0.25rem; }
  h3 { margin: 1rem 0 0.4rem; font-size: 1rem; }
  .small { font-size: 0.8rem; }
  .chars { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; }
  .chars select {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.35rem 0.7rem;
    font: inherit;
    min-width: min(100%, 14rem);
  }
  .bests { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; }
  .bests li { display: flex; flex-direction: column; }
  .scroll { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.3rem 0.5rem 0.3rem 0; vertical-align: top; }
  td .small { display: block; }
  .num { text-align: right; }
  .pair { display: grid; gap: 0 1.5rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr)); }
  .spreads { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.25rem; }
  .spreads li { display: flex; justify-content: space-between; gap: 0.75rem; }
</style>
