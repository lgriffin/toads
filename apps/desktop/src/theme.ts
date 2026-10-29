/**
 * The app's colours follow the reader's theme on the site (Display in the account menu): dark, light, or their device.
 * The site says which with its theme-color tag (apps/web/src/lib/display.ts themeColor): a picked theme's page colour,
 * or no tag for a reader who follows their device. The app turns that into Electron's theme source, so the title bar,
 * native menus and the offline page match the site, and paints the window in the page colour while a page loads.
 */
import { THEME_COLOR } from '../../web/src/lib/display';

export type ThemeSource = 'dark' | 'light' | 'system';

/** The theme a hub page's theme-color asks for. No tag, or a colour that is not one of the site's, follows the device. */
export function themeFromColor(color: string | null | undefined): ThemeSource {
  const c = color?.trim().toLowerCase();
  if (c === THEME_COLOR.dark) return 'dark';
  if (c === THEME_COLOR.light) return 'light';
  return 'system';
}

/** The window's colour behind a loading page, so it never flashes the other theme. */
export function windowBackground(source: ThemeSource, deviceDark: boolean): string {
  const dark = source === 'system' ? deviceDark : source === 'dark';
  return dark ? THEME_COLOR.dark : THEME_COLOR.light;
}

export function parseThemeSource(value: unknown): ThemeSource | null {
  return value === 'dark' || value === 'light' || value === 'system' ? value : null;
}
