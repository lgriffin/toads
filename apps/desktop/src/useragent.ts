/**
 * The browser the app says it is. Electron's own user agent names the app and Electron, which some sign-in pages treat
 * as an unknown browser; dropping those two words leaves the plain Chrome it is built on.
 */
export function plainChrome(userAgent: string): string {
  return userAgent
    .replace(/\s(?:toads-hub-desktop|Toads Hub)\/\S+/g, '')
    .replace(/\sElectron\/\S+/g, '')
    .trim();
}
