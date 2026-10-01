/**
 * The static preview's guild bank: the real bank page ($lib/components/BankLive.svelte) talking to an in-memory
 * stand-in for the hub's /api/bank routes instead of ToadsBank. Shapes follow $lib/bank. State lives in this tab only
 * (kept across client-side navigation and view switches, reset on reload), so a visitor can mint an officer token as
 * the officer, switch to the raider view and redeem it.
 *
 * The officer view is also a super admin here, so the grants, officer tokens and break-glass notice show.
 */
import type { Fetch } from '$lib/api';
import type {
  BankGrant,
  BankMe,
  BankRequest,
  BankSource,
  BankTab,
  BankToken,
  GrantPermission,
  ImportPreview,
  Inventory,
  InventoryItem,
  NewGrant,
  NewRequest,
  NewToken,
  ReplicaSlot,
  SourceStock
} from '$lib/bank';
import { previewSession } from './session.svelte';

const DAYS = ['wed', 'sun'];
/** Short pretend Discord ids: real ones are 17 to 20 digits. */
const HOPSCOTCH = '1001';
const BREAK_GLASS = '1000';
const MEMBERS: Record<string, string> = {
  [BREAK_GLASS]: 'Leapfrog',
  [HOPSCOTCH]: 'Hopscotch',
  '1002': 'Croakley',
  '1003': 'Ribbitz',
  '1004': 'Tadpolly'
};

const HOUR = 3600;
const nowS = () => Math.floor(Date.now() / 1000);
const iso = (s: number) => new Date(s * 1000).toISOString();

interface Held {
  itemId: number;
  name: string;
  count: number;
  tab: number;
}

interface Bank {
  source: BankSource;
  items: Held[];
  /** Stock set aside for raid nights, which members cannot reserve. */
  raidHeld: Record<number, number>;
}

function tabs(names: string[], at: number | null): BankTab[] {
  return names.map((name, i) => ({ index: i + 1, name, status: 'observed', observedAt: at, capacity: 98 }));
}

function source(
  id: string,
  name: string,
  guild: string,
  raidDay: string | null,
  audience: BankSource['audience'],
  ageHours: number,
  tabNames: string[]
): BankSource {
  const at = nowS() - ageHours * HOUR;
  return {
    id,
    revision: 1,
    name,
    kind: 'guild',
    guild,
    realm: 'Spineshatter',
    region: 'EU',
    audience,
    raidDay,
    managers: [],
    lastObservedAt: at,
    freshness: ageHours < 24 ? 'fresh' : ageHours < 72 ? 'warn' : 'stale',
    tabs: tabs(tabNames, at)
  };
}

