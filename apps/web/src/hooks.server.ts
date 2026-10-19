import { redirect, type Handle } from '@sveltejs/kit';
import { base } from '$app/paths';
import { heldPublicRedirect } from '$lib/launch';

// Until the launch, a direct request for a held public page goes home before anything renders, so visitors without
// JavaScript reach our story too; the layout does the same for client-side navigation (src/lib/launch.ts).
export const handle: Handle = async ({ event, resolve }) => {
  const to = __PREVIEW__ ? null : heldPublicRedirect(event.url.pathname, base);
  if (to) redirect(307, to);
  return resolve(event);
};
