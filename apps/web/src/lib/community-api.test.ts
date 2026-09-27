import { describe, expect, it } from 'vitest';
import { deskLines, highlightFromApi, needFromApi, postFromApi } from './community-api';

describe('community API mapping', () => {
  it('maps a post and keeps big Discord ids as strings', () => {
    const p = postFromApi({
      id: 7,
      title: 'Raid night',
      body: 'See you at 19:30',
      author_name: 'Hops',
      origin: 'discord',
      visibility: 'guild',
      raid_day: 'wed',
      status: 'published',
      pinned: true,
      publish_to_discord: false,
      discord_message_id: '1234567890123456789',
      edited_since_review: false,
      created_at: '2026-09-27T10:00:00Z',
      published_at: null
    });
    expect(p).toMatchObject({ id: '7', authorName: 'Hops', raidDay: 'wed', discordMessageId: '1234567890123456789' });
  });

  it('maps a highlight', () => {
    const h = highlightFromApi({
      id: 3,
      title: 'Lurker',
      provider: 'youtube',
      clip_id: 'abc',
      submitted_by: 'Ribbit',
      raid_id: null,
      boss: 'The Lurker Below',
      visibility: 'guild',
      status: 'published',
      created_at: '2026-09-27T10:00:00Z'
    });
    expect(h).toMatchObject({ id: '3', clipId: 'abc', submittedBy: 'Ribbit', visibility: 'guild' });
  });

  it('maps a recruitment need', () => {
    const n = needFromApi({ class_name: 'Shaman', spec: 'Restoration', role: 'Healer', priority: 'high', raid_days: ['sun'] });
    expect(n).toEqual({ className: 'Shaman', spec: 'Restoration', role: 'Healer', priority: 'high', raidDays: ['sun'] });
  });

  it('lists the desk in a fixed order', () => {
    const lines = deskLines({
      applications_waiting: 2,
      posts_to_curate: 1,
      highlights_to_review: 0,
      spotlights_awaiting_consent: 3
    });
    expect(lines.map((l) => l.count)).toEqual([2, 1, 0, 3]);
  });
});
