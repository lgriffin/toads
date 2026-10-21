<script lang="ts">
  import { hubBankDesk } from '$lib/bank-desk';
  import BankDesk from '$lib/components/BankDesk.svelte';
  import BankLive from '$lib/components/BankLive.svelte';
  import Bank from '$lib/preview/Bank.svelte';
</script>

{#if __PREVIEW__}
  <Bank />
{:else}
  <!-- The request desk (docs/bank-desk.md) is the hub's own and needs no bank snapshot; BankLive is ToadsBank's. -->
  <BankDesk backend={hubBankDesk()} />
  <BankLive />
{/if}
