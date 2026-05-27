// Service endpoint configuration. Override per-deployment by editing this file
// or by setting `window.EMFI_VIEW_CONFIG` before the app loads.

export const CONTROL_URL = import.meta.env.VITE_CONTROL_URL ?? 'http://localhost:8001';
export const DEVELOP_URL = import.meta.env.VITE_DEVELOP_URL ?? 'http://localhost:8002';

export function wsUrl(httpUrl: string, path = '/ws'): string {
  const u = new URL(httpUrl);
  u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
  u.pathname = path;
  return u.toString();
}
