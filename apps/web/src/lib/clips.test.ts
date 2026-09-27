import { describe, expect, it } from 'vitest';
import { EMBED_ORIGINS, embedUrl, parseClipUrl, type ClipProvider } from './clips';

const YT = 'Tq3vN8xLp2A';

describe('parseClipUrl accepts the allowlisted forms', () => {
  it.each([
    [`https://www.youtube.com/watch?v=${YT}`, 'youtube', YT],
    [`https://youtube.com/watch?v=${YT}&t=42s`, 'youtube', YT],
    [`https://m.youtube.com/watch?feature=share&v=${YT}`, 'youtube', YT],
    [`https://youtu.be/${YT}`, 'youtube', YT],
    [`https://youtu.be/${YT}?si=abc`, 'youtube', YT],
    [`https://www.youtube.com/shorts/${YT}`, 'youtube', YT],
    [`  https://WWW.YOUTUBE.COM/watch?v=${YT}  `, 'youtube', YT],
    ['https://clips.twitch.tv/HopscotchKicksVashj-aB3dEf9gHiJk', 'twitch', 'HopscotchKicksVashj-aB3dEf9gHiJk'],
    ['https://www.twitch.tv/ribbitz/clip/HopscotchKicksVashj-aB3d', 'twitch', 'HopscotchKicksVashj-aB3d'],
    ['https://streamable.com/k7x2qp', 'streamable', 'k7x2qp'],
    ['https://streamable.com/k7x2qp/', 'streamable', 'k7x2qp']
  ])('%s', (url, provider, clipId) => {
    expect(parseClipUrl(url)).toEqual({ provider, clipId });
  });
});

describe('parseClipUrl rejects hostile or unsupported input', () => {
  it.each([
    '',
    '   ',
    'not a url',
    `javascript:alert(1)//https://youtu.be/${YT}`,
    'javascript://youtube.com/%0aalert(1)',
    `data:text/html,<script>alert(1)</script>`,
    `data:text/html;base64,PHNjcmlwdD4=`,
    `http://www.youtube.com/watch?v=${YT}`,
    `http://youtu.be/${YT}`,
    `ftp://youtube.com/watch?v=${YT}`,
    `//youtube.com/watch?v=${YT}`,
    `https://youtube.com.evil.example/watch?v=${YT}`,
    `https://evil.example/youtube.com/watch?v=${YT}`,
    `https://evil.example/?u=https://youtube.com/watch?v=${YT}`,
    `https://notyoutube.com/watch?v=${YT}`,
    `https://youtube.co/watch?v=${YT}`,
    `https://user@youtube.com/watch?v=${YT}`,
    `https://youtube.com:pass@evil.example/watch?v=${YT}`,
    `https://youtube.com@evil.example/watch?v=${YT}`,
    `https://youtube.com:8443/watch?v=${YT}`,
    `https://youtube.com\\@evil.example/watch?v=${YT}`,
    `https://www.youtube.com/embed/${YT}`,
    `https://www.youtube.com/watch`,
    `https://www.youtube.com/watch?v=${YT}"onload="x`,
    `https://www.youtube.com/watch?v=abc"><svg>`,
    `https://www.youtube.com/watch?v=${YT}x`,
    `https://www.youtube.com/watch?v=short`,
    `https://youtu.be/${YT}/extra`,
    `https://youtu.be/${YT.slice(0, 10)}%27`,
    `https://www.youtube.com/shorts/${YT}/../../evil`,
    'https://clips.twitch.tv/embed?clip=abc',
    `https://clips.twitch.tv/${'a'.repeat(101)}`,
    'https://clips.twitch.tv/abc%22%3E%3Cscript%3E',
    'https://twitch.tv/clip/abc',
    'https://twitch.tv//clip/abc',
    'https://www.twitch.tv/chan/videos/123',
    'https://clips.twitch.tv.evil.example/abc',
    'https://streamable.com/e/k7x2qp',
    'https://streamable.com/K7X2QP',
    `https://streamable.com/${'a'.repeat(17)}`,
    'https://streamable.com/k7x2qp%2F..%2F',
    'https://streamable.com.evil.example/k7x2qp',
    `https://youtu.be/${'a'.repeat(3000)}`
  ])('%s', (url) => {
    expect(parseClipUrl(url)).toBeNull();
  });

  it('rejects non-strings at runtime', () => {
    expect(parseClipUrl(undefined as unknown as string)).toBeNull();
    expect(parseClipUrl(42 as unknown as string)).toBeNull();
  });
});

describe('embedUrl', () => {
  it('builds each provider embed', () => {
    expect(embedUrl({ provider: 'youtube', clipId: YT }, 'toads.example')).toBe(
      `https://www.youtube-nocookie.com/embed/${YT}`
    );
    expect(embedUrl({ provider: 'streamable', clipId: 'k7x2qp' }, 'toads.example')).toBe(
      'https://streamable.com/e/k7x2qp'
    );
    expect(embedUrl({ provider: 'twitch', clipId: 'Frog-aB3' }, 'lgriffin.github.io')).toBe(
      'https://clips.twitch.tv/embed?clip=Frog-aB3&parent=lgriffin.github.io'
    );
  });

  it('refuses ids that fail the regex', () => {
    for (const clipId of ['', `${YT}"`, '<script>', '../../x', 'a/b', 'a'.repeat(200), `javascript:alert(1)`]) {
      expect(embedUrl({ provider: 'youtube', clipId }, 'h')).toBeNull();
      expect(embedUrl({ provider: 'streamable', clipId }, 'h')).toBeNull();
    }
    expect(embedUrl({ provider: 'twitch', clipId: 'a&parent=evil.example' }, 'h')).toBeNull();
    expect(embedUrl({ provider: 'evil' as ClipProvider, clipId: YT }, 'h')).toBeNull();
  });

  it('never lets the parent host inject parameters', () => {
    const url = embedUrl({ provider: 'twitch', clipId: 'Frog' }, 'evil.example&clip=x"><');
    expect(url).toBe('https://clips.twitch.tv/embed?clip=Frog&parent=localhost');
  });

  it('always starts with the fixed provider origin', () => {
    const inputs: [ClipProvider, string, string][] = [
      ['youtube', YT, 'a.b'],
      ['twitch', 'x_y-Z', 'javascript:alert(1)'],
      ['twitch', 'abc', ''],
      ['streamable', 'k7x2qp', 'toads.example']
    ];
    for (const [provider, clipId, host] of inputs) {
      const url = embedUrl({ provider, clipId }, host);
      expect(url?.startsWith(EMBED_ORIGINS[provider])).toBe(true);
      expect(new URL(url!).protocol).toBe('https:');
    }
  });

  it('adds autoplay only when asked (after the visitor clicks)', () => {
    expect(embedUrl({ provider: 'youtube', clipId: YT }, 'h', { autoplay: true })).toBe(
      `${EMBED_ORIGINS.youtube}${YT}?autoplay=1`
    );
    expect(embedUrl({ provider: 'twitch', clipId: 'Frog' }, 'toads.example', { autoplay: true })).toBe(
      'https://clips.twitch.tv/embed?clip=Frog&parent=toads.example&autoplay=true'
    );
  });

  it('round-trips parsed links', () => {
    const parsed = parseClipUrl(`https://youtu.be/${YT}`)!;
    expect(embedUrl(parsed, 'toads.example')).toBe(`${EMBED_ORIGINS.youtube}${YT}`);
  });
});
