<script lang="ts">
  import { base } from '$app/paths';
  import { memberToads, rankToad, toadSrc, type MemberFacts } from '$lib/toads';

  // The signed-in member's own toad, large, with their name: what every member meets first when they sign in, held
  // pages included. The rank toad stands as a badge; any titles, class and role toads follow it small.
  let { name, ...facts }: MemberFacts & { name: string } = $props();
  const rank = $derived(rankToad(facts.tier ?? 'raider', facts.username));
  const rest = $derived(memberToads(facts).slice(rank ? 1 : 0));
</script>

{#if rank}
  <section class="greeting" aria-labelledby="greeting-h">
    <img class="rank" src={toadSrc(base, rank, true)} alt="{rank.label} toad" width="104" height="125" />
    <div>
      <h2 id="greeting-h">Welcome back, {name}</h2>
      <p>
        Your toad is the <strong>{rank.label}</strong> toad. It goes with you around the hub, beside your name.
      </p>
      {#if rest.length}
        <p class="rest">
          {#each rest as t (t.id)}<img src={toadSrc(base, t)} alt={t.label} title={t.label} width="34" height="30" />{/each}
        </p>
      {/if}
    </div>
  </section>
{/if}

<style>
  .greeting {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 1.1rem;
    align-items: center;
    padding: 1.4rem 0 0;
    max-width: 44rem;
  }
  .rank { filter: drop-shadow(0 8px 16px rgb(5 3 30 / 0.55)); }
  h2 { margin: 0; font-family: 'Cinzel', Georgia, serif; font-weight: 600; font-size: 1.35rem; color: var(--bronze-hi); }
  p { margin: 0.25rem 0 0; color: var(--muted); }
  strong { color: var(--cream); }
  .rest { display: flex; gap: 0.3rem; margin-top: 0.5rem; }
  @media (max-width: 30rem) {
    .greeting { grid-template-columns: 1fr; justify-items: start; }
  }
</style>
