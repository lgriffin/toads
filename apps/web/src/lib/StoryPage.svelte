<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import '$lib/pond.css';
  import { base } from '$app/paths';
  import PondHero from '$lib/components/PondHero.svelte';
  import { PROVIDER_LABELS } from '$lib/clips';
  import { ANONYMOUS, visibleHighlights, visibleSpotlights } from '$lib/community';
  import ClipPlayer from '$lib/components/ClipPlayer.svelte';
  import NeedsList from '$lib/components/NeedsList.svelte';
  import PostCard from '$lib/components/PostCard.svelte';
  import ProgressBars from '$lib/components/ProgressBars.svelte';
  import SpotlightCard from '$lib/components/SpotlightCard.svelte';
  import type { PublicStory } from '$lib/community';
  import { visibleFeed } from '$lib/posts';

  // The public story page, from GET /api/public/story on the live hub and from sample data in the preview.
  // `storyOnly` is the launch hold's public site: the hero, the Discord link and our story, nothing else.
  let { story, storyOnly = false }: { story: PublicStory; storyOnly?: boolean } = $props();

  // The outward story is what an anonymous visitor sees, even in the signed-in preview.
  const reels = $derived(visibleHighlights(story.highlights, ANONYMOUS).slice(0, 3));
  const spots = $derived(visibleSpotlights(story.spotlights));
  const feed = $derived(visibleFeed(story.posts, ANONYMOUS).slice(0, 4));
</script>

<div class="pond-page">
  <PondHero
    title={story.guild}
    line="Horde · PvP · EU"
    lede={story.tagline}
    toads={['pond-medallion', '01-the-regular', '05-croak']}
  >
    {#if !storyOnly}<a class="medal" href="{base}/recruit/">Apply to raid with us</a>{/if}
    {#if story.discordInvite}
      <a class={storyOnly ? 'medal' : 'ghost'} href={story.discordInvite} target="_blank" rel="noopener noreferrer">Join our Discord</a>
    {/if}
  </PondHero>

  <section class="band dusk" aria-labelledby="story-h">
    <div class="story-grid" class:alone={storyOnly}>
      <div class="story">
        <h2 id="story-h">Our story</h2>
        {#each story.story as para}<p>{para}</p>{/each}
      </div>
      {#if !storyOnly}
      <div class="side">
        <section class="card" aria-labelledby="prog-h">
          <h2 id="prog-h">Progression</h2>
          {#if story.progression.length}
            <ProgressBars zones={story.progression} />
          {:else}
            <p class="muted">No bosses logged yet.</p>
          {/if}
        </section>
        <section class="card" aria-labelledby="needs-h">
          <h2 id="needs-h">We’re recruiting</h2>
          {#if story.needs.length}
            <NeedsList needs={story.needs} />
          {:else}
            <p class="muted">No open spots right now, but we are always happy to hear from good people.</p>
          {/if}
          <p><a href="{base}/recruit/">How applying works</a></p>
        </section>
      </div>
      {/if}
    </div>
  </section>

  {#if !storyOnly}

  <section class="band" aria-labelledby="reels-h">
    <div class="band-head">
      <h2 id="reels-h">Highlight reels</h2>
      <a href="{base}/highlights/">All highlights</a>
    </div>
    <div class="reels">
      {#each reels as h (h.id)}
        <ClipPlayer provider={h.provider} clipId={h.clipId} title={h.title} meta="{h.boss ?? ''} · {PROVIDER_LABELS[h.provider]}" />
      {:else}
        <p class="muted">No highlight reels yet.</p>
      {/each}
    </div>
  </section>

  <section class="band dusk" aria-label="Members and news">
    <div class="pair">
      <section aria-labelledby="spot-h">
        <h2 id="spot-h" class="sub">Member spotlights</h2>
        {#each spots as s (s.id)}
          <SpotlightCard spotlight={s} />
        {:else}
          <p class="muted">No spotlights yet.</p>
        {/each}
      </section>
      <section aria-labelledby="news-h">
        <h2 id="news-h" class="sub">News from the pond</h2>
        {#each feed as p (p.id)}
          <PostCard post={p} />
        {:else}
          <p class="muted">No news yet.</p>
        {/each}
      </section>
    </div>
  </section>
  {/if}
</div>

<style>
  .story-grid { display: grid; gap: 2rem; align-items: start; }
  @media (min-width: 56rem) { .story-grid:not(.alone) { grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); } }
  .story { display: grid; gap: 1rem; font-size: 1.2rem; }
  .story h2 { font-size: clamp(1.5rem, 4vw, 2.1rem); color: var(--bronze-hi); }
  .story p { margin: 0; max-width: 62ch; }
  .side { display: grid; gap: 1rem; }
  .side .card { display: grid; gap: 0.75rem; }
  .side p { margin: 0; }
  .band-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
  .reels { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); }
  .pair { display: grid; gap: 2rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); align-items: start; }
  .pair > section { display: grid; gap: 0.9rem; align-content: start; }
  .sub { font-size: 1.4rem; color: var(--bronze-hi); }
</style>
