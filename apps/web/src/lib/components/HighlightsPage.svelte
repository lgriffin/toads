<script lang="ts">
  import { onMount } from 'svelte';
  import { PROVIDER_LABELS } from '$lib/clips';
  import type { Highlight } from '$lib/community';
  import { shortDate } from '$lib/format';
  import {
    appendPage,
    byMonth,
    galleryError,
    step,
    timeLeft,
    twitchChannelUrl,
    type Board,
    type ClipReview,
    type Decision,
    type GalleryBackend,
    type Photo,
    type ReviewKind,
    type ReviewQueue,
    type WaitingPhoto,
    type WaitingStream
  } from '$lib/gallery';
  import ClipPlayer from './ClipPlayer.svelte';
  import LivePlayer from './LivePlayer.svelte';

  interface Props {
    backend: GalleryBackend;
  }
  let { backend }: Props = $props();

  let board = $state<Board | null>(null);
  let loadError = $state('');
  let archive = $state<Photo[]>([]);
  let nextBefore = $state<number | null>(null);
  let picked = $state<Set<number>>(new Set());
  let archiveError = $state('');
  let clips = $state<Highlight[]>([]);
  let clipsError = $state('');
  let queue = $state<Highlight[]>([]);
  let approvals = $state<ReviewQueue>({ photos: [], streams: [] });
  let approvalsError = $state('');
  let slide = $state(0);
  let selected = $state<Photo | null>(null);
  let confirming = $state(false);
  let busy = $state(false);
  let notice = $state('');
  let actionError = $state('');
  let dialog = $state<HTMLDialogElement | null>(null);

  const carousel = $derived(board?.carousel ?? []);
  const current = $derived(carousel[Math.min(slide, Math.max(carousel.length - 1, 0))]);
  const months = $derived(byMonth(archive));
  const pickId = $derived(board?.photo_of_the_week?.photo.id ?? null);

  async function loadBoard() {
    try {
      board = await backend.board();
      loadError = '';
      if (board.can_curate) queue = await backend.clipQueue().catch(() => []);
      await loadApprovals();
    } catch (e) {
      loadError = galleryError(e);
    }
  }

  async function loadApprovals() {
    if (!board?.review) return;
    try {
      approvals = await backend.reviewQueue(board.review);
      approvalsError = '';
    } catch (e) {
      approvalsError = galleryError(e);
    }
  }

  async function decide(kind: ReviewKind, item: WaitingPhoto | WaitingStream, decision: Decision) {
    if (!board?.review) return;
    const what = kind === 'photos' ? `“${(item as WaitingPhoto).caption || 'The photo'}”` : `${(item as WaitingStream).streamer_name}’s stream`;
    try {
      await backend.decide(board.review, kind, item, decision);
      notice =
        decision === 'approve'
          ? `${what} is on the page now.`
          : kind === 'photos'
            ? `${what} was turned down and deleted.`
            : `${what} was turned down.`;
      await loadBoard();
      if (decision === 'approve' && kind === 'photos') await loadArchive();
    } catch (e) {
      notice = galleryError(e);
    }
  }

  async function loadArchive(more = false) {
    try {
      const page = await backend.archive(more ? nextBefore : null);
      archive = more ? appendPage(archive, page) : page.photos;
      nextBefore = page.next_before;
      picked = new Set([...(more ? picked : []), ...page.picked]);
      archiveError = '';
    } catch (e) {
      archiveError = galleryError(e);
    }
  }

  async function loadClips() {
    try {
      clips = await backend.clips();
      clipsError = '';
    } catch (e) {
      clipsError = galleryError(e);
    }
  }

  onMount(() => {
    void loadBoard();
    void loadArchive();
    void loadClips();
  });

  function open(photo: Photo) {
    selected = photo;
    confirming = false;
    actionError = '';
    dialog?.showModal();
  }

  function close() {
    dialog?.close();
  }

  /** `after` updates the archive in place, so older pages a member has opened stay open. */
  async function act(work: () => Promise<unknown>, done: string, after: () => void) {
    busy = true;
    actionError = '';
    try {
      await work();
      notice = done;
      after();
      close();
      await loadBoard();
    } catch (e) {
      actionError = galleryError(e);
    } finally {
      busy = false;
    }
  }

  const makePick = (p: Photo) =>
    act(() => backend.pickPhoto(p.id), `“${p.caption || 'That photo'}” is the photo of the week.`, () => {
      picked = new Set([...picked, p.id]);
    });
  const takeDown = (p: Photo) =>
    act(() => backend.removePhoto(p.id), 'The photo was taken down.', () => {
      archive = archive.filter((a) => a.id !== p.id);
    });

  async function stopStream(id: number) {
    try {
      await backend.removeStream(id);
      notice = 'The stream is off the page.';
      await loadBoard();
    } catch (e) {
      notice = galleryError(e);
    }
  }

  async function review(h: Highlight, action: ClipReview) {
    try {
      await backend.reviewClip(h.id, action);
      notice = action === 'reject' ? `“${h.title}” was turned down.` : `“${h.title}” is in the clips now.`;
      queue = await backend.clipQueue();
      await loadClips();
    } catch (e) {
      notice = galleryError(e);
    }
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'ArrowLeft') slide = step(slide, -1, carousel.length);
    else if (e.key === 'ArrowRight') slide = step(slide, 1, carousel.length);
  }

  const by = (p: Photo) => `${p.uploader_name} · ${shortDate(p.created_at)}`;
