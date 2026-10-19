<script lang="ts">
  import { absenceError, nightLabel, rangeLabel, type AbsencesBackend, type TeamAbsences } from '$lib/absences';

  // A raid day's upcoming nights and who has said they will miss each one, for that day's officers. The API refuses
  // anyone else (view_absences on the day in the path); pages only show this to officers.
  // `heading` false leaves the title to the surrounding section (the Calendar's own "Team absences").
  // `version` changes when the page knows the list changed (the viewer reported or cancelled one), to read it again.
  let {
    backend,
    day,
    name,
    heading = true,
    version = 0
  }: { backend: AbsencesBackend; day: string; name: string; heading?: boolean; version?: number } = $props();

  let team = $state<TeamAbsences | null>(null);
  let error = $state('');
  // Each read's number: only the latest one's answer is shown, so an earlier read finishing late never undoes it.
  let latest = 0;

  $effect(() => {
    const d = day;
    void version;
    const read = ++latest;
    team = null;
    error = '';
    backend.team(d).then(
      (t) => {
        if (read === latest) team = t;
      },
      (e) => {
        if (read === latest) error = absenceError(e);
      }
    );
  });

  // Absences still running after the last night shown, including ones that started within it.
  const lastShown = $derived(team?.nights.at(-1)?.date ?? '');
  const later = $derived(
    team
      ? team.absences.filter(
          (a) => a.nights.some((n) => n > lastShown) || !team!.nights.some((n) => n.absent.some((x) => x.id === a.id))
        )
      : []
  );
</script>

<section class="team" aria-labelledby={heading ? `team-${day}-h` : undefined} aria-label={heading ? undefined : `${name} absences`}>
  {#if heading}<h3 id="team-{day}-h">{name} absences</h3>{/if}
  {#if error}
    <p class="err" role="alert">{error}</p>
  {:else if !team}
    <p class="muted" role="status">Loading…</p>
  {:else if !team.nights.length && !team.absences.length}
    <p class="muted">Nobody has reported an absence for {name}.</p>
  {:else}
    {#if team.nights.length}
      <ol class="nights">
        {#each team.nights as n (n.date)}
          <li class:clear={!n.absent.length}>
            <span class="date"><time datetime={n.date}>{nightLabel(n.date)}</time></span>
            <span class="count" aria-label="{n.absent.length} away">{n.absent.length || '–'}</span>
            {#if n.absent.length}
              <ul class="who">
                {#each n.absent as a (a.id)}
                  <li><strong>{a.member_name || 'A member'}</strong>{#if a.note}<span class="note">{a.note}</span>{/if}</li>
                {/each}
              </ul>
            {:else}
              <span class="muted">Everyone expected</span>
            {/if}
          </li>
        {/each}
      </ol>
    {/if}
    {#if later.length}
      <h4>Further ahead</h4>
      <ul class="later">
        {#each later as a (a.id)}
          <li><strong>{a.member_name || 'A member'}</strong> {rangeLabel(a)}{#if a.note}<span class="note">{a.note}</span>{/if}</li>
        {/each}
      </ul>
    {/if}
  {/if}
</section>

<style>
  .team { display: grid; gap: 0.75rem; }
  h3 { font-size: 1.15rem; margin: 0; }
  h4 { margin: 0.5rem 0 0; font-size: 1rem; color: var(--muted); font-weight: 500; }
  .nights, .later, .who { list-style: none; margin: 0; padding: 0; }
  .nights > li {
    display: grid;
    grid-template-columns: 7.5rem 2.25rem minmax(0, 1fr);
    gap: 0.75rem;
    align-items: baseline;
    padding: 0.6rem 0;
    border-top: 1px solid var(--line);
  }
  .nights > li:last-child { border-bottom: 1px solid var(--line); }
  .date { font-variant-numeric: tabular-nums; }
  .count {
    font-variant-numeric: tabular-nums;
    font-weight: 700;
    color: var(--bronze-hi);
    text-align: center;
  }
  .clear .count { color: var(--muted); font-weight: 400; }
  .who { display: grid; gap: 0.25rem; }
  .note { display: block; color: var(--muted); font-size: 0.92em; }
  .later { display: grid; gap: 0.4rem; }
  @media (max-width: 30rem) {
    .nights > li { grid-template-columns: 6.5rem 1.75rem minmax(0, 1fr); gap: 0.5rem; }
  }
</style>
