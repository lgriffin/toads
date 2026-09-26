<script lang="ts">
  import Home from '$lib/preview/Home.svelte';
</script>

{#if __PREVIEW__}
  <Home />
{:else}
  <h1>Toads Hub</h1>
  <p>Next raid, latest logs and guild announcements land here in milestone H3.</p>
{/if}
