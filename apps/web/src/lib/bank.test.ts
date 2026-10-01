import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import {
  addParts,
  bankDays,
  bankError,
  bestSource,
  cancelRequest,
  captureRange,
  createRequest,
  filterItems,
  freshnessClass,
  freshnessLabel,
  getInventory,
  GRANT_LABELS,
  grantBank,
  grantScope,
  grantsText,
  isDiscordId,
  listTokens,
  mintToken,
  redeemToken,
  revokeToken,
  TOKEN_STATUS_LABELS,
  listGrants,
  revokeGrant,
  isOpen,
  keyFor,
  manageRequest,
  newKey,
  observationAge,
  outcomeKnown,
  progressLabel,
  receiptLabel,
  requestQueue,
  requestStatusLabel,
  slotsInOrder,
  staleCurrent,
  waitlistOffer,
  type InventoryItem
} from './bank';

type Call = { url: string; init: RequestInit };

function fakeFetch(status: number, body?: unknown): { f: typeof fetch; calls: Call[] } {
  const calls: Call[] = [];
  const f = (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return new Response(body === undefined ? null : JSON.stringify(body), { status });
  }) as unknown as typeof fetch;
  return { f, calls };
}

const NOW = 1_790_800_000 * 1000;

describe('freshness and ages', () => {
  it('labels freshness', () => {
    expect(freshnessLabel('fresh')).toBe('Fresh');
    expect(freshnessLabel('warn')).toBe('Over a day old');
    expect(freshnessLabel('stale')).toMatch(/^Stale/);
    expect([freshnessClass('fresh'), freshnessClass('warn'), freshnessClass('stale')]).toEqual(['ok', 'warn', 'bad']);
  });
  it('says how long ago a capture was', () => {
    const now = NOW / 1000;
    expect(observationAge(null, NOW)).toBe('never captured');
    expect(observationAge(now - 30, NOW)).toBe('just now');
    expect(observationAge(now - 60, NOW)).toBe('1 minute ago');
    expect(observationAge(now - 59 * 60, NOW)).toBe('59 minutes ago');
    expect(observationAge(now - 3600, NOW)).toBe('1 hour ago');
    expect(observationAge(now - 47 * 3600, NOW)).toBe('47 hours ago');
    expect(observationAge(now - 3 * 86400, NOW)).toBe('3 days ago');
  });
  it('describes the capture-time range of an aggregate', () => {
    const now = NOW / 1000;
    expect(captureRange(null, NOW)).toBe('Nothing has been captured yet.');
    expect(captureRange({ oldest: now - 120, newest: now - 120 }, NOW)).toMatch(/^Captured .* \(2 minutes ago\)\.$/);
    const range = captureRange({ oldest: now - 2 * 86400, newest: now - 3600 }, NOW);
    expect(range).toMatch(/^Captured between .* \(2 days ago\) and .* \(1 hour ago\)\.$/);
  });
});

describe('requests', () => {
  it('labels status with partial deliveries', () => {
    expect(requestStatusLabel({ status: 'approved', delivered: 0, quantity: 5 })).toBe('Approved');
    expect(requestStatusLabel({ status: 'approved', delivered: 2, quantity: 5 })).toBe('Approved, 2 of 5 delivered');
    expect(requestStatusLabel({ status: 'fulfilled', delivered: 5, quantity: 5 })).toBe('Fulfilled');
  });
  it('knows which requests are still open', () => {
    expect(['reserved', 'approved', 'waitlisted'].every((status) => isOpen({ status: status as never }))).toBe(true);
    expect(['fulfilled', 'cancelled', 'rejected', 'expired'].some((status) => isOpen({ status: status as never }))).toBe(false);
  });
  it('sends an idempotency key and the revision', async () => {
    const { f, calls } = fakeFetch(200, { id: 'req_1' });
    await cancelRequest({ id: 'req_1', revision: 3 }, 'key-1', f);
    expect(calls[0].url).toBe('/api/bank/requests/req_1/cancel');
    expect((calls[0].init.headers as Record<string, string>)['Idempotency-Key']).toBe('key-1');
    expect(JSON.parse(String(calls[0].init.body))).toEqual({ expectedRevision: 3 });
    await createRequest({ sourceId: 'src_1', itemId: 1, quantity: 2, character: 'Frog' }, 'key-2', f);
    expect(calls[1].url).toBe('/api/bank/requests');
    await manageRequest('wed', { id: 'req_1', revision: 2 }, 'deliveries', { quantity: 2 }, 'key-3', f);
    expect(calls[2].url).toBe('/api/days/wed/bank/requests/req_1/deliveries');
    expect(JSON.parse(String(calls[2].init.body))).toEqual({ expectedRevision: 2, quantity: 2 });
  });
  it('builds query strings only from what is given', async () => {
    const { f, calls } = fakeFetch(200, { range: null, items: [] });
    await getInventory(undefined, undefined, f);
    await getInventory('mana potion', 'src_1', f);
    await requestQueue('wed', 'all', f);
    await addParts('wed', 'imp/1', 'text', 'k', f);
    expect(calls.map((c) => c.url)).toEqual([
      '/api/bank/inventory',
      '/api/bank/inventory?q=mana+potion&sourceId=src_1',
      '/api/days/wed/bank/requests?scope=all',
      '/api/days/wed/bank/imports/imp%2F1/parts'
    ]);
  });
  it('makes a new key each time', () => {
    expect(newKey()).not.toBe(newKey());
  });
});

