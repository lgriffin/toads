<script lang="ts">
  import { base } from '$app/paths';
  import Me from '$lib/preview/Me.svelte';
</script>

{#if __PREVIEW__}
  <Me />
  <p><a href="{base}/me/claim">Claim a character</a></p>
{:else}
  <h1>Your performance</h1>
  <p>
    Claim your characters and see how each raid went for you against the guild median for your role.
    The seven charts from the build spec arrive in milestone H3.
  </p>
  <p><a href="{base}/me/claim">Claim your characters</a></p>
{/if}
