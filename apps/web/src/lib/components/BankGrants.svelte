<script lang="ts">
  import { onMount } from 'svelte';
  import {
    bankError,
    bankTime,
    GRANT_LABELS,
    grantBank,
    grantScope,
    grantsText,
    isDiscordId,
    listGrants,
    listTokens,
    mintToken,
    revokeGrant,
    revokeToken,
    TOKEN_STATUS_LABELS,
    type BankGrant,
    type BankToken,
    type GrantPermission,
    type MintedToken
  } from '$lib/bank';

  // docs/admin.md. The global tier sees who else runs the bank; super admins (named in the hub's configuration) grant
  // and revoke it, directly or through officer tokens a member redeems. Officers hold both permissions through their
  // role already. A revoke takes effect on the member's next call.
  let {
    days,
    manage = false,
    breakGlass = false,
    breakGlassAdmin = null
  }: { days: string[]; manage?: boolean; breakGlass?: boolean; breakGlassAdmin?: string | null } = $props();

  let grants = $state<BankGrant[]>([]);
  let tokens = $state<BankToken[]>([]);
  let message = $state('');
  let busy = $state(false);
  let userId = $state('');
  let permission = $state<GrantPermission>('import_bank_snapshot');
  let day = $state('');

  // The mint form, and the token just minted: shown here once, never again.
  let mintImport = $state(true);
  let mintManage = $state(false);
  let mintDay = $state('');
  let mintDays = $state(7);
  let mintUses = $state(1);
  let mintNote = $state('');
  let minted = $state<MintedToken | null>(null);
  let copied = $state('');

  async function load() {
    try {
      grants = await listGrants();
      if (manage) tokens = await listTokens();
    } catch (e) {
      message = bankError(e);
    }
  }

  async function mint(event: SubmitEvent) {
    event.preventDefault();
    const permissions: GrantPermission[] = [];
    if (mintImport) permissions.push('import_bank_snapshot');
    if (mintManage) permissions.push('manage_bank');
    if (!permissions.length) {
      message = 'Pick at least one thing the token lets its holder do.';
      return;
    }
    busy = true;
    message = '';
    copied = '';
    try {
      minted = await mintToken({
        permissions,
        raid_day: mintDay || null,
        days: mintDays,
        max_uses: mintUses,
        note: mintNote.trim()
      });
      mintNote = '';
      await load();
    } catch (e) {
      message = bankError(e);
    } finally {
      busy = false;
    }
  }

  async function copy() {
    if (!minted) return;
    try {
      await navigator.clipboard.writeText(minted.token);
      copied = 'Copied.';
    } catch {
      copied = 'Copy it by hand: your browser would not let the page copy it.';
    }
  }

  async function revokeT(t: BankToken) {
    busy = true;
    message = '';
    try {
      await revokeToken(t.id);
      message = `Token ${t.id} revoked. Grants already given from it stay until you revoke them above.`;
      if (minted?.id === t.id) minted = null;
      await load();
    } catch (e) {
      message = bankError(e);
    } finally {
      busy = false;
    }
  }

  onMount(load);

  async function grant(event: SubmitEvent) {
    event.preventDefault();
    if (!isDiscordId(userId)) {
      message = 'Give the member’s Discord user id: the digits from Copy User ID in Discord.';
      return;
    }
    busy = true;
    message = '';
    try {
      const made = await grantBank({ discord_user_id: userId.trim(), permission, raid_day: day || null });
      message = `${made.display_name} may now ${GRANT_LABELS[made.permission].toLowerCase()} on ${grantScope(made.raid_day)}.`;
      userId = '';
      await load();
    } catch (e) {
      message = bankError(e);
    } finally {
      busy = false;
    }
  }

  async function revoke(g: BankGrant) {
    busy = true;
    message = '';
    try {
      await revokeGrant(g.id);
      message = `${g.display_name} may no longer ${GRANT_LABELS[g.permission].toLowerCase()} on ${grantScope(g.raid_day)}.`;
      await load();
    } catch (e) {
      message = bankError(e);
    } finally {
      busy = false;
    }
  }
</script>

