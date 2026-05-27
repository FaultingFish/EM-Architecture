import { writable } from 'svelte/store';

export interface DeviceStatus {
	name: string;
	available: boolean;
	connected: boolean;
	port: string | null;
	label: string | null;
	last_error: string | null;
	busy: boolean;
}

export const devicesStore = writable<Map<string, DeviceStatus>>(new Map());
