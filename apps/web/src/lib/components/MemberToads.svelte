<script lang="ts">
  import { base } from '$app/paths';
  import { memberToads, toadSrc, type MemberFacts } from '$lib/toads';

  // The toads a member has earned: rank, class and role, side by side. Decorative next to a name, so each carries its
  // meaning as a tooltip and as the list's text for screen readers.
  let { size = 28, ...facts }: MemberFacts & { size?: number } = $props();
  const toads = $derived(memberToads(facts));
</script>

{#if toads.length}
  <ul class="toads" aria-label="Rank, class and role">
    {#each toads as t (t.id)}
      <li title={t.label}>
        <img src={toadSrc(base, t)} alt="" width={size} height={Math.round(size * 0.875)} loading="lazy" />
        <span class="sr-only">{t.label}</span>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .toads { display: inline-flex; gap: 0.15rem; margin: 0; padding: 0; list-style: none; vertical-align: middle; }
  img { display: block; height: auto; }
</style>
