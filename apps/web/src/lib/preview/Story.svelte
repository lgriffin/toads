<script lang="ts">
  import { story } from '$lib/mock/community';
  import StoryPage from '$lib/StoryPage.svelte';
  import { community } from './state.svelte';

  // The preview's officer and consent actions change the community state, so the story reads it rather than the
  // sample story's own copies.
  const preview = $derived({
    ...story,
    posts: community.posts,
    highlights: community.highlights,
    spotlights: community.spotlights
  });
</script>

<StoryPage story={preview} />
