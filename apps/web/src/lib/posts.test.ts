import { describe, expect, it } from 'vitest';
import { ANONYMOUS, type Post, type Viewer } from './community';
import { excerpt, validatePost, visibleFeed } from './posts';

function post(id: string, over: Partial<Post> = {}): Post {
  return {
    id,
    title: id,
    body: 'body',
    authorName: 'Ribbitz',
    origin: 'hub',
    visibility: 'guild',
    raidDay: null,
    status: 'published',
    pinned: false,
    publishToDiscord: false,
    discordMessageId: null,
    editedSinceReview: false,
    createdAt: '2026-09-20T10:00:00Z',
    publishedAt: '2026-09-20T10:00:00Z',
    ...over
  };
}

const member = (over: Partial<Viewer> = {}): Viewer => ({
  name: 'Tadpole',
  signedIn: true,
  raidDays: ['Wednesday'],
  officerDays: [],
  globalOfficer: false,
  ...over
});

const posts: Post[] = [
  post('public', { visibility: 'public', publishedAt: '2026-09-21T10:00:00Z' }),
  post('guild', { publishedAt: '2026-09-22T10:00:00Z' }),
  post('wed', { visibility: 'raid_day', raidDay: 'Wednesday', publishedAt: '2026-09-23T10:00:00Z' }),
  post('sun', { visibility: 'raid_day', raidDay: 'Sunday', publishedAt: '2026-09-24T10:00:00Z' }),
  post('orphan-raid-day', { visibility: 'raid_day', raidDay: null }),
  post('draft', { status: 'draft', visibility: 'public' }),
  post('pending', { status: 'pending_review', visibility: 'public', origin: 'discord' }),
  post('hidden', { status: 'hidden', visibility: 'public' })
];

const ids = (v: Viewer) => visibleFeed(posts, v).map((p) => p.id);

describe('visibleFeed', () => {
  it('shows anonymous visitors public posts only', () => {
    expect(ids(ANONYMOUS)).toEqual(['public']);
  });
  it('shows members guild posts and their own raid days, newest first', () => {
    expect(ids(member())).toEqual(['wed', 'guild', 'public']);
    expect(ids(member({ raidDays: ['Sunday'] }))).toEqual(['sun', 'guild', 'public']);
    expect(ids(member({ raidDays: [] }))).toEqual(['guild', 'public']);
  });
  it('shows global officers every raid day', () => {
    expect(ids(member({ raidDays: [], globalOfficer: true }))).toEqual(['sun', 'wed', 'guild', 'public']);
  });
  it('does not widen raid-day scope for a raid-day officer of another day', () => {
    expect(ids(member({ raidDays: [], officerDays: ['Sunday'] }))).toEqual(['guild', 'public']);
  });
  it('never shows drafts, pending review or hidden posts', () => {
    const all = ids(member({ raidDays: ['Wednesday', 'Sunday'], globalOfficer: true }));
    expect(all).not.toContain('draft');
    expect(all).not.toContain('pending');
    expect(all).not.toContain('hidden');
  });
  it('puts pinned posts first', () => {
    const feed = visibleFeed([...posts, post('pinned-old', { pinned: true, publishedAt: '2026-09-01T00:00:00Z' })], member());
    expect(feed.map((p) => p.id)).toEqual(['pinned-old', 'wed', 'guild', 'public']);
  });
  it('falls back to created time and does not mutate its input', () => {
    const input = [post('a', { publishedAt: null, createdAt: '2026-09-01T00:00:00Z' }), post('b')];
    expect(visibleFeed(input, member()).map((p) => p.id)).toEqual(['b', 'a']);
    expect(input.map((p) => p.id)).toEqual(['a', 'b']);
  });
});

describe('excerpt', () => {
  it('keeps short text and collapses whitespace', () => {
    expect(excerpt('Hello\n\n  toads ')).toBe('Hello toads');
  });
  it('cuts on a word boundary with an ellipsis', () => {
    const got = excerpt('Bring fire resist for Hydross swaps and a stack of flasks.', 30);
    expect(got).toBe('Bring fire resist for Hydross…');
    expect(got.length).toBeLessThanOrEqual(30);
  });
  it('hard-cuts a single long word', () => {
    expect(excerpt('a'.repeat(50), 10)).toBe(`${'a'.repeat(9)}…`);
  });
  it('treats markup as plain text', () => {
    expect(excerpt('<b>hi</b>')).toBe('<b>hi</b>');
  });
});

describe('validatePost', () => {
  const ok = { title: 'Vashj prep', body: 'Bring resists', visibility: 'guild' as const, raidDay: null };
  it('accepts a good draft', () => {
    expect(validatePost(ok, [], false)).toEqual({});
  });
  it('requires title and body within limits', () => {
    expect(validatePost({ ...ok, title: '  ', body: '' }, [], false)).toEqual({
      title: expect.any(String),
      body: expect.any(String)
    });
    expect(validatePost({ ...ok, title: 'x'.repeat(101), body: 'y'.repeat(2001) }, [], false)).toHaveProperty('body');
  });
  it('scopes raid-day posts to the officer’s days', () => {
    const wed = { ...ok, visibility: 'raid_day' as const, raidDay: 'Wednesday' as const };
    expect(validatePost(wed, ['Wednesday'], false)).toEqual({});
    expect(validatePost(wed, ['Sunday'], false)).toHaveProperty('raidDay');
    expect(validatePost(wed, [], true)).toEqual({});
    expect(validatePost({ ...wed, raidDay: null }, ['Wednesday'], false)).toHaveProperty('raidDay');
  });
});
