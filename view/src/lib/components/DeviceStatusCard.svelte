<script lang="ts">
  // One card per hardware device. TODO: subscribe to devices store; render
  // available/connected/port/last_error/busy in a compact card.
  export let device: {
    name: string;
    available: boolean;
    connected: boolean;
    port: string | null;
    label: string | null;
    last_error: string | null;
    busy: boolean;
  };
</script>

<div class="card" class:offline={!device.connected}>
  <h4>{device.name}</h4>
  <p>{device.connected ? 'connected' : 'offline'} — {device.port ?? '—'}</p>
  {#if device.last_error}<p class="err">{device.last_error}</p>{/if}
</div>

<style>
  .card { border: 1px solid #ccc; padding: 0.5rem; border-radius: 0.25rem; }
  .card.offline { opacity: 0.6; }
  .err { color: #c00; }
</style>
