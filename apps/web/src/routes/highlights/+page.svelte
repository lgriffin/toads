<script lang="ts">
  import HighlightsPage from '$lib/components/HighlightsPage.svelte';
  import { hubGallery } from '$lib/gallery';
  import Highlights from '$lib/preview/Highlights.svelte';
</script>

<svelte:head><title>Highlights · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Highlights />
{:else}
  <HighlightsPage backend={hubGallery()} />
{/if}
