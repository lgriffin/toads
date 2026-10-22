import { describe, expect, it, vi } from 'vitest';
import { ApiError } from './api';
import {
  appendPage,
  byMonth,
  galleryError,
  hubGallery,
  mergeQueues,
  reviewBase,
  step,
  timeLeft,
  twitchChannelUrl,
  twitchPlayerUrl,
  type Photo
} from './gallery';
import { previewGallery } from './preview/gallery-fake';

const photo = (id: number, created_at: string): Photo => ({
  id,
  uploader_name: 'Hopscotch',
  caption: `photo ${id}`,
  width: 10,
  height: 10,
  created_at,
  carousel_until: created_at,
  image_url: `/api/gallery/photos/${id}/image`,
  thumbnail_url: `/api/gallery/photos/${id}/thumbnail`,
  removable: false
});

describe('twitch player', () => {
  it('builds the player URL itself from a checked channel', () => {
    const url = twitchPlayerUrl('hopscotch', 'toads.gg');
    expect(url).toBe('https://player.twitch.tv/?channel=hopscotch&parent=toads.gg&autoplay=true&muted=true');
  });

  it('refuses anything that is not a Twitch login', () => {
    for (const bad of ['', 'ab', 'Hopscotch', 'hop/../evil', 'a'.repeat(26), 'hop&parent=evil.example']) {
      expect(twitchPlayerUrl(bad, 'toads.gg')).toBeNull();
      expect(twitchChannelUrl(bad)).toBeNull();
    }
  });

  it('never passes a strange host as the parent', () => {
    expect(twitchPlayerUrl('hopscotch', 'evil.example&x=1')).toContain('parent=localhost');
    expect(twitchChannelUrl('hopscotch')).toBe('https://www.twitch.tv/hopscotch');
  });
});

describe('page helpers', () => {
  const now = new Date('2026-10-21T20:00:00Z');

  it('says how long is left in words', () => {
    expect(timeLeft('2026-10-21T20:40:00Z', now)).toBe('in 40 min');
    expect(timeLeft('2026-10-22T01:00:00Z', now)).toBe('in 5 h');
    expect(timeLeft('2026-10-26T20:00:00Z', now)).toBe('in 5 days');
    expect(timeLeft('2026-10-21T19:00:00Z', now)).toBe('soon');
    expect(timeLeft('not a date', now)).toBe('soon');
  });

  it('groups the archive by month, newest first', () => {
    const groups = byMonth([photo(3, '2026-10-20T10:00:00Z'), photo(2, '2026-10-01T00:00:00Z'), photo(1, '2026-09-30T23:00:00Z')]);
    expect(groups.map((g) => [g.label, g.photos.map((p) => p.id)])).toEqual([
      ['October 2026', [3, 2]],
      ['September 2026', [1]]
    ]);
  });

  it('adds a page without repeating photos', () => {
    const shown = [photo(5, '2026-10-20T10:00:00Z'), photo(4, '2026-10-19T10:00:00Z')];
    const page = { photos: [photo(4, '2026-10-19T10:00:00Z'), photo(3, '2026-10-18T10:00:00Z')], next_before: null, picked: [] };
    expect(appendPage(shown, page).map((p) => p.id)).toEqual([5, 4, 3]);
  });

  it('wraps the carousel at both ends', () => {
    expect([step(0, -1, 3), step(2, 1, 3), step(1, 1, 3), step(0, 1, 0)]).toEqual([2, 0, 2, 0]);
  });

  it('explains refusals', () => {
    expect(galleryError(new ApiError(403, 'Only the streamer, or a global officer, can take a stream down'))).toContain('streamer');
    expect(galleryError(new ApiError(403, 'Forbidden'))).toBe('That is for global officers.');
    expect(galleryError(new ApiError(404, 'No such photo'))).toContain('gone already');
    expect(galleryError(new ApiError(401, ''))).toContain('Sign in');
    expect(galleryError(new Error('boom'))).toContain('try again');
  });
});

describe('approval', () => {
  const waiting = (id: number, nights: string[]) => ({ ...photo(id, '2026-10-20T10:00:00Z'), waiting: true, nights });

  it('sends a night officer to a night they run that the poster is on', () => {
    expect(reviewBase({ every_night: true, nights: [] }, [])).toBe('/api/admin/gallery');
    expect(reviewBase({ every_night: false, nights: ['wed', 'sun'] }, ['sun'])).toBe('/api/days/sun/gallery');
    expect(reviewBase({ every_night: false, nights: ['wed'] }, ['sun'])).toBeNull();
    expect(reviewBase({ every_night: false, nights: ['wed'] }, [])).toBeNull();
  });

  it('merges nights’ queues without repeating a post', () => {
    const merged = mergeQueues([
      { photos: [waiting(3, ['wed', 'sun']), waiting(1, ['wed'])], streams: [] },
      { photos: [waiting(3, ['wed', 'sun'])], streams: [] }
    ]);
    expect(merged.photos.map((p) => p.id)).toEqual([1, 3]);
  });

  it('asks each night the officer runs, and decides on the right route', async () => {
    const f = vi.fn(async (path: string, init?: RequestInit) => {
      void init;
      return new Response(JSON.stringify(path.endsWith('review') ? { photos: [waiting(5, ['wed'])], streams: [] } : {}));
    });
    const g = hubGallery(f as unknown as typeof fetch);
    const queue = await g.reviewQueue({ every_night: false, nights: ['wed', 'sun'] });
    expect(queue.photos.map((p) => p.id)).toEqual([5]);
    await g.decide({ every_night: false, nights: ['wed', 'sun'] }, 'photos', queue.photos[0], 'approve');
    await g.reviewQueue({ every_night: true, nights: [] });
    await g.decide({ every_night: true, nights: [] }, 'streams', { ...queue.photos[0], nights: [] } as never, 'reject');
    await expect(g.decide({ every_night: false, nights: ['sun'] }, 'photos', queue.photos[0], 'approve')).rejects.toMatchObject({
      status: 403
    });
    expect(f.mock.calls.map(([path, init]) => `${init?.method ?? 'GET'} ${path}`)).toEqual([
      'GET /api/days/wed/gallery/review',
      'GET /api/days/sun/gallery/review',
      'POST /api/days/wed/gallery/photos/5/approve',
      'GET /api/admin/gallery/review',
      'POST /api/admin/gallery/streams/5/reject'
    ]);
  });
});

