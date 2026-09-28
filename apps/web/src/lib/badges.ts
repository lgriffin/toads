/**
 * Toads badges (wcl_app.badges in lgriffin/warcraftlogs_project, contract in its guides/badges.md): awards for turning
 * up to raids and coming prepared, each in up to four tiers named after item quality. Counts arrive formatted
 * (`display`), so nothing here formats numbers.
 */

export type Quality = '' | 'uncommon' | 'rare' | 'epic' | 'legendary';

export interface Badge {
  id: string;
  name: string;
  description: string;
  /** A stable icon id for artwork; `glyph` is drawn until there is some. */
  icon: string;
  glyph: string;
  /** 0 is not earned yet. */
  tier: number;
  quality: Quality;
  tier_name: string;
  value: number;
  display: string;
  /** How many times the first tier has been reached ("x20"). */
  stacks: number;
  /** The count the next tier needs; null at the top tier. */
  next_at: number | null;
  next_tier: string;
  /** 0 to 1 from this tier's threshold to the next; 1 at the top. */
  progress: number;
}

/** wcl_app PlayerBadges.to_dict(): every badge in play, earned or not, in catalogue order. */
export interface PlayerBadges {
  name: string;
  player_class: string;
  /** Tiers earned across every badge. */
  score: number;
  badges: Badge[];
}

/** One holder in the analyzer's `badges` home widget: earned badges only. */
export interface BadgeHolder {
  name: string;
  player_class: string;
  badges: Badge[];
  link: { kind: string; params: Record<string, string> } | null;
}

/** GET /api/me/badges (services/api/src/toads_api/home/badges.py). */
export interface MyBadges {
  /** Null until the worker has published. */
  generated_at: string | null;
  /** Null when none of the member's characters has raided with the guild. */
  entry: PlayerBadges | null;
  matched_by: 'chosen' | 'claim' | 'nickname' | null;
  /** The characters looked for, best first. */
  looked_for: string[];
}

/** The colours guides/badges.md suggests, WoW item quality. */
export const QUALITY_COLOURS: Record<Exclude<Quality, ''>, string> = {
  uncommon: '#1eff00',
  rare: '#0070dd',
  epic: '#a335ee',
  legendary: '#ff8000'
};

export function qualityColour(quality: Quality): string | null {
  return quality ? QUALITY_COLOURS[quality] : null;
}

/** The same hues lightened where needed so tier names stay readable on the dark theme (WCAG AA). */
const QUALITY_TEXT: Record<Exclude<Quality, ''>, string> = {
  uncommon: '#1eff00',
  rare: '#5aa9ff',
  epic: '#c58af9',
  legendary: '#ff8000'
};

export function qualityTextColour(quality: Quality): string | null {
  return quality ? QUALITY_TEXT[quality] : null;
}

export function earned(badges: readonly Badge[]): Badge[] {
  return badges.filter((b) => b.tier > 0);
}

/** "x20" once the first tier has been reached more than once, else "". */
export function stacksLabel(b: Pick<Badge, 'stacks'>): string {
  return b.stacks > 1 ? `x${b.stacks}` : '';
}

/** What a badge says on hover and to screen readers: "Loyal Toad, Epic: 42 raids. Legendary at 100." */
export function badgeLabel(b: Badge): string {
  const head = b.tier > 0 ? `${b.name}, ${b.tier_name}` : `${b.name}, not earned yet`;
  const next = b.next_at === null ? 'Top tier.' : `${b.next_tier} at ${b.next_at}.`;
  return `${head}: ${b.display}. ${next}`;
}

/** Progress to the next tier as a whole percentage, clamped to 0..100. */
export function progressPercent(b: Pick<Badge, 'progress'>): number {
  return Math.round(Math.max(0, Math.min(1, b.progress)) * 100);
}
