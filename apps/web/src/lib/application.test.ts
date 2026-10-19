import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  EMPTY_APPLICATION,
  RECRUIT_DRAFT_KEY,
  forgetRecruitDraft,
  rolesForClass,
  toApiBody,
  validateApplication,
  type ApplicationInput
} from './application';

const good: ApplicationInput = {
  characterName: 'Bogwalker',
  className: 'Shaman',
  primaryRole: 'Melee',
  secondaryRole: 'Healer',
  whyToads: 'A friend raids Sundays with you and says it is the friendliest pond on the server.'
};

const errors = (over: Partial<ApplicationInput>) => validateApplication({ ...good, ...over });

describe('validateApplication', () => {
  it('accepts a complete application', () => {
    expect(validateApplication(good)).toEqual({});
  });
  it('treats the secondary role as optional', () => {
    expect(errors({ secondaryRole: '' })).toEqual({});
  });
  it('requires name, class, primary role and why Toads', () => {
    expect(Object.keys(validateApplication(EMPTY_APPLICATION)).sort()).toEqual(
      ['characterName', 'className', 'primaryRole', 'whyToads'].sort()
    );
  });

  it.each(['Hopscotch', 'Jo', 'Twelveletter', 'Frögé', 'Ëlùne', '  Tadpole  ', 'Frög'])('accepts name %j', (n) => {
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

  it('rejects classes and roles not in the lists', () => {
    expect(errors({ className: 'Death Knight' }).className).toBeDefined();
    expect(errors({ className: '__proto__' }).className).toBeDefined();
    expect(errors({ className: 'constructor' }).className).toBeDefined();
    expect(errors({ primaryRole: 'DPS' }).primaryRole).toBeDefined();
    expect(errors({ secondaryRole: 'toString' }).secondaryRole).toBeDefined();
  });
  it('rejects a role the class cannot fill', () => {
    expect(errors({ className: 'Mage', primaryRole: 'Tank', secondaryRole: '' }).primaryRole).toBe('Mages raid as Ranged.');
    expect(errors({ className: 'Rogue', primaryRole: 'Melee', secondaryRole: 'Healer' }).secondaryRole).toBe(
      'Rogues raid as Melee.'
    );
    expect(errors({ className: 'Paladin', primaryRole: 'Ranged' }).primaryRole).toBe(
      'Paladins raid as Tank, Healer or Melee.'
    );
    expect(errors({ className: 'Druid', primaryRole: 'Tank', secondaryRole: 'Healer' })).toEqual({});
  });
  it('wants two different roles', () => {
    expect(errors({ secondaryRole: 'Melee' }).secondaryRole).toMatch(/different role/);
  });
  it('limits why Toads', () => {
    expect(errors({ whyToads: '   ' }).whyToads).toBeDefined();
    expect(errors({ whyToads: 'x'.repeat(1000) }).whyToads).toBeUndefined();
    expect(errors({ whyToads: 'x'.repeat(1001) }).whyToads).toBeDefined();
  });
});

describe('rolesForClass', () => {
  it('lists the roles any spec of the class fills, in role order', () => {
    expect(rolesForClass('Druid')).toEqual(['Tank', 'Healer', 'Melee', 'Ranged']);
    expect(rolesForClass('Paladin')).toEqual(['Tank', 'Healer', 'Melee']);
    expect(rolesForClass('Hunter')).toEqual(['Ranged']);
    expect(rolesForClass('__proto__')).toEqual([]);
  });
});

describe('toApiBody', () => {
  it('sends the API’s field names, trimmed, with no secondary role as null', () => {
    expect(toApiBody({ ...good, characterName: '  Bogwalker ', secondaryRole: '', whyToads: ' Friends. ' })).toEqual({
      character_name: 'Bogwalker',
      class_name: 'Shaman',
      role: 'Melee',
      secondary_role: null,
      why_toads: 'Friends.'
    });
  });
});

describe('forgetRecruitDraft', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('drops the saved answers and nothing else', () => {
    const store = new Map([
      [RECRUIT_DRAFT_KEY, '{"characterName":"Bogwalker"}'],
      ['other', 'kept']
    ]);
    vi.stubGlobal('sessionStorage', { removeItem: (k: string) => store.delete(k) });
    forgetRecruitDraft();
    expect([...store.keys()]).toEqual(['other']);
  });
  it('shrugs off blocked storage', () => {
    vi.stubGlobal('sessionStorage', {
      removeItem: () => {
        throw new Error('blocked');
      }
    });
    expect(() => forgetRecruitDraft()).not.toThrow();
  });
});
