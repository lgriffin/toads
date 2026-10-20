/**
 * The preview's interview panels: a few sample Discord members to search, and panels kept in the browser only, so
 * the page works on GitHub Pages with no hub behind it. Changes last until the page reloads.
 */
import { ApiError } from '$lib/api';
import { PANEL_LIMIT, type InterviewPanel, type Interviewer, type PanelBackend } from '$lib/interview-panels';

const MEMBERS: Interviewer[] = [
  ['301', '_gallagher', 'Gallagher'],
  ['302', 'hadur117', 'Hadur'],
  ['303', 'hopscotch', 'Hopscotch'],
  ['304', 'lilypadd', 'Lilypadd'],
  ['305', 'ribbit', 'Ribbit'],
  ['306', 'tadpole', 'Tadpole']
].map(([discord_user_id, username, display_name]) => ({ discord_user_id, username, display_name }));

const FALLBACK = ['_gallagher', 'hadur117'];

export function previewPanels(): PanelBackend {
  const panels: Record<string, Interviewer[]> = { wed: [MEMBERS[0], MEMBERS[1]], sun: [] };
  const view = (day: string): InterviewPanel => ({
    raid_day: day,
    interviewers: [...(panels[day] ?? [])],
    fallback: FALLBACK
  });
  return {
    panel: async (day) => view(day),
    search: async (_day, q) => {
      const query = q.trim().toLowerCase();
      return MEMBERS.filter((m) => m.username.startsWith(query) || m.display_name.toLowerCase().startsWith(query));
    },
    add: async (day, id) => {
      const panel = (panels[day] ??= []);
      const who = MEMBERS.find((m) => m.discord_user_id === id);
      if (!who) throw new ApiError(422, 'They are not in the Toads Discord');
      if (panel.some((m) => m.discord_user_id === id)) {
        throw new ApiError(409, `${who.display_name} is already on this night's panel`);
      }
      if (panel.length >= PANEL_LIMIT) {
        throw new ApiError(409, `A panel holds ${PANEL_LIMIT} interviewers; remove someone first`);
      }
      panel.push(who);
      return view(day);
    },
    remove: async (day, id) => {
      panels[day] = (panels[day] ?? []).filter((m) => m.discord_user_id !== id);
      return view(day);
    }
  };
}
