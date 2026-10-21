import { describe, expect, it } from 'vitest';
import { scrollable } from './scrollable';

function box(scrollWidth: number, clientWidth: number) {
  const attrs = new Map<string, string>();
  return {
    scrollWidth,
    clientWidth,
    firstElementChild: null,
    set tabIndex(v: number) {
      attrs.set('tabindex', String(v));
    },
    removeAttribute: (k: string) => attrs.delete(k),
    attrs
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
});
