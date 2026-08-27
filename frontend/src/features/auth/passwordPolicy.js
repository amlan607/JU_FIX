/**
 * Client side mirror of the FR-A3 password policy.
 *
 * The backend is the authority; this module only gives the user immediate
 * feedback while typing so the form does not need a round trip to show a
 * predictable error.
 */

export const PASSWORD_MIN_LENGTH = 8;

/** Each rule the password must satisfy. */
export const PASSWORD_RULES = [
  { id: 'length', label: `At least ${PASSWORD_MIN_LENGTH} characters`, test: (v) => v.length >= PASSWORD_MIN_LENGTH },
  { id: 'upper', label: 'One uppercase letter', test: (v) => /[A-Z]/.test(v) },
  { id: 'lower', label: 'One lowercase letter', test: (v) => /[a-z]/.test(v) },
  { id: 'digit', label: 'One digit', test: (v) => /\d/.test(v) },
  { id: 'special', label: 'One special character', test: (v) => /[^A-Za-z0-9]/.test(v) },
];

/**
 * Evaluate a candidate password against every rule.
 * @param {string} password The candidate password.
 * @returns {Array<{id: string, label: string, satisfied: boolean}>} Rule results.
 */
export function checkPassword(password = '') {
  return PASSWORD_RULES.map((rule) => ({
    id: rule.id,
    label: rule.label,
    satisfied: rule.test(password),
  }));
}

/**
 * Report whether a password satisfies the whole policy.
 * @param {string} password The candidate password.
 * @returns {boolean} True when every rule passes.
 */
export function isPasswordValid(password = '') {
  return PASSWORD_RULES.every((rule) => rule.test(password));
}

/** Bangladeshi mobile number pattern matching the backend validator. */
const BD_PHONE = /^(?:\+?88)?01[3-9]\d{8}$/;

/**
 * Report whether a phone number is a valid Bangladeshi mobile number.
 * @param {string} phone The candidate number.
 * @returns {boolean} True when the number is valid.
 */
export function isBdPhoneValid(phone = '') {
  return BD_PHONE.test(phone.replaceAll(' ', ''));
}
