<script lang="ts">
  import type { ZoneProgress } from '$lib/community';

  let { zones }: { zones: ZoneProgress[] } = $props();
</script>

<ul class="prog">
  {#each zones as z (z.zone)}
    <li>
      <span class="zone"><span>{z.zone}</span><span class="muted">{z.killed}/{z.total}</span></span>
      <span class="bar" aria-hidden="true"><span style="width: {z.total ? (z.killed / z.total) * 100 : 0}%"></span></span>
    </li>
  {/each}
</ul>

<style>
  .prog { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.75rem; }
  .zone { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.95rem; }
  .bar { display: block; height: 0.5rem; margin-top: 0.3rem; border-radius: 999px; background: var(--line); overflow: hidden; }
  .bar span { display: block; height: 100%; background: var(--accent); }
</style>
