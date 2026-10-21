<script lang="ts">
  import { absenceError, nightLabel, type AbsencesBackend } from '$lib/absences';
  import type { CompBackend } from '$lib/comp';
  import {
    LINK_LABEL_LIMIT,
    LINK_URL_LIMIT,
    linkHost,
    linkProblem,
    linksError,
    type LinksBackend,
    type NightLink
  } from '$lib/night-links';
  import { tonight, type Tonight } from '$lib/tonight';

  // The top of a raid night's officer section, for the ten minutes before invites: the next night, who will miss it
  // with the role they play, and the night's pinned strategy and role documents (kept in Google Drive, linked here).
  let {
    day,
    name,
    absences,
    comps,
    links
  }: { day: string; name: string; absences: AbsencesBackend; comps: CompBackend; links: LinksBackend } = $props();

  let next = $state<Tonight | null | undefined>(undefined);
  let awayError = $state('');
  let pinned = $state<NightLink[] | null>(null);
  let linkError = $state('');
  let label = $state('');
  let url = $state('');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  const ROLE_PLURAL = { tank: 'tank', healer: 'healer', melee: 'melee', ranged: 'ranged' } as const;

  $effect(() => {
    const d = day;
    // The roster only adds specs; without it the away list still reads.
    Promise.all([absences.team(d), comps.pool(d).catch(() => [])]).then(
      ([team, pool]) => (next = tonight(team, pool)),
      (e) => ((awayError = absenceError(e)), (next = null))
    );
    links.links(d).then(
      (l) => (pinned = l),
      (e) => (linkError = linksError(e))
    );
  });

  async function pin(event: SubmitEvent) {
    event.preventDefault();
    const problem = linkProblem(label, url);
    if (problem) {
      [message, failed] = [problem, true];
      return;
    }
    busy = true;
    try {
      const link = await links.pin(day, label, url);
      pinned = [...(pinned ?? []), link];
      [label, url] = ['', ''];
      [message, failed] = [`Pinned “${link.label}”.`, false];
    } catch (e) {
      [message, failed] = [linksError(e), true];
    } finally {
      busy = false;
    }
  }

  async function unpin(link: NightLink) {
    busy = true;
    try {
      await links.unpin(day, link.id);
      pinned = (pinned ?? []).filter((x) => x.id !== link.id);
      [message, failed] = [`Unpinned “${link.label}”.`, false];
    } catch (e) {
      [message, failed] = [linksError(e), true];
    } finally {
      busy = false;
    }
  }

</script>

<section class="band tonight" aria-labelledby="tonight-h">
  <div class="head">
    {#if next}
      <h2 id="tonight-h">Next {name}: {nightLabel(next.date)}</h2>
      <p>
        {#if next.away.length}
          {next.away.length}{next.roster ? ` of ${next.roster}` : ''} away{#if next.short.length}, so short
            {next.short.map((s) => `${s.count} ${ROLE_PLURAL[s.role]}`).join(', ')}{/if}.
        {:else}
          Everyone on the roster is expected.
        {/if}
      </p>
    {:else}
      <h2 id="tonight-h">Next {name}</h2>
    {/if}
  </div>

  <div class="cols">
    <div class="card" aria-labelledby="tonight-away-h" role="group">
      <h3 id="tonight-away-h">Who is away</h3>
      {#if next === undefined}
        <p class="muted" role="status">Loading…</p>
      {:else if awayError}
        <p class="err" role="alert">{awayError}</p>
      {:else if !next}
        <p class="muted">No {name} nights ahead in the calendar.</p>
      {:else if !next.away.length}
        <p class="muted">Nobody has said they will miss it.</p>
      {:else}
        <ul class="away">
          {#each next.away as a, i (i)}
            <li>
              <strong>{a.name}</strong>
              {#if a.spec}<span class="spec">{a.spec}</span>{:else}<span class="muted small">no specs set</span>{/if}
              {#if a.note}<span class="note">{a.note}</span>{/if}
            </li>
          {/each}
        </ul>
      {/if}
    </div>

    <div class="card" aria-labelledby="tonight-links-h" role="group">
      <h3 id="tonight-links-h">Strategy and roles</h3>
      {#if linkError}
        <p class="err" role="alert">{linkError}</p>
      {:else if pinned === null}
        <p class="muted" role="status">Loading…</p>
      {:else if !pinned.length}
        <p class="muted">
          Pin the night’s strategy doc and role sheet from Google Drive, so every {name} officer has them in one place.
        </p>
      {:else}
        <ul class="links">
          {#each pinned as link (link.id)}
            <li>
              <a href={link.url} rel="external noopener noreferrer" target="_blank">{link.label}</a>
              <span class="muted small">{linkHost(link.url)}</span>
              <button type="button" class="btn small" disabled={busy} onclick={() => unpin(link)}>
                Unpin<span class="sr-only"> {link.label}</span>
              </button>
            </li>
          {/each}
        </ul>
      {/if}
      <form class="pin" onsubmit={pin}>
        <div class="field">
          <label for="link-label-{day}">Name</label>
          <input id="link-label-{day}" maxlength={LINK_LABEL_LIMIT} placeholder="Kael’thas strategy" bind:value={label} />
        </div>
        <div class="field grow">
          <label for="link-url-{day}">Link</label>
          <input
            id="link-url-{day}"
            type="url"
            inputmode="url"
            maxlength={LINK_URL_LIMIT}
            placeholder="https://docs.google.com/…"
            bind:value={url}
          />
        </div>
        <button class="btn primary" type="submit" disabled={busy || !label.trim() || !url.trim()}>Pin link</button>
      </form>
      {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
    </div>
  </div>
</section>

<style>
  .cols { display: grid; gap: 1rem; grid-template-columns: minmax(0, 1fr); }
  @media (min-width: 52rem) { .cols { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); align-items: start; } }
  .card { display: grid; gap: 0.75rem; padding: 1.25rem; }
  .card p { margin: 0; }
  .away, .links { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; }
  .away li { display: flex; flex-wrap: wrap; gap: 0.25rem 0.6rem; align-items: baseline; }
  .spec { color: var(--bronze-hi); }
  .note { flex-basis: 100%; color: var(--muted); font-size: 0.95rem; }
  .links li { display: flex; flex-wrap: wrap; align-items: center; gap: 0.25rem 0.75rem; }
  .links a { font-weight: 700; }
  .links button { margin-left: auto; }
  .pin { display: flex; flex-wrap: wrap; gap: 0.5rem 0.75rem; align-items: end; }
  .field { display: grid; gap: 0.25rem; min-width: 0; }
  .field.grow { flex: 1 1 14rem; }
  .field label { color: var(--muted); font-size: 0.9rem; }
  input { background: var(--bg); color: var(--text); border: 1px solid var(--line); border-radius: 6px; padding: 0.5rem; font: inherit; }
  .small { font-size: 0.85rem; }
  .links .btn { padding: 0.3rem 0.65rem; font-size: 0.85rem; }
</style>
