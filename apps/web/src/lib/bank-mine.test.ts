import { describe, expect, it } from 'vitest';
import type { BankRequest as StockRequest, InventoryItem } from './bank';
import type { BankRequest as DeskRequest } from './bank-desk';
import { myRequestRows, stockedItem } from './bank-mine';

const stock = (over: Partial<StockRequest> = {}): StockRequest => ({
  id: 's1',
  revision: 1,
  status: 'reserved',
  memberId: 'm1',
  memberName: 'Hopscotch',
  character: 'Hopscotch',
  sourceId: 'wed',
  itemId: 22832,
  itemName: 'Super Mana Potion',
  quantity: 5,
  delivered: 0,
  outstanding: 5,
  occurrenceId: null,
  note: null,
  managerNote: null,
  createdAt: Date.parse('2026-10-20T12:00:00Z') / 1000,
  updatedAt: 0,
  ...over
});

const desk = (over: Partial<DeskRequest> = {}): DeskRequest => ({
  id: 7,
  discord_user_id: '1',
  requester_name: 'Hopscotch',
  item: 'Primal Fire',
  quantity: 3,
  source: 'discord',
  status: 'denied',
  created_at: '2026-10-21T09:00:00Z',
  officer_message: 'We are short this week',
  decided_by_name: 'Croakley',
  decided_at: '2026-10-21T10:00:00Z',
  notice: 'failed',
  notice_error: 'Cannot send messages to this user',
  ...over
});

describe('a member\'s bank requests in one list', () => {
  it('puts both services\' requests together, newest first, in plain words', () => {
    const rows = myRequestRows([stock()], [desk()], (id) => (id === 'wed' ? 'Wednesday bank' : id));
    expect(rows.map((r) => r.what)).toEqual(['3 × Primal Fire', '5 × Super Mana Potion']);
    expect(rows[0]).toMatchObject({
      status: 'Denied',
      tone: 'bad',
      said: 'We are short this week',
      detail: 'answered by Croakley',
      dm: 'We could not DM you on Discord, so the answer is only here',
      dmFailed: true,
      cancel: null
    });
    expect(rows[1]).toMatchObject({ status: 'Reserved', tone: 'wait', detail: 'for Hopscotch, from Wednesday bank' });
    expect(rows[1].cancel?.id).toBe('s1');
  });

  it('offers Cancel only on stock requests that still hold or wait for stock', () => {
    expect(myRequestRows([stock({ status: 'fulfilled', delivered: 5 })], [])[0].cancel).toBeNull();
    expect(myRequestRows([stock({ status: 'waitlisted' })], [])[0].cancel).not.toBeNull();
    expect(myRequestRows([], [desk({ status: 'pending', notice: null })])[0]).toMatchObject({ status: 'Waiting', dm: null });
  });
});

describe('what the ask form sends where', () => {
  const items = [{ itemId: 1, name: 'Super Mana Potion' }] as InventoryItem[];
  it('matches a stocked item by name in any case', () => {
    expect(stockedItem(items, '  super   mana potion ')?.itemId).toBe(1);
  });
  it('leaves anything else for the request desk', () => {
    expect(stockedItem(items, 'Primal Fire')).toBeNull();
    expect(stockedItem(items, '   ')).toBeNull();
  });
});
