import { describe, expect, it } from 'vitest';
import { scrollable } from './scrollable';

function box(scrollWidth: number, clientWidth: number) {
  const attrs = new Map<string, string>();
  const listeners = new Map<string, () => void>();
  return {
    scrollWidth,
    clientWidth,
    children: [],
    set tabIndex(v: number) {
      attrs.set('tabindex', String(v));
    },
    removeAttribute: (k: string) => attrs.delete(k),
    addEventListener: (type: string, fn: () => void) => listeners.set(type, fn),
    removeEventListener: (type: string) => listeners.delete(type),
    attrs,
    listeners
  };
}

describe('scrollable', () => {
  it('puts a box wider than its frame in the tab order and leaves one that fits out', () => {
    const wide = box(800, 300);
    scrollable(wide as unknown as HTMLElement).destroy();
    expect(wide.attrs.get('tabindex')).toBe('0');
    const fits = box(300, 300);
    scrollable(fits as unknown as HTMLElement).destroy();
    expect(fits.attrs.has('tabindex')).toBe(false);
  });

  it('rechecks when a <details> inside opens and the content grows wider', () => {
    const b = box(300, 300);
    const action = scrollable(b as unknown as HTMLElement);
    expect(b.attrs.has('tabindex')).toBe(false);
    b.scrollWidth = 900;
    b.listeners.get('toggle')?.();
    expect(b.attrs.get('tabindex')).toBe('0');
    action.destroy();
    expect(b.listeners.has('toggle')).toBe(false);
  });
});
