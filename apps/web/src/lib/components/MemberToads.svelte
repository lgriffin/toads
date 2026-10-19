<script lang="ts">
  import { base } from '$app/paths';
  import { memberToads, toadSrc, type MemberFacts } from '$lib/toads';

  // The toads a member has earned: rank, titles, class and role, side by side. Each image says what it stands for in
  // its alt text and tooltip. Kept out of lists and labels on purpose: it sits in headings and the header, where an
  // extra list or label would change what those read as.
  let { size = 28, ...facts }: MemberFacts & { size?: number } = $props();
  const toads = $derived(memberToads(facts));
</script>

{#if toads.length}
  <span class="toads">
    {#each toads as t (t.id)}
      <img
        src={toadSrc(base, t)}
        alt={t.label}
        title={t.label}
        width={size}
        height={Math.round(size * 0.875)}
        loading="lazy"
      />
    {/each}
  </span>
{/if}

<style>
  .toads { display: inline-flex; gap: 0.15rem; vertical-align: middle; }
  img { display: block; height: auto; }
</style>
