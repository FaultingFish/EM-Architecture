import { createLogger } from '../logger';
import { DEVELOP_URL } from '../config';

const log = createLogger('develop-api');

async function request(method: string, path: string) {
  const url = `${DEVELOP_URL}${path}`;
  log.info(`${method} ${path}`);
  try {
    const r = await fetch(url, { method });
    if (!r.ok) {
      const text = await r.text().catch(() => '');
      log.error(`${method} ${path} => ${r.status}`, text);
      throw new Error(`Develop ${method} ${path} failed: ${r.status}`);
    }
    const data = await r.json();
    log.debug(`${method} ${path} => 200`, data);
    return data;
  } catch (err) {
    if (err instanceof TypeError) {
      log.error(`${method} ${path} network error — is Develop running on ${DEVELOP_URL}?`, err.message);
    }
    throw err;
  }
}

export async function listProjects() {
  return request('GET', '/projects');
}

export async function getProject(id: string) {
  return request('GET', `/projects/${id}`);
}

export async function listBuilds(id: string) {
  return request('GET', `/projects/${id}/builds`);
}

export async function disassembly(id: string, sha: string) {
  return request('GET', `/projects/${id}/builds/${sha}/disassembly`);
}

export async function listTargets(id: string) {
  return request('GET', `/projects/${id}/targets`);
}

export async function listPresets(id: string) {
  return request('GET', `/projects/${id}/presets`);
}