function seed() {
  const banks: Bank[] = [
    {
      source: source('wed-main', 'Wednesday bank', 'Toads Bank', 'wed', 'members', 3, ['Consumables', 'Mats', 'Recipes']),
      items: [
        { itemId: 22832, name: 'Super Mana Potion', count: 60, tab: 1 },
        { itemId: 22831, name: 'Elixir of Major Agility', count: 40, tab: 1 },
        { itemId: 22854, name: 'Flask of Relentless Assault', count: 12, tab: 1 },
        { itemId: 23571, name: 'Primal Might', count: 3, tab: 2 },
        { itemId: 30183, name: 'Nether Vortex', count: 5, tab: 2 },
        { itemId: 32447, name: 'Pattern: Belt of Deep Shadow', count: 1, tab: 3 }
      ],
      raidHeld: { 22854: 4 }
    },
    {
      source: source('sun-main', 'Sunday bank', 'Toads Bank II', 'sun', 'members', 30, ['Consumables', 'Mats', 'Recipes']),
      items: [
        { itemId: 22829, name: 'Super Healing Potion', count: 45, tab: 1 },
        { itemId: 22853, name: 'Flask of Mighty Restoration', count: 8, tab: 1 },
        { itemId: 22841, name: 'Major Fire Protection Potion', count: 20, tab: 1 },
        { itemId: 23572, name: 'Primal Nether', count: 4, tab: 2 },
        { itemId: 22559, name: 'Formula: Enchant Weapon - Mongoose', count: 1, tab: 3 }
      ],
      raidHeld: { 22853: 2 }
    },
    {
      source: source('officers', 'Officer reserve', 'Toads Vault', null, 'officers', 6, ['Reserve']),
      items: [
        { itemId: 22854, name: 'Flask of Relentless Assault', count: 20, tab: 1 },
        { itemId: 22853, name: 'Flask of Mighty Restoration', count: 15, tab: 1 },
        { itemId: 30183, name: 'Nether Vortex', count: 8, tab: 1 }
      ],
      raidHeld: {}
    }
  ];
  const t = nowS();
  let n = 0;
  const request = (
    who: string,
    character: string,
    sourceId: string,
    itemId: number,
    itemName: string,
    quantity: number,
    status: BankRequest['status'],
    ageHours: number,
    note: string | null = null
  ): BankRequest => ({
    id: `req-${++n}`,
    revision: 1,
    status,
    memberId: who,
    memberName: MEMBERS[who],
    character,
    sourceId,
    itemId,
    itemName,
    quantity,
    delivered: 0,
    outstanding: quantity,
    occurrenceId: null,
    note,
    managerNote: null,
    createdAt: t - ageHours * HOUR,
    updatedAt: t - ageHours * HOUR
  });
  const requests: BankRequest[] = [
    request(HOPSCOTCH, 'Hopscotch', 'wed-main', 22854, 'Flask of Relentless Assault', 2, 'approved', 20, 'For SSC'),
    request(HOPSCOTCH, 'Lilypadd', 'sun-main', 22559, 'Formula: Enchant Weapon - Mongoose', 2, 'waitlisted', 50),
    request('1002', 'Croakley', 'wed-main', 22832, 'Super Mana Potion', 10, 'reserved', 2, 'Vashj attempts'),
    request('1003', 'Ribbitz', 'wed-main', 23571, 'Primal Might', 1, 'reserved', 5),
    request('1004', 'Tadpolly', 'sun-main', 22829, 'Super Healing Potion', 5, 'reserved', 9)
  ];
  const grants: BankGrant[] = [
    {
      id: 1,
      discord_user_id: '1002',
      display_name: 'Croakley',
      permission: 'import_bank_snapshot',
      raid_day: 'wed',
      granted_by: 1,
      granted_by_name: 'Hopscotch',
      granted_at: iso(t - 6 * 24 * HOUR)
    },
    {
      id: 2,
      discord_user_id: '1003',
      display_name: 'Ribbitz',
      permission: 'manage_bank',
      raid_day: null,
      granted_by: 2,
      granted_by_name: 'Leapfrog',
      granted_at: iso(t - 3 * 24 * HOUR)
    }
  ];
  const token = (id: number, permissions: GrantPermission[], day: string | null, note: string, ageDays: number) => ({
    id,
    permissions,
    raid_day: day,
    note,
    minted_by: 1,
    minted_by_name: 'Hopscotch',
    minted_at: iso(t - ageDays * 24 * HOUR),
    expires_at: iso(t + (7 - ageDays) * 24 * HOUR),
    max_uses: 1,
    uses: 0,
    used_by: null,
    used_at: null,
    revoked_at: null,
    status: 'active' as BankToken['status']
  });
  const used = token(1, ['import_bank_snapshot'], 'wed', 'Croakley', 6);
  Object.assign(used, { uses: 1, used_by: '1002', used_at: iso(t - 6 * 24 * HOUR + HOUR), status: 'used' });
  const tokens: (BankToken & { secret: string })[] = [
    { ...used, secret: '' },
    { ...token(2, ['manage_bank'], 'sun', 'Sunday bank alt', 1), secret: '' }
  ];
  return { banks, requests, grants, tokens, imports: new Map<string, string>(),
    /** Delivered since the last capture, per source and item: gone from the bank, not yet in a snapshot. */
    outgoing: new Map<string, number>(),
    next: 100
  };
}

