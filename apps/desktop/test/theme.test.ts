import { describe, expect, it } from 'vitest';
import { THEME_COLOR, themeColor } from '../../web/src/lib/display';
import { parseThemeSource, themeFromColor, windowBackground } from '../src/theme';

describe("following the site's theme", () => {
  it("takes the reader's picked theme from the site's theme-color tag, and the device without one", () => {
    expect(themeFromColor(themeColor('dark', true))).toBe('dark');
    expect(themeFromColor(themeColor('light', false))).toBe('light');
    expect(themeFromColor(themeColor('system', true))).toBe('system');
    expect(themeFromColor(THEME_COLOR.light.toUpperCase())).toBe('light');
    expect(themeFromColor('#ff0000')).toBe('system');
    expect(themeFromColor(undefined)).toBe('system');
  });

  it("paints the window in the site's page colour for the theme", () => {
    expect(windowBackground('dark', false)).toBe(THEME_COLOR.dark);
    expect(windowBackground('light', true)).toBe(THEME_COLOR.light);
    expect(windowBackground('system', true)).toBe(THEME_COLOR.dark);
    expect(windowBackground('system', false)).toBe(THEME_COLOR.light);
  });

  it('reads back only a theme source', () => {
    expect(parseThemeSource('light')).toBe('light');
    expect(parseThemeSource('sepia')).toBeNull();
  });
});
