// WebSocket client for /ws topics: build_log, build_status, agent_output.
// TODO: reconnect-on-disconnect, topic filter, message queue.

export function connect(): WebSocket {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return new WebSocket(`${proto}://${location.host}/ws`);
}
