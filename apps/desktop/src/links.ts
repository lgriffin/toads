/**
 * Where a link opens. The app window holds the hub and Discord's sign-in pages only; everything else (Google Docs,
 * Warcraft Logs, YouTube, a Discord channel) opens in the member's own browser, so a page from another site never runs
 * inside the app with the hub's session beside it.
 */

export type Destination = 'app' | 'browser' | 'blocked';

// Discord's own pages the sign-in passes through: the authorize screen, its login (with two-factor) and sign-up.
const DISCORD_HOSTS = new Set(['discord.com', 'www.discord.com']);
const DISCORD_SIGN_IN = ['/oauth2/authorize', '/login', '/register'];

// Schemes the default browser or mail client may open. discord: is the Discord app's own link.
const EXTERNAL = new Set(['https:', 'http:', 'mailto:', 'discord:']);

function parse(raw: string): URL | null {
  try {
    return new URL(raw);
  } catch {
    return null;
  }
}

/** True for the pages of Discord's sign-in, which must stay in the window so the hub's sign-in cookie comes back to it. */
export function isDiscordSignIn(raw: string): boolean {
  const url = parse(raw);
  if (!url || url.protocol !== 'https:' || !DISCORD_HOSTS.has(url.hostname)) return false;
  return DISCORD_SIGN_IN.some((p) => url.pathname === p || url.pathname.startsWith(`${p}/`));
}

/** Where a top-level navigation to `raw` goes, for the hub at `origin`. */
export function destination(raw: string, origin: string): Destination {
  const url = parse(raw);
  if (!url) return 'blocked';
  if (url.origin === origin || isDiscordSignIn(raw)) return 'app';
  if (EXTERNAL.has(url.protocol) && !url.username && !url.password) return 'browser';
  return 'blocked';
}

// Powers a hub page may ask for: notifications (the desk alerts), fullscreen (clips and streams) and writing to the
// clipboard (copy buttons). Camera, microphone, location, USB and the rest are always refused.
const HUB_PERMISSIONS = new Set(['notifications', 'clipboard-sanitized-write', 'fullscreen']);

/** Whether a page at `requestingUrl` gets `permission`. Only the hub's own pages get anything; fullscreen also for embeds. */
export function permissionAllowed(permission: string, requestingUrl: string, origin: string): boolean {
  if (!HUB_PERMISSIONS.has(permission)) return false;
  if (permission === 'fullscreen') return true;
  return parse(requestingUrl)?.origin === origin;
}
