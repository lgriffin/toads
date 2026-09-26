<script lang="ts">
  import Raids from '$lib/preview/Raids.svelte';
</script>

{#if __PREVIEW__}
  <Raids />
{:else}
  <h1>Raids &amp; Logs</h1>
  <p>Analysed raids with zone, raid day, size and lookback filters arrive in phase 2.7.</p>
{/if}