</script>

<header class="intro">
  <h1>Highlights</h1>
  <p class="muted lede">
    Raid night in pictures, streams and clips. An officer approves each photo; it then stays in the carousel for 48
    hours and in the archive for good.
  </p>
</header>

<p class="sr-only" role="status" aria-live="polite">{notice}</p>
{#if notice}<p class="notice" aria-hidden="true">{notice}</p>{/if}

{#if loadError}
  <p class="card err" role="alert">{loadError} <button type="button" class="btn small" onclick={loadBoard}>Try again</button></p>
{:else if !board}
  <p class="muted">Loading highlights…</p>
{:else}
  {#if board.review && (approvals.photos.length || approvals.streams.length || approvalsError)}
    <section aria-labelledby="approve-h" class="card review approvals">
      <h2 id="approve-h">Waiting for your approval</h2>
      <p class="muted">
        {board.review.every_night ? 'Everything members have posted' : 'What members of your raid nights have posted'}.
        Nothing here shows to anyone else until you approve it; turning down a photo deletes it.
      </p>
      {#if approvalsError}
        <p class="err" role="alert">{approvalsError} <button type="button" class="btn small" onclick={loadApprovals}>Try again</button></p>
      {/if}
      <ul>
        {#each approvals.photos as p (p.id)}
          <li>
            <span class="pending">
              <button type="button" class="pending-thumb" onclick={() => open(p)} aria-label="Open “{p.caption || 'photo'}” by {p.uploader_name}">
                <img src={p.thumbnail_url} alt="" loading="lazy" />
              </button>
              <span><strong>{p.caption || 'Untitled photo'}</strong> <span class="muted">by {by(p)}</span></span>
            </span>
            <span class="actions">
              <button type="button" class="btn small primary" onclick={() => decide('photos', p, 'approve')}>Approve</button>
              <button type="button" class="btn small danger" onclick={() => decide('photos', p, 'reject')}>Turn down</button>
            </span>
          </li>
        {/each}
        {#each approvals.streams as s (s.id)}
          <li>
            <span>
              <strong>{s.streamer_name}</strong> wants to stream
              <a href={twitchChannelUrl(s.channel) ?? undefined} target="_blank" rel="noopener noreferrer">twitch.tv/{s.channel}</a>{s.title ? `: ${s.title}` : ''}
              <span class="muted">· approving trusts this channel for their later streams</span>
            </span>
            <span class="actions">
              <button type="button" class="btn small primary" onclick={() => decide('streams', s, 'approve')}>Approve</button>
              <button type="button" class="btn small danger" onclick={() => decide('streams', s, 'reject')}>Turn down</button>
            </span>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  {#if board.waiting_photos.length || board.waiting_streams.length}
    <section aria-labelledby="mine-h" class="card mine">
      <h2 id="mine-h">Waiting for an officer</h2>
      <p class="muted">Only you and the officers can see these until one of them approves them.</p>
      <ul class="tiles">
        {#each board.waiting_photos as p (p.id)}
          <li>
            <button type="button" class="tile" onclick={() => open(p)} aria-label="Open your waiting photo “{p.caption || 'photo'}”">
              <img src={p.thumbnail_url} alt="" loading="lazy" />
              <span class="star waiting">Waiting</span>
            </button>
          </li>
        {/each}
      </ul>
      {#each board.waiting_streams as s (s.id)}
        <p>Your stream on twitch.tv/{s.channel} shows here once an officer approves the channel.</p>
      {/each}
    </section>
  {/if}

  {#if board.streams.length}
    <section aria-labelledby="live-h">
      <h2 id="live-h">Live now</h2>
      <div class="grid live-grid">
        {#each board.streams as s (s.id)}
          <div class="card stack">
            <LivePlayer stream={s} />
            {#if s.removable}
              <button type="button" class="btn small danger end" onclick={() => stopStream(s.id)}>Take off the page</button>
            {/if}
          </div>
        {/each}
      </div>
    </section>
  {/if}

  {#if board.photo_of_the_week}
    {@const pick = board.photo_of_the_week}
    <section aria-labelledby="potw-h" class="potw card">
      <button type="button" class="potw-image" onclick={() => open(pick.photo)} aria-label="Open the photo of the week">
        <img src={pick.photo.image_url} alt={pick.photo.caption || `Photo by ${pick.photo.uploader_name}`} width={pick.photo.width} height={pick.photo.height} />
      </button>
      <div class="potw-text">
        <p class="eyebrow">Photo of the week</p>
        <h2 id="potw-h">{pick.photo.caption || 'Untitled'}</h2>
        <p class="muted">Posted by {pick.photo.uploader_name} · picked by {pick.chosen_by_name} · until {shortDate(pick.ends_at)}</p>
      </div>
    </section>
  {/if}

  <section aria-labelledby="recent-h">
    <h2 id="recent-h">The last 48 hours</h2>
    {#if current}
      <div
        class="carousel"
        role="region"
        aria-roledescription="carousel"
        aria-label="Photos from the last 48 hours"
      >
        <figure class="slide" aria-roledescription="slide" aria-label="{slide + 1} of {carousel.length}">
          <button type="button" class="slide-image always-dusk" onclick={() => open(current)} onkeydown={onKey} aria-label="Open “{current.caption || 'photo'}”">
            <img src={current.image_url} alt={current.caption || `Photo by ${current.uploader_name}`} />
          </button>
          <figcaption>
            <strong>{current.caption || 'Untitled'}</strong>
            <span class="muted">{by(current)} · leaves the carousel {timeLeft(current.carousel_until)}</span>
          </figcaption>
        </figure>
        {#if carousel.length > 1}
          <div class="controls">
            <button type="button" class="btn small" onclick={() => (slide = step(slide, -1, carousel.length))} aria-label="Previous photo">‹ Previous</button>
            <ol class="thumbs">
              {#each carousel as p, i (p.id)}
                <li>
                  <button type="button" class="thumb" aria-current={i === slide ? 'true' : undefined} aria-label="Show photo {i + 1}: {p.caption || p.uploader_name}" onclick={() => (slide = i)}>
                    <img src={p.thumbnail_url} alt="" loading="lazy" />
                  </button>
                </li>
              {/each}
            </ol>
            <button type="button" class="btn small" onclick={() => (slide = step(slide, 1, carousel.length))} aria-label="Next photo">Next ›</button>
          </div>
        {/if}
      </div>
    {:else}
      <p class="muted">No photos in the last 48 hours. Post one from Discord with <code>/highlight</code>.</p>
    {/if}
  </section>

  <section aria-labelledby="clips-h">
    <h2 id="clips-h">Clips</h2>
    {#if board.can_curate && queue.length}
      <div class="card review">
        <h3>Waiting for your review</h3>
        <ul>
          {#each queue as h (h.id)}
            <li>
              <span><strong>{h.title}</strong> <span class="muted">from {h.submittedBy} · {PROVIDER_LABELS[h.provider]}</span></span>
              <span class="actions">
                <button type="button" class="btn small primary" onclick={() => review(h, 'publish_guild')}>Publish to members</button>
                <button type="button" class="btn small" onclick={() => review(h, 'publish_public')}>Publish to the Story too</button>
                <button type="button" class="btn small danger" onclick={() => review(h, 'reject')}>Turn down</button>
              </span>
            </li>
          {/each}
        </ul>
      </div>
    {/if}
    {#if clipsError}
      <p class="err" role="alert">{clipsError} <button type="button" class="btn small" onclick={loadClips}>Try again</button></p>
    {/if}
    <div class="grid">
      {#each clips as h (h.id)}
        <div class="card">
          <ClipPlayer
            provider={h.provider}
            clipId={h.clipId}
            title={h.title}
            meta="{h.boss ? `${h.boss} · ` : ''}{shortDate(h.createdAt)} · by {h.submittedBy} · {PROVIDER_LABELS[h.provider]}"
          />
        </div>
      {:else}
        {#if !clipsError}
          <p class="muted">No clips yet. Share one from Discord with <code>/clip</code>; a global officer publishes it here.</p>
        {/if}
      {/each}
    </div>
  </section>
{/if}

<section aria-labelledby="archive-h">
  <h2 id="archive-h">Archive</h2>
  {#if archiveError}
    <p class="err" role="alert">{archiveError}</p>
  {:else if !archive.length}
    <p class="muted">Every photo ever posted lands here once it leaves the carousel.</p>
  {/if}
  {#each months as m (m.label)}
    <h3 class="month">{m.label}</h3>
    <ul class="tiles">
      {#each m.photos as p (p.id)}
        <li>
          <button type="button" class="tile" onclick={() => open(p)} aria-label="Open “{p.caption || 'photo'}” by {p.uploader_name}">
            <img src={p.thumbnail_url} alt="" loading="lazy" />
            {#if picked.has(p.id)}<span class="star">Photo of the week</span>{/if}
          </button>
        </li>
      {/each}
    </ul>
  {/each}
  {#if nextBefore}
    <button type="button" class="btn" onclick={() => loadArchive(true)}>Show older photos</button>
  {/if}
</section>

<aside class="card how" aria-labelledby="how-h">
  <h2 id="how-h">Add to Highlights from Discord</h2>
  <dl>
    <dt><code>/highlight</code></dt>
    <dd>Attach a photo and a caption. It shows here once an officer approves it; location data is stripped.</dd>
    <dt><code>/stream start</code></dt>
    <dd>
      Paste your Twitch link to show your stream here while you are live. An officer approves a channel the first time;
      after that it goes up at once. <code>/stream end</code> takes it off.
    </dd>
    <dt><code>/clip</code></dt>
    <dd>Share a YouTube, Twitch clip or Streamable link. A global officer publishes it to the clips.</dd>
  </dl>
</aside>

<dialog bind:this={dialog} class="lightbox" aria-labelledby="lb-h" onclose={() => (selected = null)}>
  {#if selected}
    <div class="lb-body">
      <img src={selected.image_url} alt={selected.caption || `Photo by ${selected.uploader_name}`} />
      <div class="lb-text">
        <h2 id="lb-h">{selected.caption || 'Untitled'}</h2>
        <p class="muted">{by(selected)}</p>
        {#if actionError}<p class="err" role="alert">{actionError}</p>{/if}
        <div class="actions">
          {#if board?.can_curate && selected.id !== pickId && !selected.waiting}
            <button type="button" class="btn small primary" disabled={busy} onclick={() => selected && makePick(selected)}>Make photo of the week</button>
          {/if}
          {#if selected.removable}
            {#if confirming}
              <button type="button" class="btn small danger" disabled={busy} onclick={() => selected && takeDown(selected)}>Yes, take it down for good</button>
              <button type="button" class="btn small" onclick={() => (confirming = false)}>Keep it</button>
            {:else}
              <button type="button" class="btn small danger" onclick={() => (confirming = true)}>Take down</button>
            {/if}
          {/if}
          <a class="btn small" href={selected.image_url} target="_blank" rel="noopener">Full size</a>
          <button type="button" class="btn small" onclick={close}>Close</button>
        </div>
      </div>
    </div>
  {/if}
</dialog>

<style>
  section { margin-top: 1.75rem; }
  h2 { margin: 0 0 0.75rem; }
  .intro h1 { margin-bottom: 0.25rem; }
  .lede { max-width: 66ch; margin: 0; }
  .notice { margin: 1rem 0 0; color: var(--accent); }
  .err { color: var(--bad-text); }
  .grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); }
  .stack { display: grid; gap: 0.6rem; }
  .live-grid { max-width: 56rem; }
  .end { justify-self: start; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .btn.small { padding: 0.3rem 0.65rem; font-size: 0.85rem; }

  .potw { display: grid; gap: 1rem; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); align-items: center; }
  .potw-image { padding: 0; border: 0; background: none; cursor: zoom-in; border-radius: 6px; overflow: hidden; }
  .potw-image img { display: block; width: 100%; height: auto; max-height: 28rem; object-fit: cover; }
  .potw-text h2 { margin: 0 0 0.4rem; color: var(--bronze-hi); }
  .eyebrow { margin: 0 0 0.3rem; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--accent); }
  @media (max-width: 44rem) { .potw { grid-template-columns: 1fr; } }

  .carousel { display: grid; gap: 0.75rem; grid-template-columns: minmax(0, 1fr); }
  .slide { margin: 0; display: grid; gap: 0.5rem; grid-template-columns: minmax(0, 1fr); }
  .slide-image {
    padding: 0;
    border: 0;
    border-radius: 8px;
    overflow: hidden;
    background: var(--dusk);
    cursor: zoom-in;
    aspect-ratio: 16 / 9;
    max-height: 34rem;
  }
  .slide-image img { width: 100%; height: 100%; object-fit: contain; display: block; }
  .slide figcaption { display: grid; gap: 0.15rem; }
  .controls { display: flex; align-items: center; gap: 0.5rem; }
  .thumbs { display: flex; gap: 0.4rem; list-style: none; margin: 0; padding: 0.2rem; overflow-x: auto; flex: 1; min-width: 0; }
  .thumb { padding: 0; border: 2px solid transparent; border-radius: 6px; background: none; cursor: pointer; display: block; }
  .thumb img { display: block; width: 4.5rem; height: 3rem; object-fit: cover; border-radius: 4px; }
  .thumb[aria-current='true'] { border-color: var(--accent); }

  .review { margin-bottom: 1rem; }
  .review h3 { margin: 0 0 0.5rem; }
  .review ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; }
  .approvals { margin-top: 1.25rem; }
  .approvals > p { margin: 0 0 0.75rem; }
  .pending { display: flex; align-items: center; gap: 0.6rem; min-width: 0; }
  .pending-thumb { padding: 0; border: 0; border-radius: 4px; overflow: hidden; background: none; cursor: zoom-in; flex: none; }
  .pending-thumb img { display: block; width: 4.5rem; height: 3rem; object-fit: cover; }
  .pending-thumb:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
  .mine { margin-top: 1.25rem; }
  .mine > p { margin: 0 0 0.6rem; }
  .star.waiting { background: var(--surface); color: var(--text); border: 1px solid var(--line); }
  .review li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.5rem; padding-bottom: 0.6rem; border-bottom: 1px solid var(--line); }

  .month { margin: 1rem 0 0.5rem; font-size: 1rem; color: var(--bronze-hi); }
  .tiles { list-style: none; margin: 0 0 0.75rem; padding: 0; display: grid; gap: 0.5rem; grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr)); }
  .tile { position: relative; padding: 0; border: 0; border-radius: 6px; overflow: hidden; display: block; width: 100%; cursor: zoom-in; background: var(--surface); }
  .tile img { display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; }
  .tile:focus-visible, .thumb:focus-visible, .slide-image:focus-visible, .potw-image:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
  .star {
    position: absolute;
    left: 0.35rem;
    bottom: 0.35rem;
    padding: 0.05rem 0.4rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 700;
    background: var(--bronze);
    color: var(--on-bronze);
  }

  .how { margin-top: 2rem; }
  .how h2 { font-size: 1.05rem; }
  .how dl { margin: 0; display: grid; gap: 0.35rem 1rem; grid-template-columns: max-content 1fr; }
  .how dt { font-weight: 600; }
  .how dd { margin: 0; }
  @media (max-width: 40rem) { .how dl { grid-template-columns: 1fr; } .how dd { margin-bottom: 0.4rem; } }

  .lightbox {
    width: min(64rem, calc(100vw - 2rem));
    max-height: calc(100vh - 2rem);
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--surface);
    color: var(--text);
  }
  .lightbox::backdrop { background: rgb(0 0 0 / 0.75); }
  .lb-body { display: grid; }
  .lb-body img { display: block; width: 100%; max-height: 70vh; object-fit: contain; background: var(--dusk); }
  .lb-text { padding: 1rem; display: grid; gap: 0.4rem; }
  .lb-text h2, .lb-text p { margin: 0; }
</style>
