<script lang="ts">
  import { dateTime } from '$lib/format';
  import {
    COMPARISON_VERSION,
    TONE_WORDS,
    averageLabel,
    comparedRaidLine,
    compactNumber,
    deltaTone,
    durationLabel,
    formatDelta,
    metricTone,
    scopeNote,
    type ComparisonResponse,
    type Metric,
    type Tone
  } from '$lib/reference';

  let { data }: { data: ComparisonResponse } = $props();
  let c = $derived(data.comparison);
  let note = $derived(c.version === COMPARISON_VERSION ? scopeNote(c.scope) : '');
</script>

{#snippet delta(percent: number | null, tone: Tone)}
  <span class={tone === 'positive' ? 'ok' : tone === 'negative' ? 'bad' : ''}>{formatDelta(percent)}</span
  >{#if TONE_WORDS[tone]}<span class="sr-only"> ({TONE_WORDS[tone]})</span>{/if}
{/snippet}

{#snippet metrics(title: string, rows: Metric[])}
  <div class="scroll">
    <table>
      <caption>{title}</caption>
      <thead>
        <tr><th scope="col">Metric</th><th scope="col" class="num">Ours</th><th scope="col" class="num">Reference</th><th scope="col" class="num">Difference</th></tr>
      </thead>
      <tbody>
        {#each rows as m (m.key)}
          <tr>
            <th scope="row">{m.label}</th>
            <td class="num">{m.guild_display}</td>
            <td class="num">{m.reference_display}</td>
            <td class="num">{@render delta(m.delta_percent, metricTone(m))}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/snippet}

<section class="card comparison" aria-labelledby="cmp-h">
  <h2 id="cmp-h">{c.guild.title} vs {c.reference.title}</h2>
  {#if c.version !== COMPARISON_VERSION}
    <p class="muted">This hub cannot draw the worker’s newer comparison yet.</p>
  {:else}
    <div class="sides">
      <div>
        <p class="side">Ours</p>
        <p><strong>{c.guild.title}</strong></p>
        <p class="muted small">{comparedRaidLine(c.guild)}</p>
      </div>
      <div>
        <p class="side">Reference</p>
        <p><strong>{c.reference.title}</strong></p>
        <p class="muted small">{comparedRaidLine(c.reference)}</p>
      </div>
    </div>
    <p class="muted small">Built {dateTime(data.generated_at)}. Green favours us, red favours the reference.</p>
    {#if note}<p class="warn note">{note}</p>{/if}

    <div class="pair">
      {@render metrics('Overview', c.overview)}
      {@render metrics('Composition', c.composition)}
    </div>

    <h3>Classes</h3>
    {#if c.classes.length}
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Class</th>
              <th scope="col">Role</th>
              <th scope="col" class="num">Ours</th>
              <th scope="col" class="num">Reference</th>
              <th scope="col" class="num">Difference</th>
            </tr>
          </thead>
          <tbody>
            {#each c.classes as row (`${row.player_class}-${row.role}-${row.metric}`)}
              <tr>
                <th scope="row">{row.player_class}</th>
                <td class="cap">{row.role}</td>
                <td class="num">{averageLabel(row.guild_average)} {row.metric} <span class="muted">×{row.guild_count}</span></td>
                <td class="num">{averageLabel(row.reference_average)} {row.metric} <span class="muted">×{row.reference_count}</span></td>
                <td class="num">{@render delta(row.delta_percent, deltaTone(row.delta_percent))}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="hint">Average per player of that class and role; ×n is how many played it.</p>
    {:else}
      <p class="muted">No class data.</p>
    {/if}

    <h3>Encounters</h3>
    {#if c.encounters.length}
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Boss</th>
              <th scope="col" class="num">Our time</th>
              <th scope="col" class="num">Their time</th>
              <th scope="col" class="num">Difference</th>
              <th scope="col" class="num">Damage (ours / theirs)</th>
              <th scope="col" class="num">Healing (ours / theirs)</th>
            </tr>
          </thead>
          <tbody>
            {#each c.encounters as e (e.name)}
              <tr>
                <th scope="row">{e.name}</th>
                <td class="num">{durationLabel(e.guild_duration_ms)}</td>
                <td class="num">{durationLabel(e.reference_duration_ms)}</td>
                <td class="num">{@render delta(e.duration_delta_percent, deltaTone(e.duration_delta_percent, false))}</td>
                <td class="num">{compactNumber(e.guild_damage)} / {compactNumber(e.reference_damage)}</td>
                <td class="num">{compactNumber(e.guild_healing)} / {compactNumber(e.reference_healing)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <p class="muted">No shared bosses.</p>
    {/if}

    <h3>Consumables</h3>
    {#if c.consumables.length}
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">Consumable</th>
              <th scope="col" class="num">Our uses</th>
              <th scope="col" class="num">Our users</th>
              <th scope="col" class="num">Their uses</th>
              <th scope="col" class="num">Their users</th>
            </tr>
          </thead>
          <tbody>
            {#each c.consumables as row (row.name)}
              <tr>
                <th scope="row">{row.name}</th>
                <td class="num">{row.guild_uses}</td>
                <td class="num">{row.guild_users}</td>
                <td class="num">{row.reference_uses}</td>
                <td class="num">{row.reference_users}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <p class="muted">No consumables recorded.</p>
    {/if}
  {/if}
</section>

<style>
  .sides { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr)); }
  .sides p { margin: 0.15rem 0; }
  .side { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
  .pair { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); margin-top: 0.75rem; }
  caption { text-align: left; font-weight: 600; padding: 0 0 0.4rem; }
  tbody th { color: var(--text); font-weight: 400; }
  h3 { font-size: 1rem; margin: 1.25rem 0 0.5rem; }
  .cap { text-transform: capitalize; }
  .small { font-size: 0.85rem; }
  .note { font-size: 0.9rem; }
  td.num { white-space: nowrap; }
</style>
