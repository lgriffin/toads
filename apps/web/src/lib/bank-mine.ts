/**
 * The member's side of the bank page in one place: one way to ask and one list of what they asked for. Behind it are
 * two services, ToadsBank's stock requests (an item the bank holds, set aside straight away) and the hub's request
 * desk (anything else, answered by an officer and DMed by the Toad Bot, docs/bank-desk.md), but a member never has
 * to know which one took their ask.
 */
import { isOpen, requestStatusLabel, type BankRequest as StockRequest, type InventoryItem } from './bank';
import { noticeLabel, STATUS_LABEL, type BankRequest as DeskRequest } from './bank-desk';

export type Tone = 'ok' | 'bad' | 'wait' | 'done';

export interface MyRequestRow {
  key: string;
  /** When they asked, in milliseconds. */
  at: number;
  what: string;
  /** Who it is for and which bank, for stock requests. */
  detail: string | null;
  status: string;
  tone: Tone;
  /** What the officer said back. */
  said: string | null;
  /** Where the Toad Bot's DM is, for desk requests. */
  dm: string | null;
  dmFailed: boolean;
  /** Set when the request still holds or waits for stock and can be cancelled. */
  cancel: StockRequest | null;
}

const STOCK_TONE: Record<StockRequest['status'], Tone> = {
  reserved: 'wait',
  approved: 'ok',
  fulfilled: 'done',
  waitlisted: 'wait',
  cancelled: 'done',
  rejected: 'bad',
  expired: 'done'
};
const DESK_TONE: Record<DeskRequest['status'], Tone> = { pending: 'wait', approved: 'ok', denied: 'bad' };

function stockRow(r: StockRequest, bankName: (id: string) => string): MyRequestRow {
  return {
    key: `stock-${r.id}`,
    at: r.createdAt * 1000,
    what: `${r.quantity} × ${r.itemName}`,
    detail: `for ${r.character}, from ${bankName(r.sourceId)}`,
    status: requestStatusLabel(r),
    tone: STOCK_TONE[r.status] ?? 'done',
    said: r.managerNote,
    dm: null,
    dmFailed: false,
    cancel: isOpen(r) ? r : null
  };
}

function deskRow(r: DeskRequest): MyRequestRow {
  return {
    key: `desk-${r.id}`,
    at: Date.parse(r.created_at),
    what: `${r.quantity} × ${r.item}`,
    detail: r.decided_by_name ? `answered by ${r.decided_by_name}` : null,
    status: STATUS_LABEL[r.status] ?? r.status,
    tone: DESK_TONE[r.status] ?? 'done',
    said: r.officer_message,
    dm: r.notice ? noticeLabel(r, true) : null,
    dmFailed: r.notice === 'failed',
    cancel: null
  };
}

/** Every request the member made, from either service, newest first. */
export function myRequestRows(
  stock: StockRequest[],
  desk: DeskRequest[],
  bankName: (id: string) => string = (id) => id
): MyRequestRow[] {
  return [...stock.map((r) => stockRow(r, bankName)), ...desk.map(deskRow)].sort((a, b) => b.at - a.at);
}

/** Every stocked item with the name the member typed (any case, extra spaces ignored); two item ids can share a name. */
export function stockMatches(items: InventoryItem[], typed: string): InventoryItem[] {
  const name = typed.trim().split(/\s+/).join(' ').toLocaleLowerCase();
  if (!name) return [];
  return items.filter((i) => i.name.toLocaleLowerCase() === name);
}

/**
 * The stocked item the member means: the one they picked (an inventory row's Ask) if its name still matches, else the
 * only item with that name. Null for anything the bank does not hold, and also while two items share the name and
 * none is picked, so the form asks which one rather than reserving the first.
 */
export function stockedItem(items: InventoryItem[], typed: string, picked: number | null = null): InventoryItem | null {
  const matches = stockMatches(items, typed);
  return matches.find((i) => i.itemId === picked) ?? (matches.length === 1 ? matches[0] : null);
}
