/**
 * Links a raid night's officers pin to their night (docs/officer-board.md): the strategy doc, the role sheet, the
 * Google Drive folder. Officers keep those documents in Drive; the hub only links them. The routes are under
 * /api/days/{day}/links, for that night's officers and the global tier.
 */
import { ApiError, call, type Fetch } from './api';

export const LINK_LABEL_LIMIT = 80;
export const LINK_URL_LIMIT = 500;
export const LINK_LIMIT = 12;

export interface NightLink {
  id: number;
  label: string;
  url: string;
}

export interface LinksBackend {
  links(day: string): Promise<NightLink[]>;
  pin(day: string, label: string, url: string): Promise<NightLink>;
  unpin(day: string, id: number): Promise<void>;
}

const links = (day: string) => `/api/days/${encodeURIComponent(day)}/links`;

export function hubLinks(f: Fetch = fetch): LinksBackend {
  return {
    links: (day) => call<NightLink[]>(f, links(day)),
    pin: (day, label, url) => call<NightLink>(f, links(day), { method: 'POST', body: JSON.stringify({ label, url }) }),
    unpin: (day, id) => call<void>(f, `${links(day)}/${encodeURIComponent(id)}`, { method: 'DELETE' })
  };
}

/** The API's own check, so the form can say what is wrong before sending: a full https link to a real host. */
export function linkProblem(label: string, url: string): string | null {
  if (!label.trim()) return 'Give the link a name, such as “Kael’thas strategy”.';
  try {
    const u = new URL(url.trim());
    if (u.protocol !== 'https:' || !u.hostname.includes('.')) throw new Error('not https');
  } catch {
    return 'Paste a full https:// link, such as a Google Drive share link.';
  }
  return null;
}

/** "Google Drive" for docs.google.com and drive.google.com links, else the host, to say where a link goes. */
export function linkHost(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    return host === 'docs.google.com' || host === 'drive.google.com' ? 'Google Drive' : host;
  } catch {
    return '';
  }
}

export function linksError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  if (e.status === 403) return 'Only this raid night’s officers can pin links to it.';
  if (e.status === 404) return 'That link is gone; someone may have unpinned it.';
  return e.message || 'Something went wrong; try again.';
}
