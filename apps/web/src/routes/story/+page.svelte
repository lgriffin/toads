<script lang="ts">
  import '$lib/pond.css';
  import PondHero from '$lib/components/PondHero.svelte';
  import Story from '$lib/preview/Story.svelte';
</script>

<svelte:head><title>Our story · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Story />
{:else}
  <div class="pond-page">
    <PondHero
      title="Our story"
      line="Horde · PvP · Europe (EU)"
      lede="The guild story, progression, recruitment needs and highlight reels land here once the public story API is live."
      toads={['pond-medallion']}
    />
  </div>
{/if}
