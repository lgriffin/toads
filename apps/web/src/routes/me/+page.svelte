<script lang="ts">
  import Me from '$lib/preview/Me.svelte';
</script>

{#if __PREVIEW__}
  <Me />
{:else}
  <h1>Your performance</h1>
  <p>
    Claim your characters and see how each raid went for you against the guild median for your role.
    The seven charts from the build spec arrive in milestone H3.
  </p>
{/if}
