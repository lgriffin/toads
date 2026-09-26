<script lang="ts">
  import { base } from '$app/paths';
  import { PROVIDER_LABELS } from '$lib/clips';
  import { isOfficer, visibleHighlights } from '$lib/community';
  import ClipPlayer from '$lib/components/ClipPlayer.svelte';
  import PostCard from '$lib/components/PostCard.svelte';
  import SpotlightCard from '$lib/components/SpotlightCard.svelte';
  import { dateTime, shortDate } from '$lib/format';
  import { viewer } from '$lib/mock/community';
  import { nextRaid, raids, type Role } from '$lib/mock/data';
  import { visibleFeed } from '$lib/posts';
  import { isFinal } from '$lib/recruitment';
  import { community } from './state.svelte';

  const roles: Role[] = ['Tank', 'Healer', 'Melee', 'Ranged'];
  const latest = raids.slice(0, 3);
  const officer = isOfficer(viewer);

  const feed = $derived(visibleFeed(community.posts, viewer));
  const mySpotlights = $derived(community.spotlights.filter((s) => s.memberName === viewer.name));
  const askingConsent = $derived(mySpotlights.filter((s) => s.consent === 'pending'));
  const recent = $derived(visibleHighlights(community.highlights, viewer).slice(0, 2));
  let consentNote = $state('');

  const desk = $derived([
    {
      label: 'Applications waiting',
      count: community.applications.filter((a) => !isFinal(a.status)).length,
      href: '#applications'
    },
    {
      label: 'Discord posts to curate',
      count: community.posts.filter((p) => p.status === 'pending_review').length,
      href: '#curation'
    },
    {
      label: 'Highlight submissions',
      count: community.highlights.filter((h) => h.status === 'submitted').length,
      href: '#highlights'
    },
    {
      label: 'Spotlights awaiting consent',
      count: community.spotlights.filter((s) => s.consent === 'pending').length,
      href: '#spotlights'
    }
  ]);
  const gaps = roles.filter((r) => nextRaid.signups[r] < nextRaid.needed[r]);

  function decide(id: string, consent: 'granted' | 'declined') {
    const s = community.spotlights.find((x) => x.id === id);
    if (!s) return;
    s.consent = consent;
    consentNote =
      consent === 'granted'
        ? 'Thanks! Officers can now publish your spotlight. You can revoke this on your Me page at any time.'
        : 'Declined. Your spotlight will not be published.';
  }
</script>

<h1>Your night, {viewer.name}</h1>

<div class="grid">
  <section class="card" aria-labelledby="next-h">
    <h2 id="next-h">Next raid</h2>
    <p class="big">{nextRaid.zone}</p>
    <p class="muted">{nextRaid.raidDay} team · {dateTime(nextRaid.start)} server time</p>
    <table>
      <thead><tr><th>Role</th><th class="num">Signed</th><th class="num">Needed</th></tr></thead>
      <tbody>
        {#each roles as role}
          {@const short = nextRaid.signups[role] < nextRaid.needed[role]}
          <tr>
            <td>{role}</td>
            <td class="num" class:warn={short}>{nextRaid.signups[role]}</td>
            <td class="num">{nextRaid.needed[role]}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>

  {#if askingConsent.length || consentNote}
    <section class="card consent" aria-labelledby="consent-h">
      <h2 id="consent-h">Spotlight about you</h2>
      {#each askingConsent as s (s.id)}
        <p>{s.writtenBy} wrote a spotlight about {s.characterName}. It is only published if you agree.</p>
        <div class="quote"><SpotlightCard spotlight={s} /></div>
        <div class="actions">
          <button class="btn primary" type="button" onclick={() => decide(s.id, 'granted')}>Grant</button>
          <button class="btn" type="button" onclick={() => decide(s.id, 'declined')}>Decline</button>
        </div>
      {/each}
      {#if consentNote}<p role="status">{consentNote}</p>{/if}
    </section>
  {/if}

  {#if officer}
    <section class="card" aria-labelledby="desk-h">
      <h2 id="desk-h">Raid leader desk</h2>
      <ul class="desk">
        {#each desk as d}
          <li>
            <a href="{base}/officers/{d.href}"><span class="n">{d.count}</span> {d.label}</a>
          </li>
        {/each}
      </ul>
      <p class="muted small">
        Next raid role gaps:
        {#if gaps.length}
          {gaps.map((r) => `${r} ${nextRaid.needed[r] - nextRaid.signups[r]}`).join(', ')}
        {:else}none{/if}
      </p>
    </section>
  {/if}

  <section class="card" aria-labelledby="logs-h">
    <h2 id="logs-h">Latest logs</h2>
    <ul class="list">
      {#each latest as raid}
        {@const kills = raid.bosses.filter((b) => b.killed).length}
        <li>
          <a href="{base}/raids/{raid.id}/">{raid.zone}</a>
          <span class="muted">{shortDate(raid.date)} · {raid.raidDay} · {kills}/{raid.bosses.length} bosses</span>
        </li>
      {/each}
    </ul>
    <a href="{base}/raids/">All raids</a>
  </section>
</div>

<div class="grid lower">
  <section class="card feed" aria-labelledby="feed-h">
    <h2 id="feed-h">Posts</h2>
    {#each feed as p (p.id)}
      <PostCard post={p} badges />
    {:else}
      <p class="muted">Nothing posted yet.</p>
    {/each}
  </section>

  <section class="card" aria-labelledby="hl-h">
    <h2 id="hl-h">Recent highlights</h2>
    <div class="clips">
      {#each recent as h (h.id)}
        <ClipPlayer
          provider={h.provider}
          clipId={h.clipId}
          title={h.title}
          meta="{h.visibility === 'guild' ? 'Guild only · ' : ''}{PROVIDER_LABELS[h.provider]}"
        />
      {/each}
    </div>
    <a href="{base}/highlights/">All highlights</a>
  </section>
</div>

<style>
  .big { font-size: 1.3rem; margin: 0; }
  .list { list-style: none; padding: 0; margin: 0 0 0.75rem; }
  .list li { display: flex; flex-direction: column; padding: 0.5rem 0; border-bottom: 1px solid var(--line); }
  .lower { margin-top: 1rem; }
  .desk { list-style: none; margin: 0 0 0.5rem; padding: 0; display: grid; gap: 0.35rem; }
  .desk a { display: flex; gap: 0.6rem; align-items: baseline; }
  .n { font-size: 1.3rem; min-width: 1.5rem; text-align: right; font-variant-numeric: tabular-nums; }
  .consent { border-color: var(--accent); }
  .quote { border-left: 3px solid var(--line); padding-left: 0.75rem; margin: 0.5rem 0 0.75rem; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .clips { display: grid; gap: 1rem; margin-bottom: 0.75rem; }
  .small { font-size: 0.8rem; }
</style>
