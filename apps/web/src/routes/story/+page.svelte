<script lang="ts">
  import '$lib/pond.css';
  import { onMount } from 'svelte';
  import { publicStory } from '$lib/api';
  import type { PublicStory } from '$lib/community';
  import { storyFromApi } from '$lib/community-api';
  import PondHero from '$lib/components/PondHero.svelte';
  import Story from '$lib/preview/Story.svelte';
  import StoryPage from '$lib/StoryPage.svelte';

  // The live hub reads the story from GET /api/public/story: the tagline and story from the repo (the API's
  // community/story.py), the guild name and Discord link from config/community.yaml, the rest is what officers
  // published as public. No login needed.
  type Loaded = { kind: 'loading' } | { kind: 'ok'; story: PublicStory } | { kind: 'error' };
  let live = $state<Loaded>({ kind: 'loading' });

  onMount(async () => {
    if (__PREVIEW__) return;
    try {
      live = { kind: 'ok', story: storyFromApi(await publicStory()) };
    } catch {
      live = { kind: 'error' };
    }
  });
</script>

<svelte:head><title>Our story · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Story />
{:else if live.kind === 'ok'}
  <StoryPage story={live.story} />
{:else}
  <div class="pond-page">
    <PondHero
      title="Our story"
      line="Horde · PvP · EU"
      lede={live.kind === 'loading' ? 'Loading the story…' : 'The story did not load. Refresh the page to try again.'}
      toads={['pond-medallion']}
    />
  </div>
{/if}
