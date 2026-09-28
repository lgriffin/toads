<script lang="ts">
  import { base } from '$app/paths';
  import { PROVIDER_LABELS } from '$lib/clips';
  import { isOfficer, visibleHighlights } from '$lib/community';
  import AnalyzerWidget from '$lib/components/AnalyzerWidget.svelte';
  import ClipPlayer from '$lib/components/ClipPlayer.svelte';
  import DeskList from '$lib/components/DeskList.svelte';
  import HomeView from '$lib/components/HomeView.svelte';
  import NeedsList from '$lib/components/NeedsList.svelte';
  import NextRaidCard from '$lib/components/NextRaidCard.svelte';
  import PerformanceCard from '$lib/components/PerformanceCard.svelte';
  import PostCard from '$lib/components/PostCard.svelte';
  import ProgressBars from '$lib/components/ProgressBars.svelte';
  import RaidTotals from '$lib/components/RaidTotals.svelte';
  import SpotlightCard from '$lib/components/SpotlightCard.svelte';
  import { deskLines } from '$lib/community-api';
  import { catalogueTitle, defaultLayout, isAnalyzer, saved, type HomeWidget } from '$lib/home';
  import { widgetById } from '$lib/home-payload';
  import { analyzerPage } from '$lib/mock/analyzer';
  import { needs, story, viewer } from '$lib/mock/community';
  import { nextRaid, type Role } from '$lib/mock/data';
  import { previewNextRaid, previewNow, previewPerformance } from '$lib/mock/hub';
  import { sheetTrend } from '$lib/mock/sheets';
  import { visibleFeed } from '$lib/posts';
  import { isFinal } from '$lib/recruitment';
  import { previewSession } from './session.svelte';
  import { community, home } from './state.svelte';

  const roles: Role[] = ['Tank', 'Healer', 'Melee', 'Ranged'];
  // Hopscotch is a Wednesday officer in the sample data; the raider view signs in without those powers.
  const officer = $derived(isOfficer(viewer) && previewSession.role === 'officer');

  const feed = $derived(visibleFeed(community.posts, viewer));
  const mySpotlights = $derived(community.spotlights.filter((s) => s.memberName === viewer.name));
  const askingConsent = $derived(mySpotlights.filter((s) => s.consent === 'pending'));
  const recent = $derived(visibleHighlights(community.highlights, viewer).slice(0, 2));
  let consentNote = $state('');

  const desk = $derived(
    deskLines({
      applications_waiting: community.applications.filter((a) => !isFinal(a.status)).length,
      posts_to_curate: community.posts.filter((p) => p.status === 'pending_review').length,
      highlights_to_review: community.highlights.filter((h) => h.status === 'submitted').length,
      spotlights_awaiting_consent: community.spotlights.filter((s) => s.consent === 'pending').length
    })
  );
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

  // The preview has no API: layouts change in memory only, as the API would answer.
  async function save(widgets: HomeWidget[]) {
    home.layout = saved(widgets);
    return null;
  }
  async function reset() {
    home.layout = defaultLayout(officer);
    return null;
  }
</script>

<HomeView name={viewer.name} layout={home.layout} {save} {reset}>
  {#snippet top()}
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
  {/snippet}

  {#snippet widget(id)}
    {#if id === 'next_raid'}
      <NextRaidCard raid={previewNextRaid} now={previewNow} />
    {:else if id === 'officer_desk'}
      <section class="card" aria-labelledby="desk-h">
        <h2 id="desk-h">Raid leader desk</h2>
        <DeskList lines={desk} />
        <p class="muted small">
          Next raid role gaps:
          {#if gaps.length}
            {gaps.map((r) => `${r} ${nextRaid.needed[r] - nextRaid.signups[r]}`).join(', ')}
          {:else}none{/if}
        </p>
      </section>
    {:else if id === 'my_performance'}
      <PerformanceCard mine={previewPerformance} />
    {:else if isAnalyzer(id)}
      <AnalyzerWidget widget={widgetById(analyzerPage, id)} title={catalogueTitle(id)} missing="Not in this sample." />
    {:else if id === 'raid_totals'}
      <RaidTotals raids={sheetTrend} />
    {:else if id === 'posts'}
      <section class="card feed" aria-labelledby="feed-h">
        <h2 id="feed-h">Posts</h2>
        {#each feed as p (p.id)}
          <PostCard post={p} badges />
        {:else}
          <p class="muted">Nothing posted yet.</p>
        {/each}
      </section>
    {:else if id === 'highlights'}
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
    {:else if id === 'progression'}
      <section class="card" aria-labelledby="prog-h">
        <h2 id="prog-h">Progression</h2>
        <ProgressBars zones={story.progression} />
      </section>
    {:else if id === 'recruiting'}
      <section class="card" aria-labelledby="needs-h">
        <h2 id="needs-h">Recruiting</h2>
        <NeedsList {needs} />
        <a href="{base}/recruit/">How applying works</a>
      </section>
    {/if}
  {/snippet}
</HomeView>

<style>
  .consent { border-color: var(--accent); margin-bottom: 1rem; }
  .quote { border-left: 3px solid var(--line); padding-left: 0.75rem; margin: 0.5rem 0 0.75rem; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .clips { display: grid; gap: 1rem; margin-bottom: 0.75rem; }
  .small { font-size: 0.8rem; }
</style>
