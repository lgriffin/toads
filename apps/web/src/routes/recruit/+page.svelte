<script lang="ts">
  import Recruit from '$lib/preview/Recruit.svelte';
</script>

<svelte:head><title>Recruit · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Recruit />
{:else}
  <h1>Raid with the Toads</h1>
  <p>What we are recruiting, how the Discord interview room works and the application form arrive with the API.</p>
{/if}
