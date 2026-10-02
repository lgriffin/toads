<script lang="ts">
  import { useBankFetch } from '$lib/bank';
  import BankLive from '$lib/components/BankLive.svelte';
  import { previewBankFetch } from './bank-fake';
  import { hasOfficerPowers } from './gate';
  import { previewSession } from './session.svelte';

  // The real bank page, answered from sample data in this browser (bank-fake.ts) rather than by the hub.
  useBankFetch(previewBankFetch);
</script>

<p class="demo" role="note">
  {#if previewSession.role === 'admin'}
    Demo: as a super admin you work every bank's request queue and imports, grant bank powers and mint officer tokens.
    Mint one, switch to the raider view and redeem it below.
  {:else if hasOfficerPowers(previewSession.role)}
    Demo: as Wednesday's officer you work Wednesday's request queue and imports. Grants and officer tokens are for super
    admins; switch to the super admin view to mint one.
  {:else}
    Demo: request an item or cancel one. A raider who redeems an officer token gains bank upkeep; switch to the super
    admin view to mint one.
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
