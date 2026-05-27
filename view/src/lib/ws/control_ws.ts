import { createLogger } from '../logger';
import { CONTROL_URL, wsUrl } from '../config';
import { armStore } from '../stores/arm';
import { countersStore } from '../stores/counters';
import { devicesStore, type DeviceStatus } from '../stores/devices';
import { logStore } from '../stores/log';
import { positionStore } from '../stores/position';

const log = createLogger('control-ws');

export function connect(): WebSocket {
  const url = wsUrl(CONTROL_URL);
  log.info(`connecting to ${url}`);
  const ws = new WebSocket(url);

  ws.onopen = () => log.info('connected');

  ws.onclose = (ev) => log.warn(`disconnected code=${ev.code} reason=${ev.reason || '(none)'}`);

  ws.onerror = () => log.error('connection error');

  ws.onmessage = (ev) => {
    let msg: any;
    try { msg = JSON.parse(ev.data); } catch {
      log.error('failed to parse message', ev.data);
      return;
    }
    if (msg.type !== 'event') {
      log.debug(`non-event message type=${msg.type}`, msg);
      return;
    }
    switch (msg.topic) {
      case 'position': positionStore.set(msg.payload); break;
      case 'arm':
        log.info('arm state changed', msg.payload);
        armStore.set(msg.payload);
        break;
      case 'counter': countersStore.set(msg.payload); break;
      case 'attempt':
        log.debug(`attempt outcome=${msg.payload?.outcome}`);
        logStore.update((l) => [...l.slice(-199), msg.payload]);
        break;
      case 'device_status':
        log.info(`device ${msg.payload?.name} status changed`, msg.payload);
        devicesStore.update((m) => {
          const next = new Map(m);
          const d = msg.payload as DeviceStatus;
          next.set(d.name, d);
          return next;
        });
        break;
      case 'campaign_progress':
        log.debug('campaign progress', msg.payload);
        break;
      default:
        log.warn(`unknown topic: ${msg.topic}`, msg.payload);
        break;
    }
  };
  return ws;
}
