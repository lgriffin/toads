<script lang="ts">
  import Story from '$lib/preview/Story.svelte';
</script>

<svelte:head><title>Our story · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Story />
{:else}
  <h1>Our story</h1>
  <p>The guild story, progression, recruitment needs and highlight reels land here once the public story API is live.</p>
{/if}
