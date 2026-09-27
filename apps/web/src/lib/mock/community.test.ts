import { describe, expect, it } from 'vitest';
import { isValidClipId } from '../clips';
import { canTransition } from '../recruitment';
import { applications, highlights, posts, spotlights, story, viewer } from './community';

describe('community sample data', () => {
  it('has clip ids that pass the provider regexes', () => {
    for (const h of highlights) expect(isValidClipId(h.provider, h.clipId)).toBe(true);
    expect(new Set(highlights.map((h) => h.provider))).toEqual(new Set(['youtube', 'twitch', 'streamable']));
  });
  it('records only allowed application transitions', () => {
    for (const a of applications) {
      for (const e of a.events.slice(1)) expect(canTransition(e.from!, e.to)).toBe(true);
      expect(a.events.at(-1)!.to).toBe(a.status);
    }
    expect(new Set(applications.map((a) => a.status)).size).toBe(applications.length);
  });
  it('has a pending spotlight about the preview viewer', () => {
    expect(spotlights.some((s) => s.memberName === viewer.name && s.consent === 'pending')).toBe(true);
    expect(spotlights.some((s) => s.status === 'published' && s.consent === 'granted')).toBe(true);
  });
  it('has pinned, raid-day and both-origin posts', () => {
    expect(posts.some((p) => p.pinned && p.status === 'published')).toBe(true);
    expect(posts.some((p) => p.visibility === 'raid_day' && p.status === 'published')).toBe(true);
    expect(new Set(posts.map((p) => p.origin))).toEqual(new Set(['hub', 'discord']));
  });
  it('tells the story with progression from the raids', () => {
    expect(story.progression.length).toBeGreaterThan(0);
    expect(story.needs.length).toBeGreaterThanOrEqual(4);
  });
});
