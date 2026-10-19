import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import type { PageLoad } from './$types';

// Raids & Logs is now Logs; old links and bookmarks land there.
export const load: PageLoad = () => redirect(308, `${base}/logs${__PREVIEW__ ? '/' : ''}`);
