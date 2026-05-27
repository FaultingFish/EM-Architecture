<script lang="ts">
  export let value = {
    delay_us: null as { start: number; stop: number; step: number } | null,
    pulse_width_ns: null as { start: number; stop: number; step: number } | null,
    voltage_v: null as { start: number; stop: number; step: number } | null,
    attempts_per_point: 1
  };

  let delayEnabled = false;
  let pulseEnabled = false;
  let voltageEnabled = false;

  let delayStart = 1.0, delayStop = 10.0, delayStep = 1.0;
  let pulseStart = 80, pulseStop = 200, pulseStep = 10;
  let voltageStart = 200, voltageStop = 300, voltageStep = 10;

  $: value.delay_us = delayEnabled ? { start: delayStart, stop: delayStop, step: delayStep } : null;
  $: value.pulse_width_ns = pulseEnabled ? { start: pulseStart, stop: pulseStop, step: pulseStep } : null;
  $: value.voltage_v = voltageEnabled ? { start: voltageStart, stop: voltageStop, step: voltageStep } : null;
</script>

<fieldset>
  <legend>Sweep Parameters</legend>

  <div class="sweep-row">
    <label class="toggle">
      <input type="checkbox" bind:checked={delayEnabled} />
      Delay (us)
    </label>
    {#if delayEnabled}
      <input type="number" bind:value={delayStart} min="0" step="0.1" placeholder="start" />
      <span class="sep">-</span>
      <input type="number" bind:value={delayStop} min="0" step="0.1" placeholder="stop" />
      <span class="sep">step</span>
      <input type="number" bind:value={delayStep} min="0.01" step="0.1" placeholder="step" />
    {/if}
  </div>

  <div class="sweep-row">
    <label class="toggle">
      <input type="checkbox" bind:checked={pulseEnabled} />
      Pulse width (ns)
    </label>
    {#if pulseEnabled}
      <input type="number" bind:value={pulseStart} min="0" step="1" />
      <span class="sep">-</span>
      <input type="number" bind:value={pulseStop} min="0" step="1" />
      <span class="sep">step</span>
      <input type="number" bind:value={pulseStep} min="1" step="1" />
    {/if}
  </div>

  <div class="sweep-row">
    <label class="toggle">
      <input type="checkbox" bind:checked={voltageEnabled} />
      Voltage (V)
    </label>
    {#if voltageEnabled}
      <input type="number" bind:value={voltageStart} min="0" step="1" />
      <span class="sep">-</span>
      <input type="number" bind:value={voltageStop} min="0" step="1" />
      <span class="sep">step</span>
      <input type="number" bind:value={voltageStep} min="1" step="1" />
    {/if}
  </div>

  <div class="sweep-row">
    <label>Attempts / point</label>
    <input type="number" bind:value={value.attempts_per_point} min="1" step="1" />
  </div>
</fieldset>

<style>
  fieldset { display: flex; flex-direction: column; gap: 0.5rem; }
  .sweep-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
  }
  .toggle { display: flex; align-items: center; gap: 0.3rem; min-width: 10rem; cursor: pointer; }
  .sep { color: var(--muted); font-size: 11px; }
  input[type="number"] { width: 4.5rem; }
</style>
