<script lang="ts">
  import type { RecruitmentNeed } from '$lib/community';

  let { needs }: { needs: RecruitmentNeed[] } = $props();
  const ORDER = { high: 0, medium: 1, low: 2 } as const;
  const sorted = $derived([...needs].sort((a, b) => ORDER[a.priority] - ORDER[b.priority]));
</script>

<ul class="needs">
  {#each sorted as n (n.className + n.spec)}
    <li>
      <span><strong>{n.spec} {n.className}</strong> <span class="muted">{n.role}</span></span>
      <span class="right">
        <span class="muted small">{n.raidDays.length ? n.raidDays.join(' & ') : 'Either night'}</span>
        <span class="pill prio-{n.priority}">{n.priority} priority</span>
      </span>
    </li>
  {/each}
</ul>

<style>
  .needs { list-style: none; margin: 0; padding: 0; }
  li {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 0.25rem 0.75rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--line);
  }
  .right { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
  .small { font-size: 0.8rem; }
  .prio-high { background: var(--accent); color: #0f1411; }
  .prio-medium { background: #3b3320; color: var(--warn); }
</style>
