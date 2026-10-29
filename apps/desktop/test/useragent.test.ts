import { expect, it } from 'vitest';
import { plainChrome } from '../src/useragent';

it('drops the app and Electron from the user agent, leaving plain Chrome', () => {
  const ua =
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) toads-hub-desktop/0.1.0 ' +
    'Chrome/140.0.0.0 Electron/44.10.0 Safari/537.36';
  expect(plainChrome(ua)).toBe(
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
  );
});
