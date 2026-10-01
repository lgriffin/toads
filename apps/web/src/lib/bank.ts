/**
 * The guild bank (docs/bank.md): ToadsBank's data through the hub's /api/bank routes. Shapes follow ToadsBank's v1
 * HTTP contract, which the hub passes through unchanged; times are epoch seconds. Officer routes are scoped to a raid
 * day (/api/days/{day}/bank/...), like every officer power.
 */

import { ApiError, call, type Fetch } from './api';

// --- API shapes ------------------------------------------------------------------------------------

export type Freshness = 'fresh' | 'warn' | 'stale';

export interface BankTab {
  index: number;
  name: string | null;
  status: string;
  observedAt: number | null;
  capacity: number | null;
}

export interface BankSource {
  id: string;
  revision: number;
  name: string;
  kind: string;
  guild: string;
  realm: string;
  region: string;
  audience: 'members' | 'officers';
  raidDay: string | null;
  managers: string[];
  lastObservedAt: number | null;
  freshness: Freshness;
  tabs: BankTab[];
}

export interface ReplicaSlot {
  slot: number;
  itemId: number;
  name?: string;
  count: number;
  link?: string;
}

export interface Replica {
  source: BankSource;
  tabs: (BankTab & { slots: ReplicaSlot[] })[];
}

export interface StockCounts {
  observed: number;
  pendingOutgoing: number;
  raidHeld: number;
  directReserved: number;
  available: number;
}

export interface SourceStock extends StockCounts {
  sourceId: string;
  observedAt: number | null;
}

export interface InventoryItem extends StockCounts {
  itemId: number;
  name: string;
  sources: SourceStock[];
}

export interface Inventory {
  /** The capture-time range of the aggregate (TB-GM-03); null before any capture. */
  range: { oldest: number; newest: number } | null;
  items: InventoryItem[];
}

export type RequestStatus = 'reserved' | 'approved' | 'fulfilled' | 'waitlisted' | 'cancelled' | 'rejected' | 'expired';

export interface BankRequest {
  id: string;
  revision: number;
  status: RequestStatus;
  memberId: string;
  memberName: string;
  character: string;
  sourceId: string;
  itemId: number;
  itemName: string;
  quantity: number;
  delivered: number;
  outstanding: number;
  occurrenceId: string | null;
  note: string | null;
  managerNote: string | null;
  createdAt: number;
  updatedAt: number;
}

export interface NewRequest {
  sourceId: string;
  itemId: number;
  quantity: number;
  character: string;
  note?: string;
  waitlist?: boolean;
}

export interface ImportSession {
  id: string;
  openedAt: number;
  expiresAt: number;
}

export interface ImportProgress {
  exportId: string | null;
  received: number[];
  total: number;
  missing: number[];
  complete: boolean;
}

export interface ImportPreview {
  snapshotId: string;
  source: { guild: string; realm: string; region: string };
  matchedSource: { id: string; name: string } | null;
  uploader: { name: string; realm: string } | null;
  capturedAt: number;
  completedAt: number;
  stable: boolean;
  tabs: { index: number; name: string | null; status: string; occupied: number; items: number; olderThanBaseline: boolean }[];
  warnings: string[];
  existingReceipt: ImportReceipt | null;
}

export interface ImportReceipt {
  snapshotId: string;
  sourceId: string;
  acceptedAt: number;
  tabsUpdated: number[];
  tabsKeptAsHistory: number[];
  tabsNotRead: number[];
  duplicate: boolean;
}

export interface BankMe {
  configured: boolean;
  discord_user_id: string | null;
  display_name: string;
  global_officer: boolean;
  /** Raid days the member may import and work the queue on. */
  officer_days: string[];
}

// --- calls ---------------------------------------------------------------------------------------

/** A fresh idempotency key for one submission; a retry of the same submission reuses it. */
export function newKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

/** A submission and the Idempotency-Key it was sent with. */
export interface KeyedSend {
  body: string;
  key: string;
}

/** The key for sending `body`: the same key when resending the very submission whose outcome is unknown, so ToadsBank
 * applies it once; a fresh key for anything else (a changed form, the waitlist instead). */
export function keyFor(previous: KeyedSend | null, body: unknown): KeyedSend {
  const text = JSON.stringify(body);
  return previous && previous.body === text ? previous : { body: text, key: newKey() };
}

/** Whether a failed send got a definite answer (the hub or ToadsBank said no), after which its key is spent. A
 * network error or a 5xx (including 502 bank_unavailable) leaves the outcome unknown, so the key is kept for a retry. */
