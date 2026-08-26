/**
 * Vitest global setup.
 *
 * Registers jest-dom matchers and clears localStorage between tests so that a
 * stored token from one test cannot leak into another.
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, vi } from 'vitest';

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});
