/**
 * Utility functions for generating stable message identifiers and timestamps.
 */

let counter = 0;

export function generateMessageId(prefix: string): string {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}-${Math.random().toString(36).substring(2, 7)}`;
}

export function getCurrentTimestamp(): Date {
  return new Date();
}
