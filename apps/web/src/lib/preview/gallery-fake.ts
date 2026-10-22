/**
 * The preview's Highlights page: sample photos as if raiders had used the Toad Bot's /highlight, a photo of the week,
 * one live stream and the mock community's clips, kept in the browser only so the page works on GitHub Pages with no
 * hub behind it. Picks, takedowns, approvals and clip reviews last until the page reloads. The photos are drawn here
 * as SVG. One photo and one stream wait for an officer: the raider sees them as theirs, the officer view can decide them.
 */
import { ApiError } from '$lib/api';
import type { Highlight } from '$lib/community';
import type {
  ArchivePage,
  Board,
  GalleryBackend,
  Photo,
  Pick,
  ReviewQueue,
  Stream,
  WaitingPhoto,
  WaitingStream
} from '$lib/gallery';
import { community } from './state.svelte';

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const PAGE = 6;

/** A pond-coloured placeholder "photo" with its caption written on it. */
function picture(hue: number, label: string): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">` +
    `<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">` +
    `<stop offset="0" stop-color="hsl(${hue} 55% 38%)"/><stop offset="1" stop-color="hsl(${(hue + 60) % 360} 50% 16%)"/>` +
    `</linearGradient></defs><rect width="1200" height="800" fill="url(#g)"/>` +
    `<ellipse cx="600" cy="660" rx="520" ry="90" fill="hsl(${hue} 40% 12%)" opacity=".55"/>` +
    `<circle cx="930" cy="190" r="70" fill="hsl(50 90% 75%)" opacity=".8"/>` +
    `<text x="60" y="110" font-family="sans-serif" font-size="56" fill="white" opacity=".9">${label}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

interface Sample {
  id: number;
  name: string;
  caption: string;
  hue: number;
  ago: number;
  mine?: boolean;
  waiting?: boolean;
}

const SAMPLES: Sample[] = [
  { id: 13, name: 'Hopscotch', caption: 'Void Reaver loot pile', hue: 220, ago: HOUR / 2, mine: true, waiting: true },
  { id: 12, name: 'Hopscotch', caption: 'Gruul down with two minutes to spare', hue: 140, ago: 3 * HOUR, mine: true },
  { id: 11, name: 'Lilypadd', caption: 'Pond party at the Mag lair entrance', hue: 190, ago: 9 * HOUR },
  { id: 10, name: 'Ribbit', caption: 'Our first Prince kill, everyone alive', hue: 260, ago: 20 * HOUR },
  { id: 9, name: 'Hadur', caption: 'Wednesday team after Karazhan', hue: 30, ago: 41 * HOUR },
  { id: 8, name: 'Lilypadd', caption: 'Nightbane screenshot, finally', hue: 320, ago: 3 * DAY },
  { id: 7, name: 'Hopscotch', caption: 'Raid night selfie by the Shattrath fountain', hue: 100, ago: 6 * DAY, mine: true },
  { id: 6, name: 'Ribbit', caption: 'Curator kill', hue: 210, ago: 9 * DAY },
  { id: 5, name: 'Croak', caption: 'Bank alt doing the rounds', hue: 50, ago: 15 * DAY },
  { id: 4, name: 'Hadur', caption: 'Fishing in Zangarmarsh between pulls', hue: 170, ago: 24 * DAY },
  { id: 3, name: 'Lilypadd', caption: 'The whole pond lined up for Moroes', hue: 280, ago: 33 * DAY },
  { id: 2, name: 'Ribbit', caption: 'First guild meeting', hue: 10, ago: 41 * DAY },
  { id: 1, name: 'Hopscotch', caption: 'Where it all began', hue: 120, ago: 50 * DAY, mine: true }
];

/** `curate`: the super admin view (a global officer), who picks the photo of the week and takes anything down. */
export function previewGallery(curate: boolean, now: () => number = Date.now): GalleryBackend {
  const start = now();
  const photo = (s: Sample): Photo => {
    const at = start - s.ago;
    const src = picture(s.hue, s.caption.slice(0, 32));
    return {
      id: s.id,
      uploader_name: s.name,
      caption: s.caption,
      width: 1200,
      height: 800,
      created_at: new Date(at).toISOString(),
      carousel_until: new Date(at + 2 * DAY).toISOString(),
      image_url: src,
      thumbnail_url: src,
      removable: curate || Boolean(s.mine),
      waiting: Boolean(s.waiting)
    };
  };
  let photos = SAMPLES.map(photo);
  const shown = () => photos.filter((p) => !p.waiting);
  let picks: Pick[] = [
    { photo: photos[5], chosen_by_name: 'Hadur', starts_at: iso(start - 2 * DAY), ends_at: iso(start + 5 * DAY) },
    { photo: photos[9], chosen_by_name: 'Hadur', starts_at: iso(start - 9 * DAY), ends_at: iso(start - 2 * DAY) }
  ];
  let streams: Stream[] = [
    {
      id: 1,
      streamer_name: 'Lilypadd',
      channel: 'lilypadd_tv',
      title: 'Sunday Gruul and Mag, healer cam',
      started_at: iso(start - HOUR),
      ends_at: iso(start + 11 * HOUR),
      removable: curate
    },
    {
      id: 2,
      streamer_name: 'Hopscotch',
      channel: 'hopscotch_plays',
      title: 'Alt night in Shattrath',
      started_at: iso(start - HOUR / 4),
      ends_at: iso(start + 11 * HOUR),
      removable: true,
      waiting: true
    }
  ];
  const live = () => streams.filter((s) => !s.waiting);
  const queue = (): ReviewQueue => ({
    photos: photos.filter((p) => p.waiting).map((p): WaitingPhoto => ({ ...p, nights: ['wed'] })),
    streams: streams.filter((s) => s.waiting).map((s): WaitingStream => ({ ...s, nights: ['wed'] }))
  });

  const find = (id: number) => {
    const found = photos.find((p) => p.id === id);
    if (!found) throw new ApiError(404, 'No such photo');
    return found;
  };
  const current = () => picks.find((p) => Date.parse(p.starts_at) <= now() && now() < Date.parse(p.ends_at)) ?? null;
  const clip = (id: string): Highlight => {
    const found = community.highlights.find((h) => h.id === id);
    if (!found) throw new ApiError(404, 'No such highlight');
    return found;
  };

  return {
    board: async (): Promise<Board> => ({
      carousel: shown().filter((p) => Date.parse(p.carousel_until) > now()),
      photo_of_the_week: current(),
      streams: live(),
      checked_live: false,
      can_curate: curate,
      can_post: true,
      // The officer view decides the waiting posts; the raider view posted them.
      waiting_photos: curate ? [] : photos.filter((p) => p.waiting),
      waiting_streams: curate ? [] : streams.filter((s) => s.waiting),
      review: curate ? { every_night: true, nights: [] } : null
    }),
    archive: async (before): Promise<ArchivePage> => {
      const older = shown().filter((p) => before == null || p.id < before);
      const page = older.slice(0, PAGE);
      return {
        photos: page,
        next_before: older.length > PAGE ? page[page.length - 1].id : null,
        picked: page.filter((p) => picks.some((k) => k.photo.id === p.id)).map((p) => p.id)
      };
    },
    picks: async () => picks,
    removePhoto: async (id) => {
      if (!find(id).removable) throw new ApiError(403, 'Only the member who posted a photo, or a global officer, can take it down');
      photos = photos.filter((p) => p.id !== id);
      picks = picks.filter((p) => p.photo.id !== id);
    },
    pickPhoto: async (id) => {
      if (!curate) throw new ApiError(403, 'Forbidden');
      const at = now();
      picks = picks.map((p) => (Date.parse(p.starts_at) <= at && at < Date.parse(p.ends_at) ? { ...p, ends_at: iso(at) } : p));
      const pick = { photo: find(id), chosen_by_name: 'Hopscotch', starts_at: iso(at), ends_at: iso(at + 7 * DAY) };
      picks = [pick, ...picks];
      return pick;
    },
    removeStream: async (id) => {
      if (!streams.some((s) => s.id === id && s.removable)) throw new ApiError(403, 'Only the streamer, or a global officer, can take a stream down');
      streams = streams.filter((s) => s.id !== id);
    },
    clips: async () =>
      community.highlights
        .filter((h) => h.status === 'published')
        .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
    clipQueue: async () => {
      if (!curate) throw new ApiError(403, 'Forbidden');
      return community.highlights.filter((h) => h.status === 'submitted');
    },
    reviewQueue: async () => {
      if (!curate) throw new ApiError(403, 'Forbidden');
      return queue();
    },
    decide: async (_scope, kind, item, decision) => {
      if (!curate) throw new ApiError(403, 'Forbidden');
      if (kind === 'photos') {
        const at = now();
        photos =
          decision === 'reject'
            ? photos.filter((p) => p.id !== item.id)
            : photos.map((p) => (p.id === item.id ? { ...p, waiting: false, carousel_until: iso(at + 2 * DAY) } : p));
      } else {
        streams =
          decision === 'reject'
            ? streams.filter((s) => s.id !== item.id)
            : streams.map((s) => (s.id === item.id ? { ...s, waiting: false } : s));
      }
    },
    reviewClip: async (id, action) => {
      if (!curate) throw new ApiError(403, 'Forbidden');
      const h = clip(id);
      h.status = action === 'reject' ? 'rejected' : 'published';
      if (action !== 'reject') h.visibility = action === 'publish_public' ? 'public' : 'guild';
      return h;
    }
  };
}

function iso(ms: number): string {
  return new Date(ms).toISOString();
}
