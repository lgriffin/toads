import { describe, expect, it } from 'vitest';
import { RECORD_GROUPS, clearClock, reportUrl } from './records';

describe('records', () => {
  it('formats clear times as the logs show them', () => {
    expect(clearClock(5829689)).toBe('1:37:10');
    expect(clearClock(1463316)).toBe('24:23');
    expect(clearClock(3494558)).toBe('58:15');
  });

  it('has a real report behind every record', () => {
    for (const g of RECORD_GROUPS) {
      expect(g.records.length).toBeGreaterThan(0);
      for (const r of g.records) {
        expect(r.code).toMatch(/^[A-Za-z0-9]{16}$/);
        expect(r.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        expect(reportUrl(r.code)).toBe(`https://fresh.warcraftlogs.com/reports/${r.code}`);
      }
    }
  });
});
