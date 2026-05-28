import { createLogger } from '../logger';
import { CONTROL_URL } from '../config';

const log = createLogger('control-api');

export class ApiError extends Error {
  status: number;
  body: any;
  constructor(message: string, status: number, body: any) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request(method: string, path: string, body?: unknown) {
  const url = `${CONTROL_URL}${path}`;
  log.info(`${method} ${path}`);
  try {
    const opts: RequestInit = { method };
    if (body !== undefined) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = JSON.stringify(body);
    }
    const r = await fetch(url, opts);
    if (!r.ok) {
      let parsed: any = null;
      try { parsed = await r.json(); } catch { /* not JSON */ }
      log.error(`${method} ${path} => ${r.status}`, parsed);
      throw new ApiError(`Control ${method} ${path} failed: ${r.status}`, r.status, parsed);
    }
    const data = await r.json();
    log.debug(`${method} ${path} => 200`, data);
    return data;
  } catch (err) {
    if (err instanceof TypeError) {
      log.error(`${method} ${path} network error — is Control running on ${CONTROL_URL}?`, err.message);
    }
    throw err;
  }
}

export async function armState() {
  return request('GET', '/arm_state');
}

export async function arm() {
  return request('POST', '/arm');
}

export async function disarm() {
  return request('POST', '/disarm');
}

export async function moveAbs(x: number, y: number, z: number) {
  return request('POST', '/motion/move_abs', { x, y, z });
}

export async function startCampaign(body: unknown) {
  return request('POST', '/campaigns', body);
}

export async function listRuns(params: Record<string, string> = {}) {
  const qs = new URLSearchParams(params).toString();
  return request('GET', `/runs?${qs}`);
}

export async function heatmap(z?: number, campaign?: string) {
  const qs = new URLSearchParams();
  if (z !== undefined) qs.set('z', String(z));
  if (campaign) qs.set('campaign', campaign);
  return request('GET', `/heatmap?${qs.toString()}`);
}

export async function replay(runId: string) {
  return request('POST', `/replay/${runId}`);
}

export async function devices() {
  return request('GET', '/devices');
}

export async function getCampaign(id: string) {
  return request('GET', `/campaigns/${id}`);
}

export async function stopCampaign(id: string) {
  return request('POST', `/campaigns/${id}/stop`);
}

export async function moveRel(axis: string, distance: number) {
  return request('POST', '/motion/move_rel', { axis, distance });
}

export async function home() {
  return request('POST', '/motion/home');
}

export async function setOrigin() {
  return request('POST', '/motion/set_origin');
}

export async function setTopRight(x: number, y: number) {
  return request('POST', '/motion/set_top_right', { x, y });
}

export async function connectDevice(id: string, port?: string) {
  return request('POST', `/devices/${id}/connect`, port ? { port } : undefined);
}

export async function shouterConfig(params: Record<string, unknown>) {
  return request('POST', '/shouter/config', params);
}

export async function shouterPulse() {
  return request('POST', '/shouter/pulse');
}

export async function shouterArm() {
  return request('POST', '/shouter/arm');
}

export async function shouterDisarm() {
  return request('POST', '/shouter/disarm');
}

export async function listCampaigns() {
  return request('GET', '/campaigns');
}
