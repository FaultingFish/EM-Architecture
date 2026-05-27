// Typed API client for Develop's backend.
//
// Build-out plan:
//   1. Run `npx openapi-typescript http://localhost:8002/openapi.json -o ./generated.ts`
//      (or read from ../../../protocol/openapi/develop.yaml)
//   2. Import paths types and wrap fetch() with type-safe helpers.

export const API_BASE = '';

export async function listProjects() {
  const r = await fetch(`${API_BASE}/projects`);
  if (!r.ok) throw new Error(`listProjects: ${r.status}`);
  return r.json();
}

export async function getProject(id: string) {
  const r = await fetch(`${API_BASE}/projects/${id}`);
  if (!r.ok) throw new Error(`getProject: ${r.status}`);
  return r.json();
}

export async function build(id: string, version?: string) {
  const r = await fetch(`${API_BASE}/projects/${id}/builds`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version })
  });
  if (!r.ok) throw new Error(`build: ${r.status}`);
  return r.json();
}

export async function getDisassembly(id: string, sha: string) {
  const r = await fetch(`${API_BASE}/projects/${id}/builds/${sha}/disassembly`);
  if (!r.ok) throw new Error(`getDisassembly: ${r.status}`);
  return r.json();
}
