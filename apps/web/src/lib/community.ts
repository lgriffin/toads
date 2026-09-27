/**
 * Community layer types: camelCase mirrors of the API's snake_case JSON (see the shared design).
 * Posts, applications, recruitment needs, highlights and spotlights.
 */
import type { ClipProvider } from './clips';
import type { RaidDay, Role } from './mock/data';
import type { ApplicationStatus } from './recruitment';

export type Visibility = 'public' | 'guild' | 'raid_day';
export type PostOrigin = 'hub' | 'discord';
export type PostStatus = 'draft' | 'pending_review' | 'published' | 'hidden';

export interface Post {
  id: string;
  title: string;
  /** Plain text with newlines; never HTML. */
  body: string;
  authorName: string;
  origin: PostOrigin;
  visibility: Visibility;
  raidDay: RaidDay | null;
  status: PostStatus;
  pinned: boolean;
  publishToDiscord: boolean;
  discordMessageId: string | null;
  editedSinceReview: boolean;
  createdAt: string;
  publishedAt: string | null;
}

export interface ApplicationEvent {
  at: string;
  actorName: string;
  from: ApplicationStatus | null;
  to: ApplicationStatus;
  note: string;
}

export interface Application {
  id: string;
  memberId: string;
  applicantName: string;
  characterName: string;
  className: string;
  spec: string;
  role: Role;
  /** Empty means any raid day. */
  raidDays: RaidDay[];
  experience: string;
  availability: string;
  logsUrl: string | null;
  status: ApplicationStatus;
  interviewChannelId: string | null;
  events: ApplicationEvent[];
  createdAt: string;
}

export type NeedPriority = 'high' | 'medium' | 'low';

export interface RecruitmentNeed {
  className: string;
  spec: string;
  role: Role;
  priority: NeedPriority;
  raidDays: RaidDay[];
}

export type HighlightStatus = 'submitted' | 'published' | 'rejected';

export interface Highlight {
  id: string;
  title: string;
  provider: ClipProvider;
  clipId: string;
  submittedBy: string;
  raidId: string | null;
  boss: string | null;
  visibility: 'public' | 'guild';
  status: HighlightStatus;
  createdAt: string;
}

export type SpotlightConsent = 'pending' | 'granted' | 'declined';
export type SpotlightStatus = 'draft' | 'published' | 'retired';

export interface Spotlight {
  id: string;
  memberName: string;
  characterName: string;
  className: string;
  headline: string;
  body: string;
  writtenBy: string;
  consent: SpotlightConsent;
  status: SpotlightStatus;
  createdAt: string;
}

export interface ZoneProgress {
  zone: string;
  killed: number;
  total: number;
}

/** GET /api/public/story */
export interface PublicStory {
  guild: string;
  realm: string;
  tagline: string;
  story: string[];
  discordInvite: string;
  progression: ZoneProgress[];
  needs: RecruitmentNeed[];
  posts: Post[];
  highlights: Highlight[];
  spotlights: Spotlight[];
}

/** Who is looking. Anonymous visitors see public content only. */
export interface Viewer {
  name: string;
  signedIn: boolean;
  raidDays: RaidDay[];
  /** Raid days this viewer is an officer for. */
  officerDays: RaidDay[];
  globalOfficer: boolean;
}

export const ANONYMOUS: Viewer = { name: '', signedIn: false, raidDays: [], officerDays: [], globalOfficer: false };

export function isOfficer(v: Viewer): boolean {
  return v.globalOfficer || v.officerDays.length > 0;
}

/** Only published spotlights whose subject has granted consent are ever shown. */
export function visibleSpotlights(spotlights: Spotlight[]): Spotlight[] {
  return spotlights.filter((s) => s.status === 'published' && s.consent === 'granted');
}

/** Published highlights; guild-only reels need a signed-in viewer. Newest first. */
export function visibleHighlights(highlights: Highlight[], viewer: Viewer): Highlight[] {
  return highlights
    .filter((h) => h.status === 'published' && (h.visibility === 'public' || viewer.signedIn))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}
