/**
 * View as (docs/admin.md "View as"): a super admin sees the hub as one raid night's raider or officer, to check what
 * those members see, launch hold included. The hub keeps the view in their session and answers every request with
 * that role's standing, so the pages need nothing of their own; it refuses every change but going back. The routes
 * are /api/admin/view-as and only super admins may call them (view_as).
 */
import { call, type Fetch } from './api';

export type ViewAsRole = 'raider' | 'officer';

export const VIEW_AS_ROLES: readonly ViewAsRole[] = ['raider', 'officer'];

/** The session's `view_as` while a super admin views the hub as someone else. */
export interface ViewAs {
  role: ViewAsRole;
  raid_day: string;
  /** The raid day's name, such as "Sunday". */
  name: string;
}

const BASE = '/api/admin/view-as';

export const startViewAs = (role: ViewAsRole, day: string, f: Fetch = fetch) =>
  call<ViewAs>(f, `${BASE}/${role}/${encodeURIComponent(day)}`, { method: 'PUT' });

export const stopViewAs = (f: Fetch = fetch) => call<void>(f, BASE, { method: 'DELETE' });

/** "Sunday raider", "Sunday officer". */
export function viewAsLabel(view: Pick<ViewAs, 'role' | 'name'>): string {
  return `${view.name} ${view.role}`;
}

/** The nights a super admin can view as, in config order: the session's day names, else the web app's own list. */
export function viewAsNights(dayNames: Record<string, string> | undefined, fallback: Record<string, string>) {
  return Object.entries(dayNames && Object.keys(dayNames).length ? dayNames : fallback).map(([id, name]) => ({ id, name }));
}
