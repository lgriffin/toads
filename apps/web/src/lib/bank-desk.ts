/**
 * The bank request desk (docs/bank-desk.md): members ask the guild bank for an item with the Toad Bot's
 * `/bankrequest <item> <quantity>` or on the site, and officers approve or deny each request with a message that the
 * Toad Bot DMs back. Every request stays on the member's record. It needs no bank snapshot, so it works before the
 * bank's stock is imported.
 *
 * Officers (and members a super admin granted the bank's upkeep) work the desk under one of their raid days' routes;
 * requests do not belong to a night yet, so every night's officers see the same desk.
 */
import { ApiError, call, type Fetch } from './api';

export type RequestStatus = 'pending' | 'approved' | 'denied';
export type Notice = 'queued' | 'sent' | 'failed';
export type Verdict = 'approve' | 'deny';

export interface BankRequest {
  id: number;
  /** A string: Discord ids are past the largest integer a browser holds exactly. */
  discord_user_id: string;
  requester_name: string;
  item: string;
  quantity: number;
  source: 'discord' | 'site' | string;
  status: RequestStatus;
  created_at: string;
  officer_message: string | null;
  decided_by_name: string | null;
  decided_at: string | null;
  /** Whether the Toad Bot has DMed the member the answer; null while the request is pending. */
  notice: Notice | null;
  notice_error: string | null;
}

/** What the desk talks to: the hub, or the preview's in-browser fake. */
export interface BankDeskBackend {
  /** The raid days whose desk routes the viewer may use (manage_bank): empty for everyone else. */
  manageDays(): Promise<string[]>;
  incoming(day: string): Promise<BankRequest[]>;
  history(day: string, discordUserId: string): Promise<BankRequest[]>;
  mine(): Promise<BankRequest[]>;
  ask(item: string, quantity: number): Promise<BankRequest>;
  answer(day: string, id: number, verdict: Verdict, message: string): Promise<BankRequest>;
}

export const ITEM_LIMIT = 100;
export const MAX_QUANTITY = 1000;
export const MESSAGE_LIMIT = 500;

export function hubBankDesk(f: Fetch = fetch): BankDeskBackend {
  const day = (d: string) => `/api/days/${encodeURIComponent(d)}/bank-desk`;
  return {
    manageDays: async () => {
      const me = await call<{ manage_days?: string[]; officer_days?: string[] }>(f, '/api/bank/me');
      return me.manage_days ?? me.officer_days ?? [];
    },
    incoming: (d) => call<BankRequest[]>(f, `${day(d)}/requests`),
    history: (d, id) => call<BankRequest[]>(f, `${day(d)}/members/${encodeURIComponent(id)}/requests`),
    mine: () => call<BankRequest[]>(f, '/api/bank-desk/requests/mine'),
    ask: (item, quantity) =>
      call<BankRequest>(f, '/api/bank-desk/requests', { method: 'POST', body: JSON.stringify({ item, quantity }) }),
    answer: (d, id, verdict, message) =>
      call<BankRequest>(f, `${day(d)}/requests/${id}/${verdict}`, { method: 'POST', body: JSON.stringify({ message }) })
  };
}

export type DeskFilter = 'pending' | 'all';

/** The rows a filter shows: pending ones oldest first (first asked, first answered), else everything newest first. */
export function shown(rows: readonly BankRequest[], filter: DeskFilter): BankRequest[] {
  if (filter === 'all') return [...rows].sort((a, b) => b.id - a.id);
  return rows.filter((r) => r.status === 'pending').sort((a, b) => a.id - b.id);
}

export function pendingCount(rows: readonly BankRequest[]): number {
  return rows.filter((r) => r.status === 'pending').length;
}

/** How many requests each member has made, and how many were approved, for the "asked before" hint. */
export function askedBefore(rows: readonly BankRequest[]): Map<string, { asked: number; approved: number }> {
  const counts = new Map<string, { asked: number; approved: number }>();
  for (const r of rows) {
    const c = counts.get(r.discord_user_id) ?? { asked: 0, approved: 0 };
    c.asked += 1;
    if (r.status === 'approved') c.approved += 1;
    counts.set(r.discord_user_id, c);
  }
  return counts;
}

export const STATUS_LABEL: Record<RequestStatus, string> = {
  pending: 'Waiting',
  approved: 'Approved',
  denied: 'Denied'
};

/** Where the answer's DM is, in words: for the member who asked (`own`), or for the officers answering. */
export function noticeLabel(r: BankRequest, own = false): string {
  switch (r.notice) {
    case 'queued':
      return 'DM on its way';
    case 'sent':
      return 'DM sent';
    case 'failed':
      if (own) return 'We could not DM you on Discord, so the answer is only here';
      // Discord's "Cannot send messages to this user" (50007) means the member has closed DMs from server members;
      // any other refusal (Missing Access, Missing Permissions) is the bot's to fix, so officers see it as it came.
      if (r.notice_error?.includes('Cannot send messages to this user')) {
        return 'DM failed: their Discord DMs are closed, so tell them in game';
      }
      return `DM failed${r.notice_error ? `: ${r.notice_error}` : ''}`;
    default:
      return '';
  }
}

export function sourceLabel(source: string): string {
  return source === 'discord' ? 'Discord' : 'Site';
}

export function bankDeskError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.status) {
    case 401:
      return 'Sign in again to use the request desk.';
    case 403:
      return 'Only officers answer bank requests for now.';
    case 409:
      return e.message || 'Another officer answered that request first.';
    default:
      return e.message || 'Something went wrong; try again.';
  }
}
