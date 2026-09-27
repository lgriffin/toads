<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import {
    ApiError,
    deskSummary,
    getHome,
    getSession,
    analyzerHome,
    guildHighlights,
    homeError,
    postsFeed,
    publicStory,
    raidTrend,
    resetHome,
    saveHome,
    type Session
  } from '$lib/api';
  import { PROVIDER_LABELS } from '$lib/clips';
  import type { Highlight, Post } from '$lib/community';
  import { deskLines, needFromApi, type ApiStory, type DeskSummary } from '$lib/community-api';
  import AnalyzerWidget from '$lib/components/AnalyzerWidget.svelte';
  import ClipPlayer from '$lib/components/ClipPlayer.svelte';
  import DeskList from '$lib/components/DeskList.svelte';
  import HomeView from '$lib/components/HomeView.svelte';
  import NeedsList from '$lib/components/NeedsList.svelte';
  import PostCard from '$lib/components/PostCard.svelte';
  import ProgressBars from '$lib/components/ProgressBars.svelte';
  import RaidTotals from '$lib/components/RaidTotals.svelte';
  import { isAnalyzer, shownIds, type HomeLayout, type HomeWidget, type WidgetId } from '$lib/home';
  import { PAGE_VERSION, widgetById, type AnalyzerPage } from '$lib/home-payload';
  import Hub from '$lib/preview/Hub.svelte';
  import type { RaidHeadline } from '$lib/sheets';

  type State =
    | { kind: 'loading' }
    | { kind: 'signed-out' }
    | { kind: 'error'; message: string }
    | { kind: 'ready'; session: Session; layout: HomeLayout };

  type Loaded<T> = { kind: 'loading' } | { kind: 'ok'; value: T } | { kind: 'error'; message: string };

  let view = $state<State>({ kind: 'loading' });
  let totals = $state<Loaded<RaidHeadline[]>>({ kind: 'loading' });
  let posts = $state<Loaded<Post[]>>({ kind: 'loading' });
  let highlights = $state<Loaded<Highlight[]>>({ kind: 'loading' });
  let story = $state<Loaded<ApiStory>>({ kind: 'loading' });
  let desk = $state<Loaded<DeskSummary>>({ kind: 'loading' });
  let analyzer = $state<Loaded<AnalyzerPage>>({ kind: 'loading' });

  function failure(e: unknown): string {
    if (e instanceof ApiError && e.status === 401) return 'Your session ended; sign in again.';
    return e instanceof ApiError && e.message ? e.message : 'Could not load this; try again later.';
  }

  function load<T>(p: Promise<T>, set: (v: Loaded<T>) => void) {
    p.then(
      (value) => set({ kind: 'ok', value }),
      (e) => set({ kind: 'error', message: failure(e) })
    );
  }

  // Each widget's data is fetched the first time it is shown, so a hidden widget costs nothing.
  type Source = WidgetId | 'analyzer';
  const loaders: Partial<Record<Source, () => void>> = {
    analyzer: () => load(analyzerHome(), (v) => (analyzer = v)),
    raid_totals: () => load(raidTrend(), (v) => (totals = v)),
    posts: () => load(postsFeed(), (v) => (posts = v)),
    highlights: () => load(guildHighlights(), (v) => (highlights = v)),
    progression: () => load(publicStory(), (v) => (story = v)),
    officer_desk: () => load(deskSummary(), (v) => (desk = v))
  };
  const requested = new Set<Source>();

  $effect(() => {
    if (view.kind !== 'ready') return;
    for (const id of shownIds(view.layout)) {
      // Progression and recruiting both come from the public story; analyzer widgets share one page.
      const key: Source = isAnalyzer(id) ? 'analyzer' : id === 'recruiting' ? 'progression' : id;
      if (!requested.has(key)) {
        requested.add(key);
        loaders[key]?.();
      }
    }
  });

  // Every failure lands in the page as a message; nothing here throws to the error page.
  onMount(async () => {
    if (__PREVIEW__) return;
    try {
      const session = await getSession();
      if (!session) {
        view = { kind: 'signed-out' };
        return;
      }
      view = { kind: 'ready', session, layout: await getHome() };
    } catch (e) {
      view = e instanceof ApiError && e.status === 401 ? { kind: 'signed-out' } : { kind: 'error', message: failure(e) };
    }
  });

  async function change(action: () => Promise<HomeLayout>): Promise<string | null> {
    if (view.kind !== 'ready') return null;
    try {
      view = { ...view, layout: await action() };
      return null;
    } catch (e) {
      return homeError(e);
    }
  }
  const save = (widgets: HomeWidget[]) => change(() => saveHome(widgets.filter((w) => w.shown).map((w) => w.id)));
  const reset = () => change(() => resetHome());

  const title = (layout: HomeLayout, id: WidgetId) => layout.widgets.find((w) => w.id === id)?.title ?? id;
</script>

<svelte:head><title>Hub · Toads</title></svelte:head>

