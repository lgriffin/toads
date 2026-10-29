import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { expect, it } from 'vitest';
import { DEFAULT_PREFS, jsonFile, parsePrefs } from '../src/prefs';

it('parsePrefs keeps what is valid and defaults the rest', () => {
  expect(parsePrefs(undefined)).toEqual(DEFAULT_PREFS);
  expect(parsePrefs({ keepInTray: true, deskNotifications: 'no' })).toEqual({ keepInTray: true, deskNotifications: true });
});

it('jsonFile round-trips, and a missing or corrupt file reads as nothing', () => {
  const dir = mkdtempSync(join(tmpdir(), 'toads-prefs-'));
  const file = jsonFile(dir, 'prefs.json');
  expect(file.read()).toBeUndefined();
  file.write({ keepInTray: true });
  expect(file.read()).toEqual({ keepInTray: true });
  writeFileSync(join(dir, 'prefs.json'), '{not json');
  expect(file.read()).toBeUndefined();
  expect(() => jsonFile(join(dir, 'missing-dir'), 'x.json').write({})).not.toThrow();
});
