import { describe, expect, it, vi } from 'vitest';
import { ApiError } from './api';
import {
  askedBefore,
  bankDeskError,
  hubBankDesk,
  noticeLabel,
  pendingCount,
  shown,
  sourceLabel,
  type BankRequest
} from './bank-desk';
import { previewBankDesk } from './preview/bank-desk-fake';

const req = (id: number, user: string, status: BankRequest['status'], extra: Partial<BankRequest> = {}): BankRequest => ({
  id,
  discord_user_id: user,
  requester_name: `U${user}`,
  item: `Item ${id}`,
  quantity: 1,
  source: 'discord',
  status,
  created_at: '2026-10-20T12:00:00Z',
  officer_message: null,
  decided_by_name: null,
  decided_at: null,
  notice: null,
  notice_error: null,
  ...extra
});

describe('bank desk', () => {
  const rows = [req(1, '7', 'approved'), req(2, '8', 'pending'), req(3, '7', 'pending'), req(4, '7', 'denied')];

  it('shows waiting requests first asked first, and everything newest first', () => {
    expect(shown(rows, 'pending').map((r) => r.id)).toEqual([2, 3]);
    expect(shown(rows, 'all').map((r) => r.id)).toEqual([4, 3, 2, 1]);
    expect(pendingCount(rows)).toBe(2);
  });

  it('counts each member’s asks and approvals', () => {
    expect(askedBefore(rows).get('7')).toEqual({ asked: 3, approved: 1 });
    expect(askedBefore(rows).get('8')).toEqual({ asked: 1, approved: 0 });
  });

  it('says where the answer’s DM is', () => {
    expect(noticeLabel(req(1, '7', 'pending'))).toBe('');
    expect(noticeLabel(req(1, '7', 'approved', { notice: 'queued' }))).toBe('DM on its way');
    expect(noticeLabel(req(1, '7', 'approved', { notice: 'sent' }))).toBe('DM sent');
    expect(noticeLabel(req(1, '7', 'denied', { notice: 'failed', notice_error: 'Discord refused: 403' }))).toBe(
      'DM failed: Discord refused: 403'
    );
    expect(sourceLabel('discord')).toBe('Discord');
    expect(sourceLabel('site')).toBe('Site');
  });

  it('calls the hub’s desk routes', async () => {
    const f = vi.fn(async () => new Response(JSON.stringify({ manage_days: ['sun'] })));
    const desk = hubBankDesk(f as unknown as typeof fetch);
    expect(await desk.manageDays()).toEqual(['sun']);
    await desk.incoming('sun');
    await desk.history('sun', '4242');
    await desk.mine();
    await desk.ask('Drums of Battle', 2);
    await desk.answer('sun', 9, 'deny', 'Short this week');
    const calls = f.mock.calls as unknown as [string, RequestInit][];
    expect(calls.map(([path, init]) => `${init.method ?? 'GET'} ${path}`)).toEqual([
      'GET /api/bank/me',
      'GET /api/days/sun/bank-desk/requests',
      'GET /api/days/sun/bank-desk/members/4242/requests',
      'GET /api/bank-desk/requests/mine',
      'POST /api/bank-desk/requests',
      'POST /api/days/sun/bank-desk/requests/9/deny'
    ]);
    expect(JSON.parse(String(calls[4][1].body))).toEqual({ item: 'Drums of Battle', quantity: 2 });
    expect(JSON.parse(String(calls[5][1].body))).toEqual({ message: 'Short this week' });
  });

  it('explains refusals', () => {
    expect(bankDeskError(new ApiError(403, 'Forbidden'))).toBe('Only officers answer bank requests for now.');
    expect(bankDeskError(new ApiError(409, 'That request was already approved'))).toBe('That request was already approved');
    expect(bankDeskError(new Error('x'))).toBe('Something went wrong; try again.');
  });

  it('the preview answers once, and only for officers', async () => {
    const officer = previewBankDesk(true);
    const waiting = shown(await officer.incoming('wed'), 'pending')[0];
    const answered = await officer.answer('wed', waiting.id, 'approve', '  Grab it after the raid ');
    expect([answered.status, answered.officer_message, answered.notice]).toEqual([
      'approved',
      'Grab it after the raid',
      'sent'
    ]);
    await expect(officer.answer('wed', waiting.id, 'deny', '')).rejects.toMatchObject({ status: 409 });
    const raider = previewBankDesk(false);
    expect(await raider.manageDays()).toEqual([]);
    await expect(raider.incoming('wed')).rejects.toMatchObject({ status: 403 });
    const asked = await raider.ask('Primal Fire', 3);
    expect((await raider.mine())[0]).toEqual(asked);
  });
});
