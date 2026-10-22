<script lang="ts">
  import { bankError, grantsText, redeemToken } from '$lib/bank';

  // Any member: redeem an officer token a super admin gave them (docs/admin.md). The same as /bank redeem in Discord.
  let { onredeemed }: { onredeemed?: () => void | Promise<void> } = $props();

  let token = $state('');
  let message = $state('');
  let busy = $state(false);

  async function redeem(event: SubmitEvent) {
    event.preventDefault();
    busy = true;
    message = '';
    try {
      const done = await redeemToken(token);
      token = '';
      message = done.grants.length
        ? `Token redeemed. You may now ${done.grants.map((g) => grantsText([g.permission], g.raid_day).toLowerCase()).join(', and ')}.`
        : 'Token redeemed, but it granted nothing new.';
      await onredeemed?.();
    } catch (e) {
      message = bankError(e);
    } finally {
      busy = false;
    }
  }
</script>

<!-- Few members ever hold a token, so it waits behind a disclosure rather than sitting in every raider's way. -->
<details class="card redeem">
  <summary><h2 id="redeem-h">Have an officer token?</h2></summary>
  <p class="muted">A super admin may give you a token to help run the bank. Paste it here, or use <code>/bank redeem</code> in Discord.</p>
  <p class="notice" role="status" aria-live="polite">{message}</p>
  <form class="form" onsubmit={redeem}>
    <div class="field">
      <label for="redeem-token">Token</label>
      <input id="redeem-token" autocomplete="off" spellcheck="false" bind:value={token} disabled={busy} />
    </div>
    <p class="actions"><button class="btn primary" type="submit" disabled={busy || !token.trim()}>Redeem</button></p>
  </form>
</details>

<style>
  .redeem { display: grid; gap: 0.75rem; }
  .redeem summary { cursor: pointer; }
  .redeem h2 { display: inline; font-size: 1.1rem; margin: 0; }
  .notice:empty { display: none; }
  .form { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); align-items: end; }
  .actions { display: flex; gap: 0.5rem; margin: 0; }
</style>
