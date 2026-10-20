<script lang="ts">
  import {
    byMember,
    grantLabel,
    grantPhrase,
    holds,
    officerGrantError,
    type DiscordMember,
    type OfficerGrant,
    type OfficerGrantBackend,
    type OfficerGrants
  } from '$lib/officer-grants';

  // The super admins' officer desk (docs/admin.md "Officer grants"): make one member of the Toads Discord an officer
  // of a raid night, or of every night, on top of their Discord roles. Super admin is never on offer: that is the
  // hub's configuration alone. The API checks the permission (manage_officer_grants); this desk only shows itself.
  let { backend }: { backend: OfficerGrantBackend } = $props();

  // "" picks every night, a global officer.
  const EVERY = '';

  let data = $state<OfficerGrants | null>(null);
  let loadError = $state('');
  let query = $state('');
  let found = $state<DiscordMember[]>([]);
  let searched = $state('');
  let searching = $state(false);
  let picked = $state<DiscordMember | null>(null);
  let night = $state(EVERY);
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  const days = $derived(data?.raid_days ?? []);
  const members = $derived(byMember(data?.grants ?? []));
  const scope = $derived(night === EVERY ? null : night);
  const alreadyHeld = $derived(!!picked && holds(data?.grants ?? [], picked.discord_user_id, scope));

  async function load() {
    try {
      data = await backend.load();
      loadError = '';
    } catch (e) {
      loadError = officerGrantError(e);
    }
  }
  $effect(() => {
    load();
  });

  async function search(event: SubmitEvent) {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;
    searching = true;
    try {
      found = await backend.search(q);
      searched = q;
      message = '';
    } catch (e) {
      message = officerGrantError(e);
      failed = true;
    } finally {
      searching = false;
    }
  }

  async function change(action: () => Promise<unknown>, done: string) {
    busy = true;
    try {
      await action();
      message = done;
      failed = false;
      await load();
    } catch (e) {
      message = officerGrantError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }

  async function grant(event: SubmitEvent) {
    event.preventDefault();
    const who = picked;
    if (!who || alreadyHeld) return;
    const what = grantPhrase(scope, days);
    await change(() => backend.grant(who.discord_user_id, scope), `${who.display_name} is now ${what}.`);
    if (!failed) [picked, query, found, searched] = [null, '', [], ''];
  }

  const revoke = (g: OfficerGrant) =>
    change(
      () => backend.revoke(g.id),
      `${g.display_name} is no longer ${grantPhrase(g.raid_day, days)} by grant.`
    );
</script>

<section class="card desk" aria-labelledby="officer-grants-h">
  <h2 id="officer-grants-h">Officer grants</h2>
  <p class="muted lede">
    Make someone an officer without a Discord role: for one raid night, or for every night as a global officer. It adds
    to their Discord roles and takes effect on their next click. Super admin is set in the hub's configuration only.
  </p>

  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
  {:else if !data}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if members.length}
      <ul class="people">
        {#each members as m (m.member.discord_user_id)}
          <li>
            <span class="who"><strong>{m.member.display_name}</strong> <span class="muted">@{m.member.username}</span></span>
            <ul class="grants">
              {#each m.grants as g (g.id)}
                <li>
                  <span class="chip" class:global={g.raid_day === null}>{grantLabel(g.raid_day, days)}</span>
                  <span class="muted when">{g.granted_by_name ? `by ${g.granted_by_name}` : ''}</span>
                  <button type="button" class="btn small" disabled={busy} onclick={() => revoke(g)}>
                    Revoke<span class="sr-only"> {grantLabel(g.raid_day, days)} from {g.display_name}</span>
                  </button>
                </li>
              {/each}
            </ul>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="muted">Nobody holds an officer grant. Officers come from their Discord roles.</p>
    {/if}

    {#if picked}
      <form class="give" onsubmit={grant}>
        <p class="picked">
          <strong>{picked.display_name}</strong> <span class="muted">@{picked.username}</span>
          <button type="button" class="btn small" disabled={busy} onclick={() => (picked = null)}>Change</button>
        </p>
        <div class="field">
          <label for="officer-grant-night">Officer of</label>
          <select id="officer-grant-night" bind:value={night} disabled={busy}>
            <option value={EVERY}>Every night (global officer)</option>
            {#each days as d (d.id)}<option value={d.id}>{d.name}</option>{/each}
          </select>
        </div>
        <button class="btn primary" type="submit" disabled={busy || alreadyHeld}>Grant officer powers</button>
        {#if alreadyHeld}<span class="hint muted">They already hold this grant.</span>{/if}
      </form>
    {:else}
      <form class="find" onsubmit={search}>
        <div class="field">
          <label for="officer-grant-q">Find someone in the Toads Discord</label>
          <input
            id="officer-grant-q"
            type="search"
            maxlength="32"
            autocomplete="off"
            spellcheck="false"
            placeholder="Username or nickname"
            bind:value={query}
          />
        </div>
        <button class="btn" type="submit" disabled={searching || !query.trim()} aria-busy={searching}>
          {searching ? 'Searching…' : 'Find'}
        </button>
      </form>
      {#if searched}
        {#if found.length}
          <ul class="people found" aria-label="Discord members matching {searched}">
            {#each found as who (who.discord_user_id)}
              <li>
                <span class="who"><strong>{who.display_name}</strong> <span class="muted">@{who.username}</span></span>
                <button type="button" class="btn primary" onclick={() => (picked = who)}>
                  Choose<span class="sr-only"> {who.display_name}</span>
                </button>
              </li>
            {/each}
          </ul>
        {:else}
          <p class="muted">Nobody in the Toads Discord has a name starting “{searched}”.</p>
        {/if}
      {/if}
    {/if}
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
  {/if}
</section>

<style>
  .desk { display: grid; gap: 0.75rem; align-content: start; }
  .desk h2, .desk p { margin: 0; }
  .lede { max-width: 62ch; }
  .people, .grants { list-style: none; margin: 0; padding: 0; display: grid; }
  .people > li {
    display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.75rem; padding: 0.5rem 0;
    border-bottom: 1px solid var(--line);
  }
  .who { flex: 1 1 10rem; min-width: 0; overflow-wrap: anywhere; }
  .grants { gap: 0.35rem; }
  .grants li { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
  .chip {
    padding: 0.1rem 0.55rem; border: 1px solid var(--line); border-radius: 999px; font-size: 0.85rem;
    background: var(--bg);
  }
  .chip.global { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, var(--bg)); }
  .when { font-size: 0.85rem; }
  .find, .give { display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; align-items: flex-end; }
  .find .field { flex: 1 1 14rem; }
  .give .field { flex: 0 1 16rem; }
  .picked { flex: 1 0 100%; display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
  .hint { flex-basis: 100%; }
</style>
