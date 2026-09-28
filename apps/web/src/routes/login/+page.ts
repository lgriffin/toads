import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

// The static preview's pretend sign-in. The real site signs in at /auth/login with Discord.
export const load: PageLoad = () => {
  if (!__PREVIEW__) error(404, 'Not found');
};
