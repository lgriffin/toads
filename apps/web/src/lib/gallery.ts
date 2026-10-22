/**
 * The Highlights page (docs/highlights.md): members post photos with the Toad Bot's `/highlight`, which, once an
 * officer approves them, sit in a 48-hour carousel and then the archive for good; a global officer picks a photo of the week for seven days;
 * `/stream start` puts a member's Twitch channel on the page while they are live; `/clip` shares a video clip that a
 * global officer publishes to the clips section.
 *
 * Streams travel as a bare Twitch login and the player URL is built here, so no member-supplied URL ever reaches an
 * iframe (the same rule as clips, `$lib/clips`).
 */
import { ApiError, call, type Fetch } from './api';
import { highlightFromApi, type ApiHighlight } from './community-api';
import type { Highlight } from './community';

export interface Photo {
  id: number;
  uploader_name: string;
  caption: string;
  width: number;
  height: number;
  created_at: string;
  /** When it leaves the carousel; it stays in the archive. */
  carousel_until: string;
  image_url: string;
  thumbnail_url: string;
  /** The viewer posted it, or is a global officer. */
  removable: boolean;
  /** Waiting for an officer: only its poster and the officers who may approve it see it. */
  waiting?: boolean;
}

export interface Pick {
  photo: Photo;
  chosen_by_name: string;
  starts_at: string;
  ends_at: string;
}

export interface Stream {
  id: number;
  streamer_name: string;
  /** The Twitch login; see `twitchPlayerUrl`. */
  channel: string;
  title: string;
  started_at: string;
  ends_at: string;
  removable: boolean;
  waiting?: boolean;
}

/** Whose posts the viewer approves: everyone's (global officers), or those of these raid nights' members. */
export interface ReviewScope {
  every_night: boolean;
  nights: string[];
}

/** A post waiting for an officer, with the raid nights whose officers may decide it (none: global officers only). */
export type WaitingPhoto = Photo & { nights: string[] };
export type WaitingStream = Stream & { nights: string[] };

export interface ReviewQueue {
  photos: WaitingPhoto[];
  streams: WaitingStream[];
}

export type ReviewKind = 'photos' | 'streams';
export type Decision = 'approve' | 'reject';

export interface Board {
  carousel: Photo[];
  photo_of_the_week: Pick | null;
  streams: Stream[];
  /** True when the hub asks Twitch who is live; otherwise a stream shows until ended or 12 hours pass. */
  checked_live: boolean;
  /** The viewer picks the photo of the week, takes anything down and reviews clips (global officers). */
  can_curate: boolean;
  /** The viewer may post with `/highlight` (raiders). */
  can_post: boolean;
  /** The viewer's own posts still waiting for an officer. */
  waiting_photos: Photo[];
  waiting_streams: Stream[];
  /** Set when the viewer approves posts. */
  review: ReviewScope | null;
}

export interface ArchivePage {
  photos: Photo[];
  next_before: number | null;
  picked: number[];
}

export type ClipReview = 'publish_guild' | 'publish_public' | 'reject';

/** What the page talks to: the hub, or the preview's in-browser fake. */
export interface GalleryBackend {
  board(): Promise<Board>;
  archive(before?: number | null): Promise<ArchivePage>;
  picks(): Promise<Pick[]>;
  removePhoto(id: number): Promise<void>;
  pickPhoto(id: number): Promise<Pick>;
  removeStream(id: number): Promise<void>;
  clips(): Promise<Highlight[]>;
  /** Clips waiting for review; global officers only. */
  clipQueue(): Promise<Highlight[]>;
  reviewClip(id: string, action: ClipReview): Promise<Highlight>;
  /** What waits for this officer's approval. */
  reviewQueue(scope: ReviewScope): Promise<ReviewQueue>;
  decide(scope: ReviewScope, kind: ReviewKind, item: WaitingPhoto | WaitingStream, decision: Decision): Promise<void>;
}

/**
 * Where an officer decides a post: the global officers' routes, or the routes of a night the officer runs and the
 * poster is on (the hub takes the night from the path). Null when the officer may not decide it.
 */
export function reviewBase(scope: ReviewScope, nights: readonly string[]): string | null {
  if (scope.every_night) return '/api/admin/gallery';
  const night = scope.nights.find((n) => nights.includes(n));
  return night ? `/api/days/${encodeURIComponent(night)}/gallery` : null;
}

/** Several nights' queues as one, oldest first, each post once (a poster on two of the officer's nights). */
export function mergeQueues(queues: readonly ReviewQueue[]): ReviewQueue {
  const once = <T extends { id: number }>(items: T[]) =>
    [...new Map(items.map((i) => [i.id, i])).values()].sort((a, b) => a.id - b.id);
  return { photos: once(queues.flatMap((q) => q.photos)), streams: once(queues.flatMap((q) => q.streams)) };
}

