/**
 * Turns the API's snake_case community JSON into the camelCase shapes the components use ($lib/community).
 * Pure functions so they can be tested without a server.
 */
import type { ClipProvider } from './clips';
import type { Highlight, NeedPriority, Post, PostOrigin, PostStatus, RecruitmentNeed, Visibility, ZoneProgress } from './community';
import type { RaidDay, Role } from './mock/data';

export interface ApiPost {
  id: number;
  title: string;
  body: string;
  author_name: string;
  origin: PostOrigin;
  visibility: Visibility;
  raid_day: string | null;
  status: PostStatus;
  pinned: boolean;
  publish_to_discord: boolean;
  discord_message_id: number | string | null;
  edited_since_review: boolean;
  created_at: string;
  published_at: string | null;
}

export interface ApiHighlight {
  id: number;
  title: string;
  provider: ClipProvider;
  clip_id: string;
  submitted_by: string;
  raid_id: string | null;
  boss: string | null;
  visibility: Visibility;
  status: Highlight['status'];
  created_at: string;
}

export interface ApiNeed {
  class_name: string;
  spec: string;
  role: Role;
  priority: NeedPriority;
  raid_days: string[];
}

/** GET /api/public/story, the parts the hub home uses. */
export interface ApiStory {
  progression: ZoneProgress[];
  needs: ApiNeed[];
}

/** GET /api/desk */
export interface DeskSummary {
  applications_waiting: number;
  posts_to_curate: number;
  highlights_to_review: number;
  spotlights_awaiting_consent: number;
}

// The API names raid days by config id ("wed"); the components only print them, so the id stands in for the name.
const day = (id: string) => id as RaidDay;

export function postFromApi(p: ApiPost): Post {
  return {
    id: String(p.id),
    title: p.title,
    body: p.body,
    authorName: p.author_name,
    origin: p.origin,
    visibility: p.visibility,
    raidDay: p.raid_day === null ? null : day(p.raid_day),
    status: p.status,
    pinned: p.pinned,
    publishToDiscord: p.publish_to_discord,
    discordMessageId: p.discord_message_id === null ? null : String(p.discord_message_id),
    editedSinceReview: p.edited_since_review,
    createdAt: p.created_at,
    publishedAt: p.published_at
  };
}

export function highlightFromApi(h: ApiHighlight): Highlight {
  return {
    id: String(h.id),
    title: h.title,
    provider: h.provider,
    clipId: h.clip_id,
    submittedBy: h.submitted_by,
    raidId: h.raid_id,
    boss: h.boss,
    // Highlights are never raid-day scoped; anything but public reads as guild-only.
    visibility: h.visibility === 'public' ? 'public' : 'guild',
    status: h.status,
    createdAt: h.created_at
  };
}

export function needFromApi(n: ApiNeed): RecruitmentNeed {
  return { className: n.class_name, spec: n.spec, role: n.role, priority: n.priority, raidDays: n.raid_days.map(day) };
}

export interface DeskLine {
  label: string;
  count: number;
  /** Anchor on the officers page. */
  href: string;
}

export function deskLines(d: DeskSummary): DeskLine[] {
  return [
    { label: 'Applications waiting', count: d.applications_waiting, href: '#applications' },
    { label: 'Discord posts to curate', count: d.posts_to_curate, href: '#curation' },
    { label: 'Highlight submissions', count: d.highlights_to_review, href: '#highlights' },
    { label: 'Spotlights awaiting consent', count: d.spotlights_awaiting_consent, href: '#spotlights' }
  ];
}
