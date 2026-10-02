<script lang="ts">
  import { RAID_WEEK } from '$lib/landing';
</script>

<ol class="week" aria-label="A raid week">
  {#each RAID_WEEK as d (d.day)}
    <li class:raid={d.raid}>
      <strong>{d.day}{#if d.raid}<span class="sr-only"> (raid night)</span>{/if}</strong>
      <span>{d.text}</span>
    </li>
  {/each}
</ol>

<style>
  .week {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 8.5rem), 1fr));
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
  }
  li { padding: 0.75rem; display: grid; gap: 0.3rem; align-content: start; font-size: 0.9rem; border: 1px solid var(--line); margin: -1px 0 0 -1px; min-width: 0; }
  li.raid { background: color-mix(in srgb, var(--accent) 14%, var(--surface)); }
  li:not(.raid) { background: var(--surface); }
</style>
