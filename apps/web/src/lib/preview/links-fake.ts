/** The preview's pinned night links: samples in the browser only, so a night's officer section works on GitHub Pages. */
import { ApiError } from '$lib/api';
import { LINK_LIMIT, linkProblem, type LinksBackend, type NightLink } from '$lib/night-links';

let nextId = 1;
const pinned: Record<string, NightLink[]> = {
  wed: [
    { id: nextId++, label: 'Kael’thas strategy', url: 'https://docs.google.com/document/d/preview-kael' },
    { id: nextId++, label: 'Wednesday roles and assignments', url: 'https://docs.google.com/spreadsheets/d/preview-roles' }
  ]
};

export const previewLinks: LinksBackend = {
  links: async (day) => [...(pinned[day] ?? [])],
  pin: async (day, label, url) => {
    const problem = linkProblem(label, url);
    if (problem) throw new ApiError(422, problem);
    const list = (pinned[day] ??= []);
    if (list.length >= LINK_LIMIT) throw new ApiError(409, `A night holds ${LINK_LIMIT} links; take one off first`);
    const link = { id: nextId++, label: label.trim().split(/\s+/).join(' '), url: url.trim() };
    list.push(link);
    return link;
  },
  unpin: async (day, id) => {
    const list = pinned[day] ?? [];
    if (!list.some((x) => x.id === id)) throw new ApiError(404, 'No such link on this night');
    pinned[day] = list.filter((x) => x.id !== id);
  }
};
