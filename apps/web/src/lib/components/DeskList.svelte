<script lang="ts">
  import type { DeskLine } from '$lib/community-api';

  // Counts only: the officer console has no queue sections for these to open yet.
  let { lines }: { lines: DeskLine[] } = $props();
</script>

<ul class="desk">
  {#each lines as d (d.label)}
    <li class="line"><span class="n">{d.count}</span> {d.label}</li>
  {/each}
</ul>

<style>
  .desk { list-style: none; margin: 0 0 0.5rem; padding: 0; display: grid; gap: 0.35rem; }
  .line { display: flex; gap: 0.6rem; align-items: baseline; }
  .n { font-size: 1.3rem; min-width: 1.5rem; text-align: right; font-variant-numeric: tabular-nums; }
</style>
