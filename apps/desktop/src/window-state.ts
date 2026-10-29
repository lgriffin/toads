/** Where the window was when the app last closed, put back only where a display can still show it. */

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface WindowState extends Rect {
  maximized: boolean;
}

export const DEFAULT_SIZE = { width: 1280, height: 860 } as const;
export const MIN_SIZE = { width: 720, height: 520 } as const;

/** How much of the window must sit on a display to restore it there: enough to grab its title bar. */
const VISIBLE = 64;

export function parseState(body: unknown): WindowState | null {
  if (!body || typeof body !== 'object') return null;
  const s = body as Record<string, unknown>;
  const nums = ['x', 'y', 'width', 'height'].every((k) => Number.isFinite(s[k]));
  if (!nums || typeof s.maximized !== 'boolean') return null;
  return { x: s.x as number, y: s.y as number, width: s.width as number, height: s.height as number, maximized: s.maximized };
}

function overlap(a: Rect, b: Rect): { w: number; h: number } {
  const w = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
  return { w, h };
}

/**
 * The bounds to open at. Saved bounds are kept when enough of them sits on one of the displays' work areas (a monitor
 * that was unplugged since would leave the window off screen); otherwise the default size, centred by the caller.
 */
export function restore(saved: WindowState | null, workAreas: readonly Rect[]): Partial<Rect> & { maximized: boolean } {
  if (!saved) return { ...DEFAULT_SIZE, maximized: false };
  const width = Math.max(saved.width, MIN_SIZE.width);
  const height = Math.max(saved.height, MIN_SIZE.height);
  const rect = { x: saved.x, y: saved.y, width, height };
  const onScreen = workAreas.some((area) => {
    const o = overlap(rect, area);
    return o.w >= VISIBLE && o.h >= VISIBLE && saved.y >= area.y;
  });
  return onScreen ? { ...rect, maximized: saved.maximized } : { width, height, maximized: saved.maximized };
}
