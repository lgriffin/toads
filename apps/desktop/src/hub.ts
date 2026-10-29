/**
 * Which hub the app opens. The live site unless a maintainer points it at another one (a local dev stack on
 * http://localhost:8080, or a staging host) with TOADS_HUB_URL or `--hub=<url>`. Anything but https, or plain http to
 * this machine, is refused so a stray setting can never send members' Discord sign-in over the open network.
 */

export const LIVE_HUB = 'https://toads.gg';

const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

/** The hub's origin (scheme, host and port), or null when the address is not one the app will open. */
export function hubOrigin(raw: string): string | null {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return null;
  }
  if (url.username || url.password) return null;
  if (url.protocol === 'https:') return url.origin;
  if (url.protocol === 'http:' && LOCAL_HOSTS.has(url.hostname)) return url.origin;
  return null;
}

/** The hub to open: `--hub=` first, then TOADS_HUB_URL, then the live site. A bad override is an error, not a fallback. */
export function resolveHub(argv: readonly string[], env: Record<string, string | undefined>): string {
  const flag = argv.find((a) => a.startsWith('--hub='))?.slice('--hub='.length);
  const raw = flag ?? env.TOADS_HUB_URL ?? LIVE_HUB;
  const origin = hubOrigin(raw);
  if (!origin) throw new Error(`Not a hub address the app will open (https, or http to localhost): ${raw}`);
  return origin;
}

/** A hub path as an address on this hub. */
export function hubUrl(origin: string, path: string): string {
  return new URL(path, `${origin}/`).toString();
}
