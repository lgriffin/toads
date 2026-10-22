<script lang="ts">
  import { hubBankDesk } from '$lib/bank-desk';
  import BankDesk from '$lib/components/BankDesk.svelte';
  import BankLive from '$lib/components/BankLive.svelte';
  import Bank from '$lib/preview/Bank.svelte';

  const desk = hubBankDesk();
  // Both show desk requests: an ask in BankLive refreshes the officers' queue, an answer there refreshes "Your requests".
  let deskCard = $state<ReturnType<typeof BankDesk>>();
  let live = $state<ReturnType<typeof BankLive>>();
</script>

{#if __PREVIEW__}
  <Bank />
{:else}
  <!-- One ask form and one list of the member's requests (BankLive), whichever service answers: ToadsBank for what
       the bank holds, the hub's request desk (docs/bank-desk.md) for anything else. Officers answer the desk above. -->
  <BankDesk bind:this={deskCard} backend={desk} own={false} onChange={() => live?.reloadDeskMine()} />
  <BankLive bind:this={live} {desk} onAsked={() => deskCard?.reloadDesk()} />
{/if}
