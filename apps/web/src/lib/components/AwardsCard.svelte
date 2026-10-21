<script lang="ts">
  import { base } from '$app/paths';
  import { awardable, monthLabel, type AwardOut } from '$lib/awards';
  import { toadSrc, type Toad } from '$lib/toads';

  // A member's toads as badges: first the ones they wear (rank, member, guild jobs, the badges their
  // Discord roles earn, class and role), then their awards, newest first. `heading` names the card; `empty` is what a
  // member with neither sees.
  let {
    awards,
    toads = [],
    heading = 'Your toads',
    empty = 'No awards yet. Officers give them for milestones, history and achievements.'
  }: { awards: AwardOut[]; toads?: readonly Toad[]; heading?: string; empty?: string } = $props();
  // Guild jobs are awards too; the award's own entry (with its date and note) shows them once.
  const worn = $derived(toads.filter((t) => !awards.some((a) => awardable(a.award_id)?.file === t.id)));
</script>

<section class="card" aria-labelledby="awards-h">
  <h2 id="awards-h">{heading}</h2>
  {#if awards.length === 0 && worn.length === 0}
    <p class="muted">{empty}</p>
  {:else}
    <ul class="awards">
      {#each worn as t (t.id)}
        <li>
          <img src={toadSrc(base, t, true)} alt="" width="96" height="115" loading="lazy" />
          <span class="name">{t.label}</span>
        </li>
      {/each}
      {#each awards as a (a.id)}
        {@const art = awardable(a.award_id)}
        <li>
          {#if art}
            <img src="{base}/logos/{art.file}-badge.svg" alt="" width="96" height="115" loading="lazy" />
          {/if}
          <span class="name">{a.name}</span>
          {#if a.period}<span class="muted small">{monthLabel(a.period)}</span>{/if}
          {#if a.note}<span class="muted small note">{a.note}</span>{/if}
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .awards { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem 0.75rem; grid-template-columns: repeat(auto-fill, minmax(7.5rem, 1fr)); }
  li { display: grid; justify-items: center; text-align: center; gap: 0.15rem; align-content: start; }
  img { width: 6rem; height: auto; }
  .name { font-weight: 600; }
  .small { font-size: 0.85rem; }
  .note { max-width: 14ch; }
</style>
