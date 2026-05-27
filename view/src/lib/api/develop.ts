// Typed Develop client.
// TODO: replace with openapi-typescript output.

import { DEVELOP_URL } from '../config';

export async function listProjects() {
  const r = await fetch(`${DEVELOP_URL}/projects`);
  return r.json();
}

export async function getProject(id: string) {
  const r = await fetch(`${DEVELOP_URL}/projects/${id}`);
  return r.json();
}

export async function listBuilds(id: string) {
  const r = await fetch(`${DEVELOP_URL}/projects/${id}/builds`);
  return r.json();
}

export async function disassembly(id: string, sha: string) {
  const r = await fetch(`${DEVELOP_URL}/projects/${id}/builds/${sha}/disassembly`);
  return r.json();
}

export async function listTargets(id: string) {
  const r = await fetch(`${DEVELOP_URL}/projects/${id}/targets`);
  return r.json();
}
