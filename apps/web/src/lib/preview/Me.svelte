<script lang="ts">
  import AwardsCard from '$lib/components/AwardsCard.svelte';
  import BadgesCard from '$lib/components/BadgesCard.svelte';
  import { titlesOf } from '$lib/awards';
  import { previewAwardsOf } from './awards-fake';
  import { previewBadges } from '$lib/mock/badges';
  import MemberToads from '$lib/components/MemberToads.svelte';
  import { getMe } from '$lib/me-context';
  import { me } from '$lib/mock/data';
  import { memberToads } from '$lib/toads';
  import CharacterCard from '$lib/components/CharacterCard.svelte';
  import { previewCharacterPage } from '$lib/mock/characters';
  import MainSwap from '$lib/components/MainSwap.svelte';
  import { previewMain } from './main-fake';

  let raids = $state(previewCharacterPage());
  const awards = previewAwardsOf(1);
  // The header's toads (rank, member, role badges, class and role), with the titles of the awards shown here.
  const signedIn = getMe();
  let facts = $derived({ ...signedIn(), titles: titlesOf(awards) });
  let toads = $derived(memberToads(facts));
</script>

<h1>Your performance <MemberToads {...facts} size={40} /></h1>

<div class="grid">
  <div class="wide">
    <CharacterCard mine={raids} pick={(name) => (raids = previewCharacterPage(name))}>
      {#snippet main(viewing)}<MainSwap backend={previewMain} {viewing} shown={raids.characters} />{/snippet}
    </CharacterCard>
  </div>

  <div class="wide"><AwardsCard {awards} {toads} /></div>

  <div class="wide"><BadgesCard mine={previewBadges} /></div>

  <section class="card">
    <h2>Bank receipts</h2>
    <table>
      <thead><tr><th>Item</th><th class="num">Qty</th><th>Date</th></tr></thead>
      <tbody>
        {#each me.receipts as r}
          <tr>
            <td>{r.item}<br /><span class="muted small">{r.request}</span></td>
            <td class="num">{r.count}</td>
            <td>{r.date.slice(5)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>
</div>

<style>
  .small { font-size: 0.8rem; }
  .wide { grid-column: 1 / -1; }
</style>
