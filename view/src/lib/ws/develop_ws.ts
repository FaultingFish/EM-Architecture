// WebSocket for Develop topics (build_log, build_status, agent_output).
// Opened on-demand when a build or agent run is started, not always-on.

import { DEVELOP_URL, wsUrl } from '../config';

export function connect(): WebSocket {
  return new WebSocket(wsUrl(DEVELOP_URL));
}
