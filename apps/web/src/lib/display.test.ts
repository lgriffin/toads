import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { DEFAULT_DISPLAY, READING_KEY, THEME_KEY, loadDisplay, parseTheme, resolveTheme, saveDisplay } from './display';

function memory(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    data,
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
    removeItem: (k: string) => void data.delete(k)
  };
}

describe('display settings', () => {
  it('defaults to the pond at dusk with standard reading', () => {
    expect(loadDisplay(memory())).toEqual(DEFAULT_DISPLAY);
    expect(DEFAULT_DISPLAY).toEqual({ theme: 'dark', easyReading: false });
    expect(parseTheme('sepia')).toBe('dark');
  });

  it('follows the device only when the reader asks to', () => {
    expect(resolveTheme('system', true)).toBe('light');
    expect(resolveTheme('system', false)).toBe('dark');
    expect(resolveTheme('dark', true)).toBe('dark');
    expect(resolveTheme('light', false)).toBe('light');
  });

  it('remembers the choice and forgets easier reading when it is turned off', () => {
    const store = memory();
    saveDisplay({ theme: 'light', easyReading: true }, store);
    expect(loadDisplay(store)).toEqual({ theme: 'light', easyReading: true });
    saveDisplay({ theme: 'system', easyReading: false }, store);
    expect(store.data.get(THEME_KEY)).toBe('system');
    expect(store.data.has(READING_KEY)).toBe(false);
  });

  it('survives blocked storage', () => {
    const blocked = { getItem: () => { throw new Error('blocked'); } };
    expect(loadDisplay(blocked)).toEqual(DEFAULT_DISPLAY);
  });

  it('shares its keys with the script that paints the theme before the page loads', () => {
    const early = readFileSync(new URL('../../static/display.js', import.meta.url), 'utf8');
    expect(early).toContain(`'${THEME_KEY}'`);
    expect(early).toContain(`'${READING_KEY}'`);
    const html = readFileSync(new URL('../app.html', import.meta.url), 'utf8');
    expect(html).toContain('%sveltekit.assets%/display.js');
  });
});
