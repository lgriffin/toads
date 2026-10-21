<script lang="ts">
  import { hubBankDesk } from '$lib/bank-desk';
  import BankDesk from '$lib/components/BankDesk.svelte';
  import BankLive from '$lib/components/BankLive.svelte';
  import Bank from '$lib/preview/Bank.svelte';

  const desk = hubBankDesk();
</script>

{#if __PREVIEW__}
  <Bank />
{:else}
  <!-- One ask form and one list of the member's requests (BankLive), whichever service answers: ToadsBank for what
       the bank holds, the hub's request desk (docs/bank-desk.md) for anything else. Officers answer the desk above. -->
  <BankDesk backend={desk} own={false} />
  <BankLive {desk} />
{/if}
