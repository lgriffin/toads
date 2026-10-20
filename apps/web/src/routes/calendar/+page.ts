import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import type { PageLoad } from './$types';

// Members now add, change and delete absences on Me, and officers read the team's under Officers; old links land on Me.
export const load: PageLoad = () => redirect(308, `${base}/me${__PREVIEW__ ? '/' : ''}#absences`);
