import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import type { PageLoad } from './$types';

// Raids & Logs is now Logs; an old raid link lands on the same raid under /logs.
export const prerender = false;
export const load: PageLoad = ({ params }) =>
  redirect(308, `${base}/logs/${encodeURIComponent(params.id)}${__PREVIEW__ ? '/' : ''}`);
