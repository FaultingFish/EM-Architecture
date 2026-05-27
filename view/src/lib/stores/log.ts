import { writable } from 'svelte/store';

export interface AttemptEntry {
  id: string;
  ts: string;
  x: number;
  y: number;
  z: number;
  outcome: 'glitch' | 'hang' | 'crash' | 'nothing';
  [k: string]: unknown;
}

export const logStore = writable<AttemptEntry[]>([]);
