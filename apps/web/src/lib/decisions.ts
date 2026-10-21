/**
 * A raid night's Decisions panel (docs/recruitment.md): the applications waiting on the night's officers, with every
 * officer's notes, and a reject or accept for each. Reject declines the application and the Toad Bot deletes its
 * interview room; accept gives the applicant the night's raider role in Discord and welcomes them in their room. The
 * hub's routes are under /api/days/{day}/admin and only that night's officers (and the global tier) may call them.
 */
import { ApiError, call, type Fetch } from './api';
import type { ApplicationStatus } from './recruitment';

export type Role = 'Tank' | 'Healer' | 'Melee' | 'Ranged';

/** The fields of the API's Application the panel shows. */
export interface DecisionApplication {
  id: number;
  applicant_name: string;
  character_name: string;
  class_name: string;
  role: Role;
  secondary_role: Role | null;
  why_toads: string;
  raid_days: string[];
  logs_url: string | null;
  status: ApplicationStatus;
  interview_room_error: string | null;
  interview_room_url: string | null;
  created_at: string;
}

export interface ApplicationNote {
  id: number;
  application_id: number;
  /** null: the Toad Bot (or the hub) wrote it, saying what happened when it acted on a decision. */
  author_name: string | null;
  body: string;
  at: string;
}

export interface DecisionCard {
  application: DecisionApplication;
  notes: ApplicationNote[];
  decided_at: string | null;
}

export interface DecisionBoard {
  raid_day: string;
  waiting: DecisionCard[];
  decided: DecisionCard[];
}

export type Decision = 'accept' | 'reject';

/** As services/api/src/toads_api/community/schemas.py ApplicationNoteAdd. */
export const NOTE_LIMIT = 1000;

/** What the Decisions panel talks to: the hub, or the preview's in-browser fake. */
export interface DecisionBackend {
  board(day: string): Promise<DecisionBoard>;
  note(day: string, appId: number, body: string): Promise<ApplicationNote>;
  decide(day: string, appId: number, decision: Decision): Promise<DecisionApplication>;
}

const base = (day: string) => `/api/days/${encodeURIComponent(day)}/admin`;

export function hubDecisions(f: Fetch = fetch): DecisionBackend {
  return {
    board: (day) => call<DecisionBoard>(f, `${base(day)}/decisions`),
    note: (day, id, body) =>
      call<ApplicationNote>(f, `${base(day)}/applications/${id}/notes`, {
        method: 'POST',
        body: JSON.stringify({ body })
      }),
    decide: (day, id, decision) =>
      call<DecisionApplication>(f, `${base(day)}/applications/${id}/decision`, {
        method: 'POST',
        body: JSON.stringify({ decision })
      })
  };
}

/** "Healer, then Ranged". */
export function rolesLine(app: DecisionApplication): string {
  return app.secondary_role ? `${app.role}, then ${app.secondary_role}` : app.role;
}

/** Who wrote a note, in words. */
export function noteAuthor(note: ApplicationNote): string {
  return note.author_name ?? 'Toad Bot';
}

/** "21 Oct, 19:05" in the viewer's own time zone. */
export function when(iso: string, locale?: string): string {
  return new Date(iso).toLocaleString(locale, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/** What happens on each button, said before the officer confirms it. */
export function consequence(decision: Decision, app: DecisionApplication, night: string): string {
  const room = app.interview_room_url ? ' and the Toad Bot deletes their interview room' : '';
  return decision === 'reject'
    ? `${app.character_name} is declined${room}. They can apply again in 30 days.`
    : `${app.character_name} joins ${night}: the Toad Bot gives them the ${night} raider role in Discord${
        app.interview_room_url ? ' and welcomes them in their room' : ''
      }.`;
}

/** The outcome of a decided application, in a word or two. */
export function outcome(status: ApplicationStatus): string {
  switch (status) {
    case 'accepted':
      return 'Accepted';
    case 'declined':
      return 'Rejected';
    case 'withdrawn':
      return 'Withdrawn by the applicant';
    default:
      return status;
  }
}

/** What to tell an officer when a Decisions call fails. */
export function decisionError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to make recruitment decisions.';
    case 403:
      return 'Only this raid night’s officers can decide its applications.';
    case 404:
      return 'That application is not for this night any more; reload the page.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
