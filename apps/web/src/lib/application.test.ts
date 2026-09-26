import { describe, expect, it } from 'vitest';
import { EMPTY_APPLICATION, isValidLogsUrl, rolesFor, specsFor, validateApplication, type ApplicationInput } from './application';

const good: ApplicationInput = {
  characterName: 'Bogwalker',
  className: 'Shaman',
  spec: 'Enhancement',
  role: 'Melee',
  raidDays: ['Wednesday'],
  experience: 'Cleared Kara and Gruul on Enhancement.',
  availability: 'Wed and Sun from 19:00 server time.',
  logsUrl: 'https://classic.warcraftlogs.com/character/eu/spineshatter/bogwalker'
};

const errors = (over: Partial<ApplicationInput>) => validateApplication({ ...good, ...over });

describe('validateApplication', () => {
  it('accepts a complete application', () => {
    expect(validateApplication(good)).toEqual({});
  });
  it('accepts optional fields left empty', () => {
    expect(errors({ raidDays: [], experience: '', availability: '', logsUrl: '' })).toEqual({});
  });
  it('requires name, class, spec and role', () => {
    expect(Object.keys(validateApplication(EMPTY_APPLICATION)).sort()).toEqual(
      ['characterName', 'className', 'role', 'spec'].sort()
    );
  });

  it.each(['Hopscotch', 'Jo', 'Twelveletter', 'Frögé', 'Ëlùne', '  Tadpole  ', 'Frög'])('accepts name %j', (n) => {
    expect(errors({ characterName: n }).characterName).toBeUndefined();
  });
  it.each([
    'X',
    'Thirteenchars',
    'Frog1',
    'Frog Walker',
    'Frog-walker',
    "Frog'); DROP TABLE",
    '<script>',
    'Frog​gy',
    'Frog‮gy',
    'Frog\ngy',
    '𝐅𝐫𝐨𝐠'.repeat(4),
    '١٢٣٤'
  ])('rejects name %j', (n) => {
    expect(errors({ characterName: n }).characterName).toBeDefined();
  });

  it('rejects classes, specs and roles not in the lists', () => {
    expect(errors({ className: 'Death Knight' }).className).toBeDefined();
    expect(errors({ className: '__proto__' }).className).toBeDefined();
    expect(errors({ className: 'constructor' }).className).toBeDefined();
    expect(errors({ spec: 'Frost' }).spec).toBeDefined();
    expect(errors({ spec: 'toString' }).spec).toBeDefined();
    expect(errors({ role: 'DPS' }).role).toBeDefined();
  });
  it('rejects a role the spec cannot fill', () => {
    expect(errors({ role: 'Healer' }).role).toMatch(/Enhancement Shamans raid as Melee/);
    expect(errors({ className: 'Druid', spec: 'Feral', role: 'Tank' })).toEqual({});
  });
  it('rejects unknown raid days', () => {
    expect(errors({ raidDays: ['Friday'] }).raidDays).toBeDefined();
  });
  it('limits free text', () => {
    expect(errors({ experience: 'x'.repeat(1000) }).experience).toBeUndefined();
    expect(errors({ experience: 'x'.repeat(1001) }).experience).toBeDefined();
    expect(errors({ availability: 'x'.repeat(300) }).availability).toBeUndefined();
    expect(errors({ availability: 'x'.repeat(301) }).availability).toBeDefined();
  });
});

describe('isValidLogsUrl', () => {
  it.each([
    'https://warcraftlogs.com/reports/aB3xKq9Lm2',
    'https://classic.warcraftlogs.com/character/eu/spineshatter/hopscotch',
    'https://fresh.warcraftlogs.com/reports/aB3xKq9Lm2',
    'https://sod.warcraftlogs.com/reports/aB3xKq9Lm2',
    'https://CLASSIC.warcraftlogs.com/reports/x'
  ])('accepts %s', (u) => expect(isValidLogsUrl(u)).toBe(true));

  it.each([
    'http://classic.warcraftlogs.com/reports/x',
    'javascript:alert(1)',
    'javascript://classic.warcraftlogs.com/%0aalert(1)',
    'data:text/html,<script>alert(1)</script>',
    'https://classic.warcraftlogs.com.evil.example/reports/x',
    'https://evil.example/classic.warcraftlogs.com/reports/x',
    'https://notwarcraftlogs.com/reports/x',
    'https://warcraftlogs.com@evil.example/reports/x',
    'https://user:pw@classic.warcraftlogs.com/reports/x',
    'https://classic.warcraftlogs.com:8443/reports/x',
    'https://retail.warcraftlogs.com/reports/x',
    '//classic.warcraftlogs.com/reports/x',
    'classic.warcraftlogs.com/reports/x',
    `https://classic.warcraftlogs.com/${'a'.repeat(300)}`
  ])('rejects %s', (u) => {
    expect(isValidLogsUrl(u)).toBe(false);
    expect(errors({ logsUrl: u }).logsUrl).toBeDefined();
  });
});

describe('spec helpers', () => {
  it('lists specs and roles', () => {
    expect(specsFor('Paladin')).toEqual(['Holy', 'Protection', 'Retribution']);
    expect(specsFor('Nope')).toEqual([]);
    expect(rolesFor('Druid', 'Feral')).toEqual(['Tank', 'Melee']);
  });
});
