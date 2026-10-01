<script lang="ts">
  import BankLive from '$lib/components/BankLive.svelte';
  import Bank from '$lib/preview/Bank.svelte';
</script>

{#if __PREVIEW__}
  <Bank />
{:else}
  <BankLive />
{/if}
