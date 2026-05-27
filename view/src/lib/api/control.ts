// Typed Control client.
// TODO: replace these hand-rolled wrappers with output from
// `openapi-typescript ../protocol/openapi/control.yaml -o control.types.ts`
// and a thin fetch helper.

import { CONTROL_URL } from '../config';

export async function armState() {
  const r = await fetch(`${CONTROL_URL}/arm_state`);
  return r.json();
}

export async function arm() {
  const r = await fetch(`${CONTROL_URL}/arm`, { method: 'POST' });
  return r.json();
}

export async function disarm() {
  const r = await fetch(`${CONTROL_URL}/disarm`, { method: 'POST' });
  return r.json();
}

export async function moveAbs(x: number, y: number, z: number) {
  const r = await fetch(`${CONTROL_URL}/motion/move_abs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ x, y, z })
  });
  return r.json();
}

export async function startCampaign(body: unknown) {
  const r = await fetch(`${CONTROL_URL}/campaigns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return r.json();
}

export async function listRuns(params: Record<string, string> = {}) {
  const qs = new URLSearchParams(params).toString();
  const r = await fetch(`${CONTROL_URL}/runs?${qs}`);
  return r.json();
}

export async function heatmap(z?: number, campaign?: string) {
  const qs = new URLSearchParams();
  if (z !== undefined) qs.set('z', String(z));
  if (campaign) qs.set('campaign', campaign);
  const r = await fetch(`${CONTROL_URL}/heatmap?${qs.toString()}`);
  return r.json();
}

export async function replay(runId: string) {
  const r = await fetch(`${CONTROL_URL}/replay/${runId}`, { method: 'POST' });
  return r.json();
}

export async function devices() {
  const r = await fetch(`${CONTROL_URL}/devices`);
  return r.json();
}

export async function getCampaign(id: string) {
  const r = await fetch(`${CONTROL_URL}/campaigns/${id}`);
  return r.json();
}

export async function stopCampaign(id: string) {
  const r = await fetch(`${CONTROL_URL}/campaigns/${id}/stop`, { method: 'POST' });
  return r.json();
}
