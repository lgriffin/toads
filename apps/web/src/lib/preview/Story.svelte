<script lang="ts">
  import { base } from '$app/paths';
  import { PROVIDER_LABELS } from '$lib/clips';
  import { ANONYMOUS, visibleHighlights, visibleSpotlights } from '$lib/community';
  import ClipPlayer from '$lib/components/ClipPlayer.svelte';
  import NeedsList from '$lib/components/NeedsList.svelte';
  import PostCard from '$lib/components/PostCard.svelte';
  import SpotlightCard from '$lib/components/SpotlightCard.svelte';
  import { story } from '$lib/mock/community';
  import { visibleFeed } from '$lib/posts';
  import { community } from './state.svelte';

  // The outward story is what an anonymous visitor sees, even in the signed-in preview.
  const reels = $derived(visibleHighlights(community.highlights, ANONYMOUS).slice(0, 3));
  const spots = $derived(visibleSpotlights(community.spotlights));
  const feed = $derived(visibleFeed(community.posts, ANONYMOUS).slice(0, 4));
</script>

<section class="hero">
  <p class="realm">{story.realm} · TBC Classic</p>
  <h1>{story.guild}</h1>
  <p class="tagline">{story.tagline}</p>
  <div class="cta">
    <a class="btn primary" href="{base}/recruit/">Apply to raid with us</a>
    <a class="btn" href={story.discordInvite} target="_blank" rel="noopener noreferrer">Join our Discord</a>
  </div>
</section>

<div class="grid">
  <section class="card" aria-labelledby="story-h">
    <h2 id="story-h">Our story</h2>
    {#each story.story as para}<p>{para}</p>{/each}
  </section>

  <section class="card" aria-labelledby="prog-h">
    <h2 id="prog-h">Progression</h2>
    <ul class="prog">
      {#each story.progression as z (z.zone)}
        <li>
          <span class="zone"><span>{z.zone}</span><span class="muted">{z.killed}/{z.total}</span></span>
          <span class="bar" aria-hidden="true"><span style="width: {(z.killed / z.total) * 100}%"></span></span>
        </li>
      {/each}
    </ul>
  </section>

  <section class="card" aria-labelledby="needs-h">
    <h2 id="needs-h">We’re recruiting</h2>
    <NeedsList needs={story.needs} />
    <p><a href="{base}/recruit/">How applying works</a></p>
  </section>
</div>

<section class="band" aria-labelledby="reels-h">
  <div class="band-head">
    <h2 id="reels-h">Highlight reels</h2>
    <a href="{base}/highlights/">All highlights</a>
  </div>
  <div class="reels">
    {#each reels as h (h.id)}
      <ClipPlayer provider={h.provider} clipId={h.clipId} title={h.title} meta="{h.boss ?? ''} · {PROVIDER_LABELS[h.provider]}" />
    {/each}
  </div>
</section>

<div class="grid">
  <section class="card" aria-labelledby="spot-h">
    <h2 id="spot-h">Member spotlights</h2>
    {#each spots as s (s.id)}
      <SpotlightCard spotlight={s} />
    {:else}
      <p class="muted">No spotlights yet.</p>
    {/each}
  </section>

  <section class="card" aria-labelledby="news-h">
    <h2 id="news-h">News from the pond</h2>
    {#each feed as p (p.id)}
      <PostCard post={p} />
    {/each}
  </section>
</div>

<style>
  .hero { padding: 1.5rem 0 1.25rem; }
  .realm { color: var(--accent); margin: 0; font-size: 0.9rem; }
  .hero h1 { font-size: clamp(2rem, 8vw, 3.2rem); margin: 0.25rem 0 0.5rem; }
  .tagline { font-size: 1.1rem; max-width: 40rem; margin: 0 0 1.25rem; }
  .cta { display: flex; flex-wrap: wrap; gap: 0.75rem; }
  .prog { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.75rem; }
  .zone { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.95rem; }
  .bar { display: block; height: 0.5rem; margin-top: 0.3rem; border-radius: 999px; background: var(--line); overflow: hidden; }
  .bar span { display: block; height: 100%; background: var(--accent); }
  .band { margin: 1.5rem 0; }
  .band-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
  .reels { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); }
</style>
