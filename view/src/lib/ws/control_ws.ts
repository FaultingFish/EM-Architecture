// Single shared WebSocket connection to Control. Routes messages by topic
// into the stores in src/lib/stores/.
//
// TODO:
//   - reconnect with exponential backoff (cap ~5s)
//   - command/response correlation by id (the old glitchweb client did this)
//   - command queue while disconnected (5 s window)

import { CONTROL_URL, wsUrl } from '../config';
import { armStore } from '../stores/arm';
import { countersStore } from '../stores/counters';
import { devicesStore, type DeviceStatus } from '../stores/devices';
import { logStore } from '../stores/log';
import { positionStore } from '../stores/position';

export function connect(): WebSocket {
  const ws = new WebSocket(wsUrl(CONTROL_URL));
  ws.onmessage = (ev) => {
    let msg: any;
    try { msg = JSON.parse(ev.data); } catch { return; }
    if (msg.type !== 'event') return;
    switch (msg.topic) {
      case 'position': positionStore.set(msg.payload); break;
      case 'arm': armStore.set(msg.payload); break;
      case 'counter': countersStore.set(msg.payload); break;
      case 'attempt': logStore.update((l) => [...l.slice(-199), msg.payload]); break;
      case 'device_status':
        devicesStore.update((m) => {
          const next = new Map(m);
          const d = msg.payload as DeviceStatus;
          next.set(d.name, d);
          return next;
        });
        break;
      case 'campaign_progress': break;
      default: break;
    }
  };
  return ws;
}