export function outcomeKnown(e: unknown): boolean {
  return e instanceof ApiError && e.status < 500;
}

const enc = encodeURIComponent;

function post<T>(f: Fetch, path: string, body: unknown, key: string): Promise<T> {
  return call<T>(f, path, { method: 'POST', body: JSON.stringify(body ?? {}), headers: { 'Idempotency-Key': key } });
}

function query(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) q.set(k, v);
  const s = q.toString();
  return s ? `?${s}` : '';
}

export const getBankMe = (f: Fetch = fetch) => call<BankMe>(f, '/api/bank/me');
export const listSources = (f: Fetch = fetch) => call<BankSource[]>(f, '/api/bank/sources');
export const getReplica = (sourceId: string, f: Fetch = fetch) =>
  call<Replica>(f, `/api/bank/sources/${enc(sourceId)}/replica`);
export const getInventory = (q?: string, sourceId?: string, f: Fetch = fetch) =>
  call<Inventory>(f, `/api/bank/inventory${query({ q, sourceId })}`);
export const myRequests = (f: Fetch = fetch) => call<BankRequest[]>(f, '/api/bank/requests');
export const createRequest = (body: NewRequest, key: string, f: Fetch = fetch) =>
  post<BankRequest>(f, '/api/bank/requests', body, key);
export const cancelRequest = (r: Pick<BankRequest, 'id' | 'revision'>, key: string, f: Fetch = fetch) =>
  post<BankRequest>(f, `/api/bank/requests/${enc(r.id)}/cancel`, { expectedRevision: r.revision }, key);

const dayBase = (day: string) => `/api/days/${enc(day)}/bank`;

export const requestQueue = (day: string, scope: 'queue' | 'all' = 'queue', f: Fetch = fetch) =>
  call<BankRequest[]>(f, `${dayBase(day)}/requests${query({ scope })}`);

export type ManagerAction = 'approve' | 'reject' | 'deliveries';

export function manageRequest(
  day: string,
  r: Pick<BankRequest, 'id' | 'revision'>,
  action: ManagerAction,
  extra: { note?: string; quantity?: number },
  key: string,
  f: Fetch = fetch
): Promise<BankRequest> {
  return post<BankRequest>(f, `${dayBase(day)}/requests/${enc(r.id)}/${action}`, { expectedRevision: r.revision, ...extra }, key);
}

export const openImport = (day: string, key: string, f: Fetch = fetch) =>
  post<ImportSession>(f, `${dayBase(day)}/imports`, {}, key);
export const addParts = (day: string, id: string, text: string, key: string, f: Fetch = fetch) =>
  post<ImportProgress>(f, `${dayBase(day)}/imports/${enc(id)}/parts`, { text }, key);
export const previewImport = (day: string, id: string, f: Fetch = fetch) =>
  call<ImportPreview>(f, `${dayBase(day)}/imports/${enc(id)}/preview`);
export const acceptImport = (day: string, id: string, key: string, f: Fetch = fetch) =>
  post<ImportReceipt>(f, `${dayBase(day)}/imports/${enc(id)}/accept`, {}, key);

// --- wording -------------------------------------------------------------------------------------

export function freshnessLabel(f: Freshness): string {
  if (f === 'fresh') return 'Fresh';
  if (f === 'warn') return 'Over a day old';
  return 'Stale: no new reservations until it is captured again';
}

export function freshnessClass(f: Freshness): 'ok' | 'warn' | 'bad' {
  return f === 'fresh' ? 'ok' : f === 'warn' ? 'warn' : 'bad';
}

/** How long ago an epoch-seconds time was, in words. */
export function observationAge(at: number | null | undefined, nowMs: number): string {
  if (at === null || at === undefined) return 'never captured';
  const minutes = Math.floor((nowMs / 1000 - at) / 60);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
  return `${Math.floor(hours / 24)} days ago`;
}

export function bankTime(at: number): string {
  return new Date(at * 1000).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Paris'
  });
}

/** TB-GM-03: the capture-time range an inventory aggregates. */
export function captureRange(range: Inventory['range'], nowMs: number): string {
  if (!range) return 'Nothing has been captured yet.';
  if (range.oldest === range.newest) return `Captured ${bankTime(range.newest)} (${observationAge(range.newest, nowMs)}).`;
  return `Captured between ${bankTime(range.oldest)} (${observationAge(range.oldest, nowMs)}) and ${bankTime(range.newest)} (${observationAge(range.newest, nowMs)}).`;
}

