<script lang="ts">
  import { base } from '$app/paths';
  import { earned, progressPercent, qualityTextColour, type MyBadges } from '$lib/badges';
  import BadgeIcon from '$lib/components/BadgeIcon.svelte';

  // The member's main character's Toads badges, earned or not, with progress to each next tier (GET /api/me/badges).
  let { mine }: { mine: MyBadges } = $props();

  const entry = $derived(mine.entry);
  const count = $derived(entry ? earned(entry.badges).length : 0);
</script>

<section class="card" aria-labelledby="badges-h">
  <h2 id="badges-h">Your badges</h2>
  {#if entry}
    <p class="muted sub">
      {entry.name}: {count} of {entry.badges.length} earned across the guild’s raids.
    </p>
    <ul class="list">
      {#each entry.badges as b (b.id)}
        <li>
          <BadgeIcon badge={b} size="large" />
          <div class="text">
            <div class="head">
              <strong>{b.name}</strong>
              {#if b.tier > 0}<span class="tier" style="color: {qualityTextColour(b.quality)}">{b.tier_name}</span>{/if}
            </div>
            <span class="muted small">{b.description} · {b.display}</span>
            {#if b.next_at !== null}
              <span class="bar" aria-hidden="true"><span style="width: {progressPercent(b)}%"></span></span>
              <span class="muted small">{b.next_tier} at {b.next_at}</span>
            {:else}
              <span class="muted small">Top tier</span>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {:else if !mine.generated_at}
    <p class="muted">Shows once the worker has counted the guild’s raids.</p>
  {:else if mine.looked_for.length}
    <p class="muted">{mine.looked_for.join(', ')} {mine.looked_for.length === 1 ? 'has' : 'have'} no guild raids yet.</p>
  {:else}
    <p class="muted">Claim your characters to see your badges here.</p>
  {/if}
  {#if !entry}
    <!-- The preview prerenders pages with trailing slashes. -->
    <a href="{base}/me/claim{__PREVIEW__ ? '/' : ''}">Claim your characters</a>
  {/if}
</section>

<style>
  .sub { margin-top: -0.25rem; }
  .list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.9rem; grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr)); }
  .list li { display: flex; gap: 0.75rem; align-items: flex-start; min-width: 0; }
  .text { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; flex: 1; }
  .head { display: flex; gap: 0.5rem; align-items: baseline; flex-wrap: wrap; }
  .tier { font-size: 0.8rem; }
  .small { font-size: 0.8rem; }
  .bar { display: block; height: 0.35rem; border-radius: 999px; background: var(--line); overflow: hidden; margin-top: 0.2rem; }
  .bar span { display: block; height: 100%; background: var(--accent); }
</style>