let state = seed();

/** Back to the sample data (tests). */
export function resetPreviewBank() {
  state = seed();
}

// --- who is asking --------------------------------------------------------------------------------

const officer = () => previewSession.role === 'officer';

/** The days a grant held by the raider view opens; null (every bank) opens every day. */
function grantedDays(permission: GrantPermission): string[] {
  const days = new Set<string>();
  for (const g of state.grants)
    if (g.discord_user_id === HOPSCOTCH && g.permission === permission)
      for (const d of g.raid_day === null ? DAYS : [g.raid_day]) days.add(d);
  return DAYS.filter((d) => days.has(d));
}

function me(): BankMe {
  const base = { configured: true, discord_user_id: HOPSCOTCH, display_name: 'Hopscotch', break_glass: false };
  if (officer())
    return {
      ...base,
      global_officer: true,
      officer_days: DAYS,
      import_days: DAYS,
      manage_days: DAYS,
      sees_grants: true,
      manages_grants: true,
      super_admin: true,
      break_glass_admin: BREAK_GLASS
    };
  return {
    ...base,
    global_officer: false,
    officer_days: [],
    import_days: grantedDays('import_bank_snapshot'),
    manage_days: grantedDays('manage_bank'),
    sees_grants: false,
    manages_grants: false,
    super_admin: false,
    break_glass_admin: null
  };
}

const visible = () => state.banks.filter((b) => b.source.audience === 'members' || officer());

// --- stock ---------------------------------------------------------------------------------------

const OPEN = new Set(['reserved', 'approved']);

function stock(bank: Bank, itemId: number): SourceStock {
  const observed = bank.items.filter((i) => i.itemId === itemId).reduce((n, i) => n + i.count, 0);
  const raidHeld = bank.raidHeld[itemId] ?? 0;
  const pendingOutgoing = state.outgoing.get(`${bank.source.id}:${itemId}`) ?? 0;
  const directReserved = state.requests
    .filter((r) => r.sourceId === bank.source.id && r.itemId === itemId && OPEN.has(r.status))
    .reduce((n, r) => n + r.outstanding, 0);
  return {
    sourceId: bank.source.id,
    observedAt: bank.source.lastObservedAt,
    observed,
    pendingOutgoing,
    raidHeld,
    directReserved,
    available: Math.max(0, observed - pendingOutgoing - raidHeld - directReserved)
  };
}

function inventory(): Inventory {
  const items = new Map<number, InventoryItem>();
  for (const bank of visible())
    for (const held of bank.items) {
      if (items.get(held.itemId)?.sources.some((s) => s.sourceId === bank.source.id)) continue;
      const s = stock(bank, held.itemId);
      const item = items.get(held.itemId) ?? {
        itemId: held.itemId,
        name: held.name,
        sources: [],
        observed: 0,
        pendingOutgoing: 0,
        raidHeld: 0,
        directReserved: 0,
        available: 0
      };
      item.sources.push(s);
      for (const k of ['observed', 'pendingOutgoing', 'raidHeld', 'directReserved', 'available'] as const) item[k] += s[k];
      items.set(held.itemId, item);
    }
  const times = visible().map((b) => b.source.lastObservedAt ?? 0);
  return { range: { oldest: Math.min(...times), newest: Math.max(...times) }, items: [...items.values()] };
}

function replica(bank: Bank) {
  return {
    source: bank.source,
    tabs: bank.source.tabs.map((tab) => ({
      ...tab,
      slots: bank.items
        .filter((i) => i.tab === tab.index)
        .map((i, n): ReplicaSlot => ({ slot: n * 7 + 1, itemId: i.itemId, name: i.name, count: i.count }))
    }))
  };
}

