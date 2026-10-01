<script lang="ts">
  import { useBankFetch } from '$lib/bank';
  import BankLive from '$lib/components/BankLive.svelte';
  import { previewBankFetch } from './bank-fake';
  import { previewSession } from './session.svelte';

  // The real bank page, answered from sample data in this browser (bank-fake.ts) rather than by the hub.
  useBankFetch(previewBankFetch);
</script>

<p class="demo" role="note">
  {#if previewSession.role === 'officer'}
    Demo: the officer view is also a super admin here, so it works the request queue and imports, grants bank powers and
    mints officer tokens. Mint one, switch to the raider view and redeem it below.
  {:else}
    Demo: request an item or cancel one. A raider who redeems an officer token gains bank upkeep; switch to the officer
    view to mint one.
  {/if}
  Nothing leaves this browser.
</p>

<!-- Switching views reloads the page as that view, as signing in again would. -->
{#key previewSession.role}
  <BankLive />
{/key}

<style>
  .demo { color: var(--muted); font-size: 0.9rem; margin: 0 0 0.5rem; }
</style>
