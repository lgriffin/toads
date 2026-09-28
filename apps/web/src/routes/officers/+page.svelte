<script lang="ts">
  import { base } from '$app/paths';
  import Officers from '$lib/preview/Officers.svelte';
</script>

<svelte:head><title>Officers · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Officers />
{:else}
  <h1>Officer console</h1>
  <p>Applications, the Discord curation queue, post composer, highlight review and spotlights arrive with the API.</p>
  <p><a href="{base}/officers/reference">Reference comparison</a>: compare one of our raids with another guild's.</p>
{/if}
