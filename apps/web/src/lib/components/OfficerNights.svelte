<script lang="ts">
  import { base } from '$app/paths';
  import { dayName, type RaidDays } from '$lib/absences';
  import { dayToad } from '$lib/raid-page';

  // The Officer console's way into each night's own officer section: only the nights the viewer runs, so a Sunday
  // officer never sees a Wednesday entry. Global officers and super admins run every night.
  let { raidDays }: { raidDays: RaidDays } = $props();
</script>

<section class="card nights" aria-labelledby="nights-h">
  <h2 id="nights-h">{raidDays.officerDays.length === 1 ? 'Your raid night' : 'Your raid nights'}</h2>
  {#if raidDays.officerDays.length}
    <p class="muted">Each night's own section: its absences, task board and interview panel, for its officers only.</p>
    <ul>
      {#each raidDays.officerDays as day (day)}
        {@const name = dayName(day, raidDays.names)}
        <li>
          <a href="{base}/officers/nights/{day}/">
            <img src="{base}/logos/{dayToad(day, name)}.svg" alt="" width="48" height="58" />
            <span>{name} officers</span>
          </a>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="muted">You do not run a raid night. A night's officer role in Discord opens its section here.</p>
  {/if}
</section>

<style>
  .nights { display: grid; gap: 0.6rem; margin-block: 1rem; }
  .nights h2, .nights p { margin: 0; }
  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.75rem; }
  a { display: flex; align-items: center; gap: 0.6rem; padding: 0.4rem 0.9rem 0.4rem 0.4rem; border: 1px solid var(--bronze); border-radius: 999px; text-decoration: none; font-weight: 700; }
  a:hover, a:focus-visible { background: color-mix(in srgb, var(--bronze) 18%, transparent); }
  img { width: 2.6rem; height: auto; }
</style>
