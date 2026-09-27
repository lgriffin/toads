<script lang="ts">
  import { base } from '$app/paths';
  import type { DeskLine } from '$lib/community-api';

  let { lines }: { lines: DeskLine[] } = $props();
</script>

<ul class="desk">
  {#each lines as d (d.label)}
    <li><a href="{base}/officers/{d.href}"><span class="n">{d.count}</span> {d.label}</a></li>
  {/each}
</ul>

<style>
  .desk { list-style: none; margin: 0 0 0.5rem; padding: 0; display: grid; gap: 0.35rem; }
  .desk a { display: flex; gap: 0.6rem; align-items: baseline; }
  .n { font-size: 1.3rem; min-width: 1.5rem; text-align: right; font-variant-numeric: tabular-nums; }
</style>