describe('hub backend', () => {
  it('calls the hub routes', async () => {
    const f = vi.fn(async (path: string, init?: RequestInit) => {
      void init;
      const body = path.includes('highlights')
        ? path.endsWith('review')
          ? { id: 4, title: 'x', provider: 'youtube', clip_id: 'dQw4w9WgXcQ', submitted_by: 'Hop', raid_id: null, boss: null, visibility: 'guild', status: 'published', created_at: '2026-10-20T00:00:00Z' }
          : []
        : {};
      return new Response(path.includes('/photos/9') && init?.method === 'DELETE' ? null : JSON.stringify(body), {
        status: path.includes('/photos/9') && init?.method === 'DELETE' ? 204 : 200
      });
    });
    const g = hubGallery(f as unknown as typeof fetch);
    await g.board();
    await g.archive(12);
    await g.archive();
    await g.picks();
    await g.removePhoto(9);
    await g.pickPhoto(9);
    await g.removeStream(2);
    await g.clips();
    await g.clipQueue();
    const reviewed = await g.reviewClip('4', 'publish_guild');
    expect(reviewed.clipId).toBe('dQw4w9WgXcQ');
    expect(f.mock.calls.map(([path, init]) => `${init?.method ?? 'GET'} ${path}`)).toEqual([
      'GET /api/gallery/board',
      'GET /api/gallery/photos?before=12',
      'GET /api/gallery/photos',
      'GET /api/gallery/photos-of-the-week',
      'DELETE /api/gallery/photos/9',
      'POST /api/admin/gallery/photos/9/photo-of-the-week',
      'DELETE /api/gallery/streams/2',
      'GET /api/highlights',
      'GET /api/admin/highlights',
      'POST /api/admin/highlights/4/review'
    ]);
  });
});

describe('preview backend', () => {
  const now = () => Date.parse('2026-10-21T20:00:00Z');

  it('shows a 48-hour carousel, a pick and a live stream', async () => {
    const g = previewGallery(false, now);
    const board = await g.board();
    expect(board.carousel.length).toBe(4);
    expect(board.photo_of_the_week?.chosen_by_name).toBe('Hadur');
    expect(board.streams.map((s) => s.channel)).toEqual(['lilypadd_tv']);
    expect(board.can_curate).toBe(false);
    const first = await g.archive();
    const second = await g.archive(first.next_before);
    expect([first.photos.length, second.photos.length, second.next_before]).toEqual([6, 6, null]);
  });

  it('lets a raider take down only their own photos, and refuses picks', async () => {
    const g = previewGallery(false, now);
    await g.removePhoto(12);
    await expect(g.removePhoto(11)).rejects.toMatchObject({ status: 403 });
    await expect(g.pickPhoto(11)).rejects.toMatchObject({ status: 403 });
    await expect(g.removeStream(1)).rejects.toMatchObject({ status: 403 });
    expect((await g.board()).carousel.map((p) => p.id)).toEqual([11, 10, 9]);
  });

  it('shows a raider their waiting posts and lets an officer decide them', async () => {
    const raider = await previewGallery(false, now).board();
    expect([raider.waiting_photos.map((p) => p.id), raider.waiting_streams.map((s) => s.channel), raider.review]).toEqual([
      [13],
      ['hopscotch_plays'],
      null
    ]);
    expect(raider.carousel.some((p) => p.id === 13)).toBe(false);
    await expect(previewGallery(false, now).reviewQueue({ every_night: true, nights: [] })).rejects.toMatchObject({ status: 403 });
    const g = previewGallery(true, now);
    const board = await g.board();
    expect(board.review).toEqual({ every_night: true, nights: [] });
    const queue = await g.reviewQueue(board.review!);
    await g.decide(board.review!, 'photos', queue.photos[0], 'approve');
    await g.decide(board.review!, 'streams', queue.streams[0], 'reject');
    const after = await g.board();
    expect([after.carousel[0].id, after.streams.map((s) => s.channel)]).toEqual([13, ['lilypadd_tv']]);
    expect(await g.reviewQueue(board.review!)).toEqual({ photos: [], streams: [] });
  });

  it('lets a global officer pick the photo of the week and work the clips', async () => {
    const g = previewGallery(true, now);
    const pick = await g.pickPhoto(10);
    expect((await g.board()).photo_of_the_week?.photo.id).toBe(10);
    expect((await g.picks())[0]).toEqual(pick);
    await g.removeStream(1);
    expect((await g.board()).streams).toEqual([]);
    const queue = await g.clipQueue();
    if (queue.length) {
      await g.reviewClip(queue[0].id, 'publish_guild');
      expect((await g.clips()).some((c) => c.id === queue[0].id)).toBe(true);
    }
  });
});