// --- answers -------------------------------------------------------------------------------------

function json(body: unknown, status = 200): Response {
  if (status === 204) return new Response(null, { status });
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

function refuse(status: number, detail: string, code?: string, details?: unknown, current?: unknown): Response {
  return json({ detail, ...(code ? { error: { code, details, current } } : {}) }, status);
}

function bump(r: BankRequest, change: Partial<BankRequest>): BankRequest {
  Object.assign(r, change, { revision: r.revision + 1, updatedAt: nowS() });
  r.outstanding = Math.max(0, r.quantity - r.delivered);
  return r;
}

function createRequest(body: NewRequest): Response {
  const bank = visible().find((b) => b.source.id === body.sourceId);
  const held = bank?.items.find((i) => i.itemId === body.itemId);
  if (!bank || !held) return refuse(404, 'No such item in that bank.', 'not_found');
  const available = stock(bank, body.itemId).available;
  if (body.quantity > available && !body.waitlist)
    return refuse(409, 'Not enough in stock.', 'insufficient_stock', { available, canWaitlist: true });
  const t = nowS();
  const r: BankRequest = {
    id: `req-${++state.next}`,
    revision: 1,
    status: body.quantity > available ? 'waitlisted' : 'reserved',
    memberId: HOPSCOTCH,
    memberName: 'Hopscotch',
    character: body.character,
    sourceId: body.sourceId,
    itemId: body.itemId,
    itemName: held.name,
    quantity: body.quantity,
    delivered: 0,
    outstanding: body.quantity,
    occurrenceId: null,
    note: body.note ?? null,
    managerNote: null,
    createdAt: t,
    updatedAt: t
  };
  state.requests.unshift(r);
  return json(r, 201);
}

function dayRoute(day: string, rest: string[], method: string, body: Record<string, unknown>): Response {
  const may = me();
  const dayBanks = state.banks.filter((b) => b.source.raidDay === day || (b.source.raidDay === null && officer()));
  const ids = new Set(dayBanks.map((b) => b.source.id));
  if (rest[0] === 'requests') {
    if (!may.manage_days?.includes(day)) return refuse(403, 'Not your raid day.');
    if (rest.length === 1)
      return json(state.requests.filter((r) => ids.has(r.sourceId) && (OPEN.has(r.status) || r.status === 'waitlisted')));
    const r = state.requests.find((q) => q.id === rest[1] && ids.has(q.sourceId));
    if (!r || method !== 'POST') return refuse(404, 'No such request.', 'not_found');
    if (body.expectedRevision !== r.revision) return refuse(409, 'Changed since.', 'stale_revision', undefined, r);
    if (rest[2] === 'approve') return json(bump(r, { status: 'approved' }));
    if (rest[2] === 'reject') return json(bump(r, { status: 'rejected', managerNote: 'Rejected in the demo' }));
    const qty = Number(body.quantity ?? 0);
    if (!Number.isInteger(qty) || qty < 1 || qty > r.outstanding)
      return refuse(409, 'That is more than the request has outstanding.', 'over_allocated');
    const key = `${r.sourceId}:${r.itemId}`;
    state.outgoing.set(key, (state.outgoing.get(key) ?? 0) + qty);
    const delivered = r.delivered + qty;
    return json(bump(r, { delivered, status: delivered >= r.quantity ? 'fulfilled' : r.status }));
  }
  if (rest[0] === 'imports') {
    if (!may.import_days?.includes(day)) return refuse(403, 'Not your raid day.');
    const bank = dayBanks.find((b) => b.source.raidDay === day) ?? dayBanks[0];
    if (rest.length === 1) {
      const id = `imp-${++state.next}`;
      state.imports.set(id, bank.source.id);
      return json({ id, openedAt: nowS(), expiresAt: nowS() + 1800 }, 201);
    }
    const sourceId = state.imports.get(rest[1]);
    if (!sourceId) return refuse(404, 'That import expired.', 'import_expired');
    const target = state.banks.find((b) => b.source.id === sourceId)!;
    if (rest[2] === 'parts') return json({ exportId: rest[1], received: [1], total: 1, missing: [], complete: true });
    if (rest[2] === 'preview') {
      const preview: ImportPreview = {
        snapshotId: `snap-${rest[1]}`,
        source: { guild: target.source.guild, realm: target.source.realm, region: target.source.region },
        matchedSource: { id: target.source.id, name: target.source.name },
        uploader: { name: 'Hopscotch', realm: 'Spineshatter' },
        capturedAt: nowS() - 120,
        completedAt: nowS() - 60,
        stable: true,
        tabs: target.source.tabs.map((tab) => {
          const items = target.items.filter((i) => i.tab === tab.index);
          return { index: tab.index, name: tab.name, status: 'observed', occupied: items.length, items: items.length, olderThanBaseline: false };
        }),
        warnings: ['Demo: any pasted text is treated as a complete export, and nothing leaves this browser.'],
        existingReceipt: null
      };
      return json(preview);
    }
    // accept: the bank's copy is now as fresh as this capture, which no longer holds what was delivered since.
    const at = nowS() - 120;
    for (const held of target.items) {
      const key = `${sourceId}:${held.itemId}`;
      held.count = Math.max(0, held.count - (state.outgoing.get(key) ?? 0));
      state.outgoing.delete(key);
    }
    Object.assign(target.source, { lastObservedAt: at, freshness: 'fresh', revision: target.source.revision + 1 });
    target.source.tabs = target.source.tabs.map((tab) => ({ ...tab, observedAt: at }));
    state.imports.delete(rest[1]);
    return json({
      snapshotId: `snap-${rest[1]}`,
      sourceId,
      acceptedAt: nowS(),
      tabsUpdated: target.source.tabs.map((tab) => tab.index),
      tabsKeptAsHistory: [],
      tabsNotRead: [],
      duplicate: false
    });
  }
  return refuse(404, 'Not found');
}

function grantRoute(rest: string[], method: string, body: Record<string, unknown>): Response {
  if (!officer()) return refuse(403, 'Super admins only.');
  if (method === 'GET') return json(state.grants);
  if (method === 'DELETE') {
    state.grants = state.grants.filter((g) => g.id !== Number(rest[0]));
    return json(null, 204);
  }
  const [made, created] = addGrant(body as unknown as NewGrant);
  return json(made, created ? 201 : 200);
}

/** A grant, or the same one already held (the hub's unique constraint), and whether it is new. */
function addGrant(ask: NewGrant): [BankGrant, boolean] {
  const same = state.grants.find(
    (g) => g.discord_user_id === ask.discord_user_id && g.permission === ask.permission && g.raid_day === ask.raid_day
  );
  if (same) return [same, false];
  const made: BankGrant = {
    id: ++state.next,
    discord_user_id: ask.discord_user_id,
    display_name: MEMBERS[ask.discord_user_id] ?? `Member ${ask.discord_user_id}`,
    permission: ask.permission,
    raid_day: ask.raid_day,
    granted_by: 1,
    granted_by_name: 'Hopscotch',
    granted_at: iso(nowS())
  };
  state.grants.push(made);
  return [made, true];
}

/** An unused token past its expiry is expired, as the hub counts it. */
function expire(t: BankToken) {
  if (t.status === 'active' && Date.parse(t.expires_at) <= Date.now()) t.status = 'expired';
}

const strip = ({ secret: _secret, ...t }: BankToken & { secret: string }): BankToken => t;

function newSecret(): string {
  const bytes = new Uint8Array(18);
  crypto.getRandomValues(bytes);
  return `demo-${Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')}`;
}

function tokenRoute(rest: string[], method: string, body: Record<string, unknown>): Response {
  if (!officer()) return refuse(403, 'Super admins only.');
  if (method === 'GET') {
    state.tokens.forEach(expire);
    return json(state.tokens.map(strip).reverse());
  }
  if (method === 'DELETE') {
    const t = state.tokens.find((x) => x.id === Number(rest[0]));
    if (t && t.status === 'active') Object.assign(t, { status: 'revoked', revoked_at: iso(nowS()) });
    return json(null, 204);
  }
  const ask = body as unknown as NewToken;
  const t = nowS();
  const minted = {
    id: ++state.next,
    permissions: ask.permissions,
    raid_day: ask.raid_day,
    note: ask.note ?? '',
    minted_by: 1,
    minted_by_name: 'Hopscotch',
    minted_at: iso(t),
    expires_at: iso(t + (ask.days ?? 7) * 24 * HOUR),
    max_uses: ask.max_uses ?? 1,
    uses: 0,
    used_by: null,
    used_at: null,
    revoked_at: null,
    status: 'active' as const,
    secret: newSecret()
  };
  state.tokens.push(minted);
  return json({ ...strip(minted), token: minted.secret }, 201);
}

function redeem(body: Record<string, unknown>): Response {
  state.tokens.forEach(expire);
  const t = state.tokens.find((x) => x.secret && x.secret === body.token && x.status === 'active');
  if (!t) return refuse(403, 'That token is not valid. Ask a super admin for a new one.');
  const grants = t.permissions
    .map((permission) => addGrant({ discord_user_id: HOPSCOTCH, permission, raid_day: t.raid_day }))
    .filter(([, created]) => created)
    .map(([g]) => g);
  t.uses += 1;
  t.used_by = HOPSCOTCH;
  t.used_at = iso(nowS());
  if (t.uses >= t.max_uses) t.status = 'used';
  return json({ token_id: t.id, grants });
}

/** Answers the bank's calls from the sample state above; installed with `useBankFetch` by the preview bank page. */
export const previewBankFetch: Fetch = async (input, init = {}) => {
  const url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, 'http://preview');
  const method = (init.method ?? 'GET').toUpperCase();
  const body = typeof init.body === 'string' && init.body ? (JSON.parse(init.body) as Record<string, unknown>) : {};
  const parts = url.pathname.split('/').filter(Boolean).map(decodeURIComponent);
  if (previewSession.role === null) return refuse(401, 'Not signed in');

  // /api/bank/...
  if (parts[1] === 'bank') {
    const [, , what, id, sub] = parts;
    if (what === 'me') return json(me());
    if (what === 'sources' && !id) return json(visible().map((b) => b.source));
    if (what === 'sources' && sub === 'replica') {
      const bank = visible().find((b) => b.source.id === id);
      return bank ? json(replica(bank)) : refuse(404, 'No such bank.', 'not_found');
    }
    if (what === 'inventory') return json(inventory());
    if (what === 'requests' && !id && method === 'GET')
      return json(state.requests.filter((r) => r.memberId === HOPSCOTCH));
    if (what === 'requests' && !id) return createRequest(body as unknown as NewRequest);
    if (what === 'requests' && sub === 'cancel') {
      const r = state.requests.find((q) => q.id === id && q.memberId === HOPSCOTCH);
      if (!r) return refuse(404, 'No such request.', 'not_found');
      if (body.expectedRevision !== r.revision) return refuse(409, 'Changed since.', 'stale_revision', undefined, r);
      return json(bump(r, { status: 'cancelled' }));
    }
    if (what === 'redeem') return redeem(body);
  }
  // /api/days/{day}/bank/...
  if (parts[1] === 'days' && parts[3] === 'bank') return dayRoute(parts[2], parts.slice(4), method, body);
  // /api/admin/bank/grants|tokens
  if (parts[1] === 'admin' && parts[3] === 'grants') return grantRoute(parts.slice(4), method, body);
  if (parts[1] === 'admin' && parts[3] === 'tokens') return tokenRoute(parts.slice(4), method, body);
  return refuse(404, 'Not found');
};
