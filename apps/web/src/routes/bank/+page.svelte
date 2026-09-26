<script lang="ts">
  import Bank from '$lib/preview/Bank.svelte';
</script>

{#if __PREVIEW__}
  <Bank />
{:else}
  <h1>Guild bank</h1>
  <p>Bank sources per raid day, requests and the fairness ledger arrive in phase 2.6.</p>
{/if}