const STATUS: Record<RequestStatus, string> = {
  reserved: 'Reserved',
  approved: 'Approved',
  fulfilled: 'Fulfilled',
  waitlisted: 'Waitlisted',
  cancelled: 'Cancelled',
  rejected: 'Rejected',
  expired: 'Expired'
};

export function requestStatusLabel(r: Pick<BankRequest, 'status' | 'delivered' | 'quantity'>): string {
  const label = STATUS[r.status] ?? r.status;
  return r.delivered > 0 && r.status !== 'fulfilled' ? `${label}, ${r.delivered} of ${r.quantity} delivered` : label;
}

/** Open requests still hold (or wait for) stock and can be cancelled. */
export function isOpen(r: Pick<BankRequest, 'status'>): boolean {
  return r.status === 'reserved' || r.status === 'approved' || r.status === 'waitlisted';
}

export function progressLabel(p: ImportProgress): string {
  if (p.complete) return `All ${p.total} parts received.`;
  if (p.total === 0) return 'No parts found in that text yet.';
  return `Received ${p.received.length} of ${p.total} parts. Still missing: ${p.missing.join(', ')}.`;
}

export function receiptLabel(r: ImportReceipt): string {
  if (r.duplicate) return 'That snapshot was already accepted; nothing changed.';
  const parts = [`Snapshot accepted. Tabs updated: ${r.tabsUpdated.join(', ') || 'none'}.`];
  if (r.tabsNotRead.length) parts.push(`Not read, kept as they were: ${r.tabsNotRead.join(', ')}.`);
  if (r.tabsKeptAsHistory.length) parts.push(`Older than the bank's copy, kept as history: ${r.tabsKeptAsHistory.join(', ')}.`);
  return parts.join(' ');
}

/** Items whose name contains the search, case-insensitively, in name order. */
export function filterItems(items: InventoryItem[], search: string): InventoryItem[] {
  const q = search.trim().toLocaleLowerCase();
  return items.filter((i) => !q || i.name.toLocaleLowerCase().includes(q)).sort((a, b) => a.name.localeCompare(b.name));
}

/** The source holding the most of an item free to reserve. */
export function bestSource(item: Pick<InventoryItem, 'sources'>): SourceStock | null {
  return item.sources.reduce<SourceStock | null>((best, s) => (best === null || s.available > best.available ? s : best), null);
}

/** A tab's slots in captured slot order (TB-GM-01). */
export function slotsInOrder<T extends { slot: number }>(slots: T[]): T[] {
  return [...slots].sort((a, b) => a.slot - b.slot);
}

// --- errors --------------------------------------------------------------------------------------

/** When a request failed for want of stock and ToadsBank offers a waitlist (TB-GM-06): how many are available. */
export function waitlistOffer(e: unknown): number | null {
  if (!(e instanceof ApiError) || e.code !== 'insufficient_stock') return null;
  const d = e.details as { available?: unknown; canWaitlist?: unknown } | undefined;
  return d?.canWaitlist ? Number(d.available ?? 0) : null;
}

/** The current state of a request a stale action was refused for (TB-BM-16). */
export function staleCurrent(e: unknown): BankRequest | null {
  return e instanceof ApiError && e.code === 'stale_revision' && e.current ? (e.current as BankRequest) : null;
}

/** What to tell a member when a bank call fails. */
export function bankError(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong; try again.';
  switch (e.code) {
    case 'bank_not_configured':
      return 'The guild bank is not set up on the hub yet.';
    case 'bank_unavailable':
      return 'The guild bank is not answering right now; try again shortly.';
    case 'insufficient_stock':
      return 'There is not enough of that in stock.';
    case 'source_stale':
      return 'That bank has not been captured recently, so nothing can be reserved from it until it is uploaded again.';
    case 'stale_revision':
      return 'That request changed since you loaded it; the list now shows its current state.';
    case 'import_expired':
      return 'That import expired after 30 minutes. Paste the parts again to start a new one.';
    case 'not_this_day':
      return 'That bank belongs to another raid day. Pick that day above, if you are one of its officers.';
    case 'unknown_source':
      return 'That export is from a bank the hub does not know yet. Ask a global officer to accept it, which registers it.';
  }
  if (e.status === 401) return 'Sign in with Discord to use the bank.';
  if (e.status === 403) return 'You can’t do that here. Bank managers and officers handle imports and the request queue.';
  return e.message || 'Something went wrong; try again.';
}
