<script lang="ts">
  import { visibleSpotlights } from '$lib/community';
  import HighlightsPage from '$lib/components/HighlightsPage.svelte';
  import SpotlightCard from '$lib/components/SpotlightCard.svelte';
  import { previewGallery } from './gallery-fake';
  import { previewSession } from './session.svelte';
  import { community } from './state.svelte';

  const spots = $derived(visibleSpotlights(community.spotlights));
</script>

<p class="demo" role="note">
  {#if previewSession.role === 'admin'}
    Demo: as a super admin (a global officer) you pick the photo of the week, take photos and streams down and review
    clips. Open a photo to try it.
  {:else}
    Demo: these photos and the stream stand in for what raiders post with the Toad Bot. You can take down your own
    (Hopscotch’s) photos; switch to the super admin view to pick the photo of the week.
  {/if}
  Nothing leaves this browser.
</p>

<!-- Switching views reloads the page as that view, as signing in again would. -->
{#key previewSession.role}
  <HighlightsPage backend={previewGallery(previewSession.role === 'admin')} />
{/key}

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
  .demo { color: var(--muted); font-size: 0.9rem; margin: 0 0 0.5rem; }
  section { margin-top: 1.75rem; }
  .grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); }
</style>
