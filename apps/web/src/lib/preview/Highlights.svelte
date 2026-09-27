<script lang="ts">
  import { PROVIDER_LABELS } from '$lib/clips';
  import { ANONYMOUS, visibleHighlights, visibleSpotlights } from '$lib/community';
  import ClipPlayer from '$lib/components/ClipPlayer.svelte';
  import SpotlightCard from '$lib/components/SpotlightCard.svelte';
  import { shortDate } from '$lib/format';
  import { community } from './state.svelte';

  const reels = $derived(visibleHighlights(community.highlights, ANONYMOUS));
  const spots = $derived(visibleSpotlights(community.spotlights));
</script>

<h1>Highlights</h1>
<p class="muted">
  Clips from our raids and the people behind them. Videos load from their provider only when you press play.
</p>

<section aria-labelledby="reels-h">
  <h2 id="reels-h">Highlight reels</h2>
  <div class="reels">
    {#each reels as h (h.id)}
      <div class="card">
        <ClipPlayer
          provider={h.provider}
          clipId={h.clipId}
          title={h.title}
          meta="{h.boss ? `${h.boss} · ` : ''}{shortDate(h.createdAt)} · by {h.submittedBy} · {PROVIDER_LABELS[h.provider]}"
        />
      </div>
    {:else}
      <p class="muted">No reels yet.</p>
    {/each}
  </div>
</section>

<section aria-labelledby="spots-h">
  <h2 id="spots-h">Member spotlights</h2>
  <div class="grid">
    {#each spots as s (s.id)}
      <div class="card"><SpotlightCard spotlight={s} /></div>
    {:else}
      <p class="muted">No spotlights yet.</p>
    {/each}
  </div>
</section>

<style>
  section { margin-top: 1.5rem; }
  .reels { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); }
</style>
