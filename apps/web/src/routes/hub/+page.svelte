<script lang="ts">
  import Hub from '$lib/preview/Hub.svelte';
</script>

<svelte:head><title>Hub · Toads</title></svelte:head>

{#if __PREVIEW__}
  <Hub />
{:else}
  <h1>Toads Hub</h1>
  <p>Your next raid, sign-ups, latest logs, the posts feed and the raid leader desk land here in milestone H3.</p>
{/if}
