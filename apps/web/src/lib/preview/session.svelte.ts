/**
 * The static preview's pretend sign-in. There is no Discord and no API: the visitor picks the member or officer view
 * on /login and the choice lives in this browser only (localStorage, so it survives reloads). Everyone is Hopscotch,
 * with or without Wednesday's raid leader powers, so the sample badges, performance and spotlight stay theirs.
 */
import { defaultLayout } from '$lib/home';
import { parseRole, type PreviewRole } from './gate';
import { home } from './state.svelte';

const KEY = 'toads-preview-role';

/** `ready` turns true once the browser's saved choice is read; until then member pages wait rather than flash. */
export const previewSession = $state<{ role: PreviewRole | null; ready: boolean }>({ role: null, ready: false });

function store(role: PreviewRole | null) {
  try {
    if (role) localStorage.setItem(KEY, role);
    else localStorage.removeItem(KEY);
  } catch {
    // Storage blocked (private window, previews): the choice lasts until the page reloads.
  }
}

export function loadPreviewSession() {
  let role: PreviewRole | null = null;
  try {
    role = parseRole(localStorage.getItem(KEY));
  } catch {
    role = null;
  }
  previewSession.role = role;
  home.layout = defaultLayout(role === 'officer');
  previewSession.ready = true;
}

export function previewSignIn(role: PreviewRole) {
  previewSession.role = role;
  // The hub offers officer widgets to officers only, so each role starts from its own default home.
  home.layout = defaultLayout(role === 'officer');
  store(role);
}

export function previewSignOut() {
  previewSession.role = null;
  store(null);
}