export function hubGallery(f: Fetch = fetch): GalleryBackend {
  return {
    board: () => call<Board>(f, '/api/gallery/board'),
    archive: (before) => call<ArchivePage>(f, `/api/gallery/photos${before ? `?before=${before}` : ''}`),
    picks: () => call<Pick[]>(f, '/api/gallery/photos-of-the-week'),
    removePhoto: (id) => call<void>(f, `/api/gallery/photos/${id}`, { method: 'DELETE' }),
    pickPhoto: (id) => call<Pick>(f, `/api/admin/gallery/photos/${id}/photo-of-the-week`, { method: 'POST' }),
    removeStream: (id) => call<void>(f, `/api/gallery/streams/${id}`, { method: 'DELETE' }),
    clips: async () => (await call<ApiHighlight[]>(f, '/api/highlights')).map(highlightFromApi),
    clipQueue: async () => (await call<ApiHighlight[]>(f, '/api/admin/highlights')).map(highlightFromApi),
    reviewClip: async (id, action) =>
      highlightFromApi(
        await call<ApiHighlight>(f, `/api/admin/highlights/${encodeURIComponent(id)}/review`, {
          method: 'POST',
          body: JSON.stringify({ action })
        })
      ),
    reviewQueue: async (scope) => {
      if (scope.every_night) return call<ReviewQueue>(f, '/api/admin/gallery/review');
      const nights = scope.nights.map((n) => call<ReviewQueue>(f, `/api/days/${encodeURIComponent(n)}/gallery/review`));
      return mergeQueues(await Promise.all(nights));
    },
    decide: async (scope, kind, item, decision) => {
      const base = reviewBase(scope, item.nights);
      if (!base) throw new ApiError(403, 'That is for the officers of its poster’s raid night.');
      await call<unknown>(f, `${base}/${kind}/${item.id}/${decision}`, { method: 'POST' });
    }
  };
}

export const TWITCH_PLAYER = 'https://player.twitch.tv/?';
const CHANNEL = /^[a-z0-9_]{3,25}$/;
const HOSTNAME = /^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$/i;

/**
 * The iframe src for a live channel, or null when the login is not one Twitch could have. parentHost is the hub's own
 * hostname (Twitch requires it); anything that is not a plain hostname becomes localhost.
 */
export function twitchPlayerUrl(channel: string, parentHost: string): string | null {
  if (!CHANNEL.test(channel)) return null;
  const parent = HOSTNAME.test(parentHost) ? parentHost.toLowerCase() : 'localhost';
  return `${TWITCH_PLAYER}${new URLSearchParams({ channel, parent, autoplay: 'true', muted: 'true' })}`;
}

export const twitchChannelUrl = (channel: string) =>
  CHANNEL.test(channel) ? `https://www.twitch.tv/${channel}` : null;

/** "in 5 h", "in 40 min", or "soon", for when a photo leaves the carousel or a pick ends. */
export function timeLeft(until: string, now: Date = new Date()): string {
  const minutes = Math.floor((Date.parse(until) - now.getTime()) / 60_000);
  if (Number.isNaN(minutes) || minutes < 1) return 'soon';
  if (minutes < 60) return `in ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `in ${hours} h`;
  return `in ${Math.floor(hours / 24)} days`;
}

export interface MonthGroup {
  /** "October 2026" */
  label: string;
  photos: Photo[];
}

/** The archive's photos under a heading per month, keeping their order (newest first). Months are UTC. */
export function byMonth(photos: readonly Photo[]): MonthGroup[] {
  const groups: MonthGroup[] = [];
  const fmt = new Intl.DateTimeFormat('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' });
  for (const p of photos) {
    const label = fmt.format(new Date(p.created_at));
    const last = groups.at(-1);
    if (last?.label === label) last.photos.push(p);
    else groups.push({ label, photos: [p] });
  }
  return groups;
}

/** The next page joined to what is shown, without repeating a photo already there. */
export function appendPage(shown: readonly Photo[], page: ArchivePage): Photo[] {
  const seen = new Set(shown.map((p) => p.id));
  return [...shown, ...page.photos.filter((p) => !seen.has(p.id))];
}

/** Step through the carousel, wrapping at both ends. */
export function step(index: number, by: number, length: number): number {
  return length === 0 ? 0 : (((index + by) % length) + length) % length;
}

export function galleryError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to see the Highlights page.';
    case 403:
      return e.message && e.message !== 'Forbidden' ? e.message : 'That is for global officers.';
    case 404:
      return 'That is gone already; reload to see the page as it is now.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
