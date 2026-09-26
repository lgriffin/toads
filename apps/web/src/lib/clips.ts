/**
 * Highlight clip URLs: parse a pasted link into {provider, clipId} and build the embed URL ourselves.
 * Only the allowlisted providers, only https, and ids checked by regex. A raw URL never reaches an iframe.
 */

export type ClipProvider = 'youtube' | 'twitch' | 'streamable';

export interface ClipRef {
  provider: ClipProvider;
  clipId: string;
}

export const CLIP_ID_PATTERNS: Record<ClipProvider, RegExp> = {
  youtube: /^[A-Za-z0-9_-]{11}$/,
  twitch: /^[A-Za-z0-9_-]{1,100}$/,
  streamable: /^[a-z0-9]{1,16}$/
};

/** Fixed embed origins; embedUrl output always starts with one of these. */
export const EMBED_ORIGINS: Record<ClipProvider, string> = {
  youtube: 'https://www.youtube-nocookie.com/embed/',
  twitch: 'https://clips.twitch.tv/embed?',
  streamable: 'https://streamable.com/e/'
};

export const PROVIDER_LABELS: Record<ClipProvider, string> = {
  youtube: 'YouTube',
  twitch: 'Twitch',
  streamable: 'Streamable'
};

const YOUTUBE_HOSTS = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com']);
const TWITCH_HOSTS = new Set(['twitch.tv', 'www.twitch.tv', 'm.twitch.tv']);
const STREAMABLE_HOSTS = new Set(['streamable.com', 'www.streamable.com']);
const MAX_URL_LENGTH = 2048;

export function isValidClipId(provider: ClipProvider, clipId: string): boolean {
  return CLIP_ID_PATTERNS[provider].test(clipId);
}

function ref(provider: ClipProvider, clipId: string | null | undefined): ClipRef | null {
  return clipId && isValidClipId(provider, clipId) ? { provider, clipId } : null;
}

/** Path segments without the leading slash; a single trailing slash is tolerated. */
function segments(pathname: string): string[] {
  const trimmed = pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
  return trimmed.split('/').slice(1);
}

export function parseClipUrl(input: string): ClipRef | null {
  if (typeof input !== 'string') return null;
  const raw = input.trim();
  if (!raw || raw.length > MAX_URL_LENGTH) return null;
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return null;
  }
  // Refuse userinfo ("youtube.com@evil.example") and ports: the href must start with the bare https origin.
  if (url.protocol !== 'https:' || url.port || !url.href.startsWith(`https://${url.hostname}/`)) return null;
  const host = url.hostname.toLowerCase();
  const parts = segments(url.pathname);

  if (host === 'youtu.be') return parts.length === 1 ? ref('youtube', parts[0]) : null;
  if (YOUTUBE_HOSTS.has(host)) {
    if (parts.length === 1 && parts[0] === 'watch') return ref('youtube', url.searchParams.get('v'));
    if (parts.length === 2 && parts[0] === 'shorts') return ref('youtube', parts[1]);
    return null;
  }
  if (host === 'clips.twitch.tv') {
    return parts.length === 1 && parts[0] !== 'embed' ? ref('twitch', parts[0]) : null;
  }
  if (TWITCH_HOSTS.has(host)) {
    return parts.length === 3 && parts[1] === 'clip' && parts[0] !== '' ? ref('twitch', parts[2]) : null;
  }
  if (STREAMABLE_HOSTS.has(host)) {
    return parts.length === 1 ? ref('streamable', parts[0]) : null;
  }
  return null;
}

const HOSTNAME = /^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$/i;

/**
 * The iframe src for a stored clip, or null if the id fails its provider's regex.
 * parentHost is the hub's own hostname (Twitch requires it); anything that is not a plain hostname becomes localhost.
 */
export function embedUrl(clip: ClipRef, parentHost: string, opts: { autoplay?: boolean } = {}): string | null {
  if (!Object.hasOwn(EMBED_ORIGINS, clip.provider) || !isValidClipId(clip.provider, clip.clipId)) return null;
  const origin = EMBED_ORIGINS[clip.provider];
  switch (clip.provider) {
    case 'youtube':
    case 'streamable':
      return `${origin}${clip.clipId}${opts.autoplay ? '?autoplay=1' : ''}`;
    case 'twitch': {
      const parent = HOSTNAME.test(parentHost) ? parentHost.toLowerCase() : 'localhost';
      const params = new URLSearchParams({ clip: clip.clipId, parent });
      if (opts.autoplay) params.set('autoplay', 'true');
      return `${origin}${params}`;
    }
  }
}
