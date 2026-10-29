import { describe, expect, it } from 'vitest';
import { DEFAULT_SIZE, MIN_SIZE, parseState, restore } from '../src/window-state';

const SCREEN = { x: 0, y: 0, width: 1920, height: 1040 };
const RIGHT = { x: 1920, y: 0, width: 2560, height: 1400 };

describe('restore', () => {
  it('opens at the default size the first time', () => {
    expect(restore(null, [SCREEN])).toEqual({ ...DEFAULT_SIZE, maximized: false });
  });

  it('puts the window back where it was, maximised or not', () => {
    const saved = { x: 100, y: 80, width: 1400, height: 900, maximized: true };
    expect(restore(saved, [SCREEN])).toEqual(saved);
  });

  it('keeps the size but lets the window centre when its monitor has gone', () => {
    const saved = { x: 2200, y: 100, width: 1400, height: 900, maximized: false };
    expect(restore(saved, [SCREEN, RIGHT])).toEqual(saved);
    expect(restore(saved, [SCREEN])).toEqual({ width: 1400, height: 900, maximized: false });
  });

  it('will not open with the title bar above the screen or only a sliver showing', () => {
    expect(restore({ x: 100, y: -200, width: 1200, height: 800, maximized: false }, [SCREEN])).not.toHaveProperty('x');
    expect(restore({ x: 1900, y: 100, width: 1200, height: 800, maximized: false }, [SCREEN])).not.toHaveProperty('x');
  });

  it('never opens smaller than the minimum', () => {
    expect(restore({ x: 0, y: 0, width: 10, height: 10, maximized: false }, [SCREEN])).toMatchObject(MIN_SIZE);
  });
});

it('parseState refuses a damaged file', () => {
  expect(parseState({ x: 1, y: 2, width: 3, height: 4, maximized: false })).toEqual({ x: 1, y: 2, width: 3, height: 4, maximized: false });
  expect(parseState({ x: 1, y: 2, width: 3, height: 4 })).toBeNull();
  expect(parseState({ x: 'a', y: 2, width: 3, height: 4, maximized: false })).toBeNull();
  expect(parseState(undefined)).toBeNull();
});
