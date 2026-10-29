/**
 * Display settings each reader picks for themselves: the theme (the pond at dusk, the pond by day, or whatever their
 * device asks for) and easier reading (larger text, more space between lines, plain headings, underlined links). They
 * live in this browser only. static/display.js applies the saved choice before the first paint, so a light-theme reader
 * never sees a dark flash; this module changes it afterwards. Keep the two in step.
 */

export type Theme = 'dark' | 'light' | 'system';

export interface Display {
  theme: Theme;
  easyReading: boolean;
}

export const THEME_KEY = 'toads-theme';
export const READING_KEY = 'toads-reading';

/** The pond at dusk is the guild's look, so it is the default until a reader picks otherwise. */
export const DEFAULT_DISPLAY: Display = { theme: 'dark', easyReading: false };

export const THEMES: readonly { id: Theme; label: string }[] = [
  { id: 'dark', label: 'Dark' },
  { id: 'light', label: 'Light' },
  { id: 'system', label: 'Match my device' }
];

/** The page colour (--ink in theme.css) of each theme; display.test.ts holds the two files to the same values. */
export const THEME_COLOR: Record<'dark' | 'light', string> = { dark: '#120f33', light: '#f6f1e5' };

/**
 * The theme-color meta tag for a theme choice: the page colour when the reader picked dark or light, none when they
 * follow their device. Browsers tint their own bars with it, and the desktop app reads it to match its window, title
 * bar and offline page to the site (no tag: it follows the device too). static/display.js writes the same tag.
 */
export function themeColor(theme: Theme, prefersLight: boolean): string | null {
  return theme === 'system' ? null : THEME_COLOR[resolveTheme(theme, prefersLight)];
}

export function parseTheme(value: string | null | undefined): Theme {
  return value === 'light' || value === 'system' || value === 'dark' ? value : DEFAULT_DISPLAY.theme;
}

/** The theme the page paints: a "system" choice follows the device's light or dark setting. */
export function resolveTheme(theme: Theme, prefersLight: boolean): 'dark' | 'light' {
  return theme === 'system' ? (prefersLight ? 'light' : 'dark') : theme;
}

export function loadDisplay(storage: Pick<Storage, 'getItem'> | undefined = safeStorage()): Display {
  try {
    return { theme: parseTheme(storage?.getItem(THEME_KEY)), easyReading: storage?.getItem(READING_KEY) === 'easy' };
  } catch {
    return { ...DEFAULT_DISPLAY };
  }
}

export function saveDisplay(display: Display, storage: Pick<Storage, 'setItem' | 'removeItem'> | undefined = safeStorage()) {
  try {
    storage?.setItem(THEME_KEY, display.theme);
    if (display.easyReading) storage?.setItem(READING_KEY, 'easy');
    else storage?.removeItem(READING_KEY);
  } catch {
    // Storage blocked (private window): the choice lasts until the page reloads.
  }
}

/** Paint the choice on <html>: data-theme picks the colour tokens, data-reading the easier reading rules. */
export function applyDisplay(display: Display, root: HTMLElement = document.documentElement) {
  const light = typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: light)').matches;
  root.dataset.theme = resolveTheme(display.theme, light);
  const color = themeColor(display.theme, light);
  let meta = root.ownerDocument.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (color === null) meta?.remove();
  else {
    if (!meta) {
      meta = root.ownerDocument.createElement('meta');
      meta.name = 'theme-color';
      root.ownerDocument.head.append(meta);
    }
    meta.content = color;
  }
  if (display.easyReading) root.dataset.reading = 'easy';
  else delete root.dataset.reading;
}

function safeStorage(): Storage | undefined {
  try {
    return typeof localStorage === 'undefined' ? undefined : localStorage;
  } catch {
    return undefined;
  }
}
