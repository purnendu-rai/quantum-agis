import { defineConfig } from 'vitest/config';

/**
 * Vitest configuration — pure-logic unit tests (formatters, store, constants).
 * Environment: node (no DOM needed for the tested modules).
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
});
