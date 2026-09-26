import type { Post, Viewer, Visibility } from './community';
import type { RaidDay } from './mock/data';

function canSee(post: Post, viewer: Viewer): boolean {
  if (post.visibility === 'public') return true;
  if (!viewer.signedIn) return false;
  if (post.visibility === 'guild') return true;
  // raid_day
  if (!post.raidDay) return false;
  return viewer.globalOfficer || viewer.raidDays.includes(post.raidDay);
}

function when(post: Post): string {
  return post.publishedAt ?? post.createdAt;
}

/**
 * The posts feed: published only; public for everyone, guild for anyone signed in, raid_day only for viewers on that
 * raid day or global officers. Pinned first, then newest.
 */
export function visibleFeed(posts: readonly Post[], viewer: Viewer): Post[] {
  return posts
    .filter((p) => p.status === 'published' && canSee(p, viewer))
    .sort((a, b) => Number(b.pinned) - Number(a.pinned) || when(b).localeCompare(when(a)));
}

/** A one-paragraph teaser: whitespace collapsed, cut on a word boundary, with an ellipsis when shortened. */
export function excerpt(body: string, max = 160): string {
  const flat = body.replace(/\s+/g, ' ').trim();
  if (flat.length <= max) return flat;
  const cut = flat.slice(0, max - 1);
  const space = flat[max - 1] === ' ' ? cut.length : cut.lastIndexOf(' ');
  return `${(space > max * 0.6 ? cut.slice(0, space) : cut).replace(/[\s.,;:!?-]+$/, '')}…`;
}

export const POST_LIMITS = { title: 100, body: 2000 } as const;

export interface PostDraft {
  title: string;
  body: string;
  visibility: Visibility;
  raidDay: RaidDay | null;
}

export type PostErrors = Partial<Record<'title' | 'body' | 'visibility' | 'raidDay', string>>;

/** Compose-form checks. Body limit matches Discord's 2000-character message cap so cross-posting never truncates. */
export function validatePost(d: PostDraft, officerDays: RaidDay[], globalOfficer: boolean): PostErrors {
  const errors: PostErrors = {};
  const title = d.title.trim();
  const body = d.body.trim();
  if (!title) errors.title = 'Give the post a title.';
  else if (title.length > POST_LIMITS.title) errors.title = `Keep the title to ${POST_LIMITS.title} characters.`;
  if (!body) errors.body = 'Write something in the body.';
  else if (body.length > POST_LIMITS.body) errors.body = `Keep the body to ${POST_LIMITS.body} characters.`;
  if (!['public', 'guild', 'raid_day'].includes(d.visibility)) errors.visibility = 'Pick an audience.';
  if (d.visibility === 'raid_day') {
    if (!d.raidDay) errors.raidDay = 'Pick a raid day.';
    else if (!globalOfficer && !officerDays.includes(d.raidDay))
      errors.raidDay = `You are not an officer for ${d.raidDay}.`;
  }
  return errors;
}
