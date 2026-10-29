// The desktop app's view of the site (src/lib/desktop.ts): built with the site, so it always matches this deploy.
import { json } from '@sveltejs/kit';
import { desktopSite } from '$lib/desktop';

export const prerender = true;
export const trailingSlash = 'never';

export function GET() {
  return json(desktopSite());
}
