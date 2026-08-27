/** Unit tests for the client side FR-A3 password policy mirror. */
import { describe, expect, it } from 'vitest';

import { checkPassword, isBdPhoneValid, isPasswordValid } from './passwordPolicy';

describe('isPasswordValid', () => {
  it('accepts a password meeting every rule', () => {
    expect(isPasswordValid('JuFix@2026')).toBe(true);
  });

  it.each([
    ['too short', 'Ju@1a'],
    ['no uppercase', 'jufix@2026'],
    ['no lowercase', 'JUFIX@2026'],
    ['no digit', 'JuFixMed@'],
    ['no special character', 'JuFix2026'],
  ])('rejects a password with %s', (_label, password) => {
    expect(isPasswordValid(password)).toBe(false);
  });

  it('treats an empty password as invalid', () => {
    expect(isPasswordValid('')).toBe(false);
  });
});

describe('checkPassword', () => {
  it('reports each rule individually', () => {
    const rules = checkPassword('jufix');
    const byId = Object.fromEntries(rules.map((rule) => [rule.id, rule.satisfied]));

    expect(byId.lower).toBe(true);
    expect(byId.upper).toBe(false);
    expect(byId.digit).toBe(false);
  });

  it('returns one entry per rule', () => {
    expect(checkPassword('JuFix@2026')).toHaveLength(5);
  });
});

describe('isBdPhoneValid', () => {
  it.each(['01712345678', '+8801812345678', '8801912345678'])('accepts %s', (phone) => {
    expect(isBdPhoneValid(phone)).toBe(true);
  });

  it.each(['12345', '01212345678', '0171234567', 'not-a-number'])('rejects %s', (phone) => {
    expect(isBdPhoneValid(phone)).toBe(false);
  });
});
