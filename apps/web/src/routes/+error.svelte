<script lang="ts">
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import MembersOnly from '$lib/MembersOnly.svelte';
</script>

{#if $page.status === 403}
  <MembersOnly />
{:else}
  <h1>{$page.status === 404 ? 'Not found' : 'Something went wrong'}</h1>
  <p class="muted">{$page.error?.message ?? ''}</p>
  <p><a href="{base}/">Back to the hub</a></p>
{/if}
