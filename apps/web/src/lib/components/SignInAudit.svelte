<script lang="ts">
  import {
    dayLabel,
    quiet,
    signInError,
    sinceLabel,
    timeLabel,
    type SignInDay,
    type SignInsBackend
  } from '$lib/sign-ins';

  // One raid night's sign-in audit for its officers (or, with `day` null, the global tier's members on no raid night):
  // who signed in on the chosen day, a fortnight of daily counts to pick another day from, and when each member last
  // signed in. The API refuses anyone who is not that night's officer; pages only show this to them.
  let {
    backend,
    day,
    title,
    on,
    onpick
  }: {
    backend: SignInsBackend;
    day: string | null;
    title: string;
    on: string;
    onpick: (date: string) => void;
  } = $props();

  let view = $state<SignInDay | null>(null);
  let error = $state('');
  let showAll = $state(false);
  // Each read's number: only the latest one's answer is shown, so an earlier read finishing late never undoes it.
  let latest = 0;

  $effect(() => {
    const d = day;
    const date = on;
    const read = ++latest;
    error = '';
    backend.day(d, date).then(
      (v) => {
        if (read === latest) view = v;
      },
      (e) => {
        if (read === latest) {
          view = null;
          error = signInError(e);
        }
      }
    );
  });

  const id = $derived(`signins-${day ?? 'none'}`);
  const peak = $derived(Math.max(1, ...(view?.recent.map((r) => r.members) ?? [])));
  const signedToday = $derived(new Set(view?.sign_ins.map((s) => s.member_id) ?? []).size);
  // The roster folds after the first dozen, quiet members kept in view at the end.
  const FOLD = 12;
  const members = $derived(view ? (showAll ? view.members : view.members.slice(0, FOLD)) : []);
</script>

<section class="card audit" aria-labelledby="{id}-h">
  <h2 id="{id}-h">{title}</h2>
  {#if error}
    <p class="err" role="alert">{error}</p>
  {:else if !view}
    <p class="muted" role="status">Loading…</p>
  {:else}
    <div class="strip" role="group" aria-label="Members signed in each day, last 14 days">
      {#each [...view.recent].reverse() as r (r.date)}
        <button
          type="button"
          class="bar"
          class:on={r.date === view.date}
          aria-pressed={r.date === view.date}
          title="{dayLabel(r.date)}: {r.members} {r.members === 1 ? 'member' : 'members'}, {r.sign_ins} sign-ins"
          onclick={() => onpick(r.date)}
        >
          <span class="fill" style="block-size: {Math.round((r.members / peak) * 100)}%"></span>
          <span class="sr">{dayLabel(r.date)}: {r.members}</span>
        </button>
      {/each}
    </div>

    <h3>{dayLabel(view.date)}</h3>
    {#if view.sign_ins.length}
      <p class="muted summary">
        {signedToday} {signedToday === 1 ? 'member' : 'members'} signed in{#if view.sign_ins.length !== signedToday}, {view.sign_ins.length} sign-ins in all{/if}.
      </p>
      <ol class="day">
        {#each view.sign_ins as s, i (`${s.member_id}-${s.at}-${i}`)}
          <li><time datetime={s.at}>{timeLabel(s.at)}</time> <strong>{s.member_name}</strong></li>
        {/each}
      </ol>
    {:else}
      <p class="muted">Nobody signed in on this day.</p>
    {/if}

    <h3>Last sign-in</h3>
    {#if view.members.length}
      <table class="last">
        <thead><tr><th scope="col">Member</th><th scope="col">Last signed in</th></tr></thead>
        <tbody>
          {#each members as m (m.member_id)}
            <tr class:quiet={quiet(m.last_signed_in_at)}>
              <td>{m.member_name}</td>
              <td>
                {#if m.last_signed_in_at}
                  <time datetime={m.last_signed_in_at} title={new Date(m.last_signed_in_at).toLocaleString('en-GB')}
                    >{sinceLabel(m.last_signed_in_at)}</time
                  >
                {:else}Never{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
      {#if view.members.length > FOLD}
        <button type="button" class="btn link" onclick={() => (showAll = !showAll)}>
          {showAll ? 'Show fewer' : `Show all ${view.members.length}`}
        </button>
      {/if}
    {:else}
      <p class="muted">Nobody to show yet.</p>
    {/if}
  {/if}
</section>

<style>
  .audit { display: grid; gap: 0.6rem; align-content: start; }
  .audit h2, .audit h3, .audit p { margin: 0; }
  h3 { font-size: 1rem; margin-top: 0.4rem !important; }
  .strip { display: grid; grid-template-columns: repeat(14, 1fr); gap: 3px; block-size: 3rem; align-items: end; }
  .bar {
    position: relative; block-size: 100%; padding: 0; border: 1px solid transparent; border-radius: 3px;
    background: var(--surface-2, rgba(127, 127, 127, 0.12)); cursor: pointer; display: flex; align-items: flex-end;
  }
  .bar.on { border-color: var(--bronze-hi); }
  .bar:focus-visible { outline: 2px solid var(--bronze-hi); outline-offset: 1px; }
  .fill { inline-size: 100%; min-block-size: 2px; border-radius: 2px; background: var(--bronze, #b08d57); }
  .sr { position: absolute; inline-size: 1px; block-size: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
  .day { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.2rem; }
  .day time { font-variant-numeric: tabular-nums; color: var(--muted); margin-inline-end: 0.4rem; }
  .last { inline-size: 100%; border-collapse: collapse; }
  .last th, .last td { text-align: start; padding: 0.25rem 0.4rem 0.25rem 0; border-block-end: 1px solid var(--line, rgba(127, 127, 127, 0.2)); }
  .last th { font-weight: 600; font-size: 0.9rem; }
  .last tr.quiet td:last-child { color: var(--muted); font-style: italic; }
  .summary { font-size: 0.95rem; }
  .btn.link { justify-self: start; }
</style>
