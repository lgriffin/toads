/**
 * Interview panels (docs/recruitment.md): each raid night's officers pick the Discord members who interview that
 * night's applicants. The Toad Bot adds them to the interview room of everyone who applies for the night; a night
 * with no panel falls back to the `interviewers` in the community config. The hub's routes are under
 * /api/days/{day}/admin and only that night's officers (and the global tier) may call them.
 */
import { ApiError, call, type Fetch } from './api';

export interface Interviewer {
  /** A string: Discord ids are past the largest integer a browser holds exactly. */
  discord_user_id: string;
  username: string;
  display_name: string;
}

export interface InterviewPanel {
  raid_day: string;
  interviewers: Interviewer[];
  /** Who interviews when the panel is empty: the community config's list (usernames or ids). */
  fallback: string[];
}

/** As services/api/src/toads_api/community/recruitment.py PANEL_LIMIT. */
export const PANEL_LIMIT = 10;

/** What the panels page talks to: the hub, or the preview's in-browser fake. */
export interface PanelBackend {
  panel(day: string): Promise<InterviewPanel>;
  search(day: string, q: string): Promise<Interviewer[]>;
  add(day: string, discordUserId: string): Promise<InterviewPanel>;
  remove(day: string, discordUserId: string): Promise<InterviewPanel>;
}

const base = (day: string) => `/api/days/${encodeURIComponent(day)}/admin`;

export function hubPanels(f: Fetch = fetch): PanelBackend {
  return {
    panel: (day) => call<InterviewPanel>(f, `${base(day)}/interview-panel`),
    search: (day, q) => call<Interviewer[]>(f, `${base(day)}/discord-members?q=${encodeURIComponent(q)}`),
    add: (day, id) =>
      call<InterviewPanel>(f, `${base(day)}/interview-panel`, {
        method: 'POST',
        body: JSON.stringify({ discord_user_id: id })
      }),
    remove: (day, id) =>
      call<InterviewPanel>(f, `${base(day)}/interview-panel/${encodeURIComponent(id)}`, { method: 'DELETE' })
  };
}

/** Search results not already on the panel. */
export function notOnPanel(found: Interviewer[], panel: Interviewer[]): Interviewer[] {
  const on = new Set(panel.map((i) => i.discord_user_id));
  return found.filter((i) => !on.has(i.discord_user_id));
}

/** Who meets this night's applicants, in a sentence, for under the panel. */
export function whoInterviews(panel: InterviewPanel, night: string): string {
  const n = panel.interviewers.length;
  if (n) return `Everyone who applies for ${night} gets a private room with ${n === 1 ? 'this interviewer' : `these ${n} interviewers`}.`;
  if (panel.fallback.length) {
    return `No panel yet, so ${night} applicants meet the interviewers set on the server: ${panel.fallback.join(', ')}.`;
  }
  return `No panel yet, so ${night} applicants wait for an officer to open their interview room.`;
}

/** What to tell an officer when a panel call fails. */
export function panelError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to change interview panels.';
    case 403:
      return 'Only this raid night’s officers can change its panel.';
    case 503:
      return 'Discord is not answering; try again shortly.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
