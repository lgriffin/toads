<script lang="ts">
  import { base } from '$app/paths';
  import { dayName } from '$lib/absences';
  import { REASON_LIMIT, claimsError, type ClaimsBackend, type QueuedClaim } from '$lib/officer-claims';

  // One raid night's pending character claims, or (day null) the claims of members on no night, which only global
  // officers and super admins decide. Approve in one press; reject asks for the reason the member will read on Me. The
  // API checks that the viewer runs this night; this card only shows itself to them.
  let {
    backend,
    day,
    title,
    names = {}
  }: { backend: ClaimsBackend; day: string | null; title: string; names?: Record<string, string> } = $props();

  const key = $derived(day ?? 'none');
  let claims = $state<QueuedClaim[] | null>(null);
  let loadError = $state('');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);
  let rejecting = $state<number | null>(null);
  let reason = $state('');

  function load() {
    backend
      .queue(day)
      .then((c) => {
        claims = c;
        loadError = '';
      })
      .catch((e) => (loadError = claimsError(e)));
  }

  $effect(load);

  async function decide(c: QueuedClaim, action: () => Promise<unknown>, done: string) {
    busy = true;
    try {
      await action();
      claims = (claims ?? []).filter((x) => x.id !== c.id);
      message = done;
      failed = false;
      rejecting = null;
      reason = '';
    } catch (e) {
      message = claimsError(e);
      failed = true;
      load();
    } finally {
      busy = false;
    }
  }

  const approve = (c: QueuedClaim) =>
    decide(c, () => backend.approve(day, c.id), `${c.character_name} is now ${c.member_name}’s.`);

  function reject(event: SubmitEvent, c: QueuedClaim) {
    event.preventDefault();
    const why = reason.trim();
    if (!why) return;
    decide(c, () => backend.reject(day, c.id, why), `Rejected ${c.member_name}’s claim on ${c.character_name}.`);
  }

  /** The claimant's other nights, so officers know who else may decide it. */
  const others = (c: QueuedClaim) => c.nights.filter((n) => n !== day).map((n) => dayName(n, names));
</script>

<section class="card claims" aria-labelledby="claims-{key}-h">
  <h2 id="claims-{key}-h">{title}</h2>
  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
  {:else if !claims}
    <p class="muted" role="status">Loading…</p>
  {:else if !claims.length}
    <p class="muted">No claims are waiting. A claim lands here when a member claims a character that does not match their Discord nickname.</p>
  {:else}
    <ul class="queue">
      {#each claims as c (c.id)}
        <li>
          <div class="who">
            <strong>{c.character_name}</strong>
            <span class="muted">claimed by {c.member_name}{#if others(c).length}; also on {others(c).join(' and ')}{/if}</span>
          </div>
          <div class="actions">
            <button type="button" class="btn primary" disabled={busy} onclick={() => approve(c)}>
              Approve<span class="sr-only"> {c.member_name}’s claim on {c.character_name}</span>
            </button>
            <button
              type="button"
              class="btn"
              disabled={busy}
              aria-expanded={rejecting === c.id}
              onclick={() => ((rejecting = rejecting === c.id ? null : c.id), (reason = ''))}
            >
              Reject<span class="sr-only"> {c.member_name}’s claim on {c.character_name}</span>
            </button>
          </div>
          {#if rejecting === c.id}
            <form class="reason" onsubmit={(e) => reject(e, c)}>
              <div class="field">
                <label for="reject-{key}-{c.id}">Why? {c.member_name} reads this on Me</label>
                <input id="reject-{key}-{c.id}" maxlength={REASON_LIMIT} autocomplete="off" bind:value={reason} />
              </div>
              <button class="btn" type="submit" disabled={busy || !reason.trim()}>Reject claim</button>
            </form>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
  {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
  {#if day === null}
    <p class="muted small">
      These members hold no raid night’s Toad role in Discord. Give them one and their claims move to that night’s
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
</style>
