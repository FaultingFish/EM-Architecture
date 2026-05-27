<script lang="ts">
  // Inputs for delay_us / pulse_width_ns / voltage_v sweep ranges + attempts_per_point.
  // TODO: validate against emfi_protocol.SweepParams shape.
  export let value = {
    delay_us: null as { start: number; stop: number; step: number } | null,
    pulse_width_ns: null as { start: number; stop: number; step: number } | null,
    voltage_v: null as { start: number; stop: number; step: number } | null,
    attempts_per_point: 1
  };
</script>

<fieldset>
  <legend>Sweep</legend>
  <p>TODO: numeric range inputs.</p>
  <pre>{JSON.stringify(value, null, 2)}</pre>
</fieldset>