describe('inventory helpers', () => {
  const item = (name: string, sources: [string, number][] = []): InventoryItem => ({
    itemId: name.length,
    name,
    observed: 0,
    pendingOutgoing: 0,
    raidHeld: 0,
    directReserved: 0,
    available: 0,
    sources: sources.map(([sourceId, available]) => ({
      sourceId,
      available,
      observed: available,
      pendingOutgoing: 0,
      raidHeld: 0,
      directReserved: 0,
      observedAt: 1
    }))
  });
  it('filters by name, case-insensitively, in name order', () => {
    const items = [item('Super Mana Potion'), item('Flask of Blinding Light'), item('Brilliant Mana Oil')];
    expect(filterItems(items, ' MANA ').map((i) => i.name)).toEqual(['Brilliant Mana Oil', 'Super Mana Potion']);
    expect(filterItems(items, '')).toHaveLength(3);
  });
  it('picks the source with most available', () => {
    expect(bestSource(item('x', [['a', 3], ['b', 18], ['c', 1]]))?.sourceId).toBe('b');
    expect(bestSource(item('x'))).toBeNull();
  });
  it('keeps slots in captured order', () => {
    expect(slotsInOrder([{ slot: 3 }, { slot: 1 }, { slot: 2 }]).map((s) => s.slot)).toEqual([1, 2, 3]);
  });
});

describe('imports', () => {
  it('reports progress', () => {
    expect(progressLabel({ exportId: 'x', received: [1, 3], total: 4, missing: [2, 4], complete: false })).toBe(
      'Received 2 of 4 parts. Still missing: 2, 4.'
    );
    expect(progressLabel({ exportId: 'x', received: [1], total: 1, missing: [], complete: true })).toBe('All 1 parts received.');
    expect(progressLabel({ exportId: null, received: [], total: 0, missing: [], complete: false })).toMatch(/^No parts/);
  });
  it('describes a receipt', () => {
    const receipt = { snapshotId: 's', sourceId: 'src_1', acceptedAt: 1, tabsUpdated: [1, 2], tabsKeptAsHistory: [4], tabsNotRead: [3], duplicate: false };
    expect(receiptLabel(receipt)).toBe(
      "Snapshot accepted. Tabs updated: 1, 2. Not read, kept as they were: 3. Older than the bank's copy, kept as history: 4."
    );
    expect(receiptLabel({ ...receipt, duplicate: true })).toMatch(/already accepted/);
  });
});

describe('errors', () => {
  it('carries ToadsBank error codes through the API error', async () => {
    const { f } = fakeFetch(409, {
      detail: 'Not enough in stock',
      error: { code: 'insufficient_stock', message: 'Not enough in stock', details: { available: 4, canWaitlist: true } }
    });
    const e = await createRequest({ sourceId: 's', itemId: 1, quantity: 9, character: 'x' }, 'k', f).catch((x) => x);
    expect(e).toBeInstanceOf(ApiError);
    expect([e.status, e.code, e.message]).toEqual([409, 'insufficient_stock', 'Not enough in stock']);
    expect(waitlistOffer(e)).toBe(4);
    expect(bankError(e)).toBe('There is not enough of that in stock.');
  });
  it('offers no waitlist for other errors', () => {
    expect(waitlistOffer(new ApiError(409, 'x', 'insufficient_stock', { canWaitlist: false }))).toBeNull();
    expect(waitlistOffer(new Error('x'))).toBeNull();
  });
  it('returns the current request for a stale revision', () => {
    const current = { id: 'req_1', revision: 4 };
    expect(staleCurrent(new ApiError(409, 'stale', 'stale_revision', undefined, current))).toEqual(current);
    expect(staleCurrent(new ApiError(409, 'other', 'invalid_transition'))).toBeNull();
  });
  it('explains failures', () => {
    expect(bankError(new ApiError(503, 'x', 'bank_not_configured'))).toMatch(/not set up/);
    expect(bankError(new ApiError(502, 'x', 'bank_unavailable'))).toMatch(/not answering/);
    expect(bankError(new ApiError(423, 'x', 'source_stale'))).toMatch(/not been captured recently/);
    expect(bankError(new ApiError(409, 'x', 'stale_revision'))).toMatch(/changed since/);
    expect(bankError(new ApiError(422, 'x', 'import_expired'))).toMatch(/expired/);
    expect(bankError(new ApiError(422, 'x', 'unknown_source'))).toMatch(/global officer/);
    expect(bankError(new ApiError(401, 'Not signed in'))).toMatch(/Sign in/);
    expect(bankError(new ApiError(403, 'Forbidden'))).toMatch(/can’t do that/);
    expect(bankError(new ApiError(422, 'Bad paste', 'transport_error'))).toBe('Bad paste');
    expect(bankError('nope')).toMatch(/Something went wrong/);
  });
});