{#snippet status(state: Loaded<unknown>)}
  {#if state.kind === 'loading'}
    <p class="muted" role="status">Loading…</p>
  {:else if state.kind === 'error'}
    <p class="err" role="alert">{state.message}</p>
  {/if}
{/snippet}

{#if __PREVIEW__}
  <Hub />
{:else if view.kind === 'ready'}
  {@const layout = view.layout}
  <HomeView name={view.session.display_name} {layout} {save} {reset}>
    {#snippet widget(id)}
      {#if isAnalyzer(id)}
        {#if analyzer.kind === 'ok' && analyzer.value.version === PAGE_VERSION}
          <AnalyzerWidget
            widget={widgetById(analyzer.value, id)}
            title={title(layout, id)}
            missing={analyzer.value.generated_at
              ? 'The analyzer has nothing for this yet.'
              : 'Shows once the worker has analysed the guild’s raids.'}
          />
        {:else}
          <section class="card" aria-labelledby="{id}-h">
            <h2 id="{id}-h">{title(layout, id)}</h2>
            {#if analyzer.kind === 'ok'}
              <p class="muted">This hub cannot draw the analyzer’s newer page yet.</p>
            {:else}{@render status(analyzer)}{/if}
          </section>
        {/if}
      {:else if id === 'raid_totals'}
        {#if totals.kind === 'ok'}
          <RaidTotals raids={totals.value} />
        {:else}
          <section class="card" aria-labelledby="totals-h">
            <h2 id="totals-h">Raid totals</h2>
            {@render status(totals)}
          </section>
        {/if}
      {:else if id === 'officer_desk'}
        <section class="card" aria-labelledby="desk-h">
          <h2 id="desk-h">Raid leader desk</h2>
          {#if desk.kind === 'ok'}<DeskList lines={deskLines(desk.value)} linked={false} />{:else}{@render status(desk)}{/if}
        </section>
      {:else if id === 'posts'}
        <section class="card" aria-labelledby="feed-h">
          <h2 id="feed-h">Posts</h2>
          {#if posts.kind === 'ok'}
            {#each posts.value as p (p.id)}
              <PostCard post={p} badges />
            {:else}
              <p class="muted">Nothing posted yet.</p>
            {/each}
          {:else}{@render status(posts)}{/if}
        </section>
      {:else if id === 'highlights'}
        <section class="card" aria-labelledby="hl-h">
          <h2 id="hl-h">Recent highlights</h2>
          {#if highlights.kind === 'ok'}
            <div class="clips">
              {#each highlights.value.slice(0, 2) as h (h.id)}
                <ClipPlayer
                  provider={h.provider}
                  clipId={h.clipId}
                  title={h.title}
                  meta="{h.visibility === 'guild' ? 'Guild only · ' : ''}{PROVIDER_LABELS[h.provider]}"
                />
              {:else}
                <p class="muted">No highlights yet.</p>
              {/each}
            </div>
          {:else}{@render status(highlights)}{/if}
          <a href="{base}/highlights">All highlights</a>
        </section>
      {:else if id === 'progression'}
        <section class="card" aria-labelledby="prog-h">
          <h2 id="prog-h">Progression</h2>
          {#if story.kind === 'ok'}<ProgressBars zones={story.value.progression} />{:else}{@render status(story)}{/if}
        </section>
      {:else if id === 'recruiting'}
        <section class="card" aria-labelledby="needs-h">
          <h2 id="needs-h">Recruiting</h2>
          {#if story.kind === 'ok'}
            <NeedsList needs={story.value.needs.map(needFromApi)} />
          {:else}{@render status(story)}{/if}
          <a href="{base}/recruit">How applying works</a>
        </section>
      {:else}
        <!-- Widgets whose data the API does not serve yet. -->
        <section class="card" aria-labelledby="{id}-h">
          <h2 id="{id}-h">{title(layout, id)}</h2>
          {#if id === 'next_raid'}
            <p class="muted">Shows the next raid and its signups once the hub reads Discord's scheduled events.</p>
          {:else}
            <p class="muted">Shows your last raid against the guild median once your characters' raids are analysed.</p>
            <a href="{base}/me/claim">Claim your characters</a>
          {/if}
        </section>
      {/if}
    {/snippet}
  </HomeView>
{:else}
  <h1>Toads Hub</h1>
  {#if view.kind === 'loading'}
    <p class="muted" role="status">Loading your home…</p>
  {:else if view.kind === 'signed-out'}
    <section class="card" aria-labelledby="signin-h">
      <h2 id="signin-h">Members only</h2>
      <p>Sign in with Discord to open your hub.</p>
      <a class="btn primary" href="/auth/login" data-sveltekit-reload>Log in with Discord</a>
    </section>
  {:else}
    <p class="err" role="alert">{view.message}</p>
  {/if}
{/if}

<style>
  .clips { display: grid; gap: 1rem; margin-bottom: 0.75rem; }
</style>
