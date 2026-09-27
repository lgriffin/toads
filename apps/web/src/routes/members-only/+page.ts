import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

// REQ-HUB-AUTH-002: /auth/callback sends non-members here. The real site answers 403 and +error.svelte
// renders the members-only message; the static preview renders the same message as a normal page.
export const load: PageLoad = () => {
  if (!__PREVIEW__) error(403, 'Members only');
};