<section class="card" aria-labelledby="grants-h">
  <h2 id="grants-h">{manage ? 'Super admins' : 'Global officers'}: who else runs the bank</h2>
  {#if breakGlass}
    <p class="glass" role="note">
      <strong>You are signed in as the break-glass admin.</strong> You hold every power here whatever your Discord roles,
      and every change you make is on the audit log marked “break_glass”.
    </p>
  {:else if breakGlassAdmin}
    <p class="glass" role="note">
      Break-glass admin: Discord user <code>{breakGlassAdmin}</code> is always a super admin (set in the hub’s
      configuration), and every change they make is on the audit log marked “break_glass”.
    </p>
  {/if}
  <p class="muted">
    Officers import snapshots and run the request queue for their raid day already.
    {#if manage}
      Grant either to another member, for one raid day’s banks or for every bank, or mint a token they redeem themselves.
    {:else}
      Only super admins grant these or mint officer tokens.
    {/if}
  </p>
  <p class="notice" role="status" aria-live="polite">{message}</p>

  {#if grants.length === 0}
    <p class="muted">No one else holds a bank grant.</p>
  {:else}
    <div class="scroll">
      <table>
        <thead>
          <tr><th scope="col">Member</th><th scope="col">May</th><th scope="col">On</th><th scope="col">Granted</th><th scope="col"><span class="sr-only">Actions</span></th></tr>
        </thead>
        <tbody>
          {#each grants as g (g.id)}
            <tr>
              <td>{g.display_name} <span class="muted">({g.discord_user_id})</span></td>
              <td>{GRANT_LABELS[g.permission] ?? g.permission}</td>
              <td>{grantScope(g.raid_day)}</td>
              <td class="muted">{bankTime(Date.parse(g.granted_at) / 1000)}{g.granted_by_name ? ` by ${g.granted_by_name}` : ''}</td>
              <td>
                {#if manage}
                  <button class="btn small danger" type="button" disabled={busy} onclick={() => revoke(g)}>Revoke<span class="sr-only"> {GRANT_LABELS[g.permission]} from {g.display_name}</span></button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  {#if manage}
  <form class="form" onsubmit={grant}>
    <div class="field">
      <label for="grant-user">Discord user id</label>
      <input id="grant-user" inputmode="numeric" autocomplete="off" bind:value={userId} disabled={busy} />
    </div>
    <div class="field">
      <label for="grant-permission">May</label>
      <select id="grant-permission" bind:value={permission} disabled={busy}>
        <option value="import_bank_snapshot">{GRANT_LABELS.import_bank_snapshot}</option>
        <option value="manage_bank">{GRANT_LABELS.manage_bank}</option>
      </select>
    </div>
    <div class="field">
      <label for="grant-day">On</label>
      <select id="grant-day" bind:value={day} disabled={busy}>
        <option value="">Every bank</option>
        {#each days as d (d)}<option value={d}>{d} banks</option>{/each}
      </select>
    </div>
    <p class="actions"><button class="btn primary" type="submit" disabled={busy || !userId.trim()}>Grant</button></p>
  </form>

  <h3 id="tokens-h">Officer tokens</h3>
  <p class="muted">
    A token gives whoever redeems it (on this page or with <code>/bank redeem</code> in Discord) what it names. It is
    shown once, when you mint it; the hub keeps only its hash.
  </p>
  <form class="form" onsubmit={mint} aria-labelledby="tokens-h">
    <fieldset class="field">
      <legend>Lets them</legend>
      <label><input type="checkbox" bind:checked={mintImport} disabled={busy} /> {GRANT_LABELS.import_bank_snapshot}</label>
      <label><input type="checkbox" bind:checked={mintManage} disabled={busy} /> {GRANT_LABELS.manage_bank}</label>
    </fieldset>
    <div class="field">
      <label for="mint-day">On</label>
      <select id="mint-day" bind:value={mintDay} disabled={busy}>
        <option value="">Every bank</option>
        {#each days as d (d)}<option value={d}>{d} banks</option>{/each}
      </select>
    </div>
    <div class="field">
      <label for="mint-days">Lasts (days)</label>
      <input id="mint-days" type="number" min="1" max="30" bind:value={mintDays} disabled={busy} />
    </div>
    <div class="field">
      <label for="mint-uses">Uses</label>
      <input id="mint-uses" type="number" min="1" max="25" bind:value={mintUses} disabled={busy} />
    </div>
    <div class="field">
      <label for="mint-note">Note (who it is for)</label>
      <input id="mint-note" maxlength="100" autocomplete="off" bind:value={mintNote} disabled={busy} />
    </div>
    <p class="actions"><button class="btn primary" type="submit" disabled={busy}>Mint token</button></p>
  </form>

  {#if minted}
    <div class="minted" role="status">
      <p><strong>Copy this token now: it will not be shown again.</strong> {grantsText(minted.permissions, minted.raid_day)}, until {bankTime(Date.parse(minted.expires_at) / 1000)}.</p>
      <p class="token"><code>{minted.token}</code></p>
      <p class="actions">
        <button class="btn small" type="button" onclick={copy}>Copy</button>
        <button class="btn small" type="button" onclick={() => (minted = null)}>Done</button>
        <span class="muted" aria-live="polite">{copied}</span>
      </p>
    </div>
  {/if}

  {#if tokens.length}
    <div class="scroll">
      <table>
        <thead>
          <tr><th scope="col">Token</th><th scope="col">Gives</th><th scope="col">Minted</th><th scope="col">Status</th><th scope="col"><span class="sr-only">Actions</span></th></tr>
        </thead>
        <tbody>
          {#each tokens as t (t.id)}
            <tr>
              <td>#{t.id}{t.note ? ` ${t.note}` : ''}</td>
              <td>{grantsText(t.permissions, t.raid_day)}</td>
              <td class="muted">{bankTime(Date.parse(t.minted_at) / 1000)}{t.minted_by_name ? ` by ${t.minted_by_name}` : ''}</td>
              <td>
                {TOKEN_STATUS_LABELS[t.status] ?? t.status}
                <span class="muted">({t.uses}/{t.max_uses}{t.used_by ? `, last by ${t.used_by}` : ''}; expires {bankTime(Date.parse(t.expires_at) / 1000)})</span>
              </td>
              <td>
                {#if t.status === 'active'}
                  <button class="btn small danger" type="button" disabled={busy} onclick={() => revokeT(t)}>Revoke<span class="sr-only"> token {t.id}</span></button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <p class="muted">No officer tokens yet.</p>
  {/if}
  {/if}
</section>

<style>
  /* Screen-reader-only text is absolutely positioned: keep it inside the table's scroll box. */
  .scroll { position: relative; }
  .notice:empty { display: none; }
  .form { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr)); align-items: end; margin-top: 0.75rem; }
  .actions { display: flex; gap: 0.5rem; margin: 0; align-items: center; flex-wrap: wrap; }
  .glass { padding: 0.75rem; border: 1px solid var(--warn); border-radius: 6px; }
  .minted { margin: 0.75rem 0; padding: 0.75rem; border: 1px solid var(--warn); border-radius: 6px; }
  .token code { overflow-wrap: anywhere; user-select: all; }
  fieldset.field { border: 0; padding: 0; margin: 0; display: grid; gap: 0.25rem; }
</style>
