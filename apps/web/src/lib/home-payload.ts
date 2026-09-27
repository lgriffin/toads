/**
 * The analyzer's home page widgets, exactly as wcl_app.home builds them (contract: guides/home_widgets.md in
 * lgriffin/warcraftlogs_project). The worker publishes a build to the API; GET /api/home/analyzer serves it.
 * Numbers arrive already formatted (`display`, `cells`), so nothing here formats them; `value`/`values` are raw.
 */

export type LinkKind = 'raid' | 'character' | 'player_page' | 'action';

export interface PayloadLink {
  kind: LinkKind;
  params: Record<string, string>;
}

export interface Tile {
  label: string;
  value: number | string | null;
  display: string;
  hint: string;
}

export interface Column {
  key: string;
  label: string;
  align: 'left' | 'right';
}

export interface Row {
  cells: Record<string, string>;
  values: Record<string, number | string | null>;
  link: PayloadLink | null;
}

export interface ListItem {
  label: string;
  detail: string;
  link: PayloadLink | null;
}

export interface Bar {
  label: string;
  value: number;
  display: string;
}

interface Base {
  id: string;
  title: string;
  size: 'full' | 'half';
  subtitle: string;
  link: PayloadLink | null;
  /** Set when there is nothing to show: draw this instead of a body. */
  empty: string;
  /** Set when building this widget failed. */
  error: string;
}

export type PayloadWidget =
  | (Base & { kind: 'stats'; tiles: Tile[] })
  | (Base & { kind: 'table'; columns: Column[]; rows: Row[] })
  | (Base & { kind: 'list'; items: ListItem[] })
  | (Base & { kind: 'bars'; bars: Bar[] })
  | (Base & { kind: 'actions'; actions: { id: string; label: string; description: string }[] });

/** GET /api/home/analyzer. `generated_at` is null until the worker has published a page. */
export interface AnalyzerPage {
  version: number;
  generated_at: string | null;
  widgets: PayloadWidget[];
}

/** The page version this hub draws (the analyzer's HOME_SCHEMA_VERSION). */
export const PAGE_VERSION = 1;

/** Where a payload link goes on the hub, or null when the hub has no page for it (the text shows unlinked). */
export function linkHref(link: PayloadLink | null | undefined, base: string): string | null {
  if (!link) return null;
  if (link.kind === 'raid' && /^[A-Za-z0-9_-]{1,64}$/.test(link.params.report_id ?? '')) {
    return `${base}/raids/${link.params.report_id}`;
  }
  if (link.kind === 'action' && link.params.id === 'raids.browse') return `${base}/raids`;
  return null;
}

/** A bar's length as a percentage of the largest value, as the contract asks. */
export function barPercent(bars: readonly Bar[], value: number): number {
  const max = Math.max(0, ...bars.map((b) => b.value));
  return max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
}

export function widgetById(page: AnalyzerPage | null, id: string): PayloadWidget | null {
  return page?.widgets.find((w) => w.id === id) ?? null;
}