describe('idempotency keys for the request form', () => {
  const body = { sourceId: 's', itemId: 1, quantity: 2, character: 'Frogmage' };
  it('reuses the key when the same submission is retried after an unknown outcome', () => {
    const first = keyFor(null, body);
    expect(keyFor(first, { ...body }).key).toBe(first.key);
  });
  it('uses a fresh key for a changed submission, including the waitlist', () => {
    const first = keyFor(null, body);
    expect(keyFor(first, { ...body, quantity: 3 }).key).not.toBe(first.key);
    expect(keyFor(first, { ...body, waitlist: true }).key).not.toBe(first.key);
  });
  it('spends the key only on a definite answer', () => {
    expect(outcomeKnown(new ApiError(409, 'x', 'insufficient_stock'))).toBe(true);
    expect(outcomeKnown(new ApiError(422, 'x'))).toBe(true);
    expect(outcomeKnown(new ApiError(502, 'x', 'bank_unavailable'))).toBe(false);
    expect(outcomeKnown(new ApiError(503, 'x'))).toBe(false);
    expect(outcomeKnown(new TypeError('Failed to fetch'))).toBe(false);
  });
});

describe('raid days', () => {
  it('explains a bank that belongs to another raid day', () => {
    expect(bankError(new ApiError(403, 'x', 'not_this_day'))).toMatch(/another raid day/);
  });
});

describe('grants', () => {
  const me = { configured: true, discord_user_id: '1', display_name: 'x', global_officer: false, officer_days: ['wed'] };
  it('offers each day the member may use, from an older hub too', () => {
    expect(bankDays(me)).toEqual({ imports: ['wed'], manage: ['wed'], all: ['wed'] });
    expect(bankDays({ ...me, officer_days: [], import_days: ['sun'], manage_days: ['wed'] })).toEqual({
      imports: ['sun'],
      manage: ['wed'],
      all: ['wed', 'sun']
    });
  });
  it('lists, grants and revokes through the admin routes', async () => {
    const { f, calls } = fakeFetch(200, []);
    await listGrants(f);
    await grantBank({ discord_user_id: '42', permission: 'manage_bank', raid_day: null }, f);
    expect(calls.map((c) => [c.url, c.init.method ?? 'GET'])).toEqual([
      ['/api/admin/bank/grants', 'GET'],
      ['/api/admin/bank/grants', 'POST']
    ]);
    expect(JSON.parse(String(calls[1].init.body))).toEqual({
      discord_user_id: '42',
      permission: 'manage_bank',
      raid_day: null
    });
    const revoked = fakeFetch(204);
    await revokeGrant(7, revoked.f);
    expect([revoked.calls[0].url, revoked.calls[0].init.method]).toEqual(['/api/admin/bank/grants/7', 'DELETE']);
  });
  it('takes Discord ids as digit strings', () => {
    expect(isDiscordId(' 42 ')).toBe(true);
    expect(['', '0123', '12a', '1'.repeat(21)].some(isDiscordId)).toBe(false);
  });
  it('words a grant', () => {
    expect(GRANT_LABELS.import_bank_snapshot).toBe('Import bank snapshots');
    expect([grantScope(null), grantScope('wed')]).toEqual(['every bank', 'wed banks']);
  });
});

describe('officer tokens', () => {
  it('mints, lists and revokes through the super admin routes', async () => {
    const { f, calls } = fakeFetch(200, []);
    await listTokens(f);
    await mintToken({ permissions: ['manage_bank'], raid_day: 'wed', days: 3, note: 'for Tadpole' }, f);
    expect(calls.map((c) => [c.url, c.init.method ?? 'GET'])).toEqual([
      ['/api/admin/bank/tokens', 'GET'],
      ['/api/admin/bank/tokens', 'POST']
    ]);
    expect(JSON.parse(String(calls[1].init.body))).toEqual({
      permissions: ['manage_bank'],
      raid_day: 'wed',
      days: 3,
      note: 'for Tadpole'
    });
    const revoked = fakeFetch(204);
    await revokeToken(3, revoked.f);
    expect([revoked.calls[0].url, revoked.calls[0].init.method]).toEqual(['/api/admin/bank/tokens/3', 'DELETE']);
  });
  it('redeems a pasted token, trimmed', async () => {
    const { f, calls } = fakeFetch(200, { token_id: 3, grants: [] });
    expect(await redeemToken('  toads-bank-abc  ', f)).toEqual({ token_id: 3, grants: [] });
    expect([calls[0].url, calls[0].init.method]).toEqual(['/api/bank/redeem', 'POST']);
    expect(JSON.parse(String(calls[0].init.body))).toEqual({ token: 'toads-bank-abc' });
  });
  it('words a token', () => {
    expect(grantsText(['import_bank_snapshot', 'manage_bank'], null)).toBe(
      'Import bank snapshots and run the request queue on every bank'
    );
    expect(grantsText(['manage_bank'], 'sun')).toBe('Run the request queue on sun banks');
    expect(TOKEN_STATUS_LABELS.active).toBe('Not yet used');
  });
});
