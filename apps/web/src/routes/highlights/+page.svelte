<script lang="ts">
  import Highlights from '$lib/preview/Highlights.svelte';
</script>

<svelte:head><title>Highlights · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Highlights />
{:else}
  <h1>Highlights</h1>
  <p>Highlight reels and member spotlights appear here once officers publish them.</p>
{/if}
