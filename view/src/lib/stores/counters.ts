import { writable } from 'svelte/store';

export interface Counters {
  attempts: number;
  glitches: number;
  hangs: number;
  crashes: number;
  nothings: number;
  campaigns: number;
}

export const countersStore = writable<Counters>({
  attempts: 0,
  glitches: 0,
  hangs: 0,
  crashes: 0,
  nothings: 0,
  campaigns: 0
});
