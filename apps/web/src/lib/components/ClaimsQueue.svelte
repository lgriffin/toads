<script lang="ts">
  import { base } from '$app/paths';
  import { dayName } from '$lib/absences';
  import { REASON_LIMIT, claimsError, itemKey, type ClaimsBackend, type PanelItem } from '$lib/officer-claims';

  // One raid night's pending character claims and main swaps (a member asking to make an approved alt their main), or
  // (day null) those of members on no night, which only global officers and super admins decide. Approve in one press;
  // reject asks for the reason the member will read on Me. The API checks that the viewer runs this night; this card
  // only shows itself to them.
  // `decided` holds the keys (itemKey) of requests decided anywhere on the page, so one on two nights leaves both panels
  // at once; `ondecided` reports this panel's decisions to it.
  let {
    backend,
    day,
    title,
    names = {},
    decided = [],
    ondecided
  }: {
    backend: ClaimsBackend;
    day: string | null;
    title: string;
    names?: Record<string, string>;
    decided?: readonly string[];
    ondecided?: (key: string) => void;
  } = $props();

  const key = $derived(day ?? 'none');
  let loaded = $state<PanelItem[] | null>(null);
  const claims = $derived(loaded && loaded.filter((c) => !decided.includes(itemKey(c))));
  let loadError = $state('');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);
  let rejecting = $state<string | null>(null);
  let reason = $state('');

  // Only the newest load may set the list, so a slow reply never brings back a claim decided after it was asked for.
  let latest = 0;
  async function load() {
    const ask = ++latest;
    try {
      const [c, s] = await Promise.all([backend.queue(day), backend.swaps(day)]);
      const items: PanelItem[] = [
        ...c.map((x) => ({ ...x, kind: 'claim' as const })),
        ...s.map((x) => ({ ...x, kind: 'main' as const }))
      ];
      if (ask === latest) [loaded, loadError] = [items, ''];
    } catch (e) {
      if (ask === latest) loadError = claimsError(e);
    }
  }

  $effect(() => {
    load();
  });

  async function decide(c: PanelItem, action: () => Promise<unknown>, done: string) {
    busy = true;
    try {
      await action();
      latest++;
      loaded = (loaded ?? []).filter((x) => itemKey(x) !== itemKey(c));
      ondecided?.(itemKey(c));
      message = done;
      failed = false;
      rejecting = null;
      reason = '';
    } catch (e) {
      message = claimsError(e);
      failed = true;
      await load();
    } finally {
      busy = false;
    }
  }

  const approve = (c: PanelItem) =>
    c.kind === 'main'
      ? decide(c, () => backend.approveSwap(day, c.id), `${c.character_name} is now ${c.member_name}’s main.`)
      : decide(c, () => backend.approve(day, c.id), `${c.character_name} is now ${c.member_name}’s.`);

  function reject(event: SubmitEvent, c: PanelItem) {
    event.preventDefault();
    const why = reason.trim();
    if (!why) return;
    if (c.kind === 'main')
      decide(c, () => backend.rejectSwap(day, c.id, why), `Kept ${c.member_name}’s main; ${c.character_name} stays an alt.`);
    else decide(c, () => backend.reject(day, c.id, why), `Rejected ${c.member_name}’s claim on ${c.character_name}.`);
  }

  /** "Puddles’s claim on Toadstool" or "Mossy’s main swap to Mossfire", for screen readers. */
  const what = (c: PanelItem) =>
    c.kind === 'main' ? `${c.member_name}’s main swap to ${c.character_name}` : `${c.member_name}’s claim on ${c.character_name}`;

  /** The claimant's other nights, so officers know who else may decide it. */
  const others = (c: PanelItem) => c.nights.filter((n) => n !== day).map((n) => dayName(n, names));
</script>

<section class="card claims" aria-labelledby="claims-{key}-h">
  <h2 id="claims-{key}-h">{title}</h2>
  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
  {:else if !claims}
    <p class="muted" role="status">Loading…</p>
  {:else if !claims.length}
    <p class="muted">
      No claims are waiting. A claim lands here when a member claims a character that does not match their Discord
      nickname, and a main swap when a member asks to raid as one of their approved alts.
    </p>
  {:else}
    <ul class="queue">
      {#each claims as c (itemKey(c))}
        {@const k = itemKey(c)}
        <li>
          <div class="who">
            {#if c.kind === 'main'}
              <span><span class="tag">Main swap</span> <strong>{c.character_name}</strong></span>
              <span class="muted">
                {c.member_name} asks to raid as {c.character_name}{c.current_main ? ` instead of ${c.current_main}` : ''}{#if others(c).length}; also on {others(c).join(' and ')}{/if}
              </span>
            {:else}
              <strong>{c.character_name}</strong>
              <span class="muted">claimed by {c.member_name}{#if others(c).length}; also on {others(c).join(' and ')}{/if}</span>
            {/if}
          </div>
          <div class="actions">
            <button type="button" class="btn primary" disabled={busy} onclick={() => approve(c)}>
              Approve<span class="sr-only"> {what(c)}</span>
            </button>
            <button
              type="button"
              class="btn"
              disabled={busy}
              aria-expanded={rejecting === k}
              onclick={() => ((rejecting = rejecting === k ? null : k), (reason = ''))}
            >
              Reject<span class="sr-only"> {what(c)}</span>
            </button>
          </div>
          {#if rejecting === k}
            <form class="reason" onsubmit={(e) => reject(e, c)}>
              <div class="field">
                <label for="reject-{key}-{k}">Why? {c.member_name} reads this on Me</label>
                <input id="reject-{key}-{k}" maxlength={REASON_LIMIT} autocomplete="off" bind:value={reason} />
              </div>
              <button class="btn" type="submit" disabled={busy || !reason.trim()}>
                {c.kind === 'main' ? 'Reject main swap' : 'Reject claim'}
              </button>
            </form>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
  {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
  {#if day === null}
    <p class="muted small">
      These members hold no raid night’s Toad role in Discord. Give them one and their requests move to that night’s
      officers; <a href="{base}/admin/">role badges</a> on Admin tie a role to a night.
    </p>
  {/if}
</section>

<style>
  .claims { display: grid; gap: 0.75rem; align-content: start; }
  .claims h2, .claims p { margin: 0; }
  .queue { list-style: none; margin: 0; padding: 0; display: grid; }
  .queue li {
    display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.75rem; padding: 0.5rem 0;
    border-bottom: 1px solid var(--line);
  }
  .who { flex: 1 1 12rem; min-width: 0; display: grid; overflow-wrap: anywhere; }
  .actions { display: flex; gap: 0.5rem; }
  .reason { flex: 1 1 100%; display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; align-items: flex-end; }
  .reason .field { flex: 1 1 14rem; }
  .small { font-size: 0.9em; }
  .tag {
    display: inline-block; font-size: 0.8em; padding: 0 0.4rem; border: 1px solid var(--accent); border-radius: 4px;
    color: var(--accent); vertical-align: 0.1em;
  }
</style>
