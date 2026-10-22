import { describe, expect, it, vi } from 'vitest';
import { ApiError, claimError, isViewAsRefusal } from './api';
import { setupError } from './setup';
import { startViewAs, stopViewAs, viewAsLabel, viewAsNights } from './view-as';

describe('view as', () => {
  it('names the role it shows', () => {
    expect(viewAsLabel({ role: 'raider', name: 'Sunday' })).toBe('Sunday raider');
    expect(viewAsLabel({ role: 'officer', name: 'Wednesday' })).toBe('Wednesday officer');
  });

  it('lists the hub’s nights, else the web app’s own', () => {
    const fallback = { wed: 'Wednesday', sun: 'Sunday' };
    expect(viewAsNights({ thu: 'Thursday' }, fallback)).toEqual([{ id: 'thu', name: 'Thursday' }]);
    expect(viewAsNights(undefined, fallback).map((n) => n.id)).toEqual(['wed', 'sun']);
    expect(viewAsNights({}, fallback).map((n) => n.id)).toEqual(['wed', 'sun']);
  });

  it('calls the super admins’ routes', async () => {
    const f = vi.fn(async () => new Response(JSON.stringify({ role: 'raider', raid_day: 'sun', name: 'Sunday' })));
    expect(await startViewAs('raider', 'sun', f)).toEqual({ role: 'raider', raid_day: 'sun', name: 'Sunday' });
    expect(f).toHaveBeenLastCalledWith('/api/admin/view-as/raider/sun', expect.objectContaining({ method: 'PUT' }));
    const g = vi.fn(async () => new Response(null, { status: 204 }));
    await stopViewAs(g);
    expect(g).toHaveBeenLastCalledWith('/api/admin/view-as', expect.objectContaining({ method: 'DELETE' }));
  });

  it('says a refusal is the read-only view, not a missing role', () => {
    const readOnly = new ApiError(403, 'You are viewing the hub as another role, which is read only. Go back to make changes.');
    expect(isViewAsRefusal(readOnly)).toBe(true);
    expect(claimError(readOnly)).toBe(readOnly.message);
    expect(setupError(readOnly)).toBe(readOnly.message);
    expect(isViewAsRefusal(new ApiError(403, 'Forbidden'))).toBe(false);
    expect(claimError(new ApiError(403, 'Forbidden'))).toMatch(/trial or raider/);
  });
});
