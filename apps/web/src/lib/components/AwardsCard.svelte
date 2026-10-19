<script lang="ts">
  import { base } from '$app/paths';
  import { awardable, monthLabel, type AwardOut } from '$lib/awards';

  // A member's awards as their badges, newest first. `heading` names the card; `empty` is what a member with none sees.
  let {
    awards,
    heading = 'Your toads',
    empty = 'No awards yet. Officers give them for milestones, history and achievements.'
  }: { awards: AwardOut[]; heading?: string; empty?: string } = $props();
</script>

<section class="card" aria-labelledby="awards-h">
  <h2 id="awards-h">{heading}</h2>
  {#if awards.length === 0}
    <p class="muted">{empty}</p>
  {:else}
    <ul class="awards">
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
